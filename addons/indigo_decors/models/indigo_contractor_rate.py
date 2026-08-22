# -*- coding: utf-8 -*-
"""Como se le paga a cada contratista.

Empezo como una tarifa suelta (un numero por unidad). El 2026-08-21 Majela
explico los acuerdos reales con los instaladores y resultaron ser dos
formas distintas, ninguna de las cuales es "tanto por puerta":

    "Mandy siempre es 150 x dia mas 10 por cada instalacion que
     corresponde a gasolina y tolls"
    "Lazaro 150 si las puertas suman menos que eso. Cada puerta es 35"

Las dos entran en una sola formula, aplicada sobre el DIA de trabajo:

    pago del dia = max(minimo_diario, tarifa * unidades) + bono * instalaciones

  Mandy:  minimo 150, tarifa 0,  bono 10  -> 150 + 10 * instalaciones
  Lazaro: minimo 150, tarifa 35, bono 0   -> max(150, 35 * puertas)

Mandy no cobra por puerta: su tarifa es 0 y por eso el minimo es siempre
su piso. No hay dos motores de calculo, hay tres numeros por persona --
y los tres se editan desde el panel, que era el requisito explicito.

Una regla con `partner_id` es de esa persona; sin `partner_id` es la que
se aplica a quien no tenga la suya. Asi un instalador nuevo cobra algo
razonable desde el primer dia sin que nadie configure nada.
"""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class IndigoContractorRate(models.Model):
    _name = "indigo.contractor.rate"
    _description = "Regla de pago de un contratista"
    # La regla especifica gana sobre la de por defecto: al ordenar con los
    # partner_id primero, un search(..., limit=1) devuelve la correcta.
    _order = "contractor_type, partner_id, id"

    name = fields.Char(string="Nombre", required=True)
    contractor_type = fields.Selection(
        [
            ("painter", "Pintor"),
            ("installer", "Instalador"),
            ("other", "Otro"),
        ],
        string="Tipo",
        required=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Contratista",
        index=True,
        help="De quien es esta regla. Vacio = regla por defecto, la que se "
             "aplica a quien no tenga una propia.",
    )
    rate = fields.Float(string="Tarifa (USD)", required=True, digits=(10, 2))
    rate_unit = fields.Selection(
        [
            ("sqf", "Por SQF"),
            ("piece", "Por pieza"),
        ],
        string="Unidad",
        required=True,
        default="sqf",
    )

    # --- Reglas del dia (solo instaladores por ahora) ---
    daily_minimum = fields.Float(
        string="Minimo diario (USD)",
        digits=(10, 2),
        default=0.0,
        help="Lo menos que se le paga por una jornada con trabajo. 0 = sin "
             "minimo (se paga solo lo que salga por unidad). Si la tarifa por "
             "unidad es 0, este monto ES la tarifa diaria.",
    )
    bonus_amount = fields.Float(
        string="Bono (USD)",
        digits=(10, 2),
        default=0.0,
        help="Se suma ADEMAS del minimo, no compite con el. Pensado para "
             "gastos de viaje (gasolina, peajes). 0 = sin bono.",
    )
    bonus_unit = fields.Selection(
        [
            ("order", "Por instalacion (orden)"),
            ("door", "Por puerta"),
        ],
        string="Bono por",
        default="order",
        help="Si el bono se cuenta una vez por orden instalada o una vez por "
             "puerta.",
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("partner_type_uniq", "unique(partner_id, contractor_type)",
         "Ese contratista ya tiene una regla para ese tipo."),
    ]

    @api.constrains("rate", "daily_minimum", "bonus_amount")
    def _check_no_negatives(self):
        for rec in self:
            if rec.rate < 0 or rec.daily_minimum < 0 or rec.bonus_amount < 0:
                raise ValidationError(
                    _("Las tarifas, minimos y bonos no pueden ser negativos.")
                )

    @api.constrains("partner_id", "contractor_type", "active")
    def _check_one_default(self):
        """Una sola regla por defecto por tipo.

        El _sql_constraints de arriba NO cubre esto: en Postgres dos NULL
        son distintos, asi que la clave unica deja pasar varias reglas sin
        contratista. Con dos, `resolve_for` elegiria una arbitrariamente y
        el pago dependeria del orden de creacion -- un error silencioso y
        dificil de ver.
        """
        for rec in self:
            if rec.partner_id or not rec.active:
                continue
            otras = self.search_count([
                ("id", "!=", rec.id),
                ("partner_id", "=", False),
                ("contractor_type", "=", rec.contractor_type),
                ("active", "=", True),
            ])
            if otras:
                raise ValidationError(_(
                    "Ya hay una regla por defecto activa para ese tipo de "
                    "contratista. Puede haber una sola: o le asignas un "
                    "contratista a esta, o desactivas la otra."
                ))

    @api.constrains("contractor_type", "rate_unit")
    def _check_installer_unit(self):
        """El pago del instalador se calcula por PUERTA.

        `day_amount` multiplica la tarifa por puertas siempre. Dejar que
        alguien ponga "por SQF" en un instalador no cambiaria el calculo,
        solo la etiqueta -- y una etiqueta que miente sobre plata es peor
        que un error.
        """
        for rec in self:
            if rec.contractor_type == "installer" and rec.rate_unit != "piece":
                raise ValidationError(_(
                    "La tarifa de un instalador se cuenta por pieza (puerta). "
                    "El SQF es la unidad del pintor."
                ))

    @api.model
    def resolve_for(self, contractor_type, partner=None):
        """La regla que aplica a `partner`, o la de por defecto.

        Devuelve un recordset vacio si no hay ninguna configurada -- quien
        llama decide el fallback, porque el valor sensato depende del caso.
        """
        domain = [("contractor_type", "=", contractor_type), ("active", "=", True)]
        if partner:
            own = self.search(domain + [("partner_id", "=", partner.id)], limit=1)
            if own:
                return own
        return self.search(domain + [("partner_id", "=", False)], limit=1)

    def day_amount(self, unit_total, installs, doors):
        """Cuanto cobra por UNA jornada.

        `unit_total` es lo que ya suman los renglones de trabajo, NO las
        puertas: quien llama multiplica. Parece un rodeo y es a proposito
        -- si esta funcion recalculara `tarifa * puertas` por su cuenta y
        la tarifa hubiera cambiado despues de emitirse los renglones, el
        total y los renglones dirian cosas distintas, y la diferencia se
        colaria disfrazada de bono. Con el total como entrada hay una sola
        definicion de la jornada.

        `installs` y `doors` van los dos porque el bono se puede contar de
        cualquiera de las dos formas.
        """
        self.ensure_one()
        base = max(self.daily_minimum or 0.0, unit_total or 0.0)
        count = doors if self.bonus_unit == "door" else installs
        return base + (self.bonus_amount or 0.0) * (count or 0.0)
