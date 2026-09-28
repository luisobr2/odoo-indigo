# -*- coding: utf-8 -*-
"""Facturar desde la app (pedido de Majela, 2026-09-28).

Hasta ahora Indigo facturaba en QuickBooks y marcaba la orden como
«Invoiced / Paid» a mano. Aqui la factura es una factura de verdad de Odoo
(`account.move`), generada a partir de una o varias ordenes del mismo dealer:

  * una linea por puerta, con el producto segun el tipo (Single / Double /
    Sidelites), el precio de la orden y el 7 % de Florida;
  * una linea de recargo de instalacion por orden, segun el rango de millas
    que ya calcula la orden (region A-D, como en QuickBooks), sin impuesto;
  * lineas libres ("production · Display") cuando hace falta.

Por que `account.move` y no un modelo propio: numeracion, impuestos, pagos
parciales, saldo por cliente y correo ya vienen resueltos, y cuando lleguen
los gastos (facturas de proveedor) caen en el mismo sitio.

La app habla con esto a traves de `indigo.billing`, con el mismo patron que
`indigo_team_*`: se comprueba el rol (oficina, gerente o admin) y se opera en
sudo, porque el equipo no tiene grupos contables de Odoo y no debe tenerlos
para usar el backend contable a pelo.

La NUMERACION sigue la de QuickBooks (decision del 2026-09-28): una secuencia
propia sin prefijo cuyo siguiente numero se fija en Settings. Mientras
QuickBooks siga emitiendo en paralelo, hay que mover ese numero a mano para
que no se pisen.
"""
import base64
import io
import logging
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)

PARAM = "indigo_decors.invoice_"
SEQUENCE_CODE = "indigo.invoice.number"
TAX_XMLID = "indigo_decors.tax_fl_sales"

# Datos del emisor tal como salen hoy en las facturas de QuickBooks. Viven en
# parametros para que se puedan corregir desde Settings sin tocar codigo:
# la razon social todavia esta por confirmar (en Odoo la empresa figura como
# Indigo Publicity Corp.).
ISSUER_DEFAULTS = {
    "issuer_name": "Indigo Decors LLC",
    "issuer_street": "6752 NE 4th Ave",
    "issuer_city": "Miami FL 33138-5515",
    "issuer_email": "indigodecors.llc@gmail.com",
    "issuer_phone": "+1 (786) 302-2732",
    "issuer_website": "https://www.indigodecors.com",
    "tax_rate": "7",
    "terms": "Due on receipt",
}
DEFAULT_NEXT_NUMBER = 1364  # la ultima vista en QuickBooks fue la 1363

# Producto por tipo de puerta. El nombre es el que sale en la factura;
# QuickBooks lo tiene escrito "DESING", aqui va bien escrito.
DOOR_PRODUCTS = {
    "SD": ("IND-SD", "DESIGN SINGLE DOOR"),
    "DD": ("IND-DD", "DESIGN DOUBLE DOOR"),
    "sidelite": ("IND-SL", "DESIGN DOOR WITH SIDELITES"),
}
OTHER_PRODUCT = ("IND-OTHER", "PRODUCTION")

# Recargo por region: los valores de QuickBooks. Solo rellenan huecos; lo
# que se edite despues en Settings se respeta.
REGION_DEFAULTS = [
    # (min_miles, region, fee)
    (0.0, "A", 0.0),
    (35.0, "B", 35.0),
    (45.0, "C", 70.0),
    (90.0, "D", 120.0),
]

DESCRIPTION_TEMPLATES = [
    ("client", "Client name"),
    ("client_address", "Client name + address"),
    ("po", "REF: PO + client + PO number"),
]


class ResPartner(models.Model):
    _inherit = "res.partner"

    indigo_invoice_emails = fields.Char(
        string="Invoice emails",
        help="Where this dealer's invoices go. Several, separated by commas. "
             "Empty = the dealer's main email.",
    )
    indigo_tax_exempt = fields.Boolean(
        string="Sales tax exempt",
        help="Resale certificate: door lines go out without sales tax.",
    )
    indigo_invoice_description = fields.Selection(
        DESCRIPTION_TEMPLATES,
        string="Invoice line description",
        default="client",
        help="What goes in the description of each door on this dealer's invoices.",
    )

    def _indigo_invoice_recipients(self):
        self.ensure_one()
        raw = self.indigo_invoice_emails or self.email or ""
        return [e.strip() for e in raw.replace(";", ",").split(",") if e.strip()]


class IndigoInstallRange(models.Model):
    _inherit = "indigo.install.range"

    invoice_region = fields.Char(
        string="Invoice region",
        help="Letter printed on the invoice fee line (A, B, C, D).",
    )
    invoice_fee = fields.Float(
        string="Installation fee (USD)",
        digits=(10, 2),
        help="Charged to the dealer on the invoice for installs in this range. No sales tax.",
    )

    @api.model
    def _indigo_seed_invoice_fees(self):
        """Rellena region y recargo en los rangos que no lo tengan. Se llama en
        cada actualizacion del modulo y no pisa lo que ya se haya editado."""
        for rng in self.search([]):
            if rng.invoice_region:
                continue
            for min_miles, region, fee in REGION_DEFAULTS:
                if abs((rng.min_miles or 0.0) - min_miles) < 0.01:
                    rng.write({"invoice_region": region, "invoice_fee": fee})
                    break


class IndigoOrder(models.Model):
    _inherit = "indigo.order"

    invoice_ids = fields.Many2many(
        "account.move",
        "indigo_order_invoice_rel",
        "order_id",
        "move_id",
        string="Invoices",
        copy=False,
    )


