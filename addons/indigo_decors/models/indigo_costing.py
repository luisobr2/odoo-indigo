# -*- coding: utf-8 -*-
"""Costo de cada puerta: el ESTIMADO por orden y el REAL del mes.

Majela (llamada del 9-oct-2026): "ya haciendo la puerta con esos precios que
estan establecidos, ya yo se cuanto me va a costar esa puerta por SQF... y
despues va a estar la opcion de real, el gasto real, los pagos que yo puse,
todas las compras que hice, de como salio el mes. Y eso me va a ayudar a
saber si mi estimacion esta correcta."

Dos cosas, a proposito separadas:

* ESTIMADO por orden, con tarifas fijas que ella dio y que se editan en
  Settings: material (CNC, ACM, pintura, pegamento, otros) + mano de obra
  (pintura, instalacion con su gasolina, digitalizacion). No cambia cuando
  entra una factura de compra.
* REAL del mes: lo vendido (facturas emitidas) contra lo gastado (facturas
  de compra que sube Majela, todo material es stock) y lo pagado a la gente
  (liquidaciones). Con el estimado de esas mismas ordenes al lado.

Nada de esto sale en la factura ni en el correo al dealer.
"""
import base64
import calendar
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

# clave -> (valor por defecto, etiqueta). Los valores son los de Majela.
COST_DEFAULTS = {
    "cnc_per_sqf": (0.94, "CNC / router cut, per SQF"),
    "acm_sheet_price": (42.0, "ACM sheet price"),
    "acm_sheet_sqf": (32.0, "SQF per ACM sheet"),
    "paint_per_sqf": (2.0, "Paint material at Indigo, per SQF"),
    "glue_per_door": (8.0, "Glue, per door"),
    "other_per_door": (5.0, "Other supplies, per door"),
    "install_per_door": (35.0, "Installation, per door"),
    "gas_per_door": (10.0, "Gas and tolls, per door"),
}
PREFIX = "indigo_decors.cost."

EXPENSE_CATEGORIES = [
    ("acm", "ACM"),
    ("paint", "Paint"),
    ("glue", "Glue"),
    ("labor", "Labor"),
    ("service", "Outside service"),
    ("other", "Other"),
]
MAX_FILE_BYTES = 10 * 1024 * 1024


class IndigoExpense(models.Model):
    _name = "indigo.expense"
    _description = "Gasto / factura de compra"
    _order = "date desc, id desc"

    date = fields.Date(required=True, default=fields.Date.context_today, index=True)
    supplier = fields.Char(required=True)
    category = fields.Selection(EXPENSE_CATEGORIES, required=True, default="other")
    amount = fields.Float(required=True, digits=(12, 2))
    note = fields.Char()
    attachment_id = fields.Many2one("ir.attachment", ondelete="set null")
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)

    @api.constrains("amount")
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_("The amount must be greater than zero."))


