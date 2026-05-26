# -*- coding: utf-8 -*-
"""Seed minimo para verificacion del flujo: 1 dealer, 1 diseno, 1 orden."""

env = env  # noqa: F821  inyectado por odoo shell

Partner = env["res.partner"]
Design = env["indigo.design"]
Order = env["indigo.order"]
Stage = env["indigo.stage"]

dealer = Partner.search([("name", "=", "Lock Tight")], limit=1)
if not dealer:
    dealer = Partner.create({
        "name": "Lock Tight",
        "is_indigo_dealer": True,
        "indigo_dealer_code": "LT",
        "is_company": True,
        "email": "ops@locktight.example",
    })

design = Design.search([("code", "=", "ID01-SD")], limit=1)
if not design:
    design = Design.create({"code": "ID01-SD", "name": "ID01 Single Door", "door_type": "SD"})

admin = env.ref("base.user_admin")

stage_new = env.ref("indigo_decors.stage_new_order")
stage_cnc = env.ref("indigo_decors.stage_cnc")

order = Order.create({
    "dealer_id": dealer.id,
    "dealer_ref": "LT-TEST-001",
    "client_name": "Cliente de prueba",
    "client_phone": "555-0100",
    "client_email": "cliente@example.com",
    "client_address": "123 Test Street, Miami FL",
    "assigned_user_ids": [(4, admin.id)],
    "stage_id": stage_new.id,
    "line_ids": [
        (0, 0, {
            "design_id": design.id,
            "door_type": "SD",
            "color": "white",
            "glass_type": "ESW",
            "width": 36.0,
            "height": 80.0,
            "qty": 1,
        }),
        (0, 0, {
            "design_id": design.id,
            "door_type": "DD",
            "color": "bronze",
            "glass_type": "ESW",
            "width": 72.0,
            "height": 80.0,
            "qty": 1,
        }),
    ],
})

env.cr.commit()

print("ORDER_CREATED:", order.name, "id=", order.id)
print("TOTAL_SQF:", order.total_sqf, "doors=", order.door_count)
print("PAINTER_PAYOUT:", order.total_painter_payout, "INSTALLER_PAYOUT:", order.total_installer_payout)

# Disparar cambio de etapa para verificar el correo
order.write({"stage_id": stage_cnc.id})
env.cr.commit()
print("STAGE_CHANGED_TO:", order.stage_id.name)
print("MAIL_QUEUE_AFTER_WRITE:", env["mail.mail"].search_count([("model", "=", "indigo.order")]))
