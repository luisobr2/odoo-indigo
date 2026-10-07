# -*- coding: utf-8 -*-
"""Enviar las facturas de Indigo a QuickBooks.

Estados (`qbo_state`):
  none      no va a QBO (sin conexion, o nunca emitida)
  pending   por enviar (recien emitida, corregida o anulada)
  synced    creada/actualizada por Indigo en QBO, mismo total
  linked    ya estaba en QBO (metida a mano) con el mismo total: se enlazo
  mismatch  hay que mirarla: el total no coincide, o se cambio aqui una
            factura que en QBO se metio a mano (no se pisa trabajo manual)
  error     no se pudo (falta una equivalencia, QBO fallo...): se reintenta
  voided    anulada en QBO

Reglas: antes de crear se busca por numero (DocNumber) para no duplicar; una
factura enlazada (`qbo_origin = manual`) nunca se sobrescribe.
"""
import logging
from datetime import timedelta
from functools import partial

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.modules.registry import Registry

from .qbo_client import QboError
from .qbo_mapping import _esc

_logger = logging.getLogger(__name__)

QBO_STATES = [
    ("none", "Not in QuickBooks"),
    ("pending", "Pending"),
    ("synced", "Synced"),
    ("linked", "Linked (entered by hand in QuickBooks)"),
    ("mismatch", "Doesn't match"),
    ("error", "Error"),
    ("voided", "Voided in QuickBooks"),
]
BACKOFF_MAX_MIN = 360
CRON_BATCH = 20


def _money(value):
    return "$%.2f" % (value or 0.0)


def _same(a, b):
    return abs((a or 0.0) - (b or 0.0)) < 0.005


