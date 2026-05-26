# indigo_decors

Módulo Odoo 17 a medida para Indigo Decors.

## Modelos previstos

- `indigo.order` — orden de trabajo (extiende o reemplaza `sale.order`)
- `indigo.dealer` — extiende `res.partner` con metadatos del dealer
- `indigo.stage` — etapas del pipeline (13 default, configurables)
- `indigo.dealer.pipeline` — qué etapas opcionales aplican por dealer
- `indigo.design` — catálogo de diseños (ID01..ID34, TD-SD-W##, etc.)
- `indigo.contractor.rate` — tarifa por SQF/pieza por contratista
- `indigo.payout` — liquidación acumulada a contratistas

## Reportes QWeb

- Ficha de Orden
- Etiqueta del Diseñador (impresora térmica)
- Hoja del Pintor
- Liquidación de contratistas

## Estado

Placeholder — pendiente respuesta del cliente al cuestionario (ver `CLAUDE.md` §6)
antes de iniciar la implementación.
