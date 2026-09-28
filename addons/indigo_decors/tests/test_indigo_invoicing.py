# -*- coding: utf-8 -*-
"""Facturar desde la app (2026-09-28).

Lo que se comprueba es lo que Majela pidio, con las facturas de QuickBooks
como referencia:

  * una linea por puerta con su producto y precio, y el 7 % de Florida solo
    sobre las puertas; el recargo de instalacion va sin impuesto;
  * el recargo sale del rango de millas de la orden (region A-D);
  * la descripcion sigue la plantilla del dealer (cliente / + direccion /
    REF: PO);
  * el numero sigue la numeracion de QuickBooks;
  * al cobrar, la orden pasa a pagada (o parcial);
  * un dealer exento no lleva impuesto;
  * solo oficina, gerente o admin facturan.
"""
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged


@tagged("indigo", "post_install", "-at_install")
class TestIndigoInvoicing(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Billing = cls.env["indigo.billing"]
        cls.status = cls.Billing.indigo_billing_setup({"next_number": 5001, "tax_rate": 7})
        cls.Partner = cls.env["res.partner"]
        cls.Order = cls.env["indigo.order"]
        cls.design_sd = cls.env["indigo.design"].create({
            "code": "INVTEST-SD", "name": "Invoice Test Single", "door_type": "SD",
        })
        cls.design_dd = cls.env["indigo.design"].create({
            "code": "INVTEST-DD", "name": "Invoice Test Double", "door_type": "DD",
        })
        cls.dealer = cls.Partner.create({
            "name": "Invoice Test Dealer", "is_company": True, "is_indigo_dealer": True,
            "email": "billing@dealer.test", "street": "1 Test St", "city": "Miami", "zip": "33138",
        })
        cls.stage_installed = cls.env.ref("indigo_decors.stage_installed")

    def _order(self, dealer=None, door_type="SD", qty=1, address=False, **extra):
        design = self.design_dd if door_type == "DD" else self.design_sd
        vals = {
            "dealer_id": (dealer or self.dealer).id,
            "client_name": extra.pop("client_name", "Maria Williams"),
            "client_address": address,
            "line_ids": [(0, 0, {
                "design_id": design.id, "door_type": door_type, "color": "white", "qty": qty, "sqf": 20.0,
            })],
        }
        vals.update(extra)
        order = self.Order.create(vals)
        order.stage_id = self.stage_installed
        return order

    def _invoice(self, orders):
        prev = self.Billing.indigo_billing_preview(orders.ids)
        move_id = self.Billing.indigo_billing_create_draft({
            "dealer_id": prev["dealer"]["id"],
            "order_ids": prev["order_ids"],
            "lines": prev["lines"],
            "photo_ids": [],
        })
        return prev, self.env["account.move"].browse(move_id)

    def test_setup_is_ready_and_idempotent(self):
        self.assertTrue(self.status["ready"], self.status["missing"])
        again = self.Billing.indigo_billing_setup({})
        self.assertTrue(again["ready"])
        self.assertEqual(self.env["product.product"].search_count([("default_code", "=", "IND-SD")]), 1)

    def test_door_taxed_fee_not(self):
        order = self._order(door_type="SD", address="100 NE 1st Ave, Miami, FL 33132")
        prev, move = self._invoice(order)
        door = [l for l in prev["lines"] if l["kind"] == "door"]
        fee = [l for l in prev["lines"] if l["kind"] == "fee"]
        self.assertEqual(len(door), 1)
        self.assertEqual(len(fee), 1)
        self.assertTrue(door[0]["taxable"])
        self.assertFalse(fee[0]["taxable"])
        price = order.line_ids.unit_price
        self.assertAlmostEqual(move.amount_untaxed, price + fee[0]["price_unit"], places=2)
        self.assertAlmostEqual(move.amount_tax, round(price * 0.07, 2), places=2)

    def test_fee_follows_distance_range(self):
        order = self._order(address="100 NE 1st Ave, Miami, FL 33132")
        prev = self.Billing.indigo_billing_preview(order.ids)
        fee = [l for l in prev["lines"] if l["kind"] == "fee"][0]
        rng = order.install_range_id
        if rng and rng.invoice_region:
            self.assertEqual(fee["product_code"], "IND-FEE-%s" % rng.invoice_region)
            self.assertAlmostEqual(fee["price_unit"], rng.invoice_fee)

    def test_order_without_zip_warns_and_uses_region_a(self):
        order = self._order(address=False)
        prev = self.Billing.indigo_billing_preview(order.ids)
        fee = [l for l in prev["lines"] if l["kind"] == "fee"][0]
        self.assertEqual(fee["product_code"], "IND-FEE-A")
        self.assertTrue(any(order.name in w for w in prev["warnings"]))

    def test_post_uses_quickbooks_numbering_and_moves_order(self):
        order = self._order()
        _prev, move = self._invoice(order)
        seq = self.Billing._sequence()
        expected = str(seq.number_next_actual)
        detail = self.Billing.indigo_billing_post(move.id)
        self.assertEqual(detail["name"], expected)
        self.assertEqual(move.state, "posted")
        self.assertEqual(order.stage_id.code, "invoiced")
        self.assertTrue(order.invoiced_at)
        self.assertEqual(order.payment_state, "unpaid")
        # la siguiente sigue el correlativo
        order2 = self._order(client_name="Carlos G")
        _p, move2 = self._invoice(order2)
        detail2 = self.Billing.indigo_billing_post(move2.id)
        self.assertEqual(int(detail2["name"]), int(expected) + 1)

    def test_payment_marks_order_paid_or_partial(self):
        order = self._order()
        _prev, move = self._invoice(order)
        self.Billing.indigo_billing_post(move.id)
        half = round(move.amount_total / 2, 2)
        self.Billing.indigo_billing_register_payment(move.id, {"amount": half, "method": "zelle", "reference": "Z1"})
        self.assertEqual(order.payment_state, "partial")
        self.Billing.indigo_billing_register_payment(move.id, {"amount": move.amount_residual, "method": "check"})
        self.assertIn(move.payment_state, ("paid", "in_payment"))
        self.assertEqual(order.payment_state, "paid")
        self.assertTrue(order.date_paid)
        statement = self.Billing.indigo_billing_dealer_statement(self.dealer.id)
        self.assertEqual(statement["open_balance"], 0)
        self.assertTrue(any(e["kind"] == "payment" for e in statement["events"]))

    def test_overpayment_refused(self):
        order = self._order()
        _prev, move = self._invoice(order)
        self.Billing.indigo_billing_post(move.id)
        with self.assertRaises(Exception):
            self.Billing.indigo_billing_register_payment(move.id, {"amount": move.amount_total + 10})

    def test_tax_exempt_dealer(self):
        exempt = self.Partner.create({
            "name": "Exempt Dealer", "is_company": True, "is_indigo_dealer": True, "indigo_tax_exempt": True,
        })
        order = self._order(dealer=exempt)
        _prev, move = self._invoice(order)
        self.assertEqual(move.amount_tax, 0.0)

    def test_description_templates(self):
        order = self._order(
            address="9720 NW 1st Pl, Coral Springs, FL 33071",
            customer_po="102868", dealer_ref="4989", client_name="FRANKLIN",
        )
        B = self.Billing
        self.assertEqual(B._line_description(order, "client"), "FRANKLIN - 4989")
        self.assertEqual(B._line_description(order, "client_address"), "FRANKLIN\n9720 NW 1st Pl, Coral Springs, FL 33071")
        self.assertEqual(B._line_description(order, "po"), "REF: PO FRANKLIN 102868")

    def test_one_dealer_per_invoice(self):
        other = self.Partner.create({"name": "Other Dealer", "is_indigo_dealer": True})
        a = self._order()
        b = self._order(dealer=other)
        with self.assertRaises(UserError):
            self.Billing.indigo_billing_preview((a | b).ids)

    def test_to_invoice_lists_installed_not_invoiced(self):
        order = self._order()
        groups = self.Billing.indigo_billing_to_invoice()
        ids = [o["id"] for g in groups for o in g["orders"]]
        self.assertIn(order.id, ids)
        _prev, move = self._invoice(order)
        groups = self.Billing.indigo_billing_to_invoice()
        ids = [o["id"] for g in groups for o in g["orders"]]
        self.assertNotIn(order.id, ids)

    def test_pdf_renders(self):
        order = self._order()
        _prev, move = self._invoice(order)
        pdf = self.Billing.indigo_billing_pdf(move.id)
        self.assertTrue(pdf["data"])

    def test_painter_cannot_invoice(self):
        painter = self.env["res.users"].create({
            "name": "Painter Inv", "login": "painter.inv@test",
            "groups_id": [(6, 0, [self.env.ref("indigo_decors.group_indigo_painter_op").id])],
        })
        with self.assertRaises(AccessError):
            self.Billing.with_user(painter).indigo_billing_to_invoice()
