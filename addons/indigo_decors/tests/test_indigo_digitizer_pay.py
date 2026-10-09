# -*- coding: utf-8 -*-
"""Digitalizacion fuera de horario (Majela, 9-oct-2026).

    "Cuando ponga Amado, ve que Amado lo hizo en horario no laboral y le
     vas a cargar $7.50. Y cuando ponga Indigo o Elio, no le cargas nada."

Quien digitalizo es el disenador de la orden. Cobra solo quien tiene una
regla de "Digitalizacion" en Settings, por puerta.
"""
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("indigo", "post_install", "-at_install")
class TestDigitizerPay(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        designer_group = cls.env.ref("indigo_decors.group_indigo_designer")
        Users = cls.env["res.users"].with_context(no_reset_password=True)
        cls.amado = Users.create({
            "name": "Amado Digit", "login": "amado_digit@test.local", "email": "amado_digit@test.local",
            "groups_id": [(6, 0, [cls.env.ref("base.group_user").id, designer_group.id])],
        })
        cls.inhouse = Users.create({
            "name": "Indigo Digit", "login": "indigo_digit@test.local", "email": "indigo_digit@test.local",
            "groups_id": [(6, 0, [cls.env.ref("base.group_user").id, designer_group.id])],
        })
        cls.rule = cls.env["indigo.contractor.rate"].create({
            "name": "Amado Digit", "contractor_type": "digitizer", "partner_id": cls.amado.partner_id.id,
            "rate": 7.5, "rate_unit": "piece",
        })
        cls.dealer = cls.env["res.partner"].create({"name": "Digit Dealer", "is_company": True, "is_indigo_dealer": True})
        cls.design = cls.env["indigo.design"].create({"code": "DIGIT-SD", "name": "Digit SD", "door_type": "SD"})

    def _order(self, doors=2, **vals):
        return self.env["indigo.order"].create(dict({
            "dealer_id": self.dealer.id, "client_name": "Digit Client",
            "line_ids": [(0, 0, {"design_id": self.design.id, "door_type": "SD", "color": "white", "qty": 1, "sqf": 20.0})
                         for _i in range(doors)],
        }, **vals))

    def _lines(self, order):
        return self.env["indigo.payout.line"].search([
            ("order_id", "=", order.id), ("payout_id.contractor_type", "=", "digitizer"),
            ("payout_id.state", "!=", "cancel"),
        ])

    def test_amado_is_paid_per_door(self):
        order = self._order(doors=2)
        order.designer_id = self.amado
        line = self._lines(order)
        self.assertEqual(len(line), 1)
        self.assertEqual((line.quantity, line.rate, line.amount), (order.door_count, 7.5, 7.5 * order.door_count))
        self.assertEqual(line.payout_id.contractor_id, self.amado.partner_id)
        self.assertEqual(line.payout_id.work_date, fields.Date.context_today(order))

    def test_in_house_designer_is_not_paid(self):
        order = self._order()
        order.designer_id = self.inhouse
        self.assertFalse(self._lines(order))

    def test_changing_the_designer_moves_the_pay(self):
        order = self._order()
        order.designer_id = self.amado
        payout = self._lines(order).payout_id
        order.designer_id = self.inhouse
        self.assertFalse(self._lines(order))
        self.assertFalse(payout.exists())  # liquidacion vacia: se borra
        order.designer_id = self.amado
        self.assertEqual(len(self._lines(order)), 1)

    def test_setting_it_twice_pays_once(self):
        order = self._order()
        order.designer_id = self.amado
        order.write({"designer_id": self.amado.id})
        self.assertEqual(len(self._lines(order)), 1)

    def test_one_payout_per_day_with_one_line_per_order(self):
        a, b = self._order(), self._order(doors=1)
        (a | b).write({"designer_id": self.amado.id})
        lines = self._lines(a) | self._lines(b)
        self.assertEqual(len(lines.payout_id), 1)

    def test_cancelling_the_order_removes_it(self):
        order = self._order()
        order.designer_id = self.amado
        order.cancelled_at = fields.Datetime.now()
        self.assertFalse(self._lines(order))

    def test_already_paid_is_not_touched(self):
        order = self._order()
        order.designer_id = self.amado
        line = self._lines(order)
        line.payout_id.action_mark_paid()
        order.designer_id = self.inhouse
        self.assertTrue(line.exists())
        self.assertIn("ya se le liquido", order.message_ids[:1].body)

    def test_more_doors_update_the_draft_line(self):
        order = self._order(doors=1)
        order.designer_id = self.amado
        order.write({"line_ids": [(0, 0, {"design_id": self.design.id, "door_type": "SD", "color": "white", "qty": 1, "sqf": 10.0})]})
        self.assertEqual(self._lines(order).quantity, order.door_count)

    def test_rule_needs_a_person_and_per_door(self):
        with self.assertRaises(ValidationError):
            self.env["indigo.contractor.rate"].create({
                "name": "x", "contractor_type": "digitizer", "rate": 5, "rate_unit": "piece"})
        with self.assertRaises(ValidationError):
            self.env["indigo.contractor.rate"].create({
                "name": "y", "contractor_type": "digitizer", "partner_id": self.inhouse.partner_id.id,
                "rate": 5, "rate_unit": "sqf"})
