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
        default=lambda self: self._default_stage_id(),
    )

    @api.model
    def _default_stage_id(self):
        """Lowest-sequence stage (i.e. 'New Order') as default for new orders."""
        return self.env["indigo.stage"].search([], order="sequence asc", limit=1)
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

    # --- SLA / aging ---
    expected_completion_date = fields.Date(
        string="Fecha de entrega prometida",
        tracking=True,
    )
    installation_date = fields.Date(
        string="Fecha de instalacion programada",
        tracking=True,
    )
    last_stage_change = fields.Datetime(
        string="Ultimo cambio de etapa",
        default=fields.Datetime.now,
    )
    days_in_current_stage = fields.Integer(
        string="Dias en etapa actual",
        compute="_compute_days_in_current_stage",
    )
    is_overdue = fields.Boolean(
        string="Atrasada",
        compute="_compute_days_in_current_stage",
        search="_search_is_overdue",
    )
    # Token publico para tracking del cliente final
    access_token = fields.Char(
        string="Token publico",
        copy=False,
        readonly=True,
        index=True,
    )
    # Recibos de pago subidos por el dealer
    payment_receipt_ids = fields.Many2many(
        "ir.attachment",
        "indigo_order_receipt_rel",
        "order_id",
        "attachment_id",
        string="Recibos de pago",
    )

    # --- Firma del cliente final al recibir la instalacion ---
    client_signature = fields.Binary(
        string="Firma del cliente",
        attachment=True,
        help="Firma capturada por el instalador al completar la instalacion (legal proof).",
    )
    client_signature_date = fields.Datetime(string="Fecha firma cliente")
    client_signature_name = fields.Char(
        string="Nombre del firmante",
        help="Nombre de la persona que firma en sitio (puede no coincidir con client_name).",
    )

    @api.depends("last_stage_change", "stage_id.sla_days", "stage_id")
    def _compute_days_in_current_stage(self):
        from datetime import datetime
        now = datetime.now()
        for order in self:
            if order.last_stage_change:
                delta = now - order.last_stage_change
                order.days_in_current_stage = delta.days
            else:
                order.days_in_current_stage = 0
            sla = order.stage_id.sla_days or 0
            order.is_overdue = bool(sla and order.days_in_current_stage > sla)

    def _search_is_overdue(self, operator, value):
        # Aproximacion: usa SQL para buscar atrasadas
        if operator == "=" and value:
            self.env.cr.execute("""
                SELECT o.id FROM indigo_order o
                JOIN indigo_stage s ON s.id = o.stage_id
                WHERE s.sla_days > 0
                  AND EXTRACT(EPOCH FROM (NOW() - o.last_stage_change)) / 86400 > s.sla_days
            """)
            return [("id", "in", [r[0] for r in self.env.cr.fetchall()])]
        return [("id", "=", False)] if value else [("id", "!=", False)]

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
    line_ids = fields.One2many(
        "indigo.order.line", "order_id", string="Piezas",
        copy=True,
    )
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

    # --- Tarifas (fallback si no hay registro en indigo.contractor.rate) ---
    DEFAULT_PAINTER_RATE_PER_SQF = 8.0
    DEFAULT_INSTALLER_RATE_PER_DOOR = 35.0

    def _get_painter_rate(self):
        rate = self.env["indigo.contractor.rate"].search([
            ("contractor_type", "=", "painter"),
            ("active", "=", True),
        ], limit=1)
        return rate.rate if rate else self.DEFAULT_PAINTER_RATE_PER_SQF

    def _get_installer_rate(self):
        rate = self.env["indigo.contractor.rate"].search([
            ("contractor_type", "=", "installer"),
            ("active", "=", True),
        ], limit=1)
        return rate.rate if rate else self.DEFAULT_INSTALLER_RATE_PER_DOOR

    # Backwards-compat alias (algunos lugares lo leen por nombre)
    PAINTER_RATE_PER_SQF = DEFAULT_PAINTER_RATE_PER_SQF
    INSTALLER_RATE_PER_DOOR = DEFAULT_INSTALLER_RATE_PER_DOOR

    @api.depends("line_ids.qty", "line_ids.sqf", "price_per_sqf")
    def _compute_totals(self):
        painter_rate = self._get_painter_rate()
        installer_rate = self._get_installer_rate()
        for order in self:
            doors = sum(line.qty for line in order.line_ids)
            sqf = sum(line.sqf for line in order.line_ids)
            order.door_count = doors
            order.total_sqf = sqf
            order.total_painter_payout = sqf * painter_rate
            order.total_installer_payout = doors * installer_rate
            order.total_dealer_charge = sqf * (order.price_per_sqf or 0.0)

    @api.onchange("dealer_id")
    def _onchange_dealer_id_set_price(self):
        for o in self:
            if o.dealer_id and o.dealer_id.indigo_default_price_per_sqf and not o.price_per_sqf:
                o.price_per_sqf = o.dealer_id.indigo_default_price_per_sqf


    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        """Si el usuario filtro por un dealer especifico, ocultar las
        etapas opcionales que ese dealer no usa."""
        dealer_id = None
        for cond in domain or []:
            if isinstance(cond, (list, tuple)) and len(cond) == 3 \
                    and cond[0] == "dealer_id" and cond[1] == "=":
                dealer_id = cond[2]
                break
        if dealer_id:
            dealer = self.env["res.partner"].browse(dealer_id)
            optional_ids = dealer.indigo_optional_stage_ids.ids
            return stages.search([
                "|",
                ("is_optional", "=", False),
                ("id", "in", optional_ids),
            ], order=order)
        return stages.search([], order=order)

    # --- Triggers por cambio de etapa: notificacion + liquidaciones + SLA ---
    def write(self, vals):
        track_stage = "stage_id" in vals
        previous = {o.id: o.stage_id.id for o in self} if track_stage else {}
        if track_stage:
            vals["last_stage_change"] = fields.Datetime.now()
        res = super().write(vals)
        if track_stage:
            generic = self.env.ref(
                "indigo_decors.mail_template_stage_change",
                raise_if_not_found=False,
            )
            stage_painting = self.env.ref("indigo_decors.stage_painting", raise_if_not_found=False)
            stage_installed = self.env.ref("indigo_decors.stage_installed", raise_if_not_found=False)
            for order in self:
                prev_id = previous.get(order.id)
                if order.stage_id.id == prev_id:
                    continue
                # 1) correo: usa template especifico de la etapa si existe, si no la generica
                template = order.stage_id.notify_template_id or generic
                if template and order.assigned_user_ids:
                    template.send_mail(order.id, force_send=False)
                # 2) payout pintor
                if stage_painting and prev_id == stage_painting.id and order.painter_id:
                    order._create_painter_payout()
                # 3) payout instalador
                if stage_installed and order.stage_id.id == stage_installed.id and order.installer_ids:
                    order._create_installer_payouts()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        Partner = self.env["res.partner"]
        import uuid
        for vals in vals_list:
            if not vals.get("price_per_sqf") and vals.get("dealer_id"):
                dealer = Partner.browse(vals["dealer_id"])
                if dealer.indigo_default_price_per_sqf:
                    vals["price_per_sqf"] = dealer.indigo_default_price_per_sqf
            if not vals.get("access_token"):
                vals["access_token"] = uuid.uuid4().hex
            if not vals.get("last_stage_change"):
                vals["last_stage_change"] = fields.Datetime.now()
        return super().create(vals_list)

    def get_tracking_url(self):
        self.ensure_one()
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        return "%s/track/%s" % (base, self.access_token or "")

    @api.model
    def _cron_check_sla_overdue(self):
        """Diario: para cada orden atrasada, crear actividad de seguimiento
        en los asignados (una sola activity 'todo' por orden, evita spam)."""
        Activity = self.env["mail.activity"]
        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        if not activity_type:
            return 0
        overdue = self.search([("is_overdue", "=", True), ("stage_id.code", "!=", "closed")])
        count = 0
        for order in overdue:
            users = order.assigned_user_ids or self.env.user
            for user in users:
                existing = Activity.search([
                    ("res_model", "=", "indigo.order"),
                    ("res_id", "=", order.id),
                    ("user_id", "=", user.id),
                    ("activity_type_id", "=", activity_type.id),
                    ("note", "ilike", "SLA"),
                ], limit=1)
                if existing:
                    continue
                Activity.create({
                    "res_model": "indigo.order",
                    "res_model_id": self.env.ref("indigo_decors.model_indigo_order").id,
                    "res_id": order.id,
                    "user_id": user.id,
                    "activity_type_id": activity_type.id,
                    "summary": "Orden %s atrasada en %s" % (order.name, order.stage_id.name),
                    "note": "SLA superado: lleva %s dias en esta etapa (max %s)." % (
                        order.days_in_current_stage, order.stage_id.sla_days or "?"
                    ),
                })
                count += 1
        return count

    def _create_painter_payout(self):
        """Crea un draft payout para el pintor con una linea por pieza."""
        self.ensure_one()
        if not self.painter_id or not self.line_ids:
            return
        existing = self.env["indigo.payout.line"].search([
            ("order_id", "=", self.id),
            ("payout_id.contractor_id", "=", self.painter_id.id),
            ("payout_id.contractor_type", "=", "painter"),
            ("payout_id.state", "!=", "cancel"),
        ], limit=1)
        if existing:
            return
        rate = self._get_painter_rate()
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
                "rate": rate,
            })

    def _create_installer_payouts(self):
        """Crea un draft payout por cada instalador con su parte proporcional."""
        self.ensure_one()
        if not self.installer_ids or not self.door_count:
            return
        share = self.door_count / max(len(self.installer_ids), 1)
        rate = self._get_installer_rate()
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
                "rate": rate,
            })
