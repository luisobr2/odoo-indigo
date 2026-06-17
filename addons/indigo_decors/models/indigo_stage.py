# -*- coding: utf-8 -*-
from odoo import fields, models


class IndigoStage(models.Model):
    _name = "indigo.stage"
    _description = "Etapa del pipeline Indigo"
    _order = "sequence, id"

    name = fields.Char(string="Nombre", required=True, translate=True)
    sequence = fields.Integer(string="Secuencia", default=10)
    code = fields.Char(string="Codigo", help="Identificador interno (ej. 'cnc', 'painting')")
    _sql_constraints = [
        ("code_uniq", "unique(code)",
         "El codigo de etapa debe ser unico — el dashboard, stock y payouts "
         "buscan etapas por codigo."),
    ]
    is_optional = fields.Boolean(
        string="Opcional por dealer",
        help="Si se marca, esta etapa solo aparece para los dealers que la tengan activada en su pipeline.",
    )
    fold = fields.Boolean(string="Plegada en kanban", default=False)
    description = fields.Text(string="Descripcion", translate=True)
    active = fields.Boolean(default=True)
    notify_template_id = fields.Many2one(
        "mail.template",
        string="Plantilla de notificacion",
        domain="[('model', '=', 'indigo.order')]",
        help="Plantilla de correo enviada al entrar a esta etapa. Si esta vacia, usa la generica.",
    )
    sla_days = fields.Integer(
        string="Dias SLA",
        default=0,
        help="Dias maximos que una orden deberia estar en esta etapa antes de marcarse atrasada. 0 = sin SLA.",
    )
