# Integración con QuickBooks Online — diseño

**Fecha:** 2026-10-06 · **Estado:** borrador para revisar · **Módulo:** `indigo_quickbooks` (nuevo, depende de `indigo_decors`)

## 1. Por qué

Hoy la factura nace en Indigo (app y asistente) y alguien la vuelve a escribir en
QuickBooks Online (QBO) a mano, con el número de Indigo y el PO en el memo. Los
cobros se registran solo en QBO, así que en Indigo la factura sigue «Open» y los
reportes de abiertas/vencidas no cuadran. La integración elimina la doble
captura y trae los cobros de vuelta.

## 2. Decisiones tomadas

| Tema | Decisión |
|---|---|
| Producto | QuickBooks **Online** (API REST v3, OAuth 2.0). |
| Origen de las facturas | **Indigo.** QBO recibe una copia con el **mismo número** (`DocNumber`). |
| Facturas metidas a mano en QBO | Pasa a veces. Antes de crear, se busca por `DocNumber`; si existe se **enlaza** (no se duplica ni se sobrescribe). |
| Origen de los cobros | **QBO** (fuente oficial). Indigo los **recibe**; su botón *Record payment* se desactiva mientras QBO está conectado. |
| Impuesto | **Pendiente.** Se manda cada línea como gravable/no gravable; si el total de QBO difiere del de Indigo se marca para revisión. |
| Pasar a *Closed* al cobrar | Ajuste en Settings, **apagado** por defecto. |

## 3. Flujo

1. **Emitir** en Indigo → la factura queda «pendiente de QBO» → se crea en QBO
   (cliente, líneas, `DocNumber` = número de Indigo, memo
   `Indigo #<n> · PO <po>`, `EmailStatus = NotSet`: el correo lo manda Indigo).
2. **Corregir** (reabrir y reemitir) → se actualiza la factura de QBO.
3. **Anular** en Indigo → se anula en QBO (`operation=void`).
4. **Cobro registrado en QBO** → aviso de QBO (webhook) → Indigo registra el
   pago en su factura → la orden pasa a *paid* / *partial* (y a *Closed* si el
   ajuste está encendido).

## 4. Piezas

### 4.1 Conexión (OAuth 2.0)
- `GET /indigo/qbo/connect` (solo gerente) → redirige a Intuit con `state` firmado.
- `GET /indigo/qbo/callback` → canjea el código, guarda `realm_id`,
  `access_token` (1 h), `refresh_token` (100 días, se renueva al usarlo) y vencimientos.
- Desconectar = revocar el token y borrar lo guardado.
- **Secretos:** `client_id` / `client_secret` / *verifier token* del webhook como
  variables de entorno del contenedor (Coolify). Tokens en `ir.config_parameter`
  (solo en la base). **Nada en el repo.**
- Entorno `sandbox` | `production` como ajuste; se prueba siempre en sandbox primero.

### 4.2 Equivalencias
| Indigo | QBO | Cómo se llena |
|---|---|---|
| Dealer (`res.partner`) | `Customer` | 1.ª vez por `DisplayName`; si no hay, pantalla para elegir o crear. Se guarda `qbo_customer_id`. |
| Producto de factura (`IND-SD`, `IND-DD`, `IND-SL`, `IND-FEE-A..D`, `IND-OTHER`) | `Item` | 1.ª vez por nombre; pantalla para corregir. Se guarda `qbo_item_id`. |
| Gravable / no gravable | `TaxCodeRef` `TAX` / `NON` | Fijo hasta decidir el impuesto (§2). |

Sin equivalencia completa, la factura queda en **error** con el motivo
(«falta el cliente de QBO de <dealer>»), no se inventa.

### 4.3 Campos nuevos
- `account.move`: `qbo_id`, `qbo_sync_token`, `qbo_state`
  (`none | pending | synced | linked | mismatch | error`), `qbo_error`,
  `qbo_synced_at`, `qbo_total` (el total que devolvió QBO).
- `res.partner`: `qbo_customer_id`. `product.product`: `qbo_item_id`.
- `account.payment`: `qbo_payment_id` (idempotencia de cobros).

