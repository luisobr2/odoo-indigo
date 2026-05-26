# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IndigoOrderLine(models.Model):
    _name = "indigo.order.line"
    _description = "Pieza / puerta de una orden Indigo"
    _order = "order_id, sequence, id"

    order_id = fields.Many2one("indigo.order", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)

    design_id = fields.Many2one("indigo.design", string="Diseno")
    door_type = fields.Selection(
        [
            ("SD", "Single Door"),
            ("DD", "Double Door"),
            ("sidelite", "Door with Sidelites"),
        ],
        string="Tipo",
        required=True,
    )
    color = fields.Selection(
        [
            ("white", "White"),
            ("bronze", "Bronze"),
            ("black", "Black"),
            ("custom", "Custom"),
        ],
        string="Color",
        required=True,
        default="white",
    )
    color_custom = fields.Char(string="Color custom")
    glass_type = fields.Char(string="Tipo de vidrio", help="Ej. ESW")

    width = fields.Float(string="Ancho (in)", digits=(8, 2))
    height = fields.Float(string="Alto (in)", digits=(8, 2))
    qty = fields.Integer(string="Cantidad", default=1, required=True)

    sqf = fields.Float(
        string="SQF",
        compute="_compute_sqf",
        store=True,
        digits=(10, 2),
        help="Ancho x Alto x cantidad / 144.",
    )
    notes_line = fields.Char(string="Notas")

    @api.depends("width", "height", "qty")
    def _compute_sqf(self):
        for line in self:
            line.sqf = (line.width * line.height * line.qty) / 144.0 if line.width and line.height else 0.0
