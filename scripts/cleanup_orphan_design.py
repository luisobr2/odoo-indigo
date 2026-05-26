# Limpia diseno huerfano antes de cargar demo data
env = env  # noqa
Design = env["indigo.design"]
ImD = env["ir.model.data"]
designs = Design.search([])
for d in designs:
    has_xmlid = ImD.search_count([("model", "=", "indigo.design"), ("res_id", "=", d.id)])
    if not has_xmlid:
        print("UNLINK", d.code, "(sin xmlid)")
        d.unlink()
env.cr.commit()
print("DONE")
