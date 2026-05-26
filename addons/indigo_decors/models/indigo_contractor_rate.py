# -*- coding: utf-8 -*-
from odoo import fields, models


class IndigoContractorRate(models.Model):
    _name = "indigo.contractor.rate"
    _description = "Tarifa de contratista (placeholder Fase 4)"
    _order = "contractor_type, id"

    name = fields.Char(string="Nombre", required=True)
    contractor_type = fields.Selection(
        [
            ("painter", "Pintor"),
            ("installer", "Instalador"),
            ("other", "Otro"),
        ],
        string="Tipo",
        required=True,
    )
    rate = fields.Float(string="Tarifa (USD)", required=True, digits=(10, 2))
    rate_unit = fields.Selection(
        [
            ("sqf", "Por SQF"),
            ("piece", "Por pieza"),
        ],
        string="Unidad",
        required=True,
        default="sqf",
    )
    active = fields.Boolean(default=True)
