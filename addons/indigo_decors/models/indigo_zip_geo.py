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

# Rumbo -> punto cardinal, en 8 sectores de 45 grados.
#
# Ocho y no cuatro por un caso real: Pembroke Pines cae a 309 grados desde el
# taller. Con cuatro cuadrantes eso es "Oeste" por 6 grados de diferencia,
# cuando cualquiera en el taller diria "noroeste". Los bordes de cuadrante
# producen etiquetas que contradicen la intuicion, y una etiqueta en la que
# no se confia no sirve para planificar. Agrupar NO+N+NE como "el lado norte"
# es trivial; deshacer una etiqueta equivocada no lo es.
_COMPASS = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]

COMPASS_LABELS = {
    "N": "Norte",
    "NE": "Noreste",
    "E": "Este",
    "SE": "Sureste",
    "S": "Sur",
    "SO": "Suroeste",
    "O": "Oeste",
    "NO": "Noroeste",
}


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


def compass_from_bearing(bearing):
    """Rumbo en grados -> uno de los 8 puntos cardinales."""
    return _COMPASS[int(((bearing + 22.5) % 360) // 45)]


class IndigoZipGeo(models.Model):
    _name = "indigo.zip.geo"
    _description = "Centroide geografico de un ZIP"
    _order = "zip"
    _rec_name = "zip"

    zip = fields.Char(string="ZIP", required=True, index=True)
    latitude = fields.Float(string="Latitud", digits=(10, 6), required=True)
    longitude = fields.Float(string="Longitud", digits=(10, 6), required=True)

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
        """(lat, lon, exacto) del ZIP, o None si no hay forma de ubicarlo.

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
            return (rec.latitude, rec.longitude, True)
        if len(code) < 3:
            return None
        near = self.sudo().search([("zip", "=like", code[:3] + "%")])
        if not near:
            return None
        return (
            sum(near.mapped("latitude")) / len(near),
            sum(near.mapped("longitude")) / len(near),
            False,
        )