class IndigoCosting(models.AbstractModel):
    _name = "indigo.costing"
    _description = "Indigo costs per door and per month"

    # ------------------------------------------------------------ roles

    def _assert_office(self):
        u = self.env.user
        if not (u._is_admin() or u.has_group("indigo_decors.group_indigo_manager")
                or u.has_group("indigo_decors.group_indigo_office")):
            raise AccessError(_("Only the office or a manager can see costs."))

    # ------------------------------------------------------------ tarifas

    def _rates(self):
        icp = self.env["ir.config_parameter"].sudo()
        out = {}
        for key, (default, _label) in COST_DEFAULTS.items():
            raw = icp.get_param(PREFIX + key)
            try:
                out[key] = float(raw) if raw not in (None, False, "") else default
            except ValueError:
                out[key] = default
        return out

    @api.model
    def indigo_cost_settings(self):
        self._assert_office()
        rates = self._rates()
        return [{"key": k, "label": label, "value": rates[k]} for k, (_d, label) in COST_DEFAULTS.items()]

    @api.model
    def indigo_cost_save_settings(self, vals):
        self._assert_office()
        icp = self.env["ir.config_parameter"].sudo()
        for key, value in (vals or {}).items():
            if key not in COST_DEFAULTS:
                continue
            try:
                num = float(value)
            except (TypeError, ValueError):
                raise ValidationError(_("%s must be a number.") % COST_DEFAULTS[key][1])
            if num < 0 or (key == "acm_sheet_sqf" and num <= 0):
                raise ValidationError(_("%s can't be zero or negative.") % COST_DEFAULTS[key][1])
            icp.set_param(PREFIX + key, str(num))
        return self.indigo_cost_settings()

    # ------------------------------------------------------------ estimado

    def _payout_lines(self, order, ctype):
        return self.env["indigo.payout.line"].sudo().search([
            ("order_id", "=", order.id), ("payout_id.contractor_type", "=", ctype),
            ("payout_id.state", "!=", "cancel"), ("line_kind", "=", "work"),
        ])

    def _estimate(self, order):
        """Desglose del costo estimado de una orden."""
        r = self._rates()
        sqf = order.total_sqf or 0.0
        doors = order.door_count or 0
        acm_sqf = r["acm_sheet_price"] / r["acm_sheet_sqf"]
        Rate = self.env["indigo.contractor.rate"].sudo()
        painter_rule = Rate.resolve_for("painter", order.painter_id) if order.painter_id else Rate
        painted_at = painter_rule.paint_shop if painter_rule and painter_rule.partner_id else False

        lines = [
            {"group": "material", "label": _("CNC / router cut"), "detail": "%.2f SQF × $%.2f" % (sqf, r["cnc_per_sqf"]),
             "amount": sqf * r["cnc_per_sqf"]},
            {"group": "material", "label": _("ACM"), "detail": "%.2f SQF × $%.4f" % (sqf, acm_sqf),
             "amount": sqf * acm_sqf},
        ]
        if painted_at != "michel":
            lines.append({"group": "material", "label": _("Paint material"),
                          "detail": "%.2f SQF × $%.2f" % (sqf, r["paint_per_sqf"]), "amount": sqf * r["paint_per_sqf"]})
        lines += [
            {"group": "material", "label": _("Glue"), "detail": "%d × $%.2f" % (doors, r["glue_per_door"]),
             "amount": doors * r["glue_per_door"]},
            {"group": "material", "label": _("Other supplies"), "detail": "%d × $%.2f" % (doors, r["other_per_door"]),
             "amount": doors * r["other_per_door"]},
        ]
        # Pintura: lo que ya se le liquido por esta orden; si aun no, su regla.
        paint_paid = self._payout_lines(order, "painter")
        if paint_paid:
            lines.append({"group": "labor", "label": _("Painting"), "detail": _("paid: %s") % ", ".join(
                paint_paid.mapped("payout_id.contractor_id.name")), "amount": sum(paint_paid.mapped("amount"))})
        elif order.painter_id and painter_rule:
            lines.append({"group": "labor", "label": _("Painting"),
                          "detail": "%s · %.2f SQF × $%.2f" % (order.painter_id.name, sqf, painter_rule.rate),
                          "amount": sqf * painter_rule.rate})
        else:
            lines.append({"group": "labor", "label": _("Painting"), "detail": _("no painter yet"), "amount": 0.0})
        lines += [
            {"group": "labor", "label": _("Installation"), "detail": "%d × $%.2f" % (doors, r["install_per_door"]),
             "amount": doors * r["install_per_door"]},
            {"group": "labor", "label": _("Gas and tolls"), "detail": "%d × $%.2f" % (doors, r["gas_per_door"]),
             "amount": doors * r["gas_per_door"]},
        ]
        digit = self._payout_lines(order, "digitizer")
        if digit:
            lines.append({"group": "labor", "label": _("Digitization after hours"),
                          "detail": ", ".join(digit.mapped("payout_id.contractor_id.name")),
                          "amount": sum(digit.mapped("amount"))})
        for ln in lines:
            ln["amount"] = round(ln["amount"], 2)
        total = round(sum(ln["amount"] for ln in lines), 2)
        price = order.total_dealer_charge or 0.0
        return {
            "order_id": order.id,
            "name": order.name,
            "sqf": sqf,
            "doors": doors,
            "lines": lines,
            "materials": round(sum(ln["amount"] for ln in lines if ln["group"] == "material"), 2),
            "labor": round(sum(ln["amount"] for ln in lines if ln["group"] == "labor"), 2),
            "total": total,
            "per_sqf": round(total / sqf, 2) if sqf else 0.0,
            "price": price,
            "margin": round(price - total, 2),
        }

    @api.model
    def indigo_cost_order(self, order_id):
        self._assert_office()
        order = self.env["indigo.order"].sudo().browse(int(order_id)).exists()
        if not order:
            raise UserError(_("Order not found."))
        return self._estimate(order)

    @api.model
    def indigo_cost_invoice(self, move_id):
        """Rentabilidad de una factura: lo facturado (sin impuesto) contra el
        costo estimado de sus ordenes."""
        self._assert_office()
        move = self.env["account.move"].sudo().browse(int(move_id)).exists()
        if not move or move.move_type != "out_invoice":
            raise UserError(_("Invoice not found."))
        orders = [self._estimate(o) for o in move.indigo_order_ids]
        cost = round(sum(o["total"] for o in orders), 2)
        revenue = move.amount_untaxed
        return {
            "revenue": revenue,
            "cost": cost,
            "margin": round(revenue - cost, 2),
            "margin_pct": round((revenue - cost) / revenue * 100, 1) if revenue else 0.0,
            "orders": [{"order_id": o["order_id"], "name": o["name"], "total": o["total"]} for o in orders],
        }

    # ------------------------------------------------------------ real del mes

    @staticmethod
    def _month_bounds(month):
        try:
            y, m = (int(x) for x in str(month).split("-")[:2])
            first = date(y, m, 1)
        except (TypeError, ValueError):
            raise ValidationError(_("Month must look like 2026-10."))
        return first, date(y, m, calendar.monthrange(y, m)[1])

    @api.model
    def indigo_cost_month(self, month):
        """Lo que entro y lo que salio en el mes, con el estimado al lado."""
        self._assert_office()
        first, last = self._month_bounds(month)
        moves = self.env["account.move"].sudo().search([
            ("move_type", "=", "out_invoice"), ("state", "=", "posted"),
            ("invoice_date", ">=", first), ("invoice_date", "<=", last),
        ])
        sold = round(sum(moves.mapped("amount_untaxed")), 2)
        expenses = self.env["indigo.expense"].sudo().search([("date", ">=", first), ("date", "<=", last)])
        by_cat = {k: 0.0 for k, _l in EXPENSE_CATEGORIES}
        for e in expenses:
            by_cat[e.category] = by_cat.get(e.category, 0.0) + e.amount
        Payout = self.env["indigo.payout"].sudo()
        pay = {}
        for ctype in ("installer", "digitizer", "painter"):
            payouts = Payout.search([
                ("contractor_type", "=", ctype), ("state", "!=", "cancel"),
                "|", "&", ("work_date", ">=", first), ("work_date", "<=", last),
                "&", ("work_date", "=", False), "&", ("date", ">=", first), ("date", "<=", last),
            ])
            pay[ctype] = round(sum(payouts.mapped("amount")), 2)
        spent_purchases = round(sum(by_cat.values()), 2)
        spent_people = round(sum(pay.values()), 2)
        orders = moves.mapped("indigo_order_ids")
        estimate = round(sum(self._estimate(o)["total"] for o in orders), 2)
        out = round(spent_purchases + spent_people, 2)
        return {
            "month": first.strftime("%Y-%m"),
            "sold": sold,
            "invoices": len(moves),
            "doors": sum(orders.mapped("door_count")),
            "sqf": round(sum(orders.mapped("total_sqf")), 2),
            "purchases": {k: round(v, 2) for k, v in by_cat.items()},
            "purchases_total": spent_purchases,
            "people": pay,
            "people_total": spent_people,
            "spent": out,
            "result": round(sold - out, 2),
            "estimate": estimate,
            "estimate_result": round(sold - estimate, 2),
        }

    # ------------------------------------------------------------ gastos

    def _expense_row(self, e):
        return {
            "id": e.id,
            "date": fields.Date.to_string(e.date),
            "supplier": e.supplier,
            "category": e.category,
            "amount": e.amount,
            "note": e.note or "",
            "attachment_id": e.attachment_id.id or False,
            "attachment_name": e.attachment_id.name or False,
            "by": e.user_id.name or "",
        }

    @api.model
    def indigo_expense_list(self, month):
        self._assert_office()
        first, last = self._month_bounds(month)
        rows = self.env["indigo.expense"].sudo().search([("date", ">=", first), ("date", "<=", last)])
        return [self._expense_row(e) for e in rows]

    @api.model
    def indigo_expense_create(self, vals):
        """vals: date, supplier, category, amount, note, file_name, file_b64."""
        self._assert_office()
        vals = vals or {}
        supplier = (vals.get("supplier") or "").strip()
        if not supplier:
            raise ValidationError(_("Write who the purchase was from."))
        category = vals.get("category") or "other"
        if category not in dict(EXPENSE_CATEGORIES):
            raise ValidationError(_("Unknown expense type."))
        try:
            amount = round(float(vals.get("amount")), 2)
        except (TypeError, ValueError):
            raise ValidationError(_("The amount must be a number."))
        rec = self.env["indigo.expense"].sudo().create({
            "date": vals.get("date") or fields.Date.context_today(self),
            "supplier": supplier[:200],
            "category": category,
            "amount": amount,
            "note": (vals.get("note") or "").strip()[:500] or False,
            "user_id": self.env.uid,
        })
        if vals.get("file_b64"):
            try:
                data = base64.b64decode(vals["file_b64"], validate=True)
            except ValueError:
                raise ValidationError(_("The file couldn't be read."))
            if len(data) > MAX_FILE_BYTES:
                raise ValidationError(_("The file is larger than 10 MB."))
            att = self.env["ir.attachment"].sudo().create({
                "name": (vals.get("file_name") or "receipt")[:200],
                "datas": base64.b64encode(data),
                "res_model": "indigo.expense",
                "res_id": rec.id,
            })
            rec.attachment_id = att
        return self._expense_row(rec)

    @api.model
    def indigo_expense_delete(self, expense_id):
        self._assert_office()
        rec = self.env["indigo.expense"].sudo().browse(int(expense_id)).exists()
        if not rec:
            raise UserError(_("Expense not found."))
        att = rec.attachment_id
        rec.unlink()
        # Odoo ya borra los adjuntos del registro; por si el archivo era de otro.
        att.exists().unlink()
        return True

    @api.model
    def indigo_expense_file(self, expense_id):
        """(nombre, mimetype, base64) del archivo de un gasto."""
        self._assert_office()
        rec = self.env["indigo.expense"].sudo().browse(int(expense_id)).exists()
        if not rec or not rec.attachment_id:
            raise UserError(_("This expense has no file."))
        att = rec.attachment_id
        return {"name": att.name, "mimetype": att.mimetype, "datas": att.datas.decode() if att.datas else ""}
