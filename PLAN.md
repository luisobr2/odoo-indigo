# PLAN — Indigo Decors / Odoo 17 + módulo `indigo_decors`

> Plan de implementación. Stack acordado: **Odoo 17 Community + módulo a medida**.
> Frontend (Odoo Website vs Next.js) **se decide después del MVP**.
> Entorno dev: **Docker local** en Windows.
> **Sin migración** — el cliente arranca desde cero.

---

## Decisiones tomadas (2026-05-26)

| Tema | Decisión |
|---|---|
| Stack backend | Odoo 17 Community + módulo `indigo_decors` |
| Frontend storefront | **Diferido** — se decide tras MVP backend |
| Entorno dev | Docker local (Odoo 17 + Postgres 15) |
| Migración de datos | **No aplica** — base nueva |
| Hosting prod | VPS dedicado (DigitalOcean / Hetzner, ~$25-40/mes) |
| Tarifa pintor | $8 USD × SQF (fija, no varía) |
| Tarifa instalador | $35 USD × puerta instalada |
| Liquidación pintor | Contra entrega (por orden) |
| Liquidación instaladores | Semanal (acumulada) |
| Notificaciones | Por correo |
| Etiqueta diseñador | 12.7 × 57.15 mm |

---

## Fases

### Fase 0 — Setup del entorno dev (3-5 días)

**Entregable:** entorno reproducible donde cualquier dev puede levantar Odoo + el módulo en un comando.

- [ ] `docker-compose.yml` con Odoo 17 + Postgres 15 + volumen para `addons/`
- [ ] `addons/indigo_decors/__manifest__.py` mínimo (nombre, versión, dependencias: `base`, `mail`, `web`, `project`, `account`)
- [ ] Estructura del módulo: `models/`, `views/`, `data/`, `reports/`, `security/`, `static/`
- [ ] `ir.model.access.csv` con grupos: `Indigo / User`, `Indigo / Manager`, `Indigo / Contractor (portal)`
- [ ] README de cómo levantar el entorno + cómo instalar el módulo
- [ ] Script de seed con datos demo (3 dealers, 5 diseños, 2 órdenes)

### Fase 1 — Modelo de datos núcleo (1-2 semanas)

**Entregable:** modelos que reflejan el negocio. Sin UI bonita aún, solo las vistas tree/form básicas.

**Modelos:**
- [ ] `indigo.dealer` — extiende `res.partner` (Lock Tight, Web Indigo, USA Windows, …)
  - Campos custom: `pipeline_id` (qué etapas opcionales aplican), `dealer_code`, `default_price_per_sqf`
- [ ] `indigo.design` — catálogo de diseños
  - Campos: `code` (ID01, TD-SD-W06), `door_type` (SD/DD/sidelite), `image`, `active`
- [ ] `indigo.stage` — etapas (las 13 + "On Hold")
  - Campos: `name`, `sequence`, `is_optional`, `is_default`, `fold`
  - Seed con las 13 etapas + estado paralelo "On Hold"
- [ ] `indigo.dealer.pipeline` — qué etapas opcionales (2-5) aplican por dealer
- [ ] `indigo.order` — orden de trabajo (la entidad principal)
  - Campos: `name` (secuencia), `dealer_id`, `client_name`, `phone`, `email`, `address`,
    `dealer_ref` (ref que el dealer le pone al cliente final), `stage_id`, `on_hold` (bool),
    `assigned_user_ids` (M2M), `payment_state`, `notes`
  - Computed: `total_sqf`, `total_painter_payout`, `total_installer_payout`
- [ ] `indigo.order.line` — una línea por puerta/pieza dentro de la orden
  - Campos: `order_id`, `design_id`, `door_type`, `color`, `glass_type`,
    `width`, `height`, `sqf` (computed = w×h/144), `qty`, `notes_line`
- [ ] `indigo.order.incident` — bitácora de incidencias por orden (timeline)
  - Campos: `order_id`, `user_id`, `date`, `category` (medida/pintura/cliente/otro), `description`, `attachment_ids`
- [ ] `indigo.contractor.rate` — tarifas (pintor SQF, instalador por puerta)
- [ ] `indigo.payout` — liquidaciones generadas

**Aprovechar Odoo built-in:**
- `mail.thread` + `mail.activity.mixin` en `indigo.order` (chatter + actividades nativas)
- `ir.attachment` para fotos del contrato/puerta

### Fase 2 — Kanban, asignación, correos (1 semana)

- [ ] Vista Kanban de `indigo.order` agrupada por `stage_id`
- [ ] Filtros: por dealer, por asignado, "Mis órdenes", "En espera"
- [ ] Botón rápido para mover de etapa (drag&drop nativo de Odoo)
- [ ] Toggle "On Hold" (oculta de la columna activa, aparece en filtro propio)
- [ ] Server actions / automatizaciones:
  - Al cambiar `stage_id` → enviar correo al `assigned_user_ids` de esa etapa
  - Al crear incidencia → notificar al manager
- [ ] Plantillas de correo (`mail.template`) en español para cada etapa

### Fase 3 — Documentos QWeb (1-2 semanas)

- [ ] **Ficha de Orden** (A4) — para imprimir y enviar por correo
  - Datos del dealer + cliente final + dirección + todas las líneas + total SQF