class AccountMove(models.Model):
    _inherit = "account.move"

    indigo_order_ids = fields.Many2many(
        "indigo.order",
        "indigo_order_invoice_rel",
        "move_id",
        "order_id",
        string="Indigo orders",
        copy=False,
    )
    indigo_photo_ids = fields.Many2many(
        "ir.attachment",
        "indigo_invoice_photo_rel",
        "move_id",
        "attachment_id",
        string="Installation photos",
        copy=False,
        help="Appended to the invoice PDF, one per page.",
    )
    indigo_sent_at = fields.Datetime(string="Sent at", copy=False)
    indigo_sent_to = fields.Char(string="Sent to", copy=False)

    def _indigo_issuer(self):
        get = self.env["ir.config_parameter"].sudo().get_param
        return {k: get(PARAM + k) or v for k, v in ISSUER_DEFAULTS.items()}

    def _indigo_logo_data(self):
        """El logo incrustado en el PDF: wkhtmltopdf no siempre alcanza la URL
        del propio servidor (detras de un proxy, o con web.base.url publico)."""
        from odoo.tools.misc import file_open

        with file_open("indigo_decors/static/src/img/invoice_logo.png", "rb") as fh:
            return "data:image/png;base64," + base64.b64encode(fh.read()).decode()

    @staticmethod
    def _indigo_money(value):
        """Como QuickBooks: $1,284.00, sin espacio tras el simbolo."""
        value = value or 0.0
        sign = "-" if value < 0 else ""
        return "%s$%s" % (sign, "{:,.2f}".format(abs(value)))

    def _indigo_photo_data(self, max_px=1400):
        """Fotos listas para el PDF: redimensionadas y en JPEG, porque las de
        un telefono pesan 3-5 MB cada una y la factura va por correo."""
        from PIL import Image

        out = []
        for att in self.indigo_photo_ids:
            if not (att.mimetype or "").startswith("image/") or not att.datas:
                continue
            try:
                im = Image.open(io.BytesIO(base64.b64decode(att.datas)))
                im = im.convert("RGB")
                im.thumbnail((max_px, max_px))
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=80)
                out.append("data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode())
            except Exception:  # una foto rota no tumba la factura
                _logger.warning("Indigo invoice %s: photo %s skipped", self.id, att.id)
        return out

    def _indigo_status_label(self):
        self.ensure_one()
        if self.state == "draft":
            return "Draft"
        if self.state == "cancel":
            return "Cancelled"
        if self.payment_state in ("paid", "in_payment", "reversed"):
            return "Paid"
        due = self.invoice_date_due or self.invoice_date
        if due and due < fields.Date.context_today(self) and self.amount_residual > 0:
            return "Overdue"
        return "Balance due"

    def _indigo_sync_orders(self):
        """Lleva el estado de pago de la factura a sus ordenes, que es lo que
        leen el tablero, la lista de ordenes y el Kanban."""
        for order in self.mapped("indigo_order_ids"):
            invoices = order.invoice_ids.filtered(
                lambda m: m.state == "posted" and m.move_type == "out_invoice"
            )
            if not invoices:
                # Su unica factura se anulo: vuelve a estar sin cobrar.
                order.sudo().write({"payment_state": "unpaid", "date_paid": False})
                continue
            states = set(invoices.mapped("payment_state"))
            if states <= {"paid", "in_payment", "reversed"}:
                # La fecha del ULTIMO pago, no la de hoy: un cheque de agosto
                # registrado en septiembre es ingreso de agosto en el tablero.
                dates = [p.date for m in invoices for p in m._get_reconciled_payments() if p.date]
                vals = {
                    "payment_state": "paid",
                    "date_paid": max(dates) if dates else fields.Date.context_today(self),
                }
            elif states & {"partial", "paid", "in_payment"}:
                vals = {"payment_state": "partial", "date_paid": False}
            else:
                vals = {"payment_state": "unpaid", "date_paid": False}
            order.sudo().write(vals)


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def action_create_payments(self):
        res = super().action_create_payments()
        # Un pago registrado desde el backend de Odoo tambien mueve la orden.
        self.line_ids.mapped("move_id")._indigo_sync_orders()
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    indigo_order_id = fields.Many2one("indigo.order", string="Indigo order", index=True, copy=False)


class IndigoBilling(models.AbstractModel):
    """Lo que la app necesita para facturar. Cada metodo publico comprueba el
    rol y trabaja en sudo."""

    _name = "indigo.billing"
    _description = "Indigo invoicing service"

    # ------------------------------------------------------------ permisos

    def _assert_office(self):
        u = self.env.user
        if not (
            u._is_admin()
            or u.has_group("indigo_decors.group_indigo_manager")
            or u.has_group("indigo_decors.group_indigo_office")
        ):
            raise AccessError(_("Only the office or a manager can invoice."))

    def _assert_manager(self):
        u = self.env.user
        if not (u._is_admin() or u.has_group("indigo_decors.group_indigo_manager")):
            raise AccessError(_("Only a manager can change the invoicing setup."))

    # ------------------------------------------------------------ helpers

    def _param(self, key):
        return self.env["ir.config_parameter"].sudo().get_param(PARAM + key) or ISSUER_DEFAULTS.get(key, "")

    def _tax(self):
        return self.env.ref(TAX_XMLID, raise_if_not_found=False)

    def _product(self, code):
        return self.env["product.product"].sudo().with_context(active_test=False).search(
            [("default_code", "=", code)], limit=1
        )

    def _sequence(self):
        return self.env["ir.sequence"].sudo().search([("code", "=", SEQUENCE_CODE)], limit=1)

    def _sale_journal(self):
        company = self.env.company
        return self.env["account.journal"].sudo().search(
            [("type", "=", "sale"), ("company_id", "=", company.id)], limit=1
        )

    def _bank_journal(self):
        company = self.env.company
        return self.env["account.journal"].sudo().search(
            [("type", "=", "bank"), ("company_id", "=", company.id)], limit=1
        )

    def _missing(self):
        company = self.env.company.sudo()
        missing = []
        if not company.chart_template:
            missing.append("chart")
        if not self._tax():
            missing.append("tax")
        if not all(self._product(code) for code, _n in DOOR_PRODUCTS.values()):
            missing.append("products")
        if not self._sequence():
            missing.append("numbering")
        return missing

    def _ensure_ready(self):
        missing = self._missing()
        if missing:
            raise UserError(_(
                "Invoicing is not set up yet (missing: %s). A manager can set it up in Settings."
            ) % ", ".join(missing))

    def _range_rows(self):
        Range = self.env["indigo.install.range"].sudo()
        return [
            {
                "id": r.id,
                "name": r.name,
                "min_miles": r.min_miles,
                "max_miles": r.max_miles,
                "region": r.invoice_region or "",
                "fee": r.invoice_fee,
            }
            for r in Range.search([], order="sequence, min_miles")
        ]

    @staticmethod
    def _m2o(rec):
        return [rec.id, rec.display_name] if rec else False

    # ------------------------------------------------------------ setup

    @api.model
    def indigo_billing_status(self):
        self._assert_office()
        seq = self._sequence()
        tax = self._tax()
        return {
            "ready": not self._missing(),
            "missing": self._missing(),
            "next_number": seq.number_next_actual if seq else DEFAULT_NEXT_NUMBER,
            "tax_rate": tax.amount if tax else float(self._param("tax_rate") or 7),
            "issuer": {k: self._param(k) for k in ISSUER_DEFAULTS if k.startswith("issuer_")},
            "terms": self._param("terms"),
            "ranges": self._range_rows(),
            "templates": [{"value": k, "label": v} for k, v in DESCRIPTION_TEMPLATES],
            "can_setup": self.env.user._is_admin()
            or self.env.user.has_group("indigo_decors.group_indigo_manager"),
        }

    @api.model
    def indigo_billing_setup(self, vals=None):
        """Deja la contabilidad lista para facturar. Idempotente: lo que ya
        existe no se toca. Se lanza a mano desde Settings (gerente): en
        produccion cargar un plan de cuentas no es algo que deba pasar solo."""
        self._assert_manager()
        vals = vals or {}
        env = self.sudo().env
        company = env.company

        loaded_now = False
        if not company.chart_template:
            env["account.chart.template"].try_loading("generic_coa", company=company, install_demo=False)
            loaded_now = True

        rate = float(vals.get("tax_rate") or self._param("tax_rate") or 7)
        tax = self._tax()
        if not tax:
            tax_account = False
            ref_tax = company.account_sale_tax_id
            if ref_tax:
                rep = ref_tax.invoice_repartition_line_ids.filtered(lambda r: r.repartition_type == "tax")
                tax_account = rep[:1].account_id.id
            tax = env["account.tax"].create({
                "name": "FL Sales Tax %s%%" % ("%g" % rate),
                "amount": rate,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "company_id": company.id,
                "description": "Sales tax",
                "invoice_repartition_line_ids": [
                    (0, 0, {"repartition_type": "base"}),
                    (0, 0, {"repartition_type": "tax", "account_id": tax_account}),
                ],
                "refund_repartition_line_ids": [
                    (0, 0, {"repartition_type": "base"}),
                    (0, 0, {"repartition_type": "tax", "account_id": tax_account}),
                ],
            })
            env["ir.model.data"].create({
                "module": "indigo_decors",
                "name": "tax_fl_sales",
                "model": "account.tax",
                "res_id": tax.id,
                "noupdate": True,
            })
        # La empresa se queda SIN impuesto por defecto. Si lo tuviera, todo
        # producto creado despues lo heredaria, y eso incluye el que nace al
        # publicar un diseno en la tienda: el dealer veria el 7 % en el
        # carrito. El impuesto va solo en los productos de facturacion.
        company.write({"account_sale_tax_id": False, "account_purchase_tax_id": False})
        # Los impuestos genericos del plan de cuentas (15 %) no aplican en
        # Florida: se apagan mientras no los use ninguna linea.
        Tax = env["account.tax"].with_context(active_test=False)
        generic = Tax.search([("company_id", "=", company.id), ("id", "!=", tax.id), ("active", "=", True)])
        if not loaded_now:
            generic = generic.filtered(lambda t: abs(t.amount - 15.0) < 1e-6)
        for t in generic:
            if not env["account.move.line"].search_count([("tax_ids", "in", t.id)]):
                t.active = False

        Product = env["product.product"]
        for code, name in list(DOOR_PRODUCTS.values()) + [OTHER_PRODUCT]:
            if not self._product(code):
                Product.create({
                    "name": name,
                    "default_code": code,
                    "type": "service",
                    "sale_ok": True,
                    "purchase_ok": False,
                    "taxes_id": [(6, 0, [tax.id])],
                    "supplier_taxes_id": [(5, 0, 0)],
                })
        env["indigo.install.range"]._indigo_seed_invoice_fees()
        for rng in env["indigo.install.range"].search([("invoice_region", "!=", False)]):
            code = "IND-FEE-%s" % rng.invoice_region
            if not self._product(code):
                label = "INSTALLATION FEE" if rng.invoice_region == "A" else "INSTALLATION FEE %s" % rng.invoice_region
                Product.create({
                    "name": label,
                    "default_code": code,
                    "type": "service",
                    "sale_ok": True,
                    "purchase_ok": False,
                    "taxes_id": [(5, 0, 0)],
                    "supplier_taxes_id": [(5, 0, 0)],
                })

        if not self._sequence():
            env["ir.sequence"].create({
                "name": "Indigo invoice number (continues QuickBooks)",
                "code": SEQUENCE_CODE,
                "implementation": "no_gap",
                "prefix": "",
                "padding": 0,
                "number_increment": 1,
                "number_next": int(vals.get("next_number") or DEFAULT_NEXT_NUMBER),
                "company_id": False,
            })
        return self.indigo_billing_status()

    @api.model
    def indigo_billing_save_settings(self, vals):
        self._assert_manager()
        ICP = self.env["ir.config_parameter"].sudo()
        for key in ISSUER_DEFAULTS:
            if key in vals and key != "tax_rate":
                ICP.set_param(PARAM + key, (vals[key] or "").strip())
        if vals.get("next_number"):
            seq = self._sequence()
            n = int(vals["next_number"])
            if seq:
                last = self._last_number()
                if n <= last:
                    raise ValidationError(_(
                        "The next number must be higher than the last invoice issued here (%s)."
                    ) % last)
                seq.sudo().write({"number_next_actual": n})
        if vals.get("tax_rate") not in (None, ""):
            rate = float(vals["tax_rate"])
            ICP.set_param(PARAM + "tax_rate", "%g" % rate)
            tax = self._tax()
            if tax and abs(tax.amount - rate) > 1e-9:
                tax.sudo().write({"amount": rate, "name": "FL Sales Tax %g%%" % rate})
        for row in vals.get("ranges") or []:
            rng = self.env["indigo.install.range"].sudo().browse(int(row["id"])).exists()
            if rng:
                rng.write({
                    "invoice_region": (row.get("region") or "").strip().upper() or False,
                    "invoice_fee": float(row.get("fee") or 0.0),
                })
        return self.indigo_billing_status()

    def _next_invoice_number(self):
        """El siguiente numero libre. Si alguien emitio desde el backend de
        Odoo (que sigue su propio correlativo), la secuencia se adelanta a lo
        ya usado en vez de chocar con un numero repetido."""
        seq = self._sequence()
        last = self._last_number()
        if seq.number_next_actual <= last:
            seq.sudo().write({"number_next_actual": last + 1})
        journal = self._sale_journal()
        Move = self.env["account.move"].sudo()
        name = seq.next_by_id()
        while Move.search_count([("journal_id", "=", journal.id), ("name", "=", name)]):
            name = seq.next_by_id()
        return name

    def _last_number(self):
        journal = self._sale_journal()
        moves = self.env["account.move"].sudo().search(
            [("journal_id", "=", journal.id), ("state", "=", "posted"), ("move_type", "=", "out_invoice")]
        ) if journal else []
        nums = [int(m.name) for m in moves if (m.name or "").isdigit()]
        return max(nums) if nums else 0

    # ------------------------------------------------------------ facturar

    def _line_description(self, order, template):
        client = (order.client_name or "").strip()
        if template == "client_address":
            addr = (order.client_address or "").strip()
            return "%s\n%s" % (client, addr) if addr else client
        if template == "po":
            po = (order.customer_po or "").strip()
            return ("REF: PO %s %s" % (client, po)).strip()
        ref = (order.dealer_ref or "").strip()
        return "%s - %s" % (client, ref) if ref else client

    @api.model
    def indigo_billing_to_invoice(self):
        """Ordenes instaladas que todavia no estan en ninguna factura de la app,
        agrupadas por dealer."""
        self._assert_office()
        Order = self.env["indigo.order"].sudo()
        orders = Order.search([("stage_id.code", "=", "installed")], order="dealer_id, create_date")
        groups = {}
        for o in orders:
            if o.invoice_ids.filtered(lambda m: m.state != "cancel"):
                continue
            g = groups.setdefault(o.dealer_id.id, {
                "dealer": self._m2o(o.dealer_id),
                "orders": [],
                "total": 0.0,
            })
            g["orders"].append({
                "id": o.id,
                "name": o.name,
                "client_name": o.client_name,
                "dealer_ref": o.dealer_ref or False,
                "customer_po": o.customer_po or False,
                "door_count": o.door_count,
                "total": o.total_dealer_charge,
                "installed_on": o.installation_date and fields.Date.to_string(o.installation_date) or False,
                "zip_missing": not o.install_range_id,
            })
            g["total"] += o.total_dealer_charge or 0.0
        return sorted(groups.values(), key=lambda g: (g["dealer"] and g["dealer"][1]) or "")

    @api.model
    def indigo_billing_preview(self, order_ids):
        """Propuesta de factura para esas ordenes: lineas, fotos y avisos. No
        escribe nada: la app la muestra editable y luego llama a create_draft."""
        self._assert_office()
        orders = self.env["indigo.order"].sudo().browse(order_ids).exists()
        if not orders:
            raise UserError(_("Pick at least one order."))
        dealers = orders.mapped("dealer_id")
        if len(dealers) != 1:
            raise UserError(_("All the orders on one invoice must belong to the same dealer."))
        dealer = dealers
        template = dealer.indigo_invoice_description or "client"
        taxable_doors = not dealer.indigo_tax_exempt
        lines, photos, warnings = [], [], []
        for order in orders:
            already = order.invoice_ids.filtered(lambda m: m.state != "cancel")
            if already:
                warnings.append(_("%s is already on invoice %s.") % (order.name, ", ".join(already.mapped("name"))))
            desc = self._line_description(order, template)
            for line in order.line_ids:
                code, label = DOOR_PRODUCTS.get(line.door_type) or OTHER_PRODUCT
                lines.append({
                    "order_id": order.id,
                    "order_name": order.name,
                    "kind": "door",
                    "product_code": code,
                    "product_label": label,
                    "description": desc,
                    "qty": line.qty or 1,
                    "price_unit": line.unit_price,
                    "taxable": taxable_doors,
                })
            rng = order.install_range_id
            if not rng or not rng.invoice_region:
                warnings.append(_(
                    "%s has no distance range (ZIP missing or unknown): the installation fee is set to region A, check it."
                ) % order.name)
                region, fee, label = "A", 0.0, "Installation Fee Region A"
                a = self.env["indigo.install.range"].sudo().search([("invoice_region", "=", "A")], limit=1)
                if a:
                    fee = a.invoice_fee
                    label = "Installation Fee Region A %s" % (a.name or "")
            else:
                region, fee = rng.invoice_region, rng.invoice_fee
                label = "Installation Fee Region %s %s" % (region, rng.name or "")
            if not dealer.indigo_charge_install_fee:
                fee = 0.0
            lines.append({
                "order_id": order.id,
                "order_name": order.name,
                "kind": "fee",
                "product_code": "IND-FEE-%s" % region,
                "product_label": "INSTALLATION FEE" if region == "A" else "INSTALLATION FEE %s" % region,
                "description": " ".join(label.replace("millas", "miles").replace(" – ", "-").replace("–", "-").split()),
                "qty": 1,
                "price_unit": fee,
                "taxable": False,
            })
            since = order.installation_date
            for att in self.env["ir.attachment"].sudo().search(
                [("res_model", "=", "indigo.order"), ("res_id", "=", order.id), ("mimetype", "like", "image/")],
                order="create_date desc",
            ):
                created = att.create_date.date() if att.create_date else None
                photos.append({
                    "id": att.id,
                    "name": att.name,
                    "order_id": order.id,
                    "order_name": order.name,
                    "created": fields.Datetime.to_string(att.create_date) if att.create_date else False,
                    "default": bool(since and created and created >= since),
                })
        if not dealer.email and not dealer.indigo_invoice_emails:
            warnings.append(_("%s has no invoice email yet.") % dealer.name)
        return {
            "dealer": {
                "id": dealer.id,
                "name": dealer.name,
                "emails": dealer._indigo_invoice_recipients(),
                "tax_exempt": dealer.indigo_tax_exempt,
                "template": template,
                "address": dealer._display_address(without_company=True),
            },
            "order_ids": orders.ids,
            "lines": lines,
            "photos": photos,
            "warnings": warnings,
            "tax_rate": self._tax().amount if self._tax() else float(self._param("tax_rate") or 7),
            "ready": not self._missing(),
        }

    def _check_orders_free(self, orders, exclude=None):
        """Una orden solo puede estar en UNA factura viva (borrador o emitida).
        La vista previa ya avisaba, pero dejaba seguir: se podia cobrar dos
        veces la misma puerta."""
        for order in orders:
            busy = order.invoice_ids.filtered(lambda m: m.state != "cancel" and m != exclude)
            if busy:
                label = ", ".join(
                    ("#%s" % m.name) if m.state == "posted" else _("a draft") for m in busy
                )
                raise UserError(_(
                    "%s is already on %s. Void or delete that invoice before invoicing it again."
                ) % (order.name, label))

    def _check_photos(self, photo_ids, orders):
        """Solo fotos de las ordenes de la factura. El servicio trabaja en
        sudo: sin esto se podia meter en el PDF cualquier adjunto del sistema."""
        ids = [int(i) for i in photo_ids or []]
        if not ids:
            return []
        ok = self.env["ir.attachment"].sudo().search([
            ("id", "in", ids),
            ("res_model", "=", "indigo.order"),
            ("res_id", "in", orders.ids),
            ("mimetype", "like", "image/"),
        ])
        if len(ok) != len(set(ids)):
            raise UserError(_("Only photos of this invoice's orders can go on it."))
        return ok.ids

    def _line_commands(self, lines, orders):
        tax = self._tax()
        cmds = []
        for ln in lines:
            code = ln.get("product_code") or OTHER_PRODUCT[0]
            # Solo productos de facturacion (IND-...): con cualquier codigo se
            # podia facturar un producto de la tienda o de envio.
            if not str(code).startswith("IND-"):
                raise UserError(_("%s is not an invoice product.") % code)
            product = self._product(code)
            if not product:
                raise UserError(_("Invoice product %s is missing: run the invoicing setup.") % code)
            order_id = ln.get("order_id") or False
            if order_id and int(order_id) not in orders.ids:
                raise UserError(_("A line points to an order that is not on this invoice."))
            qty = float(ln.get("qty") or 1)
            if qty <= 0:
                raise ValidationError(_("Quantities must be positive."))
            cmds.append((0, 0, {
                "product_id": product.id,
                "name": (ln.get("description") or product.name).strip(),
                "quantity": qty,
                "price_unit": float(ln.get("price_unit") or 0.0),
                "tax_ids": [(6, 0, [tax.id] if (tax and ln.get("taxable")) else [])],
                "indigo_order_id": ln.get("order_id") or False,
            }))
        return cmds

    @api.model
    def indigo_billing_create_draft(self, vals):
        """vals: dealer_id, order_ids, lines [{product_code, description, qty,
        price_unit, taxable, order_id}], photo_ids, invoice_date (opcional)."""
        self._assert_office()
        self._ensure_ready()
        dealer = self.env["res.partner"].sudo().browse(int(vals["dealer_id"])).exists()
        if not dealer:
            raise UserError(_("Dealer not found."))
        lines = vals.get("lines") or []
        if not lines:
            raise UserError(_("The invoice needs at least one line."))
        orders = self.env["indigo.order"].sudo().browse(vals.get("order_ids") or []).exists()
        if orders.filtered(lambda o: o.dealer_id != dealer):
            raise UserError(_("All the orders on one invoice must belong to the same dealer."))
        self._check_orders_free(orders)
        photo_ids = self._check_photos(vals.get("photo_ids"), orders)
        line_cmds = self._line_commands(lines, orders)
        term = self.env.ref("account.account_payment_term_immediate", raise_if_not_found=False)
        move = self.env["account.move"].sudo().create({
            "move_type": "out_invoice",
            "partner_id": dealer.id,
            "journal_id": self._sale_journal().id,
            "invoice_date": vals.get("invoice_date") or fields.Date.context_today(self),
            "invoice_payment_term_id": term.id if term else False,
            "indigo_order_ids": [(6, 0, orders.ids)],
            "indigo_photo_ids": [(6, 0, photo_ids)],
            "invoice_line_ids": line_cmds,
        })
        move.message_post(body=_("Draft created from the Indigo app by %s.") % self.env.user.name)
        return move.id

    def _get_move(self, move_id, states=None):
        move = self.env["account.move"].sudo().browse(int(move_id)).exists()
        if not move or move.move_type != "out_invoice":
            raise UserError(_("Invoice not found."))
        if states and move.state not in states:
            raise UserError(_("This invoice can't be changed in its current state (%s).") % move.state)
        return move

    @api.model
    def indigo_billing_update_draft(self, move_id, vals):
        self._assert_office()
        move = self._get_move(move_id, states=("draft",))
        write = {}
        if "lines" in vals:
            write["invoice_line_ids"] = [(5, 0, 0)] + self._line_commands(vals["lines"] or [], move.indigo_order_ids)
        if "photo_ids" in vals:
            write["indigo_photo_ids"] = [(6, 0, self._check_photos(vals["photo_ids"], move.indigo_order_ids))]
        if vals.get("invoice_date"):
            write["invoice_date"] = vals["invoice_date"]
        move.write(write)
        return move.id

    @api.model
    def indigo_billing_delete_draft(self, move_id):
        self._assert_office()
        move = self._get_move(move_id, states=("draft",))
        if move.posted_before:
            raise UserError(_("This invoice was issued before: cancel it instead of deleting it."))
        move.unlink()
        return True

    @api.model
    def indigo_billing_post(self, move_id):
        """Emite la factura: le da el siguiente numero (el de QuickBooks), la
        contabiliza y pasa sus ordenes a «Invoiced / Paid»."""
        self._assert_office()
        self._ensure_ready()
        move = self._get_move(move_id, states=("draft",))
        if not move.invoice_line_ids:
            raise UserError(_("The invoice has no lines."))
        self._check_orders_free(move.indigo_order_ids, exclude=move)
        # Siempre el siguiente de NUESTRA secuencia (la de QuickBooks), aunque
        # el borrador ya traiga nombre: Odoo le pone "INV/2026/00001" a la
        # primera factura del diario desde que se crea. Una factura que ya se
        # emitio antes (anulada y vuelta a borrador) conserva su numero.
        if not move.posted_before:
            move.name = self._next_invoice_number()
        move.action_post()
        invoiced = self.env["indigo.stage"].sudo().search([("code", "=", "invoiced")], limit=1)
        now = fields.Datetime.now()
        for order in move.indigo_order_ids:
            vals = {}
            if invoiced and order.stage_id.code == "installed":
                vals["stage_id"] = invoiced.id
            if not order.invoiced_at:
                vals["invoiced_at"] = now
            if vals:
                order.write(vals)
        move._indigo_sync_orders()
        move.message_post(body=_("Invoice %s issued from the Indigo app by %s.") % (move.name, self.env.user.name))
        return self.indigo_billing_detail(move.id)

    @api.model
    def indigo_billing_void(self, move_id, reason=None):
        """Anula una factura emitida (como «Void» en QuickBooks). Conserva su
        numero, deja de contar y sus ordenes vuelven a «por facturar» para
        hacer la correcta. Con pagos registrados no: primero hay que quitarlos."""
        self._assert_office()
        move = self._get_move(move_id, states=("posted",))
        if move._get_reconciled_payments():
            raise UserError(_(
                "This invoice has payments recorded, so it can't be voided from the app. "
                "Ask a manager to remove the payments in Odoo first."
            ))
        move.button_draft()
        move.button_cancel()
        installed = self.env["indigo.stage"].sudo().search([("code", "=", "installed")], limit=1)
        for order in move.indigo_order_ids:
            alive = order.invoice_ids.filtered(lambda m: m.state == "posted")
            if not alive and installed and order.stage_id.code == "invoiced":
                order.write({"stage_id": installed.id, "invoiced_at": False})
        move._indigo_sync_orders()
        note = (" " + _("Reason: %s") % reason) if reason else ""
        move.message_post(body=_("Invoice %s voided from the Indigo app by %s.") % (move.name, self.env.user.name) + note)
        return self.indigo_billing_detail(move.id)

    @api.model
    def indigo_billing_pdf(self, move_id):
        self._assert_office()
        move = self._get_move(move_id)
        pdf, _fmt = self.env["ir.actions.report"].sudo()._render_qweb_pdf(
            "indigo_decors.action_report_indigo_invoice", move.ids
        )
        return {
            "filename": "Invoice %s.pdf" % (move.name if move.name and move.name != "/" else "draft"),
            "data": base64.b64encode(pdf).decode(),
        }

    @api.model
    def indigo_billing_send(self, move_id, emails, message=None):
        """Manda la factura (PDF con las fotos) a uno o varios correos. Solo a
        mano, desde el boton: los avisos automaticos al dealer siguen
        apagados por decision del cliente."""
        self._assert_office()
        move = self._get_move(move_id, states=("posted",))
        recipients = [e.strip() for e in (emails or []) if e and "@" in e]
        if not recipients:
            raise UserError(_("Add at least one email address."))
        pdf = self.indigo_billing_pdf(move.id)
        issuer = move._indigo_issuer()
        att = self.env["ir.attachment"].sudo().create({
            "name": pdf["filename"],
            "type": "binary",
            "datas": pdf["data"],
            "mimetype": "application/pdf",
            "res_model": "account.move",
            "res_id": move.id,
        })
        body = message or _(
            "<p>Hello,</p><p>Please find attached invoice %(num)s for %(amount)s.</p>"
            "<p>Thank you for your business.</p><p>%(issuer)s<br/>%(phone)s</p>"
        ) % {
            "num": move.name,
            "amount": "%s %.2f" % (move.currency_id.symbol or "$", move.amount_total),
            "issuer": issuer["issuer_name"],
            "phone": issuer["issuer_phone"],
        }
        Mail = self.env["mail.mail"].sudo()
        mail = Mail.create({
            "subject": _("Invoice %s from %s") % (move.name, issuer["issuer_name"]),
            "body_html": body,
            "email_to": ", ".join(recipients),
            "reply_to": issuer["issuer_email"],
            "attachment_ids": [(6, 0, [att.id])],
            "model": "account.move",
            "res_id": move.id,
            "auto_delete": False,
        })
        mail.send()
        failed = mail.state == "exception"
        move.write({
            "indigo_sent_at": fields.Datetime.now(),
            "indigo_sent_to": ", ".join(recipients),
        })
        move.message_post(
            body=_("Invoice sent to %s by %s.") % (", ".join(recipients), self.env.user.name),
            attachment_ids=[att.id],
        )
        if failed:
            raise UserError(_("The email could not be sent: %s") % (mail.failure_reason or "unknown error"))
        return self.indigo_billing_detail(move.id)

    @api.model
    def indigo_billing_register_payment(self, move_id, vals):
        """vals: amount, date, method (check, transfer, zelle, card, cash, other), reference."""
        self._assert_office()
        move = self._get_move(move_id, states=("posted",))
        amount = float(vals.get("amount") or 0.0)
        if amount <= 0:
            raise ValidationError(_("The amount must be greater than zero."))
        if amount - move.amount_residual > 0.005:
            raise ValidationError(_("The amount is higher than the balance due (%.2f).") % move.amount_residual)
        journal = self._bank_journal()
        if not journal:
            raise UserError(_("There is no bank journal: run the invoicing setup."))
        memo = " · ".join(filter(None, [(vals.get("method") or "").capitalize(), vals.get("reference")])) or move.name
        wizard = self.env["account.payment.register"].sudo().with_context(
            active_model="account.move", active_ids=move.ids
        ).create({
            "amount": amount,
            "payment_date": vals.get("date") or fields.Date.context_today(self),
            "journal_id": journal.id,
            "communication": "%s · %s" % (move.name, memo) if memo != move.name else move.name,
        })
        wizard.action_create_payments()
        move._indigo_sync_orders()
        return self.indigo_billing_detail(move.id)

    # ------------------------------------------------------------ leer

    def _row(self, m):
        return {
            "id": m.id,
            "name": m.name if m.name and m.name != "/" else False,
            "state": m.state,
            "status": m._indigo_status_label(),
            "payment_state": m.payment_state,
            "dealer": self._m2o(m.partner_id),
            "invoice_date": fields.Date.to_string(m.invoice_date) if m.invoice_date else False,
            "due_date": fields.Date.to_string(m.invoice_date_due) if m.invoice_date_due else False,
            "untaxed": m.amount_untaxed,
            "tax": m.amount_tax,
            "total": m.amount_total,
            "residual": m.amount_residual if m.state == "posted" else (m.amount_total if m.state == "draft" else 0.0),
            "order_names": m.indigo_order_ids.mapped("name"),
            "sent_at": fields.Datetime.to_string(m.indigo_sent_at) if m.indigo_sent_at else False,
        }

    @api.model
    def indigo_billing_detail(self, move_id):
        self._assert_office()
        m = self._get_move(move_id)
        row = self._row(m)
        payments = []
        for p in m._get_reconciled_payments():
            payments.append({
                "id": p.id,
                "date": fields.Date.to_string(p.date),
                "amount": p.amount,
                "memo": p.ref or "",
            })
        row.update({
            "lines": [
                {
                    "product_code": ln.product_id.default_code or "",
                    "product_label": (ln.product_id.name or "").upper(),
                    "description": ln.name or "",
                    "qty": ln.quantity,
                    "price_unit": ln.price_unit,
                    "subtotal": ln.price_subtotal,
                    "taxable": bool(ln.tax_ids),
                    "order_id": ln.indigo_order_id.id or False,
                }
                for ln in m.invoice_line_ids.filtered(lambda l: l.display_type == "product")
            ],
            "orders": [{"id": o.id, "name": o.name, "client_name": o.client_name} for o in m.indigo_order_ids],
            "photo_ids": m.indigo_photo_ids.ids,
            "payments": payments,
            "sent_to": m.indigo_sent_to or False,
            "dealer_emails": m.partner_id._indigo_invoice_recipients(),
            "dealer_address": m.partner_id._display_address(without_company=True),
        })
        return row

    @api.model
    def indigo_billing_list(self, filters=None):
        """filters: date_from, date_to (fecha de factura), dealer_id,
        status (draft|open|overdue|paid|all), q. Devuelve filas y el resumen
        del periodo, que es lo que Majela pidio ver «por fecha»."""
        self._assert_office()
        f = filters or {}
        domain = [("move_type", "=", "out_invoice")]
        if f.get("date_from"):
            domain.append(("invoice_date", ">=", f["date_from"]))
        if f.get("date_to"):
            domain.append(("invoice_date", "<=", f["date_to"]))
        if f.get("dealer_id"):
            domain.append(("partner_id", "=", int(f["dealer_id"])))
        status = f.get("status") or "all"
        today = fields.Date.context_today(self)
        if status == "draft":
            domain.append(("state", "=", "draft"))
        elif status == "paid":
            domain += [("state", "=", "posted"), ("payment_state", "in", ["paid", "in_payment"])]
        elif status == "open":
            domain += [("state", "=", "posted"), ("payment_state", "not in", ["paid", "in_payment", "reversed"])]
        elif status == "overdue":
            domain += [("state", "=", "posted"), ("payment_state", "not in", ["paid", "in_payment", "reversed"]),
                       ("invoice_date_due", "<", today)]
        if f.get("q"):
            q = f["q"].strip()
            domain += ["|", "|", ("name", "ilike", q), ("partner_id.name", "ilike", q),
                       ("indigo_order_ids.client_name", "ilike", q)]
        moves = self.env["account.move"].sudo().search(domain, order="invoice_date desc, id desc", limit=500)
        posted = moves.filtered(lambda m: m.state == "posted")
        summary = {
            "count": len(posted),
            "drafts": len(moves) - len(posted),
            "untaxed": sum(posted.mapped("amount_untaxed")),
            "tax": sum(posted.mapped("amount_tax")),
            "total": sum(posted.mapped("amount_total")),
            "open": sum(posted.mapped("amount_residual")),
            "collected": sum(posted.mapped("amount_total")) - sum(posted.mapped("amount_residual")),
        }
        return {"rows": [self._row(m) for m in moves], "summary": summary}

    @api.model
    def indigo_billing_dealer_statement(self, dealer_id):
        """La ficha de cliente de QuickBooks: saldo abierto, vencido y movimientos."""
        self._assert_office()
        dealer = self.env["res.partner"].sudo().browse(int(dealer_id)).exists()
        if not dealer:
            raise UserError(_("Dealer not found."))
        moves = self.env["account.move"].sudo().search(
            [("move_type", "=", "out_invoice"), ("partner_id", "=", dealer.id), ("state", "=", "posted")],
            order="invoice_date desc, id desc",
        )
        today = fields.Date.context_today(self)
        events = []
        for m in moves:
            events.append({
                "kind": "invoice",
                "id": m.id,
                "date": fields.Date.to_string(m.invoice_date),
                "label": _("Invoice #%s") % m.name,
                "amount": m.amount_total,
                "status": m._indigo_status_label(),
            })
            for p in m._get_reconciled_payments():
                events.append({
                    "kind": "payment",
                    "id": p.id,
                    "date": fields.Date.to_string(p.date),
                    "label": _("Invoice Payment #%s") % m.name,
                    "amount": -p.amount,
                    "status": "",
                })
        events.sort(key=lambda e: (e["date"] or "", e["kind"] == "invoice"), reverse=True)
        open_moves = moves.filtered(lambda m: m.amount_residual > 0)
        return {
            "dealer": {
                "id": dealer.id,
                "name": dealer.name,
                "emails": dealer._indigo_invoice_recipients(),
                "phone": dealer.phone or False,
                "address": dealer._display_address(without_company=True),
                "tax_exempt": dealer.indigo_tax_exempt,
                "template": dealer.indigo_invoice_description or "client",
            },
            "open_balance": sum(open_moves.mapped("amount_residual")),
            "overdue": sum(open_moves.filtered(
                lambda m: (m.invoice_date_due or m.invoice_date) and (m.invoice_date_due or m.invoice_date) < today
            ).mapped("amount_residual")),
            "events": events,
        }

    @api.model
    def indigo_billing_dealer_settings(self, dealer_id, vals):
        self._assert_office()
        dealer = self.env["res.partner"].sudo().browse(int(dealer_id)).exists()
        if not dealer:
            raise UserError(_("Dealer not found."))
        write = {}
        if "emails" in vals:
            write["indigo_invoice_emails"] = (vals["emails"] or "").strip() or False
        if "tax_exempt" in vals:
            write["indigo_tax_exempt"] = bool(vals["tax_exempt"])
        if vals.get("template") in dict(DESCRIPTION_TEMPLATES):
            write["indigo_invoice_description"] = vals["template"]
        dealer.write(write)
        return self.indigo_billing_dealer_statement(dealer.id)["dealer"]