class AccountMove(models.Model):
    _inherit = "account.move"

    qbo_id = fields.Char(string="QuickBooks invoice id", copy=False, index=True)
    qbo_sync_token = fields.Char(copy=False)
    qbo_state = fields.Selection(QBO_STATES, string="QuickBooks", default="none", copy=False, index=True)
    qbo_error = fields.Text(string="QuickBooks problem", copy=False)
    qbo_synced_at = fields.Datetime(copy=False)
    qbo_total = fields.Float(string="Total in QuickBooks", copy=False)
    qbo_attempts = fields.Integer(copy=False)
    qbo_next_try = fields.Datetime(copy=False)
    qbo_origin = fields.Selection(
        [("indigo", "Created by Indigo"), ("manual", "Entered by hand in QuickBooks")], copy=False)

    # ------------------------------------------------------------ cuerpo

    def _qbo_payload(self):
        self.ensure_one()
        partner = self.partner_id
        if not partner.qbo_customer_id:
            raise QboError("mapping", _(
                "%s isn't matched with a QuickBooks customer yet (Billing → QuickBooks)."
            ) % partner.name)
        lines = []
        for ln in self.invoice_line_ids.filtered(lambda l: l.display_type == "product"):
            item = ln.product_id.qbo_item_id
            if not item:
                raise QboError("mapping", _(
                    "%s isn't matched with a QuickBooks product yet (Billing → QuickBooks)."
                ) % (ln.product_id.name or ln.name))
            lines.append({
                "DetailType": "SalesItemLineDetail",
                "Amount": round(ln.quantity * ln.price_unit, 2),
                "Description": (ln.name or "")[:4000],
                "SalesItemLineDetail": {
                    "ItemRef": {"value": item},
                    "Qty": ln.quantity,
                    "UnitPrice": ln.price_unit,
                    "TaxCodeRef": {"value": "TAX" if ln.tax_ids else "NON"},
                },
            })
        if not lines:
            raise QboError("mapping", _("The invoice has no lines."))
        pos = list(dict.fromkeys(
            o.customer_po.strip() for o in self.indigo_order_ids if (o.customer_po or "").strip()))
        note = "Indigo #%s" % self.name + (" · PO %s" % ", ".join(pos) if pos else "")
        body = {
            "DocNumber": self.name,
            "CustomerRef": {"value": partner.qbo_customer_id},
            "Line": lines,
            "PrivateNote": note[:4000],
            # El correo al dealer lo manda Indigo; QBO no.
            "EmailStatus": "NotSet",
        }
        if self.invoice_date:
            body["TxnDate"] = fields.Date.to_string(self.invoice_date)
        if self.invoice_date_due:
            body["DueDate"] = fields.Date.to_string(self.invoice_date_due)
        return body

    # ------------------------------------------------------------ enviar

    def _qbo_result(self, inv, origin):
        total = inv.get("TotalAmt") or 0.0
        vals = {
            "qbo_id": inv.get("Id"),
            "qbo_sync_token": inv.get("SyncToken"),
            "qbo_origin": origin,
            "qbo_total": total,
        }
        if _same(total, self.amount_total):
            vals.update(qbo_state="synced" if origin == "indigo" else "linked", qbo_error=False)
        elif origin == "manual":
            vals.update(qbo_state="mismatch", qbo_error=_(
                "QuickBooks already has invoice #%(n)s (entered by hand) for %(qbo)s; here it's %(here)s."
            ) % {"n": self.name, "qbo": _money(total), "here": _money(self.amount_total)})
        else:
            vals.update(qbo_state="mismatch", qbo_error=_(
                "QuickBooks calculated %(qbo)s and Indigo %(here)s. Check the sales tax."
            ) % {"qbo": _money(total), "here": _money(self.amount_total)})
        return vals

    def _qbo_push(self):
        """Lleva esta factura a QBO. Devuelve los valores qbo_* a guardar
        (o None si no hay nada que hacer todavia)."""
        self.ensure_one()
        client = self.env["indigo.qbo.client"].sudo()
        if self.state == "cancel":
            if not self.qbo_id:
                return {"qbo_state": "none", "qbo_error": False}
            if self.qbo_origin == "manual":
                return {"qbo_state": "mismatch", "qbo_error": _(
                    "Voided here, but in QuickBooks it was entered by hand: void it there too.")}
            inv = client.get("invoice/%s" % self.qbo_id).get("Invoice") or {}
            res = client.post("invoice", {"Id": self.qbo_id, "SyncToken": inv.get("SyncToken")},
                              params={"operation": "void"}).get("Invoice") or {}
            return {"qbo_state": "voided", "qbo_error": False, "qbo_sync_token": res.get("SyncToken")}
        if self.state != "posted":
            return None  # borrador (p. ej. en correccion): se envia al reemitir
        if not self.qbo_id:
            found = client.query(
                "SELECT * FROM Invoice WHERE DocNumber = '%s'" % _esc(self.name), "Invoice")
            if found:
                return self._qbo_result(found[0], "manual")
            inv = client.post("invoice", self._qbo_payload()).get("Invoice") or {}
            return self._qbo_result(inv, "indigo")
        if self.qbo_origin == "manual":
            return {"qbo_state": "mismatch", "qbo_error": _(
                "Changed here, but in QuickBooks it was entered by hand: update it there too.")}
        current = client.get("invoice/%s" % self.qbo_id).get("Invoice") or {}
        body = self._qbo_payload()
        body.update({"Id": self.qbo_id, "SyncToken": current.get("SyncToken"), "sparse": False})
        inv = client.post("invoice", body).get("Invoice") or {}
        return self._qbo_result(inv, "indigo")

    def _qbo_process(self, commit=False):
        client = self.env["indigo.qbo.client"].sudo()
        if not (client.is_configured() and client.is_connected()):
            return
        now = fields.Datetime.now()
        for move in self:
            try:
                vals = move._qbo_push()
            except QboError as e:
                if e.code == "not_connected":
                    continue  # queda pendiente hasta que se reconecte
                attempts = (move.qbo_attempts or 0) + 1
                vals = {
                    "qbo_state": "error",
                    "qbo_error": str(e),
                    "qbo_attempts": attempts,
                    "qbo_next_try": now + timedelta(minutes=min(5 * 2 ** (attempts - 1), BACKOFF_MAX_MIN)),
                }
                _logger.info("QBO push of invoice %s failed (%s): %s", move.name, e.code, e)
            else:
                if vals is None:
                    continue
                vals.update(qbo_attempts=0, qbo_next_try=False, qbo_synced_at=now)
            move.sudo().write(vals)
            if commit:
                self.env.cr.commit()

    @api.model
    def _qbo_cron_push(self):
        now = fields.Datetime.now()
        moves = self.sudo().search([
            ("qbo_state", "in", ("pending", "error")),
            ("state", "!=", "draft"),
            "|", ("qbo_next_try", "=", False), ("qbo_next_try", "<=", now),
        ], order="id", limit=CRON_BATCH)
        moves._qbo_process(commit=True)


