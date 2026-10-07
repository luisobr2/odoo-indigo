# -*- coding: utf-8 -*-
"""Cliente de la API de QuickBooks Online (Accounting v3).

Conserva los tokens OAuth en `ir.config_parameter` (prefijo `indigo_qbo.`),
renueva el access token cuando va a vencer y traduce los errores de Intuit a
un `QboError` con un `code` que el resto del modulo sabe tratar:

  not_configured  faltan las claves de la app de Intuit
  not_connected   nadie ha conectado la empresa (o se desconecto)
  auth            Intuit rechazo el refresh token: hay que reconectar
  rate_limit      429 de Intuit
  api             error de la API (lleva el mensaje de Intuit y el intuit_tid)
  network         sin respuesta
  mapping         falta una equivalencia (lo lanza el envio de facturas)

SOLO PARA USO INTERNO: tiene los tokens de la empresa. Cada metodo publico
exige superusuario (`.sudo()`), porque los metodos sin `_` de un modelo se
pueden llamar por RPC con cualquier sesion, portal incluido.

Las claves de la app (client id / secret) salen del entorno del contenedor;
para desarrollo local tambien se aceptan como parametros del sistema.
Nunca se escriben en el codigo.
"""
import base64
import logging
import os
import time

import requests

from odoo import _, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import config

_logger = logging.getLogger(__name__)

PREFIX = "indigo_qbo."
AUTHORIZE_URL = "https://appcenter.intuit.com/connect/oauth2"
TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
REVOKE_URL = "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"
API_HOSTS = {
    "sandbox": "https://sandbox-quickbooks.api.intuit.com",
    "production": "https://quickbooks.api.intuit.com",
}
SCOPE = "com.intuit.quickbooks.accounting"
MINOR_VERSION = "75"
TIMEOUT = 30
TOKEN_KEYS = ("realm_id", "access_token", "refresh_token", "access_expires_at", "refresh_expires_at")
# Candado de Postgres para que dos peticiones no renueven a la vez con el
# mismo refresh token (Intuit lo rota: la segunda perderia la conexion).
REFRESH_LOCK = 0x51B0_70C0

# Lo que este proceso acaba de guardar en su propia transaccion. La transaccion
# en curso no lo ve (aislamiento de Postgres), y sin esto volveria a renovar con
# el refresh token viejo. Caduca pronto para no tapar lo que otro proceso guarde.
_RECENT = {}
_RECENT_TTL = 120


