# -*- coding: utf-8 -*-
"""Equivalencias: dealers <-> clientes de QBO, productos de factura <-> productos de QBO."""
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .test_qbo_client import _QboCase

CLIENT = "odoo.addons.indigo_quickbooks.models.qbo_client.IndigoQboClient"

REMOTE_CUSTOMERS = [
    {"Id": "58", "DisplayName": "Mapping  Dealer"},
    {"Id": "59", "DisplayName": "Other Remote Co"},
]
REMOTE_ITEMS = [
    {"Id": "19", "Name": "DESIGN SINGLE DOOR", "Type": "Service", "Active": True},
    {"Id": "25", "Name": "installation fee c", "Type": "Service", "Active": True},
]


def fake_query(rows_by_entity):
    def _query(self, sql, entity):
        rows = rows_by_entity.get(entity, [])
        if "STARTPOSITION" in sql and "STARTPOSITION 1 " not in sql + " ":
            return []
        if "WHERE" in sql and "DisplayName =" in sql:
            name = sql.split("DisplayName = '", 1)[1].rsplit("'", 1)[0].replace("\\'", "'")
            return [r for r in rows if r.get("DisplayName") == name]
        return rows
    return _query


@tagged("indigo", "post_install", "-at_install")
class TestQboMapping(_QboCase):
    def setUp(self):
        super().setUp()
        self.connect()
        self.dealer = self.env["res.partner"].create({
            "name": "Mapping Dealer", "is_indigo_dealer": True, "is_company": True,
            "email": "main@dealer.test", "street": "1 Test St", "city": "Miami", "zip": "33138",
        })
        Product = self.env["product.product"]
        self.p_sd = Product.search([("default_code", "=", "IND-SD")], limit=1) or Product.create(
            {"name": "DESIGN SINGLE DOOR", "default_code": "IND-SD", "type": "service"})
        self.p_fee = Product.search([("default_code", "=", "IND-FEE-C")], limit=1) or Product.create(
            {"name": "INSTALLATION FEE C", "default_code": "IND-FEE-C", "type": "service"})
        (self.p_sd | self.p_fee).write({"qbo_item_id": False, "qbo_item_name": False})
        self.Qbo = self.env["indigo.qbo"]

    def _rows(self, data, key, value):
        return next(r for r in data if r[key] == value)

    def test_list_shows_dealers_and_invoice_products(self):
        data = self.Qbo.qbo_mapping_list()
        row = self._rows(data["dealers"], "id", self.dealer.id)
        self.assertFalse(row["qbo_id"])
        codes = [p["code"] for p in data["products"]]
        self.assertIn("IND-SD", codes)
        self.assertIn("IND-FEE-C", codes)
        self.assertFalse(self._rows(data["products"], "code", "IND-FEE-C")["taxable"])
        self.assertTrue(self._rows(data["products"], "code", "IND-SD")["taxable"])

    def test_auto_matches_by_name_ignoring_case_and_spaces(self):
        with patch(CLIENT + ".query", fake_query({"Customer": REMOTE_CUSTOMERS, "Item": REMOTE_ITEMS})):
            result = self.Qbo.qbo_mapping_auto()
        self.assertEqual(self.dealer.qbo_customer_id, "58")
        self.assertEqual(self.dealer.qbo_customer_name, "Mapping  Dealer")
        self.assertEqual(self.p_sd.qbo_item_id, "19")
        self.assertEqual(self.p_fee.qbo_item_id, "25")
        self.assertGreaterEqual(result["matched"]["dealers"], 1)
        self.assertGreaterEqual(result["matched"]["products"], 2)

    def test_auto_never_replaces_a_mapping_someone_chose(self):
        self.dealer.write({"qbo_customer_id": "59", "qbo_customer_name": "Other Remote Co"})
        with patch(CLIENT + ".query", fake_query({"Customer": REMOTE_CUSTOMERS, "Item": REMOTE_ITEMS})):
            self.Qbo.qbo_mapping_auto()
        self.assertEqual(self.dealer.qbo_customer_id, "59")

    def test_set_and_clear(self):
        with patch(CLIENT + ".get", return_value={"Customer": {"Id": "59", "DisplayName": "Other Remote Co"}}):
            self.Qbo.qbo_mapping_set("dealer", self.dealer.id, "59")
        self.assertEqual((self.dealer.qbo_customer_id, self.dealer.qbo_customer_name), ("59", "Other Remote Co"))
        self.Qbo.qbo_mapping_set("dealer", self.dealer.id, False)
        self.assertFalse(self.dealer.qbo_customer_id)

    def test_create_customer_links_an_existing_one_instead_of_duplicating(self):
        with patch(CLIENT + ".query", fake_query({"Customer": [{"Id": "70", "DisplayName": "Mapping Dealer"}]})), \
                patch(CLIENT + ".post") as post:
            self.Qbo.qbo_mapping_create_remote("dealer", self.dealer.id)
        post.assert_not_called()
        self.assertEqual(self.dealer.qbo_customer_id, "70")

    def test_create_customer_sends_name_email_and_address(self):
        with patch(CLIENT + ".query", fake_query({})), \
                patch(CLIENT + ".post", return_value={"Customer": {"Id": "71", "DisplayName": "Mapping Dealer"}}) as post:
            self.Qbo.qbo_mapping_create_remote("dealer", self.dealer.id)
        path, body = post.call_args.args[0], post.call_args.args[1]
        self.assertEqual(path, "customer")
        self.assertEqual(body["DisplayName"], "Mapping Dealer")
        self.assertEqual(body["PrimaryEmailAddr"]["Address"], "main@dealer.test")
        self.assertEqual(body["BillAddr"]["City"], "Miami")
        self.assertEqual(self.dealer.qbo_customer_id, "71")

    def test_create_item_needs_an_income_account_and_keeps_taxable(self):
        with self.assertRaises(UserError):
            self.Qbo.qbo_mapping_create_remote("product", self.p_fee.id)
        with patch(CLIENT + ".query", fake_query({})), \
                patch(CLIENT + ".post", return_value={"Item": {"Id": "80", "Name": "INSTALLATION FEE C"}}) as post:
            self.Qbo.qbo_mapping_create_remote("product", self.p_fee.id, "52")
        body = post.call_args.args[1]
        self.assertEqual(body["Type"], "Service")
        self.assertFalse(body["Taxable"])
        self.assertEqual(body["IncomeAccountRef"], {"value": "52"})
        self.assertEqual(self.p_fee.qbo_item_id, "80")

    def test_only_office_and_managers(self):
        user = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Plain", "login": "qbo_plain@test.local",
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        with self.assertRaises(AccessError):
            self.Qbo.with_user(user).qbo_mapping_list()
