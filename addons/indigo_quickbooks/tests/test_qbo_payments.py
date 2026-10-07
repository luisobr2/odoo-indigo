# -*- coding: utf-8 -*-
"""Cobros QuickBooks -> Indigo: webhook firmado, aplicar, CDC y bloqueo manual."""
import base64
import hashlib
import hmac
import json
import os
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from .test_qbo_client import _QboCase

CLIENT = "odoo.addons.indigo_quickbooks.models.qbo_client.IndigoQboClient"
VERIFIER = "test-verifier"


def sign(raw):
    return base64.b64encode(hmac.new(VERIFIER.encode(), raw, hashlib.sha256).digest()).decode()


def qbo_payment(pid="500", lines=None, date="2026-10-07", ref="CHK 77"):
    lines = lines or ()
    return {
        "Id": pid, "TxnDate": date, "PaymentRefNum": ref,
        "TotalAmt": sum(a for _i, a in lines),
        "Line": [{"Amount": a, "LinkedTxn": [{"TxnId": i, "TxnType": "Invoice"}]} for i, a in lines],
    }


@tagged("indigo", "post_install", "-at_install")
class TestQboPayments(_QboCase):
    def setUp(self):
        super().setUp()
        env_patch = patch.dict(os.environ, {"QBO_WEBHOOK_VERIFIER": VERIFIER})
        env_patch.start()
        self.addCleanup(env_patch.stop)
        self.Billing = self.env["indigo.billing"]
        self.Billing.indigo_billing_setup({"next_number": 8101, "tax_rate": 0})
        self.dealer = self.env["res.partner"].create({
            "name": "Pay Dealer", "is_company": True, "is_indigo_dealer": True,
            "email": "billing@paydealer.test", "zip": "33138",
        })
        self.design = self.env["indigo.design"].create({"code": "QBOPAY-SD", "name": "QBO Pay", "door_type": "SD"})
        self.order = self._order("Pat Payer")
        self.move = self._issue(self.order, "100")
        self.T = self.move.amount_total
        self.connect()
        self.Qbo = self.env["indigo.qbo"]
        self.icp = self.env["ir.config_parameter"].sudo()
        for key in ("auto_close", "cdc_cursor", "last_payment_at"):
            self.icp.set_param("indigo_qbo." + key, "")

    def _order(self, client):
        order = self.env["indigo.order"].create({
            "dealer_id": self.dealer.id, "client_name": client,
            "line_ids": [(0, 0, {"design_id": self.design.id, "door_type": "SD", "color": "white", "qty": 1, "sqf": 20.0})],
        })
        order.stage_id = self.env.ref("indigo_decors.stage_installed")
        return order

    def _issue(self, order, qbo_id):
        """Emitida SIN conexion (no se encola) y marcada como ya en QBO."""
        prev = self.Billing.indigo_billing_preview(order.ids)
        lines = [dict(ln, price_unit=300.0) for ln in prev["lines"] if ln["kind"] == "door"]
        mid = self.Billing.indigo_billing_create_draft({
            "dealer_id": self.dealer.id, "order_ids": order.ids, "lines": lines, "photo_ids": [],
        })
        self.Billing.indigo_billing_post(mid)
        move = self.env["account.move"].browse(mid)
        move.write({"qbo_id": qbo_id, "qbo_state": "synced", "qbo_origin": "indigo"})
        return move

    def _live(self, pid="500"):
        return self.env["account.payment"].search([("qbo_payment_id", "=like", "%s:%%" % pid), ("state", "!=", "cancel")])

    # ---- webhook

    def test_webhook_rejects_a_bad_signature(self):
        raw = json.dumps({"eventNotifications": []}).encode()
        Event = self.env["indigo.qbo.event"]
        self.assertEqual(Event._qbo_receive(raw, "bad", json.loads(raw)), 401)
        self.assertEqual(Event._qbo_receive(raw, None, json.loads(raw)), 401)

    def test_webhook_queues_payments_of_our_company_only(self):
        data = {"eventNotifications": [
            {"realmId": "123", "dataChangeEvent": {"entities": [
                {"name": "Payment", "id": "501", "operation": "Create", "lastUpdated": "2026-10-07T10:00:00Z"},
                {"name": "Invoice", "id": "9", "operation": "Update"},
            ]}},
            {"realmId": "999", "dataChangeEvent": {"entities": [{"name": "Payment", "id": "777", "operation": "Create"}]}},
        ]}
        raw = json.dumps(data).encode()
        self.assertEqual(self.env["indigo.qbo.event"]._qbo_receive(raw, sign(raw), data), 200)
        events = self.env["indigo.qbo.event"].search([("state", "=", "pending")])
        self.assertEqual(events.mapped("entity_id"), ["501"])

    def test_webhook_understands_cloudevents(self):
        data = [{"specversion": "1.0", "type": "qbo.payment.updated.v1", "intuitentityid": "502",
                 "intuitaccountid": "123", "time": "2026-10-07T10:00:00Z"},
                {"specversion": "1.0", "type": "qbo.invoice.updated.v1", "intuitentityid": "3", "intuitaccountid": "123"}]
        raw = json.dumps(data).encode()
        self.assertEqual(self.env["indigo.qbo.event"]._qbo_receive(raw, sign(raw), data), 200)
        ev = self.env["indigo.qbo.event"].search([("entity_id", "=", "502")])
        self.assertEqual(ev.operation, "updated")

    # ---- aplicar

    def test_full_payment_marks_the_invoice_and_order_paid(self):
        self.Qbo._qbo_apply_payment("500", qbo_payment(lines=(("100", self.T),)))
        self.assertEqual(self.move.payment_state in ("paid", "in_payment"), True)
        pay = self._live()
        self.assertEqual(pay.qbo_payment_id, "500:100")
        self.assertEqual(str(pay.date), "2026-10-07")
        self.assertIn("CHK 77", pay.ref)
        self.assertEqual(self.order.payment_state, "paid")
        self.assertTrue(self.icp.get_param("indigo_qbo.last_payment_at"))

    def test_partial_payment(self):
        self.Qbo._qbo_apply_payment("500", qbo_payment(lines=(("100", 100.0),)))
        self.assertEqual(self.move.amount_residual, round(self.T - 100.0, 2))
        self.assertEqual(self.order.payment_state, "partial")

    def test_the_same_payment_twice_is_recorded_once(self):
        self.Qbo._qbo_apply_payment("500", qbo_payment(lines=(("100", 100.0),)))
        self.Qbo._qbo_apply_payment("500", qbo_payment(lines=(("100", 100.0),)))
        self.assertEqual(len(self._live()), 1)
        self.assertEqual(self.move.amount_residual, round(self.T - 100.0, 2))

    def test_payment_edited_in_qbo_is_redone(self):
        self.Qbo._qbo_apply_payment("500", qbo_payment(lines=(("100", 100.0),)))
        first = self._live()
        self.Qbo._qbo_apply_payment("500", qbo_payment(lines=(("100", 250.0),)))
        self.assertEqual(first.state, "cancel")
        self.assertEqual(self._live().amount, 250.0)
        self.assertEqual(self.move.amount_residual, round(self.T - 250.0, 2))

    def test_payment_deleted_or_voided_in_qbo_is_undone(self):
        self.Qbo._qbo_apply_payment("500", qbo_payment(lines=(("100", self.T),)))
        self.Qbo._qbo_apply_payment("500", None)
        self.assertFalse(self._live())
        self.assertEqual(self.move.amount_residual, self.T)
        self.assertEqual(self.order.payment_state, "unpaid")
        # anulado: QBO deja el cobro con importes a 0
        self.Qbo._qbo_apply_payment("500", qbo_payment(lines=(("100", self.T),)))
        self.Qbo._qbo_apply_payment("500", qbo_payment(lines=(("100", 0.0),)))
        self.assertFalse(self._live())

    def test_one_qbo_payment_for_two_invoices(self):
        order2 = self._order("Second Payer")
        move2 = self._issue(order2, "101")
        self.Qbo._qbo_apply_payment("500", qbo_payment(lines=(("100", self.T), ("101", 120.0))))
        self.assertEqual(sorted(self._live().mapped("qbo_payment_id")), ["500:100", "500:101"])
        self.assertEqual(move2.amount_residual, round(move2.amount_total - 120.0, 2))

    def test_invoice_indigo_does_not_know_is_ignored(self):
        self.Qbo._qbo_apply_payment("500", qbo_payment(lines=(("4242", 50.0),)))
        self.assertFalse(self._live())

    def test_more_than_the_balance_is_capped_and_not_redone_each_time(self):
        over = round(self.T + 20.0, 2)
        self.Qbo._qbo_apply_payment("500", qbo_payment(lines=(("100", over),)))
        pay = self._live()
        self.assertEqual((pay.amount, pay.qbo_amount), (self.T, over))
        self.Qbo._qbo_apply_payment("500", qbo_payment(lines=(("100", over),)))
        self.assertEqual(self._live(), pay)

    def test_invoice_paid_here_is_not_paid_twice(self):
        self.client.clear_tokens()  # sin conexion, la oficina cobra a mano
        self.Billing.indigo_billing_register_payment(self.move.id, {"amount": self.T, "method": "check"})
        self.connect()
        self.Qbo._qbo_apply_payment("500", qbo_payment(lines=(("100", self.T),)))
        self.assertFalse(self._live())

    # ---- cerrar la orden al cobrar

    def test_auto_close_is_off_by_default(self):
        self.Qbo._qbo_apply_payment("500", qbo_payment(lines=(("100", self.T),)))
        self.assertNotEqual(self.order.stage_id.code, "closed")

    def test_auto_close_closes_paid_orders(self):
        self.Qbo.qbo_save_settings({"auto_close": True})
        self.assertTrue(self.Qbo.qbo_status()["auto_close"])
        self.Qbo._qbo_apply_payment("500", qbo_payment(lines=(("100", 100.0),)))
        self.assertNotEqual(self.order.stage_id.code, "closed")  # parcial: no
        self.Qbo._qbo_apply_payment("501", qbo_payment(pid="501", lines=(("100", round(self.T - 100.0, 2)),)))
        self.assertEqual(self.order.stage_id.code, "closed")

    # ---- cobro a mano bloqueado con conexion

    def test_record_payment_is_refused_while_connected(self):
        with self.assertRaises(UserError) as ctx:
            self.Billing.with_context(qbo_enforce_payments=True).indigo_billing_register_payment(
                self.move.id, {"amount": 10.0, "method": "check"})
        self.assertIn("QuickBooks", str(ctx.exception))
        self.assertTrue(self.Qbo.qbo_status()["payments_from_qbo"])
        self.assertTrue(self.Billing.indigo_billing_detail(self.move.id)["payments_from_qbo"])

    def test_record_payment_works_without_connection(self):
        self.client.clear_tokens()
        self.Billing.with_context(qbo_enforce_payments=True).indigo_billing_register_payment(
            self.move.id, {"amount": 10.0, "method": "check"})
        self.assertEqual(self.move.amount_residual, round(self.T - 10.0, 2))
        self.assertFalse(self.Billing.indigo_billing_detail(self.move.id)["payments_from_qbo"])

    # ---- tarea programada

    def test_cron_applies_queued_events(self):
        self.env["indigo.qbo.event"].create([{"entity_id": "500"}, {"entity_id": "500"}])
        queries = []

        def query(this, sql, entity):
            queries.append(sql)
            return [qbo_payment(lines=(("100", self.T),))] if entity == "Payment" else []
        with patch(CLIENT + ".query", query), patch(CLIENT + ".get", return_value={"CDCResponse": []}):
            self.env["indigo.qbo.event"]._qbo_cron_payments()
        self.assertEqual(len(queries), 1)  # dos avisos del mismo cobro, una consulta
        self.assertEqual(len(self._live()), 1)
        self.assertFalse(self.env["indigo.qbo.event"].search([("state", "=", "pending")]))

    def test_cron_cdc_applies_changes_and_moves_the_cursor(self):
        cdc = {"CDCResponse": [{"QueryResponse": [{"Payment": [qbo_payment(lines=(("100", self.T),))]}]}]}
        with patch(CLIENT + ".get", return_value=cdc) as get:
            self.env["indigo.qbo.event"]._qbo_cron_payments()
        self.assertEqual(get.call_args.args[0], "cdc")
        self.assertEqual(get.call_args.args[1]["entities"], "Payment")
        self.assertEqual(len(self._live()), 1)
        self.assertTrue(self.icp.get_param("indigo_qbo.cdc_cursor"))

    def test_cdc_deleted_payment_is_undone(self):
        self.Qbo._qbo_apply_payment("500", qbo_payment(lines=(("100", self.T),)))
        cdc = {"CDCResponse": [{"QueryResponse": [{"Payment": [{"Id": "500", "status": "Deleted"}]}]}]}
        with patch(CLIENT + ".get", return_value=cdc):
            self.env["indigo.qbo.event"]._qbo_cron_payments()
        self.assertFalse(self._live())

    def test_cdc_failure_keeps_the_cursor(self):
        self.icp.set_param("indigo_qbo.cdc_cursor", "2026-10-06 00:00:00")
        bad = {"CDCResponse": [{"QueryResponse": [{"Payment": [{"Id": "x1", "Line": []}]}]}]}
        with patch(CLIENT + ".get", return_value=bad):
            self.env["indigo.qbo.event"]._qbo_cron_payments()
        self.assertEqual(self.icp.get_param("indigo_qbo.cdc_cursor"), "2026-10-06 00:00:00")

    def test_cron_does_nothing_without_connection(self):
        self.client.clear_tokens()
        self.env["indigo.qbo.event"].create({"entity_id": "500"})
        with patch(CLIENT + ".query") as query, patch(CLIENT + ".get") as get:
            self.env["indigo.qbo.event"]._qbo_cron_payments()
        query.assert_not_called()
        get.assert_not_called()
