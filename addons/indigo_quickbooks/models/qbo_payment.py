# -*- coding: utf-8 -*-
"""Cobros de QuickBooks -> Indigo.

QuickBooks es la fuente de los cobros: la oficina los registra alli y aqui
llegan solos. Un `Payment` de QBO puede pagar varias facturas; por cada factura
que conocemos (por su `qbo_id`) hay a lo sumo UN pago vivo en Odoo con
`qbo_payment_id = "<Payment.Id>:<Invoice.Id>"`.

Se aplica comparando lo que QBO dice ahora con lo que hay aqui (no por tipo de
aviso): crear, editar, anular o borrar en QBO acaban igual — lo que no cuadra se
anula aqui y se rehace. Asi un aviso repetido o fuera de orden no duplica nada.
"""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .qbo_client import QboError

_logger = logging.getLogger(__name__)

# pg_advisory_xact_lock(PAY_LOCK, <payment id>): el webhook y el CDC pueden
# traer el mismo cobro a la vez.
PAY_LOCK = 0x51B0_7A11
EPS = 0.005


class AccountPayment(models.Model):
    _inherit = "account.payment"

    qbo_payment_id = fields.Char(string="QuickBooks payment", copy=False, index=True,
                                 help="<QuickBooks Payment Id>:<QuickBooks Invoice Id>")
    # Lo que QBO aplico a esta factura. Puede ser mas que el pago de aqui (se
    # limita al saldo): se compara con esto para saber si cambio en QBO.
    qbo_amount = fields.Float(string="Amount in QuickBooks", copy=False)


class IndigoQboPayments(models.AbstractModel):
    _inherit = "indigo.qbo"

    # ------------------------------------------------------------ aplicar

    @staticmethod
    def _qbo_wanted(pdict):
        """{qbo invoice id: importe} que el Payment de QBO aplica a facturas.
        Borrado (None o status Deleted) o anulado (importes 0) -> vacio."""
        wanted = {}
        if not pdict or pdict.get("status") == "Deleted":
            return wanted
        for line in pdict.get("Line") or []:
            amount = float(line.get("Amount") or 0.0)
            for lt in line.get("LinkedTxn") or []:
                if lt.get("TxnType") == "Invoice" and lt.get("TxnId"):
                    key = str(lt["TxnId"])
                    wanted[key] = wanted.get(key, 0.0) + amount
                    break
        return {k: round(v, 2) for k, v in wanted.items() if v > EPS}

    def _qbo_apply_payment(self, pid, pdict):
        """Deja los pagos de Odoo como dice el Payment `pid` de QBO (`pdict`
        None = ya no existe). Devuelve las facturas tocadas."""
        pid = str(pid)
        self.env.cr.execute("SELECT pg_advisory_xact_lock(%s, %s)", (PAY_LOCK, int(pid) % 2147483647))
        wanted = self._qbo_wanted(pdict)
        txn_date = fields.Date.to_date((pdict or {}).get("TxnDate")) if pdict else None
        ref = (pdict or {}).get("PaymentRefNum") or ""
        Payment = self.env["account.payment"].sudo()
        Move = self.env["account.move"].sudo()
        touched = Move.browse()

        live = Payment.search([("qbo_payment_id", "=like", "%s:%%" % pid), ("state", "!=", "cancel")])
        for pay in live:
            inv_id = pay.qbo_payment_id.split(":", 1)[1]
            want = wanted.get(inv_id, 0.0)
            if want > EPS and abs(pay.qbo_amount - want) <= EPS and pay.date == txn_date:
                wanted.pop(inv_id)  # igual que en QBO: nada que hacer
                continue
            moves = pay.reconciled_invoice_ids
            pay.action_draft()
            pay.action_cancel()
            touched |= moves
            note = _("QuickBooks payment %s for %s was changed or removed in QuickBooks: undone here.") % (
                ref or "#" + pid, moves[:1]._indigo_money(pay.amount) if moves else pay.amount)
            for m in moves:
                m.message_post(body=note)
                m._indigo_log_on_orders(note)

        if wanted:
            journal = self.env["indigo.billing"].sudo()._bank_journal()
            if not journal:
                raise UserError(_("There is no bank journal: run the invoicing setup."))
        for inv_id, amount in wanted.items():
            move = Move.search([("move_type", "=", "out_invoice"), ("qbo_id", "=", inv_id),
                                ("state", "=", "posted")], limit=1)
            if not move:
                _logger.info("QBO payment %s pays invoice %s, which Indigo doesn't know: ignored", pid, inv_id)
                continue
            apply = min(amount, move.amount_residual)
            if apply <= EPS:
                _logger.info("QBO payment %s: invoice %s is already paid here; nothing recorded", pid, move.name)
                move.message_post(body=_(
                    "QuickBooks recorded a payment of %s (%s), but this invoice was already paid here: not recorded twice."
                ) % (move._indigo_money(amount), ref or "#" + pid))
                continue
            label = _("QuickBooks payment %s") % (ref or "#" + pid)
            wizard = self.env["account.payment.register"].sudo().with_context(
                active_model="account.move", active_ids=move.ids, indigo_qbo_apply=True,
            ).create({
                "amount": apply,
                "payment_date": txn_date or fields.Date.context_today(self),
                "journal_id": journal.id,
                "communication": "%s · %s" % (move.name, label),
            })
            payments = wizard._create_payments()
            payments.write({"qbo_payment_id": "%s:%s" % (pid, inv_id), "qbo_amount": amount})
            touched |= move
            note = _("Payment of %s received from QuickBooks (%s).") % (move._indigo_money(apply), label)
            if apply < amount - EPS:
                note += " " + _("QuickBooks applied %s; the rest is more than this invoice's balance here.") % (
                    move._indigo_money(amount))
            move.message_post(body=note)
            move._indigo_log_on_orders(note)

        if touched:
            touched._indigo_sync_orders()
            self._qbo_auto_close(touched)
            self._icp().set_param("indigo_qbo.last_payment_at", fields.Datetime.to_string(fields.Datetime.now()))
        return touched

    def _qbo_auto_close(self, moves):
        """Ajuste «cerrar la orden al cobrar» (apagado por defecto): una orden
        instalada o facturada cuyas facturas quedan pagadas pasa a Closed."""
        if not self._qbo_setting_auto_close():
            return
        closed = self.env.ref("indigo_decors.stage_closed", raise_if_not_found=False)
        if not closed:
            return
        for order in moves.mapped("indigo_order_ids"):
            if (order.payment_state == "paid" and order.stage_id.code in ("installed", "invoiced")
                    and not order.cancelled_at):
                order.sudo().write({"stage_id": closed.id})
                order.sudo()._message_log(body=_("Closed automatically: paid in QuickBooks."))

    # ------------------------------------------------------------ ajustes

    def _qbo_setting_auto_close(self):
        return self._icp().get_param("indigo_qbo.auto_close") == "1"

    @api.model
    def qbo_save_settings(self, vals):
        """vals: auto_close (bool). Solo gerencia."""
        self._assert_manager()
        vals = vals or {}
        if "auto_close" in vals:
            self._icp().set_param("indigo_qbo.auto_close", "1" if vals["auto_close"] else "")
        return self.qbo_status()

    @api.model
    def qbo_status(self):
        st = super().qbo_status()
        st.update({
            "auto_close": self._qbo_setting_auto_close(),
            "last_payment_at": self._icp().get_param("indigo_qbo.last_payment_at") or False,
            # Con conexion, los cobros se registran en QuickBooks, no aqui.
            "payments_from_qbo": self.env["indigo.billing"]._qbo_payments_from_qbo(),
        })
        return st

    def _qbo_reset_company(self, old_realm, new_realm):
        super()._qbo_reset_company(old_realm, new_realm)
        # Los cobros de la otra empresa no se tocan (son dinero recibido),
        # pero dejan de estar ligados a ella; y el CDC empieza de cero.
        self.env["account.payment"].sudo().search([("qbo_payment_id", "!=", False)]).write(
            {"qbo_payment_id": False, "qbo_amount": 0.0})
        self._icp().set_param("indigo_qbo.cdc_cursor", "")
        self.env["indigo.qbo.event"].sudo().search([]).unlink()


