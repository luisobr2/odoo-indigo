# -*- coding: utf-8 -*-
"""
Importa scraping/output/products.csv -> Odoo como product.template.

Para cada fila:
- Crea/actualiza product.template con name + default_code + is_indigo_design=True
- Crea/asocia atributos (Finish Color, Door Brand, Privacy Glass) con valores
- Sube todas las imagenes de scraping/output/images/<code>/*.jpg al image_1920
  (la primera como image_1920 del template, las demas como product.image)
- Mapea door_type segun el codigo (-SD, -DD, sidelite)

Uso:
    docker compose exec -T odoo odoo shell -c /etc/odoo/odoo.conf -d indigo-db --no-http < scripts/import_scraped.py
"""
import os
import re
import csv
import json
import base64
from pathlib import Path

env = env  # noqa: F821 - inyectado por odoo shell

ROOT = "/mnt/extra-addons/../scraping/output"  # dentro del contenedor
# Fallback path - el script corre dentro de docker, busca el dir
if not os.path.isdir(ROOT):
    ROOT = "/scraping/output"
if not os.path.isdir(ROOT):
    # Path local
    here = Path("/opt/odoo")
    for parent in [Path("/mnt/extra-addons/.."), Path("/")]:
        cand = parent / "scraping" / "output"
        if cand.is_dir():
            ROOT = str(cand)
            break

CSV_PATH = os.path.join(ROOT, "products.csv")
IMAGES_DIR = os.path.join(ROOT, "images")

ProductTemplate = env["product.template"]
ProductImage = env["product.image"]
AttrModel = env["product.attribute"]
AttrValueModel = env["product.attribute.value"]
TmplLine = env["product.template.attribute.line"]
Design = env["indigo.design"]


def code_from_name(name):
    """ID01-DD => ID01-DD (already a code)"""
    if not name:
        return ""
    # Limpiar espacios y caracteres raros, mantener formato XXX-XX
    return re.sub(r"[^A-Za-z0-9-]", "", name).upper()


def door_type_from_code(code):
    c = code.upper()
    if "DD" in c or "DOUBLE" in c:
        return "DD"
    if "SIDE" in c:
        return "sidelite"
    return "SD"


def get_or_create_attribute(name, create_variant="no_variant"):
    attr = AttrModel.search([("name", "=", name)], limit=1)
    if not attr:
        attr = AttrModel.create({"name": name, "create_variant": create_variant})
        print(f"  + created attribute: {name}")
    return attr


def get_or_create_attribute_value(attr, value):
    v = AttrValueModel.search([("attribute_id", "=", attr.id), ("name", "=", value)], limit=1)
    if not v:
        v = AttrValueModel.create({"attribute_id": attr.id, "name": value})
    return v


def load_image_b64(path):
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read())


def import_row(row, idx, total):
    raw_name = row["name"].strip()
    if not raw_name or raw_name == "ERROR":
        return None
    code = (row.get("default_code") or "").strip() or code_from_name(raw_name)
    door_type = door_type_from_code(code)

    print(f"[{idx}/{total}] {code} ({raw_name})")

    # Find or create product.template
    tmpl = ProductTemplate.search([("default_code", "=", code)], limit=1)
    if not tmpl:
        tmpl = ProductTemplate.create({
            "name": raw_name,
            "default_code": code,
            "type": "consu",
            "detailed_type": "consu",
            "sale_ok": True,
            "purchase_ok": False,
            "is_published": True,
            "is_indigo_design": True,
            "indigo_door_type": door_type,
            "list_price": 0.0,
            "description_sale": row.get("description") or "",
        })
        print(f"  + created template id={tmpl.id}")
    else:
        tmpl.write({
            "is_indigo_design": True,
            "indigo_door_type": door_type,
            "is_published": True,
        })
        print(f"  ~ updated template id={tmpl.id}")

    # Atributos
    attrs_json = row.get("attributes_json") or "{}"
    try:
        attrs = json.loads(attrs_json)
    except json.JSONDecodeError:
        attrs = {}

    # Mapear nombres del shop a un set consistente
    attr_map = {
        "Finish Color": "Finish Color",
        "Door Brand": "Door Brand",
        "Privacy Glass": "Privacy Glass",
        "Handing": "Handing",
        "Width": None,  # No es atributo, es dimension custom
        "Height": None,
    }

    for raw_name_attr, values in attrs.items():
        target = attr_map.get(raw_name_attr, raw_name_attr)
        if not target:
            continue
        # Filtrar valores invalidos (tipo "in & eights")
        clean_vals = [v.strip() for v in values if v.strip() and len(v) < 40 and not re.match(r"^\d", v)]
        if not clean_vals:
            continue
        attr = get_or_create_attribute(target)
        value_ids = [get_or_create_attribute_value(attr, v).id for v in clean_vals]
        # Crear o actualizar la linea de atributo en este template
        line = TmplLine.search([
            ("product_tmpl_id", "=", tmpl.id),
            ("attribute_id", "=", attr.id),
        ], limit=1)
        if not line:
            try:
                TmplLine.create({
                    "product_tmpl_id": tmpl.id,
                    "attribute_id": attr.id,
                    "value_ids": [(6, 0, value_ids)],
                })
            except Exception as e:
                print(f"  ! attribute line create failed for {target}: {e}")
        else:
            try:
                line.write({"value_ids": [(6, 0, value_ids)]})
            except Exception:
                pass

    # Imagenes - probar varias casings/variantes del nombre del folder
    img_dir = None
    candidates = [
        re.sub(r"[^A-Za-z0-9_-]", "_", code),
        re.sub(r"[^A-Za-z0-9_-]", "_", code).lower(),
        (row.get("url_slug") or "").strip(),
    ]
    for c in candidates:
        if not c:
            continue
        p = os.path.join(IMAGES_DIR, c)
        if os.path.isdir(p):
            img_dir = p
            break
    if img_dir:
        files = sorted([f for f in os.listdir(img_dir) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))])
        for i, fname in enumerate(files):
            path = os.path.join(img_dir, fname)
            data = load_image_b64(path)
            if not data:
                continue
            if i == 0 and not tmpl.image_1920:
                tmpl.image_1920 = data
                print(f"  img main: {fname}")
            else:
                # Imagenes adicionales via product.image
                existing = ProductImage.search([
                    ("product_tmpl_id", "=", tmpl.id),
                    ("name", "=", fname),
                ], limit=1)
                if not existing:
                    ProductImage.create({
                        "name": fname,
                        "product_tmpl_id": tmpl.id,
                        "image_1920": data,
                    })
                    print(f"  img extra: {fname}")

    # Asociar a indigo.design si existe
    design = Design.search([("code", "=", code)], limit=1)
    if design:
        tmpl.indigo_design_id = design.id
        print(f"  -> linked to indigo.design {code}")

    return tmpl


def main():
    print("=" * 60)
    print(f"Importing from {CSV_PATH}")
    print("=" * 60)
    if not os.path.isfile(CSV_PATH):
        print(f"FILE NOT FOUND: {CSV_PATH}")
        return
    with open(CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"{len(rows)} products to import\n")
    created = updated = errored = 0
    for i, row in enumerate(rows, 1):
        try:
            tmpl = import_row(row, i, len(rows))
            if tmpl:
                env.cr.commit()
                created += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            env.cr.rollback()
            errored += 1
    print(f"\n=== Done: {created} OK, {errored} errors ===")


main()
