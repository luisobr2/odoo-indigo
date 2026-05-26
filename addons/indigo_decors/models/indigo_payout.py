# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IndigoPayout(models.Model):
    _name = "indigo.payout"
    _description = "Liquidacion a contratista (pintor / instalador)"
    _order = "date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="Referencia",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("indigo.payout") or "/",
        tracking=True,
    )
    contractor_id = fields.Many2one(
        "res.partner",
        string="Contratista",
        required=True,
        tracking=True,
        index=True,
    )
    contractor_type = fields.Selection(
        [
            ("painter", "Pintor"),
            ("installer", "Instalador"),
            ("other", "Otro"),
        ],
        string="Tipo",
        required=True,
        tracking=True,
    )
    date = fields.Date(
        string="Fecha emision",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    period_start = fields.Date(string="Periodo desde")
    period_end = fields.Date(string="Periodo hasta")

    line_ids = fields.One2many("indigo.payout.line", "payout_id", string="Lineas")

    amount = fields.Float(
        string="Monto total (USD)",
        compute="_compute_amount",
        store=True,
        digits=(12, 2),
        tracking=True,
    )

    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("approved", "Aprobada"),
            ("paid", "Pagada"),
            ("cancel", "Cancelada"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
    )
    notes = fields.Text(string="Notas")

    @api.depends("line_ids.amount")
    def _compute_amount(self):
        for p in self:
            p.amount = sum(p.line_ids.mapped("amount"))

    def action_approve(self):
        self.write({"state": "approved"})

    def action_mark_paid(self):
        self.write({"state": "paid"})

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})


class IndigoPayoutLine(models.Model):
    _name = "indigo.payout.line"
    _description = "Linea de liquidacion"
    _order = "date_work desc, id desc"

    payout_id = fields.Many2one(
        "indigo.payout", required=True, ondelete="cascade", index=True
    )
    order_id = fields.Many2one("indigo.order", string="Orden", index=True)
    order_line_id = fields.Many2one("indigo.order.line", string="Pieza")
    date_work = fields.Date(string="Fecha del trabajo", default=fields.Date.context_today)
    description = fields.Char(string="Descripcion", required=True)

    quantity = fields.Float(
        string="Cantidad",
        digits=(10, 2),
        help="SQF para pintor, puertas para instalador.",
    )
    rate = fields.Float(string="Tarifa (USD)", digits=(10, 2))
    amount = fields.Float(
        string="Monto (USD)",
        compute="_compute_amount",
        store=True,
        digits=(12, 2),
    )

    @api.depends("quantity", "rate")
    def _compute_amount(self):
        for line in self:
            line.amount = (line.quantity or 0.0) * (line.rate or 0.0)
