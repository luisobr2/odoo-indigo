# -*- coding: utf-8 -*-
"""Test end-to-end de liquidaciones."""
env = env  # noqa

Partner = env["res.partner"]
Order = env["indigo.order"]
Payout = env["indigo.payout"]

# Crear pintor + 2 instaladores
painter = Partner.search([("name", "=", "Pedro Pintor")], limit=1)
if not painter:
    painter = Partner.create({"name": "Pedro Pintor", "is_company": False})

inst1 = Partner.search([("name", "=", "Javier Instalador")], limit=1)
if not inst1:
    inst1 = Partner.create({"name": "Javier Instalador", "is_company": False})

inst2 = Partner.search([("name", "=", "Carlos Instalador")], limit=1)
if not inst2:
    inst2 = Partner.create({"name": "Carlos Instalador", "is_company": False})

order = env.ref("__export__.indigo_order_3", raise_if_not_found=False) or Order.browse(3)
order.write({
    "painter_id": painter.id,
    "installer_ids": [(6, 0, [inst1.id, inst2.id])],
})
env.cr.commit()
print("ORDER:", order.name, "painter=", order.painter_id.name, "installers=", order.installer_ids.mapped("name"))

# Limpiar payouts previos para test idempotente
old = Payout.search([("contractor_id", "in", [painter.id, inst1.id, inst2.id])])
old.unlink()
env.cr.commit()

# Mover a Painting, luego SALIR de Painting (gatilla payout pintor)
stage_painting = env.ref("indigo_decors.stage_painting")
stage_ready_install = env.ref("indigo_decors.stage_ready_install")
stage_installed = env.ref("indigo_decors.stage_installed")

order.stage_id = stage_painting.id
env.cr.commit()
print("STAGE -> Painting (no payout aun)")

order.stage_id = stage_ready_install.id
env.cr.commit()
print("STAGE -> Ready for Installation (debio crear payout pintor)")

# Saltar a Installed (gatilla payout instaladores)
order.stage_id = stage_installed.id
env.cr.commit()
print("STAGE -> Installed (debio crear payouts instaladores)")

# Verificar
print("\n--- PAYOUTS GENERADOS ---")
for p in Payout.search([("contractor_id", "in", [painter.id, inst1.id, inst2.id])]):
    print("  %s | %s (%s) | $%.2f | state=%s" % (
        p.name, p.contractor_id.name, p.contractor_type, p.amount, p.state
    ))
    for l in p.line_ids:
        print("    - %s: qty=%.2f rate=$%.2f amount=$%.2f" % (
            l.description, l.quantity, l.rate, l.amount
        ))
