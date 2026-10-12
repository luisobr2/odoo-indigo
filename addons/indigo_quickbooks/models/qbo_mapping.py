# -*- coding: utf-8 -*-
"""Equivalencias entre Indigo y QuickBooks.

Cada dealer necesita su cliente en QBO, y cada producto de factura de Indigo
(IND-SD, IND-FEE-B, ...) su producto en QBO. Se guardan en el propio registro
(id y nombre, para mostrarlo sin llamar a QBO). Emparejar automatico solo
rellena lo vacio y por nombre exacto (sin mayusculas ni espacios de mas): lo
que alguien eligio a mano no se toca.
"""
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

PAGE = 1000


def _norm(name):
    return re.sub(r"\s+", " ", (name or "").strip()).lower()


def _esc(value):
    return (value or "").replace("\\", "\\\\").replace("'", "\\'")


class ResPartner(models.Model):
    _inherit = "res.partner"

    qbo_customer_id = fields.Char(string="QuickBooks customer id", copy=False)
    qbo_customer_name = fields.Char(string="QuickBooks customer", copy=False)


class ProductProduct(models.Model):
    _inherit = "product.product"

    qbo_item_id = fields.Char(string="QuickBooks item id", copy=False)
    qbo_item_name = fields.Char(string="QuickBooks item", copy=False)


