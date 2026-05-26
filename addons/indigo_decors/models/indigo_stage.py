# -*- coding: utf-8 -*-
from odoo import fields, models


class IndigoStage(models.Model):
    _name = "indigo.stage"
    _description = "Etapa del pipeline Indigo"
    _order = "sequence, id"

    name = fields.Char(string="Nombre", required=True, translate=True)
    sequence = fields.Integer(string="Secuencia", default=10)
    code = fields.Char(string="Codigo", help="Identificador interno (ej. 'cnc', 'painting')")
    is_optional = fields.Boolean(
        string="Opcional por dealer",
        help="Si se marca, esta etapa solo aparece para los dealers que la tengan activada en su pipeline.",
    )
    fold = fields.Boolean(string="Plegada en kanban", default=False)
    description = fields.Text(string="Descripcion", translate=True)
    active = fields.Boolean(default=True)
