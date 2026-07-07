# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged("indigo", "indigo_dealer_portal", "post_install", "-at_install")
class TestIndigoDealerPortal(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.Users = cls.env["res.users"]

    def test_set_password_creates_portal_user(self):
        dealer = self.Partner.create({
            "name": "Portal Dealer",
            "is_indigo_dealer": True,
            "email": "portaldealer@test.example",
        })
        res = self.env["res.partner"].indigo_dealer_set_password(dealer.id, "secret123")
        self.assertTrue(res["ok"])
        self.assertTrue(res["created"])
        self.assertEqual(res["login"], "portaldealer@test.example")
        user = self.Users.with_context(active_test=False).search(
            [("partner_id", "=", dealer.id)], limit=1
        )
        self.assertTrue(user, "portal user should be created")
        self.assertTrue(user.has_group("base.group_portal"))
        self.assertTrue(user.active)

    def test_set_password_idempotent_second_call_updates(self):
        dealer = self.Partner.create({
            "name": "Portal Dealer 2",
            "email": "portaldealer2@test.example",
        })
        self.env["res.partner"].indigo_dealer_set_password(dealer.id, "secret123")
        res2 = self.env["res.partner"].indigo_dealer_set_password(dealer.id, "newpass456")
        self.assertFalse(res2["created"], "second call must reuse the existing user")
        users = self.Users.with_context(active_test=False).search(
            [("partner_id", "=", dealer.id)]
        )
        self.assertEqual(len(users), 1, "must not create a duplicate user")

    def test_set_password_requires_email(self):
        dealer = self.Partner.create({"name": "No Email Dealer"})
        with self.assertRaises(ValidationError):
            self.env["res.partner"].indigo_dealer_set_password(dealer.id, "secret123")

    def test_set_password_min_length(self):
        dealer = self.Partner.create({
            "name": "Short Pw Dealer",
            "email": "shortpw@test.example",
        })
        with self.assertRaises(ValidationError):
            self.env["res.partner"].indigo_dealer_set_password(dealer.id, "123")

    def test_portal_info_reports_status(self):
        dealer = self.Partner.create({
            "name": "Info Dealer",
            "email": "infodealer@test.example",
        })
        before = self.env["res.partner"].indigo_dealer_portal_info(dealer.id)
        self.assertFalse(before["has_user"])
        self.env["res.partner"].indigo_dealer_set_password(dealer.id, "secret123")
        after = self.env["res.partner"].indigo_dealer_portal_info(dealer.id)
        self.assertTrue(after["has_user"])
        self.assertEqual(after["login"], "infodealer@test.example")
        self.assertTrue(after["active"])
