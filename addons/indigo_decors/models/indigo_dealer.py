# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_indigo_dealer = fields.Boolean(string="Es dealer Indigo")
    indigo_dealer_code = fields.Char(string="Codigo de dealer")
    indigo_default_price_per_sqf = fields.Float(
        string="Precio por defecto por SQF",
        help="Precio que se cobra al dealer por SQF (puede sobrescribirse por orden).",
    )
    indigo_charge_install_fee = fields.Boolean(
        string="Charge installation fee",
        default=True,
        help="When off, the distance-based installation fee is NOT added to "
             "this dealer's order totals (e.g. dealers that install themselves "
             "or B2C). On by default.",
    )
    indigo_dealer_logo = fields.Image(
        string="Dealer logo",
        max_width=512,
        max_height=512,
        help="Square logo (PNG with transparent background preferred). "
             "Shown next to the dealer name on the Dashboard's "
             "'Orders by Company' card and on the order detail header.",
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
    indigo_is_demo_data = fields.Boolean(
        string="Data demo (reemplazar)",
        compute="_compute_indigo_is_demo_data",
        store=False,
        help="True cuando este dealer es de seed/demo (email con .example o phone vacio). "
             "Indica que hay que reemplazar con datos reales antes de go-live.",
    )

    @api.depends("email", "phone", "street")
    def _compute_indigo_is_demo_data(self):
        for p in self:
            email = (p.email or "").lower()
            is_demo = (
                ".example" in email
                or "@example." in email
                or email.endswith(".test")
                or (p.is_indigo_dealer and p.indigo_dealer_code != "DIRECT" and not p.street)
            )
            p.indigo_is_demo_data = is_demo

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
