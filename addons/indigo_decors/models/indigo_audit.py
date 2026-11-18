# -*- coding: utf-8 -*-
"""Registro de actividad (18-nov-2026): quien hizo que, cuando y sobre que.

Una fila por accion de una PERSONA: crear, modificar o borrar en los modelos
del negocio, notas y adjuntos en una orden, e inicios de sesion en el panel.
Lo escribe Odoo, no el panel, para que entre todo igual venga de donde venga
(panel, asistente IA, tienda o el propio Odoo).

Lo que NO entra, a proposito:
- Lo que hace Odoo solo (tareas programadas, migraciones): corre como
  OdooBot (uid 1) y llenaria el registro de sincronizaciones con QuickBooks
  y avisos de retraso que no hizo nadie.
- Campos tecnicos (seguidores, actividades, estado de QuickBooks...).
- El contenido de contrasenas, claves y tokens: se anota que cambiaron, no
  su valor.

Solo lo leen administradores y gerencia, desde el panel (Activity log).
Nadie lo edita ni lo borra.
"""
import json
import logging
import re
from datetime import datetime, time, timedelta

import pytz

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import AccessDenied, AccessError, UserError
from odoo.http import request
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)

SHOP_TZ = "America/New_York"

MODULES = [
    ("orders", "Orders"),
    ("billing", "Billing"),
    ("dealers", "Dealers"),
    ("catalog", "Catalog"),
    ("pricing", "Pricing"),
    ("labor", "Labor & pay"),
    ("inventory", "Inventory"),
    ("users", "Users"),
    ("settings", "Settings"),
    ("session", "Sign-in"),
]

ACTIONS = [
    ("create", "Created"),
    ("write", "Changed"),
    ("unlink", "Deleted"),
    ("note", "Note"),
    ("attachment", "File"),
    ("login", "Signed in"),
    ("login_failed", "Failed sign-in"),
]

# modelo -> (modulo, como se llama un registro suyo en el panel)
AUDITED = {
    "indigo.order": ("orders", "Order"),
    "indigo.order.line": ("orders", "Door"),
    "indigo.order.incident": ("orders", "Incident"),
    "account.move": ("billing", "Invoice"),
    "account.payment": ("billing", "Payment"),
    "indigo.expense": ("billing", "Expense"),
    "res.partner": ("dealers", "Dealer"),
    "indigo.design": ("catalog", "Design"),
    "indigo.brand": ("catalog", "Brand"),
    "product.template": ("catalog", "Product"),
    "indigo.design.price": ("pricing", "Design price"),
    "indigo.install.range": ("pricing", "Install range"),
    "indigo.install.zone": ("pricing", "Install zone"),
    "indigo.contractor.rate": ("labor", "Pay rule"),
    "indigo.payout": ("labor", "Payout"),
    "indigo.stock": ("inventory", "Stock item"),
    "res.users": ("users", "User"),
    "ir.config_parameter": ("settings", "Setting"),
    "indigo.stage": ("settings", "Stage"),
    "indigo.hold.reason": ("settings", "Hold reason"),
}

# Campos que se comparan aunque no vengan en el write: los que cambian como
# consecuencia (el total al tocar las lineas de una factura).
ALWAYS_COMPARE = {
    "account.move": ("amount_total", "state"),
}

SKIP_FIELDS = {
    "write_date", "write_uid", "create_date", "create_uid", "display_name",
    "__last_update", "login_date", "tz", "share", "access_token",
    "message_main_attachment_id", "signup_token", "signup_type", "signup_expiration",
}
SKIP_PREFIXES = ("message_", "activity_", "website_message", "qbo_", "access_", "__")
SECRET_RE = re.compile(r"pass|secret|token|api_?key|private|client_?key", re.I)
MASK = "••••••"
MAX_TEXT = 300
MAX_NAMES = 10


def _skip(env):
    return env.uid == SUPERUSER_ID or env.context.get("indigo_audit_off")


def _clip(text):
    text = (text or "").strip()
    return text if len(text) <= MAX_TEXT else text[: MAX_TEXT - 1] + "…"


