#!/usr/bin/env python3
"""QuickBooks Online sandbox: OAuth 2.0 (authorization_code) y primeras llamadas.

Prueba de conexion antes del modulo `indigo_quickbooks`
(docs/superpowers/specs/2026-10-06-quickbooks-integration-design.md). Solo usa
endpoints documentados por Intuit:

  authorize  https://appcenter.intuit.com/connect/oauth2
  tokens     https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer
  revoke     https://developer.api.intuit.com/v2/oauth2/tokens/revoke
  userinfo   https://sandbox-accounts.platform.intuit.com/v1/openid_connect/userinfo
  QBO API    https://sandbox-quickbooks.api.intuit.com/v3/company/<realmId>/...

Secretos: QBO_CLIENT_ID y QBO_CLIENT_SECRET (y QBO_REDIRECT_URI) salen del
entorno o de `.env.qbo` en la raiz del repo (ignorado por git). Los tokens se
guardan en `.qbo-tokens.json` (ignorado por git). Nada de esto se versiona.

Uso (desde la raiz del repo):
  py tools/qbo_sandbox/qbo_sandbox.py auth-url          # abre esta URL y autoriza
  py tools/qbo_sandbox/qbo_sandbox.py exchange "<URL a la que te llevo Intuit>"
  py tools/qbo_sandbox/qbo_sandbox.py company           # CompanyInfo
  py tools/qbo_sandbox/qbo_sandbox.py userinfo          # OpenID userinfo
  py tools/qbo_sandbox/qbo_sandbox.py invoices          # ultimas facturas
  py tools/qbo_sandbox/qbo_sandbox.py customers         # clientes
  py tools/qbo_sandbox/qbo_sandbox.py items             # productos/servicios
  py tools/qbo_sandbox/qbo_sandbox.py refresh           # renovar el access token
  py tools/qbo_sandbox/qbo_sandbox.py revoke            # desconectar
"""
import base64
import json
import os
import secrets
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env.qbo"
TOKENS_FILE = ROOT / ".qbo-tokens.json"
STATE_FILE = ROOT / ".qbo-tokens.json.state"

AUTHORIZE_URL = "https://appcenter.intuit.com/connect/oauth2"
TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
REVOKE_URL = "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"
USERINFO_URL = "https://sandbox-accounts.platform.intuit.com/v1/openid_connect/userinfo"
API_BASE = "https://sandbox-quickbooks.api.intuit.com/v3/company"
# Indigo solo necesita contabilidad (facturas, clientes, cobros). Los permisos
# de QuickBooks Payments (cobrar tarjetas) no hacen falta.
SCOPES = "com.intuit.quickbooks.accounting openid profile email"
MINOR_VERSION = "75"
TIMEOUT = 30


class QboError(Exception):
    pass


# ---------------------------------------------------------------- config

def load_env():
    """Variables de entorno; si faltan, las lee de .env.qbo (KEY=VALUE)."""
    if ENV_FILE.exists():
        for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))
    missing = [k for k in ("QBO_CLIENT_ID", "QBO_CLIENT_SECRET", "QBO_REDIRECT_URI") if not os.environ.get(k)]
    if missing:
        raise QboError(
            "Faltan %s. Ponlas en %s (KEY=VALUE, una por linea) o como variables de entorno."
            % (", ".join(missing), ENV_FILE)
        )
    return os.environ["QBO_CLIENT_ID"], os.environ["QBO_CLIENT_SECRET"], os.environ["QBO_REDIRECT_URI"]


def basic_auth(client_id, client_secret):
    raw = ("%s:%s" % (client_id, client_secret)).encode()
    return "Basic " + base64.b64encode(raw).decode()


# ---------------------------------------------------------------- tokens

def save_tokens(data, realm_id=None):
    now = int(time.time())
    current = load_tokens(required=False) or {}
    current.update({
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "access_expires_at": now + int(data.get("expires_in", 3600)),
        "refresh_expires_at": now + int(data.get("x_refresh_token_expires_in", 8640000)),
    })
    if realm_id:
        current["realm_id"] = realm_id
    TOKENS_FILE.write_text(json.dumps(current, indent=1), encoding="utf-8")
    try:
        os.chmod(TOKENS_FILE, 0o600)
    except OSError:
        pass
    return current


