env = env  # noqa
# Aplicar indigo_theme al website (esto invoca theme.utils._post_copy)
website = env["website"].browse(1)
theme = env["ir.module.module"].search([("name", "=", "indigo_theme")], limit=1)
print("Theme state:", theme.state)
print("Website theme_id before:", website.theme_id.name if website.theme_id else "None")

# Use website.button_go_website + apply, or directly invoke the install pipeline
# In Odoo 17 themes are applied via the theme installation; ensure customize is fresh
env["ir.qweb"]._get_asset_paths.cache.clear() if hasattr(env["ir.qweb"]._get_asset_paths, 'cache') else None

# Manually invoke the post_copy hook
try:
    env['theme.utils'].with_context(website_id=website.id)._theme_indigo_theme_post_copy(theme)
    print("Post copy invoked")
except Exception as e:
    print(f"Post copy error: {e}")

# Flush all compiled assets to force recompile
n = env["ir.attachment"].search([
    ("name", "ilike", "%.assets_%"),
    ("res_model", "=", "ir.ui.view"),
]).unlink()
print(f"Flushed compiled assets")

# Also flush SCSS attachments
n2 = env["ir.attachment"].search([
    ("url", "ilike", "/web/assets/%"),
]).unlink()
print(f"Flushed SCSS bundles")

env.cr.commit()
print("DONE")
