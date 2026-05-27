# -*- coding: utf-8 -*-
"""
Scraper de indigodecors.com -> products.csv + carpeta de imagenes.

Output:
    scraping/output/products.csv      (1 fila por producto, todos los atributos)
    scraping/output/variants.csv      (1 fila por combinacion color+brand)
    scraping/output/images/<code>/*   (todas las imagenes del producto)
    scraping/output/raw/<slug>.html   (HTML crudo para debug)

Uso:
    python scripts/scrape_indigo.py            # full
    python scripts/scrape_indigo.py --limit 3  # solo primeros 3 (test)
    python scripts/scrape_indigo.py --pages 1  # solo pagina 1 del shop
"""
import os
import re
import csv
import json
import time
import argparse
import urllib.parse
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://www.indigodecors.com"
SHOP_PATH = "/shop"
OUT = Path(__file__).resolve().parent.parent / "scraping" / "output"
DELAY = 1.0  # segundos entre requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Migration Bot - indigo_decors module)",
    "Accept-Language": "en,es;q=0.8",
}

session = requests.Session()
session.headers.update(HEADERS)


def fetch(url, retries=3):
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            time.sleep(DELAY)
            return r
        except Exception as e:
            print(f"  ! retry {attempt+1}: {e}")
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Failed: {url}")


def absurl(href):
    if not href:
        return ""
    if href.startswith("http"):
        return href
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return BASE + href
    return urllib.parse.urljoin(BASE, href)


def get_product_urls(max_pages=None):
    urls = []
    seen = set()
    page = 1
    while True:
        if max_pages and page > max_pages:
            break
        path = f"{SHOP_PATH}/page/{page}" if page > 1 else SHOP_PATH
        url = f"{BASE}{path}"
        print(f"[shop] page {page}: {url}")
        r = fetch(url)
        soup = BeautifulSoup(r.text, "html.parser")
        # Productos: anchors a /shop/<slug>-<id>
        found_this_page = 0
        for a in soup.select('a[href*="/shop/"]'):
            href = a.get("href") or ""
            # Filter out pagination + category links
            if not re.search(r"/shop/[a-z0-9-]+-\d+($|\?)", href):
                continue
            full = absurl(href.split("?")[0])
            if full not in seen:
                seen.add(full)
                urls.append(full)
                found_this_page += 1
        print(f"  found {found_this_page} new products (total {len(urls)})")
        if found_this_page == 0:
            break
        page += 1
    return urls


def parse_product(url):
    r = fetch(url)
    html = r.text
    soup = BeautifulSoup(html, "html.parser")

    data = {"url": url}

    # Title
    h1 = soup.select_one('h1[itemprop="name"], #product_details h1, h1.product_name, h1')
    data["name"] = h1.get_text(strip=True) if h1 else ""

    # Internal code (Odoo lo pone como <span class="o_default_code"> o en breadcrumb)
    code_el = soup.select_one('.o_default_code, span[itemprop="sku"]')
    data["default_code"] = code_el.get_text(strip=True) if code_el else ""
    if not data["default_code"]:
        # Try to extract from URL
        m = re.search(r"/shop/([a-z0-9-]+)-(\d+)$", url)
        if m:
            data["url_slug"] = m.group(1)
            data["product_id"] = m.group(2)

    # Price
    price = soup.select_one(".oe_currency_value, .product_price .oe_price")
    data["list_price"] = price.get_text(strip=True) if price else ""

    # Description
    desc = soup.select_one("#product_full_description, .product_description, #product_details .description")
    data["description"] = desc.get_text(" ", strip=True) if desc else ""

    # Breadcrumb -> categoria
    bc = soup.select(".breadcrumb a, nav[aria-label='breadcrumb'] a")
    data["categories"] = " > ".join(a.get_text(strip=True) for a in bc[1:-1]) if len(bc) > 2 else ""

    # Attributes basados en .attribute_name + siblings de variant box
    attributes = {}
    for an in soup.select(".attribute_name"):
        name = an.get_text(strip=True).rstrip(":")
        nxt = an.find_next_sibling()
        if not nxt:
            continue
        vals = []
        # 1) Inputs con data-value_name
        for inp in nxt.select("input[data-value_name]"):
            v = inp.get("data-value_name")
            if v and v not in vals:
                vals.append(v)
        # 2) Options en select
        for opt in nxt.select("option"):
            t = opt.get_text(strip=True)
            if t and t not in vals and len(t) < 60:
                vals.append(t)
        # 3) Labels (para Yes/No toggles)
        if not vals:
            for lab in nxt.select("label"):
                t = lab.get_text(strip=True)
                if t and t not in vals and len(t) < 40:
                    vals.append(t)
        if name and vals:
            attributes[name] = vals
    data["attributes_json"] = json.dumps(attributes, ensure_ascii=False)

    # Images: tomar las de mayor resolucion por record (1920 > 1024 > 512)
    images = []
    img_pattern = re.compile(
        r"/web/image/product\.(product|template)/(\d+)/image_(\d+)(?:/[^\"'\s>?]+)?"
    )
    matches = img_pattern.findall(r.text)
    # Agrupar por (model, rec_id) -> mejor resolucion disponible
    by_key = {}
    for model, rec_id, res in matches:
        key = (model, rec_id)
        cur = by_key.get(key, ("0", ""))
        if int(res) > int(cur[0]):
            # Reconstruir URL completa (con filename si lo tiene)
            m2 = re.search(
                rf"/web/image/product\.{model}/{rec_id}/image_{res}(?:/[^\"'\s>?]+)?",
                r.text,
            )
            by_key[key] = (res, m2.group(0) if m2 else f"/web/image/product.{model}/{rec_id}/image_{res}")
    # Preferir product.product (variantes) sobre product.template
    products = [u for (m, _), (_, u) in by_key.items() if m == "product"]
    templates = [u for (m, _), (_, u) in by_key.items() if m == "template"]
    images = products + templates
    images = [absurl(u) for u in images]
    data["image_urls"] = images

    return data


