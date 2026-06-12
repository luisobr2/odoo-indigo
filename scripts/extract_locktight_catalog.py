"""
Extract Lock Tight catalog designs from the PDF.

Renders each PDF page, runs OCR on the title strip to detect codes
(format: TD-{DD|SD}-{B|W|BLK}NN), maps codes to their door images by
horizontal position, and writes:

  out/images/<CODE>.jpg     — cropped door image, ready to embed as
                               ir.attachment in indigo_decors data
  out/catalog.csv           — page, code, type, color, image_path
  out/extraction_report.md  — per-page report for manual review

After extraction, a separate script generates the Odoo XML.
"""
import fitz
import pytesseract
from PIL import Image
import re
import csv
import os
import sys
import io
from pathlib import Path

# Tesseract Windows path
pytesseract.pytesseract.tesseract_cmd = (
    r'C:\Users\User\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'
)

PDF_PATH = Path(__file__).parent.parent / 'docs' / 'archive' / 'Locktight Designs.pdf'
OUT_DIR = Path(__file__).parent.parent / 'out'
OUT_IMAGES = OUT_DIR / 'images'
CSV_PATH = OUT_DIR / 'catalog.csv'
REPORT_PATH = OUT_DIR / 'extraction_report.md'

# Color/type mapping
TYPE_MAP = {'SD': 'SD', 'DD': 'DD'}
COLOR_MAP = {'B': 'bronze', 'W': 'white', 'BLK': 'black'}

CODE_RX = re.compile(r'TD-(DD|SD)-(BLK|B|W)([O0-9lI]+)')


def normalize_code(raw: str) -> str:
    m = CODE_RX.match(raw)
    if not m:
        return raw
    door_type, color, num = m.groups()
    num = num.replace('O', '0').replace('o', '0').replace('l', '1').replace('I', '1')
    return f'TD-{door_type}-{color}{num}'


def extract_codes_with_positions(page, page_img):
    """OCR the page, return list of (code, x_center) sorted by x."""
    # OCR with bounding boxes
    data = pytesseract.image_to_data(page_img, output_type=pytesseract.Output.DICT)
    # Build code candidates from contiguous tokens on the same line that
    # look like our pattern. Tesseract often splits "TD-DD-B04" across
    # multiple tokens, so we walk lines and rejoin.
    lines = {}
    for i, txt in enumerate(data['text']):
        txt = txt.strip()
        if not txt:
            continue
        line_id = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
        lines.setdefault(line_id, []).append({
            'text': txt,
            'left': data['left'][i],
            'top': data['top'][i],
            'width': data['width'][i],
            'height': data['height'][i],
        })

    found = []
    for line_id, tokens in lines.items():
        # Join all tokens on the line into one string while tracking word boundaries
        joined = ' '.join(t['text'] for t in tokens)
        # OCR sometimes drops spaces or hyphens — be lenient
        joined_norm = joined.upper().replace(' ', '')
        for m in CODE_RX.finditer(joined_norm):
            raw = m.group(0)
            code = normalize_code(raw)
            # Estimate x position: find which token contains the start
            offset = 0
            x_center = None
            for t in tokens:
                # Re-compute joined positions
                if m.start() <= offset + len(t['text'].replace(' ', '')) - 1:
                    x_center = t['left'] + t['width'] // 2
                    break
                offset += len(t['text'].replace(' ', ''))
            if x_center is None and tokens:
                x_center = tokens[0]['left']
            found.append((code, x_center, line_id[2]))
    # Dedup by code keeping the leftmost (avoid double matches)
    seen = {}
    for code, x, line in found:
        if code not in seen or x < seen[code][0]:
            seen[code] = (x, line)
    # Sort by x position (left to right)
    return sorted([(c, x, line) for c, (x, line) in seen.items()], key=lambda t: t[1])


def extract_images_with_positions(page, page_img):
    """Return embedded images with their bounding boxes on the page."""
    page_w, page_h = page.rect.width, page.rect.height
    img_w, img_h = page_img.size
    sx = img_w / page_w
    sy = img_h / page_h
    results = []
    for img_info in page.get_image_info(xrefs=True):
        bbox = img_info['bbox']
        x_center = (bbox[0] + bbox[2]) / 2 * sx
        y_top = bbox[1] * sy
        # Filter out very small images (logos < 30k pixels²)
        w = (bbox[2] - bbox[0]) * sx
        h = (bbox[3] - bbox[1]) * sy
        if w < 80 or h < 80:
            continue
        # Filter logos at top of page (header strip)
        if y_top < img_h * 0.10:
            continue
        results.append({
            'xref': img_info['xref'],
            'x_center': x_center,
            'bbox_pdf': bbox,
            'bbox_img': (bbox[0] * sx, bbox[1] * sy, bbox[2] * sx, bbox[3] * sy),
        })
    return sorted(results, key=lambda r: r['x_center'])


def main():
    OUT_DIR.mkdir(exist_ok=True)
    OUT_IMAGES.mkdir(exist_ok=True)
    doc = fitz.open(str(PDF_PATH))
    rows = []
    report_lines = ['# Lock Tight Catalog Extraction Report', '']
    total_codes = 0
    total_mismatch = 0
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        pix = page.get_pixmap(dpi=150)
        page_img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
        codes = extract_codes_with_positions(page, page_img)
        images = extract_images_with_positions(page, page_img)
        if not codes and not images:
            report_lines.append(f'## Page {page_idx + 1}: skip (cover/legend page)')
            continue
        # Match each code to closest image by x position
        report_lines.append(
            f'## Page {page_idx + 1}: {len(codes)} codes / {len(images)} images'
        )
        if len(codes) != len(images):
            total_mismatch += 1
            report_lines.append(f'  ⚠ count mismatch')
        for code, x, _ in codes:
            # Find closest image by x
            if images:
                nearest = min(images, key=lambda im: abs(im['x_center'] - x))
                # Crop the door image
                bbox = nearest['bbox_img']
                cropped = page_img.crop((int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])))
                img_path = OUT_IMAGES / f'{code}.jpg'
                cropped.save(img_path, 'JPEG', quality=85)
                door_type = code.split('-')[1]  # DD or SD
                color_key = code.split('-')[2][:3] if code.split('-')[2].startswith('BLK') else code.split('-')[2][:1]
                color = COLOR_MAP.get(color_key, '')
                rows.append({
                    'page': page_idx + 1,
                    'code': code,
                    'door_type': door_type,
                    'color': color,
                    'image_path': str(img_path.relative_to(OUT_DIR)),
                })
                report_lines.append(f'  ✓ {code} → {img_path.name}')
                total_codes += 1

    # Write CSV
    with CSV_PATH.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['page', 'code', 'door_type', 'color', 'image_path'])
        writer.writeheader()
        writer.writerows(rows)

    # Write report
    report_lines.insert(2, f'Total codes extracted: **{total_codes}**')
    report_lines.insert(3, f'Pages with count mismatch: **{total_mismatch}**')
    report_lines.insert(4, '')
    REPORT_PATH.write_text('\n'.join(report_lines), encoding='utf-8')

    doc.close()
    print(f'Done. {total_codes} codes extracted to {CSV_PATH}')
    print(f'  Images: {OUT_IMAGES}')
    print(f'  Report: {REPORT_PATH}')


if __name__ == '__main__':
    main()
