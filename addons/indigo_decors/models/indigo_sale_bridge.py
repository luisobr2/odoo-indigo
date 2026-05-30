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


class SaleOrderLine(models.Model):
    """Per-line custom fields captured from the PDP at add-to-cart time.

    Indigo doors are made-to-spec for a particular homeowner / install
    address. The dealer fills these in BEFORE adding the door to the cart
    so the quote that sales replies with already carries the install
    context per door.
    """
    _inherit = "sale.order.line"

    indigo_customer_name = fields.Char(
        string="Customer name",
        help="Name of the homeowner / final client the door is for.",
    )
    indigo_order_ref = fields.Char(
        string="Order ref (dealer)",
        help="Dealer's internal order reference / project code for this door.",
    )
    indigo_install_address = fields.Char(
        string="Install address",
        help="Where the door will be installed (homeowner address or "
             "dealer warehouse).",
    )
    indigo_install_phone = fields.Char(
        string="Install phone",
        help="Contact phone at the install address (homeowner, contractor, "
             "or dealer site lead).",
    )
    indigo_door_width = fields.Char(
        string="Width",
        help="Door width in inches & eighths (US door-trade format), "
             "e.g. '36' or '36 4/8'. Stored as text — sales validates.",
    )
    indigo_door_height = fields.Char(
        string="Height",
        help="Door height in inches & eighths, e.g. '80' or '96 4/8'.",
    )


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
        """Detecta color desde los attribute values de la variant.
        Prefer reading product.template.attribute.value (variant-bound) over
        scraping the display_name string."""
        # 1) Try variant attribute values via the proper M2M relation
        for ptav in variant.product_template_attribute_value_ids:
            attr_name = (ptav.attribute_id.name or "").lower()
            val_name = (ptav.name or "").lower()
            if "color" in attr_name or "finish" in attr_name:
                if "white" in val_name or "blanc" in val_name:
                    return "white"
                if "bronze" in val_name or "bronce" in val_name:
                    return "bronze"
                if "black" in val_name or "negro" in val_name:
                    return "black"
        # 2) Fallback to display_name scraping
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

    def _parse_attrs_from_variant(self, variant):
        """Returns (is_privacy_glass: bool, glass_brand: str) by reading the
        variant's attribute values for Privacy Glass + Door Brand."""
        is_privacy = False
        glass_brand = ""
        for ptav in variant.product_template_attribute_value_ids:
            attr_name = (ptav.attribute_id.name or "").lower()
            val_name = (ptav.name or "").strip()
            if "privacy" in attr_name:
                is_privacy = val_name.lower() in ("yes", "si", "sí", "true")
            elif "brand" in attr_name or "glass" in attr_name:
                glass_brand = val_name
        return is_privacy, glass_brand

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

    @staticmethod
    def _parse_inches_eighths(value):
        """Parse '36 4/8' or '36' or '36.5' as inches (Float).
        Returns 0.0 on empty / unparseable input."""
        if not value:
            return 0.0
        s = str(value).strip()
        if not s:
            return 0.0
        try:
            # Inches & eighths: '36 4/8' → 36 + 4/8 = 36.5
            if " " in s and "/" in s:
                whole_str, frac_str = s.split(" ", 1)
                num, den = frac_str.split("/", 1)
                return float(whole_str) + (float(num) / float(den))
            # Pure fraction '4/8'
            if "/" in s:
                num, den = s.split("/", 1)
                return float(num) / float(den)
            # Pure decimal '36' or '36.5'
            return float(s)
        except (ValueError, ZeroDivisionError):
            return 0.0

    def _create_indigo_order_from_sale(self):
        """Crea la indigo.order replicando partner + lineas.
        Usa los campos custom de sale.order.line (indigo_customer_name,
        indigo_install_address, etc.) si están seteados, sino cae al partner."""
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
        # If ANY line has a customer name on it, override with the per-line
        # value (first match wins for header-level fields).
        per_line_customer = next(
            (l.indigo_customer_name for l in self.order_line if l.indigo_customer_name),
            None,
        )
        if per_line_customer:
            client_name = per_line_customer
        per_line_phone = next(
            (l.indigo_install_phone for l in self.order_line if l.indigo_install_phone),
            None,
        )
        per_line_address = next(
            (l.indigo_install_address for l in self.order_line if l.indigo_install_address),
            None,
        )
        per_line_ref = next(
            (l.indigo_order_ref for l in self.order_line if l.indigo_order_ref),
            None,
        )
        lines = []
        for sline in self.order_line:
            tmpl = sline.product_id.product_tmpl_id
            if not tmpl.is_indigo_design:
                continue
            design = self._resolve_indigo_design(sline.product_id)
            door_type = tmpl.indigo_door_type or self._parse_door_type_from_code(
                sline.product_id.default_code or tmpl.default_code
            )
            # Dealer-selected color from variant attrs wins; fall back to
            # template default if the variant has no Finish attribute.
            color = self._parse_color_from_variant(sline.product_id) or tmpl.indigo_default_color
            is_privacy, glass_brand = self._parse_attrs_from_variant(sline.product_id)
            line_width = self._parse_inches_eighths(sline.indigo_door_width) or tmpl.indigo_default_width or 0.0
            line_height = self._parse_inches_eighths(sline.indigo_door_height) or tmpl.indigo_default_height or 0.0
            # Note appended with the per-line install context if present
            extra_notes = []
            if sline.indigo_customer_name:
                extra_notes.append("Customer: %s" % sline.indigo_customer_name)
            if sline.indigo_order_ref:
                extra_notes.append("Dealer ref: %s" % sline.indigo_order_ref)
            if sline.indigo_install_address:
                extra_notes.append("Install at: %s" % sline.indigo_install_address)
            if sline.indigo_install_phone:
                extra_notes.append("Contact: %s" % sline.indigo_install_phone)
            extra_notes.append(sline.name or "")
            lines.append((0, 0, {
                "design_id": design.id if design else False,
                "door_type": door_type,
                "color": color or tmpl.indigo_default_color or "white",
                "glass_type": glass_brand or tmpl.indigo_default_glass or "",
                "is_privacy_glass": is_privacy,
                "customer_name": sline.indigo_customer_name or "",
                "width": line_width,
                "height": line_height,
                "qty": int(sline.product_uom_qty or 1),
                "notes_line": "\n".join(filter(None, extra_notes)),
            }))
        if not lines:
            return
        # Address fallback chain: per-line indigo_install_address →
        # shipping partner → billing partner.
        if per_line_address:
            client_address = per_line_address
        else:
            client_address = "%s\n%s, %s %s" % (
                ship.street or "",
                ship.city or "",
                ship.state_id.name if ship.state_id else "",
                ship.zip or "",
            )
        indigo_order = IndigoOrder.create({
            "dealer_id": dealer.id,
            "dealer_ref": per_line_ref or self.client_order_ref or self.name,
            "client_name": client_name,
            "client_phone": per_line_phone or (ship.phone or partner.phone or ""),
            "client_email": (ship.email or partner.email or ""),
            "client_address": client_address,
            "line_ids": lines,
            "notes": "Generada automaticamente desde sale.order %s." % self.name,
        })
        self.indigo_order_id = indigo_order.id
        indigo_order.message_post(
            body="Vinculada a venta <a href='/odoo/action-sale.action_orders/%d'>%s</a>." % (
                self.id, self.name
            )
        )