def _qbo_after_commit(dbname, move_id):
    """Intento inmediato tras emitir/anular, ya fuera de la transaccion del
    usuario: si QBO tarda o falla, la factura ya esta emitida y la tarea
    programada lo reintenta."""
    try:
        with Registry(dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env["account.move"].browse(move_id).exists()._qbo_process()
    except Exception:  # nunca romper la respuesta al usuario
        _logger.exception("QBO immediate push of move %s failed", move_id)


class IndigoBillingQbo(models.AbstractModel):
    _inherit = "indigo.billing"

    def _qbo_queue(self, move_id):
        client = self.env["indigo.qbo.client"].sudo()
        if not (client.is_configured() and client.is_connected()):
            return
        move = self.env["account.move"].sudo().browse(int(move_id))
        move.write({"qbo_state": "pending", "qbo_attempts": 0, "qbo_next_try": False, "qbo_error": False})
        if not client._inline():
            self.env.cr.postcommit.add(partial(_qbo_after_commit, self.env.cr.dbname, move.id))

    @api.model
    def indigo_billing_post(self, move_id):
        super().indigo_billing_post(move_id)
        self._qbo_queue(move_id)
        return self.indigo_billing_detail(int(move_id))

    @api.model
    def indigo_billing_void(self, move_id, reason=None):
        super().indigo_billing_void(move_id, reason)
        self._qbo_queue(move_id)
        return self.indigo_billing_detail(int(move_id))

    def _row(self, m):
        row = super()._row(m)
        row.update({
            "qbo_state": m.qbo_state or "none",
            "qbo_error": m.qbo_error or False,
            "qbo_total": m.qbo_total if m.qbo_id else False,
        })
        return row


class IndigoQboInvoices(models.AbstractModel):
    _inherit = "indigo.qbo"

    @api.model
    def qbo_retry(self, move_id):
        self._assert_office()
        move = self.env["account.move"].sudo().browse(int(move_id)).exists()
        if not move or move.move_type != "out_invoice":
            raise QboError("api", _("Invoice not found."))
        if move.qbo_state in ("none", "synced", "linked", "voided") and move.state == "posted":
            move.write({"qbo_state": "pending"})
        move._qbo_process()
        return {"qbo_state": move.qbo_state, "qbo_error": move.qbo_error or False}

    @api.model
    def qbo_status(self):
        st = super().qbo_status()
        Move = self.env["account.move"].sudo()
        dom = [("move_type", "=", "out_invoice")]
        last = Move.search(dom + [("qbo_synced_at", "!=", False)], order="qbo_synced_at desc", limit=1)
        st.update({
            "pending": Move.search_count(dom + [("qbo_state", "=", "pending")]),
            "errors": Move.search_count(dom + [("qbo_state", "=", "error")]),
            "mismatches": Move.search_count(dom + [("qbo_state", "=", "mismatch")]),
            "last_push_at": fields.Datetime.to_string(last.qbo_synced_at) if last else False,
        })
        return st
