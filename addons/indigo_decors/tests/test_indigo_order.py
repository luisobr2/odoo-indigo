# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
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
        cls.designer_user = cls.env["res.users"].create({
            "name": "Test Designer",
            "login": "test.designer.payout@test.local",
            "email": "test.designer.payout@test.local",
            "groups_id": [(6, 0, [cls.env.ref("indigo_decors.group_indigo_designer").id])],
        })

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
                    # SQF is manual, never derived from width x height (see
                    # indigo.order.line.sqf's help text) — set explicitly so
                    # tests exercise the real, current behaviour instead of
                    # the pre-manual-SQF assumption (36*80/144 = 20) that
                    # used to hold when SQF was computed from the frame.
                    "sqf": 20.0,
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
        # sqf=20.0 set explicitly on the test line (_create_order) — SQF is
        # manual (see indigo.order.line.sqf help text), NOT width*height/144.
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

    def test_hold_reason_list_is_seeded_for_both_causes(self):
        Reason = self.env["indigo.hold.reason"]
        self.assertTrue(Reason.search([("cause", "=", "dealer")]), "faltan motivos del dealer")
        self.assertTrue(Reason.search([("cause", "=", "client")]), "faltan motivos del cliente")

    def test_reason_and_cause_cannot_contradict_each_other(self):
        # "Faltan piezas" es del dealer. Guardarlo bajo "problema del cliente"
        # haria que el contador que Majela usa para saber a quien llamar
        # mienta -- y ese contador es el pedido entero.
        piezas = self.env.ref("indigo_decors.hold_reason_dealer_parts")
        order = self._create_order()
        with self.assertRaises(ValidationError):
            order.write({
                "on_hold": True, "hold_cause": "client",
                "hold_reason_id": piezas.id,
            })

    def test_matching_reason_and_cause_is_accepted(self):
        piezas = self.env.ref("indigo_decors.hold_reason_dealer_parts")
        order = self._create_order()
        order.write({
            "on_hold": True, "hold_cause": "dealer",
            "hold_reason_id": piezas.id,
        })
        self.assertEqual(order.hold_reason_id, piezas)

    def test_free_text_detail_survives_next_to_the_list(self):
        # Las ordenes viejas tienen el motivo como texto libre y no se puede
        # perder al introducir la lista.
        order = self._create_order()
        order.write({
            "on_hold": True, "hold_cause": "other",
            "hold_reason": "el vecino no deja pasar el camion",
        })
        self.assertEqual(order.hold_reason, "el vecino no deja pasar el camion")
        self.assertFalse(order.hold_reason_id)

    def test_no_painter_payout_when_a_piece_has_no_sqf(self):
        # `indigo.payout.line.quantity` es un float ALMACENADO, congelado al
        # crear la liquidacion, y `_create_painter_payout` tiene un guard que
        # impide crear una segunda para la misma orden. O sea: un payout
        # emitido en 0 no se puede arreglar nunca -- corregir line.sqf despues
        # no lo recalcula y el correcto ya no se puede generar. Por eso, si
        # falta SQF, NO se emite: se avisa en el chatter y la liquidacion
        # correcta todavia se puede generar cuando carguen el dato.
        order = self._create_order()
        order.line_ids.write({"sqf": 0.0})
        order.invalidate_recordset(["total_sqf", "total_painter_payout"])

        stage_painting = self.env.ref("indigo_decors.stage_painting")
        stage_ready_install = self.env.ref("indigo_decors.stage_ready_install")
        order.stage_id = stage_painting.id
        order.stage_id = stage_ready_install.id

        payouts = self.Payout.search([
            ("contractor_id", "=", self.painter.id),
            ("contractor_type", "=", "painter"),
        ])
        lines = self.env["indigo.payout.line"].search([("order_id", "=", order.id)])
        self.assertFalse(
            lines.filtered(lambda l: l.payout_id.contractor_type == "painter"),
            "No debe emitirse una liquidacion de pintor sin SQF: seria de $0 y permanente",
        )
        self.assertFalse(payouts.filtered(lambda p: order.name in (p.notes or "")))

        # Y tiene que quedar dicho en la orden, no solo en el log del servidor.
        cuerpos = " ".join(order.message_ids.mapped("body") or [])
        self.assertIn("SQF", cuerpos)

    def test_painter_payout_is_still_created_once_the_missing_sqf_is_entered(self):
        # La contracara del test anterior: negarse a emitir en 0 no puede
        # significar que la liquidacion se pierda para siempre.
        order = self._create_order()
        order.line_ids.write({"sqf": 0.0})
        stage_painting = self.env.ref("indigo_decors.stage_painting")
        stage_ready_install = self.env.ref("indigo_decors.stage_ready_install")
        order.stage_id = stage_painting.id
        order.stage_id = stage_ready_install.id  # no emite nada

        order.line_ids.write({"sqf": 20.0})
        order.invalidate_recordset(["total_sqf", "total_painter_payout"])
        order.stage_id = stage_painting.id
        order.stage_id = stage_ready_install.id  # ahora si

        lines = self.env["indigo.payout.line"].search([
            ("order_id", "=", order.id),
            ("payout_id.contractor_type", "=", "painter"),
        ])
        self.assertTrue(lines, "Con el SQF cargado, la liquidacion debe poder emitirse")
        self.assertEqual(sum(lines.mapped("quantity")), 20.0)

    def test_send_to_designer_refuses_from_an_unrelated_stage(self):
        # El paso final de action_send_to_designer mueve a CNC siempre que no
        # este ya ahi -- desde Pintura eso seria un RETROCESO, y salir de
        # Pintura es justo lo que dispara el pago al pintor.
        from odoo.exceptions import UserError

        order = self._create_order(designer_id=self.designer_user.id)
        order.stage_id = self.env.ref("indigo_decors.stage_painting").id
        with self.assertRaises(UserError):
            order.action_send_to_designer()
        self.assertEqual(
            order.stage_id, self.env.ref("indigo_decors.stage_painting"),
            "La orden no puede retroceder a CNC",
        )

    def test_painter_payout_correct_when_sqf_entered_at_cnc(self):
        # Majela's 2026-08-15 request moved SQF entry from Digitalization to
        # CNC (indigo.cnc.done.wizard). The painter payout fires on LEAVING
        # Painting, which is after CNC either way — but prove it rather than
        # reason about it: 120 real payouts already exist on this logic.
        order = self._create_order(line_ids=[
            (0, 0, {
                "design_id": self.design.id,
                "door_type": "SD",
                "color": "white",
                "width": 36.0,
                "height": 80.0,
                "qty": 1,
                "sqf": 0.0,  # not entered yet — order is still "in Digitalization"
            }),
        ])
        self.assertEqual(order.total_sqf, 0.0)

        # Send to the designer -> advances to CNC (mirrors the real flow;
        # SUPERUSER_ID in TransactionCase passes the office/manager/admin
        # role check via _is_admin()).
        order.designer_id = self.designer_user.id
        order.action_send_to_designer()
        self.assertEqual(order.stage_id, self.env.ref("indigo_decors.stage_cnc"))

        # SQF entered NOW, while the order sits in CNC (what
        # indigo.cnc.done.wizard's embedded line tree persists in practice).
        order.line_ids.write({"sqf": 20.0})
        order.invalidate_recordset(["total_sqf", "total_painter_payout"])
        self.assertEqual(order.total_sqf, 20.0)

        # Leaving Painting still creates the correct payout from the SQF
        # that was entered late (at CNC, not at Digitalization).
        stage_painting = self.env.ref("indigo_decors.stage_painting")
        stage_ready_install = self.env.ref("indigo_decors.stage_ready_install")
        order.stage_id = stage_painting.id
        order.stage_id = stage_ready_install.id
        payouts = self.Payout.search([
            ("contractor_id", "=", self.painter.id),
            ("contractor_type", "=", "painter"),
        ])
        self.assertEqual(len(payouts), 1, "Debe crear 1 payout de pintor")
        self.assertEqual(payouts.amount, 160.0, "20 SQF * $8, aunque el SQF se cargo en CNC")

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

    # ---------- hold_cause (Majela 2026-08-15, item 3: dealer vs cliente) ----------

    def test_on_hold_requires_cause_on_write(self):
        order = self._create_order()
        with self.assertRaises(ValidationError):
            order.write({"on_hold": True})

    def test_on_hold_requires_cause_on_create(self):
        with self.assertRaises(ValidationError):
            self._create_order(on_hold=True)

    def test_on_hold_with_cause_roundtrips_dealer(self):
        order = self._create_order()
        order.write({"on_hold": True, "hold_cause": "dealer"})
        order.invalidate_recordset(["on_hold", "hold_cause"])
        self.assertTrue(order.on_hold)
        self.assertEqual(order.hold_cause, "dealer")

    def test_on_hold_with_cause_roundtrips_client(self):
        order = self._create_order()
        order.write({"on_hold": True, "hold_cause": "client"})
        order.invalidate_recordset(["on_hold", "hold_cause"])
        self.assertTrue(order.on_hold)
        self.assertEqual(order.hold_cause, "client")

    def test_on_hold_with_cause_roundtrips_other(self):
        order = self._create_order()
        order.write({"on_hold": True, "hold_cause": "other"})
        order.invalidate_recordset(["on_hold", "hold_cause"])
        self.assertTrue(order.on_hold)
        self.assertEqual(order.hold_cause, "other")

    def test_releasing_hold_does_not_require_cause(self):
        # Clearing a hold (on_hold False) must never be blocked by the
        # cause check -- only SETTING a hold requires one.
        order = self._create_order()
        order.write({"on_hold": True, "hold_cause": "dealer"})
        order.write({"on_hold": False})
        order.invalidate_recordset(["on_hold"])
        self.assertFalse(order.on_hold)

    def test_hold_cause_can_be_set_without_on_hold(self):
        # A stale/leftover hold_cause with on_hold False is not itself an
        # error -- the constraint only fires when on_hold is True.
        order = self._create_order()
        order.write({"hold_cause": "other"})
        self.assertFalse(order.on_hold)
