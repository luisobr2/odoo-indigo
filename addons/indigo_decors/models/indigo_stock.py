# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IndigoStock(models.Model):
    """Inventario simple de piezas CNC ya cortadas listas para pintar.

    Track manual del taller: el admin ajusta on_hand cuando CNC produce piezas
    y se descuenta automaticamente al avanzar a 'Painting' las ordenes que las usan.
    """
    _name = "indigo.stock"
    _description = "Stock de piezas (CNC -> pintura)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "design_id, id"
    _rec_name = "design_id"

    design_id = fields.Many2one("indigo.design", string="Diseno", required=True, index=True)
    door_type = fields.Selection(
        [("SD", "Single Door"), ("DD", "Double Door"), ("sidelite", "Door with Sidelites")],
        string="Tipo",
        required=True,
    )
    on_hand = fields.Integer(
        string="En existencia (CNC)",
        default=0,
        help="Piezas ya cortadas listas para pintar. Ajustar manualmente cuando CNC produce.",
    )
    reserved = fields.Integer(
        string="Reservadas",
        compute="_compute_reserved",
        help="Piezas en ordenes activas que aun no llegaron a Painting (consumiran stock).",
    )
    available = fields.Integer(
        string="Disponibles",
        compute="_compute_reserved",
        store=False,
    )
    low_stock_threshold = fields.Integer(
        string="Umbral bajo",
        default=5,
        help="Si disponibles cae debajo de este valor, se notifica.",
    )
    is_low_stock = fields.Boolean(
        compute="_compute_reserved",
        search="_search_is_low_stock",
    )

    _sql_constraints = [
        ("design_type_uniq", "unique(design_id, door_type)",
         "Solo puede existir un registro de stock por combinacion diseno+tipo."),
    ]

    @api.depends("design_id", "door_type", "on_hand")
    def _compute_reserved(self):
        Order = self.env["indigo.order"]
        for s in self:
            # Ordenes activas (no closed/installed) que requieren esta combinacion
            orders = Order.search([
                ("stage_id.code", "not in", ["closed", "installed", "invoiced"]),
                ("line_ids.design_id", "=", s.design_id.id),
                ("line_ids.door_type", "=", s.door_type),
            ])
            qty = 0
            for o in orders:
                for line in o.line_ids:
                    if line.design_id.id == s.design_id.id and line.door_type == s.door_type:
                        qty += line.qty
            s.reserved = qty
            s.available = (s.on_hand or 0) - qty
            s.is_low_stock = s.available < (s.low_stock_threshold or 0)

    def _search_is_low_stock(self, operator, value):
        # Filtro busqueda: low stock = available < threshold
        # Resolvemos en Python (sin SQL complicado por ser computed non-stored)
        results = self.search([])
        ids = [r.id for r in results if (r.available < (r.low_stock_threshold or 0)) == value]
        return [("id", "in", ids)] if ids else [("id", "=", False)]

    @api.model
    def _cron_low_stock_alert(self):
        low = self.search([]).filtered(lambda s: s.is_low_stock)
        if not low:
            return 0
        # Notificar a managers via activity
        Activity = self.env["mail.activity"]
        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        if not activity_type:
            return 0
        managers = self.env.ref("indigo_decors.group_indigo_manager").users
        if not managers:
            return 0
        summary = "Indigo: %s items con stock bajo" % len(low)
        lines = "\n".join(
            "- %s %s: %s disponibles (umbral %s)" % (s.design_id.code, s.door_type, s.available, s.low_stock_threshold)
            for s in low
        )
        for mgr in managers:
            Activity.create({
                "res_model": "indigo.stock",
                "res_model_id": self.env.ref("indigo_decors.model_indigo_stock").id,
                "res_id": low[0].id,
                "user_id": mgr.id,
                "activity_type_id": activity_type.id,
                "summary": summary,
                "note": lines,
            })
        return len(low)
