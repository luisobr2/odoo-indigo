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
