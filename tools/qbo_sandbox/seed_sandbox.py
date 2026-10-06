#!/usr/bin/env python3
"""Deja el SANDBOX de QuickBooks parecido a la empresa de Indigo para probar.

Solo escribe en la empresa de prueba de Intuit (el realm de .qbo-tokens.json,
obtenido con qbo_sandbox.py contra el sandbox). Idempotente: busca antes de
crear, asi que se puede ejecutar varias veces.

  1. Enciende los numeros de factura propios (Custom transaction numbers),
     para que la factura lleve el numero de Indigo (DocNumber).
  2. Crea los productos de factura de Indigo (mismos nombres que en el PDF).
  3. Crea dealers de prueba con direccion en Miami.
  4. Con --probe, crea una factura de prueba #9001 y muestra el impuesto que
     calcula QuickBooks.

Uso:  py tools/qbo_sandbox/seed_sandbox.py [--probe]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qbo_sandbox as q  # noqa: E402

API_HOST = q.API_BASE
assert "sandbox-quickbooks" in API_HOST, "Este script solo escribe en el SANDBOX."

DOOR_ACCOUNT = "Sales of Product Income"
FEE_ACCOUNT = "Installation"
ITEMS = [
    ("DESIGN SINGLE DOOR", True, DOOR_ACCOUNT),
    ("DESIGN DOUBLE DOOR", True, DOOR_ACCOUNT),
    ("DESIGN DOOR WITH SIDELITES", True, DOOR_ACCOUNT),
    ("PRODUCTION", True, DOOR_ACCOUNT),
    ("INSTALLATION FEE", False, FEE_ACCOUNT),
    ("INSTALLATION FEE B", False, FEE_ACCOUNT),
    ("INSTALLATION FEE C", False, FEE_ACCOUNT),
    ("INSTALLATION FEE D", False, FEE_ACCOUNT),
]
CUSTOMERS = ["Locktight", "Safeguard Impact", "USA Windows"]
MIAMI = {"Line1": "7820 NW 33rd Street", "City": "Doral", "CountrySubDivisionCode": "FL", "PostalCode": "33122", "Country": "USA"}


def esc(s):
    return s.replace("'", "\\'")


def account_id(name):
    rows = q.query("SELECT Id FROM Account WHERE Name = '%s'" % esc(name)).get("Account", [])
    if not rows:
        raise q.QboError("No existe la cuenta de ingresos '%s' en el sandbox." % name)
    return rows[0]["Id"]


def enable_custom_numbers():
    pref = q.api_get("preferences")["Preferences"]
    if pref.get("SalesFormsPrefs", {}).get("CustomTxnNumbers"):
        print("Custom transaction numbers: ya encendido")
        return
    q.api_post("preferences", {
        "SyncToken": pref["SyncToken"],
        "sparse": True,
        "SalesFormsPrefs": {"CustomTxnNumbers": True},
    })
    print("Custom transaction numbers: ENCENDIDO")


def ensure_items():
    ids = {}
    acc = {name: account_id(name) for name in {DOOR_ACCOUNT, FEE_ACCOUNT}}
    for name, taxable, account in ITEMS:
        rows = q.query("SELECT Id FROM Item WHERE Name = '%s'" % esc(name)).get("Item", [])
        if rows:
            ids[name] = rows[0]["Id"]
            print("producto ya existe: %s (%s)" % (name, ids[name]))
            continue
        res = q.api_post("item", {
            "Name": name, "Type": "Service", "Taxable": taxable,
            "IncomeAccountRef": {"value": acc[account]},
        })["Item"]
        ids[name] = res["Id"]
        print("producto creado: %s (%s) taxable=%s" % (name, res["Id"], taxable))
    return ids


def ensure_customers():
    ids = {}
    for name in CUSTOMERS:
        rows = q.query("SELECT Id FROM Customer WHERE DisplayName = '%s'" % esc(name)).get("Customer", [])
        if rows:
            ids[name] = rows[0]["Id"]
            print("cliente ya existe: %s (%s)" % (name, ids[name]))
            continue
        res = q.api_post("customer", {
            "DisplayName": name, "CompanyName": name,
            "BillAddr": dict(MIAMI), "ShipAddr": dict(MIAMI),
            "PrimaryEmailAddr": {"Address": "test+%s@example.com" % name.lower().replace(" ", "")},
        })["Customer"]
        ids[name] = res["Id"]
        print("cliente creado: %s (%s)" % (name, res["Id"]))
    return ids


def probe_invoice(items, customers):
    rows = q.query("SELECT * FROM Invoice WHERE DocNumber = '9001'").get("Invoice", [])
    if rows:
        inv = rows[0]
        print("factura de prueba ya existe: #%s" % inv["DocNumber"])
    else:
        inv = q.api_post("invoice", {
            "DocNumber": "9001",
            "CustomerRef": {"value": customers["Locktight"]},
            "PrivateNote": "Indigo #9001 · PO TEST 123456",
            "Line": [
                {"DetailType": "SalesItemLineDetail", "Amount": 600.00, "Description": "REF: PO TEST 123456",
                 "SalesItemLineDetail": {"ItemRef": {"value": items["DESIGN DOUBLE DOOR"]}, "Qty": 1,
                                         "UnitPrice": 600.00, "TaxCodeRef": {"value": "TAX"}}},
                {"DetailType": "SalesItemLineDetail", "Amount": 70.00, "Description": "Installation Fee Region C 45-90 miles",
                 "SalesItemLineDetail": {"ItemRef": {"value": items["INSTALLATION FEE C"]}, "Qty": 1,
                                         "UnitPrice": 70.00, "TaxCodeRef": {"value": "NON"}}},
            ],
        })["Invoice"]
        print("factura de prueba creada: #%s (Id %s)" % (inv["DocNumber"], inv["Id"]))
    tax = (inv.get("TxnTaxDetail") or {}).get("TotalTax")
    print("  subtotal %s | impuesto QBO %s | total %s | (Indigo: impuesto 42.00, total 712.00)" % (
        sum(l.get("Amount", 0) for l in inv["Line"] if l.get("DetailType") == "SalesItemLineDetail"),
        tax, inv.get("TotalAmt")))


def main():
    try:
        enable_custom_numbers()
        items = ensure_items()
        customers = ensure_customers()
        if "--probe" in sys.argv:
            probe_invoice(items, customers)
    except q.QboError as e:
        print("ERROR:", e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
