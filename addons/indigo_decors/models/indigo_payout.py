# -*- coding: utf-8 -*-
from odoo import fields, models


class IndigoPayout(models.Model):
    _name = "indigo.payout"
    _description = "Liquidacion a contratista (placeholder Fase 4)"
    _order = "period_end desc, id desc"

    name = fields.Char(string="Referencia", required=True, copy=False, default="Nuevo")
    contractor_id = fields.Many2one("res.partner", string="Contratista", required=True)
    contractor_type = fields.Selection(
        [
            ("painter", "Pintor"),
            ("installer", "Instalador"),
            ("other", "Otro"),
        ],
        string="Tipo",
        required=True,
    )
    period_start = fields.Date(string="Desde")
    period_end = fields.Date(string="Hasta")
    amount = fields.Float(string="Monto (USD)", digits=(12, 2))
    state = fields.Selection(
        [("draft", "Borrador"), ("paid", "Pagado")],
        string="Estado",
        default="draft",
        required=True,
    )
    notes = fields.Text(string="Notas")
