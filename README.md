# Indigo Decors — Sistema de Gestión de Órdenes

Repositorio del proyecto **Indigo Decors** (https://www.indigodecors.com): taller de
puertas decorativas (CNC, pintura, instalación) que trabaja con dealers (Lock Tight,
Web Indigo, USA Windows, etc.).

**Stack acordado:** Odoo 17 Community + módulo a medida `indigo_decors`.

> Propuesta aceptada el 2026-05-26.

---

## Estructura

```
.
├── PROPUESTA_Odoo.md          Propuesta vigente (v1.0)
├── CLAUDE.md                  Contexto del proyecto para asistencia con IA
├── addons/
│   └── indigo_decors/         Módulo Odoo a medida (en desarrollo)
├── demo-spa/                  Prototipo React de las pantallas custom (referencia UX)
├── docs/
│   ├── source-materials/      Material original del cliente (WhatsApp, catálogo, etiquetas)
│   └── archive/               Propuestas previas (Decors / MVP) — superadas
└── scripts/
    └── _build_docx.py         Generador de la propuesta en .docx
```

## Qué resuelve el sistema

- Captura unificada de órdenes (web dealer, WhatsApp, papel).
- Tablero de producción Kanban con **13 etapas configurables por dealer**.
- Generación automática de **Ficha de Orden**, **Etiqueta del Diseñador**
  (impresora térmica) y **Hoja del Pintor**.
- Cálculo de liquidación a contratistas por SQF.
- Portal de instaladores con usuarios "portal" de Odoo (sin licencia interna).

## Entorno de desarrollo (Docker)

Requiere Docker Desktop corriendo. Desde la raíz del repo:

```bash
docker compose up -d        # levantar Odoo 17 + Postgres 15
docker compose logs -f odoo # ver logs
docker compose down         # detener (mantiene datos)
docker compose down -v      # detener y borrar datos (reset total)
```

Odoo queda en **http://localhost:8069**.

**Primera vez** (crear base de datos):
1. Ir a http://localhost:8069
2. Master Password: `admin` (definido en `config/odoo.conf`)
3. Database Name: `indigo`
4. Email admin / password a elección
5. Marcar "Demo data" si quieres datos de ejemplo
6. Crear

**Instalar el módulo `indigo_decors`:**
1. Activar modo desarrollador (Settings → activar developer mode)
2. Apps → Update Apps List
3. Quitar el filtro "Apps" del buscador
4. Buscar "Indigo Decors" → Install

**Reinstalar el módulo tras cambios en código** (DB local: `indigo-db`):
```bash
docker compose exec odoo odoo -c /etc/odoo/odoo.conf -d indigo-db -u indigo_decors --stop-after-init
docker compose restart odoo
```

## Demo SPA

```bash
cd demo-spa
npm install
npm run dev
```

> El demo SPA **no es el entregable final** — es referencia visual de UX para alinear
> las pantallas Odoo con el cliente.

## Módulo Odoo

En `addons/indigo_decors/` (placeholder). Modelos previstos:
`indigo.order`, `indigo.dealer`, `indigo.stage`, `indigo.dealer.pipeline`,
`indigo.design`, `indigo.contractor.rate`, `indigo.payout`.

Hosting previsto: VPS dedicado (DigitalOcean / Hetzner), no Odoo.sh.
