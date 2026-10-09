# -*- coding: utf-8 -*-
"""Costo estimado por puerta, gastos y real del mes (Majela, 9-oct-2026)."""
import base64

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("indigo", "post_install", "-at_install")
class TestIndigoCosting(TransactionCase):
    def setUp(self):
        super().setUp()
        self.C = self.env["indigo.costing"]
        icp = self.env["ir.config_parameter"].sudo()
        for key in ("cnc_per_sqf", "acm_sheet_price", "acm_sheet_sqf", "paint_per_sqf", "glue_per_door",
                    "other_per_door", "install_per_door", "gas_per_door"):
            icp.set_param("indigo_decors.cost." + key, "")
        self.dealer = self.env["res.partner"].create({"name": "Cost Dealer", "is_company": True, "is_indigo_dealer": True})
        self.design = self.env["indigo.design"].create({"code": "COST-SD", "name": "Cost SD", "door_type": "SD"})
        self.order = self.env["indigo.order"].create({
            "dealer_id": self.dealer.id, "client_name": "Cost Client",
            "line_ids": [(0, 0, {"design_id": self.design.id, "door_type": "SD", "color": "white", "qty": 1, "sqf": 20.0})
                         for _i in range(2)],
        })

    def _line(self, est, label):
        return next(l for l in est["lines"] if l["label"] == label)

    def test_estimate_uses_majela_rates(self):
        est = self.C.indigo_cost_order(self.order.id)
        sqf, doors = self.order.total_sqf, self.order.door_count
        self.assertAlmostEqual(self._line(est, "CNC / router cut")["amount"], round(sqf * 0.94, 2))
        self.assertAlmostEqual(self._line(est, "ACM")["amount"], round(sqf * 42 / 32, 2))
        self.assertAlmostEqual(self._line(est, "Paint material")["amount"], round(sqf * 2, 2))
        self.assertAlmostEqual(self._line(est, "Glue")["amount"], doors * 8)
        self.assertAlmostEqual(self._line(est, "Other supplies")["amount"], doors * 5)
        self.assertAlmostEqual(self._line(est, "Installation")["amount"], doors * 35)
        self.assertAlmostEqual(self._line(est, "Gas and tolls")["amount"], doors * 10)
        self.assertAlmostEqual(est["total"], round(sum(l["amount"] for l in est["lines"]), 2))
        self.assertAlmostEqual(est["per_sqf"], round(est["total"] / sqf, 2))
        self.assertAlmostEqual(est["margin"], round(self.order.total_dealer_charge - est["total"], 2))

    def test_rates_are_editable(self):
        self.C.indigo_cost_save_settings({"glue_per_door": 10, "unknown": 5})
        est = self.C.indigo_cost_order(self.order.id)
        self.assertAlmostEqual(self._line(est, "Glue")["amount"], self.order.door_count * 10)
        with self.assertRaises(ValidationError):
            self.C.indigo_cost_save_settings({"acm_sheet_sqf": 0})

    def test_digitization_paid_counts_as_labor(self):
        grp = self.env.ref("indigo_decors.group_indigo_designer")
        amado = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Amado Cost", "login": "amado_cost@test.local", "email": "amado_cost@test.local",
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id, grp.id])]})
        self.env["indigo.contractor.rate"].create({"name": "Amado Cost", "contractor_type": "digitizer",
                                                   "partner_id": amado.partner_id.id, "rate": 7.5, "rate_unit": "piece"})
        self.order.designer_id = amado
        est = self.C.indigo_cost_order(self.order.id)
        self.assertAlmostEqual(self._line(est, "Digitization after hours")["amount"], 7.5 * self.order.door_count)

    def test_expenses_and_month(self):
        today = fields.Date.context_today(self.C)
        month = today.strftime("%Y-%m")
        before = len(self.C.indigo_expense_list(month))
        row = self.C.indigo_expense_create({
            "date": str(today), "supplier": "ACM Supplier", "category": "acm", "amount": 420,
            "file_name": "bill.pdf", "file_b64": base64.b64encode(b"%PDF-1.4 test").decode()})
        self.assertTrue(row["attachment_id"])
        self.C.indigo_expense_create({"date": str(today), "supplier": "Paint Co", "category": "paint", "amount": 80})
        self.assertEqual(len(self.C.indigo_expense_list(month)), before + 2)
        m = self.C.indigo_cost_month(month)
        self.assertGreaterEqual(m["purchases"]["acm"], 420)
        self.assertGreaterEqual(m["purchases_total"], 500)
        self.assertAlmostEqual(m["result"], round(m["sold"] - m["spent"], 2))
        self.C.indigo_expense_delete(row["id"])
        self.assertEqual(len(self.C.indigo_expense_list(month)), before + 1)

    def test_expense_needs_supplier_and_positive_amount(self):
        with self.assertRaises(ValidationError):
            self.C.indigo_expense_create({"supplier": " ", "category": "acm", "amount": 10})
        with self.assertRaises(ValidationError):
            self.C.indigo_expense_create({"supplier": "X", "category": "acm", "amount": 0})
        with self.assertRaises(ValidationError):
            self.C.indigo_cost_month("octubre")

    def test_only_office_and_managers(self):
        plain = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Plain Cost", "login": "plain_cost@test.local",
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id])]})
        with self.assertRaises(AccessError):
            self.C.with_user(plain).indigo_cost_order(self.order.id)
        with self.assertRaises(AccessError):
            self.C.with_user(plain).indigo_cost_month("2026-10")

    # ---- auditoria (9-oct)

    def test_nan_and_infinity_are_refused(self):
        with self.assertRaises(ValidationError):
            self.C.indigo_cost_save_settings({"glue_per_door": "nan"})
        with self.assertRaises(ValidationError):
            self.C.indigo_cost_save_settings({"glue_per_door": float("inf")})
        with self.assertRaises(ValidationError):
            self.C.indigo_expense_create({"supplier": "X", "category": "acm", "amount": "nan"})
        with self.assertRaises(ValidationError):
            self.C.indigo_expense_create({"supplier": "X", "category": "acm", "amount": 5, "date": "2026-02-30"})
        with self.assertRaises(ValidationError):
            self.C.indigo_expense_create({"supplier": "X", "category": "acm", "amount": 5, "file_b64": "%%%"})

    def test_a_foreign_attachment_is_never_served_or_deleted(self):
        other = self.env["ir.attachment"].create({"name": "secret.txt", "datas": base64.b64encode(b"x"),
                                                  "res_model": "res.partner", "res_id": self.dealer.id})
        exp = self.env["indigo.expense"].create({"supplier": "S", "category": "other", "amount": 5,
                                                 "attachment_id": other.id})
        with self.assertRaises(Exception):
            self.C.indigo_expense_file(exp.id)
        self.C.indigo_expense_delete(exp.id)
        self.assertTrue(other.exists())

    def test_office_cannot_write_expenses_directly(self):
        office = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Office Cost", "login": "office_cost@test.local",
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id, self.env.ref("indigo_decors.group_indigo_office").id])]})
        with self.assertRaises(AccessError):
            self.env["indigo.expense"].with_user(office).create({"supplier": "S", "category": "other", "amount": 5})
        row = self.C.with_user(office).indigo_expense_create({"supplier": "S", "category": "other", "amount": 5})
        self.assertTrue(row["id"])

    def test_painting_estimate_uses_the_expected_rate_without_painter(self):
        est = self.C.indigo_cost_order(self.order.id)
        paint = self._line(est, "Painting")
        rate = self.order._indigo_expected_paint_rate()
        if rate is not None:
            self.assertAlmostEqual(paint["amount"], round(self.order.total_sqf * rate, 2))
        self.order.stage_id = self.env.ref("indigo_decors.stage_painting")  # Michel
        est = self.C.indigo_cost_order(self.order.id)
        self.assertFalse([l for l in est["lines"] if l["label"] == "Paint material"])

    def test_bad_ids_say_not_found(self):
        from odoo.exceptions import UserError
        with self.assertRaises(UserError):
            self.C.indigo_cost_order("abc")
