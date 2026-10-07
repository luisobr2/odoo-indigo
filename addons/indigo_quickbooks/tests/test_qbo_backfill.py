# -*- coding: utf-8 -*-
"""Lo ya emitido antes de conectar: informe y aplicar."""
import re
from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests import tagged

from odoo.addons.indigo_quickbooks.models.qbo_client import QboError

from .test_qbo_client import _QboCase

CLIENT = "odoo.addons.indigo_quickbooks.models.qbo_client.IndigoQboClient"


class FakeBooks:
    """QBO en memoria: facturas por DocNumber y cobros por Id."""

    def __init__(self):
        self.invoices = {}   # Id -> dict
        self.payments = {}   # Id -> dict
        self.created = []
        self.totals = {}     # DocNumber -> total con impuesto que QBO calcularia
        self.next_id = 300

    def add_invoice(self, number, total, customer="58", payments=()):
        self.next_id += 1
        inv = {"Id": str(self.next_id), "DocNumber": number, "TotalAmt": total, "Balance": total,
               "SyncToken": "0", "CustomerRef": {"value": customer, "name": "C%s" % customer},
               "LinkedTxn": [{"TxnId": p, "TxnType": "Payment"} for p in payments]}
        self.invoices[inv["Id"]] = inv
        return inv

    def query(self, sql, entity):
        if entity == "Invoice":
            m = re.search(r"DocNumber IN \((.*)\)", sql) or re.search(r"DocNumber = ('.*?')", sql)
            names = re.findall(r"'([^']*)'", m.group(1))
            return [i for i in self.invoices.values() if i["DocNumber"] in names]
        if entity == "Payment":
            pid = re.search(r"Id = '(\d+)'", sql).group(1)
            return [self.payments[pid]] if pid in self.payments else []
        return []

    def get(self, path, params=None):
        kind, _sep, rid = path.partition("/")
        if kind == "invoice":
            return {"Invoice": self.invoices[rid]}
        return {}

    def post(self, path, body, params=None):
        self.next_id += 1
        inv = dict(body, Id=str(self.next_id), SyncToken="0",
                   TotalAmt=self.totals.get(body["DocNumber"], sum(l["Amount"] for l in body["Line"])))
        self.invoices[inv["Id"]] = inv
        self.created.append(body["DocNumber"])
        return {"Invoice": inv}

    def patches(self):
        fake = self
        return [patch(CLIENT + ".query", lambda s, sql, e: fake.query(sql, e)),
                patch(CLIENT + ".get", lambda s, p, params=None: fake.get(p, params)),
                patch(CLIENT + ".post", lambda s, p, b, params=None: fake.post(p, b, params))]


