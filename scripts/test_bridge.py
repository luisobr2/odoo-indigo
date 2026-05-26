env = env  # noqa
# 1. Crear/encontrar producto indigo
Product = env["product.product"]
Template = env["product.template"]
prod = Product.search([("default_code", "=", "ID01-SD")], limit=1)
if not prod:
    tmpl = Template.create({
        "name": "ID01 Single Door",
        "default_code": "ID01-SD",
        "detailed_type": "consu",
        "list_price": 250.0,
        "is_indigo_design": True,
        "indigo_door_type": "SD",
        "indigo_design_id": env.ref("indigo_decors.design_id01_sd").id,
    })
    prod = tmpl.product_variant_id
    print("CREATED product:", prod.default_code, "id=", prod.id)
else:
    prod.product_tmpl_id.write({
        "is_indigo_design": True,
        "indigo_door_type": "SD",
        "indigo_design_id": env.ref("indigo_decors.design_id01_sd").id,
    })
    print("UPDATED product:", prod.default_code)

# 2. Crear sale.order para Lock Tight
lock = env.ref("indigo_decors.dealer_lock_tight")
SO = env["sale.order"]
so = SO.create({
    "partner_id": lock.id,
    "order_line": [
        (0, 0, {"product_id": prod.id, "product_uom_qty": 2, "price_unit": 250.0}),
    ],
})
print("CREATED sale.order:", so.name)
print("  indigo_order_id BEFORE confirm:", so.indigo_order_id.id if so.indigo_order_id else "None")

# 3. Confirmar
so.action_confirm()
env.cr.commit()
print("AFTER confirm:")
print("  indigo_order_id:", so.indigo_order_id.id if so.indigo_order_id else "None")
if so.indigo_order_id:
    io = so.indigo_order_id
    print("  indigo.order:", io.name, "dealer:", io.dealer_id.name, "client:", io.client_name)
    print("  doors:", io.door_count, "sqf:", io.total_sqf)
    for l in io.line_ids:
        print("    line: design=%s door=%s color=%s qty=%s" % (
            l.design_id.code, l.door_type, l.color, l.qty
        ))
