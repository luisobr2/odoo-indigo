# -*- coding: utf-8 -*-
import logging
import os

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


def _panel_url():
    return (os.environ.get("QBO_PANEL_URL")
            or request.env["ir.config_parameter"].sudo().get_param("indigo_qbo.panel_url")
            or "https://app.indigodecors.com").rstrip("/")


class IndigoQboController(http.Controller):

    @http.route("/indigo/qbo/callback", type="http", auth="public", methods=["GET"], csrf=False)
    def callback(self, code=None, state=None, realmId=None, error=None, **kw):
        """Vuelta de Intuit tras autorizar. Publica a proposito: quien conecta
        lo hace desde el panel y no tiene por que tener sesion en Odoo. La
        protege el `state` (ver indigo.qbo._qbo_take_state)."""
        result = request.env["indigo.qbo"].sudo()._qbo_finish_connect(code, state, realmId, error)
        return request.redirect("%s/settings?qbo=%s" % (_panel_url(), result), local=False)
