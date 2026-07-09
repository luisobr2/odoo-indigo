# -*- coding: utf-8 -*-
"""Dedicated endpoint to write Indigo per-line custom values onto the most
recently added sale.order.line of the current cart.

Flow:
  1. PDP renders 6 inputs (customer name, dealer order ref, install address,
     install phone, door width, door height).
  2. Customer clicks 'Add to quote list' — Odoo's stock /shop/cart/update_json
     fires, creates/updates the line.
  3. theme.js detects the cart counter change, fires POST to
     /indigo/cart/update_line_meta with { product_id, kwargs… }
  4. This endpoint resolves the most recent line for that product on the
     current cart and writes the values.

Why a separate endpoint instead of overriding cart_update_json:
  - cart_update_json signature varies across Odoo minor versions and the
    override is fragile.
  - A small dedicated route is easier to call from JS, easier to audit,
    and never blocks the cart add even if it fails.
"""
import base64
import logging

from odoo import http
from odoo.http import request, Stream
from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)

# Reference uploads from the PDP order form: keep them sane so a dealer
# can't accidentally (or maliciously) push a multi-GB payload.
MAX_REFERENCE_FILES = 10
MAX_REFERENCE_TOTAL_BYTES = 25 * 1024 * 1024  # 25 MB across all files
ALLOWED_REFERENCE_MIMES = (
    "image/", "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
)

INDIGO_LINE_FIELDS = (
    "indigo_customer_name",
    "indigo_order_ref",
    "indigo_install_address",
    "indigo_install_phone",
    "indigo_door_width",
    "indigo_door_height",
)


class IndigoCartMeta(http.Controller):

    @http.route(
        "/indigo/cart/update_line_meta",
        type="json",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=False,
    )
    def update_line_meta(self, product_id, line_id=None, **kwargs):
        """Write Indigo custom fields onto a cart line.

        Accepts:
            product_id: int — the product just added
            line_id:    int (optional) — explicit sale.order.line id
            kwargs:     subset of INDIGO_LINE_FIELDS

        Returns:
            { 'ok': True, 'line_id': <int> } or { 'ok': False, 'reason': str }
        """
        values = {f: kwargs.get(f) for f in INDIGO_LINE_FIELDS if kwargs.get(f)}
        if not values:
            return {"ok": False, "reason": "no_values"}
        try:
            order = request.website.sale_get_order()
            if not order:
                return {"ok": False, "reason": "no_cart"}
            target = None
            if line_id:
                target = order.order_line.filtered(lambda l: l.id == int(line_id))
            if not target and product_id:
                target = order.order_line.filtered(
                    lambda l: l.product_id.id == int(product_id)
                ).sorted("id", reverse=True)[:1]
            if not target:
                return {"ok": False, "reason": "no_line"}
            target.write(values)
            return {"ok": True, "line_id": target.id}
        except Exception as e:
            _logger.warning("indigo update_line_meta failed: %s", e)
            return {"ok": False, "reason": "error", "detail": str(e)}


def _current_dealer(partner):
    """Return the dealer partner for the logged-in user, or empty recordset.
    A dealer is either the partner itself or its commercial parent flagged
    is_indigo_dealer (covers child contacts under a dealer company)."""
    if partner.is_indigo_dealer:
        return partner
    commercial = partner.commercial_partner_id
    if commercial and commercial.is_indigo_dealer:
        return commercial
    return partner.browse()


class IndigoDesignImage(http.Controller):
    """Serve a design's per-color door photo so the storefront PDP can swap the
    image when the dealer picks a color/finish.

    The photos live as ir.attachment on indigo.design with the color in the
    filename (e.g. ID01-DD-black.jpg) — the same store the back-office panel
    uses for its per-color gallery. Products on the storefront carry no color
    variant, so the native carousel can't do this; the PDP color <select> holds
    a data-img pointing here and theme.js swaps the main image on change.
    """

    _COLORS = ("white", "bronze", "bronze_eco", "black")
    # door-type -> filename token (CUSTOM stores SD & DD photos under one design
    # as CUSTOM-SD-black.jpg / CUSTOM-DD-black.jpg, so the type disambiguates).
    _TYPE_TOKEN = {"SD": "SD", "DD": "DD", "SIDELITE": "SDL", "SDL": "SDL"}

    @http.route("/indigo/door_image/<int:design_id>/<string:color>",
                type="http", auth="public", website=True, sitemap=False)
    def door_image(self, design_id, color, **kw):
        color = (color or "").strip().lower()
        if color not in self._COLORS:
            return request.not_found()
        Att = request.env["ir.attachment"].sudo()
        base = [("res_model", "=", "indigo.design"), ("res_id", "=", design_id)]
        att = Att.browse()
        # When a door type is given, prefer the photo whose filename carries BOTH
        # the type token AND the color. Needed for CUSTOM (SD & DD under one
        # design); harmless for standard designs (type already in the code).
        token = self._TYPE_TOKEN.get((kw.get("type") or "").strip().upper())
        if token:
            att = Att.search(base + [("name", "=ilike", "%%-%s-%%%s.%%" % (token, color))], limit=1)
            if not att:
                att = Att.search(base + [("name", "=ilike", "%%%s%%%s.%%" % (token, color))], limit=1)
        # Fallback (or no type): match "<...>-<color>." so 'bronze' doesn't grab
        # 'bronze_eco'.
        if not att:
            att = Att.search(base + [("name", "=ilike", "%%-%s.%%" % color)], limit=1)
        if not att or not att.datas:
            return request.not_found()
        response = Stream.from_attachment(att).get_response()
        response.headers["Cache-Control"] = "public, max-age=3600"
        return response


