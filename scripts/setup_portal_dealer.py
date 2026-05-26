# -*- coding: utf-8 -*-
"""Crear portal user para Lock Tight (dealer demo)."""
env = env  # noqa

# Usar el dealer del demo data (xmlid) — el otro Lock Tight sin xmlid lo ignoramos
dealer = env.ref("indigo_decors.dealer_lock_tight")
if not dealer.email:
    dealer.email = "ops@locktight.example"

User = env["res.users"]
group_portal = env.ref("base.group_portal")
existing = User.search([("login", "=", dealer.email)], limit=1)
if not existing:
    user = User.with_context(no_reset_password=True).create({
        "name": dealer.name + " (Dealer)",
        "login": dealer.email,
        "partner_id": dealer.id,
        "groups_id": [(6, 0, [group_portal.id])],
        "password": "DealerDemo2026!",
    })
    print("CREATED dealer user id=", user.id, "login=", user.login)
else:
    existing.write({"password": "DealerDemo2026!"})
    print("UPDATED dealer user id=", existing.id)

env.cr.commit()
