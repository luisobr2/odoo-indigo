# Integración con QuickBooks Online — plan de implementación

> **Para quien lo ejecute:** se implementa tarea por tarea, en orden. Cada tarea
> termina con pruebas en verde y un commit. Los pasos usan casillas (`- [ ]`).

**Objetivo:** que cada factura emitida en Indigo aparezca sola en QuickBooks
Online con el mismo número, y que los cobros registrados en QuickBooks vuelvan
solos a Indigo.

**Arquitectura:** un módulo Odoo nuevo, `indigo_quickbooks` (depende de
`indigo_decors`), con un cliente HTTP de QBO, la conexión OAuth, las
equivalencias, el envío de facturas, la recepción de cobros (webhook + CDC) y
tareas programadas. El panel Next (`indigo-next`) añade la tarjeta de Settings,
la pantalla de equivalencias y el estado en cada factura, hablando con el
servicio `indigo.qbo` como Billing habla con `indigo.billing`.

**Stack:** Odoo 17 (Python, `requests`), Next 16 (App Router), QBO Accounting
API v3 (`minorversion=75`), OAuth 2.0 de Intuit.

**Spec:** `docs/superpowers/specs/2026-10-06-quickbooks-integration-design.md`.
Herramientas de prueba: `tools/qbo_sandbox/` (conexión y sandbox ya preparado:
custom numbers encendido, productos de Indigo, dealers de prueba).

## Restricciones globales

- **El repo es público.** Ni secretos ni nombres de dealers ni cifras del
  negocio en código, pruebas o commits. Secretos solo como variables de entorno
  del contenedor (`QBO_CLIENT_ID`, `QBO_CLIENT_SECRET`, `QBO_WEBHOOK_VERIFIER`,
  `QBO_ENVIRONMENT=sandbox|production`) o en `.env.qbo` local (ignorado).
- **Nunca escribir en la empresa real de QBO** hasta la tarea 10, con OK explícito.
- **Indigo manda en las facturas, QBO en los cobros.** Una factura enlazada (metida
  a mano en QBO) nunca se sobrescribe; se marca `mismatch`.
- **Todo idempotente:** buscar antes de crear (`DocNumber`, `qbo_payment_id`).
- QBO no envía correos (`EmailStatus = "NotSet"`); el envío sigue en Indigo.
- Solo **gerencia** conecta/desconecta; **oficina y gerencia** ven estados y reintentan.
- El impuesto queda como en el spec (§2): `TaxCodeRef` `TAX`/`NON` por línea y
  `mismatch` si el total de QBO difiere. Decidirlo antes de la tarea 10.
- Pruebas Odoo:
  `MSYS_NO_PATHCONV=1 docker exec indigo-odoo odoo -c /etc/odoo/odoo.conf -d indigo-prod --no-http --stop-after-init --http-port=8099 --test-enable --test-tags /indigo_quickbooks -i indigo_quickbooks`
  (después `-u indigo_quickbooks`). Pruebas panel: `npm test` en `indigo-next`.
- Ninguna prueba llama a Intuit: el cliente HTTP se simula (`unittest.mock.patch`).
- Tras cambiar modelos Python en local: `docker restart indigo-odoo`.

## Archivos

```
addons/indigo_quickbooks/
  __init__.py, __manifest__.py
  security/ir.model.access.csv
  data/ir_cron.xml                    # envío pendiente (5 min), cobros CDC (15 min)
  models/__init__.py
  models/qbo_client.py                # indigo.qbo.client: tokens, HTTP, errores
  models/qbo_service.py               # indigo.qbo: estado, ajustes, equivalencias, backfill
  models/qbo_invoice.py               # account.move: campos qbo_*, armar y enviar
  models/qbo_payment.py               # cobros: aplicar Payment de QBO a la factura
  models/qbo_event.py                 # indigo.qbo.event: cola de avisos del webhook
  models/qbo_hooks.py                 # engancha post/reopen/void/register_payment de indigo.billing
  controllers/main.py                 # /indigo/qbo/connect, /callback, /webhook
  tests/test_qbo_client.py, test_qbo_oauth.py, test_qbo_mapping.py,
  tests/test_qbo_invoice.py, test_qbo_payments.py, test_qbo_backfill.py
indigo-next/
  src/lib/quickbooks/server.ts        # qboCall() como billingCall()
  src/app/api/quickbooks/...          # status, settings, mappings, retry, backfill
  src/app/(app)/settings/...          # tarjeta QuickBooks
  src/app/(app)/billing/quickbooks/page.tsx   # equivalencias + backfill
  src/components/billing/qbo-badge.tsx
```

