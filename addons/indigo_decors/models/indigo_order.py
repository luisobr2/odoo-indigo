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
    price_per_sqf = fields.Float(
        string="Precio por SQF al dealer (USD)",
        digits=(10, 2),
        help="Precio que se cobra al dealer por SQF. Por defecto toma el del dealer.",
        tracking=True,
    )
    total_dealer_charge = fields.Float(
        string="Total a cobrar al dealer (USD)",
        compute="_compute_totals",
        store=True,
        digits=(12, 2),
    )

    # --- Referencia interna ("PRIV" — campo libre que sale en la etiqueta) ---
    priv_ref = fields.Char(
        string="Ref. interna (PRIV)",
        help="Referencia privada/interna que sale en la etiqueta del disenador.",
        tracking=True,
    )

    # --- Fotos del contrato / puerta ---
    photo_ids = fields.Many2many(
        "ir.attachment",
        "indigo_order_photo_rel",
        "order_id",
        "attachment_id",
        string="Fotos del contrato / puerta",
        help="Fotos firmadas del contrato y/o de la puerta del cliente final.",
    )

    # --- Contratistas asignados ---
    painter_id = fields.Many2one(
        "res.partner",
        string="Pintor asignado",
        tracking=True,
        help="Contratista que pinta esta orden. Se usa para generar la liquidacion al salir de la etapa Painting.",
    )
    installer_ids = fields.Many2many(
        "res.partner",
        "indigo_order_installer_rel",
        "order_id",
        "partner_id",
        string="Instaladores",
        tracking=True,
        help="Instaladores que reciben pago por puerta al completar la instalacion.",
    )

    # --- Lineas y bitacora ---
    line_ids = fields.One2many("indigo.order.line", "order_id", string="Piezas")
    incident_ids = fields.One2many("indigo.order.incident", "order_id", string="Incidencias")
    payout_line_ids = fields.One2many(
        "indigo.payout.line", "order_id", string="Liquidaciones generadas"
    )
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

    @api.depends("line_ids.qty", "line_ids.sqf", "price_per_sqf")
    def _compute_totals(self):
        for order in self:
            doors = sum(line.qty for line in order.line_ids)
            sqf = sum(line.sqf for line in order.line_ids)
            order.door_count = doors
            order.total_sqf = sqf
            order.total_painter_payout = sqf * self.PAINTER_RATE_PER_SQF
            order.total_installer_payout = doors * self.INSTALLER_RATE_PER_DOOR
            order.total_dealer_charge = sqf * (order.price_per_sqf or 0.0)

    @api.onchange("dealer_id")
    def _onchange_dealer_id_set_price(self):
        for o in self:
            if o.dealer_id and o.dealer_id.indigo_default_price_per_sqf and not o.price_per_sqf:
                o.price_per_sqf = o.dealer_id.indigo_default_price_per_sqf

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        return stages.search([], order=order)

    # --- Triggers por cambio de etapa: notificacion + liquidaciones ---
    def write(self, vals):
        track_stage = "stage_id" in vals
        previous = {o.id: o.stage_id.id for o in self} if track_stage else {}
        res = super().write(vals)
        if track_stage:
            template = self.env.ref(
                "indigo_decors.mail_template_stage_change",
                raise_if_not_found=False,
            )
            stage_painting = self.env.ref("indigo_decors.stage_painting", raise_if_not_found=False)
            stage_installed = self.env.ref("indigo_decors.stage_installed", raise_if_not_found=False)
            for order in self:
                prev_id = previous.get(order.id)
                if order.stage_id.id == prev_id:
                    continue
                # 1) correo
                if template and order.assigned_user_ids:
                    template.send_mail(order.id, force_send=False)
                # 2) payout pintor: al SALIR de Painting
                if stage_painting and prev_id == stage_painting.id and order.painter_id:
                    order._create_painter_payout()
                # 3) payout instalador: al ENTRAR a Installed
                if stage_installed and order.stage_id.id == stage_installed.id and order.installer_ids:
                    order._create_installer_payouts()
        return res

    def _create_painter_payout(self):
        """Crea un draft payout para el pintor con una linea por pieza."""
        self.ensure_one()
        if not self.painter_id or not self.line_ids:
            return
        # No duplicar si ya existe payout para esta orden y pintor
        existing = self.env["indigo.payout.line"].search([
            ("order_id", "=", self.id),
            ("payout_id.contractor_id", "=", self.painter_id.id),
            ("payout_id.contractor_type", "=", "painter"),
            ("payout_id.state", "!=", "cancel"),
        ], limit=1)
        if existing:
            return
        payout = self.env["indigo.payout"].create({
            "contractor_id": self.painter_id.id,
            "contractor_type": "painter",
            "notes": "Generada automaticamente al completar pintura de orden %s." % self.name,
        })
        for line in self.line_ids:
            self.env["indigo.payout.line"].create({
                "payout_id": payout.id,
                "order_id": self.id,
                "order_line_id": line.id,
                "description": "Pintura %s - %s %s" % (
                    line.design_id.code or "",
                    line.door_type or "",
                    line.color or "",
                ),
                "quantity": line.sqf or 0.0,
                "rate": self.PAINTER_RATE_PER_SQF,
            })

    def _create_installer_payouts(self):
        """Crea un draft payout por cada instalador con su parte proporcional."""
        self.ensure_one()
        if not self.installer_ids or not self.door_count:
            return
        share = self.door_count / max(len(self.installer_ids), 1)
        for installer in self.installer_ids:
            existing = self.env["indigo.payout.line"].search([
                ("order_id", "=", self.id),
                ("payout_id.contractor_id", "=", installer.id),
                ("payout_id.contractor_type", "=", "installer"),
                ("payout_id.state", "!=", "cancel"),
            ], limit=1)
            if existing:
                continue
            payout = self.env["indigo.payout"].create({
                "contractor_id": installer.id,
                "contractor_type": "installer",
                "notes": "Generada automaticamente al completar instalacion de orden %s." % self.name,
            })
            self.env["indigo.payout.line"].create({
                "payout_id": payout.id,
                "order_id": self.id,
                "description": "Instalacion orden %s (%s puertas / %s instaladores)" % (
                    self.name, self.door_count, len(self.installer_ids)
                ),
                "quantity": share,
                "rate": self.INSTALLER_RATE_PER_DOOR,
            })
