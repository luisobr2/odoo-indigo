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
from odoo import _, api, models
from odoo.exceptions import AccessError

# Todas las claves emitidas por este camino llevan el mismo prefijo en el
# nombre. Sirve para dos cosas: que en la lista de claves de Odoo se vea de
# donde salio cada una, y que revocarlas en bloque sea un filtro y no una
# arqueologia.
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
