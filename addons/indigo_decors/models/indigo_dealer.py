# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_indigo_dealer = fields.Boolean(string="Es dealer Indigo")
    indigo_dealer_code = fields.Char(string="Codigo de dealer")
    indigo_default_price_per_sqf = fields.Float(
        string="Precio por defecto por SQF",
        help="Precio que se cobra al dealer por SQF (puede sobrescribirse por orden).",
    )
    indigo_optional_stage_ids = fields.Many2many(
        "indigo.stage",
        "indigo_dealer_stage_rel",
        "partner_id",
        "stage_id",
        string="Etapas opcionales activas",
        domain=[("is_optional", "=", True)],
        help="Etapas opcionales (2-5: confirmacion/medicion) que aplican para este dealer.",
    )
