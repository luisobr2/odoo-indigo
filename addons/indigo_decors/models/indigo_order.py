# -*- coding: utf-8 -*-
import base64
import logging
import re

from odoo import _, api, fields, models

from .indigo_zip_geo import (
    bearing_degrees,
    compass_from_bearing,
    haversine_miles,
)
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)


def _zip_from_address(address):
    """Best-effort 5-digit ZIP from a free-text US address (last match wins —
    the ZIP is usually at the end, after the state)."""
    matches = re.findall(r"\b(\d{5})(?:-\d{4})?\b", address or "")
    return matches[-1] if matches else False


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

    # Archiving: archived orders drop out of the default lists/kanban/reports
    # (Odoo's active_test) but keep all their data and can be restored.
    active = fields.Boolean(default=True, tracking=True)

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
    client_zip = fields.Char(
        string="ZIP",
        help="ZIP code of the installation address. Auto-filled from the "
             "address; drives the distance-based installation fee. Editable.",
        tracking=True,
    )

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

    # Exposed for use in view attributes (e.g. invisible="stage_code != 'measure_pending'")
    # — referencing stage_id.code directly in form attribute filters does not work.
    stage_code = fields.Char(
        related="stage_id.code",
        store=False,
        string="Stage code",
    )
    on_hold = fields.Boolean(string="En espera / Pospuesta", tracking=True)
    # Majela's 2026-08-15 request (item 3): "on_hold" + a free-text reason
    # told her THAT a door was blocked but not WHO has to unblock it, so she
    # could never count "7 doors waiting on the dealer" -- free text can't be
    # counted or colored. hold_cause is the countable/colorable answer;
    # hold_reason stays as the human detail of WHAT the problem is.
    hold_cause = fields.Selection(
        [
            ("dealer", "Problema del dealer"),
            ("client", "Problema del cliente"),
            ("other", "Otro / sin clasificar"),
        ],
        string="Causa de la espera",
        tracking=True,
        help="Quien tiene que resolver el bloqueo antes de que la orden "
             "pueda seguir: el dealer o el cliente final. Alimenta los "
             "contadores y colores de 'En espera' en Instalaciones -- por "
             "eso es obligatoria en cuanto se activa 'En espera / "
             "Pospuesta'.",
    )
    hold_reason = fields.Char(string="Motivo de espera")

    @api.constrains("on_hold", "hold_cause")
    def _check_hold_requires_cause(self):
        """A hold with no cause is exactly the unclassifiable row Majela
        can't count or color -- refuse it at the source (write/create),
        which covers every caller (backend UI, portal, panel RPC, MCP) since
        they all funnel through this model's write()/create()."""
        for order in self:
            if order.on_hold and not order.hold_cause:
                raise ValidationError(
                    _("Para poner la orden %s en espera hace falta indicar "
                      "la causa: ¿problema del dealer, del cliente, u otro? "
                      "Sin eso no se puede contar ni distinguir en "
                      "Instalaciones.") % (order.name or "")
                )
    assigned_user_ids = fields.Many2many("res.users", string="Asignados", tracking=True)

    # --- Sub-status timestamps ---
    # Within a single stage (CNC, Digitalization, Painting) an order can be:
    #   Ready  -> not started yet (no `_started_at`)
    #   In Progress -> `_started_at` set, `_done_at` empty
    #   Completed -> both set
    # The UI shows tabs based on these timestamps inside each stage screen.
    digi_started_at = fields.Datetime(string="Digitalization started")
    digi_done_at = fields.Datetime(string="Digitalization done")
    cnc_started_at = fields.Datetime(string="CNC started")
    cnc_done_at = fields.Datetime(string="CNC done")
    paint_started_at = fields.Datetime(string="Painting started")
    paint_done_at = fields.Datetime(string="Painting done")

    # --- Cancellation (Design Approval flow) ---
    # Set when a dealer cancels at the design-approval stage. We keep the
    # record so we can show it in /design-approval -> "Cancelled" tab and
    # so the dashboard can report cancellation rate by dealer.
    cancelled_at = fields.Datetime(string="Cancelled at", tracking=True)
    cancellation_reason = fields.Text(
        string="Cancellation reason",
        help="Why the dealer or office cancelled the order at design "
             "approval (or any other stage).",
    )

    # --- Available Stock (re-use pool) ---
    # When an order is cancelled AFTER the door has been cut / painted, the
    # finished door can be moved to a stock pool instead of being trashed.
    # When a new order matches its characteristics (design + dimensions +
    # color + glass), the stock door is consumed and the new order skips
    # CNC / Paint straight to Ready for Installation.
    is_stock = fields.Boolean(
        string="Available stock",
        default=False,
        tracking=True,
        help="When true, the finished door from this order sits in the "
             "reusable stock pool until consumed by a new matching order.",
    )
    stock_at = fields.Datetime(string="Moved to stock at", tracking=True)
    stock_label = fields.Char(
        string="Stock nickname",
        help="Free-text name the warehouse uses to find this door, e.g. "
             "'Bronze SD #3', 'Karen O\\u2019Reilly leftover'.",
    )
    stock_reason = fields.Text(string="Stock reason")
    original_client_name = fields.Char(
        string="Original client",
        help="The client this door was originally produced for. Kept for "
             "traceability after the door is reassigned.",
    )
    reused_in_order_id = fields.Many2one(
        "indigo.order",
        string="Reassigned to",
        help="When this stock entry has been consumed by a new order, "
             "points to that order so we can audit the chain.",
    )

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
    date_paid = fields.Date(
        string="Date paid",
        help="When the order was marked as paid. Used by the dashboard "
             "to compute monthly revenue accurately (not write_date, which "
             "shifts whenever ANY field is edited).",
        tracking=True,
    )
    invoiced_at = fields.Datetime(
        string="Invoiced at",
        help="Timestamp when the order first entered the Invoiced/Paid stage. "
             "Used for the outstanding-aging counter instead of write_date "
             "(which shifts on any edit).",
        tracking=True,
    )
    price_per_sqf = fields.Float(
        string="Precio por SQF al dealer (USD)",
        digits=(10, 2),
        help="Precio que se cobra al dealer por SQF. Por defecto toma el del dealer.",
        tracking=True,
    )
    installation_fee = fields.Float(
        string="Installation fee (USD)",
        compute="_compute_totals",
        store=True,
        digits=(10, 2),
        help="Distance-based fee from the ZIP zone. Added to the dealer total.",
    )
    install_zone_name = fields.Char(
        string="Install zone",
        compute="_compute_totals",
        store=True,
    )

    # --- Planificacion por distancia (pedido de Majela, 2026-08-15) ---
    #
    # Separado a proposito de install_zone_name / installation_fee, que salen
    # de indigo.install.zone (listas de ZIP -> tarifa, para facturar). Esto es
    # logistica: agrupar por distancia y lado para no mandar al instalador al
    # norte y al sur el mismo dia. Ver models/indigo_install_range.py.
    install_distance_mi = fields.Float(
        string="Distancia (millas)",
        compute="_compute_install_geo",
        store=True,
        digits=(6, 1),
        help="Distancia estimada por carretera desde el taller, calculada "
             "desde el centroide del ZIP y corregida por el factor de rodeo. "
             "Vacia si el ZIP se desconoce.",
    )
    install_bearing = fields.Float(
        string="Rumbo (grados)",
        compute="_compute_install_geo",
        store=True,
        digits=(6, 1),
        help="0 = norte, 90 = este. Se guarda crudo para poder reagrupar por "
             "lado sin recalcular todo.",
    )
    install_direction = fields.Selection(
        [
            ("N", "Norte"), ("NE", "Noreste"), ("E", "Este"), ("SE", "Sureste"),
            ("S", "Sur"), ("SO", "Suroeste"), ("O", "Oeste"), ("NO", "Noroeste"),
        ],
        string="Lado",
        compute="_compute_install_geo",
        store=True,
    )
    install_range_id = fields.Many2one(
        "indigo.install.range",
        string="Rango de distancia",
        compute="_compute_install_geo",
        store=True,
        ondelete="set null",
    )
    total_dealer_charge = fields.Float(
        string="Total a cobrar al dealer (USD)",
        compute="_compute_totals",
        store=True,
        digits=(12, 2),
        help="Precio fijo por puerta (instalacion incluida). No se cobra fee de instalacion aparte.",
    )

    # --- Referencia interna ("PRIV" — campo libre que sale en la etiqueta) ---
    priv_ref = fields.Char(
        string="Ref. interna (PRIV)",
        help="Referencia privada/interna que sale en la etiqueta del disenador.",
        tracking=True,
    )

    # --- Purchase Order del cliente final ---
    # En USA los dealers grandes (Lock Tight, USA Windows...) suelen tener un
    # numero de PO emitido por su cliente final, que el operador necesita
    # conservar para reconciliar pagos/facturacion. Lo separamos de
    # `dealer_ref` (codigo interno del dealer) y `priv_ref` (etiqueta del
    # disenador) porque tienen significados distintos.
    customer_po = fields.Char(
        string="Customer PO",
        help="Purchase order number from the end customer (PO-XXXXXX).",
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

    # --- Disenador asignado (Digitalization -> envio de la Ficha) ---
    # Unlike painter_id/installer_ids (external res.partner contractors),
    # the designer is an internal Odoo LOGIN: group_indigo_designer members
    # need a real email to receive the Ficha de orden, and
    # action_send_to_designer() below emails them directly. So this is a
    # Many2one to res.users (not res.partner), with a domain that only shows
    # designers in the picker; _check_designer_in_group below enforces the
    # same restriction server-side for any caller that skips the UI (portal
    # bridge, panel RPC, MCP).
    designer_id = fields.Many2one(
        "res.users",
        string="Disenador asignado",
        tracking=True,
        domain=lambda model: [
            ("groups_id", "in", model.env.ref("indigo_decors.group_indigo_designer").ids)
        ],
        help="Usuario del grupo Disenador de Indigo al que se envia la "
             "Ficha de orden para digitalizar. Debe tener un email "
             "configurado para poder recibirla.",
    )
    design_sent_date = fields.Datetime(
        string="Ficha enviada el",
        tracking=True,
        help="Cuando se genero y envio por ultima vez la Ficha de orden al "
             "disenador asignado. Vacio = todavia no se le mando nada.",
    )
    design_sent_uid = fields.Many2one(
        "res.users",
        string="Enviada por",
        tracking=True,
        help="Quien disparo el ultimo envio de la Ficha al disenador.",
    )

    @api.constrains("designer_id")
    def _check_designer_in_group(self):
        group = self.env.ref("indigo_decors.group_indigo_designer", raise_if_not_found=False)
        if not group:
            return
        designers = group.sudo().users
        for order in self:
            if order.designer_id and order.designer_id not in designers:
                raise ValidationError(
                    _("%s no pertenece al grupo Disenador de Indigo.") % (order.designer_id.name or "")
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
    # Bandera de incidencia abierta (problema reportado) — independiente de la
    # etapa, para no tener que retroceder la orden solo para anotar.
    incidence = fields.Boolean(string="Incidencia abierta", default=False, tracking=True)

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

    @api.depends(
        "line_ids.qty", "line_ids.sqf", "line_ids.line_charge", "client_zip",
        "dealer_id.indigo_charge_install_fee",
    )
    def _compute_totals(self):
        painter_rate = self._get_painter_rate()
        installer_rate = self._get_installer_rate()
        Zone = self.env["indigo.install.zone"]
        for order in self:
            doors = sum(line.qty for line in order.line_ids)
            sqf = sum(line.sqf for line in order.line_ids)
            design_charge = sum(line.line_charge for line in order.line_ids)
            _fee, zone_name = Zone.fee_for_zip(order.client_zip)
            order.door_count = doors
            order.total_sqf = sqf
            order.total_painter_payout = sqf * painter_rate
            order.total_installer_payout = doors * installer_rate
            # Installation is included in the per-door price ($300 single /
            # $600 double), so it is NOT billed to the dealer as a separate fee.
            # The $35/door stays only as the installer payout above. The zone is
            # still resolved for reference (route planning), but not charged.
            order.installation_fee = 0.0
            order.install_zone_name = zone_name
            # Dealer charge = fixed price per door (by model). SQF is not billed
            # (it only drives the painter payout); install is included in price.
            order.total_dealer_charge = design_charge

    @api.depends("client_zip")
    def _compute_install_geo(self):
        """Distancia, rumbo y rango a partir del ZIP del cliente.

        Depende solo de client_zip, que el propio modelo ya deriva de la
        direccion (ver _zip_from_address, que toma el ULTIMO grupo de 5
        digitos para no confundirse con el numero de la calle).

        Si el ZIP se desconoce, los cuatro campos quedan vacios en vez de
        caer en 0 millas: una orden sin dato y una orden al lado del taller
        no se pueden ver igual en un tablero que se usa para decidir viajes.
        Aparece como "sin clasificar" y se resuelve agregando el ZIP en
        Indigo -> Config -> Geo de ZIPs.
        """
        Geo = self.env["indigo.zip.geo"]
        Range = self.env["indigo.install.range"]
        params = self.env["ir.config_parameter"].sudo()
        try:
            origin_lat = float(params.get_param("indigo_decors.origin_lat") or 0.0)
            origin_lon = float(params.get_param("indigo_decors.origin_lon") or 0.0)
            road_factor = float(params.get_param("indigo_decors.road_factor") or 1.0)
        except (TypeError, ValueError):
            # Un parametro mal escrito a mano no puede tumbar el recalculo de
            # todas las ordenes: se cae a valores neutros y no se inventa nada.
            origin_lat = origin_lon = 0.0
            road_factor = 1.0
        if road_factor <= 0:
            road_factor = 1.0

        for order in self:
            coords = Geo.coords_for_zip(order.client_zip) if order.client_zip else None
            if not coords or (not origin_lat and not origin_lon):
                order.install_distance_mi = 0.0
                order.install_bearing = 0.0
                order.install_direction = False
                order.install_range_id = False
                continue
            lat, lon = coords
            straight = haversine_miles(origin_lat, origin_lon, lat, lon)
            miles = round(straight * road_factor, 1)
            bearing = bearing_degrees(origin_lat, origin_lon, lat, lon)
            order.install_distance_mi = miles
            order.install_bearing = round(bearing, 1)
            order.install_direction = compass_from_bearing(bearing)
            order.install_range_id = Range.range_for_miles(miles).id or False

    @api.model
    def indigo_recompute_install_geo(self):
        """Recalcula la geo de TODAS las ordenes.

        Se llama a mano tras mover el origen o el factor de carretera, o tras
        cargar ZIPs que faltaban -- los campos son `store=True` y dependen
        solo de client_zip, asi que un cambio de parametro no los invalida
        por si solo.
        """
        orders = self.sudo().search([])
        orders._compute_install_geo()
        orders.flush_recordset()
        return len(orders)

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
        # Re-derive ZIP when the address changes (unless ZIP set explicitly),
        # so the distance fee follows the address.
        if "client_address" in vals and "client_zip" not in vals:
            z = _zip_from_address(vals.get("client_address"))
            if z:
                vals["client_zip"] = z
        track_stage = "stage_id" in vals
        previous = {o.id: o.stage_id.id for o in self} if track_stage else {}
        if track_stage:
            vals["last_stage_change"] = fields.Datetime.now()
        # Stamp date_paid the first time payment_state flips to 'paid' so
        # the dashboard's monthly revenue is anchored to the actual payment
        # date instead of being shifted by later edits.
        if vals.get("payment_state") == "paid" and "date_paid" not in vals:
            vals["date_paid"] = fields.Date.context_today(self)
        res = super().write(vals)
        if track_stage:
            generic = self.env.ref(
                "indigo_decors.mail_template_stage_change",
                raise_if_not_found=False,
            )
            stage_painting = self.env.ref("indigo_decors.stage_painting", raise_if_not_found=False)
            stage_installed = self.env.ref("indigo_decors.stage_installed", raise_if_not_found=False)
            stage_invoiced = self.env.ref("indigo_decors.stage_invoiced", raise_if_not_found=False)
            for order in self:
                prev_id = previous.get(order.id)
                if order.stage_id.id == prev_id:
                    continue
                # Stamp the invoicing time once, for the billing aging counter.
                if (stage_invoiced and order.stage_id.id == stage_invoiced.id
                        and not order.invoiced_at):
                    order.invoiced_at = fields.Datetime.now()
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
            if not vals.get("client_zip") and vals.get("client_address"):
                z = _zip_from_address(vals.get("client_address"))
                if z:
                    vals["client_zip"] = z
            if not vals.get("access_token"):
                vals["access_token"] = uuid.uuid4().hex
            if not vals.get("last_stage_change"):
                vals["last_stage_change"] = fields.Datetime.now()
        orders = super().create(vals_list)
        orders._notify_new_order_managers()
        return orders

    def _notify_new_order_managers(self):
        """Email every active administrator (Indigo Manager) when a new order
        arrives, and add them as followers so they also get later updates.
        Queued (force_send=False) so a slow/unconfigured SMTP never blocks
        order creation; never raises."""
        # Internal re-creations (e.g. "Duplicate order" in the panel) pass
        # indigo_skip_new_order_notify=True: a clone the office made itself is
        # not a genuinely new incoming order, so don't spam the managers.
        if self.env.context.get("indigo_skip_new_order_notify"):
            return
        template = self.env.ref(
            "indigo_decors.mail_template_new_order", raise_if_not_found=False
        )
        mgr_group = self.env.ref(
            "indigo_decors.group_indigo_manager", raise_if_not_found=False
        )
        if not template or not mgr_group:
            return
        # Recipients = active managers, minus the system admin (lbencomo94) and
        # anyone who opted out (indigo_skip_order_notify). Computed once here so
        # the email recipients and the followers stay in sync.
        admin = self.env.ref("base.user_admin", raise_if_not_found=False)
        admin_id = admin.id if admin else 0
        recipients = mgr_group.sudo().users.filtered(
            lambda u: u.active
            and u.partner_id
            and u.id != admin_id
            and not u.indigo_skip_order_notify
        )
        mgr_partners = recipients.mapped("partner_id")
        emails = ",".join(recipients.filtered(lambda u: u.email).mapped("email"))
        # Send immediately for a normal single-order creation so admins get the
        # alert right away; queue (cron) for bulk creates (imports) to avoid a
        # synchronous SMTP storm.
        immediate = len(self) == 1
        for order in self:
            try:
                # Override email_to so opted-out users never receive it, even if
                # the template's own recipient expression includes them.
                if emails:
                    template.send_mail(
                        order.id,
                        force_send=immediate,
                        email_values={"email_to": emails},
                    )
                if mgr_partners:
                    order.message_subscribe(partner_ids=mgr_partners.ids)
            except Exception as e:  # noqa: BLE001 — notifications must not break orders
                _logger.warning(
                    "new-order manager notification failed for %s: %s",
                    order.display_name, e,
                )

    def get_tracking_url(self):
        self.ensure_one()
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        return "%s/track/%s" % (base, self.access_token or "")

    # --- Digitalization -> CNC: send the Ficha de orden to the designer ----
    # Majela's 2026-08-15 request: nothing was recorded when she handed the
    # "PDF" (the Ficha de orden report) to the designer, so orders that
    # already had it sat mixed with the ones that didn't inside
    # Digitalization -- indistinguishable, which is how a stale order slipped
    # past her onto a second page. This action makes the stage ITSELF the
    # answer: still in Digitalization = not sent; in CNC = sent.
    def _indigo_assert_can_send_to_designer(self):
        """This is her action (office/manager), not the designer's -- mirrors
        the _indigo_assert_* pattern in indigo_dealer.py / indigo_team.py."""
        u = self.env.user
        if not (
            u._is_admin()
            or u.has_group("indigo_decors.group_indigo_manager")
            or u.has_group("indigo_decors.group_indigo_office")
        ):
            raise AccessError(
                _("Solo el equipo de oficina o los gerentes pueden enviar la orden al disenador.")
            )

    @api.model
    def indigo_list_designers(self):
        """Active users in the Disenador group, for the panel's picker."""
        self._indigo_assert_can_send_to_designer()
        group = self.env.ref("indigo_decors.group_indigo_designer", raise_if_not_found=False)
        if not group:
            return []
        users = group.sudo().users.filtered(lambda u: u.active)
        return [
            {"id": u.id, "name": u.name or u.login or "", "email": u.email or u.login or ""}
            for u in users
        ]

    def action_send_to_designer(self):
        """Render the Ficha de orden, attach it to the order, email it to
        the assigned designer, and advance the order to CNC.

        Idempotent-safe by design rather than by refusal: she may genuinely
        need to press this twice (the designer says they lost the PDF), so
        calling it again re-renders + re-attaches + re-emails and refreshes
        design_sent_date/uid to the latest send -- but it only MOVES the
        stage the first time (next_stage.id != stage_id.id guard below), so
        a resend can never duplicate a stage transition or anything tied to
        leaving a stage (e.g. a payout). Nothing here reads the current
        stage to decide whether to run -- that's left to the UI (the button
        only shows while stage_code == 'ready_digitalization', same pattern
        as every other stage wizard button) so a genuine resend from a later
        screen keeps working if one gets added.
        """
        self.ensure_one()
        self._indigo_assert_can_send_to_designer()
        # Nunca desde una etapa POSTERIOR a CNC. El paso 4 mueve la orden a
        # CNC siempre que no este ya ahi, asi que llamar a esto sobre una
        # orden en Pintura la moveria HACIA ATRAS -- y ese retroceso dispara
        # el hook de write() que crea el pago al pintor con el SQF que
        # hubiera en ese momento (y el guard de deduplicacion despues impide
        # emitir el correcto). Hoy los tres llamadores reales filtran por
        # etapa, pero "el llamador ya lo valida" es justamente el patron que
        # este trabajo vino a eliminar.
        #
        # Se compara por `sequence` y no por una lista de codigos a proposito:
        # las etapas 2-5 son opcionales por dealer (ver CLAUDE.md), asi que
        # una orden puede llegar aqui desde varias etapas anteriores
        # distintas. Adelantar es legitimo; retroceder no.
        stage_cnc = self.env.ref("indigo_decors.stage_cnc", raise_if_not_found=False)
        if stage_cnc and self.stage_id and self.stage_id.sequence > stage_cnc.sequence:
            raise UserError(_(
                "La orden %(orden)s ya paso de CNC (esta en '%(etapa)s'). Enviar la "
                "Ficha ahora la haria retroceder, y eso dispararia el pago al pintor "
                "con datos incompletos."
            ) % {"orden": self.name or "", "etapa": self.stage_id.name or ""})
        if not self.designer_id:
            raise UserError(
                _("Asigna un disenador a esta orden antes de enviarle la Ficha.")
            )
        if not self.designer_id.email:
            raise UserError(
                _("El disenador asignado (%s) no tiene un email configurado.")
                % (self.designer_id.name or "")
            )

        # 1) Render + attach FIRST. If this raises (bad report data, etc.)
        #    the whole call aborts and nothing else below runs -- the order
        #    stays in Digitalization and she sees a clear error to fix and
        #    retry, instead of silently losing the PDF.
        pdf_content, _report_format = self.env["ir.actions.report"].sudo()._render_qweb_pdf(
            "indigo_decors.action_report_order_card", res_ids=self.ids
        )
        # Order names carry slashes (IND/2026/00291), which make a poor
        # filename. And a re-send must be tellable apart from the original at a
        # glance, so the send timestamp goes in the name rather than leaving
        # two identically-named PDFs on the order.
        safe_ref = (self.name or "orden").replace("/", "-")
        # Seconds, not minutes: a re-send usually happens moments after the
        # first one, and minute precision left two identically-named PDFs.
        stamp = fields.Datetime.now().strftime("%Y-%m-%d_%H%M%S")
        attachment = self.env["ir.attachment"].sudo().create({
            "name": "Ficha_%s_%s.pdf" % (safe_ref, stamp),
            "type": "binary",
            "datas": base64.b64encode(pdf_content),
            "res_model": "indigo.order",
            "res_id": self.id,
            "mimetype": "application/pdf",
        })

        # 2) Stamp who/when BEFORE the email step and BEFORE the stage move:
        #    a mail hiccup below can never lose the fact that the PDF was
        #    generated and attached, and the attachment is already saved on
        #    the order regardless of what happens next.
        self.write({
            "design_sent_date": fields.Datetime.now(),
            "design_sent_uid": self.env.user.id,
        })

        # 3) Email the designer, attaching the SAME ir.attachment created
        #    above (no re-render). force_send=True: this is a single order,
        #    same "notify right away" treatment as a lone new-order alert
        #    (_notify_new_order_managers). The try/except is NOT redundant
        #    with Odoo's own mail.mail.send() -- that method swallows most
        #    SMTP failures internally (state='exception', no raise) but
        #    deliberately RE-RAISES psycopg2.Error / SMTPServerDisconnected,
        #    and a template render error would raise too. Either way, a
        #    failure here must never block the stage advance below, or an
        #    order she just processed would get stuck in Digitalization
        #    over a mail-server hiccup -- worse than an email she can
        #    resend by pressing the button again.
        template = self.env.ref(
            "indigo_decors.mail_template_send_to_designer", raise_if_not_found=False
        )
        if not template:
            raise UserError(_(
                "Falta la plantilla de correo para el disenador "
                "(indigo_decors.mail_template_send_to_designer). Avisa a soporte."
            ))
        fallo = None
        try:
            mail_id = template.sudo().send_mail(
                self.id,
                force_send=True,
                email_values={
                    "email_to": self.designer_id.email,
                    "attachment_ids": [(4, attachment.id)],
                },
            )
            # send_mail() NO alcanza para saber si salio. mail.mail.send()
            # se traga casi todos los fallos SMTP por dentro (deja
            # state='exception' y no lanza) y solo re-lanza psycopg2.Error /
            # SMTPServerDisconnected. Sin mirar el estado del mail.mail, un
            # servidor mal configurado -- p.ej. odoo.conf apuntando todavia a
            # mailhog, o el ir.mail_server perdido al recrear el volumen
            # db-data -- hacia que TODO envio "funcionara" y toda orden pasara
            # igual a CNC. Eso es exactamente el bug que Majela describio
            # ("entro una puerta y no me di cuenta"), reintroducido por el
            # arreglo de ese bug.
            mail = self.env["mail.mail"].sudo().browse(mail_id).exists()
            if not mail:
                fallo = _("el correo no llego a generarse")
            elif mail.state == "exception":
                fallo = mail.failure_reason or _("el servidor de correo lo rechazo")
            elif mail.state != "sent":
                fallo = _("quedo en cola sin enviarse (estado '%s')") % mail.state
        except Exception as e:  # noqa: BLE001 - se convierte en UserError legible
            _logger.warning(
                "action_send_to_designer: email failed for %s: %s", self.name, e
            )
            fallo = str(e)

        if fallo:
            # No se avanza ni se marca como enviada. La etapa es la respuesta
            # a "que esta hecho y que no" -- si el correo no salio, la orden
            # NO esta hecha, y dejarla en Digitalizacion es lo unico honesto.
            # Ademas el boton de enviar solo se ve en esta etapa: avanzar
            # igual le quitaria el reintento de un clic.
            raise UserError(_(
                "No se pudo enviar la Ficha a %(disenador)s (%(email)s): %(motivo)s. "
                "La orden se queda en Digitalizacion para que puedas reintentar. "
                "Si vuelve a fallar, avisa a soporte: es el servidor de correo, "
                "no la orden."
            ) % {
                "disenador": self.designer_id.name or "",
                "email": self.designer_id.email or "",
                "motivo": fallo,
            })

        self.message_post(
            body=_("Ficha de orden enviada a %s (disenador).") % (self.designer_id.name or ""),
            attachment_ids=[attachment.id],
        )

        # 4) Advance the stage LAST, and only if it hasn't already happened
        #    (a resend from CNC is a stage no-op).
        stage_cnc = self.env.ref("indigo_decors.stage_cnc", raise_if_not_found=False)
        if stage_cnc and self.stage_id.id != stage_cnc.id:
            self.stage_id = stage_cnc.id

        return True

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
        # Sin SQF no se crea el payout. `quantity` se congela aqui (es un
        # float almacenado en indigo.payout.line, no un related), y el guard
        # de `existing` de abajo impide crear un segundo payout para la misma
        # orden -- asi que un payout emitido en 0 no se puede corregir nunca
        # mas: corregir line.sqf despues no lo recalcula, y el correcto ya no
        # se puede generar. Es preferible NO emitirlo y avisar en el chatter:
        # asi, cuando alguien cargue el SQF que falta, la siguiente transicion
        # todavia puede generarlo bien.
        sin_sqf = self.line_ids.filtered(lambda l: not l.sqf or l.sqf <= 0)
        if sin_sqf:
            self.message_post(body=_(
                "No se genero el pago al pintor: %(faltan)d de %(total)d pieza(s) "
                "no tienen SQF cargado. Carga el SQF real de cada pieza y avisa "
                "a oficina para generar la liquidacion; si se emitiera ahora "
                "seria de $0 y no se podria corregir."
            ) % {"faltan": len(sin_sqf), "total": len(self.line_ids)})
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
        payout = self.env["indigo.payout"].sudo().create({
            "contractor_id": self.painter_id.id,
            "contractor_type": "painter",
            "notes": "Generada automaticamente al completar pintura de orden %s." % self.name,
        })
        for line in self.line_ids:
            self.env["indigo.payout.line"].sudo().create({
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
            payout = self.env["indigo.payout"].sudo().create({
                "contractor_id": installer.id,
                "contractor_type": "installer",
                "notes": "Generada automaticamente al completar instalacion de orden %s." % self.name,
            })
            self.env["indigo.payout.line"].sudo().create({
                "payout_id": payout.id,
                "order_id": self.id,
                "description": "Instalacion orden %s (%s puertas / %s instaladores)" % (
                    self.name, self.door_count, len(self.installer_ids)
                ),
                "quantity": share,
                "rate": rate,
            })
