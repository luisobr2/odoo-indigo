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
        self._icp().set_param("indigo_qbo.oauth_state", json.dumps({
            "state": state, "exp": int(time.time()) + STATE_TTL, "uid": self.env.uid,
        }))
        return AUTHORIZE_URL + "?" + urlencode({
            "client_id": cfg["client_id"],
            "response_type": "code",
            "scope": SCOPE,
            "redirect_uri": cfg["redirect_uri"],
            "state": state,
        })

    def _qbo_take_state(self, state):
        """El state guardado si coincide y no caduco; se borra siempre (un uso)."""
        raw = self._icp().get_param("indigo_qbo.oauth_state")
        self._icp().set_param("indigo_qbo.oauth_state", "")
        if not raw or not state:
            return None
        try:
            stored = json.loads(raw)
        except ValueError:
            return None
        if not secrets.compare_digest(str(stored.get("state", "")), str(state)):
            return None
        if int(stored.get("exp", 0)) < time.time():
            return None
        return stored

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
            info = client.get("companyinfo/%s" % realm_id).get("CompanyInfo") or {}
        except QboError as e:
            _logger.warning("QBO connect failed: %s", e)
            return "error"
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
        }
