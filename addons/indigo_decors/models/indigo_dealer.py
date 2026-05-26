# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_indigo_dealer = fields.Boolean(string="Es dealer Indigo")
    indigo_dealer_code = fields.Char(string="Codigo de dealer")
    indigo_default_price_per_sqf = fields.Float(
        string="Precio por defecto por SQF",
        help="Precio que se cobra al dealer por SQF (puede sobrescribirse por orden).",
    )
    indigo_optional_stage_ids = fields.Many2many(
        "indigo.stage",
        "indigo_dealer_stage_rel",
        "partner_id",
        "stage_id",
        string="Etapas opcionales activas",
        domain=[("is_optional", "=", True)],
        help="Etapas opcionales (2-5: confirmacion/medicion) que aplican para este dealer.",
    )

    def action_indigo_create_portal_user(self):
        """Crea un usuario portal para este partner (dealer o contratista)."""
        from odoo.exceptions import UserError
        self.ensure_one()
        if not self.email:
            raise UserError("El contacto necesita un email para crear acceso portal.")
        User = self.env["res.users"]
        existing = User.search([("login", "=", self.email)], limit=1)
        if existing:
            raise UserError("Ya existe un usuario con login %s." % self.email)
        portal = self.env.ref("base.group_portal")
        user = User.with_context(no_reset_password=True).create({
            "name": self.name,
            "login": self.email,
            "partner_id": self.id,
            "groups_id": [(6, 0, [portal.id])],
        })
        # Disparar reset de password (envia email — en dev sera capturado por MailHog)
        user.action_reset_password()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": "Usuario portal %s creado. Se envio email para fijar password." % user.login,
                "type": "success",
                "sticky": False,
            },
        }
