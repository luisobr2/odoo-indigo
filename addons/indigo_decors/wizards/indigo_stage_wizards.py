# -*- coding: utf-8 -*-
"""Stage-focused 'do my job + advance' wizards.

Each wizard:
  - Targets ONE stage transition (e.g. Painting -> Ready for Installation).
  - Loads the relevant data from the order.
  - On save: persists the user's input, bumps the stage to the next one,
    and posts a chatter note that captures who advanced what.

The buttons that open them sit in the order form header and are
visibility-controlled by `stage_code`, so each role only sees their own.
"""
from odoo import _, api, fields, models


def _close_and_back_to_kanban(env):
    """Return an action that closes the wizard AND navigates the user
    away from the (now-out-of-scope) form view to the orders Kanban.

    Without this, returning act_window_close makes the web client refresh
    the order form behind the modal -> AccessError because the record's
    stage just left the user's record-rule scope.

    sudo() on the read because some restricted backend users (e.g. painter,
    designer scoped to a single stage) don't get read access on
    ir.actions.act_window for unrelated records — the action dict itself
    is safe to expose, only the records it loads are guarded by rules.
    """
    action = env.ref(
        "indigo_decors.action_indigo_order", raise_if_not_found=False
    )
    if not action:
        return {"type": "ir.actions.act_window_close"}
    return action.sudo().read()[0]


# ---------------------------------------------------------------------------
# Designer (Mario) -- Enter SQF, advance ready_digitalization -> cnc
# ---------------------------------------------------------------------------
class IndigoSqfEntryWizard(models.TransientModel):
    _name = "indigo.sqf.entry.wizard"
    _description = "Designer enters SQF per piece + advance to CNC"

    order_id = fields.Many2one("indigo.order", required=True, readonly=True)
    dealer_id = fields.Many2one(related="order_id.dealer_id", readonly=True)
    client_name = fields.Char(related="order_id.client_name", readonly=True)
    line_ids = fields.Many2many("indigo.order.line", string="Pieces", readonly=False)
    note = fields.Char(string="Note (optional)")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        oid = self.env.context.get("default_order_id") or self.env.context.get("active_id")
        if oid:
            order = self.env["indigo.order"].browse(oid)
            res["order_id"] = order.id
            res["line_ids"] = [(6, 0, order.line_ids.ids)]
        return res

    def action_save_and_advance(self):
        self.ensure_one()
        # sudo() on the order write+post: once we move past the user's scoped
        # stage, the record rule kicks them out and any further access on the
        # record raises AccessError. The user's identity is preserved in the
        # message_post body via env.user.
        order = self.order_id.sudo()
        next_stage = self.env.ref("indigo_decors.stage_cnc", raise_if_not_found=False)
        if next_stage and next_stage.id != order.stage_id.id:
            order.stage_id = next_stage.id
        body = _("SQF entered for %d piece(s) - sent to CNC.") % len(self.line_ids)
        if self.note:
            body += " " + self.note
        order.message_post(body=body)
        return _close_and_back_to_kanban(self.env)


# ---------------------------------------------------------------------------
# CNC operator -- Mark CNC done, advance cnc -> painting
# ---------------------------------------------------------------------------
class IndigoCncDoneWizard(models.TransientModel):
    _name = "indigo.cnc.done.wizard"
    _description = "CNC operator marks pieces as cut, advance to Painting"

    order_id = fields.Many2one("indigo.order", required=True, readonly=True)
    client_name = fields.Char(related="order_id.client_name", readonly=True)
    door_count = fields.Integer(related="order_id.door_count", readonly=True)
    total_sqf = fields.Float(related="order_id.total_sqf", readonly=True)
    note = fields.Char(string="Note (optional)", help="e.g. 'broken bit, redid piece 2'")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        oid = self.env.context.get("default_order_id") or self.env.context.get("active_id")
        if oid:
            res["order_id"] = oid
        return res

    def action_save_and_advance(self):
        self.ensure_one()
        order = self.order_id.sudo()
        next_stage = self.env.ref("indigo_decors.stage_painting", raise_if_not_found=False)
        if next_stage and next_stage.id != order.stage_id.id:
            order.stage_id = next_stage.id
        body = _("CNC cutting done - sent to Painting.")
        if self.note:
            body += " " + self.note
        order.message_post(body=body)
        return _close_and_back_to_kanban(self.env)