class IndigoAuditLog(models.Model):
    _name = "indigo.audit.log"
    _description = "Activity log"
    _order = "date desc, id desc"
    _rec_name = "summary"

    date = fields.Datetime(required=True, default=fields.Datetime.now, index=True, readonly=True)
    user_id = fields.Many2one("res.users", ondelete="set null", index=True, readonly=True)
    # El nombre se guarda aparte: si el usuario se borra, la fila sigue diciendo quien fue.
    user_name = fields.Char(readonly=True)
    module = fields.Selection(MODULES, required=True, index=True, readonly=True)
    action = fields.Selection(ACTIONS, required=True, index=True, readonly=True)
    record_type = fields.Char(readonly=True)
    res_model = fields.Char(index=True, readonly=True)
    res_id = fields.Integer(index=True, readonly=True)
    res_name = fields.Char(readonly=True)
    summary = fields.Char(readonly=True)
    # JSON: [{"field": "stage_id", "label": "Stage", "old": "...", "new": "..."}]
    changes = fields.Text(readonly=True)
    # Mensaje del historial de la orden del que salio la fila (importacion del
    # historial). Evita duplicar si la importacion se repite.
    origin_message_id = fields.Integer(index=True, readonly=True)

    # ------------------------------------------------------------ inmutable

    def write(self, vals):
        if not self.env.context.get("indigo_audit_system"):
            raise UserError(_("The activity log can't be edited."))
        return super().write(vals)

    def unlink(self):
        if not self.env.context.get("indigo_audit_system"):
            raise UserError(_("The activity log can't be deleted."))
        return super().unlink()

    # ------------------------------------------------------------ escritura

    @api.model
    def _audit_add(self, vals_list):
        """Crea filas sin pasar por los permisos de quien actua."""
        if not vals_list:
            return self.browse()
        return self.sudo().with_context(indigo_audit_off=True).create(vals_list)

    @api.model
    def _audit_base(self, records, action):
        module, record_type = AUDITED.get(records._name, ("settings", records._description))
        user = self.env.user
        return {
            "user_id": user.id,
            "user_name": user.name,
            "module": module,
            "action": action,
            "record_type": record_type,
            "res_model": records._name,
        }

    # ------------------------------------------------------------ lectura (panel)

    @api.model
    def _assert_audit_reader(self):
        u = self.env.user
        if not (u._is_admin() or u.has_group("indigo_decors.group_indigo_manager")):
            raise AccessError(_("Only administrators can see the activity log."))

    @api.model
    def _audit_domain(self, p):
        domain = []
        tz = pytz.timezone(SHOP_TZ)

        def utc(day, end=False):
            d = fields.Date.from_string(day)
            local = tz.localize(datetime.combine(d + timedelta(days=1) if end else d, time.min))
            return local.astimezone(pytz.utc).replace(tzinfo=None)

        if p.get("date_from"):
            domain.append(("date", ">=", utc(p["date_from"])))
        if p.get("date_to"):
            domain.append(("date", "<", utc(p["date_to"], end=True)))
        if p.get("user_id"):
            domain.append(("user_id", "=", int(p["user_id"])))
        if p.get("module"):
            domain.append(("module", "=", p["module"]))
        if p.get("action"):
            domain.append(("action", "=", p["action"]))
        if p.get("res_model") and p.get("res_id"):
            domain += [("res_model", "=", p["res_model"]), ("res_id", "=", int(p["res_id"]))]
        q = (p.get("q") or "").strip()
        if q:
            domain += ["|", "|", "|", ("res_name", "ilike", q), ("summary", "ilike", q),
                       ("user_name", "ilike", q), ("changes", "ilike", q)]
        return domain

    def _audit_row(self):
        self.ensure_one()
        try:
            changes = json.loads(self.changes or "[]")
        except ValueError:
            changes = []
        return {
            "id": self.id,
            "date": fields.Datetime.to_string(self.date),
            "user_id": self.user_id.id or False,
            "user_name": self.user_name or self.user_id.name or "",
            "module": self.module,
            "action": self.action,
            "record_type": self.record_type or "",
            "res_model": self.res_model or "",
            "res_id": self.res_id or False,
            "res_name": self.res_name or "",
            "summary": self.summary or "",
            "changes": changes,
        }

    @api.model
    def indigo_audit_search(self, params=None):
        """Lo que pide la pagina Activity log: filas filtradas y paginadas,
        con el total y la lista de personas para el filtro."""
        self._assert_audit_reader()
        p = params or {}
        Log = self.sudo()
        domain = self._audit_domain(p)
        cap = 5000 if p.get("export") else 200
        limit = max(1, min(int(p.get("limit") or 50), cap))
        offset = max(0, int(p.get("offset") or 0))
        rows = Log.search(domain, offset=offset, limit=limit)
        users = Log.read_group([("user_id", "!=", False)], ["user_id"], ["user_id"], orderby="user_id")
        return {
            "total": Log.search_count(domain),
            "rows": [r._audit_row() for r in rows],
            "users": sorted(
                ({"id": g["user_id"][0], "name": g["user_id"][1]} for g in users if g.get("user_id")),
                key=lambda u: (u["name"] or "").lower(),
            ),
            "modules": [{"key": k, "label": v} for k, v in MODULES],
            "actions": [{"key": k, "label": v} for k, v in ACTIONS],
        }

    # ------------------------------------------------------------ historial

    @api.model
    def _audit_import_history(self, before=None):
        """Pasa al registro lo que ya guardo el historial (chatter) de las
        ordenes y demas: cambios de campo, notas y adjuntos. Idempotente.

        Solo lo anterior a la activacion (`before`, o el parametro
        indigo_decors.audit_since): lo posterior ya lo anota el registro en
        vivo, y traerlo otra vez lo duplicaria."""
        if before is None:
            since = self.env["ir.config_parameter"].sudo().get_param("indigo_decors.audit_since")
            before = fields.Datetime.to_datetime(since) if since else fields.Datetime.now()
        Msg = self.env["mail.message"].sudo().with_context(lang="en_US")
        thread_models = [m for m in AUDITED if m in self.env and "message_ids" in self.env[m]._fields]
        bot = self.env.ref("base.partner_root", raise_if_not_found=False)
        done = set(self.sudo().search([("origin_message_id", "!=", 0)]).mapped("origin_message_id"))
        msgs = Msg.search([("model", "in", thread_models), ("res_id", "!=", False),
                           ("author_id", "!=", bot.id if bot else False),
                           ("date", "<", before)], order="date asc, id asc")
        names = {}

        def res_name(model, rid):
            key = (model, rid)
            if key not in names:
                rec = self.env[model].sudo().with_context(active_test=False).browse(rid).exists()
                names[key] = rec.display_name if rec else "#%s" % rid
            return names[key]

        vals_list = []
        for m in msgs:
            if m.id in done:
                continue
            module, record_type = AUDITED[m.model]
            user = m.author_id.user_ids[:1]
            base = {
                "date": m.date,
                "user_id": user.id or False,
                "user_name": m.author_id.name or "",
                "module": module,
                "record_type": record_type,
                "res_model": m.model,
                "res_id": m.res_id,
                "res_name": res_name(m.model, m.res_id),
                "origin_message_id": m.id,
            }
            if m.tracking_value_ids:
                changes = []
                for tv in m.tracking_value_ids:
                    ttype = tv.field_id.ttype or "char"
                    old = tv._format_display_value(ttype, new=False)[0]
                    new = tv._format_display_value(ttype, new=True)[0]
                    changes.append({
                        "field": tv.field_id.name or "",
                        "label": tv.field_id.field_description or tv.field_id.name or "",
                        "old": "" if old in (None, False) else str(old),
                        "new": "" if new in (None, False) else str(new),
                    })
                vals_list.append(dict(base, action="write", summary=_summary_write(changes),
                                      changes=json.dumps(changes)))
            elif m.message_type == "comment" and html2plaintext(m.body or "").strip():
                vals_list.append(dict(base, action="note", summary=_clip(html2plaintext(m.body or ""))))
            elif m.attachment_ids:
                vals_list.append(dict(base, action="attachment",
                                      summary=_clip("Uploaded " + ", ".join(m.attachment_ids.mapped("name")))))
        for i in range(0, len(vals_list), 1000):
            self._audit_add(vals_list[i:i + 1000])
        _logger.info("Activity log: %s rows imported from the record history", len(vals_list))
        return len(vals_list)


