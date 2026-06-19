# -*- coding: utf-8 -*-
"""Team (internal user) management exposed to the Next.js admin panel.

The panel calls these methods as the logged-in user (an Indigo Manager).
Creating/editing res.users normally needs Odoo Settings-admin rights, which
managers don't have — so each method first verifies the caller is an Indigo
Manager (or system admin) and then performs the privileged work via sudo().
"""
from odoo import api, models, _
from odoo.exceptions import AccessError, ValidationError

# Role key -> the Indigo group XMLID that defines it. Order matters for
# detection (first match wins, most-privileged first).
ROLE_GROUP = [
    ("manager", "indigo_decors.group_indigo_manager"),
    ("office", "indigo_decors.group_indigo_office"),
    ("designer", "indigo_decors.group_indigo_designer"),
    ("cnc", "indigo_decors.group_indigo_cnc"),
    ("painter", "indigo_decors.group_indigo_painter_op"),
    ("installer", "indigo_decors.group_indigo_installer_internal"),
]
ROLE_LABEL = {
    "manager": "Manager",
    "office": "Office / Administration",
    "designer": "Designer",
    "cnc": "CNC / Router",
    "painter": "Painter",
    "installer": "Installer",
}


class ResUsers(models.Model):
    _inherit = "res.users"

    # ---- internal helpers -------------------------------------------------
    def _indigo_assert_manager(self):
        u = self.env.user
        if not (u._is_admin() or u.has_group("indigo_decors.group_indigo_manager")):
            raise AccessError(_("Only Indigo managers can manage team users."))

    @api.model
    def _indigo_protected_ids(self):
        """System users that must never be managed from the panel
        (OdooBot + the system administrator), to avoid owner lockout."""
        out = set()
        for xmlid in ("base.user_root", "base.user_admin"):
            u = self.env.ref(xmlid, raise_if_not_found=False)
            if u:
                out.add(u.id)
        return out

    def _indigo_guard_target(self):
        if self.id in self.env["res.users"]._indigo_protected_ids():
            raise AccessError(_("This system account can't be managed here."))

    @api.model
    def _indigo_role_group_ids(self):
        ids = {}
        for key, xmlid in ROLE_GROUP:
            g = self.env.ref(xmlid, raise_if_not_found=False)
            if g:
                ids[key] = g.id
        return ids

    def _indigo_role_of(self, role_ids):
        gids = set(self.groups_id.ids)
        for key, _xid in ROLE_GROUP:
            if role_ids.get(key) and role_ids[key] in gids:
                return key
        return ""

    # ---- API used by the panel -------------------------------------------
    @api.model
    def indigo_team_list(self):
        """Return all internal team users with their Indigo role."""
        self._indigo_assert_manager()
        role_ids = self._indigo_role_group_ids()
        protected = list(self._indigo_protected_ids())
        users = self.with_context(active_test=False).sudo().search(
            [("share", "=", False), ("id", "not in", protected)], order="active desc, name"
        )
        out = []
        for u in users:
            role = u._indigo_role_of(role_ids)
            out.append({
                "id": u.id,
                "name": u.name or "",
                "login": u.login or "",
                "email": u.email or u.login or "",
                "active": bool(u.active),
                "role": role,
                "role_label": ROLE_LABEL.get(role, "—"),
            })
        return out

    @api.model
    def indigo_team_create(self, vals):
        """Create a team user and assign the chosen role group.
        vals: {name, login(email), password, role}"""
        self._indigo_assert_manager()
        name = (vals.get("name") or "").strip()
        login = (vals.get("login") or "").strip()
        password = (vals.get("password") or "").strip()
        role = (vals.get("role") or "").strip()
        if not name or not login:
            raise ValidationError(_("Name and email are required."))
        role_ids = self._indigo_role_group_ids()
        if role not in role_ids:
            raise ValidationError(_("Pick a valid role."))
        if self.with_context(active_test=False).sudo().search_count([("login", "=", login)]):
            raise ValidationError(_("A user with that email already exists."))
        Sudo = self.sudo()
        user = Sudo.create({
            "name": name,
            "login": login,
            "email": login,
            "password": password or None,
            "groups_id": [(4, role_ids[role])],
        })
        return {"id": user.id}

    @api.model
    def indigo_team_update(self, user_id, vals):
        """Update name/email/role of a team user."""
        self._indigo_assert_manager()
        user = self.with_context(active_test=False).sudo().browse(int(user_id))
        if not user.exists():
            raise ValidationError(_("User not found."))
        user._indigo_guard_target()
        write_vals = {}
        if "name" in vals and (vals.get("name") or "").strip():
            write_vals["name"] = vals["name"].strip()
        if "email" in vals and (vals.get("email") or "").strip():
            write_vals["email"] = vals["email"].strip()
        if write_vals:
            user.write(write_vals)
        # Role change: drop all Indigo role groups, add the selected one.
        if vals.get("role"):
            role_ids = self._indigo_role_group_ids()
            if vals["role"] not in role_ids:
                raise ValidationError(_("Pick a valid role."))
            cmds = [(3, gid) for gid in role_ids.values()]
            cmds.append((4, role_ids[vals["role"]]))
            user.write({"groups_id": cmds})
        return {"ok": True}

    @api.model
    def indigo_team_set_active(self, user_id, active):
        """Archive (deactivate) or restore a team user."""
        self._indigo_assert_manager()
        user = self.with_context(active_test=False).sudo().browse(int(user_id))
        if not user.exists():
            raise ValidationError(_("User not found."))
        user._indigo_guard_target()
        if user.id == self.env.user.id and not active:
            raise ValidationError(_("You can't deactivate your own account."))
        user.write({"active": bool(active)})
        return {"ok": True}

    @api.model
    def indigo_team_reset_password(self, user_id, password):
        """Set a new password for a team user."""
        self._indigo_assert_manager()
        password = (password or "").strip()
        if len(password) < 6:
            raise ValidationError(_("Password must be at least 6 characters."))
        user = self.with_context(active_test=False).sudo().browse(int(user_id))
        if not user.exists():
            raise ValidationError(_("User not found."))
        user._indigo_guard_target()
        user.write({"password": password})
        return {"ok": True}