---

### Tarea 1: Esqueleto del módulo

**Archivos:** crear `addons/indigo_quickbooks/{__init__,__manifest__}.py`,
`models/__init__.py`, `security/ir.model.access.csv`, `tests/__init__.py`.

- [ ] Manifest: `'name': 'Indigo QuickBooks'`, `'version': '17.0.1.0.0'`,
  `'depends': ['indigo_decors', 'account']`, `'license': 'LGPL-3'`,
  `'data': ['security/ir.model.access.csv', 'data/ir_cron.xml']`, `'installable': True`.
- [ ] Prueba mínima `test_module_installed`: `self.env['ir.module.module'].search([('name','=','indigo_quickbooks')]).state == 'installed'`.
- [ ] Instalar en local con `-i indigo_quickbooks`, pruebas en verde.
- [ ] Commit `feat(quickbooks): esqueleto del modulo`.

### Tarea 2: Cliente de QBO (`indigo.qbo.client`)

**Archivos:** `models/qbo_client.py`, `tests/test_qbo_client.py`.

Produce (lo usan las demás tareas):
- `QboError(UserError)` con `code` (`not_connected`, `auth`, `rate_limit`, `api`, `network`).
- `client._config()` → `{client_id, client_secret, verifier, environment}` desde `os.environ`; falta algo → `QboError('not_configured')`.
- `client._urls()` → base API `https://sandbox-quickbooks.api.intuit.com` o `https://quickbooks.api.intuit.com`; token `https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer`; revoke `https://developer.api.intuit.com/v2/oauth2/tokens/revoke`; authorize `https://appcenter.intuit.com/connect/oauth2`.
- Tokens en `ir.config_parameter` (sudo): `indigo_qbo.realm_id`, `.access_token`, `.refresh_token`, `.access_expires_at`, `.refresh_expires_at`, `.company_name`.
- `client.save_tokens(data, realm_id=None)`, `client.access_token()` (renueva si faltan < 60 s; guarda SIEMPRE el refresh token nuevo), `client.get(path, params)`, `client.post(path, body, params)`, `client.query(sql)`, `client.revoke()`.
- 401 → renovar y reintentar una vez; `invalid_grant` al renovar → borrar tokens y `QboError('auth', 'Hay que reconectar QuickBooks')`; 429 → `QboError('rate_limit')`; ≥400 → `QboError('api', '<Fault.Error[0].Message> (intuit_tid=…)')`; `requests.RequestException` → `QboError('network')`. Siempre `?minorversion=75`, `timeout=30`.

- [ ] Pruebas primero (con `patch('requests.post')`/`patch('requests.get')`):
  token vigente no llama a Intuit; token vencido renueva y guarda el refresh nuevo;
  401 renueva y reintenta una vez; `invalid_grant` deja `not_connected`;
  429 → `rate_limit`; error 400 de QBO trae el mensaje y el `intuit_tid`.
- [ ] Implementar (base: `tools/qbo_sandbox/qbo_sandbox.py`, ya probado contra el sandbox).
- [ ] Pruebas en verde. Commit `feat(quickbooks): cliente de la API con tokens y errores`.

### Tarea 3: Conexión OAuth (controladores)

**Archivos:** `controllers/main.py`, `models/qbo_service.py` (parte), `tests/test_qbo_oauth.py`.

- `GET /indigo/qbo/connect` (`auth='user'`): solo `group_indigo_manager` o admin
  (si no, 403). Genera `state` aleatorio, lo guarda con caducidad 10 min en
  `indigo_qbo.oauth_state` (valor + expiración + uid) y redirige a authorize con
  `scope=com.intuit.quickbooks.accounting`, `redirect_uri=<web.base.url>/indigo/qbo/callback`.
- `GET /indigo/qbo/callback`: compara `state` (y que no caducó, mismo uid), canjea
  el `code`, guarda tokens y `realmId`, lee `CompanyInfo` para guardar el nombre,
  deja un mensaje en el log y redirige a `<PANEL_URL>/settings?qbo=connected`
  (`PANEL_URL` del entorno, por defecto `https://app.indigodecors.com`).
  `error=access_denied` → redirige con `?qbo=denied`.
