# Setea el logo Indigo en el website + nombre del site
env = env  # noqa
import base64
from pathlib import Path

LOGO_PATH = "/mnt/extra-addons/indigo_theme/static/src/img/logo.png"
try:
    with open(LOGO_PATH, "rb") as f:
        logo_b64 = base64.b64encode(f.read())
except FileNotFoundError:
    print(f"Logo not found at {LOGO_PATH}")
    raise SystemExit(1)

websites = env["website"].search([])
for w in websites:
    w.write({
        "logo": logo_b64,
        "name": "Indigo Decors",
    })
    print(f"Updated website {w.id}: {w.name}")

# Tambien aplicar el tema
indigo_theme = env["ir.module.module"].search([("name", "=", "indigo_theme")], limit=1)
if indigo_theme.state != "installed":
    indigo_theme.button_immediate_install()

env.cr.commit()
print("DONE")
