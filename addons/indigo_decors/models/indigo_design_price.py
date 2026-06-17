# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IndigoDesignPrice(models.Model):
    """Base price charged to the dealer per door, by design model.

    Time D'signs prices each door by its model (door type x design tier),
    not by SQF. Admins edit the matrix here (Indigo -> Config -> Design
    Prices). An order line's unit_price is the price of the row matching its
    (door_type, design_tier); 'custom' tier uses the line's manual price.
    """

    _name = "indigo.design.price"
    _description = "Design model base price (dealer charge)"
    _order = "door_type, tier"

    door_type = fields.Selection(
        [
            ("SD", "Single Door"),
            ("DD", "Double Door"),
            ("sidelite", "Door with Sidelites"),
        ],
        string="Door type",
        required=True,
    )
    tier = fields.Selection(
        [
            ("basic", "Basic"),
            ("full_partial", "Full / Partial"),
            ("custom", "Custom"),
        ],
        string="Design tier",
        required=True,
    )
    price = fields.Float(string="Base price (USD)", digits=(10, 2))
    name = fields.Char(string="Model", compute="_compute_name", store=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "door_tier_uniq",
            "unique(door_type, tier)",
            "There is already a price for this door type + tier.",
        ),
    ]

    @api.depends("door_type", "tier")
    def _compute_name(self):
        dt = dict(self._fields["door_type"].selection)
        tr = dict(self._fields["tier"].selection)
        for r in self:
            r.name = f"{dt.get(r.door_type, r.door_type)} — {tr.get(r.tier, r.tier)}"

    @api.model
    def price_for(self, door_type, tier):
        """Base price for a (door_type, tier) combo, 0.0 if none configured."""
        if not door_type or not tier:
            return 0.0
        rec = self.search(
            [("door_type", "=", door_type), ("tier", "=", tier)], limit=1
        )
        return rec.price if rec else 0.0

    # ------------------------------------------------------------------
    # Keep order totals in sync when the matrix changes. order.line.unit_price
    # reads price_for() but doesn't @api.depend on this model, so editing a
    # tier price would otherwise leave existing orders' totals stale.
    # We refresh only NON-custom lines on OPEN orders (not invoiced/closed)
    # so already-billed history isn't rewritten retroactively.
    # ------------------------------------------------------------------
    def _recompute_open_order_lines(self):
        lines = self.env["indigo.order.line"].search([
            ("design_tier", "!=", "custom"),
            ("order_id.stage_id.code", "not in", ["invoiced", "closed"]),
        ])
        if lines:
            lines._compute_unit_price()
            lines.order_id._compute_totals()

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        recs._recompute_open_order_lines()
        return recs

    def write(self, vals):
        res = super().write(vals)
        if {"price", "door_type", "tier", "active"} & set(vals):
            self._recompute_open_order_lines()
        return res

    def unlink(self):
        res = super().unlink()
        self._recompute_open_order_lines()
        return res
