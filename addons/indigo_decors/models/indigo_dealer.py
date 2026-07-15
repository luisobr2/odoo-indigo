# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError, UserError


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

    def write(self, vals):
        res = super().write(vals)
        # Keep a dealer's portal LOGIN in sync with their email. The portal user
        # is created with login = email, but if office later edits the email the
        # two silently diverge and the dealer can't log in with the new address.
        # Only touches portal (share) users of Indigo dealers; never internal or
        # protected accounts, and never steals a login already used elsewhere.
        if vals.get("email"):
            Users = self.env["res.users"].sudo().with_context(active_test=False)
            protected = set(Users._indigo_protected_ids())
            for partner in self:
                if not partner.is_indigo_dealer or not partner.email:
                    continue
                user = Users.search([("partner_id", "=", partner.id)], limit=1)
                if (
                    not user
                    or not user.share
                    or user.id in protected
                    or user.login == partner.email
                ):
                    continue
                clash = Users.search(
                    [("login", "=", partner.email), ("id", "!=", user.id)], limit=1
                )
                if clash:
                    continue
                user.write({"login": partner.email})
        return res

    def action_indigo_create_portal_user(self):
        """Crea un usuario portal para este partner (dealer o contratista)."""
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

    # ---- Dealer portal access (called from the Next.js admin) ------------
    def _indigo_assert_dealer_admin(self):
        u = self.env.user
        if not (
            u._is_admin()
            or u.has_group("indigo_decors.group_indigo_manager")
            or u.has_group("indigo_decors.group_indigo_office")
        ):
            raise AccessError(
                _("Only Indigo managers or office can manage dealer access.")
            )

    @api.model
    def indigo_dealer_portal_info(self, partner_id):
        """Portal-access status for a dealer partner (for the Next.js admin)."""
        self._indigo_assert_dealer_admin()
        partner = self.sudo().browse(int(partner_id))
        if not partner.exists():
            raise ValidationError(_("Dealer not found."))
        if not partner.is_indigo_dealer:
            raise ValidationError(_("Portal access is only managed for dealer contacts."))
        user = (
            self.env["res.users"]
            .sudo()
            .with_context(active_test=False)
            .search([("partner_id", "=", partner.id)], limit=1)
        )
        return {
            "has_user": bool(user),
            "login": user.login if user else False,
            "active": bool(user.active) if user else False,
        }

    @api.model
    def indigo_dealer_set_password(self, partner_id, password):
        """Create the dealer's portal user if missing, then set its password."""
        self._indigo_assert_dealer_admin()
        password = (password or "").strip()
        if len(password) < 6:
            raise ValidationError(_("Password must be at least 6 characters."))
        partner = self.sudo().browse(int(partner_id))
        if not partner.exists():
            raise ValidationError(_("Dealer not found."))
        if not partner.is_indigo_dealer:
            raise ValidationError(_("Portal access is only managed for dealer contacts."))
        if not partner.email:
            raise ValidationError(
                _("The dealer needs an email before portal access can be created.")
            )
        Users = self.env["res.users"].sudo().with_context(active_test=False)
        user = Users.search([("partner_id", "=", partner.id)], limit=1)
        created = False
        if not user:
            clash = Users.search([("login", "=", partner.email)], limit=1)
            if clash:
                raise ValidationError(
                    _("A different user already exists with login %s.") % partner.email
                )
            portal = self.env.ref("base.group_portal")
            user = Users.with_context(no_reset_password=True).create({
                "name": partner.name,
                "login": partner.email,
                "partner_id": partner.id,
                "groups_id": [(6, 0, [portal.id])],
            })
            created = True
        else:
            # Defense in depth: never reset a protected/system account or an
            # internal (non-portal) user through the dealer endpoint. `share`
            # is True only for portal/public users; internal users are False.
            if user.id in Users._indigo_protected_ids() or not user.share:
                raise ValidationError(
                    _("This dealer is linked to a non-portal user; its password can't be set here.")
                )
        user.write({"password": password, "active": True})
        return {"ok": True, "login": user.login, "created": created}
