# -*- coding: utf-8 -*-
"""Motivos de espera, como lista editable en vez de texto libre.

`hold_cause` responde QUIEN destraba la orden (el dealer o el cliente) y por
eso es una Selection cerrada: solo con eso se puede contar y colorear. Este
modelo responde QUE pasa exactamente -- "el cliente esta de viaje", "falta
cambiar un vidrio" -- que hasta ahora era un Char libre.

El texto libre no se puede contar ni filtrar: "no responde", "No Responde" y
"no contesta" son tres motivos distintos para la maquina y el mismo para
quien trabaja. Con una lista, Majela ve "7 puertas trabadas por falta de
piezas" sin tener que leer 7 renglones.

Editable a proposito: la lista sembrada es un punto de partida, no una
verdad. Ella agrega los suyos desde Indigo -> Config -> Motivos de espera,
sin tocar codigo. Y `hold_reason` (el Char) se conserva para el detalle que
no entra en ninguna etiqueta.
"""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class IndigoHoldReason(models.Model):
    _name = "indigo.hold.reason"
    _description = "Motivo por el que una orden queda en espera"
    _order = "cause, sequence, name"

    name = fields.Char(string="Motivo", required=True, translate=True)
    sequence = fields.Integer(default=10)
    cause = fields.Selection(
        [
            ("dealer", "Problema del dealer"),
            ("client", "Problema del cliente"),
            ("other", "Otro / sin clasificar"),
        ],
        string="Causa",
        required=True,
        default="other",
        help="A que columna pertenece. Determina quien tiene que destrabarlo.",
    )
    color = fields.Char(
        string="Color",
        default="#64748b",
        help="Color de la etiqueta en el panel (hex, p. ej. #dc2626).",
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("name_cause_uniq", "unique(name, cause)",
         "Ya existe un motivo con ese nombre para esa causa."),
    ]

    @api.constrains("color")
    def _check_color(self):
        for rec in self:
            value = (rec.color or "").strip()
            if value and not (value.startswith("#") and len(value) in (4, 7)):
                raise ValidationError(
                    _("El color tiene que ser hexadecimal, como #dc2626.")
                )

    def name_get(self):
        # El panel agrupa por causa, asi que el nombre solo alcanza; pero en
        # un desplegable suelto conviene ver a que columna pertenece.
        labels = dict(self._fields["cause"].selection)
        return [(r.id, "%s (%s)" % (r.name, labels.get(r.cause, ""))) for r in self]
