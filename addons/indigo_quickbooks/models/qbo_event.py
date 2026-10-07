# -*- coding: utf-8 -*-
"""Avisos de QuickBooks (webhook) y el respaldo CDC.

El webhook solo apunta el aviso y responde al momento (Intuit espera una
respuesta rapida); el trabajo lo hace la tarea programada, que ademas cada
15 minutos pregunta a QBO por los cobros cambiados (Change Data Capture) por
si algun aviso se perdio. Las dos vias acaban en indigo.qbo._qbo_apply_payment,
que es idempotente.
"""
import base64
import hashlib
import hmac
import logging
from datetime import timedelta

from odoo import _, api, fields, models

from .qbo_client import QboError
from .qbo_payment import qbo_fetch_payment

_logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
CDC_MAX_DAYS = 30
EVENT_BATCH = 50


def qbo_signature_ok(verifier, raw, signature):
    """intuit-signature = base64(HMAC-SHA256(cuerpo crudo, verifier token))."""
    if not verifier or not signature or raw is None:
        return False
    digest = hmac.new(verifier.encode(), raw, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(digest).decode(), signature.strip())


def qbo_parse_webhook(data, realm_id):
    """Los cobros que trae un aviso, como [(id, operacion, cuando)], solo de
    nuestra empresa. Acepta el formato clasico (eventNotifications) y el de
    CloudEvents (lista de eventos con type qbo.payment.<op>.v1)."""
    out = []
    realm = str(realm_id or "")
    if isinstance(data, dict):
        for note in data.get("eventNotifications") or []:
            if realm and str(note.get("realmId")) != realm:
                continue
            for ent in (note.get("dataChangeEvent") or {}).get("entities") or []:
                if ent.get("name") == "Payment" and ent.get("id"):
                    out.append((str(ent["id"]), ent.get("operation") or "", ent.get("lastUpdated") or ""))
    elif isinstance(data, list):
        for ev in data:
            if not isinstance(ev, dict):
                continue
            parts = str(ev.get("type") or "").split(".")
            if len(parts) < 3 or parts[0] != "qbo" or parts[1] != "payment":
                continue
            if realm and str(ev.get("intuitaccountid")) != realm:
                continue
            if ev.get("intuitentityid"):
                out.append((str(ev["intuitentityid"]), parts[2], ev.get("time") or ""))
    return out


class IndigoQboEvent(models.Model):
    _name = "indigo.qbo.event"
    _description = "QuickBooks notification"
    _order = "id"

    entity_id = fields.Char(required=True, index=True)
    operation = fields.Char()
    last_updated = fields.Char()
    state = fields.Selection([("pending", "Pending"), ("done", "Done"), ("error", "Error")],
                             default="pending", required=True, index=True)
    error = fields.Text()
    attempts = fields.Integer(default=0)

    @api.model
    def _qbo_receive(self, raw, signature, data):
        """Lo que hace el webhook, sin HTTP (probado aparte). Devuelve el
        codigo HTTP: 401 firma mala, 200 aceptado (aunque no traiga cobros)."""
        client = self.env["indigo.qbo.client"].sudo()
        try:
            verifier = client._config()["verifier"]
        except QboError:
            return 401
        if not qbo_signature_ok(verifier, raw, signature):
            _logger.warning("QBO webhook with a bad signature")
            return 401
        realm = client._param("realm_id")
        events = qbo_parse_webhook(data, realm)
        if events:
            self.sudo().create([{"entity_id": e[0], "operation": e[1], "last_updated": e[2]} for e in events])
            cron = self.env.ref("indigo_quickbooks.cron_qbo_payments", raise_if_not_found=False)
            if cron and not client._inline():
                cron.sudo()._trigger()
        return 200

    # ------------------------------------------------------------ tarea

    @api.model
    def _qbo_cron_payments(self, commit=True):
        client = self.env["indigo.qbo.client"].sudo()
        if not (client.is_configured() and client.is_connected()):
            return
        try:
            self._qbo_process_events(client, commit)
            self._qbo_cdc(client)
        except QboError as e:
            # Sin red, limite de peticiones o conexion caida: la proxima vez.
            _logger.warning("QBO payments sync stopped: %s", e)

    def _qbo_process_events(self, client, commit):
        Qbo = self.env["indigo.qbo"].sudo()
        pending = self.sudo().search([("state", "=", "pending")], limit=EVENT_BATCH)
        for pid in list(dict.fromkeys(pending.mapped("entity_id"))):
            events = pending.filtered(lambda e: e.entity_id == pid)
            try:
                with self.env.cr.savepoint():
                    Qbo._qbo_apply_payment(pid, qbo_fetch_payment(client, pid))
                    events.write({"state": "done", "error": False})
            except QboError as e:
                if e.code in ("rate_limit", "network", "not_connected", "auth"):
                    raise
                self._qbo_event_failed(events, e)
            except Exception as e:  # que un cobro raro no pare los demas
                _logger.exception("QBO payment %s crashed", pid)
                self._qbo_event_failed(events, e)
            if commit and not client._inline():
                self.env.cr.commit()

    def _qbo_event_failed(self, events, err):
        for ev in events:
            ev.write({"attempts": ev.attempts + 1, "error": str(err)[:500],
                      "state": "error" if ev.attempts + 1 >= MAX_ATTEMPTS else "pending"})

    def _qbo_cdc(self, client):
        """Cobros cambiados desde el cursor. El cursor se guarda en ESTA
        transaccion, con los cobros: si algo falla no avanza y la proxima vez
        se repite (aplicar es idempotente)."""
        icp = self.env["ir.config_parameter"].sudo()
        now = fields.Datetime.now()
        oldest = now - timedelta(days=CDC_MAX_DAYS)
        since = fields.Datetime.to_datetime(icp.get_param("indigo_qbo.cdc_cursor")
                                            or icp.get_param("indigo_qbo.sync_from") or None) or now - timedelta(days=1)
        since = max(since, oldest)
        data = client.get("cdc", {"entities": "Payment", "changedSince": since.strftime("%Y-%m-%dT%H:%M:%S-00:00")})
        Qbo = self.env["indigo.qbo"].sudo()
        failed = False
        for block in data.get("CDCResponse") or []:
            for qr in block.get("QueryResponse") or []:
                for pay in qr.get("Payment") or []:
                    try:
                        with self.env.cr.savepoint():
                            Qbo._qbo_apply_payment(pay["Id"], pay)
                    except Exception:
                        failed = True
                        _logger.exception("QBO payment %s from CDC failed", pay.get("Id"))
        if not failed:
            # Un minuto de solape: lo que cambio mientras se consultaba entra la proxima vez.
            icp.set_param("indigo_qbo.cdc_cursor", fields.Datetime.to_string(now - timedelta(minutes=1)))
