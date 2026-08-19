# -*- coding: utf-8 -*-
"""Centroide geografico de cada ZIP, para calcular distancia y rumbo.

Por que una tabla propia y no un servicio de geocodificacion:

- Los rangos que usa el taller son anchos (0-35, 35-45, 45-90...). Un
  centroide de ZIP se desvia 1-3 millas en zona urbana, o sea que casi nunca
  puede mover una puerta de rango -- solo justo en un borde.
- Las direcciones que llegan son texto libre y sucio ("813 SW 3rd AveBoynton
  Beach", "9355 W OKEECHOBEE RD Bay # 7"). Un geocodificador falla con
  varias; el ZIP se lee bien en el 96% de las ordenes reales.
- No agrega una dependencia externa (cuenta, API key, cuota, latencia, y un
  servicio mas que puede estar caido) a un sistema que hoy no tiene ninguna.

Los datos salen del Gazetteer de ZCTA del censo de EE.UU. (dominio publico),
recortado a Florida: `data/indigo.zip.geo.csv`. Si aparece un ZIP que no
esta, se agrega a mano desde Indigo -> Config -> Geo de ZIPs; mientras
tanto la orden queda sin distancia, que es mas honesto que inventarsela.
"""
import math

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# Radio medio de la Tierra en millas.
_EARTH_RADIUS_MI = 3958.8

# Corredores de manejo, no puntos de brujula.
#
# El rumbo geometrico no sirve para planificar, y hay un caso que lo prueba:
# Fort Myers (140 millas, cruzando los Everglades por Alligator Alley) y Doral
# (17 millas) salen los dos "Oeste". Mismo angulo, viajes que no tienen nada
# que ver. Los corredores los definio Majela el 2026-08-19 por criterio
# practico -- por que autopista se sale, no por que direccion cae.
CORRIDORS = [
    ("S", "SOUTH"),   # baja a south Miami-Dade y los Cayos
    ("C", "CENTRAL"), # Miami y el area inmediata al taller
    ("W", "WEST"),    # Doral, Sweetwater, Tamiami, Weston
    ("N", "NORTH"),   # sube por I-95 / Turnpike a Broward y Palm Beach
    ("SW", "SOUTHWEST"),  # cruza a la costa oeste: Naples, Fort Myers
]

CORRIDOR_LABELS = dict(CORRIDORS)


def haversine_miles(lat1, lon1, lat2, lon2):
    """Distancia en linea recta, en millas, entre dos puntos."""
    rlat1, rlon1, rlat2, rlon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * _EARTH_RADIUS_MI * math.asin(math.sqrt(a))


def bearing_degrees(lat1, lon1, lat2, lon2):
    """Rumbo inicial en grados (0 = norte, 90 = este) del punto 1 al 2."""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(rlat2)
    x = math.cos(rlat1) * math.sin(rlat2) - math.sin(rlat1) * math.cos(rlat2) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def corridor_from_coords(lat, lon):
    """Corredor de manejo para un punto, sembrando la tabla de ZIPs.

    Reproduce el 93% de los ejemplos que dio Majela. El 7% restante son casos
    donde su tabla agrupa por NOMBRE DE CIUDAD y no por geografia -- Hialeah y
    Pembroke Pines se extienden tan al oeste como Weston, pero ella los llama
    CENTRAL y NORTH. Ninguna formula sobre coordenadas puede saber eso, asi
    que esos ZIP vienen ya corregidos en el CSV y el campo queda editable:
    donde ella se pronuncio, manda ella.
    """
    # Arriba de Palm Beach ya no hay corredores locales: se sube por la
    # Turnpike / I-95 y punto. Orlando, Tampa y Jacksonville son NORTH.
    if lat > 26.9:
        return "N"
    # Costa oeste cruzando los Everglades. El piso de latitud deja fuera los
    # Cayos, que tambien caen al oeste en longitud pero son viaje al SUR.
    if lon < -80.9 and lat > 25.5:
        return "SW"
    if lat < 25.71:
        return "S"
    if lat >= 25.92:
        return "W" if lon < -80.33 else "N"
    return "W" if lon < -80.30 else "C"


class IndigoZipGeo(models.Model):
    _name = "indigo.zip.geo"
    _description = "Centroide geografico de un ZIP"
    _order = "zip"
    _rec_name = "zip"

    zip = fields.Char(string="ZIP", required=True, index=True)
    latitude = fields.Float(string="Latitud", digits=(10, 6), required=True)
    longitude = fields.Float(string="Longitud", digits=(10, 6), required=True)
    corridor = fields.Selection(
        CORRIDORS,
        string="Corredor",
        help="Por donde se sale hacia ahi. Viene sembrado, pero se puede "
             "corregir: si un ZIP quedo mal, se cambia aca y todas sus "
             "ordenes se reclasifican.",
    )

    _sql_constraints = [
        ("zip_uniq", "unique(zip)", "Ya existe un centroide para ese ZIP."),
    ]

    @api.constrains("latitude", "longitude")
    def _check_coords(self):
        for rec in self:
            if not (-90.0 <= rec.latitude <= 90.0):
                raise ValidationError(_("La latitud tiene que estar entre -90 y 90."))
            if not (-180.0 <= rec.longitude <= 180.0):
                raise ValidationError(_("La longitud tiene que estar entre -180 y 180."))

    @api.model
    def coords_for_zip(self, zipcode):
        """(lat, lon, exacto, corredor) del ZIP, o None si no se puede ubicar.

        `exacto` es False cuando se resolvio por el prefijo de 3 digitos en
        vez de por el ZIP completo. Eso pasa porque el censo publica ZCTA, no
        ZIPs: los de solo apartado postal y algunos especiales no existen como
        area. En produccion son pocos pero visibles -- 33336 (apartados de
        Fort Lauderdale), 33466 (Lake Worth), 33869 (Lake Placid).

        Sin este respaldo, una orden de Fort Lauderdale aparece "sin ubicar"
        cuando cualquiera sabe que esta 30 millas al norte, y eso hace que se
        deje de confiar en toda la pantalla. El prefijo cubre un area de
        condado: de sobra para meterla en un rango de 10 a 45 millas de ancho,
        y se marca como aproximada para no aparentar una precision que no tiene.
        """
        if not zipcode:
            return None
        code = str(zipcode).strip()
        rec = self.sudo().search([("zip", "=", code)], limit=1)
        if rec:
            return (rec.latitude, rec.longitude, True, rec.corridor)
        if len(code) < 3:
            return None
        near = self.sudo().search([("zip", "=like", code[:3] + "%")])
        if not near:
            return None
        # El corredor del prefijo solo se toma si TODOS coinciden: un condado
        # a caballo entre dos corredores no puede decidir por el que falta.
        corridors = set(near.mapped("corridor")) - {False}
        return (
            sum(near.mapped("latitude")) / len(near),
            sum(near.mapped("longitude")) / len(near),
            False,
            corridors.pop() if len(corridors) == 1 else False,
        )
