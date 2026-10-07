# -*- coding: utf-8 -*-
"""Lo ya emitido antes de conectar QuickBooks (backfill).

Las facturas emitidas en Indigo antes de conectar no estan enlazadas. Muchas ya
existen en QBO porque la oficina las copiaba a mano con el mismo numero. Primero
un informe de solo lectura (que pasara con cada una) y despues, con el OK de un
gerente, se aplican: van a la cola de envio, que ya sabe enlazar las que
existen (igual -> enlazada, distinta -> no coincide) y crear las que no.
Nunca se tocan las que ya tienen qbo_id.

Al enlazar una que ya existia, sus cobros en QBO se traen tambien: el CDC solo
ve lo que cambia desde que se conecto, y esas facturas suelen estar cobradas.
"""
import logging

from odoo import _, api, models

from .qbo_client import QboError
from .qbo_invoice import _same
from .qbo_mapping import _esc
from .qbo_payment import qbo_fetch_payment

_logger = logging.getLogger(__name__)

QUERY_CHUNK = 30


class AccountMoveQboBackfill(models.Model):
    _inherit = "account.move"

    def _qbo_backfill_candidates(self):
        return self.sudo().search([
            ("move_type", "=", "out_invoice"), ("state", "=", "posted"),
            ("qbo_id", "=", False), ("qbo_state", "in", [False, "none"]),
        ], order="name")

    def _qbo_pull_payments(self, client):
        """Trae los cobros que QBO ya tiene en esta factura (recien enlazada)."""
        self.ensure_one()
        inv = client.get("invoice/%s" % self.qbo_id).get("Invoice") or {}
        pids = [str(t["TxnId"]) for t in inv.get("LinkedTxn") or [] if t.get("TxnType") == "Payment" and t.get("TxnId")]
        Qbo = self.env["indigo.qbo"].sudo()
        for pid in dict.fromkeys(pids):
            Qbo._qbo_apply_payment(pid, qbo_fetch_payment(client, pid))

    def _qbo_after_push(self, client, was_linked):
        super()._qbo_after_push(client, was_linked)
        if not was_linked and self.qbo_id and self.qbo_origin == "manual":
            self._qbo_pull_payments(client)


class IndigoQboBackfill(models.AbstractModel):
    _inherit = "indigo.qbo"

    @api.model
    def qbo_backfill_report(self):
        """Solo lectura: por cada emitida sin enlazar, lo que hay en QBO con su
        numero. outcome: same | different | other_customer | missing."""
        self._assert_office()
        client = self._client()
        client.realm_id()
        moves = self.env["account.move"]._qbo_backfill_candidates()
        found = {}
        names = moves.mapped("name")
        for i in range(0, len(names), QUERY_CHUNK):
            chunk = names[i:i + QUERY_CHUNK]
            sql = "SELECT * FROM Invoice WHERE DocNumber IN (%s) MAXRESULTS 1000" % ", ".join(
                "'%s'" % _esc(n) for n in chunk)
            for inv in client.query(sql, "Invoice"):
                found.setdefault(inv.get("DocNumber"), inv)
        rows = []
        for m in moves:
            inv = found.get(m.name)
            row = {
                "id": m.id, "name": m.name, "dealer": m.partner_id.name or "",
                "invoice_date": m.invoice_date and str(m.invoice_date) or False,
                "total": m.amount_total, "residual": m.amount_residual,
                "qbo_total": False, "qbo_balance": False, "qbo_customer": False, "problem": False,
            }
            if inv:
                customer = inv.get("CustomerRef") or {}
                row.update(qbo_total=inv.get("TotalAmt") or 0.0, qbo_balance=inv.get("Balance") or 0.0,
                           qbo_customer=customer.get("name") or customer.get("value") or False)
                if m.partner_id.qbo_customer_id and customer.get("value") and customer["value"] != m.partner_id.qbo_customer_id:
                    row["outcome"] = "other_customer"
                elif _same(row["qbo_total"], m.amount_total):
                    row["outcome"] = "same"
                else:
                    row["outcome"] = "different"
            else:
                row["outcome"] = "missing"
                try:
                    m._qbo_payload()
                except QboError as e:
                    row["problem"] = str(e)
            rows.append(row)
        counts = {k: sum(1 for r in rows if r["outcome"] == k) for k in ("same", "different", "other_customer", "missing")}
        counts["blocked"] = sum(1 for r in rows if r["problem"])
        return {"rows": rows, "counts": counts}

    @api.model
    def qbo_backfill_apply(self, move_ids):
        """Gerencia: manda a la cola las elegidas (solo las que siguen sin
        enlazar). La tarea de envio las enlaza o las crea."""
        self._assert_manager()
        self._client().realm_id()
        ids = [int(i) for i in move_ids or [] if str(i).isdigit()]
        moves = self.env["account.move"]._qbo_backfill_candidates().filtered(lambda m: m.id in ids)
        if not moves:
            raise QboError("api", _("None of these invoices is waiting to go to QuickBooks."))
        moves.write({"qbo_state": "pending", "qbo_attempts": 0, "qbo_next_try": False,
                     "qbo_error": False, "qbo_local_change": False})
        for m in moves:
            m.message_post(body=_("Sent to QuickBooks by %s (invoices issued before connecting).") % self.env.user.name)
        cron = self.env.ref("indigo_quickbooks.cron_qbo_push_invoices", raise_if_not_found=False)
        if cron and not self._client()._inline():
            cron.sudo()._trigger()
        return {"queued": len(moves)}
