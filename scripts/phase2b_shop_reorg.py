# -*- coding: utf-8 -*-
"""Phase 2B storefront reorganization (Option B: one card per family + selector).

Run inside an Odoo shell against the target DB, e.g.:

    # DRY RUN (prints the plan, changes nothing):
    docker exec -i <odoo> odoo shell -c /etc/odoo/odoo.conf -d <db> \
        --no-http --stop-after-init < scripts/phase2b_shop_reorg.py

    # APPLY (commits): set the env var first
    docker exec -e INDIGO_APPLY=1 -i <odoo> odoo shell -c /etc/odoo/odoo.conf \
        -d <db> --no-http --stop-after-init < scripts/phase2b_shop_reorg.py

What it does (idempotent — safe to re-run):

  1. REPAIR unflagged design products. Some catalog products are named like a
     design (ID02-DD, ID08-SD, ...) and have a matching indigo.design by code,
     but were imported with is_indigo_design=False, no design link and no door
     type. Ordering them silently skips the production bridge and the storefront
     shows no door-type selector for them. Flag them, link the design and set
     the door type (from the design, else parsed from the -SD/-DD/-SDL code).

  2. ONE CARD PER FAMILY. A design family (ID01) has separate SD and DD product
     templates; publishing both shows duplicate cards. Keep exactly one card
     published per family (prefer the Double Door — it is the lower-sequence
     primary in the current data and matches the existing ID05 convention) and
     unpublish the SD / sidelite siblings. The PDP door-type selector still
     offers every type in the family and the server orders the right sibling
     (see indigo_variant_for_type), so nothing becomes unorderable.

  3. CUSTOM FIRST. The flexible CUSTOM design (no fixed door type — dealer photo
     orders) is moved to the front of the grid via a low website_sequence.
"""
import os
import re

APPLY = os.environ.get("INDIGO_APPLY") == "1"
TYPE_RANK = {"DD": 0, "SD": 1, "sidelite": 2}  # keeper preference: DD is the face
CODE_TO_TYPE = {"SD": "SD", "DD": "DD", "SDL": "sidelite"}

Tmpl = env["product.template"]
Des = env["indigo.design"]


def family_of(code):
    m = re.match(r"^(.+)-(SD|DD|SDL)$", code or "", re.I)
    return m.group(1) if (m and len(m.group(1)) >= 2) else (code or "")


def type_of(tmpl):
    d = tmpl.indigo_design_id
    return tmpl.indigo_door_type or (d.door_type if d else None)


print("=" * 64)
print("PHASE 2B SHOP REORG  —  mode:", "APPLY (will commit)" if APPLY else "DRY RUN (rollback)")
print("=" * 64)

# ---------------------------------------------------------------- Part 1
# Repair design-named products that were never flagged as Indigo designs.
repaired = 0
for t in Tmpl.search([("is_indigo_design", "=", False)]):
    code = t.default_code or t.name or ""
    design = Des.search([("code", "=", code)], limit=1)
    if not design:
        continue
    vals = {"is_indigo_design": True}
    if not t.indigo_design_id:
        vals["indigo_design_id"] = design.id
    dt = design.door_type
    if not dt:
        m = re.match(r"^.+-(SD|DD|SDL)$", code, re.I)
        if m:
            dt = CODE_TO_TYPE[m.group(1).upper()]
    if dt and not t.indigo_door_type:
        vals["indigo_door_type"] = dt
    print("  REPAIR %-12s id=%-4s -> is_design=True design=%s type=%s" % (
        code, t.id, design.code, vals.get("indigo_door_type", t.indigo_door_type)))
    t.write(vals)
    repaired += 1
print("Part 1: repaired %d unflagged design products." % repaired)
print("-" * 64)

# ---------------------------------------------------------------- Part 2
# One published card per family.
fams = {}
for t in Tmpl.search([("is_indigo_design", "=", True)]):
    d = t.indigo_design_id
    code = (d.code if d else (t.default_code or t.name)) or ""
    fams.setdefault(family_of(code), Tmpl)
    fams[family_of(code)] |= t

unpublished = 0
republished = 0
for fam in sorted(fams):
    tmpls = fams[fam]
    if len(tmpls) < 2:
        continue
    ordered = tmpls.sorted(key=lambda t: (TYPE_RANK.get(type_of(t), 9),
                                          t.website_sequence or 0, t.id))
    keeper = ordered[0]
    losers = ordered[1:]
    pubs = tmpls.filtered("is_published")
    if len(pubs) <= 1 and keeper.is_published:
        continue  # already one-per-family, nothing to do
    print("  FAM %-8s keep %-12s (type=%s) | unpublish: %s" % (
        fam, keeper.name, type_of(keeper),
        ", ".join("%s(%s)" % (t.name, type_of(t)) for t in losers)))
    if not keeper.is_published:
        keeper.is_published = True
        republished += 1
    for t in losers:
        if t.is_published:
            t.is_published = False
            unpublished += 1
print("Part 2: unpublished %d redundant cards, (re)published %d keepers." % (
    unpublished, republished))
print("-" * 64)

# ---------------------------------------------------------------- Part 3
# CUSTOM first.
custom = Tmpl.search([("is_indigo_design", "=", True),
                      ("indigo_design_id.code", "=", "CUSTOM")], limit=1)
if not custom:
    custom = Tmpl.search([("name", "=", "CUSTOM")], limit=1)
if custom:
    if custom.website_sequence != 10 or not custom.is_published:
        print("  CUSTOM id=%s seq %s -> 10, published=%s -> True" % (
            custom.id, custom.website_sequence, custom.is_published))
        custom.website_sequence = 10
        custom.is_published = True
    else:
        print("  CUSTOM already first (seq=10, published).")
else:
    print("  CUSTOM design not found — skipped.")
print("-" * 64)

# ---------------------------------------------------------------- summary
pub_designs = Tmpl.search_count([("is_indigo_design", "=", True), ("is_published", "=", True)])
print("Published design cards now:", pub_designs)
if APPLY:
    env.cr.commit()
    print(">>> COMMITTED.")
else:
    env.cr.rollback()
    print(">>> DRY RUN — rolled back, no changes persisted.")
