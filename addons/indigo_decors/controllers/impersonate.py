# -*- coding: utf-8 -*-
"""Password-less "View as" (impersonation) for Indigo managers.

A manager (or system admin) can preview the app as another internal team
member WITHOUT knowing their password. We verify the caller is an Indigo
Manager, then mint a fresh Odoo session bound to the target user and return
its session id. The caller's own session is untouched — the Next BFF stashes
it so it can be restored when leaving impersonation.

Security:
  - Only Indigo Managers / system admins may call this.
  - The target must be an active internal user (share=False).
  - System accounts (admin/OdooBot/template) can never be impersonated, so a
    manager can't escalate into the system administrator.
"""
import logging

from odoo import http
from odoo.http import request, root

_logger = logging.getLogger(__name__)


class IndigoImpersonate(http.Controller):

    @http.route(
        "/indigo/impersonate", type="json", auth="user", methods=["POST"], csrf=False
    )
    def impersonate(self, login=None, **kw):
        caller = request.env.user
        if not (caller._is_admin() or caller.has_group("indigo_decors.group_indigo_manager")):
            return {"error": "Only Indigo managers can use View as."}
        if not login:
            return {"error": "login required"}

        Users = request.env["res.users"]
        protected = Users._indigo_protected_ids() if hasattr(Users, "_indigo_protected_ids") else set()
        target = Users.sudo().search(
            [("login", "=", login), ("active", "=", True), ("share", "=", False)], limit=1
        )
        if not target or target.id in protected:
            return {"error": "User not available for View as."}

        # Mint a new session bound to the target user (mirrors what
        # Session.authenticate does, minus the password check).
        sess = root.session_store.new()
        sess.db = request.session.db
        sess.uid = target.id
        sess.login = target.login
        sess.session_token = target._compute_session_token(sess.sid)
        try:
            sess.context = dict(target.with_user(target.id).context_get())
        except Exception:  # noqa: BLE001
            sess.context = {}
        root.session_store.save(sess)

        groups = target.groups_id.mapped(lambda g: g.full_name or g.name)
        _logger.info(
            "View as: %s (%s) impersonating %s (%s)",
            caller.login, caller.id, target.login, target.id,
        )
        return {
            "session_id": sess.sid,
            "uid": target.id,
            "login": target.login,
            "name": target.name,
            "partner_id": target.partner_id.id,
            "is_admin": target._is_admin(),
            "groups": groups,
        }
