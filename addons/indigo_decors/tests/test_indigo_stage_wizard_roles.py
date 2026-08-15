# -*- coding: utf-8 -*-
"""Server-side role backstops on the six stage-advance wizards.

`ir.model.access.csv` grants full r/w/c/u on every `indigo.*.wizard` model
to `group_indigo_user` -- the base group every internal role (Designer,
CNC, Painter, Office, Installer-internal, Manager) implies -- and
`action_save_and_advance` writes the order via `sudo()`, which bypasses
record rules too. Before the role checks added in
`wizards/indigo_stage_wizards.py` and
`wizards/indigo_measurement_entry_wizard.py`, the Next.js panel's own role
gate (`orders/[id]/advance/route.ts`) was the ONLY thing standing between a
caller and driving any order through any stage -- and even there, four of
the six wizards weren't panel-gated at all. These tests prove each wizard
now refuses a role that shouldn't reach it and still allows one that
should, independent of the panel.
"""
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "indigo_wizard_roles")
class TestIndigoStageWizardRoles(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.Users = cls.env["res.users"]
        cls.Order = cls.env["indigo.order"]
        cls.Design = cls.env["indigo.design"]

        cls.dealer = cls.Partner.create({
            "name": "Wizard Role Test Dealer",
            "is_company": True,
            "is_indigo_dealer": True,
            "indigo_default_price_per_sqf": 15.0,
            "email": "wizardroledealer@test.example",
        })
        cls.design = cls.Design.create({
            "code": "WZTEST-SD", "name": "Wizard Test Single", "door_type": "SD",
        })
        cls.painter_partner = cls.Partner.create({"name": "Wizard Test Painter"})
        cls.installer_partner = cls.Partner.create({"name": "Wizard Test Installer"})
        cls.other_installer_partner = cls.Partner.create({"name": "Wizard Test Other Installer"})

        def _mk(login, group_xmlid, partner=None):
            vals = {
                "name": login,
                "login": login,
                "groups_id": [(6, 0, [cls.env.ref(group_xmlid).id])],
            }
            if partner is not None:
                vals["partner_id"] = partner.id
            return cls.Users.create(vals)

        cls.manager = _mk("wztest.manager@test.local", "indigo_decors.group_indigo_manager")
        cls.office = _mk("wztest.office@test.local", "indigo_decors.group_indigo_office")
        cls.designer = _mk("wztest.designer@test.local", "indigo_decors.group_indigo_designer")
        cls.cnc = _mk("wztest.cnc@test.local", "indigo_decors.group_indigo_cnc")
        cls.painter = _mk("wztest.painter@test.local", "indigo_decors.group_indigo_painter_op")
        # Two internal installers so we can prove assignment (not just group
        # membership) gates the installed wizard.
        cls.installer_assigned = _mk(
            "wztest.installer.assigned@test.local",
            "indigo_decors.group_indigo_installer_internal",
            partner=cls.installer_partner,
        )
        cls.installer_unassigned = _mk(
            "wztest.installer.unassigned@test.local",
            "indigo_decors.group_indigo_installer_internal",
            partner=cls.other_installer_partner,
        )

    def _create_order(self, **overrides):
        vals = {
            "dealer_id": self.dealer.id,
            "client_name": "Wizard Role Test Client",
            "painter_id": self.painter_partner.id,
            "installer_ids": [(6, 0, [self.installer_partner.id])],
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

    # ---------- measurement entry: office/manager only ----------
    def test_measurement_entry_requires_office_or_manager(self):
        order = self._create_order()
        Wizard = self.env["indigo.measurement.entry.wizard"]

        wiz = Wizard.with_user(self.cnc).create({"order_id": order.id})
        with self.assertRaises(AccessError):
            wiz.action_save_and_advance()

        wiz2 = Wizard.with_user(self.office).create({"order_id": order.id})
        wiz2.action_save_and_advance()
        self.assertEqual(order.stage_id, self.env.ref("indigo_decors.stage_measured"))

    # ---------- sqf entry: office/manager only ----------
    def test_sqf_entry_requires_office_or_manager(self):
        order = self._create_order()
        Wizard = self.env["indigo.sqf.entry.wizard"]

        wiz = Wizard.with_user(self.designer).create({"order_id": order.id})
        with self.assertRaises(AccessError):
            wiz.action_save_and_advance()

        wiz2 = Wizard.with_user(self.manager).create({"order_id": order.id})
        wiz2.action_save_and_advance()
        self.assertEqual(order.stage_id, self.env.ref("indigo_decors.stage_cnc"))

    # ---------- cnc done: cnc / office / manager ----------
    def test_cnc_done_requires_cnc_office_or_manager(self):
        order = self._create_order()
        Wizard = self.env["indigo.cnc.done.wizard"]

        wiz = Wizard.with_user(self.painter).create({"order_id": order.id})
        with self.assertRaises(AccessError):
            wiz.action_save_and_advance()

        wiz2 = Wizard.with_user(self.cnc).create({"order_id": order.id})
        wiz2.action_save_and_advance()
        self.assertEqual(order.stage_id, self.env.ref("indigo_decors.stage_painting"))

    # ---------- painter done: painter / office / manager ----------
    def test_painter_done_requires_painter_office_or_manager(self):
        order = self._create_order()
        Wizard = self.env["indigo.painter.done.wizard"]

        wiz = Wizard.with_user(self.cnc).create({"order_id": order.id})
        with self.assertRaises(AccessError):
            wiz.action_save_and_advance()

        wiz2 = Wizard.with_user(self.painter).create({"order_id": order.id})
        wiz2.action_save_and_advance()
        self.assertEqual(order.stage_id, self.env.ref("indigo_decors.stage_ready_install"))

    # ---------- installed: assigned installer / office / manager ----------
    def test_installed_requires_assignment_or_office_manager(self):
        order = self._create_order()
        Wizard = self.env["indigo.installed.wizard"]

        # No role match at all -> refused outright.
        wiz_designer = Wizard.with_user(self.designer).create({"order_id": order.id})
        with self.assertRaises(AccessError):
            wiz_designer.action_save_and_advance()

        # An internal installer who IS NOT assigned to this order -> refused,
        # even though they hold the installer group.
        wiz_unassigned = Wizard.with_user(self.installer_unassigned).create({"order_id": order.id})
        with self.assertRaises(AccessError):
            wiz_unassigned.action_save_and_advance()

        # The installer actually assigned to the order (installer_ids) may
        # close their own installation -- the one case the panel already
        # allowed (orders/[id]/advance/route.ts) that must keep working.
        wiz_assigned = Wizard.with_user(self.installer_assigned).create({"order_id": order.id})
        wiz_assigned.action_save_and_advance()
        self.assertEqual(order.stage_id, self.env.ref("indigo_decors.stage_installed"))

    def test_installed_office_and_manager_can_close_any_order(self):
        # Assigned installer is someone else entirely -- office/manager must
        # still be able to close it (mirrors panel's "privileged" branch).
        order = self._create_order(installer_ids=[(6, 0, [self.other_installer_partner.id])])
        Wizard = self.env["indigo.installed.wizard"]

        wiz = Wizard.with_user(self.office).create({"order_id": order.id})
        wiz.action_save_and_advance()
        self.assertEqual(order.stage_id, self.env.ref("indigo_decors.stage_installed"))

    # ---------- invoiced/paid: the money one -- office/manager ONLY ----------
    def test_invoiced_paid_requires_office_or_manager(self):
        order = self._create_order()
        Wizard = self.env["indigo.invoiced.paid.wizard"]

        # Every non office/manager role is refused, including the installer
        # actually assigned to the order -- this is deliberately stricter
        # than "installed" above.
        for role_user in (self.designer, self.cnc, self.painter, self.installer_assigned):
            wiz = Wizard.with_user(role_user).create({
                "order_id": order.id,
                "amount_collected": 100.0,
                "payment_state": "paid",
            })
            with self.assertRaises(AccessError):
                wiz.action_save_and_advance()

        wiz2 = Wizard.with_user(self.manager).create({
            "order_id": order.id,
            "amount_collected": 100.0,
            "payment_state": "paid",
        })
        wiz2.action_save_and_advance()
        self.assertEqual(order.stage_id, self.env.ref("indigo_decors.stage_invoiced"))
