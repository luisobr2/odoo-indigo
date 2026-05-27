"""Reemplaza datos placeholder hardcoded en ir.ui.view arch_db."""
env = env  # noqa

REPLACEMENTS = [
    ("+1 555-555-5556", "+1 786-300-2752"),
    ("Mi Compañía", "Indigo Decors"),
    ("Mi compañía", "Indigo Decors"),
    ("My Company", "Indigo Decors"),
    ("info@sucompañía.example.com", "sales@indigodecors.com"),
    ("info@sucompania.example.com", "sales@indigodecors.com"),
    ("3575 Fake Buena Vista Avenue", "Miami, FL · USA"),
    ("3575 Fake Buena Vista", "Miami"),
    ("sucompañia.example.com", "indigodecors.com"),
    ("YourCompany.com", "indigodecors.com"),
    ("Nombre de la empresa", "Indigo Decors"),
]

views = env["ir.ui.view"].search([])
updated = 0
for v in views:
    if not v.arch_db:
        continue
    arch = v.arch_db
    changed = False
    for old, new in REPLACEMENTS:
        if old in arch:
            arch = arch.replace(old, new)
            changed = True
    if changed:
        try:
            v.arch_db = arch
            updated += 1
            print(f"  updated view {v.id}: {v.name}")
        except Exception as e:
            print(f"  skip {v.id} ({v.name}): {e}")
env.cr.commit()
print(f"\nUpdated {updated} views")
