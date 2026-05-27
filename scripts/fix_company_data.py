"""Reemplaza datos placeholder de la empresa con datos reales Indigo Decors."""
env = env  # noqa

company = env.company  # default company
company.write({
    "name": "Indigo Decors",
    "street": "Miami",
    "street2": "",
    "city": "Miami",
    "state_id": env.ref("base.state_us_9").id,  # Florida
    "zip": "33172",
    "country_id": env.ref("base.us").id,
    "phone": "+1 786-300-2752",
    "mobile": "+1 786-300-2752",
    "email": "sales@indigodecors.com",
    "website": "https://www.indigodecors.com",
})
print(f"Updated company: {company.name}")

# Actualizar tambien res.partner asociado
company.partner_id.write({
    "name": "Indigo Decors",
    "street": "Miami",
    "city": "Miami",
    "state_id": env.ref("base.state_us_9").id,
    "zip": "33172",
    "country_id": env.ref("base.us").id,
    "phone": "+1 786-300-2752",
    "email": "sales@indigodecors.com",
    "website": "https://www.indigodecors.com",
})

# Sistema parameter: web.base.url
env["ir.config_parameter"].sudo().set_param("web.base.url", "https://app.indigodecors.com")

env.cr.commit()
print("DONE - datos de empresa actualizados")
