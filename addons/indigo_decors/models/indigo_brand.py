# -*- coding: utf-8 -*-
"""Brand catalog — window/door manufacturers that interfere with paint type.

Majela explicitly called out (chat 2026-06-07) that the brand the customer
specifies "interferes with the paint type that is used" — so it's not a
cosmetic field: it gates downstream production decisions. Modeling it as
its own table lets us extend later (default paint per brand, technical
notes, etc.) without breaking history.
"""
from odoo import fields, models


class IndigoBrand(models.Model):
    _name = "indigo.brand"
    _description = "Window / door brand"
    _order = "name asc"

    name = fields.Char(string="Brand", required=True, translate=False)
    code = fields.Char(string="Short code")
    active = fields.Boolean(default=True)
    notes = fields.Text(
        string="Notes",
        help="Free-form notes about this brand — e.g. compatible paints, "
             "known limitations, contact info for technical questions.",
    )

    _sql_constraints = [
        ("indigo_brand_name_uniq", "UNIQUE(name)", "Brand name must be unique."),
    ]
