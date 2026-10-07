# -*- coding: utf-8 -*-
"""Cliente de QuickBooks Online: tokens, renovacion y errores.

Ninguna prueba llama a Intuit: `requests` se simula.
"""
import json
import os
import time
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from odoo.addons.indigo_quickbooks.models.qbo_client import QboError

REQ = "odoo.addons.indigo_quickbooks.models.qbo_client.requests"
ENV = {
    "QBO_CLIENT_ID": "test-client",
    "QBO_CLIENT_SECRET": "test-secret",
    "QBO_ENVIRONMENT": "sandbox",
    "QBO_REDIRECT_URI": "https://example.test/indigo/qbo/callback",
}


class FakeResponse:
    def __init__(self, status=200, body=None, headers=None):
        self.status_code = status
        self._body = body if body is not None else {}
        self.text = json.dumps(self._body) if not isinstance(self._body, str) else self._body
        self.headers = headers or {}

    def json(self):
        return self._body if not isinstance(self._body, str) else json.loads(self._body)


def token_body(access="AT", refresh="RT"):
    return {"access_token": access, "refresh_token": refresh, "expires_in": 3600,
            "x_refresh_token_expires_in": 8726400, "token_type": "bearer"}


class _QboCase(TransactionCase):
    def setUp(self):
        super().setUp()
        patcher = patch.dict(os.environ, ENV)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = self.env["indigo.qbo.client"]
        # Los parametros se cachean entre pruebas: cada una empieza desconectada.
        self.client.clear_tokens()

    def connect(self, expires_in=3600):
        self.client.save_tokens(token_body(), realm_id="123")
        if expires_in != 3600:
            self.client._set_params({"access_expires_at": int(time.time()) + expires_in})

    def param(self, key):
        return self.env["ir.config_parameter"].sudo().get_param("indigo_qbo." + key)


@tagged("indigo", "post_install", "-at_install")
class TestQboClient(_QboCase):
    def test_missing_configuration(self):
        with patch.dict(os.environ, {"QBO_CLIENT_SECRET": ""}):
            with self.assertRaises(QboError) as ctx:
                self.client._config()
        self.assertEqual(ctx.exception.code, "not_configured")

    def test_not_connected(self):
        with self.assertRaises(QboError) as ctx:
            self.client.get("companyinfo/123")
        self.assertEqual(ctx.exception.code, "not_connected")

    def test_valid_token_is_used_without_renewing(self):
        self.connect()
        with patch(REQ + ".get", return_value=FakeResponse(200, {"ok": 1})) as get, \
                patch(REQ + ".post") as post:
            self.assertEqual(self.client.get("companyinfo/123"), {"ok": 1})
        post.assert_not_called()
        args, kwargs = get.call_args
        self.assertIn("sandbox-quickbooks.api.intuit.com/v3/company/123/companyinfo/123", args[0])
        self.assertEqual(kwargs["params"]["minorversion"], "75")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer AT")

    def test_expired_token_is_renewed_and_new_refresh_token_kept(self):
        self.connect(expires_in=-10)
        with patch(REQ + ".post", return_value=FakeResponse(200, token_body("AT2", "RT2"))) as post, \
                patch(REQ + ".get", return_value=FakeResponse(200, {"ok": 1})):
            self.client.get("companyinfo/123")
        self.assertEqual(post.call_args.kwargs["data"]["grant_type"], "refresh_token")
        self.assertEqual(post.call_args.kwargs["data"]["refresh_token"], "RT")
        self.assertEqual(self.param("access_token"), "AT2")
        self.assertEqual(self.param("refresh_token"), "RT2")

    def test_401_renews_once_and_retries(self):
        self.connect()
        responses = [FakeResponse(401, "unauthorized"), FakeResponse(200, {"ok": 1})]
        with patch(REQ + ".get", side_effect=responses) as get, \
                patch(REQ + ".post", return_value=FakeResponse(200, token_body("AT2", "RT2"))) as post:
            self.assertEqual(self.client.get("companyinfo/123"), {"ok": 1})
        self.assertEqual(get.call_count, 2)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(get.call_args.kwargs["headers"]["Authorization"], "Bearer AT2")

    def test_invalid_grant_disconnects(self):
        self.connect(expires_in=-10)
        # Sin assertRaises: Odoo deshace lo que pasa dentro de el, y aqui hay que
        # ver que la desconexion queda hecha (en produccion va en su propia
        # transaccion y sobrevive al error).
        code = None
        with patch(REQ + ".post", return_value=FakeResponse(400, {"error": "invalid_grant"})):
            try:
                self.client.get("companyinfo/123")
            except QboError as e:
                code = e.code
        self.assertEqual(code, "auth")
        self.assertFalse(self.client.is_connected())

    def test_rate_limit(self):
        self.connect()
        with patch(REQ + ".get", return_value=FakeResponse(429, "too many")):
            with self.assertRaises(QboError) as ctx:
                self.client.get("companyinfo/123")
        self.assertEqual(ctx.exception.code, "rate_limit")

    def test_api_error_carries_intuit_message_and_tid(self):
        self.connect()
        fault = {"Fault": {"Error": [{"Message": "Duplicate Document Number Error", "Detail": "Duplicate DocNumber 1366"}]}}
        with patch(REQ + ".post", return_value=FakeResponse(400, fault, {"intuit_tid": "tid-42"})):
            with self.assertRaises(QboError) as ctx:
                self.client.post("invoice", {"DocNumber": "1366"})
        self.assertEqual(ctx.exception.code, "api")
        self.assertIn("Duplicate DocNumber 1366", str(ctx.exception))
        self.assertIn("tid-42", str(ctx.exception))

    def test_network_error(self):
        self.connect()
        import requests as real_requests
        with patch(REQ + ".get", side_effect=real_requests.ConnectionError("down")):
            with self.assertRaises(QboError) as ctx:
                self.client.get("companyinfo/123")
        self.assertEqual(ctx.exception.code, "network")

    def test_query_returns_the_entity_list(self):
        self.connect()
        body = {"QueryResponse": {"Invoice": [{"Id": "1", "DocNumber": "1366"}]}}
        with patch(REQ + ".get", return_value=FakeResponse(200, body)) as get:
            rows = self.client.query("SELECT * FROM Invoice WHERE DocNumber = '1366'", "Invoice")
        self.assertEqual(rows, [{"Id": "1", "DocNumber": "1366"}])
        self.assertEqual(get.call_args.kwargs["params"]["query"], "SELECT * FROM Invoice WHERE DocNumber = '1366'")
