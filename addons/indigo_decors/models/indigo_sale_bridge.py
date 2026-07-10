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
from odoo.osv import expression

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
            ("bronze_eco", "Bronze ECO"),
            ("black", "Black"),
            ("custom", "Custom"),
        ],
        string="Color default",
        default="white",
    )
    indigo_default_glass = fields.Char(string="Vidrio default", help="Ej. ESW")

    # Base dealer price for this design, shown on the storefront to logged-in
    # dealers instead of "Quote on request". Uses the BASIC tier of the design
    # price matrix (the default charge); door type comes from the product or
    # its linked design. 0 for CUSTOM / untyped products (stay quote-only).
    indigo_dealer_price = fields.Float(
        string="Dealer base price",
        compute="_compute_indigo_dealer_price",
        digits=(10, 2),
        help="Base price (basic tier) charged to a dealer for this door type. "
             "Displayed on the catalog for logged-in dealers.",
    )

    @api.depends(
        "indigo_door_type", "indigo_design_id", "indigo_design_id.dealer_price_override"
    )
    def _compute_indigo_dealer_price(self):
        # sudo: the price matrix (indigo.design.price) and indigo.design are
        # not readable by portal dealers, but the price is meant to be shown to
        # them on the catalog. Read both elevated — non-sensitive value.
        # A design's own price (dealer_price_override) wins; otherwise the base
        # price for the door type.
        Price = self.env["indigo.design.price"].sudo()
        for tmpl in self:
            design = tmpl.indigo_design_id.sudo() if tmpl.indigo_design_id else False
            override = design.dealer_price_override if design else 0.0
            if override and override > 0:
                tmpl.indigo_dealer_price = override
                continue
            door_type = tmpl.indigo_door_type or (design.door_type if design else False)
            tmpl.indigo_dealer_price = Price.price_for(door_type, "basic") if door_type else 0.0

    def indigo_family_types(self):
        """Door types available in this design's family, each pointing at the
        product to order — powers the storefront door-type selector so a single
        published card can order Single, Double or Sidelite.

        Returns a list ordered SD, DD, SDL (design_id powers the per-type image
        swap on the storefront — the photo follows the picked Single/Double):
            [{'door_type': 'SD', 'label': 'Single Door', 'product_id': <int>, 'design_id': <int>}, ...]

        - Fixed-type product (e.g. ID01-DD): finds the sibling type products by
          family code; each option switches the submitted product to the right
          record so design_id and door_type stay consistent.
        - Flexible product (CUSTOM, no fixed type): the three types all point at
          THIS product; the type is carried on the line, no switching.
        """
        self.ensure_one()
        LABELS = {"SD": "Single Door", "DD": "Double Door", "sidelite": "Door with Sidelites"}
        ORDER = {"SD": 0, "DD": 1, "sidelite": 2}
        design = self.indigo_design_id
        my_type = self.indigo_door_type or (design.door_type if design else False)

        # Flexible / CUSTOM (no fixed type): pick any type on the same product.
        if not my_type:
            variant = self.product_variant_id
            pid = variant.id if variant else 0
            did = design.id if design else False
            return [{"door_type": dt, "label": LABELS[dt], "product_id": pid, "design_id": did}
                    for dt in ("SD", "DD", "sidelite")]

        # Fixed type: gather sibling type products in the same family.
        code = (design.code if design else (self.default_code or self.name)) or ""
        m = re.match(r"^(.+)-(SD|DD|SDL)$", code, re.I)
        family = m.group(1) if (m and len(m.group(1)) >= 2) else code
        codes = ["%s-SD" % family, "%s-DD" % family, "%s-SDL" % family]
        tmpls = self.sudo().search([
            ("is_indigo_design", "=", True),
            "|", ("indigo_design_id.code", "in", codes), ("default_code", "in", codes),
        ]) if family else self.browse()
        seen = {}
        for t in tmpls:
            dt = t.indigo_door_type or (t.indigo_design_id.door_type if t.indigo_design_id else False)
            v = t.product_variant_id
            if dt and dt not in seen and v:
                seen[dt] = {"door_type": dt, "label": LABELS.get(dt, dt), "product_id": v.id,
                            "design_id": t.indigo_design_id.id if t.indigo_design_id else False}
        # Guarantee this product's own type is present even if the search missed.
        if my_type not in seen and self.product_variant_id:
            seen[my_type] = {"door_type": my_type, "label": LABELS.get(my_type, my_type),
                             "product_id": self.product_variant_id.id,
                             "design_id": design.id if design else False}
        return [seen[k] for k in sorted(seen, key=lambda x: ORDER.get(x, 99))]

    def indigo_variant_for_type(self, door_type, from_variant=None):
        """Resolve the product.product to ORDER for the requested door type
        within this design's family. Server-side authority for the storefront
        door-type selector: the controller calls this so the ordered product is
        derived from (family + selected type), never from client-side JS.

        - Flexible / CUSTOM product (no fixed type): stays on this product; the
          type is carried on the sale line, no switch.
        - Fixed-type product where the requested type differs: switches to the
          sibling template of that type. When the sibling carries color/finish
          variants it returns the variant matching `from_variant`'s color (so a
          Bronze pick on the Double card orders the Bronze Single); otherwise
          the sibling's single variant. Empty recordset if no such sibling.
        """
        self.ensure_one()
        Product = self.env["product.product"].sudo()
        if door_type not in ("SD", "DD", "sidelite"):
            return Product.browse()
        design = self.indigo_design_id
        my_type = self.indigo_door_type or (design.door_type if design else False)

        # Flexible / CUSTOM: the type rides on the line, product doesn't change.
        if not my_type:
            return self.product_variant_id
        # Same type requested: keep the submitted variant (it carries the color).
        if door_type == my_type:
            if from_variant and from_variant.product_tmpl_id == self:
                return from_variant
            return self.product_variant_id

        # Different fixed type: find the sibling template of the requested type.
        code = (design.code if design else (self.default_code or self.name)) or ""
        m = re.match(r"^(.+)-(SD|DD|SDL)$", code, re.I)
        family = m.group(1) if (m and len(m.group(1)) >= 2) else code
        if not family:
            return Product.browse()
        codes = ["%s-SD" % family, "%s-DD" % family, "%s-SDL" % family]
        sibling = self.sudo().search([
            ("is_indigo_design", "=", True),
            "|", ("indigo_design_id.code", "in", codes), ("default_code", "in", codes),
        ]).filtered(
            lambda t: (t.indigo_door_type
                       or (t.indigo_design_id.door_type if t.indigo_design_id else False)) == door_type
        )[:1]
        if not sibling:
            return Product.browse()

        # Preserve color when the sibling carries color/finish variants.
        if from_variant:
            cur_color = from_variant.product_template_variant_value_ids.mapped(
                "product_attribute_value_id"
            ).filtered(
                lambda av: "color" in (av.attribute_id.name or "").lower()
                or "finish" in (av.attribute_id.name or "").lower()
            )
            if cur_color:
                match = sibling.product_variant_ids.filtered(
                    lambda v: cur_color <= v.product_template_variant_value_ids.mapped(
                        "product_attribute_value_id")
                )[:1]
                if match:
                    return match
        return sibling.product_variant_id

    # Door types available in this design's family, comma-separated ("SD,DD").
    # Powers the /shop type filter's hide. Not an @api.depends compute (it reads
    # sibling products, which isn't a clean dependency) — populated by
    # _indigo_compute_avail_types, recomputed on deploy via
    # scripts/recompute_avail_types.py after adding designs.
    indigo_avail_types = fields.Char(
        string="Available door types (storefront)",
        help="Comma-separated door types available in this design's family "
             "(e.g. 'SD,DD'). Powers the /shop type filter's hide.",
    )

    def _indigo_compute_avail_types(self):
        for tmpl in self:
            if not tmpl.is_indigo_design:
                tmpl.indigo_avail_types = False
                continue
            types = [f["door_type"] for f in tmpl.indigo_family_types()]
            tmpl.indigo_avail_types = ",".join(types) if types else False


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
    indigo_brand_id = fields.Many2one(
        "indigo.brand",
        string="Brand (Indigo)",
        help="Window/door brand for this line — drives the paint tone. "
             "Captured on the storefront product page.",
    )
    indigo_glass_privacy = fields.Selection(
        [("clear", "Clear"), ("privacy", "Privacy")],
        string="Glass (Indigo)",
        help="Clear vs privacy glass — clear needs an extra coat behind "
             "the design. Captured on the storefront product page.",
    )
    indigo_door_type = fields.Selection(
        [("SD", "Single Door"), ("DD", "Double Door"), ("sidelite", "Door with Sidelites")],
        string="Door type (Indigo)",
        help="Per-line door type. Only used for flexible products (CUSTOM) "
             "where the type isn't fixed on the product and the dealer picks "
             "it on the order form. Normal products keep their fixed type.",
    )
    indigo_parts_count = fields.Integer(
        string="Pieces (Indigo)",
        help="Number of cut pieces/panels this door is made of. Captured on the "
             "order form and copied to the production order line.",
    )
    indigo_color = fields.Selection(
        [
            ("white", "White"),
            ("bronze", "Bronze"),
            ("bronze_eco", "Bronze ECO"),
            ("black", "Black"),
            ("custom", "Custom"),
        ],
        string="Color / Finish (Indigo)",
        help="Finish/color picked on the storefront order form. Copied to the "
             "production order line; falls back to the variant/template default "
             "when not set.",
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

    def _match_existing_dealer(self, partner):
        """Try to match a guest-checkout partner to an existing Indigo dealer.

        Matching strategy (first match wins):
          1. Exact email match against any partner with is_indigo_dealer=True
             OR any of their child contacts (employees of that dealer).
          2. Normalized company-name match (lowercase, stripped of common
             corp suffixes like 'LLC', 'Inc', 'Corp').

        Returns the matched dealer res.partner or empty recordset.
        """
        Partner = self.env["res.partner"]
        # 1) Email match — most reliable signal
        email = (partner.email or "").strip().lower()
        if email:
            # direct match on dealer record
            match = Partner.search([
                ("is_indigo_dealer", "=", True),
                ("email", "=ilike", email),
            ], limit=1)
            if match:
                return match
            # match on any contact under a dealer (commercial entity)
            child = Partner.search([
                ("email", "=ilike", email),
                ("parent_id.is_indigo_dealer", "=", True),
            ], limit=1)
            if child:
                return child.parent_id
        # 2) Normalized company-name match
        raw = partner.commercial_company_name or partner.name or ""
        norm = self._normalize_company(raw)
        if norm and len(norm) >= 3:
            dealers = Partner.search([("is_indigo_dealer", "=", True)])
            for d in dealers:
                if self._normalize_company(d.name) == norm:
                    return d
        return Partner

    @staticmethod
    def _normalize_company(name):
        """Lowercase + strip whitespace + remove common corp suffixes.
        E.g. 'Lock Tight LLC' / 'Lock Tight, Inc.' both → 'lock tight'."""
        if not name:
            return ""
        s = name.strip().lower()
        # Strip well-known corp suffixes (with optional trailing dot)
        s = re.sub(r"\b(llc|inc|corp|corporation|ltd|limited|sa|s\.a\.|co)\.?\b", "", s)
        # Drop ALL stray punctuation (commas, dots, semicolons left after suffix removal)
        s = re.sub(r"[.,;:]+", "", s)
        # Collapse internal whitespace
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _create_indigo_order_from_sale(self):
        """Crea la indigo.order replicando partner + lineas.
        Usa los campos custom de sale.order.line (indigo_customer_name,
        indigo_install_address, etc.) si están seteados, sino cae al partner."""
        self.ensure_one()
        IndigoOrder = self.env["indigo.order"]
        partner = self.partner_id
        ship = self.partner_shipping_id or partner
        # Si el partner es dealer Indigo, lo seteamos como dealer.
        # Si NO lo es (caso típico: checkout anonimo, Odoo creó partner
        # nuevo desde el form), intentamos auto-matchear con un dealer
        # existente por email o nombre antes de caer al fallback B2C.
        if partner.is_indigo_dealer:
            dealer = partner
            client_name = ship.name or partner.name
        else:
            matched_dealer = self._match_existing_dealer(partner)
            if matched_dealer:
                # Promover ESTE partner a dealer y dejarlo vinculado al
                # match para que futuras órdenes del mismo email/empresa
                # ya no necesiten matchear de nuevo.
                partner.write({
                    "is_indigo_dealer": True,
                    "indigo_dealer_code": matched_dealer.indigo_dealer_code or False,
                    "indigo_default_price_per_sqf": matched_dealer.indigo_default_price_per_sqf,
                    "parent_id": matched_dealer.id if not partner.parent_id else partner.parent_id.id,
                })
                dealer = matched_dealer
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
            # Per-line type (CUSTOM/flexible, picked on the form) wins; then the
            # product's fixed type; then a guess from the code.
            door_type = sline.indigo_door_type or tmpl.indigo_door_type or self._parse_door_type_from_code(
                sline.product_id.default_code or tmpl.default_code
            ) or "SD"
            # Explicit per-line color from the storefront form wins; then the
            # variant's Finish attribute; then the template default.
            color = (
                sline.indigo_color
                or self._parse_color_from_variant(sline.product_id)
                or tmpl.indigo_default_color
            )
            is_privacy, glass_brand = self._parse_attrs_from_variant(sline.product_id)
            # Explicit per-line brand/privacy captured on the PDP form take
            # precedence over whatever we inferred from variant attributes.
            brand_id = sline.indigo_brand_id.id if sline.indigo_brand_id else False
            if sline.indigo_glass_privacy:
                glass_privacy = sline.indigo_glass_privacy
                is_privacy = glass_privacy == "privacy"
            else:
                glass_privacy = "privacy" if is_privacy else "clear"
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
                "glass_privacy": glass_privacy,
                "brand_id": brand_id,
                "customer_name": sline.indigo_customer_name or "",
                "width": line_width,
                "height": line_height,
                "qty": int(sline.product_uom_qty or 1),
                "parts_count": int(sline.indigo_parts_count or 1),
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


class Website(models.Model):
    _inherit = "website"

    def sale_product_domain(self):
        """Storefront /shop base domain + the Indigo door-type filter.

        When the shop URL carries ?type=SD|DD, restrict to families that have
        that door type (indigo_avail_types). Color never narrows the set (all
        designs come in every color) — it only changes the card image, handled
        in the theme. Scoped to /shop paths so other callers are untouched.
        """
        domain = super().sale_product_domain()
        try:
            from odoo.http import request
            if request and request.httprequest.path.startswith("/shop"):
                door_type = self.indigo_shop_filters()["type"]
                if door_type:
                    domain = expression.AND([domain, [("indigo_avail_types", "like", door_type)]])
        except Exception:  # noqa: BLE001 — never break the shop over the filter
            pass
        return domain

    def indigo_shop_filters(self):
        """Validated (type, color) from the current /shop request, read straight
        from request.params so the theme can render the filter bar and swap card
        images without relying on qcontext propagation into products_item.

        Returns {'type': 'SD'|'DD'|'', 'color': 'white'|'bronze'|'black'|''}.
        """
        dt = dc = ""
        try:
            from odoo.http import request
            if request:
                dt = (request.params.get("type") or "").strip().upper()
                dc = (request.params.get("color") or "").strip().lower()
        except Exception:  # noqa: BLE001
            pass
        return {
            "type": dt if dt in ("SD", "DD") else "",
            "color": dc if dc in ("white", "bronze", "black") else "",
        }
