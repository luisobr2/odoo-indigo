# indigo_decors

Módulo Odoo 17 a medida de Indigo Decors: toda la lógica del taller. El panel
(`indigo-next`) y el asistente IA lo usan por JSON-RPC con la sesión de cada
persona; la tienda (`indigo_theme`) también lo usa para los pedidos de dealers.
Contexto completo en el `CLAUDE.md` de la raíz del repo.

## Modelos principales (`models/`)

| Modelo | Archivo | Para qué |
|---|---|---|
| `indigo.order`, `indigo.order.line` | `indigo_order.py`, `indigo_order_line.py` | La orden (un cliente final) y sus puertas |
| `indigo.stage` | `indigo_stage.py`, `indigo_paint_shops.py` | Etapas del flujo (dos de pintura: Michel e Indigo) |
| `indigo.order.incident`, `indigo.hold.reason` | | Incidencias y motivos de espera |
| `indigo.design`, `indigo.design.price`, `indigo.brand` | | Catálogo de diseños y precios |
| `indigo.install.zone`, `indigo.install.range`, `indigo.zip.geo` | | Zonas y tarifa de instalación por distancia |
| `indigo.contractor.rate`, `indigo.payout` | | Reglas de pago al equipo y liquidaciones |
| `indigo.expense`, `indigo.costing` | `indigo_costing.py` | Gastos, costo por puerta y margen |
| `indigo.stock` | `indigo_stock.py` | Puertas en inventario |
| `indigo.billing` | `indigo_invoicing.py` | Facturación desde la app (y Customer PO normalizado) |
| `indigo.audit.log` | `indigo_audit.py` | Registro de actividad (quién hizo qué) |
| `res.partner` (dealer), `res.users` | `indigo_dealer.py`, `indigo_team.py`, `res_users_mcp_key.py` | Dealers, equipo y claves del asistente |

La integración con QuickBooks Online es un módulo aparte: `addons/indigo_quickbooks`.

## Reportes QWeb (`reports/`)

Ficha de orden, etiqueta del diseñador, hoja del pintor, direcciones de
instalación, liquidación y factura.

## Pruebas

`tests/` (TransactionCase, etiqueta `indigo`). Cómo correrlas en local: ver
`docs/DEPLOY.md` → «Antes».

## Versiones y migraciones

La versión está en `__manifest__.py`. Un cambio que necesita transformar datos
sube la versión y añade `migrations/<versión>/post-migrate.py` (idempotente);
corre en el `-u indigo_decors` del despliegue.
