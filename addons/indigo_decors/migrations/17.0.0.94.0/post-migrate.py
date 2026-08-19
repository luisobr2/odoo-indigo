# -*- coding: utf-8 -*-
"""Recalcula la geo tras cambiar los 8 rumbos por los 5 corredores.

`install_corridor` sale del ZIP, y el compute depende solo de `client_zip`,
que no cambio. Sin este recalculo las ordenes quedarian con el campo vacio y
la pantalla de zonas se veria entera "sin corredor".
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    count = env["indigo.order"].indigo_recompute_install_geo()
    _logger.info("indigo_decors: corredores recalculados en %s ordenes", count)
