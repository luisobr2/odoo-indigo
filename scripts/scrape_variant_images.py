"""
Scrape variant images por color desde indigodecors.com usando Playwright.

Visita cada PDP, clickea cada radio Black/White/Bronze y captura la URL del
main image variant. Luego descarga via requests (más rápido que Playwright).

Output:
    scraping/output/variant_images/<code>/<color>.jpg
    scraping/output/variant_images.csv

Uso:
    python scripts/scrape_variant_images.py            # full (142 productos)
    python scripts/scrape_variant_images.py --limit 5  # primeros 5 (test)
    python scripts/scrape_variant_images.py --code ID01-DD  # solo uno
"""
import argparse
import csv
import re
import sys
import time
import urllib.parse
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

BASE = "https://www.indigodecors.com"
OUT = Path(__file__).resolve().parent.parent / "scraping" / "output" / "variant_images"
CSV_OUT = Path(__file__).resolve().parent.parent / "scraping" / "output" / "variant_images.csv"
COLORS = ["Black", "White", "Bronze"]
HEADERS = {"User-Agent": "Mozilla/5.0 (Indigo Migration Bot - variant image sync)"}

dl_session = requests.Session()
dl_session.headers.update(HEADERS)


def slug_to_code(slug):
    m = re.match(r"^([a-z0-9\-]+?)-\d+$", slug)
    return (m.group(1) if m else slug).upper()


def discover_products(page, max_pages=20):
    print("Discovering products...")
    seen = set()
    for n in range(1, max_pages + 1):
        url = f"{BASE}/shop?page={n}" if n > 1 else f"{BASE}/shop"
        page.goto(url, wait_until="domcontentloaded")
        page_links = set()
        for a in page.query_selector_all('a[href*="/shop/"]'):
            href = a.get_attribute("href") or ""
            m = re.match(r"^/shop/([a-z0-9\-]+-\d+)$", href)
            if m:
                page_links.add(m.group(1))
        new = page_links - seen
        if not new:
            print(f"  page {n}: no new products, stopping")
            break
        seen.update(new)
        print(f"  page {n}: +{len(new)} (total {len(seen)})")
    return sorted(seen)


def scrape_product(page, slug):
    code = slug_to_code(slug)
    url = f"{BASE}/shop/{slug}"
    print(f"\n[{code}] {url}")
    page.goto(url, wait_until="domcontentloaded")
    # Wait for the variant initialization JS to settle
    page.wait_for_selector('input[type="radio"][data-attribute-name="Finish Color"]', timeout=10000)

    # Collect available colors
    color_radios = {}
    for r in page.query_selector_all('input[type="radio"][data-attribute-name="Finish Color"]'):
        name = r.get_attribute("data-value-name")
        if name:
            color_radios[name] = r
    if not color_radios:
        print(f"  ! no Finish Color radios, skipping")
        return []

    rows = []
    code_dir = OUT / code
    code_dir.mkdir(parents=True, exist_ok=True)

    for color in COLORS:
        if color not in color_radios:
            print(f"  - {color}: not available")
            continue
        try:
            color_radios[color].click()
        except Exception as e:
            print(f"  ! click {color} failed: {e}")
            continue
        # Wait for image swap (the unique= query string changes)
        page.wait_for_function(
            "(c) => { const img = document.querySelector('#o-carousel-product .item.active img') || document.querySelector('#o-carousel-product img'); return img && img.src && img.src.toLowerCase().includes(c); }",
            arg=color.lower(),
            timeout=8000,
        )
        img = page.query_selector('#o-carousel-product .item.active img') or page.query_selector('#o-carousel-product img')
        img_url = img.get_attribute("src") if img else None
        if not img_url:
            print(f"  ! {color}: no image")
            continue
        if img_url.startswith("/"):
            img_url = urllib.parse.urljoin(BASE, img_url)

        # Download
        try:
            r = dl_session.get(img_url, timeout=30)
            r.raise_for_status()
        except Exception as e:
            print(f"  ! {color}: download failed: {e}")
            continue
        out_path = code_dir / f"{color.lower()}.jpg"
        out_path.write_bytes(r.content)
        print(f"  + {color}: {len(r.content)//1024} KB  {img_url[-80:]}")
        rows.append({"code": code, "color": color, "image_url": img_url, "file": str(out_path.relative_to(OUT.parent.parent.parent))})

    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--code", type=str, default=None)
    ap.add_argument("--pages", type=int, default=20)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=HEADERS["User-Agent"])
        page = ctx.new_page()

        slugs = discover_products(page, max_pages=args.pages)
        print(f"\nFound {len(slugs)} products")
        if args.code:
            slugs = [s for s in slugs if slug_to_code(s).upper() == args.code.upper()]
            print(f"Filtered to {len(slugs)} matching --code")
        elif args.limit:
            slugs = slugs[:args.limit]

        all_rows = []
        t0 = time.time()
        for i, slug in enumerate(slugs, 1):
            elapsed = time.time() - t0
            avg = elapsed / max(1, i - 1) if i > 1 else 0
            eta = avg * (len(slugs) - i + 1)
            print(f"\n=== [{i}/{len(slugs)}] {slug}  elapsed={elapsed:.0f}s  eta={eta:.0f}s ===")
            try:
                rows = scrape_product(page, slug)
                all_rows.extend(rows)
            except Exception as e:
                print(f"  !! error: {e}")

        browser.close()

    if all_rows:
        with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["code", "color", "image_url", "file"])
            w.writeheader()
            w.writerows(all_rows)
        print(f"\n=== Done ===\n  Products: {len(slugs)}\n  Images: {len(all_rows)}\n  CSV: {CSV_OUT}")
    else:
        print("\nNo images saved.")


if __name__ == "__main__":
    main()
