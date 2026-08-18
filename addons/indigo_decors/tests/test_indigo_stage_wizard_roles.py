# -*- coding: utf-8 -*-
"""Server-side role backstops on the five stage-advance wizards.

(A sixth, `indigo.sqf.entry.wizard`, existed here too until Majela's
2026-08-15 request removed per-line SQF entry from Digitalization --
that stage now advances via `indigo.order.action_send_to_designer()`
instead, which is not a wizard and has its own role check; see
`models/indigo_order.py`.)

`ir.model.access.csv` grants full r/w/c/u on every `indigo.*.wizard` model
to `group_indigo_user` -- the base group every internal role (Designer,
CNC, Painter, Office, Installer-internal, Manager) implies -- and
`action_save_and_advance` writes the order via `sudo()`, which bypasses
record rules too. Before the role checks added in
`wizards/indigo_stage_wizards.py` and
`wizards/indigo_measurement_entry_wizard.py`, the Next.js panel's own role
gate (`orders/[id]/advance/route.ts`) was the ONLY thing standing between a
caller and driving any order through any stage -- and even there, four of
the wizards weren't panel-gated at all. These tests prove each wizard now
refuses a role that shouldn't reach it and still allows one that should,
independent of the panel.
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
                    # El SQF se carga a mano en CNC y es la base del pago al
                    # pintor; indigo.cnc.done.wizard ahora se niega a avanzar
                    # sin el. Los tests de ROL de este archivo no son sobre
                    # eso, asi que arrancan con el dato ya puesto.
                    "sqf": 20.0,
                }),
            ],
        }
        vals.update(overrides)
        return self.Order.create(vals)

    # ---------- measurement entry: installer / office / manager ----------
    def test_measurement_entry_requires_installer_office_or_manager(self):
        order = self._create_order()
        Wizard = self.env["indigo.measurement.entry.wizard"]

        # CNC has no business role here -> refused.
        wiz = Wizard.with_user(self.cnc).create({"order_id": order.id})
        with self.assertRaises(AccessError):
            wiz.action_save_and_advance()

        wiz2 = Wizard.with_user(self.office).create({"order_id": order.id})
        wiz2.action_save_and_advance()
        self.assertEqual(order.stage_id, self.env.ref("indigo_decors.stage_measured"))

    def test_measurement_entry_allows_any_internal_installer(self):
        # Measuring (Javier's job, per CLAUDE.md) typically happens before
        # an installer is assigned to the order at all -- unlike
        # indigo.installed.wizard, ANY internal installer may enter
        # measurements, not just one already listed in installer_ids.
        order = self._create_order(installer_ids=[(6, 0, [])])
        self.assertFalse(order.installer_ids)
        Wizard = self.env["indigo.measurement.entry.wizard"]
        wiz = Wizard.with_user(self.installer_unassigned).create({"order_id": order.id})
        wiz.action_save_and_advance()
        self.assertEqual(order.stage_id, self.env.ref("indigo_decors.stage_measured"))

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

    def test_cnc_done_allows_the_designer_who_holds_the_sqf(self):
        # El SQF sale del plugin de CorelDraw del disenador. Cuando la carga
        # paso de Digitalizacion a CNC, quedo en una pantalla que el
        # disenador no podia cerrar -- y desde el panel eso era lo peor de
        # los dos mundos: su escritura de SQF se guardaba y despues se le
        # negaba el avance.
        order = self._create_order()
        wiz = self.env["indigo.cnc.done.wizard"].with_user(self.designer).create(
            {"order_id": order.id}
        )
        wiz.action_save_and_advance()
        self.assertEqual(order.stage_id, self.env.ref("indigo_decors.stage_painting"))

    def test_cnc_done_refuses_to_advance_without_sqf(self):
        # Sin SQF el pintor se liquida en $0 y, por el guard de deduplicacion
        # de _create_painter_payout, esa liquidacion no se puede corregir
        # despues. CNC es el ultimo momento en que la pieza esta delante.
        from odoo.exceptions import UserError

        order = self._create_order()
        order.line_ids.write({"sqf": 0.0})
        wiz = self.env["indigo.cnc.done.wizard"].with_user(self.cnc).create(
            {"order_id": order.id}
        )
        with self.assertRaises(UserError):
            wiz.action_save_and_advance()
        self.assertNotEqual(
            order.stage_id, self.env.ref("indigo_decors.stage_painting"),
            "La orden no debe llegar a Pintura sin SQF",
        )

    def test_only_sqf_holders_can_write_sqf(self):
        # Las ACL de Odoo son por modelo, no por campo: ir.model.access.csv da
        # write sobre indigo.order.line a group_indigo_user, que TODO rol
        # interno implica, y la record rule del pintor lo alcanza justo en
        # Pintura -- la etapa cuya salida calcula su propio pago. El check de
        # rol del wizard no lo cubre, porque el dialogo de Odoo guarda las
        # lineas en un RPC anterior al del boton.
        order = self._create_order()
        # La record rule del operador CNC lo limita a ordenes en su etapa, asi
        # que para probar el limite POR CAMPO hay que ponerlo en su alcance --
        # si no, lo que se estaria probando es la rule, no el override.
        order.stage_id = self.env.ref("indigo_decors.stage_cnc").id
        with self.assertRaises(AccessError):
            order.line_ids.with_user(self.painter).write({"sqf": 999.0})
        self.assertEqual(order.line_ids[0].sqf, 20.0, "El SQF no debe haber cambiado")

        # Y quien si lo tiene, puede.
        order.line_ids.with_user(self.cnc).write({"sqf": 21.0})
        self.assertEqual(order.line_ids[0].sqf, 21.0)

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
