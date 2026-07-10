# Shop Type+Color Filters — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add server-side Type + Color filters to `indigodecors.com/shop`, with each product card defaulting to the single-door black photo.

**Architecture:** Odoo 17 `website_sale` override. A stored `indigo_avail_types` char on `product.template` powers the type-based hide; a `WebsiteSale` controller override reads `type`/`color` URL params (type → search domain, color → context only); QWeb inherits inject a filter bar and swap each card image to `/indigo/door_image/<design>/<color>?type=<type>`.

**Tech Stack:** Odoo 17 (Python, QWeb XML), `indigo_decors` + `indigo_theme` modules. Verification via `docker exec … odoo shell`, `curl`, and the live storefront in a browser (dealer session).

## Global Constraints

- Storefront cards are one-per-family, all published as the **DD** product; color is served as an image via `/indigo/door_image/<design_id>/<color>?type=<type>`, not as a variant.
- Default image = **SD + black** (`type='SD'`, `color='black'` when params absent).
- **Color never hides** (all 92 designs allow all 3 colors); **type hides** only families lacking the selected type (today only ID93-DD).
- Deploy = commit+push → Coolify deploy (uuid `f57xxcgj6dph9nkrvekz91h6`) → `-u indigo_decors,indigo_theme` → `docker restart`. Bump `theme.css`/`theme.js` `?v=` only if those assets change (this plan changes neither by default).
- Never place real storefront orders on prod (emails staff).

---

### Task 1: `indigo_avail_types` stored field + recompute

**Files:**
- Modify: `addons/indigo_decors/models/indigo_sale_bridge.py` (ProductTemplate class)
- Create: `scripts/recompute_avail_types.py` (odoo-shell recompute)
- Modify: `addons/indigo_decors/__manifest__.py` (version bump)

**Interfaces:**
- Produces: `product.template.indigo_avail_types` (Char, stored, e.g. `"SD,DD"`), and `product.template._indigo_compute_avail_types()` recompute method.

- [ ] **Step 1: Add the field + compute** in the `ProductTemplate` class (near `indigo_family_types`):

```python
    indigo_avail_types = fields.Char(
        string="Available door types (storefront)",
        help="Comma-separated door types available in this design's family "
             "(e.g. 'SD,DD'). Powers the /shop type filter's hide. Recompute "
             "with scripts/recompute_avail_types.py after adding designs.",
    )

    def _indigo_compute_avail_types(self):
        for tmpl in self:
            if not tmpl.is_indigo_design:
                tmpl.indigo_avail_types = False
                continue
            types = [f["door_type"] for f in tmpl.indigo_family_types()]
            tmpl.indigo_avail_types = ",".join(types) if types else False
```

- [ ] **Step 2: Recompute script** `scripts/recompute_avail_types.py`:

```python
# odoo shell -c /etc/odoo/odoo.conf -d indigo-prod --no-http --stop-after-init < this
tmpls = env["product.template"].search([("is_indigo_design", "=", True)])
tmpls._indigo_compute_avail_types()
env.cr.commit()
print("MARK recomputed indigo_avail_types for", len(tmpls), "designs")
for t in tmpls[:5]:
    print("MARK", t.name, "->", t.indigo_avail_types)
```

- [ ] **Step 3: Bump `indigo_decors` version** in `__manifest__.py` (e.g. `17.0.0.74.0` → `17.0.0.75.0`).

- [ ] **Step 4 (verify, local): `-u` then run the recompute + check**

```bash
docker exec indigo-odoo odoo -c /etc/odoo/odoo.conf -d indigo-prod -u indigo_decors --no-http --stop-after-init 2>&1 | grep -Ei "Modules loaded|error"
docker exec -i indigo-odoo odoo shell -c /etc/odoo/odoo.conf -d indigo-prod --no-http --stop-after-init < scripts/recompute_avail_types.py | grep MARK
```
Expected: `Modules loaded`, and `indigo_avail_types` like `SD,DD` (and `DD` for the DD-only family).

- [ ] **Step 5: Commit** `git add addons/indigo_decors/models/indigo_sale_bridge.py scripts/recompute_avail_types.py addons/indigo_decors/__manifest__.py && git commit -m "feat(shop): indigo_avail_types stored field for the type filter"`

---