# ---------------------------------------------------------------------------
# Painter -- Mark painted, advance painting -> ready_install
# ---------------------------------------------------------------------------
class IndigoPainterDoneWizard(models.TransientModel):
    _name = "indigo.painter.done.wizard"
    _description = "Painter marks pieces as painted, advance to Ready for Installation"

    order_id = fields.Many2one("indigo.order", required=True, readonly=True)
    client_name = fields.Char(related="order_id.client_name", readonly=True)
    door_count = fields.Integer(related="order_id.door_count", readonly=True)
    total_sqf = fields.Float(related="order_id.total_sqf", readonly=True)
    photo = fields.Binary(
        string="Photo (optional)",
        help="A photo of the painted pieces, for record/quality check.",
    )
    note = fields.Char(string="Note (optional)")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        oid = self.env.context.get("default_order_id") or self.env.context.get("active_id")
        if oid:
            res["order_id"] = oid
        return res

    def action_save_and_advance(self):
        self.ensure_one()
        order = self.order_id.sudo()
        next_stage = self.env.ref("indigo_decors.stage_ready_install", raise_if_not_found=False)
        if next_stage and next_stage.id != order.stage_id.id:
            order.stage_id = next_stage.id
        body = _("Painting done - ready for installation.")
        if self.note:
            body += " " + self.note
        if self.photo:
            self.env["ir.attachment"].sudo().create({
                "name": "painted_%s.jpg" % order.name,
                "type": "binary",
                "datas": self.photo,
                "res_model": "indigo.order",
                "res_id": order.id,
            })
            body += _(" [photo attached]")
        order.message_post(body=body)
        return _close_and_back_to_kanban(self.env)


# ---------------------------------------------------------------------------
# Internal installer -- Mark installed, advance install_scheduled -> installed
# ---------------------------------------------------------------------------
class IndigoInstalledWizard(models.TransientModel):
    _name = "indigo.installed.wizard"
    _description = "Installer marks order as installed"

    order_id = fields.Many2one("indigo.order", required=True, readonly=True)
    client_name = fields.Char(related="order_id.client_name", readonly=True)
    client_address = fields.Text(related="order_id.client_address", readonly=True)
    door_count = fields.Integer(related="order_id.door_count", readonly=True)
    photo = fields.Binary(
        string="Install photo",
        help="Photo of the installed door(s) - used for payout proof.",
    )
    note = fields.Char(string="Note (optional)")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        oid = self.env.context.get("default_order_id") or self.env.context.get("active_id")
        if oid:
            res["order_id"] = oid
        return res

    def action_save_and_advance(self):
        self.ensure_one()
        order = self.order_id.sudo()
        next_stage = self.env.ref("indigo_decors.stage_installed", raise_if_not_found=False)
        if next_stage and next_stage.id != order.stage_id.id:
            order.stage_id = next_stage.id
        body = _("Order installed.")
        if self.note:
            body += " " + self.note
        Attach = self.env["ir.attachment"].sudo()
        if self.photo:
            Attach.create({
                "name": "installed_%s.jpg" % order.name,
                "type": "binary",
                "datas": self.photo,
                "res_model": "indigo.order",
                "res_id": order.id,
            })
            body += _(" [install photo attached]")
        order.message_post(body=body)
        return _close_and_back_to_kanban(self.env)


# ---------------------------------------------------------------------------
# Office / Admin -- Mark invoiced & paid, advance installed -> invoiced
# ---------------------------------------------------------------------------
class IndigoInvoicedPaidWizard(models.TransientModel):
    _name = "indigo.invoiced.paid.wizard"
    _description = "Office marks order as invoiced and paid"

    order_id = fields.Many2one("indigo.order", required=True, readonly=True)
    dealer_id = fields.Many2one(related="order_id.dealer_id", readonly=True)
    total_dealer_charge = fields.Float(
        related="order_id.total_dealer_charge", readonly=True,
    )
    amount_collected = fields.Float(
        string="Amount collected (USD)",
        digits=(12, 2),
        required=True,
    )
    payment_state = fields.Selection(
        [("paid", "Paid in full"), ("partial", "Partial payment")],
        string="Payment status",
        required=True,
        default="paid",
    )
    payment_ref = fields.Char(string="Reference (check #, transfer ID, etc.)")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        oid = self.env.context.get("default_order_id") or self.env.context.get("active_id")
        if oid:
            order = self.env["indigo.order"].browse(oid)
            res["order_id"] = order.id
            res["amount_collected"] = order.total_dealer_charge or 0.0
        return res

    def action_save_and_advance(self):
        self.ensure_one()
        order = self.order_id.sudo()
        next_stage = self.env.ref("indigo_decors.stage_invoiced", raise_if_not_found=False)
        vals = {"payment_state": self.payment_state}
        if next_stage:
            vals["stage_id"] = next_stage.id
        order.write(vals)
        body = _("Invoiced - %s collected.") % ("$%.2f" % (self.amount_collected or 0))
        if self.payment_ref:
            body += _(" Ref: %s") % self.payment_ref
        order.message_post(body=body)
        return _close_and_back_to_kanban(self.env)
