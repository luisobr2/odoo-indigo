# -*- coding: utf-8 -*-
"""El gestor de bases de datos no se puede usar desde internet (25-nov-2026)."""
import json

from odoo.tools import config
from odoo.tests import HttpCase, tagged


@tagged("indigo", "post_install", "-at_install")
class TestIndigoDatabaseLock(HttpCase):
    def _rpc_db(self, method, args):
        res = self.url_open(
            "/jsonrpc",
            data=json.dumps({"jsonrpc": "2.0", "method": "call", "id": 1,
                             "params": {"service": "db", "method": method, "args": args}}),
            headers={"Content-Type": "application/json"},
        )
        return res.json()

    def test_database_manager_routes_answer_404(self):
        for path in ("backup", "restore", "drop", "duplicate", "create", "change_password"):
            res = self.url_open("/web/database/%s" % path, data={"master_pwd": config["admin_passwd"], "name": "x"})
            self.assertEqual(res.status_code, 404, path)
        for path in ("manager", "selector"):
            self.assertEqual(self.url_open("/web/database/%s" % path).status_code, 404, path)

    def test_rpc_refuses_dump_and_drop_but_answers_the_version(self):
        # Con la contrasena maestra BUENA: sin el cierre, el dump funcionaria.
        good = config["admin_passwd"]
        for method, args in (("dump", [good, self.env.cr.dbname, "zip"]),
                             ("drop", [good, "indigo-no-such-db"]),
                             ("change_admin_password", [good, good])):
            body = self._rpc_db(method, args)
            self.assertIn("error", body, method)
            self.assertIn("AccessDenied", json.dumps(body["error"]), method)
        self.assertIn("result", self._rpc_db("server_version", []))
