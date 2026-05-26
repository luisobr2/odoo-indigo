env = env  # noqa
Stock = env["indigo.stock"]
Design = env["indigo.design"]

design = env.ref("indigo_decors.design_id01_sd")

stock = Stock.search([("design_id", "=", design.id), ("door_type", "=", "SD")], limit=1)
if not stock:
    stock = Stock.create({
        "design_id": design.id,
        "door_type": "SD",
        "on_hand": 10,
        "low_stock_threshold": 5,
    })
print("Stock", stock.design_id.code, "type", stock.door_type)
print("  on_hand:", stock.on_hand)
print("  reserved:", stock.reserved)
print("  available:", stock.available)
print("  is_low_stock:", stock.is_low_stock)

# Bajar on_hand para forzar low stock
stock.on_hand = 3
stock._compute_reserved()
print("AFTER setting on_hand=3:")
print("  available:", stock.available, "is_low:", stock.is_low_stock)

# Cron
n = env["indigo.stock"]._cron_low_stock_alert()
print("Low stock alerts created:", n)
env.cr.commit()
