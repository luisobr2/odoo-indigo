# -*- coding: utf-8 -*-
import base64
import logging

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

_logger = logging.getLogger(__name__)


class InstallerPortal(CustomerPortal):

    # NOTE: there used to be TWO _prepare_home_portal_values defined in
    # this class (one for installer, one for dealer). Python's later
    # definition silently replaced the former so install_count never
    # showed up. Merged into the single override below.
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        if "install_count" in counters:
            values["install_count"] = request.env["indigo.order"].sudo().search_count(
                [("installer_ids", "in", partner.id)]
            )
        if "order_count" in counters:
            values["order_count"] = request.env["indigo.order"].sudo().search_count(
                [("dealer_id", "=", partner.id)]
            )
        return values

    @http.route(["/my", "/my/home"], type="http", auth="user", website=True)
    def home(self, **kw):
        """Skip the noisy default /my home for installer-only users and
        send them straight to /my/installs. Other portal users (dealers,
        admins) still see the standard portal home.

        Overrides CustomerPortal.home exactly (same URL + method name)
        so route registration replaces the parent's binding.
        """
        user = request.env.user
        is_installer_only = (
            user.has_group("indigo_decors.group_indigo_contractor")
            and not user.has_group("indigo_decors.group_indigo_manager")
            and not user.has_group("indigo_decors.group_indigo_office")
            and not user.has_group("indigo_decors.group_indigo_user")
        )
        if is_installer_only:
            return request.redirect("/my/installs")
        return super().home(**kw)

    @http.route(["/my/installs"], type="http", auth="user", website=True)
    def portal_installer_orders(self, q=None, **kw):
        """Mobile-first list of orders assigned to the current installer.

        Optional `?q=...` search filter that matches:
          - order name (e.g. 'IND/2026/00009' or just '0009')
          - client name (e.g. 'Karan')
          - dealer ref (the dealer-side ticket id)
        Case-insensitive partial match.
        """
        partner = request.env.user.partner_id
        domain = [("installer_ids", "in", partner.id)]
        q = (q or "").strip()
        if q:
            domain += [
                "|", "|",
                ("name", "ilike", q),
                ("client_name", "ilike", q),
                ("dealer_ref", "ilike", q),
            ]
        Order = request.env["indigo.order"].sudo()
        orders = Order.search(domain, order="installation_date asc, create_date desc")
        return request.render(
            "indigo_decors.portal_installer_orders",
            {
                "orders": orders,
                "search_query": q,
                "page_name": "installer_orders",
            },
        )

    @http.route(["/my/install/<int:order_id>"], type="http", auth="user", website=True)
    def portal_installer_order_detail(self, order_id, **kw):
        partner = request.env.user.partner_id
        order = request.env["indigo.order"].sudo().search(
            [("id", "=", order_id), ("installer_ids", "in", partner.id)], limit=1
        )
        if not order:
            return request.redirect("/my")
        return request.render(
            "indigo_decors.portal_installer_order_detail",
            {
                "order": order,
                "page_name": "installer_order_detail",
            },
        )

    @http.route(
        ["/my/install/<int:order_id>/upload"],
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def portal_installer_upload(self, order_id, **kw):
        partner = request.env.user.partner_id
        order = request.env["indigo.order"].sudo().search(
            [("id", "=", order_id), ("installer_ids", "in", partner.id)], limit=1
        )
        if not order:
            return request.redirect("/my")
        photo = kw.get("photo")
        note = (kw.get("note") or "").strip()
        if photo and getattr(photo, "filename", None):
            data = photo.read()
            attachment = request.env["ir.attachment"].sudo().create({
                "name": photo.filename,
                "datas": base64.b64encode(data),
                "res_model": "indigo.order",
                "res_id": order.id,
                "mimetype": photo.mimetype or "application/octet-stream",
            })
            order.sudo().message_post(
                body=(note or "Photo uploaded from portal by %s" % request.env.user.name),
                attachment_ids=[attachment.id],
            )
        return request.redirect("/my/install/%d" % order_id)

    @http.route(
        ["/my/install/<int:order_id>/mark-installed"],
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def portal_installer_mark_installed(self, order_id, **kw):
        partner = request.env.user.partner_id
        order = request.env["indigo.order"].sudo().search(
            [("id", "=", order_id), ("installer_ids", "in", partner.id)], limit=1
        )
        if not order:
            return request.redirect("/my")
        # Capturar firma del cliente (base64 PNG desde canvas)
        signature_b64 = (kw.get("signature_data") or "").strip()
        signer_name = (kw.get("signer_name") or "").strip()
        vals = {}
        if signature_b64 and signature_b64.startswith("data:image/png;base64,"):
            from odoo import fields as f
            vals["client_signature"] = signature_b64.split(",", 1)[1]
            vals["client_signature_date"] = f.Datetime.now()
            vals["client_signature_name"] = signer_name or order.client_name
        stage_installed = request.env.ref(
            "indigo_decors.stage_installed", raise_if_not_found=False
        )
        if stage_installed:
            vals["stage_id"] = stage_installed.id
        if vals:
            order.sudo().write(vals)
            if signature_b64:
                order.sudo().message_post(
                    body="Customer signed on site (%s) - installation confirmed by %s." % (
                        vals.get("client_signature_name") or "?", request.env.user.name
                    )
                )
        return request.redirect("/my/install/%d" % order_id)

    # =============================
    # PORTAL DEALER
    # =============================
    # (_prepare_home_portal_values is now merged with the installer one above
    # — having two separate definitions caused only the second to be active.)

    @http.route(["/my/orders"], type="http", auth="user", website=True)
    def portal_dealer_orders(self, **kw):
        partner = request.env.user.partner_id
        orders = request.env["indigo.order"].sudo().search(
            [("dealer_id", "=", partner.id)], order="create_date desc"
        )
        return request.render(
            "indigo_decors.portal_dealer_orders",
            {"orders": orders, "page_name": "dealer_orders"},
        )

    @http.route(["/my/order/<int:order_id>"], type="http", auth="user", website=True)
    def portal_dealer_order_detail(self, order_id, **kw):
        partner = request.env.user.partner_id
        order = request.env["indigo.order"].sudo().search(
            [("id", "=", order_id), ("dealer_id", "=", partner.id)], limit=1
        )
        if not order:
            return request.redirect("/my")
        return request.render(
            "indigo_decors.portal_dealer_order_detail",
            {"order": order, "page_name": "dealer_order_detail"},
        )

    @http.route(["/my/order/new"], type="http", auth="user", website=True)
    def portal_dealer_order_new(self, **kw):
        partner = request.env.user.partner_id
        if not partner.is_indigo_dealer:
            return request.redirect("/my")
        designs = request.env["indigo.design"].sudo().search([("active", "=", True)])
        return request.render(
            "indigo_decors.portal_dealer_order_new",
            {
                "designs": designs,
                "partner": partner,
                "page_name": "dealer_order_new",
            },
        )

    @http.route(["/my/order/customers.json"], type="http", auth="user", website=True, methods=["GET"], csrf=False)
    def portal_dealer_customers(self, q="", **kw):
        """Autocomplete endpoint: returns past homeowners (client_name +
        phone + email + address) that THIS dealer has previously used,
        so they don't retype the same data each order.

        Picks the most-recent occurrence of each distinct client_name."""
        import json
        partner = request.env.user.partner_id
        if not partner.is_indigo_dealer:
            return request.make_response(json.dumps([]), [("Content-Type", "application/json")])
        domain = [
            ("dealer_id", "=", partner.id),
            ("client_name", "!=", False),
            ("client_name", "!=", ""),
        ]
        if q:
            domain.append(("client_name", "ilike", q.strip()))
        # Most recent first; we dedupe in Python to keep the latest
        # phone/email/address per homeowner.
        orders = request.env["indigo.order"].sudo().search(
            domain, order="create_date desc", limit=200,
        )
        seen = {}
        for o in orders:
            key = (o.client_name or "").strip().lower()
            if not key or key in seen:
                continue
            seen[key] = {
                "name": o.client_name,
                "phone": o.client_phone or "",
                "email": o.client_email or "",
                "address": o.client_address or "",
            }
            if len(seen) >= 20:
                break
        return request.make_response(
            json.dumps(list(seen.values())),
            headers=[("Content-Type", "application/json")],
        )

    @http.route(["/my/order/<int:order_id>/duplicate"], type="http", auth="user", methods=["POST"], website=True, csrf=True)
    def portal_dealer_order_duplicate(self, order_id, **kw):
        partner = request.env.user.partner_id
        order = request.env["indigo.order"].sudo().search(
            [("id", "=", order_id), ("dealer_id", "=", partner.id)], limit=1
        )
        if not order:
            return request.redirect("/my")
        new = order.copy({
            "stage_id": request.env.ref("indigo_decors.stage_new_order").id,
            "client_name": (order.client_name or "") + " (copia)",
            "payment_state": "unpaid",
            "on_hold": False,
            "hold_reason": False,
        })
        return request.redirect("/my/order/%d" % new.id)

    @http.route(["/my/order/<int:order_id>/upload-receipt"], type="http", auth="user", methods=["POST"], website=True, csrf=True)
    def portal_dealer_upload_receipt(self, order_id, **kw):
        import base64
        partner = request.env.user.partner_id
        order = request.env["indigo.order"].sudo().search(
            [("id", "=", order_id), ("dealer_id", "=", partner.id)], limit=1
        )
        if not order:
            return request.redirect("/my")
        f = kw.get("receipt")
        if f and getattr(f, "filename", None):
            attachment = request.env["ir.attachment"].sudo().create({
                "name": f.filename,
                "datas": base64.b64encode(f.read()),
                "res_model": "indigo.order",
                "res_id": order.id,
                "mimetype": f.mimetype or "application/octet-stream",
            })
            order.sudo().write({"payment_receipt_ids": [(4, attachment.id)]})
            order.sudo().message_post(body="Recibo de pago subido por %s." % request.env.user.name,
                                      attachment_ids=[attachment.id])
            # Notificar a managers
            managers = request.env.ref("indigo_decors.group_indigo_manager").users
            for mgr in managers:
                if mgr.partner_id and mgr.partner_id.email:
                    order.sudo().message_subscribe(partner_ids=[mgr.partner_id.id])
        return request.redirect("/my/order/%d" % order_id)

    # =============================
    # TRACKING PUBLICO (sin login)
    # =============================

    @http.route(["/track/<string:token>"], type="http", auth="public", website=True)
    def portal_public_tracking(self, token, **kw):
        order = request.env["indigo.order"].sudo().search(
            [("access_token", "=", token)], limit=1
        )
        # Stop exposing the page once the order is finished — limits the window
        # the capability URL stays live (the token never expires by itself).
        if not order or order.stage_id.code == "closed":
            return request.render("indigo_decors.portal_public_tracking_not_found", {})
        # Mask the homeowner name to first-name + last-initial so a leaked
        # tracking link doesn't hand out the full name.
        parts = (order.client_name or "").split()
        masked_name = parts[0] if parts else ""
        if len(parts) > 1 and parts[-1]:
            masked_name += " " + parts[-1][0].upper() + "."
        return request.render(
            "indigo_decors.portal_public_tracking",
            {"order": order, "masked_name": masked_name, "page_name": "public_tracking"},
        )

    @http.route(
        ["/my/order/new"],
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def portal_dealer_order_create(self, **post):
        partner = request.env.user.partner_id
        if not partner.is_indigo_dealer:
            return request.redirect("/my")
        # Header fields
        Order = request.env["indigo.order"].sudo()
        order_vals = {
            "dealer_id": partner.id,
            "client_name": (post.get("client_name") or "").strip() or "(sin nombre)",
            "client_phone": post.get("client_phone") or "",
            "client_email": post.get("client_email") or "",
            "client_address": post.get("client_address") or "",
            "dealer_ref": post.get("dealer_ref") or "",
            "priv_ref": post.get("priv_ref") or "",
            "notes": post.get("notes") or "",
        }
        # Lines: keys like line_design_1, line_width_1, etc.
        line_vals = []
        Design = request.env["indigo.design"].sudo()
        # Parser handles "36", "36.5" or "36 1/8" (inches + eighths US standard)
        parse_dim = request.env["sale.order"]._parse_inches_eighths
        # Iterate up to 50 rows; skip missing indices (user may have deleted rows
        # via the JS "Remove row" button which leaves index gaps in the form).
        for i in range(1, 51):
            design_code = (post.get("line_design_%d" % i) or "").strip()
            width_raw = (post.get("line_width_%d" % i) or "").strip()
            height_raw = (post.get("line_height_%d" % i) or "").strip()
            # Skip empty rows entirely
            if not design_code and not width_raw and not height_raw:
                continue
            try:
                design = Design.search([("code", "=", design_code)], limit=1) if design_code else None
                width = parse_dim(width_raw)
                height = parse_dim(height_raw)
                qty = int(post.get("line_qty_%d" % i) or 1)
                line_vals.append((0, 0, {
                    "design_id": design.id if design else False,
                    "door_type": post.get("line_door_type_%d" % i) or "SD",
                    "color": post.get("line_color_%d" % i) or "white",
                    "glass_type": post.get("line_glass_%d" % i) or "",
                    "width": width,
                    "height": height,
                    "qty": qty,
                }))
            except (ValueError, TypeError) as e:
                _logger.warning("Skipping invalid portal-order line %d: %s", i, e)
        if line_vals:
            order_vals["line_ids"] = line_vals
        order = Order.create(order_vals)
        return request.redirect("/my/order/%d" % order.id)
