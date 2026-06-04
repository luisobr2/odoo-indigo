# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class IndigoMeasurementEntryWizard(models.TransientModel):
    """Stage-focused wizard for Javier: enter measurements + advance stage.

    Triggered by the 'Enter measurements' button on the order form that is
    only visible when stage.code == 'measure_pending'. The wizard:
      - Lets him fill width/height per piece (the only fields that matter
        at this point in the workflow).
      - On 'Save & advance': writes the measurements (already persisted
        inline by the tree widget), bumps the stage to 'Measured', and
        posts a chatter note.
    """
    _name = "indigo.measurement.entry.wizard"
    _description = "Enter measurements for an order's pieces"

    order_id = fields.Many2one(
        "indigo.order",
        string="Order",
        required=True,
        readonly=True,
    )
    dealer_id = fields.Many2one(
        related="order_id.dealer_id", readonly=True,
    )
    client_name = fields.Char(
        related="order_id.client_name", readonly=True,
    )
    client_address = fields.Text(
        related="order_id.client_address", readonly=True,
    )
    line_ids = fields.Many2many(
        "indigo.order.line",
        string="Pieces",
        readonly=False,
    )
    note = fields.Char(
        string="Note (optional)",
        help="Goes into the order chatter together with the stage change.",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        order_id = self.env.context.get("default_order_id") or self.env.context.get("active_id")
        if order_id:
            order = self.env["indigo.order"].browse(order_id)
            res["order_id"] = order.id
            res["line_ids"] = [(6, 0, order.line_ids.ids)]
        return res

    def action_save_and_advance(self):
        self.ensure_one()
        # sudo(): once the stage advances the user may no longer be in scope
        # for that record (record rules filter by stage_id.code), so any
        # subsequent message_post would AccessError. The user identity is
        # still recorded via env.user in the post.
        order = self.order_id.sudo()
        next_stage = self.env.ref(
            "indigo_decors.stage_measured", raise_if_not_found=False
        )
        if next_stage and next_stage.id != order.stage_id.id:
            order.stage_id = next_stage.id

        body = _("Measurements entered for %d piece(s).") % len(self.line_ids)
        if self.note:
            body += " " + self.note
        order.message_post(body=body)
        # Navigate to the Kanban list instead of closing back to the form,
        # because the form may have just left the user's scope (record rule
        # filters by stage_id.code) and refreshing it would AccessError.
        action = self.env.ref(
            "indigo_decors.action_indigo_order", raise_if_not_found=False
        )
        if action:
            # sudo: scoped users can't read ir.actions.act_window directly
            return action.sudo().read()[0]
        return {"type": "ir.actions.act_window_close"}
