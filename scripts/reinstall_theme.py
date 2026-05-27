env = env  # noqa
m = env["ir.module.module"].search([("name", "=", "indigo_theme")], limit=1)
print("State before:", m.state)
if m.state == "installed":
    m.button_immediate_uninstall()
    env.cr.commit()
    print("Uninstalled")
m = env["ir.module.module"].search([("name", "=", "indigo_theme")], limit=1)
m.button_immediate_install()
env.cr.commit()
print("Installed. State:", m.state)
# Flush assets
n = env["ir.attachment"].search([("name", "ilike", "%.assets_%"), ("res_model", "=", "ir.ui.view")]).unlink()
env.cr.commit()
print("Flushed compiled assets")
# Count ir.asset for indigo_theme
ct = env["ir.asset"].search_count([("path", "ilike", "%indigo_theme%")])
print(f"ir.asset entries for indigo_theme: {ct}")
