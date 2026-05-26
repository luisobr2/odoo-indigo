# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import api, fields, models
from odoo.exceptions import UserError


class IndigoPayoutSettleWizard(models.TransientModel):
    _name = "indigo.payout.settle.wizard"
    _description = "Consolidar liquidaciones por contratista en un periodo"

    contractor_id = fields.Many2one("res.partner", string="Contratista", required=True)
    contractor_type = fields.Selection(
        [("painter", "Pintor"), ("installer", "Instalador"), ("other", "Otro")],
        string="Tipo",
        required=True,
        default="installer",
    )
    period_start = fields.Date(string="Desde", required=True, default=lambda s: fields.Date.context_today(s) - timedelta(days=7))
    period_end = fields.Date(string="Hasta", required=True, default=fields.Date.context_today)

    def action_consolidate(self):
        self.ensure_one()
        Payout = self.env["indigo.payout"]
        # Buscar payouts en borrador del contratista en el rango
        domain = [
            ("contractor_id", "=", self.contractor_id.id),
            ("contractor_type", "=", self.contractor_type),
            ("state", "=", "draft"),
            ("date", ">=", self.period_start),
            ("date", "<=", self.period_end),
        ]
        drafts = Payout.search(domain)
        if not drafts:
            raise UserError(
                "No hay liquidaciones en borrador para %s entre %s y %s." % (
                    self.contractor_id.name, self.period_start, self.period_end
                )
            )
        if len(drafts) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "indigo.payout",
                "res_id": drafts.id,
                "view_mode": "form",
                "target": "current",
            }
        # Consolidar: crear un payout nuevo con todas las lineas + cancelar los originales
        consolidated = Payout.create({
            "contractor_id": self.contractor_id.id,
            "contractor_type": self.contractor_type,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "notes": "Consolidacion automatica de %s liquidaciones (%s a %s)." % (
                len(drafts), self.period_start, self.period_end
            ),
        })
        # Mover lineas al consolidated
        drafts.mapped("line_ids").write({"payout_id": consolidated.id})
        # Cancelar y dejar nota en originales
        for d in drafts:
            d.message_post(body="Lineas movidas a liquidacion consolidada %s." % consolidated.name)
            d.state = "cancel"
        return {
            "type": "ir.actions.act_window",
            "res_model": "indigo.payout",
            "res_id": consolidated.id,
            "view_mode": "form",
            "target": "current",
        }