def load_tokens(required=True):
    if not TOKENS_FILE.exists():
        if required:
            raise QboError("No hay tokens todavia: ejecuta 'auth-url' y luego 'exchange'.")
        return None
    return json.loads(TOKENS_FILE.read_text(encoding="utf-8"))


def token_request(body):
    client_id, client_secret, _ = load_env()
    resp = requests.post(
        TOKEN_URL,
        headers={
            "Authorization": basic_auth(client_id, client_secret),
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data=body,
        timeout=TIMEOUT,
    )
    if resp.status_code != 200:
        # invalid_grant = codigo usado/vencido o refresh token revocado.
        raise QboError("Intuit rechazo el token (%s): %s" % (resp.status_code, resp.text[:300]))
    return resp.json()


def refresh(force=False):
    tok = load_tokens()
    if not force and tok["access_expires_at"] - 60 > time.time():
        return tok
    if tok["refresh_expires_at"] < time.time():
        raise QboError("El refresh token vencio: vuelve a autorizar con 'auth-url'.")
    data = token_request({"grant_type": "refresh_token", "refresh_token": tok["refresh_token"]})
    # Intuit puede devolver un refresh token NUEVO: hay que guardar siempre el ultimo.
    return save_tokens(data)


# ---------------------------------------------------------------- API

def api_get(path, params=None, retry=True):
    tok = refresh()
    url = "%s/%s/%s" % (API_BASE, tok["realm_id"], path.lstrip("/"))
    query = {"minorversion": MINOR_VERSION}
    query.update(params or {})
    resp = requests.get(
        url,
        headers={"Authorization": "Bearer " + tok["access_token"], "Accept": "application/json"},
        params=query,
        timeout=TIMEOUT,
    )
    if resp.status_code == 401 and retry:
        refresh(force=True)
        return api_get(path, params, retry=False)
    if resp.status_code == 429:
        raise QboError("Limite de la API de Intuit alcanzado; espera un minuto y repite.")
    if resp.status_code >= 400:
        # intuit_tid identifica la llamada si hay que abrir un caso con Intuit.
        raise QboError("QBO %s (intuit_tid=%s): %s" % (
            resp.status_code, resp.headers.get("intuit_tid", "-"), resp.text[:500]))
    return resp.json()


def query(sql):
    return api_get("query", {"query": sql}).get("QueryResponse", {})


def api_post(path, body, params=None, retry=True):
    """POST a la API de contabilidad (crear/actualizar). Mismo manejo de
    errores que api_get: renueva el token una vez ante un 401."""
    tok = refresh()
    url = "%s/%s/%s" % (API_BASE, tok["realm_id"], path.lstrip("/"))
    query_params = {"minorversion": MINOR_VERSION}
    query_params.update(params or {})
    resp = requests.post(
        url,
        headers={
            "Authorization": "Bearer " + tok["access_token"],
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        params=query_params,
        json=body,
        timeout=TIMEOUT,
    )
    if resp.status_code == 401 and retry:
        refresh(force=True)
        return api_post(path, body, params, retry=False)
    if resp.status_code == 429:
        raise QboError("Limite de la API de Intuit alcanzado; espera un minuto y repite.")
    if resp.status_code >= 400:
        raise QboError("QBO %s (intuit_tid=%s): %s" % (
            resp.status_code, resp.headers.get("intuit_tid", "-"), resp.text[:800]))
    return resp.json()


# ---------------------------------------------------------------- comandos

def cmd_auth_url():
    client_id, _, redirect_uri = load_env()
    state = secrets.token_urlsafe(24)
    STATE_FILE.write_text(state, encoding="utf-8")
    url = AUTHORIZE_URL + "?" + urlencode({
        "client_id": client_id,
        "response_type": "code",
        "scope": SCOPES,
        "redirect_uri": redirect_uri,
        "state": state,
    })
    print("Abre esta URL, inicia sesion, elige la empresa SANDBOX y autoriza:\n")
    print(url)
    print("\nLuego copia la URL completa a la que te lleva Intuit y ejecuta:")
    print('  py tools/qbo_sandbox/qbo_sandbox.py exchange "<esa URL>"')


def cmd_exchange(redirected_url):
    _, _, redirect_uri = load_env()
    qs = parse_qs(urlparse(redirected_url).query)
    if "error" in qs:
        raise QboError("Intuit devolvio un error: %s" % qs["error"][0])
    code, realm, state = (qs.get(k, [None])[0] for k in ("code", "realmId", "state"))
    if not code or not realm:
        raise QboError("La URL no trae 'code' y 'realmId'. Copia la URL completa de la barra del navegador.")
    expected = STATE_FILE.read_text(encoding="utf-8").strip() if STATE_FILE.exists() else None
    if not expected or state != expected:
        raise QboError("El 'state' no coincide (proteccion CSRF). Genera otra URL con 'auth-url'.")
    data = token_request({"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri})
    save_tokens(data, realm_id=realm)
    STATE_FILE.unlink(missing_ok=True)
    print("Conectado. realmId=%s. Tokens guardados en %s" % (realm, TOKENS_FILE.name))


def cmd_company():
    tok = load_tokens()
    info = api_get("companyinfo/%s" % tok["realm_id"])["CompanyInfo"]
    print(json.dumps({k: info.get(k) for k in ("CompanyName", "LegalName", "Country", "CompanyAddr")}, indent=1))


def cmd_userinfo():
    tok = refresh()
    resp = requests.get(USERINFO_URL, headers={"Authorization": "Bearer " + tok["access_token"],
                                               "Accept": "application/json"}, timeout=TIMEOUT)
    if resp.status_code >= 400:
        raise QboError("userinfo %s: %s" % (resp.status_code, resp.text[:300]))
    print(json.dumps(resp.json(), indent=1))


def cmd_invoices():
    rows = query("SELECT * FROM Invoice ORDERBY MetaData.CreateTime DESC MAXRESULTS 10").get("Invoice", [])
    for inv in rows:
        print("#%s  %s  %s  total %s  saldo %s" % (
            inv.get("DocNumber"), inv.get("TxnDate"), inv.get("CustomerRef", {}).get("name"),
            inv.get("TotalAmt"), inv.get("Balance")))
    print("(%d)" % len(rows))


def cmd_customers():
    for c in query("SELECT Id, DisplayName, PrimaryEmailAddr FROM Customer MAXRESULTS 100").get("Customer", []):
        print("%s  %s  %s" % (c["Id"], c.get("DisplayName"), (c.get("PrimaryEmailAddr") or {}).get("Address", "")))


def cmd_items():
    for it in query("SELECT Id, Name, Type, UnitPrice, Taxable FROM Item MAXRESULTS 100").get("Item", []):
        print("%s  %s  [%s] %s taxable=%s" % (it["Id"], it.get("Name"), it.get("Type"), it.get("UnitPrice"), it.get("Taxable")))


def cmd_refresh():
    tok = refresh(force=True)
    print("Access token renovado; vence en %d s." % (tok["access_expires_at"] - time.time()))


def cmd_revoke():
    client_id, client_secret, _ = load_env()
    tok = load_tokens()
    resp = requests.post(REVOKE_URL, headers={
        "Authorization": basic_auth(client_id, client_secret),
        "Accept": "application/json", "Content-Type": "application/json",
    }, json={"token": tok["refresh_token"]}, timeout=TIMEOUT)
    if resp.status_code != 200:
        raise QboError("No se pudo revocar (%s): %s" % (resp.status_code, resp.text[:300]))
    TOKENS_FILE.unlink(missing_ok=True)
    print("Desconectado y tokens borrados.")


COMMANDS = {
    "auth-url": cmd_auth_url, "company": cmd_company, "userinfo": cmd_userinfo,
    "invoices": cmd_invoices, "customers": cmd_customers, "items": cmd_items,
    "refresh": cmd_refresh, "revoke": cmd_revoke,
}


def main(argv):
    if len(argv) < 2 or (argv[1] not in COMMANDS and argv[1] != "exchange"):
        print(__doc__)
        return 2
    try:
        if argv[1] == "exchange":
            if len(argv) < 3:
                raise QboError('Falta la URL: exchange "<URL a la que te llevo Intuit>"')
            cmd_exchange(argv[2])
        else:
            COMMANDS[argv[1]]()
    except QboError as e:
        print("ERROR:", e, file=sys.stderr)
        return 1
    except requests.RequestException as e:
        print("ERROR de red:", e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
