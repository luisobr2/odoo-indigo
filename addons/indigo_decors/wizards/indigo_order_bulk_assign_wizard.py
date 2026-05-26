# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IndigoOrderBulkAssignWizard(models.TransientModel):
    _name = "indigo.order.bulk.assign.wizard"
    _description = "Asignar pintor / instaladores a varias ordenes"

    order_ids = fields.Many2many("indigo.order", string="Ordenes")
    painter_id = fields.Many2one("res.partner", string="Pintor")
    installer_ids = fields.Many2many("res.partner", string="Instaladores")
    new_stage_id = fields.Many2one("indigo.stage", string="Mover a etapa")
    replace_installers = fields.Boolean(
        string="Reemplazar instaladores existentes",
        default=False,
        help="Si es falso, los nuevos se agregan a los existentes.",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ids = self.env.context.get("active_ids") or []
        if ids:
            res["order_ids"] = [(6, 0, ids)]
        return res

    def action_apply(self):
        self.ensure_one()
        vals = {}
        if self.painter_id:
            vals["painter_id"] = self.painter_id.id
        if self.new_stage_id:
            vals["stage_id"] = self.new_stage_id.id
        if self.installer_ids:
            if self.replace_installers:
                vals["installer_ids"] = [(6, 0, self.installer_ids.ids)]
            else:
                vals["installer_ids"] = [(4, i) for i in self.installer_ids.ids]
        if vals:
            self.order_ids.write(vals)
        return {"type": "ir.actions.act_window_close"}