def download_images(urls, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    saved = []
    for i, url in enumerate(urls):
        ext = ".jpg"
        if ".png" in url.lower():
            ext = ".png"
        elif ".webp" in url.lower():
            ext = ".webp"
        path = outdir / f"{i+1:02d}{ext}"
        if path.exists() and path.stat().st_size > 1000:
            saved.append(str(path))
            continue
        try:
            r = session.get(url, timeout=60)
            r.raise_for_status()
            path.write_bytes(r.content)
            saved.append(str(path))
            print(f"    img {i+1}: {len(r.content)//1024}KB")
            time.sleep(0.3)
        except Exception as e:
            print(f"    ! img {i+1} failed: {e}")
    return saved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Limitar a N productos (test)")
    parser.add_argument("--pages", type=int, default=None, help="Limitar a N paginas del shop")
    parser.add_argument("--skip-images", action="store_true", help="No descargar imagenes (solo CSV)")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "raw").mkdir(exist_ok=True)
    (OUT / "images").mkdir(exist_ok=True)

    print("=" * 60)
    print("Scraping indigodecors.com")
    print("=" * 60)

    urls = get_product_urls(max_pages=args.pages)
    print(f"\n{len(urls)} product URLs discovered\n")
    if args.limit:
        urls = urls[: args.limit]
        print(f"Limited to {len(urls)} products for test\n")

    rows = []
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}")
        try:
            data = parse_product(url)
            code = data.get("default_code") or data.get("url_slug") or f"product-{i}"
            code = re.sub(r"[^A-Za-z0-9_-]", "_", code)
            # Download images
            if not args.skip_images and data["image_urls"]:
                saved = download_images(data["image_urls"], OUT / "images" / code)
                data["image_files"] = ";".join(saved)
            else:
                data["image_files"] = ""
            data["num_images"] = len(data["image_urls"])
            data["image_urls"] = ";".join(data["image_urls"])
            print(f"  name: {data['name']}")
            print(f"  code: {data['default_code']}")
            print(f"  attributes: {data['attributes_json']}")
            print(f"  images: {data['num_images']}")
            rows.append(data)
        except Exception as e:
            print(f"  ERROR: {e}")
            rows.append({"url": url, "name": "ERROR", "default_code": "", "error": str(e)})

    # Save CSV
    csv_path = OUT / "products.csv"
    if rows:
        fields = [
            "default_code", "name", "list_price", "description",
            "categories", "attributes_json", "num_images", "image_urls",
            "image_files", "url", "url_slug", "product_id", "error",
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            for row in rows:
                w.writerow(row)
        print(f"\nSaved {csv_path} ({len(rows)} rows)")

    print("\nDone.")


if __name__ == "__main__":
    main()
