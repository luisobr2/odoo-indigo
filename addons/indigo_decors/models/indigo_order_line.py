# -*- coding: utf-8 -*-
from math import gcd

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
    is_privacy_glass = fields.Boolean(
        string="Vidrio privacidad",
        help="Marcar si el vidrio es de privacidad (sale como 'PRIVACY' en la etiqueta del disenador).",
    )
    customer_name = fields.Char(
        string="Cliente final (linea)",
        help="Homeowner especifico para esta pieza. Sobreescribe el cliente "
             "de la orden en la etiqueta del disenador.",
    )

    width = fields.Float(string="Ancho (in)", digits=(8, 3))
    height = fields.Float(string="Alto (in)", digits=(8, 3))
    width_label = fields.Char(string="Ancho (etiqueta)", compute="_compute_dim_labels")
    height_label = fields.Char(string="Alto (etiqueta)", compute="_compute_dim_labels")
    qty = fields.Integer(string="Cantidad", default=1, required=True)

    # SQF used to be computed as width x height x qty / 144 (frame area).
    # That is NOT what the workshop bills: the painter is paid for the
    # area of the carved/painted DESIGN, which the designer (Mario) gets
    # from a CorelDraw plugin after digitizing the door at real size.
    # So SQF is entered manually during the Digitalization stage.
    sqf = fields.Float(
        string="SQF",
        digits=(10, 2),
        help="Real decorated area in square feet. Entered manually by the "
             "designer during the Digitalization stage (from CorelDraw at "
             "real size). NOT computed from width x height — the frame is "
             "larger than the carved design.",
    )
    notes_line = fields.Char(string="Notas")

    @api.depends("width", "height")
    def _compute_dim_labels(self):
        for line in self:
            line.width_label = self._format_eighths(line.width)
            line.height_label = self._format_eighths(line.height)

    @staticmethod
    def _format_eighths(value):
        """Convert decimal inches to inches+eighths label, e.g. 24.125 -> '24 1/8'."""
        if not value:
            return ""
        # Round to nearest 1/8
        total_eighths = round(value * 8)
        whole, eighths = divmod(total_eighths, 8)
        if eighths == 0:
            return str(int(whole))
        g = gcd(eighths, 8)
        num, den = eighths // g, 8 // g
        if whole == 0:
            return "%d/%d" % (num, den)
        return "%d %d/%d" % (whole, num, den)
