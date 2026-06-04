# -*- coding: utf-8 -*-
"""Migration script — Indigo Decors v0.35.0 (role lockdown + installer portal).

What this script does to a fresh-from-master prod database:
  1. Creates the new role groups (group_indigo_installer_internal already
     comes from the module XML; this only adds users to it).
  2. Converts Carlos (instalador@indigodecors.com) to a portal user so he
     lands on /my/installs after login.
  3. Adds Pedro (disenador@), Mario (pintor@), Ramon (cnc@ — created if
     missing), Beatriz (oficina@ — created if missing) to their role groups.
  4. Removes the catch-all groups (Sales, Mail Template Editor,
     Technical Features) that the default user template attached, so
     scoped users only see Indigo.

How to run against prod:

    docker exec <db-container> psql -U odoo -d indigo-prod < scripts/migrate_to_v0.35.sql

OR via odoo shell:

    docker exec <odoo-container> odoo shell -c /etc/odoo/odoo.conf -d indigo-prod
    >>> exec(open('/path/to/migrate_to_v0.35.py').read())

This script is IDEMPOTENT — running twice is a no-op. It checks before
each insert/update.

After running:
  - All passwords stay UNCHANGED (we only touch group membership +
    user share flag). Users keep whatever password they had in prod.
  - The new Dashboard menu auto-appears for manager + office users.

ROLLBACK:
  - To make Carlos an internal user again, run the inverse SQL at the end
    of this file (commented out).
"""
import logging
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

_logger = logging.getLogger(__name__)


