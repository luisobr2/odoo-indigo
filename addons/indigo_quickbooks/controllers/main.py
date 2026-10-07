# -*- coding: utf-8 -*-
import json
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

    @http.route("/indigo/qbo/webhook", type="http", auth="none", methods=["POST"], csrf=False)
    def webhook(self, **kw):
        """Avisos de Intuit. Sin sesion: lo protege la firma intuit-signature
        (HMAC con el verifier token). Solo se apunta el aviso; el cobro lo
        aplica la tarea programada."""
        raw = request.httprequest.get_data()
        try:
            data = json.loads(raw or b"null")
        except ValueError:
            data = None
        status = request.env["indigo.qbo.event"].sudo()._qbo_receive(
            raw, request.httprequest.headers.get("intuit-signature"), data)
        return request.make_response("", status=status)