class IndigoStorefrontOrder(http.Controller):
    """Cart-less storefront ordering.

    The dealer fills the product page form (variant + dimensions + install
    context) and submits — we create a sale.order with that single line and
    confirm it immediately, which fires the indigo_sale_bridge to produce the
    production indigo.order. No cart, no checkout pages.
    """

    # type="http" (not json) because the form now carries file uploads
    # (reference photos/documents) as multipart/form-data, which the
    # JSON-RPC transport can't express. We hand-build JSON responses so the
    # PDP JS keeps reading {ok|error} the same way.
    @http.route("/indigo/order/submit", type="http", auth="user",
                methods=["POST"], website=True, csrf=True)
    def submit(self, product_id=None, add_qty=1, **kw):
        partner = request.env.user.partner_id
        dealer = _current_dealer(partner)
        if not dealer:
            return request.make_json_response(
                {"error": "Your account is not a registered Indigo dealer."})
        try:
            pid = int(product_id)
        except (TypeError, ValueError):
            return request.make_json_response({"error": "Missing product."})
        product = request.env["product.product"].sudo().browse(pid)
        if not product.exists():
            return request.make_json_response({"error": "Product not found."})
        try:
            qty = max(1, int(add_qty or 1))
        except (TypeError, ValueError):
            qty = 1

        # Brand + glass privacy are required for manufacturing.
        try:
            brand_id = int(kw.get("indigo_brand_id"))
        except (TypeError, ValueError):
            brand_id = 0
        privacy = (kw.get("indigo_glass_privacy") or "").strip()
        if not brand_id:
            return request.make_json_response({"error": "Please choose the door brand."})
        if privacy not in ("clear", "privacy"):
            return request.make_json_response({"error": "Please choose Clear or Privacy glass."})

        # Color / finish — normalize + validate the format now; whether it's
        # required depends on whether the product carries a color variant (below).
        # 'custom' is not a self-serve storefront option (needs a described color).
        color = (kw.get("indigo_color") or "").strip().lower()
        if color and color not in ("white", "bronze", "bronze_eco", "black"):
            return request.make_json_response({"error": "Invalid color."})

        # Door type (Option B): the storefront publishes one card per design
        # family and offers a type selector. Resolve the product to ORDER from
        # (family + the SELECTED type) here, server-side — this is authoritative,
        # not whatever product_id the client submitted. A fixed-type product
        # switches to the family sibling of the chosen type (color preserved);
        # a flexible / CUSTOM product keeps its product and carries the type on
        # the line.
        tmpl = product.product_tmpl_id
        src_product = product  # remember the pre-switch variant (carries its color)
        family_types = tmpl.indigo_family_types()
        sel_type = (kw.get("indigo_door_type") or "").strip()
        if len(family_types) > 1:
            if sel_type not in [ft["door_type"] for ft in family_types]:
                return request.make_json_response(
                    {"error": "Please choose the door type (Single or Double)."})
            switched = tmpl.indigo_variant_for_type(sel_type, from_variant=product)
            if switched and switched.exists():
                product = switched
                tmpl = product.product_tmpl_id
        # Type stored on the line: the picked one, else the product's fixed type.
        door_type = sel_type or tmpl.indigo_door_type or ""

        # Reconcile color with the FINAL product after any door-type switch, so a
        # family that mixes color-variant and plain siblings can't record a wrong
        # color or dead-end the dealer:
        #  - final product carries a color/finish variant -> the variant owns the
        #    color; drop any stale manual value (it would otherwise override the
        #    variant color in the bridge).
        #  - final product has NO variant but the manual color field was never
        #    rendered (the originally-viewed product had a variant) -> inherit the
        #    color from that product's variant instead of hard-blocking.
        def _has_color_variant(t):
            return any(
                ("color" in (al.attribute_id.name or "").lower()
                 or "finish" in (al.attribute_id.name or "").lower())
                for al in t.attribute_line_ids
            )
        has_color_variant = _has_color_variant(tmpl)
        if has_color_variant:
            color = ""
        elif not color and src_product.id != product.id \
                and _has_color_variant(src_product.product_tmpl_id):
            color = request.env["sale.order"]._parse_color_from_variant(src_product)

        # Color is required when the final product doesn't capture it via a variant.
        if not has_color_variant and not color:
            return request.make_json_response(
                {"error": "Please choose the color / finish."})

        try:
            parts_count = max(1, int(kw.get("indigo_parts_count") or 1))
        except (TypeError, ValueError):
            parts_count = 1

        # Read + validate uploaded reference files BEFORE creating the order,
        # so a bad upload doesn't leave a half-finished order behind.
        files = request.httprequest.files.getlist("indigo_reference_files")
        files = [f for f in files if f and f.filename]
        if len(files) > MAX_REFERENCE_FILES:
            return request.make_json_response(
                {"error": "Too many files (max %d)." % MAX_REFERENCE_FILES})
        payloads = []
        total = 0
        for f in files:
            data = f.read()
            if not data:
                continue
            total += len(data)
            if total > MAX_REFERENCE_TOTAL_BYTES:
                return request.make_json_response(
                    {"error": "Attachments are too large (max 25 MB total)."})
            mime = f.mimetype or "application/octet-stream"
            if not mime.startswith(ALLOWED_REFERENCE_MIMES):
                return request.make_json_response(
                    {"error": "Unsupported file type: %s. Use images, PDF or Word." % f.filename})
            payloads.append((f.filename, data, mime))

        line_vals = {
            "product_id": product.id,
            "product_uom_qty": qty,
            "indigo_brand_id": brand_id,
            "indigo_glass_privacy": privacy,
            "indigo_door_type": door_type or False,
            "indigo_parts_count": parts_count,
            "indigo_color": color,
            "indigo_customer_name": (kw.get("indigo_customer_name") or "").strip(),
            "indigo_order_ref": (kw.get("indigo_order_ref") or "").strip(),
            "indigo_install_address": (kw.get("indigo_install_address") or "").strip(),
            "indigo_install_phone": (kw.get("indigo_install_phone") or "").strip(),
            "indigo_door_width": (kw.get("indigo_door_width") or "").strip(),
            "indigo_door_height": (kw.get("indigo_door_height") or "").strip(),
        }
        try:
            order = request.env["sale.order"].sudo().create({
                "partner_id": dealer.id,
                "partner_invoice_id": dealer.id,
                "partner_shipping_id": dealer.id,
                "pricelist_id": partner.property_product_pricelist.id,
                "website_id": request.website.id,
                "client_order_ref": line_vals["indigo_order_ref"] or False,
                "order_line": [(0, 0, line_vals)],
            })
            order.action_confirm()
        except Exception as e:  # noqa: BLE001 — surface a clean message to the dealer
            _logger.exception("indigo storefront order submit failed: %s", e)
            return request.make_json_response(
                {"error": "We couldn't place the order. Please try again or contact sales."})

        # Attach the reference files to the production order (indigo.order) so
        # the workshop sees them in the order chatter + the panel's photos.
        # Falls back to the sale.order if the bridge didn't create one.
        if payloads:
            target = order.indigo_order_id or order
            try:
                att_ids = []
                for fname, data, mime in payloads:
                    att = request.env["ir.attachment"].sudo().create({
                        "name": fname,
                        "datas": base64.b64encode(data),
                        "res_model": target._name,
                        "res_id": target.id,
                        "mimetype": mime,
                    })
                    att_ids.append(att.id)
                if att_ids:
                    target.sudo().message_post(
                        body="Reference files attached by %s at order time (%d)." % (
                            request.env.user.name, len(att_ids)),
                        attachment_ids=att_ids,
                    )
            except Exception as e:  # noqa: BLE001 — never lose the order over an attach hiccup
                _logger.warning("indigo reference upload failed for %s: %s", order.name, e)

        return request.make_json_response(
            {"ok": True, "redirect": "/indigo/order/thanks/%d" % order.id})

    @http.route("/indigo/order/thanks/<int:order_id>", type="http", auth="user",
                website=True)
    def thanks(self, order_id, **kw):
        partner = request.env.user.partner_id
        order = request.env["sale.order"].sudo().browse(order_id)
        owners = (partner.id, partner.commercial_partner_id.id)
        if not order.exists() or order.partner_id.id not in owners:
            return request.redirect("/shop")
        return request.render("indigo_decors.storefront_order_thanks", {
            "order": order,
            "indigo_order": order.indigo_order_id,
        })


class IndigoNoCart(WebsiteSale):
    """Cart + checkout are removed from the storefront flow — ordering happens
    on the product page. Bounce the stock cart/checkout routes back to the shop."""

    @http.route()
    def cart(self, **post):
        return request.redirect("/shop")

    @http.route()
    def checkout(self, **post):
        return request.redirect("/shop")
