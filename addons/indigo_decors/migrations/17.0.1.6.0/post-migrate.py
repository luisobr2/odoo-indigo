# -*- coding: utf-8 -*-
"""Registro de actividad (18-nov-2026): al activarlo, trae lo que ya guardo el
historial de las ordenes (cambios de campo, notas y adjuntos), para que la
pagina no arranque vacia. Lo posterior a este momento lo anota el registro en
vivo; la marca `audit_since` evita traerlo dos veces. Idempotente."""


def migrate(cr, version):
    from odoo import SUPERUSER_ID, api, fields

    env = api.Environment(cr, SUPERUSER_ID, {})
    icp = env["ir.config_parameter"]
    if not icp.get_param("indigo_decors.audit_since"):
        icp.set_param("indigo_decors.audit_since", fields.Datetime.to_string(fields.Datetime.now()))
    env["indigo.audit.log"]._audit_import_history()
