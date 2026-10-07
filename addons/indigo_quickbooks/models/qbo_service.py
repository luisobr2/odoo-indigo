# -*- coding: utf-8 -*-
"""Servicio de QuickBooks para el panel (`indigo.qbo`): conexion y estado.

Como `indigo.billing`, es la unica puerta que usa el panel: oficina y gerencia
ven el estado; solo gerencia conecta y desconecta.

Conectar sin pasar por el backend de Odoo: el panel pide `qbo_authorize_url()`
con la sesion del gerente, abre la URL de Intuit, e Intuit vuelve a
`/indigo/qbo/callback` (publica). Lo que protege esa vuelta es el `state`:
aleatorio, de un solo uso, con 10 minutos de vida y ligado a quien lo pidio.
"""
import json
import logging
import secrets
import time
from urllib.parse import urlencode

from odoo import _, api, fields, models
from odoo.exceptions import AccessError

from .qbo_client import AUTHORIZE_URL, SCOPE, QboError

_logger = logging.getLogger(__name__)

STATE_TTL = 600


class IndigoQbo(models.AbstractModel):
    _name = "indigo.qbo"
    _description = "QuickBooks Online integration"

    # ------------------------------------------------------------ roles

    def _assert_office(self):
        u = self.env.user
        if not (u._is_admin() or u.has_group("indigo_decors.group_indigo_manager")
                or u.has_group("indigo_decors.group_indigo_office")):
            raise AccessError(_("Only the office or a manager can see QuickBooks."))

    def _is_manager(self):
        u = self.env.user
        return u._is_admin() or u.has_group("indigo_decors.group_indigo_manager")

    def _assert_manager(self):
        if not self._is_manager():
            raise AccessError(_("Only a manager can connect or disconnect QuickBooks."))

    def _client(self):
        return self.env["indigo.qbo.client"].sudo()

    def _icp(self):
        return self.env["ir.config_parameter"].sudo()

    # ------------------------------------------------------------ conectar

    @api.model
    def qbo_authorize_url(self):
        self._assert_manager()
        cfg = self._client()._config()
        state = secrets.token_urlsafe(32)
        states = self._qbo_states()
        states[state] = {"exp": int(time.time()) + STATE_TTL, "uid": self.env.uid}
        self._icp().set_param("indigo_qbo.oauth_states", json.dumps(states))
        return AUTHORIZE_URL + "?" + urlencode({
            "client_id": cfg["client_id"],
            "response_type": "code",
            "scope": SCOPE,
            "redirect_uri": cfg["redirect_uri"],
            "state": state,
        })

    def _qbo_states(self):
        """Los state pendientes que no han caducado (varios: dos pestanas o
        dos gerentes pueden estar conectando a la vez)."""
        try:
            states = json.loads(self._icp().get_param("indigo_qbo.oauth_states") or "{}")
        except ValueError:
            states = {}
        now = time.time()
        return {k: v for k, v in states.items() if isinstance(v, dict) and int(v.get("exp", 0)) > now}

    def _qbo_take_state(self, state):
        """El state si existe y no caduco; se borra SOLO ese (un uso). Una
        peticion con un state que no existe no toca los demas."""
        if not state:
            return None
        states = self._qbo_states()
        match = next((k for k in states if secrets.compare_digest(k, str(state))), None)
        if not match:
            return None
        stored = states.pop(match)
        self._icp().set_param("indigo_qbo.oauth_states", json.dumps(states))
        return stored

    def _qbo_reset_company(self, old_realm, new_realm):
        """Se conecto OTRA empresa de QuickBooks (p. ej. del sandbox a la real).
        Los ids de QBO son numeros pequenos por empresa: los de la anterior
        apuntarian a otras cosas en la nueva. Se borran las equivalencias y el
        enlace de las facturas, que vuelven a 'no esta en QuickBooks'."""
        _logger.warning("QBO company changed from realm %s to %s: resetting matches and invoice links",
                        old_realm, new_realm)
        self.env["res.partner"].sudo().with_context(active_test=False).search(
            [("qbo_customer_id", "!=", False)]).write({"qbo_customer_id": False, "qbo_customer_name": False})
        self.env["product.product"].sudo().with_context(active_test=False).search(
            [("qbo_item_id", "!=", False)]).write({"qbo_item_id": False, "qbo_item_name": False})
        Move = self.env["account.move"].sudo()
        if "qbo_state" in Move._fields:
            Move.search([("qbo_state", "!=", "none")]).write({
                "qbo_id": False, "qbo_sync_token": False, "qbo_state": "none", "qbo_error": False,
                "qbo_origin": False, "qbo_total": 0.0, "qbo_attempts": 0, "qbo_next_try": False,
            })

    @api.model
    def _qbo_finish_connect(self, code, state, realm_id, error):
        """Vuelta de Intuit. Devuelve connected | denied | invalid_state | error."""
        stored = self._qbo_take_state(state)
        if not stored:
            _logger.warning("QBO callback with an unknown or expired state")
            return "invalid_state"
        if error:
            _logger.info("QBO connection not authorized: %s", error)
            return "denied"
        if not code or not realm_id:
            return "error"
        client = self._client()
        try:
            client.exchange_code(code, realm_id)
        except QboError as e:
            _logger.warning("QBO connect failed: %s", e)
            return "error"
        previous = self._icp().get_param("indigo_qbo.mapping_realm")
        if previous and previous != str(realm_id):
            self._qbo_reset_company(previous, realm_id)
        self._icp().set_param("indigo_qbo.mapping_realm", str(realm_id))
        if not self._icp().get_param("indigo_qbo.sync_from"):
            # Desde aqui las facturas van a QBO, aunque luego se desconecte un
            # rato: lo emitido mientras tanto queda pendiente, no se pierde.
            self._icp().set_param("indigo_qbo.sync_from", fields.Datetime.to_string(fields.Datetime.now()))
        try:
            info = client.get("companyinfo/%s" % realm_id).get("CompanyInfo") or {}
        except QboError as e:
            # Ya esta conectado: solo falta el nombre de la empresa.
            _logger.warning("QBO connected but CompanyInfo failed: %s", e)
            info = {}
        client._set_params({
            "company_name": info.get("CompanyName") or "",
            "connected_at": fields.Datetime.to_string(fields.Datetime.now()),
            "connected_by": stored.get("uid") or "",
        })
        _logger.info("QBO connected to realm %s (%s)", realm_id, info.get("CompanyName"))
        return "connected"

    @api.model
    def qbo_disconnect(self):
        self._assert_manager()
        self._client().revoke()
        self._client()._set_params({"connected_at": "", "connected_by": ""})
        return self.qbo_status()

    # ------------------------------------------------------------ estado

    @api.model
    def qbo_status(self):
        self._assert_office()
        client = self._client()
        configured = client.is_configured()
        connected = configured and client.is_connected()
        env_name = (client._setting("QBO_ENVIRONMENT") or "sandbox").lower()
        by = client._param("connected_by")
        user = self.env["res.users"].sudo().browse(int(by)).exists() if by and str(by).isdigit() else None
        return {
            "configured": configured,
            "connected": connected,
            "environment": env_name,
            "company_name": client._param("company_name") or False if connected else False,
            "realm_id": client._param("realm_id") or False if connected else False,
            "connected_at": client._param("connected_at") or False if connected else False,
            "connected_by": user.name if connected and user else False,
            "can_connect": bool(configured and self._is_manager()),
            # Estuvo conectado y ya no (token revocado/vencido): las facturas
            # nuevas quedan pendientes hasta reconectar.
            "needs_reconnect": bool(configured and not connected
                                    and self._icp().get_param("indigo_qbo.sync_from")),
        }
