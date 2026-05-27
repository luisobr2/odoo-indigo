"""
Sube las imagenes por color scrapeadas (scraping/output/variant_images/<CODE>/<color>.jpg)
a los product.product variants correspondientes en Odoo prod via Odoo shell (SSH).

Pre-requisito: ya se ejecuto SQL para cambiar product_attribute.create_variant='always'
en Finish Color, y se llamo _create_variant_ids() en cada template afectado.

Estrategia:
    1. Genera un script Python que se ejecuta DENTRO del odoo container via
       `docker exec odoo odoo shell` (stdin).
    2. El script recibe el directorio scraping/output/variant_images/ subido via
       `docker cp` a /tmp/variant_images/ en el container.
    3. Itera /tmp/variant_images/<CODE>/<color>.jpg, busca el variant que matchea
       (default_code=CODE + Finish Color value=color) y le asigna image_variant_1920.

Uso:
    python scripts/import_variant_images.py
        --ssh-host 2.25.137.220
        --ssh-pass 820415Indigo+
        --container odoo-f57xxcgj6dph9nkrvekz91h6-XXXXX
        --db indigo-prod
"""
import argparse
import base64
import csv
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "scraping" / "output" / "variant_images"
CSV_PATH = ROOT / "scraping" / "output" / "variant_images.csv"


def ssh_run(client, cmd, timeout=300):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout, get_pty=False)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    rc = stdout.channel.recv_exit_status()
    return rc, out, err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ssh-host", default="2.25.137.220")
    ap.add_argument("--ssh-user", default="root")
    ap.add_argument("--ssh-pass", required=True)
    ap.add_argument("--db", default="indigo-prod")
    args = ap.parse_args()

    if not CSV_PATH.exists():
        print(f"!! CSV not found: {CSV_PATH}  — run scrape first")
        sys.exit(1)

    # Read CSV to know what we will upload
    rows = []
    with open(CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"CSV has {len(rows)} variant images")

    # Connect SSH
    print(f"Connecting to {args.ssh_user}@{args.ssh_host}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(args.ssh_host, username=args.ssh_user, password=args.ssh_pass,
                   timeout=15, look_for_keys=False, allow_agent=False)

    # Find odoo container
    rc, out, err = ssh_run(client, "docker ps --format '{{.Names}}' | grep '^odoo-' | head -1")
    container = out.strip()
    if not container:
        print(f"!! No odoo container found:\n{err}")
        sys.exit(1)
    print(f"Container: {container}")

    # Build a tarball with all variant images and ship it
    print(f"Packing {SRC_DIR} into tarball...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tar_local = Path(tmpdir) / "variant_images.tar.gz"
        # Use tar from git-bash / mingw
        subprocess.run(["tar", "czf", str(tar_local), "-C", str(SRC_DIR.parent), SRC_DIR.name],
                       check=True)
        size = tar_local.stat().st_size
        print(f"  tarball: {size//1024} KB")

        # SCP to /tmp/ on VPS
        sftp = client.open_sftp()
        remote_tar = "/tmp/variant_images.tar.gz"
        print(f"Uploading to VPS {remote_tar}...")
        sftp.put(str(tar_local), remote_tar)
        sftp.close()

    # Extract + docker cp into container
    print("Extracting on VPS...")
    ssh_run(client, "rm -rf /tmp/variant_images && mkdir -p /tmp/variant_images")
    rc, out, err = ssh_run(client,
        "tar xzf /tmp/variant_images.tar.gz -C /tmp/ && ls /tmp/variant_images | head -5 && echo TOTAL_DIRS=$(ls /tmp/variant_images | wc -l)")
    print(out)
    if rc != 0:
        print(f"!! tar error:\n{err}")
        sys.exit(1)

    print(f"Copying to container...")
    rc, out, err = ssh_run(client, f"docker cp /tmp/variant_images {container}:/tmp/variant_images")
    if rc != 0:
        print(f"!! docker cp error:\n{err}")
        sys.exit(1)

    # Write the Odoo shell python script
    shell_script = '''
import os, base64, glob
env = self.env
finish_attr = env['product.attribute'].search([('name', '=', 'Finish Color')], limit=1)
print('Finish Color attribute:', finish_attr.id, finish_attr.create_variant)
if finish_attr.create_variant != 'always':
    print('!! Finish Color is not create_variant=always; flipping now...')
    finish_attr.create_variant = 'always'

# Trigger variant materialization on every product.template that has Finish Color
templates_with_color = env['product.template'].search([
    ('attribute_line_ids.attribute_id', '=', finish_attr.id),
])
print(f'Templates with Finish Color: {len(templates_with_color)}')
for t in templates_with_color:
    t._create_variant_ids()
env.cr.commit()

base_dir = '/tmp/variant_images'
if not os.path.isdir(base_dir):
    raise Exception(f'{base_dir} not found inside container')

color_to_value = {}
for v in env['product.attribute.value'].search([('attribute_id', '=', finish_attr.id)]):
    color_to_value[v.name.lower()] = v

uploaded = 0
missing_variant = 0
missing_file = 0
for code_dir in sorted(os.listdir(base_dir)):
    full = os.path.join(base_dir, code_dir)
    if not os.path.isdir(full):
        continue
    tmpl = env['product.template'].search([('default_code', '=', code_dir)], limit=1)
    if not tmpl:
        tmpl = env['product.template'].search([('name', '=', code_dir)], limit=1)
    if not tmpl:
        tmpl = env['product.template'].search([('name', '=ilike', code_dir)], limit=1)
    if not tmpl:
        print(f'  !! template not found for code {code_dir}')
        continue
    for fname in os.listdir(full):
        color_key = os.path.splitext(fname)[0].lower()
        pav_value = color_to_value.get(color_key)
        if not pav_value:
            print(f'  - {code_dir}/{fname}: no product.attribute.value matches {color_key}')
            continue
        # Find the variant of this template with that PAV
        variant = env['product.product'].search([
            ('product_tmpl_id', '=', tmpl.id),
            ('product_template_attribute_value_ids.product_attribute_value_id', '=', pav_value.id),
        ], limit=1)
        if not variant:
            print(f'  - {code_dir}/{fname}: no variant matches color {color_key}')
            missing_variant += 1
            continue
        try:
            with open(os.path.join(full, fname), 'rb') as f:
                b64 = base64.b64encode(f.read())
            variant.image_variant_1920 = b64
            uploaded += 1
        except Exception as e:
            print(f'  !! {code_dir}/{fname}: write failed: {e}')
env.cr.commit()
print(f'=== uploaded={uploaded} missing_variant={missing_variant} missing_file={missing_file} ===')
'''
    remote_script = "/tmp/upload_variant_images.py"
    sftp = client.open_sftp()
    with sftp.file(remote_script, "w") as f:
        f.write(shell_script)
    sftp.close()
    ssh_run(client, f"docker cp {remote_script} {container}:/tmp/upload_variant_images.py")

    # Run via odoo shell — pipe the script through stdin
    print("Running upload via odoo shell (may take 1-2 min)...")
    cmd = (
        f"docker exec -i {container} bash -c "
        f"\"odoo shell -c /etc/odoo/odoo.conf -d {args.db} --no-http "
        f"< /tmp/upload_variant_images.py 2>&1 | tail -40\""
    )
    rc, out, err = ssh_run(client, cmd, timeout=600)
    print(out)
    if err:
        print("STDERR:", err)

    print("Restarting container so the registry picks up changes...")
    ssh_run(client, f"docker restart {container}")
    print("Done.")

    client.close()


if __name__ == "__main__":
    main()