class QboError(UserError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class IndigoQboClient(models.AbstractModel):
    _name = "indigo.qbo.client"
    _description = "QuickBooks Online API client"

    def _ensure_su(self):
        if not self.env.su:
            raise AccessError(_("The QuickBooks client is internal."))

    # ------------------------------------------------------------ config

    def _setting(self, name):
        """QBO_CLIENT_ID -> entorno; si no, parametro indigo_qbo.client_id."""
        val = os.environ.get(name)
        if val:
            return val.strip()
        key = PREFIX + name[len("QBO_"):].lower()
        return (self.env["ir.config_parameter"].sudo().get_param(key) or "").strip()

    def _config(self):
        cfg = {
            "client_id": self._setting("QBO_CLIENT_ID"),
            "client_secret": self._setting("QBO_CLIENT_SECRET"),
            "redirect_uri": self._setting("QBO_REDIRECT_URI"),
            "environment": (self._setting("QBO_ENVIRONMENT") or "sandbox").lower(),
            "verifier": self._setting("QBO_WEBHOOK_VERIFIER"),
        }
        missing = [k for k in ("client_id", "client_secret", "redirect_uri") if not cfg[k]]
        if missing:
            raise QboError("not_configured", _(
                "QuickBooks isn't set up on this server yet (missing %s)."
            ) % ", ".join(missing))
        if cfg["environment"] not in API_HOSTS:
            raise QboError("not_configured", _("QBO_ENVIRONMENT must be sandbox or production."))
        return cfg

    def is_configured(self):
        self._ensure_su()
        try:
            self._config()
            return True
        except QboError:
            return False

    # ------------------------------------------------------------ params

    @staticmethod
    def _inline():
        """En las pruebas todo va en la transaccion de la prueba (se deshace)."""
        return bool(config.get("test_enable"))

    def _param(self, key, default=False):
        recent = _RECENT.get(self.env.cr.dbname)
        if recent and recent["until"] > time.time() and key in recent["vals"]:
            return recent["vals"][key] or default
        return self.env["ir.config_parameter"].sudo().get_param(PREFIX + key, default)

    def _remember(self, vals):
        entry = _RECENT.setdefault(self.env.cr.dbname, {"vals": {}, "until": 0})
        entry["vals"].update({k: ("" if v is None or v is False else str(v)) for k, v in vals.items()})
        entry["until"] = time.time() + _RECENT_TTL

    def _set_params(self, vals):
        """Guarda parametros. Fuera de las pruebas, en su propia transaccion:
        Intuit puede entregar un refresh token nuevo y, si el resto de la
        operacion falla y se deshace, perderlo dejaria la conexion rota.
        (Para lo que deba confirmarse JUNTO con otros cambios, como el cursor
        de cobros, no usar esto: escribir en la transaccion en curso.)"""
        if self._inline() or self.env.context.get("qbo_inline_params"):
            self._write_params(self.env, vals)
            return
        with self.env.registry.cursor() as cr:
            self._write_params(self.env(cr=cr), vals)
        self._remember(vals)

    @staticmethod
    def _write_params(env, vals):
        icp = env["ir.config_parameter"].sudo()
        for key, val in vals.items():
            icp.set_param(PREFIX + key, "" if val is None or val is False else str(val))

    def is_connected(self):
        self._ensure_su()
        if not (self._param("realm_id") and self._param("refresh_token")):
            return False
        expires = int(self._param("refresh_expires_at") or 0)
        return not expires or expires > time.time()

    def realm_id(self):
        self._ensure_su()
        realm = self._param("realm_id")
        if not realm or not self.is_connected():
            raise QboError("not_connected", _("QuickBooks isn't connected. A manager can connect it in Settings."))
        return realm

    @staticmethod
    def _token_vals(data, realm_id=None):
        now = int(time.time())
        try:
            vals = {
                "access_token": data["access_token"],
                "refresh_token": data["refresh_token"],
                "access_expires_at": now + int(data.get("expires_in", 3600)),
                "refresh_expires_at": now + int(data.get("x_refresh_token_expires_in", 8640000)),
            }
        except (KeyError, TypeError, ValueError):
            raise QboError("api", _("QuickBooks sent an unexpected token response."))
        if realm_id:
            vals["realm_id"] = realm_id
        return vals

    def save_tokens(self, data, realm_id=None):
        self._ensure_su()
        self._set_params(self._token_vals(data, realm_id))

    def clear_tokens(self):
        self._ensure_su()
        self._set_params({k: "" for k in TOKEN_KEYS + ("company_name",)})

    # ------------------------------------------------------------ tokens

    def _basic_auth(self, cfg):
        raw = ("%s:%s" % (cfg["client_id"], cfg["client_secret"])).encode()
        return "Basic " + base64.b64encode(raw).decode()

    def _token_request(self, body):
        """Llamada al endpoint de tokens. No toca lo guardado: decide quien llama."""
        cfg = self._config()
        try:
            resp = requests.post(
                TOKEN_URL,
                headers={
                    "Authorization": self._basic_auth(cfg),
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data=body,
                timeout=TIMEOUT,
            )
        except requests.RequestException as e:
            raise QboError("network", _("QuickBooks didn't answer: %s") % e)
        if resp.status_code != 200:
            text = resp.text or ""
            if "invalid_grant" in text:
                raise QboError("auth", _("QuickBooks needs to be connected again (the authorization expired or was revoked)."))
            raise QboError("api", _("QuickBooks refused the token request (%s): %s") % (resp.status_code, text[:300]))
        try:
            return resp.json()
        except ValueError:
            raise QboError("api", _("QuickBooks sent an unexpected token response."))

    def exchange_code(self, code, realm_id):
        self._ensure_su()
        cfg = self._config()
        data = self._token_request({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": cfg["redirect_uri"],
        })
        self.save_tokens(data, realm_id=realm_id)

    def access_token(self, force=False, failed=None):
        """Access token vigente. `force`: renovar aunque no haya vencido (tras
        un 401); `failed`: el token que dio el 401 (si otro proceso ya renovo,
        se usa el suyo en vez de renovar otra vez)."""
        self._ensure_su()
        self.realm_id()
        expires = int(self._param("access_expires_at") or 0)
        if not force and expires - 60 > time.time():
            return self._param("access_token")
        if self._inline() or self.env.context.get("qbo_inline_params"):
            return self._refresh_in(self.env, force, failed)
        with self.env.registry.cursor() as cr:
            cr.execute("SELECT pg_advisory_xact_lock(%s)", (REFRESH_LOCK,))
            token = self._refresh_in(self.env(cr=cr), force, failed)
        return token

    def _refresh_in(self, env, force, failed):
        """Renueva leyendo y escribiendo los tokens en `env` (otra transaccion,
        con el candado ya tomado, salvo en pruebas)."""
        env.cr.execute(
            "SELECT key, value FROM ir_config_parameter WHERE key IN %s",
            (tuple(PREFIX + k for k in TOKEN_KEYS),),
        )
        stored = {k[len(PREFIX):]: v for k, v in env.cr.fetchall()}
        fresh = int(stored.get("access_expires_at") or 0) - 60 > time.time()
        if stored.get("access_token") and fresh and (not force or (failed and stored["access_token"] != failed)):
            # Otro proceso ya renovo mientras esperabamos el candado.
            if env is not self.env:
                self._remember(stored)
            return stored["access_token"]
        sent = stored.get("refresh_token")
        if not sent:
            raise QboError("not_connected", _("QuickBooks isn't connected. A manager can connect it in Settings."))
        try:
            data = self._token_request({"grant_type": "refresh_token", "refresh_token": sent})
        except QboError as e:
            if e.code == "auth":
                # Solo se desconecta si lo rechazado sigue siendo lo guardado
                # (aqui siempre: se leyo con el candado tomado).
                cleared = {k: "" for k in TOKEN_KEYS + ("company_name",)}
                self._write_params(env, cleared)
                if env is not self.env:
                    env.cr.commit()
                    self._remember(cleared)
            raise
        vals = self._token_vals(data)
        self._write_params(env, vals)
        if env is not self.env:
            self._remember(vals)
        return vals["access_token"]

    def revoke(self):
        self._ensure_su()
        cfg = self._config()
        token = self._param("refresh_token")
        if token:
            try:
                requests.post(
                    REVOKE_URL,
                    headers={"Authorization": self._basic_auth(cfg), "Accept": "application/json",
                             "Content-Type": "application/json"},
                    json={"token": token},
                    timeout=TIMEOUT,
                )
            except requests.RequestException as e:
                _logger.warning("QBO revoke failed: %s", e)
        self.clear_tokens()

    # ------------------------------------------------------------ API

    def _url(self, path):
        cfg = self._config()
        return "%s/v3/company/%s/%s" % (API_HOSTS[cfg["environment"]], self.realm_id(), path.lstrip("/"))

    def _request(self, method, path, params=None, body=None, retry=True, token=None):
        url = self._url(path)
        token = token or self.access_token()
        query = {"minorversion": MINOR_VERSION}
        query.update(params or {})
        headers = {"Authorization": "Bearer " + token, "Accept": "application/json"}
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, params=query, timeout=TIMEOUT)
            else:
                headers["Content-Type"] = "application/json"
                resp = requests.post(url, headers=headers, params=query, json=body, timeout=TIMEOUT)
        except requests.RequestException as e:
            raise QboError("network", _("QuickBooks didn't answer: %s") % e)
        if resp.status_code == 401 and retry:
            fresh = self.access_token(force=True, failed=token)
            return self._request(method, path, params, body, retry=False, token=fresh)
        if resp.status_code == 429:
            raise QboError("rate_limit", _("QuickBooks is receiving too many requests; it will be retried."))
        if resp.status_code >= 400:
            raise QboError("api", self._fault_message(resp))
        try:
            return resp.json()
        except ValueError:
            raise QboError("api", _("QuickBooks sent an unexpected response (intuit_tid=%s).")
                           % resp.headers.get("intuit_tid", "-"))

    @staticmethod
    def _fault_message(resp):
        detail = ""
        try:
            errors = (resp.json().get("Fault") or {}).get("Error") or []
            if errors:
                e = errors[0]
                detail = " - ".join(x for x in (e.get("Message"), e.get("Detail")) if x)
        except Exception:  # cuerpo que no es JSON
            detail = (resp.text or "")[:300]
        return "QuickBooks %s: %s (intuit_tid=%s)" % (
            resp.status_code, detail or (resp.text or "")[:300], resp.headers.get("intuit_tid", "-"))

    def get(self, path, params=None):
        self._ensure_su()
        return self._request("GET", path, params=params)

    def post(self, path, body, params=None):
        self._ensure_su()
        return self._request("POST", path, params=params, body=body)

    def query(self, sql, entity):
        """SELECT de QBO; devuelve la lista de la entidad (vacia si no hay)."""
        self._ensure_su()
        return (self.get("query", {"query": sql}).get("QueryResponse") or {}).get(entity, [])
