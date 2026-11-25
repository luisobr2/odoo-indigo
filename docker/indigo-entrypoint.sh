#!/bin/bash
# Arranque del contenedor de Odoo de Indigo (25-nov-2026).
#
# La contrasena maestra NO va en config/odoo.conf: el repo es publico y ya
# estuvo publicada. En produccion llega como secreto de Coolify en la variable
# ODOO_ADMIN_PASSWD y se escribe aqui, dentro del contenedor, en cada arranque.
# En desarrollo local la variable no existe y config/ va montado de solo
# lectura: no se toca nada.
#
# Despues sigue el arranque normal de la imagen oficial (/entrypoint.sh).
set -e

CONF=/etc/odoo/odoo.conf
if [ -n "${ODOO_ADMIN_PASSWD:-}" ] && [ -w "$CONF" ]; then
  python3 - "$CONF" <<'PY'
import os, re, sys
path = sys.argv[1]
line = "admin_passwd = " + os.environ["ODOO_ADMIN_PASSWD"]
text = open(path, encoding="utf-8").read()
pattern = re.compile(r"^\s*admin_passwd\s*=.*$", re.M)
if pattern.search(text):
    text = pattern.sub(lambda _m: line, text, count=1)
else:
    text = text.replace("[options]", "[options]\n" + line, 1)
open(path, "w", encoding="utf-8").write(text)
PY
fi

exec /entrypoint.sh "$@"