### 4.4 Envío de facturas (Indigo → QBO)
- Al emitir/corregir/anular: `qbo_state = pending` y se intenta al momento
  (después del commit); si falla, la tarea periódica reintenta (cada 5 min, con
  espera creciente).
- **Antes de crear:** `SELECT * FROM Invoice WHERE DocNumber = '<n>'`.
  - existe y el total coincide → `linked` (se guarda `qbo_id`, no se toca);
  - existe y no coincide → `mismatch` (se muestra para revisar, no se sobrescribe);
  - no existe → se crea → `synced`. Si `TotalAmt` de QBO ≠ total de Indigo → `mismatch`.
- Corregir una factura `linked` (metida a mano) → `mismatch`: no se pisa trabajo manual.

### 4.5 Cobros (QBO → Indigo)
- **Webhook** `POST /indigo/qbo/webhook`: verifica la firma `intuit-signature`
  (HMAC-SHA256 con el verifier token) y responde rápido; el trabajo se encola.
- **Respaldo:** tarea cada 15 min con *Change Data Capture* (`/cdc?entities=Payment,Invoice`)
  desde el último cursor, por si un aviso se pierde.
- Por cada `Payment` con líneas enlazadas a facturas con `qbo_id` conocido:
  registrar el pago en Indigo (`account.payment.register`), fecha y referencia de
  QBO, `qbo_payment_id` para no duplicar. Edición/borrado en QBO → se deshace y
  rehace el pago en Indigo.
- Cobros de facturas que Indigo no conoce (QBO puro, órdenes antiguas): se ignoran y se registran en el log.

### 4.6 Pantallas (panel Next)
- **Settings → QuickBooks:** estado (conectado a <empresa>, entorno, último
  envío, último cobro recibido), *Connect / Disconnect*, ajuste «cerrar la orden
  al cobrar», contador de facturas en error con enlace.
- **Equivalencias:** dealers y productos con su par en QBO; elegir/crear.
- **Factura:** insignia *QuickBooks: sincronizada / enlazada / pendiente / no
  coincide / error* + **Reintentar** y el motivo del error.
- **Billing → Invoices:** filtro «no está en QuickBooks / con error».
- *Record payment* oculto con el aviso «Los cobros llegan de QuickBooks» cuando hay conexión.
- Asistente (MCP): `get_invoice` informa el estado de QBO; sin herramientas nuevas al principio.

## 5. Errores y avisos
- Token vencido o revocado → estado «Hay que reconectar QuickBooks» en Settings y
  en la cabecera de Billing; nada se pierde: todo queda `pending`.
- Error de QBO por factura → `qbo_error` con el texto de Intuit traducido a algo
  accionable; reintento manual y automático.
- Límite de la API (500 llamadas/min por empresa): holgado para el volumen; se
  respetan los `429` con espera.

## 6. Puesta en marcha
1. App en Intuit Developer (sandbox + producción), URI de retorno y URL del webhook registradas.
2. Fase sandbox: conexión, equivalencias, envío, cobros, corrección y anulación de punta a punta.
3. **Enlace de lo ya emitido** (de la #1364 en adelante): primero un informe en
   seco (existe / no existe / no coincide), y con OK se enlaza o crea.
4. Producción: conecta quien administre QBO desde Settings.

## 7. Pruebas
- Odoo: cliente HTTP de QBO simulado; casos de crear, enlazar, no coincide,
  corregir, anular, webhook con firma buena/mala, cobro parcial/total, cobro
  editado/borrado, idempotencia, token vencido.
- Panel: estados e insignias; *Record payment* oculto con conexión.
- Sandbox de Intuit con facturas reales copiadas antes de producción.

## 8. Pendiente de decidir
- **Impuesto:** cálculo automático de QBO o 7 % fijo; quién manda si difieren.
- ¿Adjuntar el PDF de Indigo a la factura de QBO? (opcional, `Attachable`).
- ¿Avisar por correo cuando hay facturas en error o hay que reconectar?