@tagged("indigo", "post_install", "-at_install")
class TestQboBackfill(_QboCase):
    def setUp(self):
        super().setUp()
        self.Billing = self.env["indigo.billing"]
        self.Billing.indigo_billing_setup({"next_number": 8201, "tax_rate": 0})
        self.dealer = self.env["res.partner"].create({
            "name": "Backfill Dealer", "is_company": True, "is_indigo_dealer": True, "zip": "33138",
            "qbo_customer_id": "58", "qbo_customer_name": "Backfill Dealer",
        })
        self.unmatched = self.env["res.partner"].create({
            "name": "Unmatched Dealer", "is_company": True, "is_indigo_dealer": True, "zip": "33138",
        })
        self.design = self.env["indigo.design"].create({"code": "QBOBF-SD", "name": "QBO BF", "door_type": "SD"})
        for p in self.env["product.product"].search([("default_code", "=like", "IND-%")]):
            p.qbo_item_id = "2%s" % p.id
        # Emitidas sin conexion: quedan fuera de QuickBooks.
        self.a = self._issue(self.dealer, "Ann")
        self.b = self._issue(self.dealer, "Bob")
        self.c = self._issue(self.dealer, "Cid")
        self.d = self._issue(self.dealer, "Dee")
        self.e = self._issue(self.unmatched, "Eve")
        self.linked = self._issue(self.dealer, "Lin")
        self.linked.write({"qbo_id": "999", "qbo_state": "linked", "qbo_origin": "manual"})
        self.connect()
        self.books = FakeBooks()
        self.books.payments["700"] = {"Id": "700", "TxnDate": "2026-09-30", "PaymentRefNum": "CHK 9",
                                      "Line": [{"Amount": self.a.amount_total,
                                                "LinkedTxn": [{"TxnId": "301", "TxnType": "Invoice"}]}]}
        self.books.add_invoice(self.a.name, self.a.amount_total, payments=["700"])   # 301: igual y cobrada
        self.books.add_invoice(self.b.name, self.b.amount_total + 10)                # distinta
        self.books.add_invoice(self.c.name, self.c.amount_total, customer="77")      # de otro cliente
        self.books.totals[self.d.name] = self.d.amount_total
        self.Qbo = self.env["indigo.qbo"]

    def _issue(self, dealer, client):
        order = self.env["indigo.order"].create({
            "dealer_id": dealer.id, "client_name": client,
            "line_ids": [(0, 0, {"design_id": self.design.id, "door_type": "SD", "color": "white", "qty": 1, "sqf": 20.0})],
        })
        order.stage_id = self.env.ref("indigo_decors.stage_installed")
        prev = self.Billing.indigo_billing_preview(order.ids)
        lines = [dict(ln, price_unit=300.0) for ln in prev["lines"] if ln["kind"] == "door"]
        mid = self.Billing.indigo_billing_create_draft(
            {"dealer_id": dealer.id, "order_ids": order.ids, "lines": lines, "photo_ids": []})
        self.Billing.indigo_billing_post(mid)
        move = self.env["account.move"].browse(mid)
        self.assertEqual(move.qbo_state, "none")
        return move

    def _with_books(self, fn, *args):
        ps = self.books.patches()
        for p in ps:
            p.start()
        try:
            return fn(*args)
        finally:
            for p in ps:
                p.stop()

    def _report(self):
        res = self._with_books(self.Qbo.qbo_backfill_report)
        return res, {r["id"]: r for r in res["rows"]}

    def test_report_says_what_will_happen_to_each(self):
        res, rows = self._report()
        self.assertEqual(rows[self.a.id]["outcome"], "same")
        self.assertEqual(rows[self.a.id]["qbo_balance"], self.a.amount_total)
        self.assertEqual(rows[self.b.id]["outcome"], "different")
        self.assertEqual(rows[self.c.id]["outcome"], "other_customer")
        self.assertEqual(rows[self.d.id]["outcome"], "missing")
        self.assertFalse(rows[self.d.id]["problem"])
        self.assertEqual(rows[self.e.id]["outcome"], "missing")
        self.assertIn("isn't matched", rows[self.e.id]["problem"])
        self.assertNotIn(self.linked.id, rows)
        self.assertGreaterEqual(res["counts"]["blocked"], 1)

    def test_report_writes_nothing(self):
        self._report()
        self.assertEqual((self.a | self.b | self.d).mapped("qbo_state"), ["none"] * 3)
        self.assertFalse(self.books.created)

    def test_apply_links_creates_and_brings_the_payments(self):
        res = self.Qbo.qbo_backfill_apply([self.a.id, self.b.id, self.c.id, self.d.id, self.linked.id])
        self.assertEqual(res["queued"], 4)  # la ya enlazada no
        self.assertEqual(self.linked.qbo_id, "999")
        self._with_books((self.a | self.b | self.c | self.d)._qbo_process)
        self.assertEqual((self.a.qbo_state, self.a.qbo_origin), ("linked", "manual"))
        self.assertEqual(self.b.qbo_state, "mismatch")
        self.assertEqual(self.c.qbo_state, "mismatch")
        self.assertFalse(self.c.qbo_id)  # otro cliente: no se enlaza
        self.assertEqual(self.d.qbo_state, "synced")
        self.assertEqual(self.books.created, [self.d.name])
        # el cobro que QBO ya tenia en la enlazada llega aqui
        self.assertIn(self.a.payment_state, ("paid", "in_payment"))
        pay = self.env["account.payment"].search([("qbo_payment_id", "=", "700:301")])
        self.assertEqual(pay.amount, self.a.amount_total)

    def test_apply_is_for_managers(self):
        office = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Office BF", "login": "qbo_bf_office@test.local",
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id,
                                  self.env.ref("indigo_decors.group_indigo_office").id])],
        })
        self._with_books(self.Qbo.with_user(office).qbo_backfill_report)  # ver, si
        with self.assertRaises(AccessError):
            self.Qbo.with_user(office).qbo_backfill_apply([self.a.id])

    def test_apply_with_nothing_left_says_so(self):
        with self.assertRaises(QboError):
            self.Qbo.qbo_backfill_apply([self.linked.id])

    def test_needs_a_connection(self):
        self.client.clear_tokens()
        with self.assertRaises(QboError) as ctx:
            self.Qbo.qbo_backfill_report()
        self.assertEqual(ctx.exception.code, "not_connected")
