# -*- coding: utf-8 -*-
"""Registro de actividad (18-nov-2026)."""
import json

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged


@tagged("indigo", "post_install", "-at_install")
class TestIndigoAudit(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Users = cls.env["res.users"].with_context(no_reset_password=True)

        def user(name, group):
            return Users.create({
                "name": name, "login": "%s@audit.test" % name.lower().replace(" ", "."),
                "email": "%s@audit.test" % name.lower().replace(" ", "."),
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id, cls.env.ref(group).id])],
            })

        cls.manager = user("Audit Manager", "indigo_decors.group_indigo_manager")
        cls.office = user("Audit Office", "indigo_decors.group_indigo_office")
        cls.dealer = cls.env["res.partner"].create({"name": "Audit Dealer", "is_indigo_dealer": True})
        cls.design = cls.env["indigo.design"].create({"code": "AUDIT-SD", "name": "Audit Single", "door_type": "SD"})
        cls.Log = cls.env["indigo.audit.log"].sudo()

    def _order(self, env_user=None):
        Order = self.env["indigo.order"]
        if env_user:
            Order = Order.with_user(env_user)
        return Order.create({
            "dealer_id": self.dealer.id,
            "client_name": "Zed Quillon",
            "line_ids": [(0, 0, {"design_id": self.design.id, "door_type": "SD", "color": "white", "qty": 1, "sqf": 20.0})],
        })

    def _rows(self, record, **extra):
        domain = [("res_model", "=", record._name), ("res_id", "=", record.id)]
        domain += [(k, "=", v) for k, v in extra.items()]
        return self.Log.search(domain)

    # ------------------------------------------------------------ quien y que

    def test_automatic_jobs_are_not_logged(self):
        order = self._order()  # superusuario = OdooBot
        order.write({"customer_po": "QUILLON 400001"})
        self.assertFalse(self._rows(order))

    def test_a_person_creating_and_changing_an_order(self):
        order = self._order(self.manager)
        created = self._rows(order, action="create")
        self.assertEqual(len(created), 1)
        self.assertEqual(created.user_id, self.manager)
        self.assertEqual(created.module, "orders")
        self.assertEqual(created.res_name, order.display_name)
        # las puertas creadas con la orden van dentro de esa fila, no aparte
        self.assertFalse(self.Log.search([("res_model", "=", "indigo.order.line"), ("res_id", "in", order.line_ids.ids)]))

        order.with_user(self.manager).write({"customer_po": "QUILLON 400001", "client_name": "Zed Quillon"})
        changed = self._rows(order, action="write")
        self.assertEqual(len(changed), 1, "un nombre igual que antes no es un cambio")
        changes = json.loads(changed.changes)
        self.assertEqual(changes[0]["field"], "customer_po")
        self.assertEqual((changes[0]["old"], changes[0]["new"]), ("", "QUILLON 400001"))
        self.assertIn("QUILLON 400001", changed.summary)

    def test_writing_the_same_value_leaves_no_row(self):
        order = self._order()
        order.with_user(self.manager).write({"client_name": "Zed Quillon"})
        self.assertFalse(self._rows(order))

    def test_deleting_is_logged_with_the_name(self):
        reason = self.env["indigo.hold.reason"].create({"name": "Audit weather"})
        reason.with_user(self.manager).unlink()
        row = self.Log.search([("res_model", "=", "indigo.hold.reason"), ("action", "=", "unlink")])
        self.assertEqual(len(row), 1)
        self.assertIn("Audit weather", row.summary)

    def test_only_dealers_count_among_contacts(self):
        # sudo() conserva a la persona (uid): sigue siendo una accion suya
        plain = self.env["res.partner"].with_user(self.manager).sudo().create({"name": "Somebody"})
        self.assertFalse(self._rows(plain))
        self.dealer.with_user(self.manager).sudo().write({"phone": "305-000-0000"})
        row = self._rows(self.dealer, action="write")
        self.assertEqual(row.module, "dealers")

    def test_secret_settings_are_logged_without_their_value(self):
        icp = self.env["ir.config_parameter"].with_user(self.manager).sudo()
        icp.set_param("indigo_decors.audit_client_secret", "s3cr3t-value")
        icp.set_param("web.base.url.audit", "x")  # no es de Indigo: no entra
        rows = self.Log.search([("res_model", "=", "ir.config_parameter")])
        self.assertEqual(rows.mapped("res_name"), ["indigo_decors.audit_client_secret"])
        self.assertNotIn("s3cr3t-value", (rows.changes or "") + (rows.summary or ""))

    def test_notes_and_files_on_an_order(self):
        order = self._order()
        as_mgr = order.with_user(self.manager)
        as_mgr.message_post(body="Client asked to move the install", message_type="comment")
        as_mgr.message_post(body="Attachment uploaded: <b>photo.png</b>", message_type="comment")
        self.env["ir.attachment"].with_user(self.manager).create({
            "name": "contract.pdf", "res_model": "indigo.order", "res_id": order.id, "raw": b"%PDF-1.4",
        })
        notes = self._rows(order, action="note")
        self.assertEqual(notes.mapped("summary"), ["Client asked to move the install"])
        files = self._rows(order, action="attachment")
        self.assertEqual(files.mapped("summary"), ["Uploaded contract.pdf"])

    # ------------------------------------------------------------ la pagina

    def test_search_filters_and_who_can_read_it(self):
        order = self._order(self.manager)
        order.with_user(self.manager).write({"customer_po": "QUILLON 400009"})
        Log = self.env["indigo.audit.log"]
        today = fields.Date.context_today(self.env.user.with_context(tz="America/New_York"))
        res = Log.with_user(self.manager).indigo_audit_search({
            "module": "orders", "user_id": self.manager.id, "q": "400009",
            "date_from": str(today), "date_to": str(today),
        })
        self.assertEqual(res["total"], 1)
        self.assertEqual(res["rows"][0]["action"], "write")
        self.assertIn({"id": self.manager.id, "name": "Audit Manager"}, res["users"])
        self.assertEqual(Log.with_user(self.manager).indigo_audit_search({"module": "billing", "q": "400009"})["total"], 0)
        with self.assertRaises(AccessError):
            Log.with_user(self.office).indigo_audit_search({})

    def test_the_log_cannot_be_edited_or_deleted(self):
        order = self._order(self.manager)
        row = self._rows(order)
        with self.assertRaises(UserError):
            row.write({"summary": "nothing happened"})
        with self.assertRaises(UserError):
            row.unlink()

    # ------------------------------------------------------------ historial

    def test_history_import_brings_old_notes_once(self):
        order = self._order()
        # Nota de antes de activar el registro: la escribio el gerente, pero
        # entra como OdooBot (sin fila en vivo), igual que el historial real.
        order.message_post(body="Measured on site", message_type="comment",
                           author_id=self.manager.partner_id.id)
        Log = self.env["indigo.audit.log"]
        later = fields.Datetime.add(fields.Datetime.now(), minutes=1)
        Log._audit_import_history(before=later)
        rows = self._rows(order, action="note")
        self.assertEqual(rows.mapped("summary"), ["Measured on site"])
        self.assertEqual(rows.user_id, self.manager)
        Log._audit_import_history(before=later)
        self.assertEqual(len(self._rows(order, action="note")), 1, "repetir no duplica")
        # lo posterior a la activacion ya lo anota el registro en vivo: no se importa
        Log._audit_import_history(before=fields.Datetime.add(fields.Datetime.now(), hours=-1))
        self.assertEqual(len(self._rows(order, action="note")), 1)
