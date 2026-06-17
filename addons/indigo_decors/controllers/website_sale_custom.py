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
import logging

from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)

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


class IndigoStorefrontOrder(http.Controller):
    """Cart-less storefront ordering.

    The dealer fills the product page form (variant + dimensions + install
    context) and submits — we create a sale.order with that single line and
    confirm it immediately, which fires the indigo_sale_bridge to produce the
    production indigo.order. No cart, no checkout pages.
    """

    @http.route("/indigo/order/submit", type="json", auth="user",
                methods=["POST"], website=True)
    def submit(self, product_id=None, add_qty=1, **kw):
        partner = request.env.user.partner_id
        dealer = _current_dealer(partner)
        if not dealer:
            return {"error": "Your account is not a registered Indigo dealer."}
        try:
            pid = int(product_id)
        except (TypeError, ValueError):
            return {"error": "Missing product."}
        product = request.env["product.product"].sudo().browse(pid)
        if not product.exists():
            return {"error": "Product not found."}
        try:
            qty = max(1, int(add_qty or 1))
        except (TypeError, ValueError):
            qty = 1

        line_vals = {
            "product_id": product.id,
            "product_uom_qty": qty,
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
            return {"error": "We couldn't place the order. Please try again or contact sales."}
        return {"ok": True, "redirect": "/indigo/order/thanks/%d" % order.id}

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
