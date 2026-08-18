# -*- coding: utf-8 -*-
"""Rangos de distancia para PLANIFICAR la instalacion.

Ojo con no confundirlo con `indigo.install.zone`, que existe desde antes y
hace otra cosa: aquel mapea listas de ZIP a una TARIFA, para cobrarle el
recargo por distancia al cliente. Este agrupa por millas calculadas, para
decidir a quien se manda junto el mismo dia. Se dejan separados a proposito:
uno es facturacion y el otro logistica, y mezclarlos haria que tocar la
planificacion moviera precios.

El motivo de existir es concreto. Hoy las zonas de tarifa se mantienen a
mano, ZIP por ZIP, y en produccion **62 de 249 ordenes (25%) no caen en
ninguna**: sus ZIPs nunca se agregaron a las listas. Una distancia calculada
no se puede desactualizar asi.
"""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class IndigoInstallRange(models.Model):
    _name = "indigo.install.range"
    _description = "Rango de distancia para planificar instalaciones"
    _order = "sequence, min_miles"

    name = fields.Char(string="Rango", required=True, translate=True)
    short_name = fields.Char(
        string="Etiqueta corta",
        translate=True,
        help="Lo que se muestra en la tabla, p. ej. 'LOCAL' o 'REGIONAL'.",
    )
    sequence = fields.Integer(default=10)
    min_miles = fields.Float(string="Desde (millas)", digits=(6, 1), default=0.0)
    max_miles = fields.Float(
        string="Hasta (millas)",
        digits=(6, 1),
        help="Limite superior EXCLUSIVO. Dejar en 0 para 'sin limite' "
             "(el ultimo rango, el de larga distancia).",
    )
    color = fields.Char(
        string="Color",
        default="#64748b",
        help="Color de la etiqueta en el panel (hex, p. ej. #16a34a).",
    )
    active = fields.Boolean(default=True)

    @api.constrains("min_miles", "max_miles")
    def _check_bounds(self):
        for rec in self:
            if rec.min_miles < 0 or rec.max_miles < 0:
                raise ValidationError(_("Las millas no pueden ser negativas."))
            if rec.max_miles and rec.max_miles <= rec.min_miles:
                raise ValidationError(
                    _("En el rango '%s' el limite superior tiene que ser mayor que el inferior "
                      "(o 0 para dejarlo sin limite).") % (rec.name or "")
                )

    @api.model
    def range_for_miles(self, miles):
        """Primer rango que contiene esa distancia, o un recordset vacio.

        `max_miles` es exclusivo para que los rangos contiguos (0-35, 35-45)
        no se solapen: 35.0 exactas caen en el segundo, una sola vez.
        """
        if miles is None:
            return self.browse()
        for rng in self.sudo().search([]):
            if miles < rng.min_miles:
                continue
            if not rng.max_miles or miles < rng.max_miles:
                return rng
        return self.browse()
