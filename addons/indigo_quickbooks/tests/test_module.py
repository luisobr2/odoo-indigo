# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged("indigo", "post_install", "-at_install")
class TestQboModule(TransactionCase):
    def test_module_installed(self):
        mod = self.env["ir.module.module"].search([("name", "=", "indigo_quickbooks")])
        self.assertEqual(mod.state, "installed")