- [ ] **Etiqueta del Diseñador** (12.7 × 57.15 mm) — una por línea de orden
  - Cliente / Dealer / Medidas / Tipo–Color–Vidrio / Nº Orden / PRIV / Cantidad / Código diseño
  - Formato: PDF para impresora genérica + opción ZPL (Zebra) si confirman impresora
  - **Pendiente confirmar**: ¿código de barras / QR?
- [ ] **Hoja del Pintor** — tabla con Company / Order# / Client / Color / Door Type / SQF / Price / Total
  - `price = $8` constante, `total = SQF × 8`
- [ ] **Reporte de direcciones de instalación** — listado de órdenes en etapa "Installation Scheduled" con dirección + fecha + asignado
- [ ] Botones de impresión en el formulario de orden

### Fase 4 — Liquidaciones + portal contratistas (1 semana)

- [ ] **Liquidación pintor**: al marcar etapa "Painting" como completada, generar payout del trabajo (SQF × $8)
- [ ] **Liquidación instaladores**: job semanal que acumula puertas instaladas × $35 por instalador
- [ ] Vista `indigo.payout` con: contratista, período, monto, estado (pendiente/pagado), líneas detalle
- [ ] Reporte QWeb de liquidación imprimible
- [ ] **Portal instaladores**: usuarios "portal" de Odoo (sin licencia interna)
  - Ver sólo sus órdenes asignadas
  - Subir fotos desde móvil al completar instalación
  - Ver su acumulado de la semana

### Fase 5 — Deploy + entrenamiento + go-live (1 semana)

- [ ] Provisionar VPS (Ubuntu 22.04, Docker, Nginx, Certbot/HTTPS)
- [ ] Deploy del módulo en prod
- [ ] Crear usuarios reales (Majela, Javier, diseñador, pintor, administración, manager)
- [ ] Cargar dealers reales + catálogo de diseños
- [ ] **2 sesiones de capacitación** al equipo (1.5h c/u): operación diaria + administración
- [ ] Manual breve PDF (cómo crear orden, mover etapas, imprimir docs, reportes)
- [ ] Período de hipercuidado (2 semanas post go-live) — ajustes finos

---

## Pendientes del cliente (bloqueantes para ciertas fases)

| Item | Bloquea fase | Workaround |
|---|---|---|
| Modelo impresora etiquetas | Fase 3 | Generar PDF genérico, ZPL después |
| ¿Código de barras / QR en etiqueta? | Fase 3 | Default: sin código, agregar si piden |
| Lista oficial de dealers | Fase 5 (carga) | Usar los 3 conocidos en demo |
| Lista oficial de códigos de diseño | Fase 5 (carga) | Usar los ~22 detectados en catálogo |
| Precio al dealer (SQF? por dealer?) | Fase 1 (campo `default_price_per_sqf`) | Dejar campo, llenar después |
| ¿Aclarar volumen 20-40 — semana o mes? | — | Dimensionamiento del VPS |
| Confirmar dominio | Fase 5 | Usar subdominio temporal mientras |

## Riesgos / alertas

- **Etiqueta 12.7×57.15 mm es muy chica** — caben ~6-8 líneas de texto a 6pt. Hay que probar prototipo impreso temprano (Fase 3), no al final.
- **Multi-pieza por orden** complica los reportes (especialmente la hoja del pintor, que en el ejemplo manual tiene una fila por puerta). Modelar bien las líneas desde Fase 1.
- **"On Hold" paralelo a las 13 etapas** — no es una etapa más, es un flag. Si se modela mal (como etapa 14) rompe el flujo.
- **Reentrenar al equipo** ("tenemos Odoo pero no sabemos usarlo") — Fase 5 capacitación es crítica, no opcional.

## Estimación total

**~6-8 semanas calendario** asumiendo 1 dev full-time. Sumar 2 semanas de hipercuidado post go-live.

---

## Estado de avance (2026-05-26)

| Fase | Estado | Notas |
|---|---|---|
| 0 — Setup Docker + skeleton | ✅ COMPLETO | docker-compose con Odoo 17 + Postgres 15 + MailHog |
| 1 — Modelo de datos núcleo | ✅ COMPLETO | 8 modelos, 13 etapas seed, ACL, mail.thread |
| 2 — Kanban + correos | ✅ COMPLETO | Mail template + trigger en `write()`, verificado en MailHog |
| 3 — 4 reportes QWeb | ✅ COMPLETO | Ficha, etiqueta (con QR), hoja pintor, direcciones |
| 4 — Liquidaciones + portales | ✅ COMPLETO | Pintor + instalador + wizard semanal + comprobante PDF + portal instalador + portal dealer |
| 5 — Deploy VPS + capacitación | ⏳ PENDIENTE | Esperando confirmación cliente sobre items críticos (ver CLAUDE.md §6) |

**Adicionales implementados sobre PLAN.md original** (asunciones profesionales):
- Comprobante de liquidación QWeb (PDF firmable)
- Portal de dealers (no solo instaladores) con creación de órdenes web
- Subgrupos por área (Diseñador / CNC / Pintor / Office) para ACL fino
- Campo PRIV (ref interna) + QR code en etiqueta
- Precio por dealer + total a cobrar computed
- 3 dealers + 33 códigos de diseño pre-cargados como demo data
- Fotos del contrato/puerta en orden (Many2many ir.attachment)
