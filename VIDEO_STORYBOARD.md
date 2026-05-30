# Video — Flujo end-to-end Indigo Decors

Duración estimada **6–8 min**. Hilo narrativo: una orden real entra por la web del
cliente, llega a Odoo, recorre el pipeline de producción y se materializa en los
documentos físicos que hoy se hacen a mano.

**Pre-grabación**: limpiar la base de demo. Recomendación: crear UNA sola orden
limpia con 2 puertas para el mismo cliente final, para que los documentos salgan
prolijos. La grabación de hoy usó un carrito mixto de pruebas (4 puertas, 3
homeowners distintos) y eso "ensucia" el painter sheet / order card.

```bash
# Limpia data de demo previa antes de grabar
docker exec db-f57xxcgj6dph9nkrvekz91h6-184024461169 psql -U odoo -d indigo-prod -c "
  DELETE FROM indigo_order_line;
  DELETE FROM indigo_order;
  DELETE FROM sale_order_line WHERE order_id > 1;
  DELETE FROM sale_order WHERE id > 1;
"
```

---

## ESCENA 1 · Storefront — el dealer pide un presupuesto
**Duración**: 2 min · **URL**: http://2.25.137.220:8069/

### 1.1 Home + Shop (15s)
- Abrir home. Mostrar hero v2 con la copy "A door that *tells* your story".
- Click en `Shop` (top nav).

### 1.2 PDP con campos custom (60s)
- Click en un producto (ej. **ID01-DD**).
- Mostrar el bloque de variantes:
  - Finish color: Black / White / **Bronze** ← click
  - Privacy glass: No / **Yes** ← click
  - Door brand: dropdown con 12 marcas (ESW seleccionado por defecto)
- **For this door** (campos B2B exclusivos de Indigo):
  - Customer name: `Ana & David Bogenschutz`
  - Order ref: `LT-2026-145`
  - Install address: `4521 Bay Drive, Coral Gables FL 33133`
  - Install phone: `+1 (305) 555-0140`
- **Dimensions** (pulgadas + octavos US standard):
  - Width: `36 1/8`
  - Height: `83 3/4`
- Click `Add to quote list`.
- (Opcional) Repetir con un segundo producto para mostrar carrito multi-puerta.

> **Narración clave**: "Esto es lo que reemplaza el WhatsApp + foto del contrato.
> El dealer entra los datos del homeowner final por puerta, antes de mandar el
> pedido. Cuando llegue a producción, no hace falta retranscribir nada."

### 1.3 Carrito + checkout (30s)
- Click ícono carrito → ver lista con dimensiones y campos custom visibles.
- Click `Checkout`.
- Llenar form de dirección del **dealer** (Lock Tight LLC, Doral FL).
- Click `Continue checkout`.
- Página `/shop/payment`: explicar que aquí NO hay pago online (modelo quote
  request). El método único es "Wire Transfer".
- Click `Submit quote request`.

### 1.4 Confirmación (15s)
- Página `/shop/confirmation`: "Thank you — your quote request has been received".
- Anotar el order number (`S00004`).
- Nota: el cliente recibe email auto, sales recibe notificación interna.

---

## ESCENA 2 · Backend Odoo — recepción y pipeline
**Duración**: 3 min · **URL**: http://2.25.137.220:8069/web (login con
`lbencomo94@gmail.com` / `demo2026`)

### 2.1 Sale order en backend (30s)
- Navegar a **Ventas → Presupuestos** → abrir `S00004`.
- Mostrar:
  - Cliente: Lock Tight LLC
  - 4 líneas de puerta + delivery
  - Activity log con mensaje del cliente
  - PDF de Quotation adjunto
- Click `Confirmar`.

### 2.2 Bridge automático (30s)
- Al confirmar, el bridge crea automáticamente una **`indigo.order`**.
- Mostrar el activity log: "Vinculada a venta S00004" + "Orden de trabajo Indigo
  creado".
- Click el link al indigo.order (botón en el activity log).

### 2.3 Form de la indigo.order (45s)
- Mostrar las secciones:
  - **Dealer / Origin**: Lock Tight LLC + Dealer ref
  - **End Customer**: Ana & David Bogenschutz + phone + email + install address
  - **Internal Assignment / Payment**: $12/SQF (precio del dealer) · **Total a
    cobrar al dealer: $1,075.44** (calculado automático de SQF total)
  - **Contractors**: pintor + instaladores (asignar)
  - **Fechas y SLA**: días en etapa actual, atrasada (overdue automático)
- Click en tab **Pieces** → mostrar la tabla con cada puerta: design, type, color,
  glass, **Width 36.12 in × Height 83.75 in**, qty, SQF computado.

> **Narración clave**: "Notar que `36 1/8` que el dealer entró en la web aquí ya
> está como `36.125`. Bridge parsea el formato US estándar."

### 2.4 Recorrido por el Kanban — 13 etapas (60s)
- Volver a **Indigo → Órdenes** (vista Kanban).
- Mostrar las 13 columnas:
  ```
  New Order → Design Confirmation Pending → Design Confirmed →
  Measurement Pending → Measured → Ready for Digitalization →
  CNC / Router → Painting → Ready for Installation →
  Installation Scheduled → Installed → Invoiced / Paid → Closed
  ```
- Drag-drop la card desde New Order hasta Painting (4-5 movimientos).
- Cada movimiento dispara tracking en el chatter (`New Order → Design Confirmed
  (Etapa)`).
