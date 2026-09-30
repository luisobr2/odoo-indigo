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


class _PaintCase(TransactionCase):
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


@tagged("indigo", "post_install", "-at_install")
class TestIndigoPaintStages(_PaintCase):

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
        with self.assertRaises(UserError):  # quien no pinta en Indigo, ni asignarlo
            order.painter_id = self.outsider.id
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


@tagged("indigo", "post_install", "-at_install")
class TestIndigoPaintStagesAudit(_PaintCase):
    """Lo que encontro la auditoria antes de desplegar (2026-09-30)."""

    def _paid(self, order):
        return [(l.payout_id.contractor_id.name, l.rate) for l in self._painter_payout(order)]

    def test_one_painter_payout_per_order(self):
        # Pintada por Elio y pagada; vuelve a Michel y avanza otra vez: no se
        # le paga tambien a Michel, y el pintor sigue siendo Elio.
        order = self._order(self.indigo_stage)
        order.painter_id = self.elio.id
        order.stage_id = self.ready.id
        order.stage_id = self.michel_stage.id
        self.assertEqual(order.painter_id, self.elio, "ya se le pago a Elio: no se toca")
        order.stage_id = self.ready.id
        self.assertEqual(self._paid(order), [("Elio (test)", 4.0)])

    def test_cancelled_order_closed_from_paint_pays_nobody(self):
        order = self._order(self.michel_stage)
        order.cancelled_at = "2026-09-30 10:00:00"
        order.stage_id = self.env.ref("indigo_decors.stage_closed").id
        self.assertFalse(self._painter_payout(order))
        other = self._order(self.indigo_stage)  # sin pintor, cancelada: se puede cerrar
        other.cancelled_at = "2026-09-30 10:00:00"
        other.stage_id = self.env.ref("indigo_decors.stage_closed").id
        self.assertFalse(self._painter_payout(other))

    def test_old_door_in_michel_without_painter_is_paid_to_michel(self):
        # Una puerta que ya estaba en "painting" antes de las dos etapas no
        # "entro" nunca: al salir hacia instalacion la pinto Michel.
        order = self._order()
        self.env.flush_all()  # si no, el cambio pendiente a CNC se escribe despues del UPDATE
        self.env.cr.execute("UPDATE indigo_order SET stage_id = %s, painter_id = NULL WHERE id = %s",
                            (self.michel_stage.id, order.id))
        order.invalidate_recordset()
        order.stage_id = self.ready.id
        self.assertEqual(order.painter_id, self.michel)
        self.assertEqual(self._paid(order), [("Michel (test)", 8.0)])

    def test_painter_must_belong_to_the_stage(self):
        order = self._order(self.indigo_stage)
        with self.assertRaises(UserError):
            order.painter_id = self.michel.id
        michel_order = self._order(self.michel_stage)
        with self.assertRaises(UserError):
            michel_order.painter_id = self.elio.id
        # Etapa y pintor en la misma escritura: se respeta, y se valida.
        other = self._order()
        other.write({"stage_id": self.indigo_stage.id, "painter_id": self.mandy.id})
        self.assertEqual(other.painter_id, self.mandy)
        with self.assertRaises(UserError):
            self._order().write({"stage_id": self.michel_stage.id, "painter_id": self.elio.id})

    def test_clearing_the_painter_on_the_way_out_is_refused(self):
        order = self._order(self.indigo_stage)
        order.painter_id = self.elio.id
        with self.assertRaises(UserError):
            order.write({"stage_id": self.ready.id, "painter_id": False})

    def test_cnc_asks_for_sqf_when_the_shop_has_painters(self):
        order = self._order()
        order.line_ids.write({"sqf": 0.0})
        wiz = self.env["indigo.cnc.done.wizard"].create({"order_id": order.id, "paint_stage": "indigo"})
        with self.assertRaises(UserError):
            wiz.action_save_and_advance()
        self.assertEqual(order.stage_id, self.stage_cnc)

    def test_painted_wizard_uses_the_chosen_painter_in_michel_too(self):
        order = self._order(self.michel_stage)
        Wizard = self.env["indigo.painter.done.wizard"]
        with self.assertRaises(UserError):
            Wizard.create({"order_id": order.id, "painter_id": self.elio.id}).action_save_and_advance()
        Wizard.create({"order_id": order.id, "painter_id": self.michel.id}).action_save_and_advance()
        self.assertEqual(self._paid(order), [("Michel (test)", 8.0)])

    def test_unknown_indigo_rate_is_not_printed_as_8(self):
        order = self._order(self.indigo_stage)
        self.assertEqual(order._indigo_expected_paint_rate(), 4.0, "Elio y Mandy cobran igual")
        self.env["indigo.contractor.rate"].search([("partner_id", "=", self.mandy.id)]).rate = 5.0
        self.assertIsNone(order._indigo_expected_paint_rate())
        info = order._indigo_painter_sheet_info()
        self.assertIsNone(info["rates"][order.id])
        self.assertFalse(info["single_rate"])
        html, _fmt = self.env["ir.actions.report"]._render_qweb_html(
            "indigo_decors.action_report_painter_sheet", order.ids
        )
        html = html.decode() if isinstance(html, bytes) else html
        self.assertNotIn("$8.00", html)
        self.assertIn("—", html)

    def test_portal_cannot_read_the_painters(self):
        from odoo.exceptions import AccessError
        portal = self.env["res.users"].create({
            "name": "Portal painter probe", "login": "portal.paint.probe@test",
            "groups_id": [(6, 0, [self.env.ref("base.group_portal").id])],
        })
        with self.assertRaises(AccessError):
            self.Order.with_user(portal).indigo_painters_list()

    def test_designer_can_still_send_cnc_to_michel(self):
        designer = self.env["res.users"].create({
            "name": "Designer paint probe", "login": "designer.paint.probe@test",
            "groups_id": [(6, 0, [self.env.ref("indigo_decors.group_indigo_designer").id])],
        })
        order = self._order()
        order.with_user(designer).write({"stage_id": self.michel_stage.id})
        self.assertEqual(order.painter_id, self.michel)

    def test_setup_leaves_a_customised_rule_alone(self):
        rule = self.env.ref("indigo_decors.rule_indigo_order_painter")
        rule.domain_force = "[('stage_id.code', 'in', ['painting', 'painting_indigo', 'cnc'])]"
        self.env["indigo.stage"]._indigo_setup_paint_stages()
        self.assertIn("'cnc'", rule.domain_force)

