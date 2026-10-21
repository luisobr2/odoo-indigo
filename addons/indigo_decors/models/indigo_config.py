# -*- coding: utf-8 -*-
"""Capacity settings exposed to the panel without granting managers full
access to ir.config_parameter (which also holds secrets like the SMTP
password). Only the three Indigo capacity keys are read/written, via sudo,
gated to managers/office."""
import re

from odoo import api, models, _
from odoo.exceptions import AccessError, ValidationError

CAP_KEYS = {
    "cnc": "indigo_decors.capacity.cnc_per_day",
    "painting": "indigo_decors.capacity.painting_sqf_per_day",
    "install": "indigo_decors.capacity.installations_per_day",
}

#: Interruptor de los avisos automaticos al dealer. Apagado por defecto a
#: proposito: encender solo el modulo no debe empezar a mandar correo a
#: clientes reales sin que alguien lo decida.
NOTIFY_KEY = "indigo_decors.notify_client_on_stage"

#: Notas del equipo con Anota (widget de feedback visual, 21-oct-2026). Apagado
#: por defecto; la clave del proyecto (pk_...) es publica: va en el HTML.
ANOTA_ENABLED_KEY = "indigo_decors.anota_enabled"
ANOTA_PROJECT_KEY = "indigo_decors.anota_project_key"
ANOTA_URL_KEY = "indigo_decors.anota_url"
ANOTA_DEFAULT_URL = "https://anota.lbencomo94.workers.dev"
_ANOTA_PK = re.compile(r"^pk_[A-Za-z0-9_-]{8,64}$")


class IrConfigParameter(models.Model):
    _inherit = "ir.config_parameter"

    @api.model
    def _indigo_assert_settings(self):
        u = self.env.user
        if not (
            u._is_admin()
            or u.has_group("indigo_decors.group_indigo_manager")
            or u.has_group("indigo_decors.group_indigo_office")
        ):
            raise AccessError(_("Only Indigo managers can manage settings."))

    @api.model
    def indigo_get_capacities(self):
        """Return the 3 capacity params as raw strings ('' if unset)."""
        self._indigo_assert_settings()
        Sudo = self.sudo()
        return {k: (Sudo.get_param(key, "") or "") for k, key in CAP_KEYS.items()}

    @api.model
    def indigo_set_capacities(self, vals):
        """Persist the capacity params. vals: {cnc, painting, install}."""
        self._indigo_assert_settings()
        Sudo = self.sudo()
        for k, key in CAP_KEYS.items():
            if k in vals and vals[k] not in (None, ""):
                Sudo.set_param(key, str(vals[k]))
        return {"ok": True}

    # ------------------------------------------------------------------
    # Avisos automaticos al dealer
    # ------------------------------------------------------------------

    @api.model
    def indigo_notify_on_stage_enabled(self):
        """Si los avisos automaticos por hito estan encendidos.

        Sin gate de permisos y con sudo: lo llama el propio `write()` de la
        orden, que puede ejecutarse como cualquiera que mueva una orden
        (un pintor, un instalador). Solo lee un booleano, no expone nada.
        """
        return (self.sudo().get_param(NOTIFY_KEY, "") or "").strip() == "1"

    @api.model
    def indigo_get_notify_settings(self):
        self._indigo_assert_settings()
        return {"notify_client_on_stage": self.indigo_notify_on_stage_enabled()}

    @api.model
    def indigo_set_notify_settings(self, vals):
        """Enciende o apaga los avisos automaticos. vals: {notify_client_on_stage}."""
        self._indigo_assert_settings()
        if "notify_client_on_stage" in vals:
            self.sudo().set_param(
                NOTIFY_KEY, "1" if vals["notify_client_on_stage"] else "0"
            )
        return {"ok": True}

    # ------------------------------------------------------------------
    # Notas del equipo (Anota)
    # ------------------------------------------------------------------

    def _indigo_anota(self):
        Sudo = self.sudo()
        key = (Sudo.get_param(ANOTA_PROJECT_KEY, "") or "").strip()
        return {
            "enabled": (Sudo.get_param(ANOTA_ENABLED_KEY, "") or "").strip() == "1",
            "project_key": key or False,
            "url": (Sudo.get_param(ANOTA_URL_KEY, "") or "").strip() or ANOTA_DEFAULT_URL,
        }

    @api.model
    def indigo_get_anota(self):
        """Lo que el panel necesita para cargar el widget. Lo lee cualquier
        usuario interno (no hay nada secreto: la clave pk_ va en la pagina);
        a un usuario del portal (dealer) se le dice que esta apagado."""
        if self.env.user.share:
            return {"enabled": False, "project_key": False, "url": ANOTA_DEFAULT_URL}
        return self._indigo_anota()

    @api.model
    def indigo_set_anota(self, vals):
        """vals: enabled (bool), project_key (pk_...). Gerencia u oficina."""
        self._indigo_assert_settings()
        vals = vals or {}
        Sudo = self.sudo()
        if "project_key" in vals:
            key = (vals.get("project_key") or "").strip()
            if key and not _ANOTA_PK.match(key):
                raise ValidationError(_("The Anota project key looks like pk_ followed by letters and numbers."))
            Sudo.set_param(ANOTA_PROJECT_KEY, key)
        if "enabled" in vals:
            if vals["enabled"] and not (Sudo.get_param(ANOTA_PROJECT_KEY, "") or "").strip():
                raise ValidationError(_("Add the Anota project key before turning team notes on."))
            Sudo.set_param(ANOTA_ENABLED_KEY, "1" if vals["enabled"] else "0")
        return self._indigo_anota()