def migrate(env):
    Users = env["res.users"]
    Groups = env["res.groups"]

    # --- helpers ---
    def grp(xmlid):
        return env.ref(xmlid, raise_if_not_found=False)

    def user_by_login(login):
        return Users.search([("login", "=", login)], limit=1)

    g_user = grp("indigo_decors.group_indigo_user")
    g_manager = grp("indigo_decors.group_indigo_manager")
    g_office = grp("indigo_decors.group_indigo_office")
    g_designer = grp("indigo_decors.group_indigo_designer")
    g_cnc = grp("indigo_decors.group_indigo_cnc")
    g_painter = grp("indigo_decors.group_indigo_painter_op")
    g_installer_internal = grp("indigo_decors.group_indigo_installer_internal")
    g_contractor = grp("indigo_decors.group_indigo_contractor")
    g_portal = grp("base.group_portal")
    g_internal = grp("base.group_user")

    # Categories of "extra" groups to strip from scoped users so they only
    # see Indigo. By group XML id.
    NOISE_XMLIDS = [
        "base.group_no_one",                   # Technical Features
        "mail.group_mail_template_editor",     # Mail Template Editor
        "sales_team.group_sale_salesman",      # Sales User: Own Documents Only
        "sales_team.group_sale_salesman_all_leads",  # Sales User: All Documents
        "base.group_partner_manager",          # Contact Creation
    ]

    def strip_noise(user):
        """Remove the noisy default groups from a scoped user."""
        for xmlid in NOISE_XMLIDS:
            g = grp(xmlid)
            if g and g in user.groups_id:
                user.write({"groups_id": [(3, g.id)]})

    # ---------------------------------------------------------------
    # 1. Pedro Disenador -> Designer
    # ---------------------------------------------------------------
    u = user_by_login("disenador@indigodecors.com")
    if u and g_designer and g_designer not in u.groups_id:
        u.write({"groups_id": [(4, g_designer.id)]})
        strip_noise(u)
        _logger.info("Migrated %s -> Designer", u.login)

    # ---------------------------------------------------------------
    # 2. Mario Pintor -> Painter
    # ---------------------------------------------------------------
    u = user_by_login("pintor@indigodecors.com")
    if u and g_painter and g_painter not in u.groups_id:
        u.write({"groups_id": [(4, g_painter.id)]})
        strip_noise(u)
        _logger.info("Migrated %s -> Painter", u.login)

    # ---------------------------------------------------------------
    # 3. Carlos Instalador -> Portal + Contractor (NOT internal anymore)
    # ---------------------------------------------------------------
    u = user_by_login("instalador@indigodecors.com")
    if u and g_contractor and not u.share:
        # Remove internal-user groups
        for g in (g_user, g_manager, g_office, g_designer, g_cnc,
                  g_painter, g_installer_internal, g_internal):
            if g and g in u.groups_id:
                u.write({"groups_id": [(3, g.id)]})
        strip_noise(u)
        # Add portal + contractor
        u.write({"groups_id": [(4, g_portal.id), (4, g_contractor.id)]})
        u.write({"share": True})
        _logger.info("Converted %s to PORTAL user (Contractor)", u.login)

    # ---------------------------------------------------------------
    # 4. Ramon CNC operator — create if missing, then assign group
    # ---------------------------------------------------------------
    u = user_by_login("cnc@indigodecors.com")
    if not u:
        u = Users.create({
            "login": "cnc@indigodecors.com",
            "name": "Ramon CNC",
            "email": "cnc@indigodecors.com",
            "tz": "America/New_York",
            "lang": "es_ES",
            "groups_id": [(6, 0, [g_cnc.id])] if g_cnc else False,
        })
        _logger.info("Created CNC user: %s", u.login)
    elif g_cnc and g_cnc not in u.groups_id:
        u.write({"groups_id": [(4, g_cnc.id)]})
    strip_noise(u)

    # ---------------------------------------------------------------
    # 5. Beatriz Oficina — create if missing, then assign group
    # ---------------------------------------------------------------
    u = user_by_login("oficina@indigodecors.com")
    if not u:
        u = Users.create({
            "login": "oficina@indigodecors.com",
            "name": "Beatriz Oficina",
            "email": "oficina@indigodecors.com",
            "tz": "America/New_York",
            "lang": "es_ES",
            "groups_id": [(6, 0, [g_office.id])] if g_office else False,
        })
        _logger.info("Created Office user: %s", u.login)
    elif g_office and g_office not in u.groups_id:
        u.write({"groups_id": [(4, g_office.id)]})
    strip_noise(u)

    # ---------------------------------------------------------------
    # 6. Make sure Javier is a manager (admin total per requirement)
    # ---------------------------------------------------------------
    u = user_by_login("javier@indigodecors.com")
    if u and g_manager and g_manager not in u.groups_id:
        # Clone Luis's groups (simplest way to grant full admin)
        luis = user_by_login("lbencomo94@gmail.com")
        if luis:
            u.write({"groups_id": [(4, g.id) for g in luis.groups_id]})
            _logger.info("Made %s a Manager (cloned Luis's groups)", u.login)


def main(env):
    migrate(env)


# Allow execution via odoo shell: just paste the file in shell or call main(env)
if __name__ == "__main__":
    # Convenience: if run as `python migrate.py` outside odoo shell, try to
    # bootstrap an env from the running container's config.
    import sys
    try:
        import odoo
        odoo.tools.config.parse_config(["-c", "/etc/odoo/odoo.conf"])
        reg = Registry("indigo-prod")
        with reg.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            main(env)
            cr.commit()
        print("Migration applied.")
    except Exception as e:
        print("Run inside odoo shell: docker exec <c> odoo shell -d indigo-prod < this_file")
        print("Or paste the contents and call main(env).")
        sys.exit(1)


# ----------------------------------------------------------------------
# ROLLBACK (commented). Run if you need to revert Carlos to internal user.
# ----------------------------------------------------------------------
# u = env['res.users'].search([('login','=','instalador@indigodecors.com')])
# u.write({'share': False, 'groups_id': [(4, env.ref('base.group_user').id),
#                                          (4, env.ref('indigo_decors.group_indigo_installer_internal').id),
#                                          (3, env.ref('base.group_portal').id),
#                                          (3, env.ref('indigo_decors.group_indigo_contractor').id)]})