class IndigoBillingQboPayments(models.AbstractModel):
    _inherit = "indigo.billing"

    def _qbo_payments_from_qbo(self):
        """Con QuickBooks REAL conectado, los cobros se registran alli y llegan
        solos. Con el sandbox (pruebas con ordenes reales, 12-oct-2026) la
        oficina sigue registrando sus cobros aqui: el sandbox no es su
        contabilidad."""
        client = self.env["indigo.qbo.client"].sudo()
        if not (client.is_configured() and client.is_connected()):
            return False
        return client._config()["environment"] == "production"

    @api.model
    def indigo_billing_detail(self, move_id):
        res = super().indigo_billing_detail(move_id)
        res["payments_from_qbo"] = self._qbo_payments_from_qbo()
        return res

    @api.model
    def indigo_billing_register_payment(self, move_id, vals):
        client = self.env["indigo.qbo.client"].sudo()
        # En las pruebas de otros modulos (que no saben de QuickBooks) no se
        # bloquea aunque la base de desarrollo este conectada al sandbox.
        enforce = not client._inline() or self.env.context.get("qbo_enforce_payments")
        if enforce and not self.env.context.get("indigo_qbo_apply") and self._qbo_payments_from_qbo():
            raise UserError(_(
                "Payments are recorded in QuickBooks and come here by themselves. "
                "Record this payment in QuickBooks."
            ))
        return super().indigo_billing_register_payment(move_id, vals)


def qbo_fetch_payment(client, pid):
    """El Payment de QBO, o None si ya no existe (borrado). Por query y no por
    GET: un borrado responde con lista vacia en vez de un error que habria que
    distinguir de los demas."""
    if not str(pid).isdigit():
        raise QboError("api", _("Bad QuickBooks payment id: %s") % pid)
    rows = client.query("SELECT * FROM Payment WHERE Id = '%s'" % pid, "Payment")
    return rows[0] if rows else None