def _summary_write(changes):
    if len(changes) == 1:
        c = changes[0]
        return _clip("%s: %s → %s" % (c["label"], c["old"] or "empty", c["new"] or "empty"))
    labels = [c["label"] for c in changes]
    if len(labels) <= 3:
        return _clip("Changed " + ", ".join(labels))
    return _clip("Changed %s and %d more" % (", ".join(labels[:3]), len(labels) - 3))


class IndigoAuditMixin(models.AbstractModel):
    """Se mezcla en cada modelo de AUDITED (ver abajo) y anota crear,
    modificar y borrar."""

    _name = "indigo.audit.mixin"
    _description = "Activity log hooks"

    # -- que registros cuentan --------------------------------------------

    def _indigo_audit_scope(self):
        name = self._name
        if name == "res.partner":
            return self.filtered("is_indigo_dealer")
        if name == "account.move":
            return self.filtered(lambda m: m.move_type in ("out_invoice", "out_refund"))
        if name == "ir.config_parameter":
            return self.filtered(lambda p: (p.key or "").startswith("indigo"))
        return self

    def _indigo_audit_name(self):
        if self._name == "ir.config_parameter":
            return self.key
        return self.display_name

    # -- que campos y como se escriben -------------------------------------

    def _indigo_audit_fields(self, names):
        out = []
        for fname in names:
            field = self._fields.get(fname)
            if not field or fname in SKIP_FIELDS or fname.startswith(SKIP_PREFIXES):
                continue
            # Una contrasena no se guarda como campo normal, pero cambiarla
            # es justo lo que hay que anotar (sin el valor).
            if not (field.store or field.type in ("one2many", "many2many") or SECRET_RE.search(fname)):
                continue
            out.append(fname)
        return out

    def _indigo_audit_secret(self, fname):
        if self._name == "ir.config_parameter" and fname == "value":
            return bool(SECRET_RE.search(self.key or ""))
        return bool(SECRET_RE.search(fname))

    def _indigo_audit_value(self, fname):
        field = self._fields[fname]
        value = self[fname]
        if self._indigo_audit_secret(fname):
            return MASK if value else ""
        if field.type == "many2one":
            return value.display_name or ""
        if field.type in ("one2many", "many2many"):
            labels = [n or "" for n in value.mapped("display_name")]
            more = len(labels) - MAX_NAMES
            return ", ".join(labels[:MAX_NAMES]) + (" +%d more" % more if more > 0 else "")
        if value is False or value is None:
            return "" if field.type != "boolean" else "No"
        if field.type == "boolean":
            return "Yes" if value else "No"
        if field.type == "selection":
            en = self.with_context(lang="en_US").env
            return dict(field._description_selection(en)).get(value, value) or ""
        if field.type in ("float", "monetary"):
            return ("%.2f" % value).rstrip("0").rstrip(".")
        if field.type == "datetime":
            return fields.Datetime.to_string(value)
        if field.type == "date":
            return fields.Date.to_string(value)
        if field.type == "binary":
            return "(file)"
        if field.type == "html":
            return _clip(html2plaintext(value))
        return _clip(str(value))

    def _indigo_audit_label(self, fname):
        field = self.with_context(lang="en_US")._fields[fname]
        return field._description_string(self.with_context(lang="en_US").env) or fname

    def _indigo_audit_snapshot(self, fnames):
        return {
            rec.id: {f: rec._indigo_audit_value(f) for f in fnames}
            for rec in self.sudo().with_context(prefetch_fields=False)
        }

    # -- ganchos -------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        if _skip(self.env):
            return super().create(vals_list)
        records = super(IndigoAuditMixin, self.with_context(indigo_audit_off=True)).create(vals_list)
        records = records.with_context(indigo_audit_off=False)
        scoped = records._indigo_audit_scope()
        if scoped:
            Log = self.env["indigo.audit.log"]
            base = Log._audit_base(scoped, "create")
            Log._audit_add([dict(base, res_id=r.id, res_name=r.sudo()._indigo_audit_name() or "",
                                 summary=_clip("Created %s %s" % (base["record_type"].lower(),
                                                                   r.sudo()._indigo_audit_name() or "")))
                            for r in scoped])
        return records

    def write(self, vals):
        if _skip(self.env):
            return super().write(vals)
        scoped = self._indigo_audit_scope()
        fnames = scoped._indigo_audit_fields(list(vals) + list(ALWAYS_COMPARE.get(self._name, ())))
        if not scoped or not fnames:
            return super().write(vals)
        before = scoped._indigo_audit_snapshot(fnames)
        res = super().write(vals)
        after = scoped._indigo_audit_snapshot(fnames)
        Log = self.env["indigo.audit.log"]
        base = Log._audit_base(scoped, "write")
        rows = []
        for rec in scoped.sudo():
            changes = []
            for f in fnames:
                if f in vals and vals[f] and rec._indigo_audit_secret(f):
                    # Nunca el valor: solo que cambio.
                    changes.append({"field": f, "label": rec._indigo_audit_label(f), "old": "", "new": "(changed)"})
                elif before[rec.id][f] != after[rec.id][f]:
                    changes.append({"field": f, "label": rec._indigo_audit_label(f),
                                    "old": before[rec.id][f], "new": after[rec.id][f]})
            if not changes:
                continue
            rows.append(dict(base, res_id=rec.id, res_name=rec._indigo_audit_name() or "",
                             summary=_summary_write(changes), changes=json.dumps(changes)))
        Log._audit_add(rows)
        return res

    def unlink(self):
        if _skip(self.env):
            return super().unlink()
        scoped = self._indigo_audit_scope()
        if scoped:
            Log = self.env["indigo.audit.log"]
            base = Log._audit_base(scoped, "unlink")
            rows = [dict(base, res_id=r.id, res_name=r._indigo_audit_name() or "",
                         summary=_clip("Deleted %s %s" % (base["record_type"].lower(), r._indigo_audit_name() or "")))
                    for r in scoped.sudo()]
        res = super().unlink()
        if scoped:
            Log._audit_add(rows)
        return res


