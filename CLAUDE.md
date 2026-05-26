# CLAUDE.md — Proyecto Indigo Decors

Contexto del proyecto para asistir en el desarrollo de la propuesta y, posteriormente,
del sistema de gestión de órdenes.

---

## 1. Objetivo

**Indigo Decors** (sitio oficial: https://www.indigodecors.com) es un taller que
decora/fabrica puertas decorativas (corte CNC, pintura, instalación) para
**dealers grandes** (Lock Tight, Web Indigo, USA Windows, etc.). El cliente final
pertenece al dealer, no al taller. La marca usa una paleta **azul** (azul Indigo
~#1f4486 sobre navy oscuro); el demo SPA ya está alineado a esos colores.

Hoy todo el proceso detrás de cada pedido es **manual y engorroso**: las órdenes entran por
varios canales, la información se transcribe varias veces y los documentos de cada área se
hacen a mano.

**Objetivo del proyecto:** entregarles una **propuesta** para automatizar y agilizar la
gestión de órdenes.

**Decisión final (2026-05-22):** stack **Odoo 17 Community + módulo a medida `indigo_decors`**.

> Inicialmente exploramos WordPress + WooCommerce + SPA React. Tras analizar las capturas
> reales de la instancia Odoo del cliente (kanban, tareas, asignados, log de actividad,
> portal con adjuntos ya funcionando) concluimos que **construir todo eso desde cero
> equivale a reimplementar medio Odoo**. Con Community + un módulo a medida acotado:
> licencia $0 y pantallas adaptadas al taller. Ver `PROPUESTA_Odoo.md`.

**Entregable actual:** `PROPUESTA_Odoo.md` (v1.0) + demo SPA navegable como referencia
visual de UX (`demo-spa/` — no es el entregable final, es solo para alinear pantallas
con el cliente). Antes de firmar se espera la respuesta del cliente al cuestionario
(ver sección 6).

---

## 2. El negocio

### Flujo de trabajo
```
Orden Web → Confirmación de diseño → Medición → Digitalización
   → CNC/Router → Pintura → Instalación → Facturación / Pago a contratistas
```

### Cómo llegan las órdenes
- Cada dealer tiene cuenta de cliente en la tienda (actualmente Odoo) y hace pedidos logueado.
- También llegan por **WhatsApp** y en **papel** → requieren entrada manual al sistema.
- Ningún dealer puede integrarse por API; toda la entrada es manual.

---

## 3. Requerimientos funcionales

### 3.1 Captura de la orden — campos
- Nombre del cliente
- Teléfono
- Dirección
- Email
- Código del diseño (ej. `TD-SD-W06`, `ID70-DD-B`)
- Tipo de puerta: Single Door (SD) / Double Door (DD) / Door with Sidelites
- Color / Finish: White, Bronze, Black (+ custom bajo pedido)
- Fotos del contrato o puerta
- Estado del pago
- Compañía origen (dealer): Lock Tight, Web Indigo, USA Windows, otra
- Código de referencia del cliente (número/nombre que asigna el dealer al cliente final)
- Medidas y área (SQF) de cada pieza

### 3.2 Tablero de producción (Kanban) — 13 etapas
```
1. New Order
2. Design Confirmation Pending   ┐
3. Design Confirmed              │ OPCIONALES — configurables sin código,
4. Measurement Pending           │ aplican a varios dealers (flexible).
5. Measured                      ┘ Si no aplican: la orden pasa de New Order a CNC.
6. Ready for Digitalization
7. CNC / Router
8. Painting
9. Ready for Installation
10. Installation Scheduled
11. Installed
12. Invoiced / Paid
13. Closed
```
- Lista completa y en orden correcto (confirmado por el cliente).
- Las etapas 2–5 deben poder activarse/desactivarse **por dealer (o por orden) sin tocar
  código** — configuración flexible desde el panel.

### 3.3 Roles
| Rol | Persona | Responsabilidad |
|---|---|---|
| Confirmación / seguimiento | Majela | Contacto y confirmación con el cliente |
| Medición e instalación | Javier | Medir e instalar |
| Digitalización | Diseñador | Pasar el diseño a archivo CNC |
| Corte | CNC / Router | Cortar piezas |
| Pintura | Pintor | Pintar piezas |
| Administración | Administración | Facturas y pagos |
- Debe existir un **rol con acceso total** (dueño/gerente).
- Las órdenes se asignan a responsables.

### 3.4 Documentos (hoy se hacen a mano — deben generarse desde la orden, sin retranscribir)
1. **Ficha de orden** — se imprime y se envía por correo (ambas).
2. **Etiqueta del diseñador** — se imprime en impresora de etiquetas y se pega detrás de las
   piezas cortadas. Contiene: Cliente / Dealer, medidas, Tipo de puerta–Color–tipo de vidrio
   (ej. ESW), N° de orden, PRIV, cantidad de piezas (Parts), código de diseño.
3. **Hoja del pintor** — tabla con columnas: Company, Order Number, Client Name, Color,
   Door Type, SQF, price, total. `total = SQF × price`; en los ejemplos `price = $8`
   constante. El `total` es el **monto a pagar al pintor**.

### 3.5 Pagos a contratistas
- A partir del área (SQF) se calcula el pago al pintor (y otros contratistas con tarifa por SQF).
- Acumular por período y producir reporte de liquidación.

---

## 4. Solución técnica propuesta — Odoo Community + módulo a medida

- **Odoo 17 Community** (open source, sin licencia): clientes, productos, pedidos,
  inventario, contabilidad básica, **Project + Tasks** (kanban, asignados, log de
  actividad, adjuntos), **Website + eCommerce** (tienda dealer), portal externo para
  usuarios "portal" sin licencia (instaladores).
- **Módulo a medida `indigo_decors`** (Python + XML + QWeb):
  - Modelos: `indigo.order`, `indigo.dealer` (extiende `res.partner`), `indigo.stage`,
    `indigo.dealer.pipeline`, `indigo.design`, `indigo.contractor.rate`, `indigo.payout`.
  - Lógica: 13 etapas configurables por dealer, asignación, cálculo de liquidación SQF.
  - Reportes QWeb: Ficha de Orden, Etiqueta del Diseñador (impresora térmica), Hoja
    del Pintor, Liquidación de contratistas.
  - Pantallas custom (kanban filtrado, configurador de pipeline, mini-CRM dealers).
- **Portal de instaladores**: vista móvil con usuarios "portal" de Odoo (sin licencia
  interna), tareas asignadas, subida de fotos desde el celular.
- **Hosting**: VPS dedicado (DigitalOcean / Hetzner) ~$25-40/mes, no Odoo.sh.

### Por qué Odoo y NO WooCommerce + SPA (decisión revisada)
- Las capturas del cliente prueban que el flujo de Project + Tasks + Kanban + portal
  + adjuntos **ya funcionaba en Odoo**. Reescribir todo eso en una SPA equivale a
  reimplementar medio ERP — meses de trabajo + mantenimiento permanente.
- Lo que les molestaba era la **UX genérica** y el **costo Enterprise**, no la
  funcionalidad. Con Community + módulo a medida resolvemos ambos.
- El módulo a medida queda **acotado** a lo verdaderamente específico del negocio
  (etiqueta del diseñador, hoja del pintor, liquidación SQF, 13 etapas configurables,
  agrupación por dealer), no a reinventar gestión de proyectos.

---

## 5. Archivos en la carpeta del proyecto (`D:\01_Trabajo\Indigo`)

- `conversacion.txt` — chat de WhatsApp con el cliente describiendo el flujo y requerimientos.
- `orden por whatsapp.jpeg` — ejemplo de orden recibida por WhatsApp.
- `esta es la otra manera en la que nos hacen llegar la orden.jpeg` — orden en papel
  (hoja "Quote Items" de Lock Tight con anotaciones a mano).
- `esto se lo hago para el diseñador ... label ...jpeg` — ejemplo de la etiqueta del diseñador.
- `esto es para el pintor ... area de la pieza ...jpeg` — ejemplo de la hoja del pintor.
- `IMPACT DOOR DECORATION_CATALOG LOCKTIGHT 2026_compressed.pdf` — catálogo de diseños 2026.
- `PROPUESTA_Odoo.md` — **propuesta v1.0 vigente** (stack Odoo Community + módulo a medida).
- `demo-spa/` — prototipo navegable en React de las pantallas custom. **No es el
  entregable final**: sirve como referencia visual de UX para alinear con el cliente
  antes de implementar las pantallas Odoo. Se ejecuta con `npm run dev` desde la carpeta.

### Códigos de diseño detectados en el catálogo (parcial)
ID01, ID06, ID07, ID09, ID10, ID12, ID13, ID15, ID17, ID18, ID20, ID21, ID22, ID23, ID24,
ID26, ID27, ID29, ID31, ID32, ID33, ID34 — en variantes SD/DD.
Además códigos tipo `TD-SD-W##` / `TD-DED-B##` que aparecen en órdenes reales.

---

## 6. Estado / preguntas pendientes al cliente

Antes de finalizar la propuesta se envió al cliente un cuestionario. **Pendiente de respuesta:**

1. Lista completa de dealers.
2. Volumen de órdenes por semana/mes.
3. ¿Una orden trae varias piezas o solo una?
4. ¿Una orden puede regresar a etapas anteriores?
5. ¿Necesitan estados "En espera / Cancelada / Pausada"?
6. ¿Una etapa la trabaja una persona o varias?
7. ¿Notificaciones? ¿Dónde (sistema / correo)?
8. Medida de la etiqueta y modelo de impresora.
9. ¿Agregar código de barras / QR a la etiqueta?
10. ¿Otros documentos manuales no listados?
11. Confirmar tarifa del pintor (¿SQF × $8?).
12. ¿La tarifa varía por color / tipo / dealer?
13. ¿Otros contratistas pagados por SQF o pieza? Tarifas.
14. Frecuencia de liquidación y reporte.
15. Lista oficial completa de códigos de diseño.
16. Precio al dealer: ¿por SQF? ¿igual para todos o por dealer?
17. Acceso admin a Odoo y datos a conservar.
18. Dispositivos (PC/móvil), dominio/hosting, interés en automatizar WhatsApp.

> Cuando el cliente responda, actualizar este archivo y finalizar
> `PROPUESTA_Sistema_Gestion_Indigo.md`.
