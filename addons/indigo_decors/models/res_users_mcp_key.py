# -*- coding: utf-8 -*-
"""Emision de claves API para el flujo OAuth del servidor MCP.

Por que existe este metodo
--------------------------
El panel necesita, al final de un login OAuth, dejarle al cliente (Claude
Desktop, Cowork) una credencial con la que llamar a Odoo despues. Esa
credencial tiene que ser una **clave API**, porque las 13 herramientas del MCP
llaman por ``execute_kw(uid, clave, ...)``.

Odoo ya sabe emitir claves API, pero solo por dos caminos que aqui no sirven:

* ``res.users.apikeys._generate(...)`` empieza por guion bajo, y Odoo **prohibe
  llamar por RPC a cualquier metodo que empiece asi**. Desde fuera no se llega.
* El asistente ``res.users.apikeys.description.make_key()`` esta decorado con
  ``@check_identity``, que exige una verificacion de identidad reciente hecha
  con el asistente ``res.users.identitycheck``. Reproducir ese baile por RPC es
  fragil y cambia entre versiones.

De ahi este metodo: publico, minimo y explicito.

Que NO es
---------
No es una escalada de privilegios. Emite una clave **solo para quien llama** —
``self.env.user``, nunca un usuario elegido por el que pide— y exactamente lo
mismo que esa persona ya puede hacer sola desde Ajustes -> Seguridad de la
cuenta -> Nueva clave API. Lo unico que aporta es poder hacerlo desde el flujo
OAuth en vez de a mano.

Quien llama ya viene autenticado: para llegar hasta aqui hubo que pasar por
``execute_kw`` con la contrasena correcta. Este metodo no autentica a nadie.
"""
import logging

from odoo import _, api, models
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)

# Todas las claves emitidas por este camino llevan el mismo prefijo en el
# nombre. Sirve para tres cosas: que en la lista de claves de Odoo se vea de
# donde salio cada una, que revocarlas en bloque sea un filtro y no una
# arqueologia, y que el metodo de revocar de abajo pueda distinguir una clave
# de MCP de una que la persona creo a mano para otra cosa.
MCP_KEY_PREFIX = "MCP OAuth"


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def indigo_mcp_issue_key(self, label=None):
        """Emite una clave API para el usuario autenticado y la devuelve.

        :param label: de donde viene la solicitud (nombre del cliente OAuth).
                      Solo decora el nombre de la clave, para que la persona
                      reconozca cual revocar.
        :return: la clave en claro. Odoo no la vuelve a mostrar nunca mas.
        """
        user = self.env.user

        # Los usuarios de portal (dealers, instaladores externos) no entran al
        # MCP. El servidor ya lo comprueba, pero esto es el cierre del lado de
        # Odoo: sin esto, un dealer con contrasena valida podria emitirse una
        # credencial de MCP aunque el servidor luego le negara las
        # herramientas.
        if user.share:
            raise AccessError(_("Esta cuenta no puede emitir claves de MCP."))

        clean = "".join(c for c in (label or "") if c.isalnum() or c in " -_.")[:40].strip()
        name = "%s - %s" % (MCP_KEY_PREFIX, clean) if clean else MCP_KEY_PREFIX

        # `_generate` toma el usuario de `self.env.user`, asi que corre a nombre
        # de quien llama. No se usa sudo() a proposito: la clave tiene que
        # pertenecer a esa persona y heredar sus permisos, no los de nadie mas.
        #
        # La firma cambio entre versiones (17 anadio expiration_date), asi que
        # se prueba la larga y se cae a la corta en vez de atarse a una.
        Keys = self.env["res.users.apikeys"]
        try:
            return Keys._generate("rpc", name, False)
        except TypeError:
            return Keys._generate("rpc", name)

    @api.model
    def indigo_mcp_revoke_key(self, key_id):
        """Revoca UNA clave de MCP del usuario autenticado.

        Por que hace falta un metodo
        ----------------------------
        Odoo deja que cualquiera LEA sus propias claves API, pero no que las
        borre: ``res.users.apikeys`` no da permiso de unlink a ningun grupo
        ("No group currently allows this operation"). Comprobado contra
        produccion antes de escribir esto.

        Sin este metodo, desconectar un cliente obliga a pedirselo a un
        administrador, que es justo el mensaje que la pantalla del asistente
        existe para evitar.

        Los dos limites que lo hacen seguro, y por que estan asi
        -------------------------------------------------------
        1. **Solo claves del que llama.** El filtro incluye
           ``user_id = self.env.user.id``, asi que un id ajeno no encuentra
           nada y devuelve False. No se comprueba despues de leer: se filtra
           al buscar, para que no exista una ventana en la que el registro
           ajeno este cargado.
        2. **Solo claves de MCP.** El nombre tiene que empezar por
           ``MCP OAuth``. Si no, esto seria un borrador universal de
           credenciales: la clave que alguien creo a mano para un script suyo
           no se toca desde aqui, porque nadie pidio eso.

        Se usa ``sudo()`` SOLO para el unlink, y despues de que el filtro ya
        acoto el conjunto a "mis claves de MCP". Es el patron correcto:
        elevar para la operacion que el ACL prohibe, nunca para la busqueda
        que decide sobre que se opera.

        :return: True si borro algo, False si no habia nada que borrar.
        """
        try:
            key_id = int(key_id)
        except (TypeError, ValueError):
            return False

        key = self.env["res.users.apikeys"].sudo().search([
            ("id", "=", key_id),
            ("user_id", "=", self.env.user.id),
            ("name", "=like", MCP_KEY_PREFIX + "%"),
        ], limit=1)
        if not key:
            return False

        # Queda en el log: una credencial que desaparece sin rastro es una
        # credencial que nadie puede auditar despues.
        _logger.info(
            "MCP: %s revoco su clave %r (id=%s)",
            self.env.user.login, key.name, key.id,
        )
        key.unlink()
        return True
