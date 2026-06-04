# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IndigoInstallationScheduleWizard(models.TransientModel):
    """Pick an existing indigo.order and assign it an installation date.

    Used from the Installations Calendar:
      - Click on an empty day -> opens this wizard with installation_date prefilled.
      - 'Schedule Installation' button -> opens it with today as default.
    """
    _name = "indigo.installation.schedule.wizard"
    _description = "Schedule installation for an existing order"

    installation_date = fields.Date(
        string="Installation date",
        required=True,
        default=fields.Date.context_today,
    )
    order_id = fields.Many2one(
        "indigo.order",
        string="Order",
        required=True,
        # Hide already-closed orders; everything else is allowed (re-scheduling included).
        domain="[('stage_id.code', 'not in', ['closed', 'invoiced_paid'])]",
    )
    dealer_id = fields.Many2one(
        "res.partner",
        string="Dealer",
        related="order_id.dealer_id",
        readonly=True,
    )
    client_name = fields.Char(
        string="Customer",
        related="order_id.client_name",
        readonly=True,
    )
    client_address = fields.Text(
        string="Address",
        related="order_id.client_address",
        readonly=True,
    )
    door_count = fields.Integer(
        string="Doors",
        related="order_id.door_count",
        readonly=True,
    )
    installer_ids = fields.Many2many(
        "res.partner",
        string="Installers",
        help="Leave empty to keep the installers already assigned on the order.",
    )

    def action_schedule(self):
        self.ensure_one()
        vals = {"installation_date": self.installation_date}
        if self.installer_ids:
            vals["installer_ids"] = [(6, 0, self.installer_ids.ids)]
        self.order_id.write(vals)
        return {"type": "ir.actions.act_window_close"}
