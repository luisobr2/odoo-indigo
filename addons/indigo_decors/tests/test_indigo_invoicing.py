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


class _InvoicingCase(TransactionCase):
    """Preparacion comun: facturacion configurada, un dealer y dos disenos."""

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



@tagged("indigo", "post_install", "-at_install")
class TestIndigoInvoicing(_InvoicingCase):
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


@tagged("indigo", "post_install", "-at_install")
class TestIndigoInvoicingAudit(_InvoicingCase):
    """Lo que encontro la auditoria del 2026-09-28, cada punto con su prueba."""

    # 1. una orden no se factura dos veces
    def test_same_order_cannot_be_invoiced_twice(self):
        order = self._order()
        prev, move = self._invoice(order)
        with self.assertRaises(UserError):
            self.Billing.indigo_billing_create_draft({
                "dealer_id": self.dealer.id, "order_ids": order.ids, "lines": prev["lines"], "photo_ids": [],
            })
        self.Billing.indigo_billing_post(move.id)
        with self.assertRaises(UserError):
            self.Billing.indigo_billing_create_draft({
                "dealer_id": self.dealer.id, "order_ids": order.ids, "lines": prev["lines"], "photo_ids": [],
            })

    # 2. la empresa no reparte impuesto a los productos nuevos (tienda)
    def test_new_products_get_no_default_tax(self):
        self.assertFalse(self.env.company.account_sale_tax_id)
        shop = self.env["product.template"].create({"name": "Shop product after setup", "type": "consu"})
        self.assertFalse(shop.taxes_id)
        door = self.env["product.product"].search([("default_code", "=", "IND-SD")])
        self.assertTrue(door.taxes_id)

    # 3. anular devuelve las ordenes y permite rehacer la factura
    def test_void_returns_orders_and_allows_new_invoice(self):
        order = self._order()
        _prev, move = self._invoice(order)
        first = self.Billing.indigo_billing_post(move.id)["name"]
        detail = self.Billing.indigo_billing_void(move.id, "wrong price")
        self.assertEqual(detail["state"], "cancel")
        self.assertEqual(detail["name"], first)  # conserva su numero
        self.assertEqual(order.stage_id.code, "installed")
        self.assertEqual(order.payment_state, "unpaid")
        ids = [o["id"] for g in self.Billing.indigo_billing_to_invoice() for o in g["orders"]]
        self.assertIn(order.id, ids)
        _p2, move2 = self._invoice(order)
        second = self.Billing.indigo_billing_post(move2.id)["name"]
        self.assertNotEqual(first, second)

    def test_void_refused_with_payments(self):
        order = self._order()
        _prev, move = self._invoice(order)
        self.Billing.indigo_billing_post(move.id)
        self.Billing.indigo_billing_register_payment(move.id, {"amount": 10, "method": "cash"})
        with self.assertRaises(UserError):
            self.Billing.indigo_billing_void(move.id)

    # 4. lo que llega se valida
    def test_line_cannot_point_to_another_order(self):
        order = self._order()
        other = self._order(client_name="Other client")
        prev = self.Billing.indigo_billing_preview(order.ids)
        lines = [dict(prev["lines"][0], order_id=other.id)]
        with self.assertRaises(UserError):
            self.Billing.indigo_billing_create_draft({
                "dealer_id": self.dealer.id, "order_ids": order.ids, "lines": lines, "photo_ids": [],
            })

    def test_only_this_invoices_photos(self):
        order = self._order()
        prev = self.Billing.indigo_billing_preview(order.ids)
        foreign = self.env["ir.attachment"].create({
            "name": "secret.png", "res_model": "res.partner", "res_id": self.dealer.id,
            "mimetype": "image/png", "raw": b"\x89PNG\r\n",
        })
        with self.assertRaises(UserError):
            self.Billing.indigo_billing_create_draft({
                "dealer_id": self.dealer.id, "order_ids": order.ids, "lines": prev["lines"], "photo_ids": [foreign.id],
            })
        own = self.env["ir.attachment"].create({
            "name": "install.png", "res_model": "indigo.order", "res_id": order.id,
            "mimetype": "image/png", "raw": b"\x89PNG\r\n",
        })
        move_id = self.Billing.indigo_billing_create_draft({
            "dealer_id": self.dealer.id, "order_ids": order.ids, "lines": prev["lines"], "photo_ids": [own.id],
        })
        self.assertEqual(self.env["account.move"].browse(move_id).indigo_photo_ids, own)

    def test_only_invoice_products(self):
        order = self._order()
        prev = self.Billing.indigo_billing_preview(order.ids)
        lines = [dict(prev["lines"][0], product_code="SOMETHING-ELSE")]
        with self.assertRaises(UserError):
            self.Billing.indigo_billing_create_draft({
                "dealer_id": self.dealer.id, "order_ids": order.ids, "lines": lines, "photo_ids": [],
            })

    # 5. la numeracion no choca con una factura emitida desde el backend
    def test_numbering_skips_numbers_used_in_backend(self):
        a = self._order()
        _p, backend = self._invoice(a)
        backend.name = str(self.Billing._sequence().number_next_actual)
        backend.action_post()  # como si alguien la validara en Odoo
        b = self._order(client_name="Second")
        _p2, app = self._invoice(b)
        detail = self.Billing.indigo_billing_post(app.id)
        self.assertEqual(int(detail["name"]), int(backend.name) + 1)

    # 6. la orden guarda la fecha real del pago
    def test_date_paid_is_the_payment_date(self):
        order = self._order()
        _prev, move = self._invoice(order)
        self.Billing.indigo_billing_post(move.id)
        self.Billing.indigo_billing_register_payment(move.id, {"amount": move.amount_total, "date": "2026-08-15", "method": "check"})
        self.assertEqual(str(order.date_paid), "2026-08-15")


