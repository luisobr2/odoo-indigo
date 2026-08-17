# -*- coding: utf-8 -*-
"""Tests for indigo.order.action_send_to_designer -- Majela's 2026-08-15
Digitalization redesign (see docs/majela/audio-1-digitalizacion.md).

Before this action existed, nothing was recorded when she handed the
Ficha de orden ("the PDF") to the designer, so Digitalization mixed orders
that already had it with ones that didn't -- indistinguishable, which is
how a stale order slipped past her onto a second page. These tests prove
the new action makes the STAGE the answer (still in Digitalization = not
sent; in CNC = sent), and that it fails the way she'd expect (clear
Spanish errors, no silent no-ops).
"""
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "indigo_send_to_designer")
class TestIndigoSendToDesigner(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.Users = cls.env["res.users"]
        cls.Order = cls.env["indigo.order"]
        cls.Design = cls.env["indigo.design"]
        cls.Attachment = cls.env["ir.attachment"]
        cls.Mail = cls.env["mail.mail"]

        cls.dealer = cls.Partner.create({
            "name": "Send To Designer Test Dealer",
            "is_company": True,
            "is_indigo_dealer": True,
            "indigo_default_price_per_sqf": 15.0,
            "email": "s2d.dealer@test.example",
        })
        cls.design = cls.Design.create({
            "code": "S2DTEST-SD", "name": "Send2Designer Test Single", "door_type": "SD",
        })

        def _mk(login, group_xmlid, email=True):
            vals = {
                "name": login,
                "login": login,
                # res.users.email does NOT auto-populate from login on
                # create() — pass it explicitly (or the designer would
                # always look "email-less" to action_send_to_designer).
                "email": login if email else False,
                "groups_id": [(6, 0, [cls.env.ref(group_xmlid).id])],
            }
            return cls.Users.create(vals)

        cls.designer = _mk("s2d.designer@test.local", "indigo_decors.group_indigo_designer")
        cls.designer_no_email = _mk(
            "s2d.designer.noemail@test.local", "indigo_decors.group_indigo_designer", email=False
        )
        cls.office = _mk("s2d.office@test.local", "indigo_decors.group_indigo_office")
        cls.manager = _mk("s2d.manager@test.local", "indigo_decors.group_indigo_manager")
        cls.painter_user = _mk("s2d.painter@test.local", "indigo_decors.group_indigo_painter_op")

    def _create_order(self, **overrides):
        vals = {
            "dealer_id": self.dealer.id,
            "client_name": "Send To Designer Test Client",
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

    # ---------- Refuses clearly ----------

    def test_refuses_without_designer(self):
        order = self._create_order()
        self.assertFalse(order.designer_id)
        with self.assertRaises(UserError):
            order.action_send_to_designer()
        # No side effects on a refusal: no attachment, no stage change.
        self.assertFalse(order.design_sent_date)

    def test_refuses_designer_without_email(self):
        order = self._create_order(designer_id=self.designer_no_email.id)
        with self.assertRaises(UserError):
            order.action_send_to_designer()

    # ---------- Role check: her action, not the designer's ----------

    def test_role_check_denies_painter(self):
        order = self._create_order(designer_id=self.designer.id)
        with self.assertRaises(AccessError):
            order.with_user(self.painter_user).action_send_to_designer()

    def test_role_check_allows_office_and_manager(self):
        order1 = self._create_order(designer_id=self.designer.id)
        order1.with_user(self.office).action_send_to_designer()
        self.assertEqual(order1.stage_id, self.env.ref("indigo_decors.stage_cnc"))

        order2 = self._create_order(designer_id=self.designer.id)
        order2.with_user(self.manager).action_send_to_designer()
        self.assertEqual(order2.stage_id, self.env.ref("indigo_decors.stage_cnc"))

    # ---------- Happy path ----------

    def test_send_creates_attachment_emails_and_advances_stage(self):
        order = self._create_order(designer_id=self.designer.id)
        before_attachments = self.Attachment.search_count([
            ("res_model", "=", "indigo.order"), ("res_id", "=", order.id),
        ])

        order.with_user(self.office).action_send_to_designer()

        # Attachment saved on the order.
        attachments = self.Attachment.search([
            ("res_model", "=", "indigo.order"), ("res_id", "=", order.id),
        ])
        self.assertEqual(len(attachments), before_attachments + 1)
        self.assertTrue(attachments[-1].datas, "El PDF debe tener contenido")

        # Email queued to the designer (mail.mail persists: auto_delete=False
        # on the template) -- doesn't require an actual SMTP server to exist.
        mails = self.Mail.search([
            ("model", "=", "indigo.order"), ("res_id", "=", order.id),
        ])
        self.assertTrue(mails, "Debe quedar un mail.mail en cola para el disenador")
        self.assertIn(self.designer.email, mails[0].email_to or "")

        # Sent-date + sender recorded, stage advanced.
        self.assertTrue(order.design_sent_date)
        self.assertEqual(order.design_sent_uid, self.office)
        self.assertEqual(order.stage_id, self.env.ref("indigo_decors.stage_cnc"))

    def test_resend_updates_timestamp_but_does_not_revert_stage(self):
        # She may genuinely need to re-send (the designer lost the PDF).
        # Resending must never duplicate a stage transition or get stuck.
        order = self._create_order(designer_id=self.designer.id)
        order.with_user(self.office).action_send_to_designer()
        first_sent = order.design_sent_date
        stage_cnc = self.env.ref("indigo_decors.stage_cnc")
        self.assertEqual(order.stage_id, stage_cnc)

        order.with_user(self.manager).action_send_to_designer()
        self.assertEqual(order.stage_id, stage_cnc, "Un reenvio no debe mover la etapa de nuevo")
        self.assertGreaterEqual(order.design_sent_date, first_sent)
        self.assertEqual(order.design_sent_uid, self.manager, "El reenvio registra quien lo hizo")

        attachments = self.Attachment.search_count([
            ("res_model", "=", "indigo.order"), ("res_id", "=", order.id),
        ])
        self.assertEqual(attachments, 2, "Cada envio deja su propia Ficha adjunta")
