# Flush compiled assets cache - fuerza recompilacion SCSS
env = env  # noqa
n = env["ir.attachment"].search([
    ("name", "ilike", "%.assets_%"),
    ("res_model", "=", "ir.ui.view"),
]).unlink()
print("Cleared compiled assets")
env.cr.commit()
