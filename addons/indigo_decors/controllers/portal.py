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
