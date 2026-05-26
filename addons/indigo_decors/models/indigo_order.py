# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IndigoOrder(models.Model):
    _name = "indigo.order"
    _description = "Orden de trabajo Indigo"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"
    _rec_name = "name"

    name = fields.Char(
        string="Numero de orden",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("indigo.order") or "/",
        tracking=True,
    )

    # --- Origen / dealer ---
    dealer_id = fields.Many2one(
        "res.partner",
        string="Dealer",
        domain=[("is_indigo_dealer", "=", True)],
        required=True,
        tracking=True,
    )
    dealer_ref = fields.Char(
        string="Referencia del dealer",
        help="Codigo o nombre que el dealer asigna al cliente final.",
        tracking=True,
    )

    # --- Cliente final (no necesariamente un res.partner) ---
    client_name = fields.Char(string="Cliente final", required=True, tracking=True)
    client_phone = fields.Char(string="Telefono")
    client_email = fields.Char(string="Email")
    client_address = fields.Text(string="Direccion de instalacion")

    # --- Pipeline / asignacion ---
    stage_id = fields.Many2one(
        "indigo.stage",
        string="Etapa",
        group_expand="_read_group_stage_ids",
        tracking=True,
        index=True,
    )
    on_hold = fields.Boolean(string="En espera / Pospuesta", tracking=True)
    hold_reason = fields.Char(string="Motivo de espera")
    assigned_user_ids = fields.Many2many("res.users", string="Asignados", tracking=True)

    # --- Pago ---
    payment_state = fields.Selection(
        [
            ("unpaid", "Sin pagar"),
            ("partial", "Pago parcial"),
            ("paid", "Pagado"),
        ],
        string="Estado de pago",
        default="unpaid",
        tracking=True,
    )

    # --- Lineas y bitacora ---
    line_ids = fields.One2many("indigo.order.line", "order_id", string="Piezas")
    incident_ids = fields.One2many("indigo.order.incident", "order_id", string="Incidencias")
    notes = fields.Text(string="Notas generales")

    # --- Totales computados ---
    door_count = fields.Integer(
        string="Total de puertas",
        compute="_compute_totals",
        store=True,
    )
    total_sqf = fields.Float(
        string="Total SQF",
        compute="_compute_totals",
        store=True,
        digits=(12, 2),
    )
    total_painter_payout = fields.Float(
        string="Pago al pintor (USD)",
        compute="_compute_totals",
        store=True,
        digits=(12, 2),
        help="Total SQF x $8 USD.",
    )
    total_installer_payout = fields.Float(
        string="Pago a instaladores (USD)",
        compute="_compute_totals",
        store=True,
        digits=(12, 2),
        help="Total de puertas x $35 USD.",
    )

    # --- Constantes de negocio (fase 1; en fase 4 vendran de indigo.contractor.rate) ---
    PAINTER_RATE_PER_SQF = 8.0
    INSTALLER_RATE_PER_DOOR = 35.0

    @api.depends("line_ids.qty", "line_ids.sqf")
    def _compute_totals(self):
        for order in self:
            doors = sum(line.qty for line in order.line_ids)
            sqf = sum(line.sqf for line in order.line_ids)
            order.door_count = doors
            order.total_sqf = sqf
            order.total_painter_payout = sqf * self.PAINTER_RATE_PER_SQF
            order.total_installer_payout = doors * self.INSTALLER_RATE_PER_DOOR

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        return stages.search([], order=order)

    # --- Notificacion por cambio de etapa ---
    def write(self, vals):
        track_stage = "stage_id" in vals
        previous = {o.id: o.stage_id.id for o in self} if track_stage else {}
        res = super().write(vals)
        if track_stage:
            template = self.env.ref(
                "indigo_decors.mail_template_stage_change",
                raise_if_not_found=False,
            )
            if template:
                for order in self:
                    if order.stage_id.id != previous.get(order.id) and order.assigned_user_ids:
                        template.send_mail(order.id, force_send=False)
        return res