# Cada modelo de AUDITED recibe el mixin. Clases creadas en bucle para no
# repetir veinte veces lo mismo; `__module__` las deja registradas en este
# addon como si estuvieran escritas a mano.
for _model in AUDITED:
    type(
        "IndigoAudit_%s" % _model.replace(".", "_"),
        (models.Model,),
        {"_inherit": [_model, "indigo.audit.mixin"], "_name": _model, "__module__": __name__},
    )


class MailMessageAudit(models.Model):
    """Una nota escrita en una orden (o factura, pago...) tambien es una accion."""

    _inherit = "mail.message"

    @api.model_create_multi
    def create(self, vals_list):
        msgs = super().create(vals_list)
        if _skip(self.env):
            return msgs
        Log = self.env["indigo.audit.log"]
        rows = []
        for m in msgs.sudo():
            if m.model not in AUDITED or not m.res_id or m.message_type != "comment":
                continue
            text = html2plaintext(m.body or "").strip()
            # El panel narra cada archivo subido ("Attachment uploaded: x");
            # ese ya entra como fila de archivo, no se duplica como nota.
            if not text or text.startswith("Attachment uploaded"):
                continue
            record = self.env[m.model].sudo().browse(m.res_id).exists()
            module, record_type = AUDITED[m.model]
            rows.append({
                "user_id": self.env.user.id, "user_name": self.env.user.name,
                "module": module, "action": "note", "record_type": record_type,
                "res_model": m.model, "res_id": m.res_id,
                "res_name": record.display_name if record else "", "summary": _clip(text),
            })
        Log._audit_add(rows)
        return msgs


