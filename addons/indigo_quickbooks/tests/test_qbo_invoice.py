# -*- coding: utf-8 -*-
"""Enviar facturas de Indigo a QuickBooks (crear, enlazar, corregir, anular).

QBO se simula sustituyendo query/get/post del cliente.
"""
from unittest.mock import patch

from odoo.tests import tagged

from .test_qbo_client import _QboCase

CLIENT = "odoo.addons.indigo_quickbooks.models.qbo_client.IndigoQboClient"


class FakeQbo:
    """QBO en memoria: guarda las facturas por DocNumber y registra llamadas."""

    def __init__(self, existing=None, total_override=None):
        self.invoices = {}  # Id -> dict
        self.calls = []
        self.total_override = total_override
        for inv in existing or []:
            self.invoices[inv["Id"]] = dict(inv)

    def query(self, sql, entity):
        self.calls.append(("query", sql))
        if entity == "Invoice" and "DocNumber = '" in sql:
            num = sql.split("DocNumber = '", 1)[1].split("'", 1)[0]
            return [i for i in self.invoices.values() if i["DocNumber"] == num]
        return []

    def get(self, path, params=None):
        self.calls.append(("get", path))
        if path.startswith("invoice/"):
            return {"Invoice": self.invoices[path.split("/", 1)[1]]}
        return {}

    def post(self, path, body, params=None):
        self.calls.append(("post", path, body, params))
        if params and params.get("operation") == "void":
            inv = self.invoices[body["Id"]]
            inv["SyncToken"] = str(int(inv["SyncToken"]) + 1)
            inv["voided"] = True
            return {"Invoice": inv}
        total = self.total_override if self.total_override is not None else round(
            sum(l["Amount"] for l in body["Line"]) * 1.0, 2)
        if body.get("Id"):
            inv = self.invoices[body["Id"]]
            inv.update(body)
            inv["SyncToken"] = str(int(inv["SyncToken"]) + 1)
            inv["TotalAmt"] = self._total(body, total)
            return {"Invoice": inv}
        new_id = str(100 + len(self.invoices))
        inv = dict(body, Id=new_id, SyncToken="0", TotalAmt=self._total(body, total))
        self.invoices[new_id] = inv
        return {"Invoice": inv}

    def _total(self, body, untaxed):
        # El impuesto: lo que Indigo calculo, salvo que la prueba pida otra cosa.
        return body.get("_expected_total", untaxed) if self.total_override is None else self.total_override

    def patches(self):
        return [patch(CLIENT + ".query", lambda _s, sql, entity: self.query(sql, entity)),
                patch(CLIENT + ".get", lambda _s, path, params=None: self.get(path, params)),
                patch(CLIENT + ".post", lambda _s, path, body, params=None: self.post(path, body, params))]

    def posts(self):
        return [c for c in self.calls if c[0] == "post"]


