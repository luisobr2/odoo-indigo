# Demo SPA — Indigo Decors

Demo navegable del sistema de gestión de producción, con **datos de ejemplo**.
Sirve para presentárselo al cliente antes de desarrollar el sistema real.

## Cómo ejecutarlo

```bash
cd demo-spa
npm install      # solo la primera vez
npm run dev      # abre en http://localhost:5173
```

## Qué incluye

- **Tablero de Producción** — Kanban con las 13 etapas; tarjetas arrastrables
  entre columnas. Las etapas opcionales (Design / Measurement) van marcadas `OPC`.
  Filtros por dealer y por rol.
- **Detalle de Orden** — toda la info + historial + generación de documentos
  (ficha de orden, etiqueta del diseñador, hoja del pintor).
- **Nueva Orden** — captura rápida (web / WhatsApp / papel en una sola pantalla).
- **Pagos a Contratistas** — liquidación del pintor calculada automática (SQF × tarifa).
- **Reportes** — KPIs y gráficos por etapa y por dealer.

## Notas técnicas

- React + Vite. Navegación con **HashRouter** — las rutas van tras el `#`
  para no chocar con `wp-admin.php?page=indigo` al embeber en WordPress.
- `base: './'` en `vite.config.js` para que los assets carguen embebidos.
- Datos mock en `src/data/mockData.js`. En producción esto se reemplaza por
  llamadas a la API REST de WordPress/WooCommerce.
- Para integrar en WP: el plugin compila este `build` y lo monta en un
  `<div id="indigo-root">` dentro de una página del admin.
