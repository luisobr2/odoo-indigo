# -*- coding: utf-8 -*-
from math import gcd

from odoo import api, fields, models


class IndigoOrderLine(models.Model):
    _name = "indigo.order.line"
    _description = "Pieza / puerta de una orden Indigo"
    _order = "order_id, sequence, id"
    # Track changes so Edit Order writes (and any direct Odoo edits) end
    # up in the parent order's chatter. Without this, switching width or
    # color on a line silently disappears into the DB.
    _inherit = ["mail.thread"]

    order_id = fields.Many2one("indigo.order", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)

    design_id = fields.Many2one("indigo.design", string="Diseno", tracking=True)
    door_type = fields.Selection(
        [
            ("SD", "Single Door"),
            ("DD", "Double Door"),
            ("sidelite", "Door with Sidelites"),
        ],
        string="Tipo",
        required=True,
        tracking=True,
    )
    color = fields.Selection(
        [
            ("white", "White"),
            ("bronze", "Bronze"),
            ("bronze_eco", "Bronze ECO"),
            ("black", "Black"),
            ("custom", "Custom"),
        ],
        string="Color",
        required=True,
        default="white",
        tracking=True,
    )
    color_custom = fields.Char(string="Color custom", tracking=True)
    glass_type = fields.Char(string="Tipo de vidrio", help="Ej. ESW", tracking=True)

    # ---------- CNC production specs ----------
    # Material the CNC operator cuts (ACM = aluminum composite). Majela's
    # 2026-06-08 mockup review made these visible on the CNC stage view.
    material = fields.Selection(
        [
            ("acm_white", "ACM White"),
            ("acm_black", "ACM Black"),
            ("acm_bronze", "ACM Bronze"),
        ],
        string="Material",
        tracking=True,
    )
    thickness = fields.Selection(
        [
            ("3mm", "3mm"),
            ("4mm", "4mm"),
            ("6mm", "6mm"),
        ],
        string="Thickness",
        tracking=True,
    )

    # ---------- Painting sides ----------
    # "Lados de la puerta" — number of faces the painter has to paint.
    # Single door = 2 (front + back). Sidelites = 4. Etc.
    paint_sides = fields.Integer(
        string="Sides to paint",
        default=2,
        tracking=True,
        help="Number of door faces to paint (informational for the painter). "
             "NOTE: the painter payout is $8 x SQF only — it does NOT multiply "
             "by sides or by qty. Do not wire this field into the payout.",
    )

    # ---------- Digitalization measurements ----------
    # Margins for sidelite designs (gap from door edge to glass).
    sidelite_margin_left = fields.Float(
        string="Left margin (in)",
        digits=(8, 3),
        help="Left-side margin from the door edge to the glass / design "
             "boundary. Used by the designer to calibrate the CorelDraw plot.",
    )
    sidelite_margin_right = fields.Float(
        string="Right margin (in)",
        digits=(8, 3),
        help="Right-side margin from the door edge to the glass / design "
             "boundary.",
    )
    brand_id = fields.Many2one(
        "indigo.brand",
        string="Brand",
        help="Window/door brand. Affects the paint type that must be used; "
             "Mario picks the brand when entering measurements.",
    )
    # Privacy / Clear glass: was a Boolean before, Majela clarified in the
    # 2026-06-07 review that "PRIVACY or CLEAR — they always have one or the
    # other, and it interferes with production". So we model it as a real
    # selection. Computed field `is_privacy_glass` is kept as a backwards-
    # compatibility helper so existing reports + the dashboard keep working.
    glass_privacy = fields.Selection(
        [
            ("clear", "Clear"),
            ("privacy", "Privacy"),
        ],
        string="Privacy",
        default="clear",
        tracking=True,
        help="Clear glass vs privacy glass — affects paint type used.",
    )
    is_privacy_glass = fields.Boolean(
        string="Vidrio privacidad",
        compute="_compute_is_privacy_glass",
        store=True,
        help="True when glass_privacy is 'privacy'. Auto-derived for "
             "compatibility with existing QWeb reports and dashboard queries.",
    )

    @api.depends("glass_privacy")
    def _compute_is_privacy_glass(self):
        for line in self:
            line.is_privacy_glass = line.glass_privacy == "privacy"

    customer_name = fields.Char(
        string="Cliente final (linea)",
        help="Homeowner especifico para esta pieza. Sobreescribe el cliente "
             "de la orden en la etiqueta del disenador.",
    )

    width = fields.Float(string="Ancho (in)", digits=(8, 3), tracking=True)
    height = fields.Float(string="Alto (in)", digits=(8, 3), tracking=True)
    width_label = fields.Char(string="Ancho (etiqueta)", compute="_compute_dim_labels")
    height_label = fields.Char(string="Alto (etiqueta)", compute="_compute_dim_labels")
    qty = fields.Integer(string="Cantidad", default=1, required=True, tracking=True)
    parts_count = fields.Integer(
        string="Pieces",
        default=1,
        tracking=True,
        help="Number of cut pieces/panels this door is made of. Entered on the "
             "order; printed as 'Parts' on the designer label and shown to CNC.",
    )

    # ---------- Dealer pricing (by design model, not SQF) ----------
    # The dealer is charged a fixed base price per door by its model
    # (door_type x design_tier). 'custom' tier uses a manual price.
    design_tier = fields.Selection(
        [
            ("basic", "Basic"),
            ("full_partial", "Full / Partial"),
            ("custom", "Custom"),
        ],
        string="Design tier",
        default="basic",
        required=True,
        tracking=True,
        help="Price tier per the design model price list.",
    )
    custom_price = fields.Float(
        string="Custom price (USD)",
        digits=(10, 2),
        tracking=True,
        help="Manual base price per door when the tier is Custom.",
    )
    unit_price = fields.Float(
        string="Unit price (USD)",
        compute="_compute_unit_price",
        store=True,
        digits=(10, 2),
        help="Base price per door: from the design model price matrix, or "
             "the custom price when the tier is Custom.",
    )
    line_charge = fields.Float(
        string="Line charge (USD)",
        compute="_compute_unit_price",
        store=True,
        digits=(12, 2),
        help="qty x unit_price — what the dealer is charged for this line.",
    )

    @api.depends("door_type", "design_tier", "custom_price", "qty")
    def _compute_unit_price(self):
        Price = self.env["indigo.design.price"]
        for line in self:
            if line.design_tier == "custom":
                unit = line.custom_price or 0.0
            else:
                unit = Price.price_for(line.door_type, line.design_tier)
            line.unit_price = unit
            line.line_charge = (line.qty or 0) * unit

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
            line.width_label = self._format_sixteenths(line.width)
            line.height_label = self._format_sixteenths(line.height)

    @staticmethod
    def _format_sixteenths(value):
        """Convert decimal inches to inches+sixteenths label, e.g. 24.9375 -> '24 15/16'.

        Snap precision matches the FractionalInchInput on the Next.js
        panel — both use 1/16" so what the operator types ("24 15/16")
        comes back formatted the same way on labels, reports, and read-only
        displays. Eighths precision (used previously) silently turned
        24 15/16 into "25", which mismatched the user's intent.
        """
        if not value:
            return ""
        total_sixteenths = round(value * 16)
        whole, sixteenths = divmod(total_sixteenths, 16)
        if sixteenths == 0:
            return str(int(whole))
        g = gcd(sixteenths, 16)
        num, den = sixteenths // g, 16 // g
        if whole == 0:
            return "%d/%d" % (num, den)
        return "%d %d/%d" % (whole, num, den)