@tagged("indigo", "post_install", "-at_install")
class TestQboInvoice(_QboCase):
    def setUp(self):
        super().setUp()
        self.Billing = self.env["indigo.billing"]
        self.Billing.indigo_billing_setup({"next_number": 8001, "tax_rate": 7})
        self.dealer = self.env["res.partner"].create({
            "name": "QBO Dealer", "is_company": True, "is_indigo_dealer": True,
            "email": "billing@dealer.test", "zip": "33138", "qbo_customer_id": "58",
            "qbo_customer_name": "QBO Dealer",
        })
        design = self.env["indigo.design"].create({"code": "QBOTEST-SD", "name": "QBO Test", "door_type": "SD"})
        self.order = self.env["indigo.order"].create({
            "dealer_id": self.dealer.id, "client_name": "Jane Roe", "customer_po": "ROE 123456",
            "line_ids": [(0, 0, {"design_id": design.id, "door_type": "SD", "color": "white", "qty": 1, "sqf": 20.0})],
        })
        self.order.stage_id = self.env.ref("indigo_decors.stage_installed")
        for p in self.env["product.product"].search([("default_code", "=like", "IND-%")]):
            p.qbo_item_id = {"IND-SD": "19", "IND-DD": "20"}.get(p.default_code, "2%s" % p.id)
        self.connect()

    def _issue(self):
        prev = self.Billing.indigo_billing_preview(self.order.ids)
        for ln in prev["lines"]:
            if ln["kind"] == "door":
                ln["price_unit"] = 300.0
        mid = self.Billing.indigo_billing_create_draft({
            "dealer_id": self.dealer.id, "order_ids": self.order.ids, "lines": prev["lines"], "photo_ids": [],
        })
        self.Billing.indigo_billing_post(mid)
        return self.env["account.move"].browse(mid)

    def _run(self, fake, moves):
        ps = fake.patches()
        for p in ps:
            p.start()
        try:
            moves._qbo_process()
        finally:
            for p in ps:
                p.stop()

    # ---- crear

    def test_issuing_marks_the_invoice_pending(self):
        move = self._issue()
        self.assertEqual(move.qbo_state, "pending")

    def test_not_connected_leaves_it_alone(self):
        self.client.clear_tokens()
        move = self._issue()
        self.assertEqual(move.qbo_state, "none")

    def test_create_sends_number_customer_lines_and_memo(self):
        move = self._issue()
        fake = FakeQbo(total_override=move.amount_total)
        self._run(fake, move)
        self.assertEqual(move.qbo_state, "synced", move.qbo_error)
        self.assertEqual(move.qbo_origin, "indigo")
        path, body = fake.posts()[0][1], fake.posts()[0][2]
        self.assertEqual(path, "invoice")
        self.assertEqual(body["DocNumber"], move.name)
        self.assertEqual(body["CustomerRef"], {"value": "58"})
        self.assertEqual(body["EmailStatus"], "NotSet")
        self.assertIn("Indigo #%s" % move.name, body["PrivateNote"])
        self.assertIn("ROE 123456", body["PrivateNote"])
        door = next(l for l in body["Line"] if l["SalesItemLineDetail"]["ItemRef"]["value"] == "19")
        self.assertEqual(door["SalesItemLineDetail"]["TaxCodeRef"], {"value": "TAX"})
        self.assertEqual(door["Amount"], 300.0)
        fees = [l for l in body["Line"] if l is not door]
        self.assertTrue(all(l["SalesItemLineDetail"]["TaxCodeRef"] == {"value": "NON"} for l in fees))
        self.assertEqual(move.qbo_id, "100")

    def test_total_that_differs_is_flagged(self):
        move = self._issue()
        fake = FakeQbo(total_override=move.amount_total + 5)
        self._run(fake, move)
        self.assertEqual(move.qbo_state, "mismatch")
        self.assertIn("QuickBooks", move.qbo_error)

    # ---- enlazar lo metido a mano

    def test_existing_invoice_with_the_same_total_is_linked_not_duplicated(self):
        move = self._issue()
        fake = FakeQbo(existing=[{"Id": "77", "DocNumber": move.name, "SyncToken": "4", "TotalAmt": move.amount_total}])
        self._run(fake, move)
        self.assertEqual((move.qbo_state, move.qbo_origin, move.qbo_id), ("linked", "manual", "77"))
        self.assertFalse(fake.posts())

    def test_existing_invoice_with_another_total_is_a_mismatch(self):
        move = self._issue()
        fake = FakeQbo(existing=[{"Id": "77", "DocNumber": move.name, "SyncToken": "4", "TotalAmt": 1.0}])
        self._run(fake, move)
        self.assertEqual(move.qbo_state, "mismatch")
        self.assertFalse(fake.posts())

    # ---- corregir y anular

    def test_correction_updates_the_same_qbo_invoice(self):
        move = self._issue()
        fake = FakeQbo(total_override=move.amount_total)
        self._run(fake, move)
        self.Billing.indigo_billing_reopen(move.id, "price")
        lines = self.Billing.indigo_billing_detail(move.id)["lines"]
        for ln in lines:
            if ln["product_code"] == "IND-SD":
                ln["price_unit"] = 350.0
        self.Billing.indigo_billing_update_draft(move.id, {"lines": lines})
        self.Billing.indigo_billing_post(move.id)
        self.assertEqual(move.qbo_state, "pending")
        fake.total_override = move.amount_total
        self._run(fake, move)
        self.assertEqual(move.qbo_state, "synced", move.qbo_error)
        update = fake.posts()[-1][2]
        self.assertEqual(update["Id"], "100")
        self.assertEqual(update["SyncToken"], "0")
        self.assertEqual(len([c for c in fake.calls if c[0] == "post"]), 2)

    def test_correction_of_a_hand_made_qbo_invoice_is_not_overwritten(self):
        move = self._issue()
        fake = FakeQbo(existing=[{"Id": "77", "DocNumber": move.name, "SyncToken": "4", "TotalAmt": move.amount_total}])
        self._run(fake, move)
        self.Billing.indigo_billing_reopen(move.id)
        self.Billing.indigo_billing_post(move.id)
        self._run(fake, move)
        self.assertEqual(move.qbo_state, "mismatch")
        self.assertFalse(fake.posts())

    def test_void_voids_it_in_qbo(self):
        move = self._issue()
        fake = FakeQbo(total_override=move.amount_total)
        self._run(fake, move)
        self.Billing.indigo_billing_void(move.id, "test")
        self.assertEqual(move.qbo_state, "pending")
        self._run(fake, move)
        self.assertEqual(move.qbo_state, "voided", move.qbo_error)
        _op, path, body, params = fake.posts()[-1]
        self.assertEqual((path, params), ("invoice", {"operation": "void"}))
        self.assertEqual(body["Id"], "100")

    # ---- errores

    def test_missing_customer_match_is_an_error_with_backoff(self):
        self.dealer.qbo_customer_id = False
        move = self._issue()
        fake = FakeQbo()
        self._run(fake, move)
        self.assertEqual(move.qbo_state, "error")
        self.assertIn("QBO Dealer", move.qbo_error)
        self.assertEqual(move.qbo_attempts, 1)
        self.assertTrue(move.qbo_next_try)
        self.assertFalse(fake.posts())

    def test_rate_limit_keeps_it_pending_for_later(self):
        from odoo.addons.indigo_quickbooks.models.qbo_client import QboError
        move = self._issue()

        def boom(*a, **k):
            raise QboError("rate_limit", "too many")
        with patch(CLIENT + ".query", boom):
            move._qbo_process()
        self.assertEqual(move.qbo_state, "error")
        self.assertTrue(move.qbo_next_try)

    def test_status_counts_and_retry(self):
        self.dealer.qbo_customer_id = False
        move = self._issue()
        self._run(FakeQbo(), move)
        status = self.env["indigo.qbo"].qbo_status()
        self.assertEqual(status["errors"], 1)
        self.dealer.qbo_customer_id = "58"
        fake = FakeQbo(total_override=move.amount_total)
        ps = fake.patches()
        for p in ps:
            p.start()
        try:
            detail = self.env["indigo.qbo"].qbo_retry(move.id)
        finally:
            for p in ps:
                p.stop()
        self.assertEqual(detail["qbo_state"], "synced")
        row = self.Billing.indigo_billing_detail(move.id)
        self.assertEqual(row["qbo_state"], "synced")