- `indigo.qbo.qbo_disconnect()` (gerencia): revoca y borra tokens.
- `indigo.qbo.qbo_status()` (oficina/gerencia): `{configured, connected, environment, company_name, realm_id, connected_at, last_push_at, last_payment_at, pending, errors, mismatches, auto_close}`.

- [ ] Pruebas primero: `state` distinto o caducado → no guarda nada; callback
  correcto (token y CompanyInfo simulados) guarda realm y nombre; usuario sin
  gerencia → 403; `qbo_status` sin configuración → `configured=False`.
- [ ] Implementar. Pruebas en verde. Commit `feat(quickbooks): conectar y desconectar`.

### Tarea 4: Settings en el panel

**Archivos (indigo-next):** `src/lib/quickbooks/server.ts`,
`src/app/api/quickbooks/{status,settings,disconnect}/route.ts`, tarjeta en
`src/app/(app)/settings/page.tsx`.

- `qboCall(method, args)`: igual que `billingCall` (oficina/gerencia/admin,
  errores Odoo → 400/403), modelo `indigo.qbo`.
- Tarjeta **QuickBooks**: estado (conectado a *<empresa>* · sandbox/producción,
  último envío, último cobro, contadores pendiente/error/no coincide con enlace),
  botón **Connect** (enlace a `<ODOO_PUBLIC_URL>/indigo/qbo/connect`, solo
  gerencia), **Disconnect** con confirmación, interruptor **«Pasar la orden a
  Closed al cobrarse completa»** (apagado). Muestra `?qbo=connected|denied` como aviso.
- [ ] Probar con el sandbox en local (conectar, ver nombre, desconectar).
- [ ] Commit en indigo-next `feat(quickbooks): tarjeta en Settings`.

### Tarea 5: Equivalencias

**Archivos:** `models/qbo_service.py`, campos en `models/qbo_invoice.py`
(`res.partner.qbo_customer_id`, `product.product.qbo_item_id`),
`tests/test_qbo_mapping.py`; panel `src/app/api/quickbooks/mappings/route.ts`,
`src/app/(app)/billing/quickbooks/page.tsx`.

Produce:
- `qbo_mapping_list()` → `{dealers: [{id, name, qbo_id, qbo_name}], products: [{code, label, qbo_id, qbo_name}]}` (dealers con alguna factura o marcados dealer; productos `IND-*`).
- `qbo_remote_list(kind)` → clientes o productos de QBO (`Id`, `DisplayName`/`Name`), paginando con `STARTPOSITION`.
- `qbo_mapping_auto()` → empareja por nombre exacto (sin mayúsculas/espacios
  extra); devuelve qué emparejó y qué falta. No crea nada en QBO.
- `qbo_mapping_set(kind, local_id, qbo_id)`; `qbo_mapping_create_remote(kind, local_id)` crea el cliente/producto en QBO (producto: tipo Service, `Taxable` según el producto de Indigo, cuenta de ingresos elegida en la pantalla).

- [ ] Pruebas primero: auto-empareja «Lock Tight» ↔ «lock  tight»; no
  sobrescribe un emparejamiento manual; `create_remote` arma el cuerpo correcto.
- [ ] Pantalla **Billing → QuickBooks**: dos tablas (dealers, productos) con
  selector de su par en QBO, «Emparejar automáticamente» y «Crear en QuickBooks».
- [ ] Probar contra el sandbox (los productos y dealers de prueba ya existen).
- [ ] Commits `feat(quickbooks): equivalencias` (Odoo y panel).

### Tarea 6: Envío de facturas (Indigo → QBO)

**Archivos:** `models/qbo_invoice.py`, `models/qbo_hooks.py`, `data/ir_cron.xml`,
`tests/test_qbo_invoice.py`.

Campos en `account.move`: `qbo_id`, `qbo_sync_token`, `qbo_state`
(`none|pending|synced|linked|mismatch|error`), `qbo_error`, `qbo_synced_at`,
`qbo_total`, `qbo_attempts`, `qbo_next_try`, `qbo_origin` (`indigo|manual`).

