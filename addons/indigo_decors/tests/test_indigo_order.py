# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged("indigo", "post_install", "-at_install")
class TestIndigoOrder(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.Order = cls.env["indigo.order"]
        cls.Design = cls.env["indigo.design"]
        cls.Stage = cls.env["indigo.stage"]
        cls.Payout = cls.env["indigo.payout"]

        cls.dealer = cls.Partner.create({
            "name": "Test Dealer Co",
            "is_company": True,
            "is_indigo_dealer": True,
            "indigo_default_price_per_sqf": 15.0,
            "email": "dealer@test.example",
        })
        cls.painter = cls.Partner.create({"name": "Test Painter"})
        cls.installer1 = cls.Partner.create({"name": "Test Installer 1"})
        cls.installer2 = cls.Partner.create({"name": "Test Installer 2"})
        cls.design = cls.Design.create({"code": "TEST-SD", "name": "Test Single", "door_type": "SD"})

    def _create_order(self, **overrides):
        vals = {
            "dealer_id": self.dealer.id,
            "client_name": "Test Client",
            "painter_id": self.painter.id,
            "installer_ids": [(6, 0, [self.installer1.id, self.installer2.id])],
            "line_ids": [
                (0, 0, {
                    "design_id": self.design.id,
                    "door_type": "SD",
                    "color": "white",
                    "width": 36.0,
                    "height": 80.0,
                    "qty": 1,
                }),
            ],
        }
        vals.update(overrides)
        return self.Order.create(vals)

    # ---------- Creacion / valores por defecto ----------

    def test_create_defaults_price_from_dealer(self):
        order = self._create_order()
        self.assertEqual(order.price_per_sqf, 15.0, "price_per_sqf debe venir del dealer")

    def test_create_generates_access_token(self):
        order = self._create_order()
        self.assertTrue(order.access_token, "access_token debe generarse automaticamente")
        self.assertEqual(len(order.access_token), 32)

    def test_create_sets_last_stage_change(self):
        order = self._create_order()
        self.assertTrue(order.last_stage_change)

    # ---------- Calculos ----------

    def test_sqf_computation(self):
        order = self._create_order()
        # 36*80/144 = 20
        self.assertEqual(order.total_sqf, 20.0)
        self.assertEqual(order.door_count, 1)

    def test_dealer_charge_computation(self):
        order = self._create_order()
        # 20 SQF * $15 = $300
        self.assertEqual(order.total_dealer_charge, 300.0)

    def test_payouts_use_contractor_rate(self):
        order = self._create_order()
        # Cambiar tarifa pintor a $10
        rate = self.env["indigo.contractor.rate"].search([
            ("contractor_type", "=", "painter"),
        ], limit=1)
        original_rate = rate.rate
        rate.rate = 10.0
        order.invalidate_recordset(["total_painter_payout"])
        # Recompute
        order._compute_totals()
        self.assertEqual(order.total_painter_payout, 200.0, "20 SQF * $10")
        # Restore
        rate.rate = original_rate

    # ---------- Workflow / triggers ----------

    def test_painter_payout_on_leaving_painting(self):
        order = self._create_order()
        stage_painting = self.env.ref("indigo_decors.stage_painting")
        stage_ready_install = self.env.ref("indigo_decors.stage_ready_install")
        order.stage_id = stage_painting.id
        order.stage_id = stage_ready_install.id
        payouts = self.Payout.search([
            ("contractor_id", "=", self.painter.id),
            ("contractor_type", "=", "painter"),
        ])
        self.assertEqual(len(payouts), 1, "Debe crear 1 payout de pintor")
        self.assertEqual(payouts.amount, 160.0, "20 SQF * $8")

    def test_installer_payout_on_entering_installed(self):
        order = self._create_order()
        stage_installed = self.env.ref("indigo_decors.stage_installed")
        order.stage_id = stage_installed.id
        payouts = self.Payout.search([
            ("contractor_id", "in", [self.installer1.id, self.installer2.id]),
            ("contractor_type", "=", "installer"),
        ])
        self.assertEqual(len(payouts), 2, "Un payout por instalador")
        total = sum(payouts.mapped("amount"))
        # 1 puerta / 2 instaladores = 0.5 cada uno, * $35 = $17.5 cada uno = $35 total
        self.assertEqual(total, 35.0)

    def test_payouts_are_idempotent(self):
        order = self._create_order()
        stage_painting = self.env.ref("indigo_decors.stage_painting")
        stage_ready_install = self.env.ref("indigo_decors.stage_ready_install")
        order.stage_id = stage_painting.id
        order.stage_id = stage_ready_install.id
        order.stage_id = stage_painting.id
        order.stage_id = stage_ready_install.id  # 2do "salir de Painting"
        painter_payouts = self.Payout.search([
            ("contractor_id", "=", self.painter.id),
        ])
        self.assertEqual(len(painter_payouts), 1, "Idempotente: solo 1 payout aunque pase 2 veces")

    # ---------- Kanban filter por dealer ----------

    def test_kanban_group_expand_with_dealer_filter_hides_optional(self):
        # Dealer SIN etapas opcionales activas
        stages = self.Order._read_group_stage_ids(
            self.Stage.browse(),
            [("dealer_id", "=", self.dealer.id)],
            "sequence",
        )
        codes = stages.mapped("code")
        # No deberian estar las opcionales 2-5
        self.assertNotIn("design_pending", codes)
        self.assertNotIn("design_confirmed", codes)
        # Pero si las no-opcionales
        self.assertIn("cnc", codes)
        self.assertIn("painting", codes)
        self.assertIn("installed", codes)

    def test_kanban_group_expand_without_dealer_shows_all(self):
        stages = self.Order._read_group_stage_ids(
            self.Stage.browse(),
            [],
            "sequence",
        )
        codes = stages.mapped("code")
        # Todas presentes (opcionales y no-opcionales)
        self.assertIn("design_pending", codes)
        self.assertIn("cnc", codes)
