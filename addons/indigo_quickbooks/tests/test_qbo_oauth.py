# -*- coding: utf-8 -*-
"""Conectar y desconectar QuickBooks (OAuth 2.0, authorization_code)."""
import json
import time
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from odoo.exceptions import AccessError
from odoo.tests import tagged

from .test_qbo_client import REQ, FakeResponse, _QboCase, token_body


@tagged("indigo", "post_install", "-at_install")
class TestQboOauth(_QboCase):
    def setUp(self):
        super().setUp()
        Users = self.env["res.users"].with_context(no_reset_password=True)
        base = self.env.ref("base.group_user")
        self.manager = Users.create({
            "name": "QBO Manager", "login": "qbo_manager@test.local",
            "groups_id": [(6, 0, [base.id, self.env.ref("indigo_decors.group_indigo_manager").id])],
        })
        self.office = Users.create({
            "name": "QBO Office", "login": "qbo_office@test.local",
            "groups_id": [(6, 0, [base.id, self.env.ref("indigo_decors.group_indigo_office").id])],
        })
        self.Qbo = self.env["indigo.qbo"]

    def _authorize(self):
        url = self.Qbo.with_user(self.manager).qbo_authorize_url()
        return parse_qs(urlparse(url).query), url

    def _company_response(self):
        return FakeResponse(200, {"CompanyInfo": {"CompanyName": "Sandbox Co", "Id": "1"}})

    def test_manager_gets_the_intuit_url(self):
        qs, url = self._authorize()
        self.assertTrue(url.startswith("https://appcenter.intuit.com/connect/oauth2?"))
        self.assertEqual(qs["client_id"], ["test-client"])
        self.assertEqual(qs["scope"], ["com.intuit.quickbooks.accounting"])
        self.assertEqual(qs["redirect_uri"], ["https://example.test/indigo/qbo/callback"])
        self.assertEqual(qs["response_type"], ["code"])
        self.assertTrue(len(qs["state"][0]) >= 32)

    def test_office_cannot_connect_but_sees_the_status(self):
        with self.assertRaises(AccessError):
            self.Qbo.with_user(self.office).qbo_authorize_url()
        status = self.Qbo.with_user(self.office).qbo_status()
        self.assertTrue(status["configured"])
        self.assertFalse(status["connected"])
        self.assertFalse(status["can_connect"])

    def test_wrong_state_is_refused_and_nothing_saved(self):
        self._authorize()
        with patch(REQ + ".post") as post:
            result = self.Qbo.sudo()._qbo_finish_connect("CODE", "not-the-state", "999", None)
        self.assertEqual(result, "invalid_state")
        post.assert_not_called()
        self.assertFalse(self.client.is_connected())

    def test_expired_state_is_refused(self):
        qs, _url = self._authorize()
        states = json.loads(self.param("oauth_states"))
        states[qs["state"][0]]["exp"] = int(time.time()) - 1
        self.env["ir.config_parameter"].sudo().set_param("indigo_qbo.oauth_states", json.dumps(states))
        with patch(REQ + ".post") as post:
            result = self.Qbo.sudo()._qbo_finish_connect("CODE", qs["state"][0], "999", None)
        self.assertEqual(result, "invalid_state")
        post.assert_not_called()

    def test_callback_connects_and_the_state_is_single_use(self):
        qs, _url = self._authorize()
        state = qs["state"][0]
        with patch(REQ + ".post", return_value=FakeResponse(200, token_body())) as post, \
                patch(REQ + ".get", return_value=self._company_response()):
            result = self.Qbo.sudo()._qbo_finish_connect("CODE", state, "999", None)
        self.assertEqual(result, "connected")
        self.assertEqual(post.call_args.kwargs["data"]["grant_type"], "authorization_code")
        self.assertEqual(post.call_args.kwargs["data"]["code"], "CODE")
        self.assertEqual(self.param("realm_id"), "999")
        self.assertEqual(self.param("company_name"), "Sandbox Co")
        self.assertEqual(self.param("connected_by"), str(self.manager.id))
        status = self.Qbo.with_user(self.manager).qbo_status()
        self.assertTrue(status["connected"])
        self.assertEqual(status["company_name"], "Sandbox Co")
        self.assertEqual(status["environment"], "sandbox")
        # el mismo state no sirve dos veces
        with patch(REQ + ".post") as post2:
            self.assertEqual(self.Qbo.sudo()._qbo_finish_connect("CODE", state, "999", None), "invalid_state")
        post2.assert_not_called()

    def test_user_denies_access(self):
        qs, _url = self._authorize()
        result = self.Qbo.sudo()._qbo_finish_connect(None, qs["state"][0], None, "access_denied")
        self.assertEqual(result, "denied")
        self.assertFalse(self.client.is_connected())

    def test_disconnect_revokes_and_clears(self):
        self.connect()
        with patch(REQ + ".post", return_value=FakeResponse(200, {})) as post:
            self.Qbo.with_user(self.manager).qbo_disconnect()
        self.assertIn("revoke", post.call_args.args[0])
        self.assertFalse(self.client.is_connected())
        with self.assertRaises(AccessError):
            self.Qbo.with_user(self.office).qbo_disconnect()

    def test_status_when_not_configured(self):
        with patch.dict("os.environ", {"QBO_CLIENT_ID": ""}):
            status = self.Qbo.with_user(self.manager).qbo_status()
        self.assertFalse(status["configured"])
        self.assertFalse(status["connected"])

    def test_panel_can_call_the_service_without_records(self):
        """El panel llama por RPC sin ids (call_kw con args vacios): sin
        @api.model fallaba con 'list index out of range'."""
        from odoo.api import call_kw
        Qbo = self.env["indigo.qbo"].with_user(self.manager)
        self.assertIn("configured", call_kw(Qbo, "qbo_status", [], {}))
        self.assertTrue(call_kw(Qbo, "qbo_authorize_url", [], {}).startswith("https://appcenter.intuit.com/"))

    def test_a_bogus_callback_does_not_cancel_a_connection_in_progress(self):
        qs, _url = self._authorize()
        self.assertEqual(self.Qbo.sudo()._qbo_finish_connect("X", "bogus", "1", None), "invalid_state")
        with patch(REQ + ".post", return_value=FakeResponse(200, token_body())),                 patch(REQ + ".get", return_value=self._company_response()):
            self.assertEqual(self.Qbo.sudo()._qbo_finish_connect("CODE", qs["state"][0], "999", None), "connected")

    def test_two_pending_connections_both_work(self):
        qs1, _ = self._authorize()
        qs2, _ = self._authorize()
        with patch(REQ + ".post", return_value=FakeResponse(200, token_body())),                 patch(REQ + ".get", return_value=self._company_response()):
            self.assertEqual(self.Qbo.sudo()._qbo_finish_connect("C1", qs1["state"][0], "999", None), "connected")
            self.assertEqual(self.Qbo.sudo()._qbo_finish_connect("C2", qs2["state"][0], "999", None), "connected")

    def test_connecting_another_company_resets_the_matches(self):
        dealer = self.env["res.partner"].create({"name": "Reset Dealer", "is_indigo_dealer": True,
                                                 "qbo_customer_id": "58", "qbo_customer_name": "Old"})
        self.env["ir.config_parameter"].sudo().set_param("indigo_qbo.mapping_realm", "111")
        qs, _ = self._authorize()
        with patch(REQ + ".post", return_value=FakeResponse(200, token_body())),                 patch(REQ + ".get", return_value=self._company_response()):
            self.Qbo.sudo()._qbo_finish_connect("CODE", qs["state"][0], "222", None)
        self.assertFalse(dealer.qbo_customer_id)
        self.assertEqual(self.param("mapping_realm"), "222")
        self.assertTrue(self.param("sync_from"))

    def test_company_info_failing_still_connects(self):
        qs, _ = self._authorize()
        with patch(REQ + ".post", return_value=FakeResponse(200, token_body())),                 patch(REQ + ".get", return_value=FakeResponse(500, "boom")):
            self.assertEqual(self.Qbo.sudo()._qbo_finish_connect("CODE", qs["state"][0], "999", None), "connected")
        self.assertTrue(self.client.is_connected())

    def test_status_says_when_it_needs_reconnecting(self):
        self.env["ir.config_parameter"].sudo().set_param("indigo_qbo.sync_from", "2026-10-07 00:00:00")
        status = self.Qbo.with_user(self.manager).qbo_status()
        self.assertFalse(status["connected"])
        self.assertTrue(status["needs_reconnect"])
