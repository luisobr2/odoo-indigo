"""
Load Lock Tight catalog into Odoo via JSON-RPC.

For each row in out/catalog.csv:
  1. Upsert an `indigo.design` record (matched by `code`) with
     code, name, door_type, description, allowed_colors, catalog_source='locktight'.
  2. Upload the cropped door image as an `ir.attachment` linked to the design,
     ONLY if no image attachment already exists for it (so re-runs are safe).

Also retro-tags existing designs:
  - CUSTOM-* → catalog_source='custom'
  - everything else (ID##) keeps the default 'indigo'

Auth: lbencomo94@gmail.com / indigo123 (with majela@indigodecors.com fallback).
Targets prod (2.25.137.220:8069).
"""
import argparse
import base64
import csv
import sys
from pathlib import Path
import requests

ODOO_URL = 'http://2.25.137.220:8069'
DB = 'indigo-prod'

ROOT = Path(__file__).parent.parent
CSV_PATH = ROOT / 'out' / 'catalog.csv'
IMAGES_DIR = ROOT / 'out' / 'images'

# Map color code in TD-{DD|SD}-{B|W|BLK}NN → indigo color token.
COLOR_NAME = {'bronze': 'Bronze', 'white': 'White', 'black': 'Black'}
TYPE_NAME = {'DD': 'Double Door', 'SD': 'Single Door'}


def rpc(session, endpoint, params):
    r = session.post(
        f'{ODOO_URL}{endpoint}',
        json={'jsonrpc': '2.0', 'method': 'call', 'params': params},
        timeout=120,
    )
    r.raise_for_status()
    payload = r.json()
    if 'error' in payload:
        raise RuntimeError(f'Odoo error: {payload["error"]}')
    return payload.get('result')


def call_kw(session, model, method, args, kwargs=None):
    return rpc(session, '/web/dataset/call_kw', {
        'model': model,
        'method': method,
        'args': args,
        'kwargs': kwargs or {},
    })


def authenticate(session):
    """Try a list of credential candidates, return uid on first success."""
    candidates = [
        ('lbencomo94@gmail.com', 'indigo123'),
        ('majela@indigodecors.com', 'indigo123'),
    ]
    for login, pw in candidates:
        try:
            result = rpc(session, '/web/session/authenticate', {
                'db': DB,
                'login': login,
                'password': pw,
            })
            if result and result.get('uid'):
                print(f'Authenticated as {login} (uid={result["uid"]})')
                return result['uid']
        except Exception as e:
            print(f'  Auth attempt {login}: {e}')
    raise RuntimeError('All auth candidates failed.')


def backfill_catalog_source(session):
    """Mark CUSTOM-* designs as 'custom'. Everything else keeps the Odoo
    field default ('indigo'). Idempotent — re-running is a no-op."""
    custom = call_kw(session, 'indigo.design', 'search',
                     [[('code', 'ilike', 'CUSTOM%')]])
    if custom:
        call_kw(session, 'indigo.design', 'write',
                [custom, {'catalog_source': 'custom'}])
        print(f'  Tagged {len(custom)} CUSTOM-* designs as catalog_source=custom')

    # Make sure existing designs without a source get the indigo default. Odoo
    # doesn't always backfill defaults on field add — we patch any nulls.
    untagged = call_kw(
        session, 'indigo.design', 'search',
        [[('catalog_source', '=', False), ('code', 'not ilike', 'CUSTOM%')]],
    )
    if untagged:
        call_kw(session, 'indigo.design', 'write',
                [untagged, {'catalog_source': 'indigo'}])
        print(f'  Tagged {len(untagged)} remaining designs as catalog_source=indigo')


def build_design_vals(code: str, door_type: str, color: str) -> dict:
    """Build the field values for a Lock Tight indigo.design record."""
    type_label = TYPE_NAME.get(door_type, door_type)
    color_label = COLOR_NAME.get(color, color.title())
    # Numeric suffix after color code (e.g. TD-DD-B04 → 04)
    suffix = code.rsplit('-', 1)[-1].lstrip('BLKWB')  # strip color prefix
    return {
        'code': code,
        'name': f'Lock Tight {door_type} {color_label} #{suffix}',
        'door_type': door_type,
        'allowed_colors': color,
        'description': (
            f'Lock Tight Impact Doors catalog. {type_label}, {color_label} finish, '
            f'code {code}.'
        ),
        'catalog_source': 'locktight',
        'active': True,
    }