class IrAttachmentAudit(models.Model):
    """Subir o quitar un archivo de una orden."""

    _inherit = "ir.attachment"

    def _indigo_audit_rows(self, verb):
        rows = []
        for a in self.sudo():
            if a.res_model not in AUDITED or not a.res_id or a.res_field:
                continue
            record = self.env[a.res_model].sudo().browse(a.res_id).exists()
            module, record_type = AUDITED[a.res_model]
            rows.append({
                "user_id": self.env.user.id, "user_name": self.env.user.name,
                "module": module, "action": "attachment", "record_type": record_type,
                "res_model": a.res_model, "res_id": a.res_id,
                "res_name": record.display_name if record else "",
                "summary": _clip("%s %s" % (verb, a.name or "")),
            })
        return rows

    @api.model_create_multi
    def create(self, vals_list):
        atts = super().create(vals_list)
        if not _skip(self.env):
            self.env["indigo.audit.log"]._audit_add(atts._indigo_audit_rows("Uploaded"))
        return atts

    def unlink(self):
        rows = [] if _skip(self.env) else self._indigo_audit_rows("Removed")
        res = super().unlink()
        self.env["indigo.audit.log"]._audit_add(rows)
        return res


class ResUsersAuditLogin(models.Model):
    """Inicios de sesion. Se anotan en un cursor aparte: un intento fallido
    deshace la transaccion de la peticion y se llevaria la fila con el."""

    _inherit = "res.users"

    @classmethod
    def _login(cls, db, login, password, user_agent_env):
        try:
            uid = super()._login(db, login, password, user_agent_env)
        except AccessDenied:
            cls._indigo_audit_login(login, False)
            raise
        # El asistente IA se autentica en cada consulta (/jsonrpc): solo cuenta
        # la entrada al panel, que pasa por /web/session/authenticate.
        path = request.httprequest.path if request else ""
        if path.startswith("/web/session/authenticate") or path.startswith("/web/login"):
            cls._indigo_audit_login(login, uid)
        return uid

    @classmethod
    def _indigo_audit_login(cls, login, uid):
        try:
            with cls.pool.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                Users = env["res.users"].with_context(active_test=False)
                user = Users.browse(uid) if uid else Users.search([("login", "=", login)], limit=1)
                env["indigo.audit.log"]._audit_add([{
                    "user_id": user.id or False,
                    "user_name": user.name or login or "",
                    "module": "session",
                    "action": "login" if uid else "login_failed",
                    "record_type": "User",
                    "res_model": "res.users",
                    "res_id": user.id or False,
                    "res_name": login or "",
                    "summary": "Signed in" if uid else _clip("Failed sign-in as %s" % (login or "")),
                }])
        except Exception:  # el registro nunca debe impedir entrar
            _logger.exception("Activity log: could not record sign-in for %s", login)