### Task 2: `WebsiteSale` controller override (type domain + color/type context)

**Files:**
- Modify: `addons/indigo_decors/controllers/website_sale_custom.py` (extend the existing `IndigoNoCart(WebsiteSale)` class OR add a new `WebsiteSale` subclass)

**Interfaces:**
- Consumes: `indigo_avail_types` (Task 1).
- Produces: `/shop` renders with `indigo_type` (`'SD'|'DD'|''`) and `indigo_color` (`'white'|'bronze'|'black'|''`) in `response.qcontext`; type filters the product domain.

- [ ] **Step 1: Add the overrides.** In `website_sale_custom.py`, on the class that already inherits `WebsiteSale` (`IndigoNoCart`), add:

```python
    _INDIGO_TYPES = ("SD", "DD")
    _INDIGO_COLORS = ("white", "bronze", "black")

    def _get_search_domain(self, search, category, attrib_values, search_in_description=True):
        domain = super()._get_search_domain(search, category, attrib_values, search_in_description)
        door_type = (request.params.get("type") or "").strip().upper()
        if door_type in self._INDIGO_TYPES:
            domain += [("indigo_avail_types", "like", door_type)]
        return domain

    @http.route()
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        response = super().shop(page=page, category=category, search=search,
                                min_price=min_price, max_price=max_price, ppg=ppg, **post)
        if hasattr(response, "qcontext"):
            dt = (post.get("type") or "").strip().upper()
            dc = (post.get("color") or "").strip().lower()
            response.qcontext["indigo_type"] = dt if dt in self._INDIGO_TYPES else ""
            response.qcontext["indigo_color"] = dc if dc in self._INDIGO_COLORS else ""
        return response
```

- [ ] **Step 2 (verify, local): the type domain hides DD-only.** Restart, then curl the shop and count products for `?type=SD` vs no filter (public grid is fine — filter is not dealer-gated):

```bash
docker restart indigo-odoo >/dev/null 2>&1 ; sleep 6
docker exec indigo-odoo curl -s "http://localhost:8069/shop?type=DD" | grep -c "oe_product" 
docker exec indigo-odoo curl -s "http://localhost:8069/shop?type=SD" | grep -c "oe_product"
```
Expected: both return a positive count; SD count ≤ DD/no-filter count (DD-only families dropped). (Local data differs from prod; the real check is on prod in Task 5.)

- [ ] **Step 3: Commit** `git add addons/indigo_decors/controllers/website_sale_custom.py && git commit -m "feat(shop): type filters the product domain; type+color passed to render"`

---

### Task 3: QWeb — swap each card image to the door_image route

**Files:**
- Modify: `addons/indigo_theme/views/product_detail.xml` (or a new `addons/indigo_theme/views/shop_grid.xml`, registered in the manifest) — inherit the grid item template.

**Interfaces:**
- Consumes: `indigo_type`/`indigo_color` (Task 2), `product.indigo_family_types()`.

- [ ] **Step 1: Find the exact image node.** Inspect the live grid item template to get the xpath target:

```bash
docker exec -i indigo-odoo odoo shell -c /etc/odoo/odoo.conf -d indigo-prod --no-http --stop-after-init <<'PY'
v = env.ref("website_sale.products_item")
import re
arch = v.arch or ""
i = arch.find("product_detail_img") if "product_detail_img" in arch else arch.find("oe_product_image")
print(arch[max(0,i-200):i+300])
PY
```
Note the `<img>` / `<span t-field=...image...>` node used for the card thumbnail (Odoo 17 typically `website_sale.products_item` → a `<span class="oe_product_image">` wrapping an `<img t-att-src>` or a `t-field` image widget).

