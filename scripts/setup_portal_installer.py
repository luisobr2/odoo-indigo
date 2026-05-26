# -*- coding: utf-8 -*-
"""Crear usuario portal para un instalador y devolver credenciales."""
env = env  # noqa

javier = env["res.partner"].search([("name", "=", "Javier Instalador")], limit=1)
if not javier:
    raise SystemExit("No existe el partner Javier Instalador")

# Asegurar email
if not javier.email:
    javier.email = "javier@indigodecors.local"

User = env["res.users"]
existing = User.search([("login", "=", javier.email)], limit=1)
group_portal = env.ref("base.group_portal")

if not existing:
    user = User.with_context(no_reset_password=True).create({
        "name": javier.name,
        "login": javier.email,
        "partner_id": javier.id,
        "groups_id": [(6, 0, [group_portal.id])],
        "password": "PortalDemo2026!",
    })
    env.cr.commit()
    print("CREATED user_id=", user.id, "login=", user.login)
else:
    existing.write({"password": "PortalDemo2026!"})
    env.cr.commit()
    print("UPDATED user_id=", existing.id, "login=", existing.login)

# Tambien resetear la orden a etapa "Ready for Installation" para poder marcarla
order = env["indigo.order"].browse(3)
order.stage_id = env.ref("indigo_decors.stage_ready_install").id
env.cr.commit()
print("ORDER %s -> Ready for Installation" % order.name)
