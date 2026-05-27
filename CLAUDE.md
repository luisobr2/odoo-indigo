# CLAUDE.md — Proyecto Indigo Decors

Contexto del proyecto para asistir en el desarrollo y mantenimiento del sistema
de gestión de órdenes de Indigo Publicity Corp.

**Estado actual (2026-05-27): EN PRODUCCIÓN.** Sistema desplegado en VPS Hostinger
con Coolify. Ver sección 7 (Producción) para credenciales y URLs.

---

## 1. Objetivo y empresa

**Razón social oficial:** Indigo Publicity Corp.
**Marca comercial:** Indigo Decors (https://www.indigodecors.com)
**Dirección:** 2192 NW 26th Ave, Miami, FL 33142
**Teléfono:** +1 786-302-2732
**Email:** sales@indigodecors.com

Taller que decora/fabrica puertas decorativas (corte CNC, pintura, instalación) para
**dealers grandes** (Lock Tight, Web Indigo, USA Windows, etc.). El cliente final
pertenece al dealer, no al taller. La marca usa una paleta **azul** (azul Indigo
~#1f4486 sobre navy oscuro).

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

## 6. Respuestas del cliente (2026-05-26) + pendientes

### Respondido
2. **Volumen**: ~20–40 puertas por período (semana/mes — aclarar).
3. **Multi-pieza**: una orden = un cliente, pero puede traer **varias puertas**.
   → Modelo: `indigo.order` con líneas `indigo.order.line` (una por puerta/pieza).
4. **Errores y retrocesos**: sí ocurren (medidas mal, pintura mal, cliente cancela
   a último minuto). Hoy hacen comentarios en la orden de Odoo. **Requerimiento**:
   sistema de **anotaciones/incidencias** por orden (timeline + autor + foto).
5. **Estados especiales**: sí — instalaciones se posponen por factores externos.
   → Agregar estado **"On Hold / Postponed"** (paralelo a las 13 etapas).
6. **Asignación**: el ciclo completo lo trabajan ~2 personas, pero en cada área
   intervienen distintos roles. Multi-asignado por etapa.
7. **Notificaciones**: por **correo** (confirmado).
8. **Etiqueta**: **12.7 × 57.15 mm** (formato tipo Brother P-touch / Dymo).
   → Confirmar modelo exacto de impresora para definir driver (ZPL vs EPL vs PDF).
11. **Tarifa pintor**: confirmado **$8 USD × SQF**.
12. **Tarifa pintor**: **misma siempre** (no varía por color/tipo/dealer).
13. **Instaladores**: pago **por pieza instalada — $35 USD/puerta**.
14. **Liquidación**:
    - Pintor: **contra entrega** del trabajo terminado (no acumula).
    - Instaladores: **semanal** (acumula y se reporta).
17. **Datos a conservar de Odoo actual**: ~~clientes, órdenes históricas, facturación~~
    → **Actualización 2026-05-26**: el cliente confirmó que **NO hace falta migrar**,
    arrancan desde cero. Lo que sí necesitan: **reportes con direcciones de instalación**
    y los documentos manuales (etiqueta, hoja pintor) generados desde el sistema.
    Nota del cliente: "tenemos el proceso pero no sabemos usarlo" → entrenamiento
    incluido en el alcance.

### Decisiones técnicas (2026-05-26)
- **Frontend (storefront)**: diferido — se decide tras el MVP backend.
- **Entorno dev**: Docker local en Windows (Odoo 17 + Postgres 15).
- **Migración**: no aplica, base nueva.
- Ver `PLAN.md` para el desglose por fases.

### Multiidioma (2026-05-26)
**Español + Inglés** (es_ES como fuente, en_US vía `i18n/en.po`).

- Campos data marcados como `translate=True`: `indigo.stage.name`,
  `indigo.design.name`, `indigo.design.description`, `indigo.stage.description`.
- Archivo `addons/indigo_decors/i18n/indigo_decors.pot` (template, ~339 strings).
- Archivo `addons/indigo_decors/i18n/en.po` (~170 strings traducidos cubren
  los labels más visibles: menús, campos, botones, etapas, estados, reportes).
- Script `scripts/generate_en_po.py` regenera `en.po` a partir del `.pot`
  con un diccionario Python. Para agregar más traducciones: editar el dict
  `TRANSLATIONS` y correr `python scripts/generate_en_po.py`.
- Activar idioma: Settings → Translations → Load language (o usar
  `scripts/install_english_v2.py`).
- Recargar `en.po` tras cambios: `docker compose exec odoo odoo -c /etc/odoo/odoo.conf -d indigo-db -u indigo_decors --i18n-overwrite --stop-after-init`
- Browser cache: hacer hard reload (F5) tras recargar `.po`.

**Caveat**: ~50% de los strings tienen traducción explícita. El resto cae
back a la versión española (source language). Se puede ampliar editando
el dict en `scripts/generate_en_po.py` y regenerando.

### Workflow de desarrollo / verificación (2026-05-26)
- **Verificación automatizada del UI** con MCP **`playwright`** — la asistencia
  navega el Odoo local, ejecuta el flujo y captura screenshots en lugar de
  pedirle al usuario que pruebe manualmente.
- **Inspección de DB** con MCP **`postgres-db-sleep`** (conexión: host `localhost`,
  port `5432` desde host / `db:5432` dentro de la red docker, user `odoo`,
  password `odoo`, DB `indigo-db`) — para validar seeds, debug, queries ad-hoc.
- **MailHog** corre como tercer contenedor (`indigo-mailhog`) y captura todo el
  correo saliente de Odoo: SMTP en `mailhog:1025` (red docker), UI web en
  http://localhost:8025. Configurado en `config/odoo.conf` con
  `smtp_server=mailhog, smtp_port=1025`. **Nunca enviar correo real desde dev.**

### Skills / herramientas instaladas (2026-05-26)
- **Skill `odoo-development`** (instalada en `~/.claude/skills/odoo-development/`,
  fuente: https://github.com/fhidalgodev/odoo-development-skill).
  Cubre Odoo 14–19 con estándares OCA. Incluye 123 patterns (modelos, vistas
  XML, QWeb, OWL, seguridad, ACL, sequences, mail, portal, cron, reportes,
  multi-company, etc.) y 4 agentes (`odoo-context-gatherer`,
  `odoo-code-reviewer`, `odoo-upgrade-analyzer`, `odoo-skill-finder`).
  **Invocar con `/odoo-development` cuando se necesite verificar patrón Odoo 17
  oficial antes de escribir código.**

### Solicitud adicional (fuera del alcance original)
- El cliente quiere **rediseñar visualmente diseños existentes** con su identidad
  y agregar nuevos al catálogo. **Pedir cotización aparte** (trabajo de diseño
  gráfico, no de software).

### Asunciones profesionales tomadas (2026-05-26) ante falta de respuesta del cliente

Para no bloquear el desarrollo, se decidió implementar con valores razonables
documentados aquí. **Reemplazar/confirmar con el cliente antes de Fase 5 (go-live).**

| Pregunta pendiente | Asunción aplicada | Dónde se cambia |
|---|---|---|
| 1. Lista completa de dealers | Cargados Lock Tight, Web Indigo, USA Windows en `data/demo_dealers.xml`. Admin agrega más desde Indigo → Dealers. | `data/demo_dealers.xml` |
| 8b. Modelo de impresora térmica | PDF genérico con paperformat 57×13mm (no respetado del todo por wkhtmltopdf, pero suficiente como proof). En producción se requiere driver real (ZPL/Brother) — ajustar en `reports/order_label_report.xml` cuando se confirme. | `reports/order_label_report.xml` |
| 9. Datos exactos etiqueta + QR | **QR sí**, con el order.name (trazabilidad estándar). Layout: dealer, orden, cliente, tipo-color-vidrio, medidas, PRIV (si seteado), Parts, código diseño, QR. | `reports/order_label_report.xml` |
| "PRIV" en etiqueta | Campo libre `priv_ref` en orden (referencia interna). Aparece junto a medidas si se llena. | `models/indigo_order.py`, `reports/order_label_report.xml` |
| 10. Otros documentos manuales | No se asumieron más. Si surgen, agregar como reportes QWeb adicionales. | `reports/` |
| 15. Lista oficial de códigos | Cargados 33 códigos detectados del catálogo PDF (ID01..ID34 en SD/DD + 4 TD-). Admin puede agregar más desde Indigo → Catálogo. | `data/demo_designs.xml` |
| 16. Precio al dealer | **Por SQF, configurable por dealer** (`indigo_default_price_per_sqf` en partner). Default: Lock Tight $12, USA Windows $11.50, Web Indigo $11. Override por orden disponible (`price_per_sqf`). Se auto-rellena desde el dealer en la orden vía `@api.model_create_multi` (cubre tanto UI como portal POST). | `data/demo_dealers.xml`, `models/indigo_order.py` |
| 18. Automatización WhatsApp | **No implementado**. Si surge requerimiento, integrar con `whatsapp_messaging` (Odoo Enterprise) o Twilio. | — |

### Pendiente real (no asumible)
- Modelo/marca exacto de la impresora térmica para definir driver final.
- Validación con cliente de los 33 códigos cargados (¿faltan, sobran, varían?).
- Validación de los precios por SQF asumidos.
- Dispositivos (PC/móvil), dominio/hosting → Fase 5.

> Cuando el cliente responda, actualizar este archivo y finalizar
> `PROPUESTA_Sistema_Gestion_Indigo.md`.

---

## 7. Producción (desplegado 2026-05-27)

### Infraestructura
- **VPS Hostinger** (Boston, Ubuntu 24.04, root@2.25.137.220).
- **Coolify** corriendo en el VPS — panel: http://2.25.137.220:8000
- **Odoo 17** desplegado via Docker Compose dentro de Coolify.
- **DB Postgres 15** + **Odoo 17 custom image** (Dockerfile con `indigo_decors` + `indigo_theme` horneados).
- Credenciales SSH, API tokens, master passwords: en `.env` local (gitignored)
  y en la memoria persistente del proyecto (`~/.claude/projects/.../memory/`).

### URLs
- **Sitio público**: http://2.25.137.220:8069
- **Backend Odoo**: http://2.25.137.220:8069/web (login con email/pass)
- **Coolify panel**: http://2.25.137.220:8000
- Dominio + SSL pendiente — DNS aún no apunta. Cuando se apunte
  `app.indigodecors.com → 2.25.137.220`, Coolify habilita SSL automático con
  Let's Encrypt via Traefik.

### Módulos instalados en producción
- `website`, `website_sale`, `sale_management`, `account`, `portal`, `mail`
- **`indigo_decors`** v17.0.0.12.0 — lógica de órdenes, 13 etapas configurables,
  liquidaciones SQF, reportes QWeb (etiqueta, hoja pintor, ficha orden).
- **`indigo_theme`** — frontend IKEA-inspired con paleta azul Indigo.

### Data en producción (sembrado inicial)
- **DB**: `indigo-prod` (creada via UI, sin demo data).
- **Dealers**: 4 (Lock Tight, USA Windows, Web Indigo, Ventas Directas B2C).
- **Diseños**: 33 códigos del catálogo (ID01..ID34 en SD/DD + TD-).
- **Etapas**: 13 etapas configurables (New Order → Closed).
- **Productos eCommerce**: 142 templates importados desde scraping de
  indigodecors.com via `scripts/import_scraped.py` (con 568 imágenes).
- **Precios**: $0.00 — pendiente seed (scraper no extrajo precios).
- **Contractor rates**: 2 (pintor $8/SQF, instalador $35/puerta).

### Lecciones críticas del deploy
1. **Coolify clona el repo solo para build context**, no preserva `addons/` ni
   `config/` en el host. Solución: COPY ambos en el Dockerfile. Bind mounts
   en `docker-compose.yml` rompen producción — se preservan solo via
   `docker-compose.override.yml` (ignorado por Coolify) para dev local.
2. **Menus que referencian `parent="menu_indigo_root"` deben cargarse después**
   del archivo que define el root. Solución: `views/indigo_menu_root.xml`
   como PRIMER archivo de views en el manifest.
3. **`odoo.conf` baked en imagen con admin_passwd plaintext** para creación
   inicial de DB. **HARDENING pendiente**: rehashear admin_passwd, cambiar
   db_password (actualmente `odoo`), `list_db = False`.
4. **Tras CLI install (`odoo -i`)**: el container running tiene registry viejo
   sin los modelos Python nuevos. **Hay que `docker restart` el container**
   para que recargue los modelos.
5. **Theme.utils `_post_copy` no se invoca automáticamente** al instalar el
   theme via CLI. Ejecutar manualmente:
   `env['theme.utils']._theme_indigo_theme_post_copy(theme)` via odoo shell.
6. **Menus del website** (Gallery, About, For Dealers) no se crean
   automáticamente. Necesitan `website.menu` records via script post-install.

### Hardening pendiente antes de go-live real
- [ ] Rehashear `admin_passwd` desde UI (Settings → General → Set Master Password)
- [ ] Cambiar `db_password` a uno fuerte y propagar a Coolify env vars +
      regenerar el container con volumen db-data limpio
- [ ] Cambiar password del admin user (lbencomo94@gmail.com)
- [ ] `list_db = False` en `config/odoo.conf`
- [ ] DNS + SSL (dominio apuntando al VPS + Let's Encrypt via Coolify Traefik)
- [ ] Backups automáticos del volumen `db-data` (configurable en Coolify
      Resource → Backups, requiere S3 o similar)
- [ ] Reemplazar SMTP mailhog por proveedor real (SendGrid/Mailgun/SES)
- [ ] Workers > 0 en `odoo.conf` para concurrencia (actualmente `workers=0`,
      single-threaded — ok para baja carga, ajustar según specs VPS)
- [ ] Cargar precios reales en los 142 productos (manual o script)

### Workflow de deploy
1. Editar código local en `D:\01_Trabajo\Indigo\addons\`.
2. Commit + push a `github.com/luisobr2/odoo-indigo`.
3. Coolify API: `POST /api/v1/deploy?uuid=f57xxcgj6dph9nkrvekz91h6&force=true`
   (con `Authorization: Bearer <token>` — token en `.env`).
4. Wait deploy: ~2-3 min (build + restart).
5. Si cambiaste modelos Python: `docker restart odoo-f57...` para recargar
   el registry.
6. Si cambiaste `__manifest__.py` o XML de views/data:
   `docker exec ... odoo -c /etc/odoo/odoo.conf -d indigo-prod -u indigo_decors --stop-after-init`.

### MCPs útiles en este proyecto
- **`playwright`**: navegar Odoo backend/frontend y capturar screenshots
  durante audits y verificación visual.
- **`postgres-db-sleep`**: queries directas a `indigo-prod` para debug
  (conexión definida en config local del MCP).
- **`ssh`**: conectar al VPS root@2.25.137.220 para ejecutar `docker logs`,
  `docker exec odoo shell`, etc.
- **Skills instaladas**: `odoo-development`, `theme-create`, `theme-snippets`,
  `coolify-deploy`.