- Asignar a un usuario (Majela / Javier / Diseñador / Pintor / Instalador) en
  cada etapa según rol.

### 2.5 Incidentes y on-hold (15s)
- En el form, mostrar:
  - Checkbox `En espera / Pospuesta` + motivo
  - Tab `Incidents` (timeline de problemas con foto + autor + fecha)

---

## ESCENA 3 · Documentos generados automáticamente
**Duración**: 90s

> Hoy se hacen a mano. Aquí salen de un click desde la orden.

### 3.1 Etiqueta del diseñador (30s)
- En la orden, click menú **Print → Etiquetas del diseñador**.
- Se descarga PDF con N etiquetas (1 por pieza), formato Brother 57×13mm.
- Cada etiqueta contiene:
  ```
  Lock Tight LLC                IND/2026/00002
  Ana & David Bogenschutz
  36 1/8 x 83 3/4
  DD-BRONZE-ESW
  PRIVACY         Parts 1   ID01-DD     [QR]
  ```
- Se imprime en impresora térmica → pega detrás de la pieza cortada.

### 3.2 Hoja del pintor (30s)
- Click **Print → Hoja del pintor**.
- Tabla por puerta: Company / Order # / Client / Color / Door Type / SQF / $8 /
  Total. Footer con **TOTAL SQF · TOTAL USD** = monto a pagar al pintor.
- Hoy se calcula en papel; aquí sale generado.

### 3.3 Ficha de orden (30s)
- Click **Print → Ficha de orden**.
- 1 página A4 con TODO: dealer + customer + lista de piezas + medidas + estado
  + notas + total + signatura.
- Se imprime y se envía por correo (físico + email).

---

## ESCENA 4 · Cierre — liquidación y dashboard
**Duración**: 60s

### 4.1 Liquidación contratistas (30s)
- Navegar a **Indigo → Liquidaciones**.
- Mostrar:
  - Pintor: contra entrega — auto-genera línea al pasar a "Painting" done.
  - Instalador: semanal — wizard `Settle payouts` consolida la semana en un solo PDF.
- Click wizard → seleccionar pintor + período → genera **Payout report PDF** con
  todas las puertas pagadas a ese contratista esa semana.

### 4.2 Dashboard ejecutivo (30s)
- **Indigo → Dashboard**:
  - Pivot: órdenes por dealer × mes
  - Graph: SQF producido por etapa
  - Lista de overdue (días en etapa > X)
  - Ranking dealers / Ranking contratistas

---

## CIERRE — narración final (15s)
> "Antes: WhatsApp → papel → transcribir 4 veces → calcular en calculadora →
> Excel del pintor → email manual. Ahora: dealer pide en la web, todo lo demás
> se genera solo. La orden recorre 13 etapas trackeable y produce 3 documentos
> físicos de un click."

---

## Hallazgos durante la verificación (corregibles antes de grabar)

| # | Hallazgo | Severidad | Acción |
|---|---|---|---|
| 1 | Header de PDFs dice "Miami **DC** 33142" (state legacy) | Visual | UI: Settings → Companies → Indigo Publicity Corp → State = Florida; Street = `6752 NE 4th Avenue`, ZIP = `33148` |
| 2 | Label del diseñador usa `o.client_name` (header) en vez de `l.notes_line` customer per-line | Funcional menor | Cuando la orden tiene 1 cliente, irrelevante. Si una orden mezcla varios homeowners (raro), las labels mostrarán todas el mismo |
| 3 | Bridge no migra `is_privacy_glass` ni `glass_type` desde los atributos de variant del producto | Funcional | Aplicar en `_create_indigo_order_from_sale`: leer attribute values de la variant y mapear |
| 4 | Bridge no respeta el color elegido por el dealer (siempre `tmpl.indigo_default_color`) | Funcional | Cambiar `color: tmpl.indigo_default_color or color` por `color: color or tmpl.indigo_default_color` |
| 5 | El indigo.order creado no entra en stage="New Order" por default | UX menor | Agregar `default=lambda self: self._default_stage()` en `stage_id` del modelo |

Las 5 son fixes de 5-15 min cada uno. Si la grabación es urgente, los puntos 2,
3, 4 son aceptables y se aclaran en narración. **Los puntos 1 y 5 sí conviene
arreglarlos antes** (visual + UX).

---

## Capturas ya generadas (referencia)

| Archivo | Escena |
|---|---|
| `e2e-01-shop.png` | Shop con 142 productos |
| `e2e-02-pdp.png` | PDP con campos custom |
| `e2e-03-cart.png` | Cart con metadata por línea |
| `e2e-04-address.png` | Checkout — address form (sin VAT) |
| `e2e-05-payment.png` | Payment — quote-only banner |
| `e2e-06-confirmation.png` | Confirmation |
| `e2e-07-saleorder.png` | Backend sale.order |
| `e2e-08-kanban-stage1.png` | Kanban 13 etapas, card en New Order |
| `e2e-09-order-form.png` | Form indigo.order con todos los datos |
| `e2e-10-stage-design-confirmed.png` | Stage avanzada + activity log con transición |
| `e2e-11-report-label.png` | PDF etiqueta diseñador (4 labels) |
| `e2e-12-painter-sheet.png` | PDF painter sheet ($716.96 total) |
| `e2e-13-order-card.png` | PDF order sheet completa |
