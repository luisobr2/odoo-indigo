# -*- coding: utf-8 -*-
"""Recalcula la geo de instalacion despues de cargar los datos.

Hace falta por un tema de orden que no es evidente: Odoo crea las columnas y
calcula los campos `store=True` ANTES de cargar los archivos de datos del
modulo. La primera vez, `_compute_install_geo` corrio con la tabla
`indigo.zip.geo` todavia vacia, asi que las 249 ordenes de produccion
quedaron sin distancia ni rango -- y como el compute depende solo de
`client_zip`, que no cambio, nada las volvia a tocar.

Los scripts post-migrate corren DESPUES de los datos, que es el momento
correcto. La contraparte para instalaciones nuevas es el `post_init_hook`
del __init__.py del modulo.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    count = env["indigo.order"].indigo_recompute_install_geo()
    ubicadas = env["indigo.order"].with_context(active_test=False).search_count(
        [("install_range_id", "!=", False)]
    )
    _logger.info(
        "indigo_decors: geo de instalacion recalculada en %s ordenes (%s ubicadas)",
        count, ubicadas,
    )