- `move._qbo_payload()` → cuerpo de `Invoice`:
  `DocNumber`=`move.name`, `TxnDate`, `DueDate`, `CustomerRef` (equivalencia del
  dealer), `PrivateNote`=`Indigo #<n> · PO <po de sus órdenes>`, `EmailStatus`
  `NotSet`, `Line[]` con `SalesItemLineDetail` (`ItemRef` del producto,
  `Qty`, `UnitPrice`, `TaxCodeRef` `TAX`/`NON` según `tax_ids`) y
  `Description` = descripción de la línea. Falta una equivalencia →
  `QboError('api', 'Falta el cliente de QuickBooks de <dealer>')`.
- `move._qbo_push()`:
  1. sin `qbo_id`: `SELECT * FROM Invoice WHERE DocNumber = '<n>'`;
     existe → guardar `qbo_id`, `qbo_origin='manual'`, comparar `TotalAmt`:
     igual → `linked`, distinto → `mismatch`; no existe → crear → `synced`
     (o `mismatch` si `TotalAmt` ≠ `amount_total`).
  2. con `qbo_id` y `qbo_origin='indigo'` (corrección): leer `SyncToken` y
     actualizar (`Id`, `SyncToken`, `sparse: false`, cuerpo completo).
  3. con `qbo_origin='manual'` y la factura cambió → `mismatch` sin tocar QBO.
  4. anulada en Indigo con `qbo_id`: `POST invoice?operation=void` (`Id`, `SyncToken`);
     si `manual` → `mismatch` («anúlala también en QuickBooks»).
  5. error → `error` + `qbo_error`, `qbo_attempts += 1`,
     `qbo_next_try = now + min(5 min × 2^attempts, 6 h)`.
- Ganchos (`qbo_hooks.py`, herencia de `indigo.billing`): tras
  `indigo_billing_post`, `indigo_billing_reopen`→(nada hasta reemitir),
  `indigo_billing_void` → `qbo_state='pending'` y `self.env.cr.postcommit.add(...)`
  para intentar al momento. Solo si hay conexión.
- Cron cada 5 min: facturas `pending`/`error` con `qbo_next_try <= now`, de 20 en 20.
- `qbo_retry(move_id)` (oficina/gerencia): fuerza el intento.

- [ ] Pruebas primero (cliente simulado): crear; enlazar igual; enlazar distinto
  → `mismatch`; corrección actualiza con `SyncToken`; corrección de una manual
  → `mismatch` sin llamadas; anular; falta equivalencia → `error` con el
  motivo; backoff; sin conexión no hace nada.
- [ ] Implementar. Pruebas en verde.
- [ ] Probar contra el sandbox con una factura local emitida (número de prueba).
- [ ] Commit `feat(quickbooks): enviar facturas a QuickBooks`.

### Tarea 7: Estado de QBO en el panel y el asistente

**Archivos (indigo-next):** `src/components/billing/qbo-badge.tsx`, página de
factura, lista de facturas, `src/app/api/quickbooks/retry/[id]/route.ts`,
`src/lib/mcp/invoices.ts`; Odoo: `indigo_billing_detail`/`_row` exponen `qbo_*`.

- Insignia en la factura: *Sincronizada* / *Enlazada (hecha a mano en QBO)* /
  *Pendiente* / *No coincide* (con el total de QBO) / *Error* (motivo) +
  **Reintentar**. Lista de facturas: filtro «Sin QuickBooks / con error».
- `get_invoice` del asistente añade `quickbooks: {estado, motivo}`.
- [ ] Prueba unitaria del texto/color por estado. Commit.

### Tarea 8: Cobros (QBO → Indigo)

**Archivos:** `controllers/main.py` (webhook), `models/qbo_event.py`,
`models/qbo_payment.py`, cron en `data/ir_cron.xml`, `tests/test_qbo_payments.py`;
`account.payment.qbo_payment_id`.

- `POST /indigo/qbo/webhook` (`auth='none'`, `csrf=False`): verifica
  `intuit-signature` = base64(HMAC-SHA256(cuerpo crudo, `QBO_WEBHOOK_VERIFIER`))
  con `hmac.compare_digest`; inválida → 401. Válida → guarda cada
  `dataChangeEvent.entities[]` de tipo `Payment` en `indigo.qbo.event`
  (`entity_id`, `operation`, `last_updated`) y responde 200 al instante.
- Cron cada 15 min: (a) procesa eventos pendientes; (b) respaldo CDC:
  `GET cdc?entities=Payment&changedSince=<cursor>` (cursor en
  `indigo_qbo.cdc_cursor`, máximo 30 días atrás).
