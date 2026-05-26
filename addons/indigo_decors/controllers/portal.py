# -*- coding: utf-8 -*-
import base64
import logging

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

_logger = logging.getLogger(__name__)


class InstallerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "install_count" in counters:
            partner = request.env.user.partner_id
            values["install_count"] = request.env["indigo.order"].sudo().search_count(
                [("installer_ids", "in", partner.id)]
            )
        return values

    @http.route(["/my/installs"], type="http", auth="user", website=True)
    def portal_installer_orders(self, **kw):
        partner = request.env.user.partner_id
        Order = request.env["indigo.order"].sudo()
        orders = Order.search(
            [("installer_ids", "in", partner.id)],
            order="create_date desc",
        )
        return request.render(
            "indigo_decors.portal_installer_orders",
            {
                "orders": orders,
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
                body=(note or "Foto subida desde portal por %s" % request.env.user.name),
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
        stage_installed = request.env.ref(
            "indigo_decors.stage_installed", raise_if_not_found=False
        )
        if stage_installed:
            order.sudo().write({"stage_id": stage_installed.id})
        return request.redirect("/my/install/%d" % order_id)

    # =============================
    # PORTAL DEALER
    # =============================

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        if "order_count" in counters:
            values["order_count"] = request.env["indigo.order"].sudo().search_count(
                [("dealer_id", "=", partner.id)]
            )
        return values

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
        return request.redirect("/my/order/%d" % order_id)

    # =============================
    # TRACKING PUBLICO (sin login)
    # =============================

    @http.route(["/track/<string:token>"], type="http", auth="public", website=True)
    def portal_public_tracking(self, token, **kw):
        order = request.env["indigo.order"].sudo().search(
            [("access_token", "=", token)], limit=1
        )
        if not order:
            return request.render("indigo_decors.portal_public_tracking_not_found", {})
        return request.render(
            "indigo_decors.portal_public_tracking",
            {"order": order, "page_name": "public_tracking"},
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
        i = 1
        while True:
            design_code = post.get("line_design_%d" % i)
            if design_code is None:
                break
            design_code = design_code.strip()
            if design_code:
                try:
                    design = Design.search([("code", "=", design_code)], limit=1)
                    width = float(post.get("line_width_%d" % i) or 0)
                    height = float(post.get("line_height_%d" % i) or 0)
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
                    _logger.warning("Skipping invalid line %d: %s", i, e)
            i += 1
            if i > 50:  # sanity bound
                break
        if line_vals:
            order_vals["line_ids"] = line_vals
        order = Order.create(order_vals)
        return request.redirect("/my/order/%d" % order.id)
