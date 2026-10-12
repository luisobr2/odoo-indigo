# -*- coding: utf-8 -*-
"""Enviar las facturas de Indigo a QuickBooks.

Estados (`qbo_state`):
  none      no va a QBO (nunca conectado, o emitida antes de conectar)
  pending   por enviar (recien emitida, corregida o anulada)
  synced    creada/actualizada por Indigo en QBO, mismo total
  linked    ya estaba en QBO (metida a mano) con el mismo total: se enlazo
  mismatch  hay que mirarla: el total no coincide, el numero lo tiene otro
            cliente en QBO, o se cambio aqui una factura que en QBO se metio a
            mano (no se pisa trabajo manual)
  error     no se pudo (falta una equivalencia, QBO fallo...): se reintenta
  voided    anulada en QBO

Reglas:
  * Antes de crear se busca por numero (DocNumber) para no duplicar.
  * Lo que Indigo crea lleva en el memo "Indigo #<n>": asi, si la respuesta de
    QBO se perdio, al reintentar se reconoce como propia y no como manual.
  * Una factura metida a mano (`qbo_origin = manual`) nunca se sobrescribe.
  * Una factura se procesa de a una vez (fila bloqueada): emitir, la tarea
    programada y Reintentar no pueden crearla dos veces.
"""
import logging
from datetime import timedelta