@tagged("indigo", "post_install", "-at_install")
class TestIndigoInvoicingOrderPage(_InvoicingCase):
    """La ficha de la orden: su factura, que accion toca y su historial."""

    def _history(self, order):
        return " | ".join(order.message_ids.mapped("body"))

    def test_order_invoices_follow_the_invoice_life(self):
        order = self._order()
        info = self.Billing.indigo_billing_order_invoices(order.id)
        self.assertTrue(info["ready"])
        self.assertTrue(info["can_create"])
        self.assertEqual(info["invoices"], [])

        _prev, move = self._invoice(order)
        info = self.Billing.indigo_billing_order_invoices(order.id)
        self.assertFalse(info["can_create"])  # ya tiene un borrador
        self.assertEqual([r["state"] for r in info["invoices"]], ["draft"])

        self.Billing.indigo_billing_post(move.id)
        info = self.Billing.indigo_billing_order_invoices(order.id)
        self.assertEqual(info["invoices"][0]["status"], "Balance due")
        self.assertAlmostEqual(info["invoices"][0]["residual"], move.amount_total)

        self.Billing.indigo_billing_void(move.id, "wrong price")
        info = self.Billing.indigo_billing_order_invoices(order.id)
        self.assertTrue(info["can_create"])  # de vuelta a «To invoice»
        self.assertEqual([r["state"] for r in info["invoices"]], ["cancel"])

    def test_order_not_installed_cannot_be_invoiced_yet(self):
        order = self._order()
        order.stage_id = self.env.ref("indigo_decors.stage_painting")
        self.assertFalse(self.Billing.indigo_billing_order_invoices(order.id)["can_create"])

    def test_order_history_tells_the_invoice(self):
        order = self._order()
        _prev, move = self._invoice(order)
        name = self.Billing.indigo_billing_post(move.id)["name"]
        self.assertIn("Invoice %s issued" % name, self._history(order))
        self.Billing.indigo_billing_register_payment(move.id, {"amount": 10, "method": "zelle", "reference": "Z9"})
        history = self._history(order)
        self.assertIn("Payment of $10.00 (Zelle · Z9) recorded on invoice %s" % name, history)
        self.assertIn("Balance due", history)
        self.Billing.indigo_billing_register_payment(move.id, {"amount": move.amount_residual, "method": "check"})
        self.assertIn("Paid in full", self._history(order))

        other = self._order(client_name="Void client")
        _p2, move2 = self._invoice(other)
        name2 = self.Billing.indigo_billing_post(move2.id)["name"]
        self.Billing.indigo_billing_void(move2.id, "wrong door")
        history2 = self._history(other)
        self.assertIn("Invoice %s voided" % name2, history2)
        self.assertIn("wrong door", history2)

    def test_order_history_notifies_nobody(self):
        # Los avisos al dealer estan apagados: dejar la linea en la orden no
        # puede mandar un correo, ni aunque el dealer siga la orden.
        order = self._order()
        order.message_subscribe(partner_ids=self.dealer.ids)
        _prev, move = self._invoice(order)
        before = self.env["mail.mail"].sudo().search_count([])
        self.Billing.indigo_billing_post(move.id)
        self.Billing.indigo_billing_register_payment(move.id, {"amount": 10, "method": "cash"})
        self.assertEqual(self.env["mail.mail"].sudo().search_count([]), before)
        notified = order.message_ids.mapped("notification_ids.res_partner_id")
        self.assertNotIn(self.dealer, notified)

    def test_painter_cannot_read_order_invoices(self):
        order = self._order()
        painter = self.env["res.users"].create({
            "name": "Painter Order Inv", "login": "painter.orderinv@test",
            "groups_id": [(6, 0, [self.env.ref("indigo_decors.group_indigo_painter_op").id])],
        })
        with self.assertRaises(AccessError):
            self.Billing.with_user(painter).indigo_billing_order_invoices(order.id)
