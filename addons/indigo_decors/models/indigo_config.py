# -*- coding: utf-8 -*-
"""Capacity settings exposed to the panel without granting managers full
access to ir.config_parameter (which also holds secrets like the SMTP
password). Only the three Indigo capacity keys are read/written, via sudo,
gated to managers/office."""
from odoo import api, models, _
from odoo.exceptions import AccessError

CAP_KEYS = {
    "cnc": "indigo_decors.capacity.cnc_per_day",
    "painting": "indigo_decors.capacity.painting_sqf_per_day",
    "install": "indigo_decors.capacity.installations_per_day",
}


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
