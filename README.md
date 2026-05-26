# Indigo Decors — Sistema de Gestión de Órdenes

Sistema a medida sobre **Odoo 17 Community** para el taller **Indigo Decors**
(https://www.indigodecors.com): captura de órdenes, pipeline de producción,
liquidaciones a contratistas, portales para dealers e instaladores.

---

## Documentación

| Documento | Para quién | Contenido |
|---|---|---|
| [docs/MANUAL_USUARIO.md](docs/MANUAL_USUARIO.md) | Equipo del taller (Office, Diseñador, CNC, Pintor) + dealers + instaladores | Día a día: cómo crear una orden, moverla por etapas, imprimir documentos, usar el portal móvil, etc. |
| [docs/ADMIN.md](docs/ADMIN.md) | Manager / dueño | Configurar dealers, tarifas, etapas, SLA, accesos portal, gestionar liquidaciones, ver dashboards |
| [docs/OPERACIONES.md](docs/OPERACIONES.md) | DevOps / técnico | Levantar entorno, backup/restore, activar Twilio (SMS/WhatsApp), deploy a producción, troubleshooting |
| [PROPUESTA_Odoo.md](PROPUESTA_Odoo.md) | Cliente | Propuesta comercial vigente |
| [PLAN.md](PLAN.md) | Equipo de proyecto | Plan por fases con estado de avance |
| [CLAUDE.md](CLAUDE.md) | Asistencia AI | Contexto del proyecto, decisiones técnicas, asunciones |

---

## Quick start (local)

```bash
docker compose up -d                # Odoo 17 + Postgres 15 + MailHog
open http://localhost:8069          # Crear DB "indigo-db"
```

Activar el módulo: Settings → Activar developer mode → Apps → Update Apps List → "Indigo Decors" → Install.

**URLs útiles:**
- http://localhost:8069 — Odoo (backoffice)
- http://localhost:8025 — MailHog (correo capturado en dev)
- http://localhost:5433 — Postgres (host:port para clientes externos)

Detalle completo en [docs/OPERACIONES.md](docs/OPERACIONES.md).

---

## Estructura del repo

```
.
├── PROPUESTA_Odoo.md          Propuesta comercial
├── CLAUDE.md                  Contexto del proyecto
├── PLAN.md                    Plan por fases
├── README.md                  Este archivo
├── docs/                      Manuales de usuario / admin / ops
├── addons/
│   └── indigo_decors/         Módulo Odoo a medida
│       ├── models/            14 modelos
│       ├── views/             20 vistas
│       ├── reports/           6 reportes QWeb PDF
│       ├── controllers/       Portal (dealer + instalador + tracking público)
│       ├── wizards/           3 wizards
│       ├── data/              Seed: dealers, diseños, etapas, tarifas, crons
│       ├── i18n/              Traducciones ES (source) + EN
│       ├── tests/             11 tests automatizados
│       └── security/          Grupos + record rules + ACL
├── demo-spa/                  Prototipo React (referencia UX, no entregable)
├── scripts/                   Utilidades dev (seed, backfill, testing)
├── docker-compose.yml         Odoo + Postgres + MailHog
└── config/odoo.conf           Configuración Odoo
```

---

## Estado del proyecto

| Fase | Estado |
|---|---|
| 0 — Setup Docker + skeleton | ✅ |
| 1 — Modelo de datos núcleo | ✅ |
| 2 — Kanban + correos | ✅ |
| 3 — 4 reportes QWeb | ✅ |
| 4 — Liquidaciones + portales | ✅ |
| 4.5 — Mejoras (SLA, tracking público, firma cliente, rankings, inventario, SMS/WhatsApp placeholders) | ✅ |
| 5 — Deploy VPS + capacitación | ⏳ pendiente |

**Verificación**: 11 tests automatizados pasando. Multiidioma ES/EN.