- [ ] **Step 2: Add the inherit** (new file `addons/indigo_theme/views/shop_grid.xml`, added to `__manifest__.py` `data` after the other views). Replace the card image src with the door_image URL. Skeleton (adjust xpath to Step 1's node):

```xml
<odoo>
  <template id="indigo_shop_card_image" inherit_id="website_sale.products_item"
            name="Indigo: card image by type+color" priority="30">
    <!-- Replace the product thumbnail with the design's type+color photo.
         Default SD+black; when a filter is active, that type/color. -->
    <xpath expr="//img[hasclass('oe_product_image_img')]" position="attributes">
      <attribute name="t-att-src">
        (lambda itype, icolor: (lambda ift: '/indigo/door_image/%s/%s?type=%s' % (
            (ift[0]['design_id'] if ift else product.indigo_design_id.id), icolor, itype))(
            [f for f in product.indigo_family_types() if f['door_type'] == itype]))(
            (indigo_type or 'SD'), (indigo_color or 'black'))
      </attribute>
      <attribute name="t-att-data-src"/>
    </xpath>
  </template>
</odoo>
```
If the node is a `t-field` image (not a plain `<img>`), instead replace the whole node with a plain `<img>` carrying that `t-att-src`, `class="img img-fluid"`, `loading="lazy"`, `t-att-alt="product.name"`.

- [ ] **Step 3: Register** the new file in `addons/indigo_theme/__manifest__.py` `data` list; bump `indigo_theme` version.

- [ ] **Step 4 (verify, local): `-u indigo_theme`, then curl the grid and confirm the door_image URL appears in the card:**

```bash
docker exec indigo-odoo odoo -c /etc/odoo/odoo.conf -d indigo-prod -u indigo_theme --no-http --stop-after-init 2>&1 | grep -Ei "Modules loaded|error|cannot be located"
docker restart indigo-odoo >/dev/null 2>&1 ; sleep 6
docker exec indigo-odoo curl -s "http://localhost:8069/shop" | grep -o "/indigo/door_image/[0-9]*/black?type=SD" | head -3
docker exec indigo-odoo curl -s "http://localhost:8069/shop?type=DD&color=bronze" | grep -o "/indigo/door_image/[0-9]*/bronze?type=DD" | head -3
```
Expected: default grid shows `…/black?type=SD` src on cards; the filtered grid shows `…/bronze?type=DD`.

- [ ] **Step 5: Commit** `git add addons/indigo_theme/views/shop_grid.xml addons/indigo_theme/__manifest__.py && git commit -m "feat(shop): card image follows the type+color filter (default SD black)"`

---

### Task 4: QWeb — the filter bar

**Files:**
- Modify: `addons/indigo_theme/views/shop_grid.xml` (add a second inherit for the bar)

**Interfaces:**
- Consumes: `indigo_type`/`indigo_color` (Task 2). Links preserve `search`/`category`.

- [ ] **Step 1: Find the grid wrapper xpath.** The bar goes just before the products grid. Inspect:

```bash
docker exec -i indigo-odoo odoo shell -c /etc/odoo/odoo.conf -d indigo-prod --no-http --stop-after-init <<'PY'
v = env.ref("website_sale.products")
a = v.arch or ""
for key in ("o_wsale_products_grid_table_wrapper", "products_grid", "oe_product"):
    print(key, a.find(key))
PY
```
Target a stable wrapper id/class before the grid (e.g. `#products_grid` or the `o_wsale_products_main_row`).

- [ ] **Step 2: Add the bar inherit** in `shop_grid.xml`. Build links preserving current `search`/`category` and toggling type/color; highlight active. Skeleton:

```xml
  <template id="indigo_shop_filter_bar" inherit_id="website_sale.products"
            name="Indigo: type+color filter bar" priority="30">
    <xpath expr="//div[@id='products_grid']" position="before">
      <t t-set="_kbase" t-value="{}"/>
      <t t-if="search"><t t-set="_kbase" t-value="dict(_kbase, search=search)"/></t>
      <t t-if="category"><t t-set="_kbase" t-value="dict(_kbase, category=category.id)"/></t>
      <t t-set="_cur_type" t-value="indigo_type or ''"/>
      <t t-set="_cur_color" t-value="indigo_color or ''"/>
      <div class="indigo-shop-filters mb-3 d-flex flex-wrap gap-3">
        <div class="indigo-filter-group">
          <span class="indigo-eyebrow me-2">Type</span>
          <t t-foreach="[('','All'),('SD','Single'),('DD','Double')]" t-as="opt">
            <a t-att-href="'/shop?' + keep_query('search','category') "
               t-attf-class="btn btn-sm #{'btn-primary' if _cur_type == opt[0] else 'btn-outline-secondary'}"
               t-att-data-type="opt[0]">
              <t t-esc="opt[1]"/>
            </a>
          </t>
        </div>
        <div class="indigo-filter-group">
          <span class="indigo-eyebrow me-2">Color</span>
          <t t-foreach="[('','All'),('black','Black'),('white','White'),('bronze','Bronze')]" t-as="opt">
            <a t-attf-class="btn btn-sm #{'btn-primary' if _cur_color == opt[0] else 'btn-outline-secondary'}"
               t-att-data-color="opt[0]"><t t-esc="opt[1]"/></a>
          </t>
        </div>
      </div>
    </xpath>
  </template>
```
Note: `keep_query` is Odoo's helper for preserving query params; the exact href must set `type`/`color` while keeping `search`/`category`. If `keep_query` proves awkward, build the href by hand from `_kbase` + the option value: `'/shop?%s' % werkzeug.urls.url_encode(dict(_kbase, type=opt[0], color=_cur_color))` (import via a QWeb-safe helper, or precompute the query strings in the controller `qcontext` in Task 2 to avoid logic in XML).

- [ ] **Step 3 (verify, local): bar renders + links carry the params:**

```bash
docker exec indigo-odoo odoo -c /etc/odoo/odoo.conf -d indigo-prod -u indigo_theme --no-http --stop-after-init 2>&1 | grep -Ei "Modules loaded|error|cannot be located"
docker restart indigo-odoo >/dev/null 2>&1 ; sleep 6
docker exec indigo-odoo curl -s "http://localhost:8069/shop?type=DD" | grep -o 'indigo-shop-filters' | head -1
docker exec indigo-odoo curl -s "http://localhost:8069/shop?type=DD" | grep -o 'btn-primary[^>]*data-type="DD"' | head -1
```
Expected: the bar class appears; the Double button is `btn-primary` (active).

- [ ] **Step 4: Commit** `git add addons/indigo_theme/views/shop_grid.xml && git commit -m "feat(shop): type+color filter bar above the grid"`

**Decision to lock during Step 2:** if building hrefs in XML is fragile, precompute in the controller (Task 2) three helper dicts (`indigo_type_links`, `indigo_color_links`) mapping option→full href, and have the XML just render them. Prefer this if the inline `keep_query` approach doesn't cleanly set one param while preserving the rest.

---

### Task 5: Deploy to prod + end-to-end verification

**Files:** none (deploy + verify)

- [ ] **Step 1: Push + Coolify deploy:**
```bash
git -c credential… push origin main
curl -s -X POST "http://2.25.137.220:8000/api/v1/deploy?uuid=f57xxcgj6dph9nkrvekz91h6&force=true" -H "Authorization: Bearer <token>"
```
- [ ] **Step 2: After build finishes:** SSH → `-u indigo_decors,indigo_theme` → run `scripts/recompute_avail_types.py` → `docker restart`.
- [ ] **Step 3: Verify on prod** (public curl, no order placed):
  - `curl https://indigodecors.com/shop` → cards carry `…/black?type=SD`.
  - `…/shop?type=DD` → `…/black?type=DD`; `…/shop?color=bronze` → `…/bronze?type=SD`.
  - `…/shop?type=SD` count `oe_product` == (all − DD-only families); confirm ID93 absent.
  - Filter bar present; active button highlighted; a filter link keeps `?search=`/`?category=` when present.
- [ ] **Step 4: Browser check** (dealer session): open /shop, click Type=Double + Color=Bronze → cards show double bronze; click Type=Single → ID93 disappears; screenshot.
- [ ] **Step 5: Update memory** (`indigo_storefront_catalog.md`) with the /shop filters + the `indigo_avail_types` recompute caveat.

## Self-Review

- **Spec coverage:** field (T1) ✓, controller domain+context (T2) ✓, card image (T3) ✓, filter bar (T4) ✓, deploy+verify+memory (T5) ✓. Default SD+black (T3 defaults) ✓. Hide by type only (T2 domain; color not in domain) ✓.
- **Placeholder scan:** the two QWeb tasks carry an explicit "find the exact xpath" step because the `website_sale` node names must be read from the live template, not guessed — the fallback (precompute hrefs in the controller) is spelled out, not a TODO.
- **Type consistency:** `indigo_type`/`indigo_color` names identical across T2 (produce) and T3/T4 (consume); `indigo_avail_types` identical across T1/T2.
