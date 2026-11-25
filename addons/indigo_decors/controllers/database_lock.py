# -*- coding: utf-8 -*-
"""Gestion de bases de datos cerrada desde internet (25-nov-2026).

Odoo trae un gestor de bases (`/web/database/*` y el servicio RPC `db`) que,
con la contrasena maestra, permite descargar, restaurar, duplicar o BORRAR la
base desde cualquier navegador. `list_db = False` solo oculta el selector: las
rutas seguian respondiendo. Y la contrasena maestra estuvo publicada en este
repo.

Indigo no usa nada de eso: las copias se hacen con `pg_dump` dentro del
servidor (docs/DEPLOY.md). Asi que se cierra todo:
- las rutas HTTP del gestor responden 404;
- por RPC solo pasan las consultas inofensivas (version, si existe la base,
  idiomas, paises).
"""
import logging

import odoo
from odoo import http
from odoo.addons.web.controllers.database import Database
from odoo.exceptions import AccessDenied
from werkzeug.exceptions import NotFound

_logger = logging.getLogger(__name__)

# Lo que el servicio `db` sigue contestando: nada de esto pide la contrasena
# maestra ni toca datos.
DB_RPC_ALLOWED = frozenset({"db_exist", "list", "list_lang", "list_countries", "server_version"})


class IndigoDatabaseLock(Database):
    """Las rutas del gestor existen, pero no hacen nada: 404."""

    @http.route()
    def selector(self, **kw):
        raise NotFound()

    @http.route()
    def manager(self, **kw):
        raise NotFound()

    @http.route()
    def create(self, **kw):
        raise NotFound()

    @http.route()
    def duplicate(self, **kw):
        raise NotFound()

    @http.route()
    def drop(self, **kw):
        raise NotFound()

    @http.route()
    def backup(self, **kw):
        raise NotFound()

    @http.route()
    def restore(self, **kw):
        raise NotFound()

    @http.route()
    def change_password(self, **kw):
        raise NotFound()


def _lock_db_rpc():
    original = odoo.service.db.dispatch
    if getattr(original, "_indigo_locked", False):
        return

    def dispatch(method, params):
        if method not in DB_RPC_ALLOWED:
            _logger.warning("Blocked database operation over RPC: db.%s", method)
            raise AccessDenied()
        return original(method, params)

    dispatch._indigo_locked = True
    # odoo.http.dispatch_rpc busca odoo.service.db.dispatch en cada llamada,
    # asi que reemplazarlo aqui basta para todo el proceso.
    odoo.service.db.dispatch = dispatch


_lock_db_rpc()