def upsert_design(session, code, vals):
    """Create-or-update a design by code. Returns the id."""
    existing = call_kw(
        session, 'indigo.design', 'search_read',
        [[('code', '=', code)]],
        {'fields': ['id', 'name', 'catalog_source'], 'limit': 1},
    )
    if existing:
        design_id = existing[0]['id']
        # Only patch fields the loader is authoritative for (don't stomp
        # name if Majela already renamed it manually).
        patch = {
            'door_type': vals['door_type'],
            'allowed_colors': vals['allowed_colors'],
            'catalog_source': vals['catalog_source'],
            'active': True,
        }
        if not existing[0].get('name'):
            patch['name'] = vals['name']
        call_kw(session, 'indigo.design', 'write', [[design_id], patch])
        return design_id, 'updated'
    return call_kw(session, 'indigo.design', 'create', [vals]), 'created'


def ensure_image_attachment(session, design_id, img_path: Path):
    """Upload the image IF the design has no image attachment yet."""
    existing = call_kw(
        session, 'ir.attachment', 'search_count',
        [[
            ('res_model', '=', 'indigo.design'),
            ('res_id', '=', design_id),
            ('mimetype', 'ilike', 'image/%'),
        ]],
    )
    if existing:
        return 'skipped'
    if not img_path.exists():
        return 'missing'
    data_b64 = base64.b64encode(img_path.read_bytes()).decode()
    call_kw(
        session, 'ir.attachment', 'create',
        [{
            'name': img_path.name,
            'res_model': 'indigo.design',
            'res_id': design_id,
            'type': 'binary',
            'mimetype': 'image/jpeg',
            'datas': data_b64,
        }],
    )
    return 'uploaded'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--limit', type=int, default=0,
        help='Only process the first N rows (0 = all). Use 6 for the test batch.',
    )
    parser.add_argument(
        '--codes', type=str, default='',
        help='Comma-separated list of codes to load — overrides --limit.',
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Read CSV + show what would happen, but make no Odoo writes.',
    )
    args = parser.parse_args()

    if not CSV_PATH.exists():
        print(f'Missing {CSV_PATH}. Run extract_locktight_catalog.py first.',
              file=sys.stderr)
        sys.exit(1)

    rows = list(csv.DictReader(CSV_PATH.open(encoding='utf-8')))
    if args.codes:
        wanted = {c.strip() for c in args.codes.split(',') if c.strip()}
        rows = [r for r in rows if r['code'] in wanted]
    elif args.limit:
        rows = rows[:args.limit]
    print(f'Processing {len(rows)} catalog rows…')

    if args.dry_run:
        for r in rows[:10]:
            vals = build_design_vals(r['code'], r['door_type'], r['color'])
            print(f'  Would upsert {vals["code"]} → {vals["name"]} '
                  f'(allowed_colors={vals["allowed_colors"]}, '
                  f'source={vals["catalog_source"]})')
        if len(rows) > 10:
            print(f'  … and {len(rows) - 10} more')
        return

    session = requests.Session()
    authenticate(session)

    print('\n=== Backfilling catalog_source on existing designs ===')
    backfill_catalog_source(session)

    print('\n=== Loading Lock Tight designs ===')
    created = updated = uploaded = skipped = missing = 0
    errors = []
    for i, row in enumerate(rows, 1):
        code = row['code']
        try:
            vals = build_design_vals(code, row['door_type'], row['color'])
            design_id, action = upsert_design(session, code, vals)
            if action == 'created':
                created += 1
            else:
                updated += 1
            img_path = ROOT / 'out' / row['image_path'].replace('\\', '/')
            att_action = ensure_image_attachment(session, design_id, img_path)
            if att_action == 'uploaded':
                uploaded += 1
            elif att_action == 'skipped':
                skipped += 1
            else:
                missing += 1
                errors.append(f'{code}: image missing at {img_path}')
        except Exception as e:
            errors.append(f'{code}: {e}')

        if i % 25 == 0:
            print(f'  [{i:>3}/{len(rows)}] '
                  f'created={created} updated={updated} '
                  f'uploaded={uploaded} skipped={skipped} '
                  f'errors={len(errors)}')

    print()
    print('=== Summary ===')
    print(f'  Created designs:    {created}')
    print(f'  Updated designs:    {updated}')
    print(f'  Uploaded images:    {uploaded}')
    print(f'  Skipped images:     {skipped}')
    print(f'  Missing images:     {missing}')
    print(f'  Errors:             {len(errors)}')
    if errors:
        print('  First 10 errors:')
        for e in errors[:10]:
            print(f'    {e}')


if __name__ == '__main__':
    main()
