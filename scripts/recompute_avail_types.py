# -*- coding: utf-8 -*-
"""Recompute product.template.indigo_avail_types for every Indigo design.

Run in an Odoo shell after adding/changing design families (the field is not an
@api.depends compute because it reads sibling products):

    docker exec -i <odoo> odoo shell -c /etc/odoo/odoo.conf -d <db> \
        --no-http --stop-after-init < scripts/recompute_avail_types.py
"""
tmpls = env["product.template"].search([("is_indigo_design", "=", True)])
tmpls._indigo_compute_avail_types()
env.cr.commit()
print("MARK recomputed indigo_avail_types for", len(tmpls), "designs")
for t in tmpls.sorted("name")[:6]:
    print("MARK", t.name, "->", t.indigo_avail_types)
# DD-only families (the ones the type=SD filter hides)
ddonly = tmpls.filtered(lambda t: t.indigo_avail_types == "DD")
print("MARK DD-only families:", ddonly.mapped("name"))
