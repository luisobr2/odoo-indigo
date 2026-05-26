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
