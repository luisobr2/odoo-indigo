# -*- coding: utf-8 -*-
"""Notas del equipo con Anota: interruptor y clave en Settings (21-oct-2026)."""
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("indigo", "post_install", "-at_install")
class TestIndigoAnotaSettings(TransactionCase):
    def setUp(self):
        super().setUp()
        icp = self.env["ir.config_parameter"].sudo()
        for k in ("anota_enabled", "anota_project_key", "anota_url"):
            icp.set_param("indigo_decors." + k, "")
        self.P = self.env["ir.config_parameter"]

    def _user(self, groups, share=False):
        return self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Anota %s" % groups, "login": "anota_%s@test.local" % "_".join(groups).replace(".", "_"),
            "groups_id": [(6, 0, [self.env.ref(g).id for g in groups])],
        })

    def test_off_by_default_with_the_default_url(self):
        res = self.P.indigo_get_anota()
        self.assertFalse(res["enabled"])
        self.assertEqual(res["url"], "https://anota.lbencomo94.workers.dev")

    def test_turn_on_needs_a_valid_key(self):
        with self.assertRaises(ValidationError):
            self.P.indigo_set_anota({"enabled": True})
        with self.assertRaises(ValidationError):
            self.P.indigo_set_anota({"project_key": "<script>"})
        res = self.P.indigo_set_anota({"project_key": "pk_G8zrVRXvrMjTuxv9UH3czPGv", "enabled": True})
        self.assertTrue(res["enabled"])
        self.assertEqual(res["project_key"], "pk_G8zrVRXvrMjTuxv9UH3czPGv")
        self.assertFalse(self.P.indigo_set_anota({"enabled": False})["enabled"])

    def test_staff_read_it_dealers_do_not_and_only_office_changes_it(self):
        self.P.indigo_set_anota({"project_key": "pk_G8zrVRXvrMjTuxv9UH3czPGv", "enabled": True})
        painter = self._user(["base.group_user", "indigo_decors.group_indigo_cnc"])
        self.assertTrue(self.P.with_user(painter).indigo_get_anota()["enabled"])
        with self.assertRaises(AccessError):
            self.P.with_user(painter).indigo_set_anota({"enabled": False})
        dealer = self._user(["base.group_portal"])
        self.assertFalse(self.P.with_user(dealer).indigo_get_anota()["enabled"])
