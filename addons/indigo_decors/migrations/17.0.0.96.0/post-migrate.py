# -*- coding: utf-8 -*-
"""Deja configurados los acuerdos reales de pago a instaladores.

Majela los explico por WhatsApp el 2026-08-21, textual:

    "Por dia son 150"
    "Mandy siempre es 150 x dia mas 10 por cada instalacion que
     corresponde a gasolina y tolls"
    "Lazaro 150 si las puertas suman menos que eso. Cada puerta es 35"

Hasta ahora el sistema pagaba 35 por puerta y nada mas. Medido sobre las
liquidaciones reales, 49 de 53 jornadas tuvieron 4 puertas o menos -- por
debajo del minimo -- asi que la regla vieja se equivocaba el 92% de los
dias.

Esta migracion NO reescribe plata. Configura las reglas y rellena el dia
de trabajo de las liquidaciones que ya existen (metadato, no monto).
Recalcular los borradores es una accion aparte y a proposito:
`env['indigo.payout'].indigo_recompute_installer_days(desde, hasta)`.
Las liquidaciones ya pagadas no se tocan ni ahi.
"""
import logging

_logger = logging.getLogger(__name__)

# Los tres numeros de cada acuerdo. Se siembran una vez; a partir de aca
# se editan desde Settings del panel, no desde el codigo.
ACUERDOS = [
    # (como buscar al contratista, tarifa/puerta, minimo diario, bono, unidad)
    ("mandy", 0.0, 150.0, 10.0, "order"),
    ("lazaro", 35.0, 150.0, 0.0, "order"),
]


def migrate(cr, version):
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    Rate = env["indigo.contractor.rate"]
    Payout = env["indigo.payout"]

    # 1. La regla por defecto gana el minimo diario. Es la que cobra quien
    #    no tenga la suya -- hoy, Amado Puebla.
    defecto = Rate.search([
        ("contractor_type", "=", "installer"),
        ("partner_id", "=", False),
    ], limit=1)
    if defecto and not defecto.daily_minimum:
        defecto.daily_minimum = 150.0
        _logger.info("indigo_decors: minimo diario de 150 en la regla por defecto")

    # 2. Reglas propias. Se busca SOLO entre quienes ya tienen
    #    liquidaciones de instalador, para no engancharse con un homonimo
    #    del padron de contactos.
    conocidos = Payout.search([("contractor_type", "=", "installer")]).mapped(
        "contractor_id"
    )
    for aguja, tarifa, minimo, bono, unidad in ACUERDOS:
        partner = conocidos.filtered(
            lambda p, a=aguja: a in (p.name or "").lower()
        )[:1]
        if not partner:
            _logger.warning(
                "indigo_decors: no encontre a '%s' entre los instaladores con "
                "liquidaciones; usara la regla por defecto hasta que se "
                "configure la suya", aguja,
            )
            continue
        existente = Rate.search([
            ("contractor_type", "=", "installer"),
            ("partner_id", "=", partner.id),
        ], limit=1)
        vals = {
            "name": partner.name,
            "contractor_type": "installer",
            "partner_id": partner.id,
            "rate": tarifa,
            "rate_unit": "piece",
            "daily_minimum": minimo,
            "bonus_amount": bono,
            "bonus_unit": unidad,
        }
        if existente:
            _logger.info("indigo_decors: la regla de %s ya existia, se respeta",
                         partner.name)
        else:
            Rate.create(vals)
            _logger.info(
                "indigo_decors: regla de %s -> %s/puerta, minimo %s, bono %s por %s",
                partner.name, tarifa, minimo, bono, unidad,
            )

    # 3. Rellenar el dia trabajado. Sin esto una jornada vieja no se
    #    reconoce como tal y el trabajo nuevo del mismo dia abriria una
    #    liquidacion suelta al lado.
    sin_dia = Payout.search([
        ("contractor_type", "=", "installer"),
        ("work_date", "=", False),
    ])
    rellenadas = 0
    for payout in sin_dia:
        dias = [d for d in payout.line_ids.mapped("date_work") if d]
        if not dias:
            dias = [
                o.installation_date
                for o in payout.line_ids.mapped("order_id")
                if o.installation_date
            ]
        if dias:
            payout.work_date = min(dias)
            rellenadas += 1
    _logger.info("indigo_decors: dia de trabajo rellenado en %s liquidaciones "
                 "(de %s sin dia)", rellenadas, len(sin_dia))