- Aplicar un `Payment` de QBO: por cada `Line` con `LinkedTxn` de tipo
  `Invoice` cuyo `qbo_id` conocemos → registrar en Odoo con
  `account.payment.register` (importe de esa línea, `TxnDate`, referencia
  `QBO <PaymentRefNum or Id>`), `qbo_payment_id` = `<Payment.Id>:<invoice qbo_id>`
  para no duplicar. `Update` → anular el pago de Odoo y recrearlo;
  `Delete`/`Void` → anularlo. Facturas desconocidas → solo log.
- Tras aplicar, `_indigo_sync_orders()`; si `auto_close` y pagada completa →
  orden a `closed`.
- Con conexión activa, `indigo_billing_register_payment` rechaza con
  «Los cobros se registran en QuickBooks» (salvo contexto `indigo_qbo_apply`),
  y el panel oculta **Record payment** (y el asistente lo dice en `record_payment`).

- **Ojo (auditoría):** el cursor del CDC y todo lo que deba confirmarse junto
  con los cobros se escribe en la transacción en curso, NO con
  `_set_params` (que confirma aparte).
- [ ] Pruebas primero: firma válida/ inválida; pago completo y parcial;
  pago repetido no duplica; pago editado y borrado; factura desconocida
  ignorada; auto-close encendido/apagado; `record_payment` bloqueado con conexión.
- [ ] Implementar. Pruebas en verde.
- [ ] Probar contra el sandbox: cobrar la factura de prueba en QBO y ver el
  cobro en Indigo (por CDC en local, el webhook necesita URL pública).
- [ ] Commit `feat(quickbooks): cobros desde QuickBooks`.

### Tarea 9: Enlace de lo ya emitido (backfill)

**Archivos:** `models/qbo_service.py`, `tests/test_qbo_backfill.py`, panel
(botón en Billing → QuickBooks).

- `qbo_backfill_report()` (solo lectura): facturas emitidas en Indigo sin
  `qbo_id` → por cada una, `existe igual` / `existe distinta` / `no existe`.
- `qbo_backfill_apply(move_ids)`: enlaza las que existen (igual → `linked`,
  distinta → `mismatch`) y crea las que no; nunca toca las que ya tienen `qbo_id`.
- [ ] Pruebas primero (cliente simulado). Pantalla: tabla del informe +
  «Aplicar» con confirmación. Commit.

### Tarea 10: Puesta en marcha

- [ ] **Antes:** decidir el impuesto (spec §8) y comprobar en la empresa real
  que *Custom transaction numbers* está encendido.
- [ ] En Intuit: registrar redirect URI `https://indigodecors.com/indigo/qbo/callback`
  y webhook `https://indigodecors.com/indigo/qbo/webhook` (entidad Payment),
  copiar el verifier token.
- [ ] Coolify (servicio Odoo): `QBO_CLIENT_ID`, `QBO_CLIENT_SECRET`,
  `QBO_REDIRECT_URI=https://indigodecors.com/indigo/qbo/callback`,
  `QBO_WEBHOOK_VERIFIER`, `QBO_ENVIRONMENT=sandbox`,
  `QBO_PANEL_URL=https://app.indigodecors.com`.
- [ ] Al pasar del sandbox a la empresa real, conectar la real borra solas las
  equivalencias y los enlaces del sandbox (los ids de QBO son por empresa).
- [ ] Desplegar (backup → Odoo → **`-i indigo_quickbooks`** una vez → panel).
- [ ] Piloto en sandbox desde producción: conectar, equivalencias, emitir una
  factura de prueba, cobrarla en QBO, ver el cobro en Indigo.
- [ ] Con OK: claves de producción, `QBO_ENVIRONMENT=production`, conectar la
  empresa real (lo hace quien administra QBO), equivalencias, informe del
  backfill revisado con Majela, aplicar.

## Autorrevisión

- Cubre el spec: conexión (T2–T4), equivalencias (T5), envío/corrección/anulación
  (T6), estado visible y reintento (T7), cobros con webhook + CDC y bloqueo de
  doble registro (T8), backfill (T9), sandbox → producción (T10).
- Pendiente fuera del plan, como dice el spec: impuesto, adjuntar PDF, correo de avisos.
