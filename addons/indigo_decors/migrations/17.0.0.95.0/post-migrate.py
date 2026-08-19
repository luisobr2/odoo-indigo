# -*- coding: utf-8 -*-
"""Re-deriva el ZIP de cada orden desde su direccion, y reclasifica.

Hace falta por el bug de _zip_from_address que se corrige en esta version:
exigia limite de palabra, asi que una direccion escrita "...FL33028" (estado
pegado al codigo, cosa comun) no exponia el ZIP y el parser terminaba
guardando el NUMERO DE LA CALLE. En produccion eso dejo a IND/2026/00078 con
un ZIP de Pennsylvania y sin corredor.

Se corren las dos cosas en orden: primero el ZIP, despues la geo que depende
de el.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    Order = env["indigo.order"]
    cambios = Order.indigo_backfill_client_zip()
    for name, antes, ahora in cambios:
        _logger.info("indigo_decors: ZIP de %s corregido %s -> %s", name, antes, ahora)
    _logger.info("indigo_decors: %s ZIP corregidos desde la direccion", len(cambios))
    _logger.info("indigo_decors: geo recalculada en %s ordenes",
                 Order.indigo_recompute_install_geo())