class IndigoQboMapping(models.AbstractModel):
    _inherit = "indigo.qbo"

    # ------------------------------------------------------------ locales

    def _qbo_dealers(self):
        return self.env["res.partner"].sudo().search([("is_indigo_dealer", "=", True)], order="name")

    def _qbo_products(self):
        return self.env["product.product"].sudo().with_context(active_test=False).search(
            [("default_code", "=like", "IND-%")], order="default_code")

    @staticmethod
    def _qbo_taxable(product):
        # Las puertas y PRODUCTION llevan sales tax; el recargo de instalacion no.
        return not (product.default_code or "").startswith("IND-FEE")

    @api.model
    def qbo_mapping_list(self):
        self._assert_office()
        return {
            "dealers": [{
                "id": p.id, "name": p.name,
                "qbo_id": p.qbo_customer_id or False, "qbo_name": p.qbo_customer_name or False,
            } for p in self._qbo_dealers()],
            "products": [{
                "id": p.id, "code": p.default_code, "label": p.name, "taxable": self._qbo_taxable(p),
                "qbo_id": p.qbo_item_id or False, "qbo_name": p.qbo_item_name or False,
            } for p in self._qbo_products()],
            "tax_code": {
                "id": self._icp().get_param("indigo_qbo.tax_code_id") or False,
                "name": self._icp().get_param("indigo_qbo.tax_code_name") or False,
            },
        }

    # ------------------------------------------------------------ remotos

    def _qbo_query_all(self, select, entity):
        rows, start = [], 1
        client = self._client()
        while True:
            page = client.query("%s STARTPOSITION %d MAXRESULTS %d" % (select, start, PAGE), entity)
            rows += page
            if len(page) < PAGE:
                return rows
            start += PAGE

    @api.model
    def qbo_remote_list(self, kind):
        """Clientes, productos o cuentas de ingresos de QBO, para elegir."""
        self._assert_office()
        if kind == "customers":
            rows = self._qbo_query_all("SELECT Id, DisplayName FROM Customer WHERE Active = true", "Customer")
            return [{"id": r["Id"], "name": r.get("DisplayName") or ""} for r in rows]
        if kind == "items":
            rows = self._qbo_query_all("SELECT Id, Name, Type FROM Item WHERE Active = true", "Item")
            return [{"id": r["Id"], "name": r.get("Name") or "", "type": r.get("Type")} for r in rows]
        if kind == "accounts":
            rows = self._qbo_query_all("SELECT Id, Name FROM Account WHERE AccountType = 'Income'", "Account")
            return [{"id": r["Id"], "name": r.get("Name") or ""} for r in rows]
        if kind == "taxcodes":
            # Solo los codigos de verdad (con numero); TAX, NON y
            # CustomSalesTax son marcas de linea, no un impuesto.
            rows = self._qbo_query_all("SELECT Id, Name, Active FROM TaxCode", "TaxCode")
            return [{"id": r["Id"], "name": r.get("Name") or ""} for r in rows
                    if str(r.get("Id", "")).isdigit() and r.get("Active", True) is not False]
        raise UserError(_("Unknown list: %s") % kind)

    # ------------------------------------------------------------ emparejar

    @api.model
    def qbo_mapping_auto(self):
        self._assert_office()
        customers = {}
        for r in self._qbo_query_all("SELECT Id, DisplayName FROM Customer WHERE Active = true", "Customer"):
            customers.setdefault(_norm(r.get("DisplayName")), r)
        items = {}
        for r in self._qbo_query_all("SELECT Id, Name, Type FROM Item WHERE Active = true", "Item"):
            items.setdefault(_norm(r.get("Name")), r)
        matched = {"dealers": 0, "products": 0}
        missing = {"dealers": [], "products": []}
        for p in self._qbo_dealers().filtered(lambda d: not d.qbo_customer_id):
            r = customers.get(_norm(p.name))
            if r:
                p.write({"qbo_customer_id": r["Id"], "qbo_customer_name": r.get("DisplayName")})
                matched["dealers"] += 1
            else:
                missing["dealers"].append(p.name)
        for p in self._qbo_products().filtered(lambda x: not x.qbo_item_id):
            r = items.get(_norm(p.name))
            if r:
                p.write({"qbo_item_id": r["Id"], "qbo_item_name": r.get("Name")})
                matched["products"] += 1
            else:
                missing["products"].append(p.default_code)
        return {"matched": matched, "missing": missing}

    def _qbo_local(self, kind, local_id):
        """Solo dealers y productos de factura (IND-...): nada mas se empareja."""
        if kind == "dealer":
            rec = self._qbo_dealers().filtered(lambda p: p.id == int(local_id))
        elif kind == "product":
            rec = self._qbo_products().filtered(lambda p: p.id == int(local_id))
        else:
            raise UserError(_("Unknown mapping: %s") % kind)
        if not rec:
            raise UserError(_("Not found."))
        return rec

    @staticmethod
    def _qbo_check_id(value, what):
        # Los ids de QBO son numeros; otra cosa iria a parar a la URL de la API.
        if not str(value).isdigit():
            raise UserError(_("That isn't a valid QuickBooks %s.") % what)
        return str(value)

    @api.model
    def qbo_tax_code_set(self, code_id):
        """El codigo de impuesto de QBO con que van las facturas con impuesto
        (p. ej. el de Florida). Vacio: QBO usa su calculo automatico y solo se
        le fija el total de impuesto, que basta en las empresas con Automated
        Sales Tax."""
        self._assert_office()
        icp = self._icp()
        if not code_id:
            icp.set_param("indigo_qbo.tax_code_id", "")
            icp.set_param("indigo_qbo.tax_code_name", "")
            return self.qbo_mapping_list()
        code_id = self._qbo_check_id(code_id, "tax code")
        r = self._client().get("taxcode/%s" % code_id).get("TaxCode") or {}
        icp.set_param("indigo_qbo.tax_code_id", code_id)
        icp.set_param("indigo_qbo.tax_code_name", r.get("Name") or "")
        return self.qbo_mapping_list()

    @api.model
    def qbo_mapping_set(self, kind, local_id, qbo_id):
        """Elegir a mano su par en QBO (o quitarlo con qbo_id vacio)."""
        self._assert_office()
        rec = self._qbo_local(kind, local_id)
        if not qbo_id:
            vals = {"qbo_customer_id": False, "qbo_customer_name": False} if kind == "dealer" \
                else {"qbo_item_id": False, "qbo_item_name": False}
            rec.write(vals)
            return self.qbo_mapping_list()
        qbo_id = self._qbo_check_id(qbo_id, "customer" if kind == "dealer" else "product")
        if kind == "dealer":
            r = self._client().get("customer/%s" % qbo_id).get("Customer") or {}
            rec.write({"qbo_customer_id": qbo_id, "qbo_customer_name": r.get("DisplayName") or ""})
        else:
            r = self._client().get("item/%s" % qbo_id).get("Item") or {}
            rec.write({"qbo_item_id": qbo_id, "qbo_item_name": r.get("Name") or ""})
        return self.qbo_mapping_list()

    @api.model
    def qbo_mapping_create_remote(self, kind, local_id, income_account_id=None):
        """Crear en QBO el cliente o producto que falta y emparejarlo. Si ya
        existe uno con ese nombre, se empareja con ese (QBO no admite dos
        clientes con el mismo nombre, y duplicar seria peor)."""
        self._assert_office()
        rec = self._qbo_local(kind, local_id)
        if income_account_id:
            income_account_id = self._qbo_check_id(income_account_id, "account")
        client = self._client()
        if kind == "dealer":
            found = client.query("SELECT Id, DisplayName FROM Customer WHERE DisplayName = '%s'" % _esc(rec.name), "Customer")
            if found:
                rec.write({"qbo_customer_id": found[0]["Id"], "qbo_customer_name": found[0].get("DisplayName")})
                return dict(self.qbo_mapping_list(), outcome="matched")
            emails = rec._indigo_invoice_recipients() if hasattr(rec, "_indigo_invoice_recipients") else []
            body = {"DisplayName": rec.name, "CompanyName": rec.name}
            if emails:
                body["PrimaryEmailAddr"] = {"Address": emails[0]}
            if rec.street or rec.city:
                body["BillAddr"] = {
                    "Line1": rec.street or "", "City": rec.city or "",
                    "CountrySubDivisionCode": rec.state_id.code or "", "PostalCode": rec.zip or "",
                }
            if rec.phone:
                body["PrimaryPhone"] = {"FreeFormNumber": rec.phone}
            r = client.post("customer", body).get("Customer") or {}
            rec.write({"qbo_customer_id": r.get("Id"), "qbo_customer_name": r.get("DisplayName")})
            return dict(self.qbo_mapping_list(), outcome="created")
        # producto
        found = client.query("SELECT Id, Name FROM Item WHERE Name = '%s'" % _esc(rec.name), "Item")
        if found:
            rec.write({"qbo_item_id": found[0]["Id"], "qbo_item_name": found[0].get("Name")})
            return dict(self.qbo_mapping_list(), outcome="matched")
        if not income_account_id:
            raise UserError(_("Choose the QuickBooks income account for %s.") % rec.name)
        r = client.post("item", {
            "Name": rec.name,
            "Type": "Service",
            "Taxable": self._qbo_taxable(rec),
            "IncomeAccountRef": {"value": str(income_account_id)},
        }).get("Item") or {}
        rec.write({"qbo_item_id": r.get("Id"), "qbo_item_name": r.get("Name")})
        return dict(self.qbo_mapping_list(), outcome="created")
