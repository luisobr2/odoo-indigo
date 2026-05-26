# -*- coding: utf-8 -*-
"""
Bridge sale.order <-> indigo.order

Cuando un sale.order se confirma (action_confirm) y el cliente esta marcado
como is_indigo_dealer (o es un sale.order generado por el website_sale para
un cliente cualquiera con productos indigo), se crea automaticamente un
indigo.order vinculado, copiando lineas y datos del cliente.

Asi:
- La tienda actual (indigodecors.com) sigue funcionando con su carrito y eCommerce
- Cuando agreguen pasarela de pago (Stripe), el pago confirma la sale.order ->
  dispara la creacion de la indigo.order -> arranca workflow de produccion
- Para casos B2B donde el dealer crea orden via /my/order/new (sin pasar por el
  carrito), se crea directamente la indigo.order (mantenemos ese path)
"""
import logging
import re
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_indigo_design = fields.Boolean(
        string="Es diseno Indigo",
        help="Marcar para que las ordenes que incluyan este producto disparen "
             "creacion automatica de indigo.order al confirmarse.",
    )
    indigo_design_id = fields.Many2one(
        "indigo.design",
        string="Diseno Indigo asociado",
        help="Catalogo Indigo correspondiente. Si esta vacio, se intenta inferir "
             "por codigo del producto.",
    )
    indigo_door_type = fields.Selection(
        [
            ("SD", "Single Door"),
            ("DD", "Double Door"),
            ("sidelite", "Door with Sidelites"),
        ],
        string="Tipo de puerta Indigo",
    )
    indigo_default_width = fields.Float(
        string="Ancho default (in)",
        digits=(8, 2),
        help="Medida default cuando se compra via eCommerce sin especificar (override en formulario custom).",
    )
    indigo_default_height = fields.Float(
        string="Alto default (in)",
        digits=(8, 2),
    )
    indigo_default_color = fields.Selection(
        [
            ("white", "White"),
            ("bronze", "Bronze"),
            ("black", "Black"),
            ("custom", "Custom"),
        ],
        string="Color default",
        default="white",
    )
    indigo_default_glass = fields.Char(string="Vidrio default", help="Ej. ESW")


class SaleOrder(models.Model):
    _inherit = "sale.order"

    indigo_order_id = fields.Many2one(
        "indigo.order",
        string="Orden Indigo de produccion",
        copy=False,
        readonly=True,
    )

    def _should_create_indigo_order(self):
        """True si esta sale.order contiene al menos una linea con producto
        marcado como is_indigo_design (o cuyo template tenga el flag)."""
        for line in self.order_line:
            tmpl = line.product_id.product_tmpl_id
            if tmpl and tmpl.is_indigo_design:
                return True
        return False

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            if order.indigo_order_id:
                continue
            if not order._should_create_indigo_order():
                continue
            try:
                order._create_indigo_order_from_sale()
            except Exception as e:
                _logger.exception("Indigo bridge: error creando indigo.order desde %s: %s", order.name, e)
                order.message_post(body="No se pudo crear orden Indigo automaticamente: %s" % e)
        return res

    def _parse_door_type_from_code(self, code):
        if not code:
            return "SD"
        c = code.upper()
        if c.endswith("-DD") or "DOUBLE" in c:
            return "DD"
        if "SIDE" in c:
            return "sidelite"
        return "SD"

    def _parse_color_from_variant(self, variant):
        """Detecta color desde el nombre de la variante o atributos."""
        name = (variant.display_name or "").lower()
        for color in ("white", "blanc"):
            if color in name:
                return "white"
        for color in ("bronze", "bronce"):
            if color in name:
                return "bronze"
        for color in ("black", "negro"):
            if color in name:
                return "black"
        return "white"

    def _resolve_indigo_design(self, product):
        """Encuentra/match el indigo.design para el producto."""
        tmpl = product.product_tmpl_id
        if tmpl.indigo_design_id:
            return tmpl.indigo_design_id
        # Try by default_code
        code = product.default_code or tmpl.default_code
        if code:
            design = self.env["indigo.design"].search([("code", "=", code)], limit=1)
            if design:
                return design
        return self.env["indigo.design"]  # empty

    def _create_indigo_order_from_sale(self):
        """Crea la indigo.order replicando partner + lineas."""
        self.ensure_one()
        IndigoOrder = self.env["indigo.order"]
        partner = self.partner_id
        ship = self.partner_shipping_id or partner
        # Si el partner es dealer Indigo, lo seteamos como dealer; si no,
        # asumimos venta directa B2C y dejamos dealer = partner mismo
        if partner.is_indigo_dealer:
            dealer = partner
            client_name = ship.name or partner.name
        else:
            # B2C: el partner es el cliente final; dealer queda vacio o
            # usamos un dealer "ventas directas" si existe
            direct_sales = self.env["res.partner"].search([
                ("is_indigo_dealer", "=", True),
                ("indigo_dealer_code", "=", "DIRECT"),
            ], limit=1)
            dealer = direct_sales or partner
            client_name = partner.name
        lines = []
        for sline in self.order_line:
            tmpl = sline.product_id.product_tmpl_id
            if not tmpl.is_indigo_design:
                continue
            design = self._resolve_indigo_design(sline.product_id)
            door_type = tmpl.indigo_door_type or self._parse_door_type_from_code(
                sline.product_id.default_code or tmpl.default_code
            )
            color = self._parse_color_from_variant(sline.product_id)
            lines.append((0, 0, {
                "design_id": design.id if design else False,
                "door_type": door_type,
                "color": tmpl.indigo_default_color or color,
                "glass_type": tmpl.indigo_default_glass or "",
                "width": tmpl.indigo_default_width or 0.0,
                "height": tmpl.indigo_default_height or 0.0,
                "qty": int(sline.product_uom_qty or 1),
                "notes_line": sline.name or "",
            }))
        if not lines:
            return
        indigo_order = IndigoOrder.create({
            "dealer_id": dealer.id,
            "dealer_ref": self.client_order_ref or self.name,
            "client_name": client_name,
            "client_phone": (ship.phone or partner.phone or ""),
            "client_email": (ship.email or partner.email or ""),
            "client_address": "%s\n%s, %s %s" % (
                ship.street or "",
                ship.city or "",
                ship.state_id.name if ship.state_id else "",
                ship.zip or "",
            ),
            "line_ids": lines,
            "notes": "Generada automaticamente desde sale.order %s." % self.name,
        })
        self.indigo_order_id = indigo_order.id
        indigo_order.message_post(
            body="Vinculada a venta <a href='/odoo/action-sale.action_orders/%d'>%s</a>." % (
                self.id, self.name
            )
        )
