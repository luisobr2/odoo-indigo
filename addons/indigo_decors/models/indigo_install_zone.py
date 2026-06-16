# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models


class IndigoInstallZone(models.Model):
    """Distance-based installation fee by ZIP code.

    The workshop charges an "outrange installation fee" that grows with the
    distance from Miami. Instead of hardcoding the ZIP -> fee map, admins
    edit zones here (Indigo -> Config -> Install Zones): each zone has a fee
    and a free-form list of ZIP codes. An order's installation_fee is the fee
    of the first zone whose list contains the order's ZIP (0 if none match).
    """

    _name = "indigo.install.zone"
    _description = "Installation fee zone (by ZIP)"
    _order = "sequence, fee"

    name = fields.Char(string="Zone", required=True, translate=True)
    sequence = fields.Integer(default=10)
    fee = fields.Float(string="Installation fee (USD)", digits=(10, 2))
    zip_codes = fields.Text(
        string="ZIP codes",
        help="ZIP codes in this zone. Separate by comma, space or newline.",
    )
    zip_count = fields.Integer(
        string="# ZIPs", compute="_compute_zip_count"
    )
    active = fields.Boolean(default=True)

    @api.depends("zip_codes")
    def _compute_zip_count(self):
        for z in self:
            z.zip_count = len(z._zip_set())

    def _zip_set(self):
        """Parsed set of 5-digit ZIPs for this zone."""
        self.ensure_one()
        return set(re.findall(r"\d{5}", self.zip_codes or ""))

    @api.model
    def fee_for_zip(self, zipcode):
        """Return (fee, zone_name) for a ZIP, or (0.0, '') if no zone matches.

        Empty/unknown ZIP -> local (no fee), matching "Zona 0".
        """
        digits = re.search(r"\d{5}", zipcode or "")
        if not digits:
            return 0.0, ""
        z = digits.group(0)
        for zone in self.search([]):
            if z in zone._zip_set():
                return zone.fee, zone.name
        return 0.0, ""
