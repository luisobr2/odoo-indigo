# -*- coding: utf-8 -*-
from odoo import fields, models


class IndigoOrderIncident(models.Model):
    _name = "indigo.order.incident"
    _description = "Incidencia / anotacion sobre una orden Indigo"
    _order = "date desc, id desc"

    order_id = fields.Many2one("indigo.order", required=True, ondelete="cascade", index=True)
    user_id = fields.Many2one(
        "res.users",
        string="Reportado por",
        default=lambda self: self.env.user,
        required=True,
    )
    date = fields.Datetime(string="Fecha", default=fields.Datetime.now, required=True)
    category = fields.Selection(
        [
            ("measure", "Medida"),
            ("painting", "Pintura"),
            ("client", "Cliente"),
            ("install", "Instalacion"),
            ("other", "Otro"),
        ],
        string="Categoria",
        default="other",
        required=True,
    )
    description = fields.Text(string="Descripcion", required=True)
    attachment_ids = fields.Many2many("ir.attachment", string="Adjuntos")