from odoo import _, api, fields, models

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
# Donde se abre una factura en la web de QuickBooks.
QBO_WEB_HOSTS = {
    "sandbox": "https://app.sandbox.qbo.intuit.com",
    "production": "https://app.qbo.intuit.com",
}
BACKOFF_MAX_MIN = 360
CRON_BATCH = 20
RETRYABLE = ("pending", "error", "mismatch")


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
    # Se emitio/corrigio/anulo aqui despues de enlazarla: QBO no lo sabe.
    qbo_local_change = fields.Boolean(copy=False)

    # ------------------------------------------------------------ cuerpo

    def _qbo_marker(self):
        return "Indigo #%s" % self.name

    def _qbo_is_ours(self, inv):
        return (inv.get("PrivateNote") or "").startswith(self._qbo_marker())

    def _qbo_payload(self):
        """Lo que Indigo pone en la factura de QBO (y lo unico que actualiza)."""
        self.ensure_one()
        partner = self.partner_id
        if self.currency_id != self.company_id.currency_id:
            raise QboError("mapping", _("Only invoices in %s go to QuickBooks.") % self.company_id.currency_id.name)
        if not partner.qbo_customer_id:
            raise QboError("mapping", _(
                "%s isn't matched with a QuickBooks customer yet (Billing → QuickBooks)."
            ) % partner.name)
        lines = []
        for ln in self.invoice_line_ids.filtered(lambda l: l.display_type == "product"):
            if ln.discount:
                raise QboError("mapping", _("Lines with a discount can't go to QuickBooks yet: put the final price instead."))
            item = ln.product_id.qbo_item_id
            if not item:
                raise QboError("mapping", _(
                    "%s isn't matched with a QuickBooks product yet (Billing → QuickBooks)."
                ) % (ln.product_id.name or ln.name))
            lines.append({
                "DetailType": "SalesItemLineDetail",
                # El mismo redondeo que Odoo, para que los totales cuadren al centavo.
                "Amount": ln.price_subtotal,
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
        note = self._qbo_marker() + (" · PO %s" % ", ".join(pos) if pos else "")
        body = {
            "DocNumber": self.name,
            "CustomerRef": {"value": partner.qbo_customer_id},
            "Line": lines,
            "PrivateNote": note[:4000],
            # El impuesto lo pone Indigo (su 7% sobre las puertas), no el
            # calculo de QuickBooks: con el total de impuesto fijado los dos
            # totales coinciden al centavo (decision del 12-oct-2026). En una
            # empresa sin calculo automatico hace falta ademas el codigo del
            # impuesto (el de Florida), que se elige en Billing -> QuickBooks.
            "TxnTaxDetail": self._qbo_tax_detail(),
        }
        if self.invoice_date:
            body["TxnDate"] = fields.Date.to_string(self.invoice_date)
        if self.invoice_date_due:
            body["DueDate"] = fields.Date.to_string(self.invoice_date_due)
        return body

    def _qbo_tax_detail(self):
        detail = {"TotalTax": round(self.amount_tax, 2)}
        code = self.env["ir.config_parameter"].sudo().get_param("indigo_qbo.tax_code_id")
        if code and self.amount_tax:
            detail["TxnTaxCodeRef"] = {"value": code}
        return detail

    # ------------------------------------------------------------ enviar

    def _qbo_result(self, inv, origin):
        total = inv.get("TotalAmt") or 0.0
        vals = {
            "qbo_id": inv.get("Id"),
            "qbo_sync_token": inv.get("SyncToken"),
            "qbo_origin": origin,
            "qbo_total": total,
        }
        if origin == "manual" and self.qbo_local_change:
            # Cambiada aqui y metida a mano en QBO: aunque el total coincida,
            # QBO puede tener otra descripcion o PO. Que la oficina la actualice
            # alli y pulse Reintentar.
            vals.update(qbo_state="mismatch", qbo_error=_(
                "Changed here, but in QuickBooks it was entered by hand: update it there too, then press Retry."))
        elif _same(total, self.amount_total):
            vals.update(qbo_state="synced" if origin == "indigo" else "linked",
                        qbo_error=False, qbo_local_change=False)
        elif origin == "manual":
            vals.update(qbo_state="mismatch", qbo_error=_(
                "QuickBooks already has invoice #%(n)s (entered by hand) for %(qbo)s; here it's %(here)s."
            ) % {"n": self.name, "qbo": _money(total), "here": _money(self.amount_total)})
        else:
            vals.update(qbo_state="mismatch", qbo_error=_(
                "QuickBooks calculated %(qbo)s and Indigo %(here)s. Check the sales tax."
            ) % {"qbo": _money(total), "here": _money(self.amount_total)})
        return vals

    def _qbo_find(self, client):
        """La factura de QBO con este numero, si es de este dealer.
        Devuelve (factura | None, problema | None)."""
        found = client.query("SELECT * FROM Invoice WHERE DocNumber = '%s'" % _esc(self.name), "Invoice")
        if not found:
            return None, None
        inv = found[0]
        customer = (inv.get("CustomerRef") or {}).get("value")
        if self.partner_id.qbo_customer_id and customer and customer != self.partner_id.qbo_customer_id:
            return None, _(
                "QuickBooks already uses number #%(n)s for another customer (%(c)s). "
                "Check the numbering before sending it."
            ) % {"n": self.name, "c": (inv.get("CustomerRef") or {}).get("name") or customer}
        return inv, None

    def _qbo_update(self, client, current):
        body = self._qbo_payload()
        # Sparse: solo lo que Indigo pone; lo que la oficina agrego en QBO
        # (correo, terminos, clases, notas al cliente...) se respeta.
        body.update({"Id": current.get("Id") or self.qbo_id, "SyncToken": current.get("SyncToken"), "sparse": True})
        inv = client.post("invoice", body).get("Invoice") or {}
        return self._qbo_result(inv, "indigo")

    def _qbo_void(self, client, inv):
        res = client.post("invoice", {"Id": inv.get("Id"), "SyncToken": inv.get("SyncToken")},
                          params={"operation": "void"}).get("Invoice") or {}
        return {"qbo_id": inv.get("Id"), "qbo_state": "voided", "qbo_error": False,
                "qbo_sync_token": res.get("SyncToken"), "qbo_local_change": False}

    def _qbo_push(self):
        """Lleva esta factura a QBO. Devuelve los valores qbo_* a guardar
        (o None si no hay nada que hacer todavia)."""
        self.ensure_one()
        client = self.env["indigo.qbo.client"].sudo()
        if self.state == "draft":
            return None  # p. ej. en correccion: se envia al reemitir
        # ---- anulada
        if self.state == "cancel":
            if self.qbo_id:
                current = client.get("invoice/%s" % self.qbo_id).get("Invoice") or {}
                ours = self.qbo_origin == "indigo" or self._qbo_is_ours(current)
            else:
                current, problem = self._qbo_find(client)
                if problem:
                    return {"qbo_state": "mismatch", "qbo_error": problem}
                if not current:
                    return {"qbo_state": "none", "qbo_error": False}
                ours = self._qbo_is_ours(current)
            if ours:
                return self._qbo_void(client, current)
            return {"qbo_id": current.get("Id"), "qbo_origin": "manual", "qbo_state": "mismatch",
                    "qbo_error": _("Voided here, but in QuickBooks it was entered by hand: void it there too.")}
        # ---- emitida, sin enlazar todavia
        if not self.qbo_id:
            current, problem = self._qbo_find(client)
            if problem:
                return {"qbo_state": "mismatch", "qbo_error": problem}
            if current:
                if self._qbo_is_ours(current):
                    # Ya la habiamos creado (la respuesta se perdio): actualizar.
                    return self._qbo_update(client, current)
                return self._qbo_result(current, "manual")
            body = self._qbo_payload()
            body["EmailStatus"] = "NotSet"  # el correo al dealer lo manda Indigo
            # requestid: si este mismo POST se repite, QBO no crea otra.
            inv = client.post("invoice", body,
                              params={"requestid": "indigo-inv-%s-%s" % (self.id, self.name)}).get("Invoice") or {}
            return self._qbo_result(inv, "indigo")
        # ---- emitida y enlazada
        current = client.get("invoice/%s" % self.qbo_id).get("Invoice") or {}
        if self.qbo_origin == "manual" and not self._qbo_is_ours(current):
            # No se toca: se vuelve a comparar (por si ya lo arreglaron en QBO).
            return self._qbo_result(current, "manual")
        return self._qbo_update(client, current)

    def _qbo_lock(self):
        """Toma la fila de esta factura; False si otro proceso la esta enviando."""
        self.env.cr.execute("SELECT id FROM account_move WHERE id = %s FOR UPDATE SKIP LOCKED", (self.id,))
        return bool(self.env.cr.fetchone())

    def _qbo_process(self, commit=False):
        client = self.env["indigo.qbo.client"].sudo()
        if not (client.is_configured() and client.is_connected()):
            return
        for move in self:
            now = fields.Datetime.now()
            try:
                with self.env.cr.savepoint():
                    if not move._qbo_lock():
                        continue
                    move.invalidate_recordset()
                    was_linked = bool(move.qbo_id)
                    vals = move._qbo_push()
                    if vals is not None:
                        vals.update(qbo_attempts=0, qbo_next_try=False, qbo_synced_at=now)
                        move.sudo().write(vals)
                        move._qbo_after_push(client, was_linked)
            except QboError as e:
                if e.code == "not_connected":
                    continue  # queda pendiente hasta que se reconecte
                move._qbo_failed(e, now)
            except Exception as e:  # nada de una factura puede frenar la cola
                _logger.exception("QBO push of invoice %s crashed", move.name)
                move._qbo_failed(e, now)
            if commit:
                self.env.cr.commit()

    def _qbo_after_push(self, client, was_linked):
        """Despues de guardar el resultado (en el mismo savepoint): si falla,
        se deshace tambien el enlace y se reintenta."""

    def _qbo_failed(self, error, now):
        attempts = (self.qbo_attempts or 0) + 1
        self.sudo().write({
            "qbo_state": "error",
            "qbo_error": str(error) or error.__class__.__name__,
            "qbo_attempts": attempts,
            "qbo_next_try": now + timedelta(minutes=min(5 * 2 ** (attempts - 1), BACKOFF_MAX_MIN)),
        })
        _logger.info("QBO push of invoice %s failed: %s", self.name, error)

    @api.model
    def _qbo_cron_push(self):
        now = fields.Datetime.now()
        moves = self.sudo().search([
            ("move_type", "=", "out_invoice"),
            ("qbo_state", "in", ("pending", "error")),
            ("state", "!=", "draft"),
            "|", ("qbo_next_try", "=", False), ("qbo_next_try", "<=", now),
        ], order="qbo_next_try asc, id asc", limit=CRON_BATCH)
        moves._qbo_process(commit=True)
        if len(moves) == CRON_BATCH:
            # Hay mas (p. ej. lo ya emitido): seguir sin esperar 5 minutos.
            self.env.ref("indigo_quickbooks.cron_qbo_push_invoices")._trigger()


class IndigoBillingQbo(models.AbstractModel):
    _inherit = "indigo.billing"

    def _qbo_queue(self, move_id):
        """Marca la factura para QBO y despierta la tarea programada (que la
        envia en segundos, fuera de la peticion del usuario). Si QBO estuvo
        conectado alguna vez, aunque ahora no lo este, queda pendiente: se
        enviara al reconectar."""
        client = self.env["indigo.qbo.client"].sudo()
        if not client.is_configured():
            return
        if not (client.is_connected() or self.env["ir.config_parameter"].sudo().get_param("indigo_qbo.sync_from")):
            return
        move = self.env["account.move"].sudo().browse(int(move_id))
        move.write({"qbo_state": "pending", "qbo_attempts": 0, "qbo_next_try": False, "qbo_error": False,
                    "qbo_local_change": bool(move.qbo_id)})
        cron = self.env.ref("indigo_quickbooks.cron_qbo_push_invoices", raise_if_not_found=False)
        if cron and not client._inline():
            cron.sudo()._trigger()

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

    def _list_domain(self, f):
        """qbo: 'problems' = pendientes, con error o que no coinciden;
        'missing' = emitidas que no estan en QuickBooks (de antes de conectar)."""
        domain = super()._list_domain(f)
        qbo = f.get("qbo")
        if qbo == "problems":
            domain.append(("qbo_state", "in", list(RETRYABLE)))
        elif qbo == "missing":
            domain += [("state", "=", "posted"), ("qbo_state", "in", [False, "none"])]
        return domain

    def _qbo_web_url(self, m):
        if not m.qbo_id:
            return False
        try:
            env_name = self.env["indigo.qbo.client"].sudo()._config()["environment"]
        except QboError:
            return False
        host = QBO_WEB_HOSTS.get(env_name)
        return "%s/app/invoice?txnId=%s" % (host, m.qbo_id) if host else False

    def _row(self, m):
        row = super()._row(m)
        row.update({
            "qbo_state": m.qbo_state or "none",
            "qbo_error": m.qbo_error or False,
            "qbo_total": m.qbo_total if m.qbo_id else False,
            "qbo_origin": m.qbo_origin or False,
            "qbo_synced_at": fields.Datetime.to_string(m.qbo_synced_at) if m.qbo_synced_at else False,
            "qbo_url": self._qbo_web_url(m),
        })
        return row


class IndigoQboInvoices(models.AbstractModel):
    _inherit = "indigo.qbo"

    @api.model
    def qbo_retry(self, move_id):
        """Reintentar ahora una factura pendiente, con error o que no coincide.
        Las emitidas antes de conectar ('none') no: esas van por el enlace de
        lo ya emitido, con su informe previo."""
        self._assert_office()
        self._client().realm_id()  # sin conexion: lo dice en vez de no hacer nada
        move = self.env["account.move"].sudo().browse(int(move_id)).exists()
        if not move or move.move_type != "out_invoice":
            raise QboError("api", _("Invoice not found."))
        if move.qbo_state not in RETRYABLE:
            raise QboError("api", _("This invoice has nothing to send to QuickBooks."))
        if move.qbo_origin == "manual":
            # Reintentar = "ya la actualice en QuickBooks": volver a comparar.
            move.write({"qbo_local_change": False})
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
