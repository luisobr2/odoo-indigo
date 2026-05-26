# -*- coding: utf-8 -*-
from odoo import fields, models


class IndigoDesign(models.Model):
    _name = "indigo.design"
    _description = "Diseno del catalogo Indigo"
    _order = "code"

    code = fields.Char(string="Codigo", required=True, index=True, help="Ej. ID01, TD-SD-W06")
    name = fields.Char(string="Nombre", translate=True)
    door_type = fields.Selection(
        [
            ("SD", "Single Door"),
            ("DD", "Double Door"),
            ("sidelite", "Door with Sidelites"),
        ],
        string="Tipo de puerta",
    )
    image = fields.Image(string="Imagen", max_width=1024, max_height=1024)
    description = fields.Text(string="Descripcion", translate=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("code_uniq", "unique(code)", "El codigo del diseno debe ser unico."),
    ]
