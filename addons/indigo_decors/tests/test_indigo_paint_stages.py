# -*- coding: utf-8 -*-
"""Dos etapas de pintura: Michel e Indigo (pedido de Majela, 2026-09-29).

Lo que se comprueba es lo que pidio:

  * dos etapas, Michel e Indigo, entre CNC y Ready for Installation;
  * en la de Michel pinta Michel; en la de Indigo, Elio o Mandy;
  * de la de Indigo no se avanza sin decir quien pinto;
  * cada uno cobra su tarifa (Michel $8/sqf, Indigo $4/sqf), y solo al
    avanzar, no al pasar de una etapa de pintura a la otra;
  * la hoja del pintor de Indigo dice quien pinto y el precio de $4.
"""
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("indigo", "post_install", "-at_install")
class TestIndigoPaintStages(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Partner = cls.env["res.partner"]
        Rate = cls.env["indigo.contractor.rate"]
        cls.Order = cls.env["indigo.order"]
        cls.Payout = cls.env["indigo.payout"]
        cls.stage_cnc = cls.env.ref("indigo_decors.stage_cnc")
        cls.michel_stage = cls.env.ref("indigo_decors.stage_painting")
        cls.indigo_stage = cls.env.ref("indigo_decors.stage_painting_indigo")
        cls.ready = cls.env.ref("indigo_decors.stage_ready_install")
        cls.dealer = Partner.create({"name": "Paint Stage Dealer", "is_company": True, "is_indigo_dealer": True})
        cls.design = cls.env["indigo.design"].create({"code": "PAINTST-SD", "name": "Paint Stage", "door_type": "SD"})
        cls.michel = Partner.create({"name": "Michel (test)"})
        cls.elio = Partner.create({"name": "Elio (test)"})
        cls.mandy = Partner.create({"name": "Mandy (test)"})
        cls.outsider = Partner.create({"name": "Not a painter (test)"})
        # Sin reglas de otras pruebas o de la base: los pintores son estos tres.
        Rate.search([("contractor_type", "=", "painter"), ("partner_id", "!=", False)]).write({"paint_shop": False})
        for partner, rate, shop in ((cls.michel, 8.0, "michel"), (cls.elio, 4.0, "indigo"), (cls.mandy, 4.0, "indigo")):
            Rate.create({
                "name": "Painter %s" % partner.name, "contractor_type": "painter", "partner_id": partner.id,
                "rate": rate, "rate_unit": "sqf", "paint_shop": shop,
            })

    def _order(self, stage=None):
        order = self.Order.create({
            "dealer_id": self.dealer.id,
            "client_name": "Paint Client",
            "line_ids": [(0, 0, {"design_id": self.design.id, "door_type": "SD", "color": "white", "qty": 1, "sqf": 20.0})],
        })
        order.stage_id = (stage or self.stage_cnc).id
        return order

    def _painter_payout(self, order):
        return self.env["indigo.payout.line"].search([
            ("order_id", "=", order.id), ("payout_id.contractor_type", "=", "painter"),
        ])

    def test_two_paint_stages_between_cnc_and_install(self):
        self.assertEqual(self.michel_stage.code, "painting")
        self.assertEqual(self.indigo_stage.code, "painting_indigo")
        self.assertIn("Michel", self.michel_stage.name)
        self.assertIn("Indigo", self.indigo_stage.name)
        for stage in (self.michel_stage, self.indigo_stage):
            self.assertTrue(self.stage_cnc.sequence < stage.sequence < self.ready.sequence)
        rule = self.env.ref("indigo_decors.rule_indigo_order_painter")
        self.assertIn("painting_indigo", rule.domain_force)

    def test_painters_come_from_their_pay_rules(self):
        self.assertEqual(self.Order._indigo_painters("michel"), self.michel)
        self.assertEqual(set(self.Order._indigo_painters("indigo").ids), {self.elio.id, self.mandy.id})
        shops = {p["name"]: p["shop"] for p in self.Order.indigo_painters_list()}
        self.assertEqual(shops, {"Michel (test)": "michel", "Elio (test)": "indigo", "Mandy (test)": "indigo"})

    def test_michel_stage_paints_michel_and_pays_8(self):
        order = self._order()
        order.stage_id = self.michel_stage.id
        self.assertEqual(order.painter_id, self.michel)
        order.stage_id = self.ready.id
        lines = self._painter_payout(order)
        self.assertEqual(lines.mapped("rate"), [8.0])
        self.assertAlmostEqual(order.total_painter_payout, 160.0)

    def test_indigo_needs_elio_or_mandy_and_pays_4(self):
        order = self._order(self.michel_stage)  # llega con Michel
        order.stage_id = self.indigo_stage.id
        self.assertFalse(order.painter_id, "Michel no pinta en Indigo: hay que elegir")
        with self.assertRaises(UserError):
            order.stage_id = self.ready.id
        order.painter_id = self.outsider.id
        with self.assertRaises(UserError):
            order.stage_id = self.ready.id
        order.painter_id = self.elio.id
        order.stage_id = self.ready.id
        self.assertEqual(order.stage_id, self.ready)
        lines = self._painter_payout(order)
        self.assertEqual(lines.mapped("rate"), [4.0])
        self.assertEqual(lines.payout_id.contractor_id, self.elio)
        self.assertAlmostEqual(order.total_painter_payout, 80.0)

    def test_moving_between_paint_stages_pays_nobody(self):
        order = self._order(self.michel_stage)
        order.stage_id = self.indigo_stage.id
        order.stage_id = self.michel_stage.id
        self.assertEqual(order.painter_id, self.michel)
        self.assertFalse(self._painter_payout(order))
        order.stage_id = self.stage_cnc.id  # volver a CNC tampoco paga
        self.assertFalse(self._painter_payout(order))

    def test_cnc_wizard_sends_to_the_chosen_stage(self):
        order = self._order()
        wiz = self.env["indigo.cnc.done.wizard"].create({"order_id": order.id, "paint_stage": "indigo"})
        wiz.action_save_and_advance()
        self.assertEqual(order.stage_id, self.indigo_stage)
        other = self._order()
        self.env["indigo.cnc.done.wizard"].create({"order_id": other.id}).action_save_and_advance()
        self.assertEqual(other.stage_id, self.michel_stage, "Michel sigue siendo el destino por defecto")
        self.assertEqual(other.painter_id, self.michel)

    def test_painted_wizard_in_indigo_asks_who_painted(self):
        order = self._order(self.indigo_stage)
        Wizard = self.env["indigo.painter.done.wizard"]
        with self.assertRaises(UserError):
            Wizard.create({"order_id": order.id}).action_save_and_advance()
        Wizard.create({"order_id": order.id, "painter_id": self.mandy.id}).action_save_and_advance()
        self.assertEqual(order.stage_id, self.ready)
        self.assertEqual(order.painter_id, self.mandy)
        self.assertEqual(self._painter_payout(order).payout_id.contractor_id, self.mandy)

    def test_indigo_sheet_names_the_painter_and_the_4_rate(self):
        a = self._order(self.indigo_stage)
        a.painter_id = self.elio.id
        b = self._order(self.indigo_stage)
        b.painter_id = self.mandy.id
        orders = a | b
        info = orders._indigo_painter_sheet_info()
        self.assertEqual(info["shop_label"], "Indigo")
        self.assertEqual(info["single_rate"], 4.0)
        self.assertTrue(info["show_painter"])
        html, _fmt = self.env["ir.actions.report"]._render_qweb_html(
            "indigo_decors.action_report_painter_sheet", orders.ids
        )
        html = html.decode() if isinstance(html, bytes) else html
        # El titulo sale traducido segun el idioma ("Painter Sheet" en ingles).
        self.assertTrue("Hoja del Pintor" in html or "Painter Sheet" in html)
        for text in ("– Indigo", "Pintor", "Elio (test)", "Mandy (test)", "$4.00", "$160.00"):
            self.assertIn(text, html)
        self.assertNotIn("$8.00", html)
