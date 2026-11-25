# DESIGN.md — Indigo Decors

Hay dos superficies con su propio sistema visual, las dos con el mismo azul de
marca:

| | Dónde | Sistema |
|---|---|---|
| **Tienda** (indigodecors.com) | `addons/indigo_theme` (este repo) | este archivo |
| **Panel de operación** (app.indigodecors.com) | repo `indigo-next` | `indigo-next/DESIGN.md` |

Regla común a las dos: **pulir no es rediseñar**. Lo que el equipo o los dealers
ya usan se queda como está salvo que lo pidan; todo cambio visual se enseña
primero en local y se sube con visto bueno.

## Tienda — `indigo_theme`

### Dónde vive cada cosa

- `static/src/scss/primary_variables.scss` — lo que Odoo necesita saber al
  compilar: paleta `indigo-blue` y la fuente del sitio. **No** usar `map-merge()`
  con variables del core de Odoo (todavía no existen en ese punto).
- `static/src/css/theme.css` — la hoja real (≈3.300 líneas), inyectada por
  `<link>` saltándose el bundle. Empieza con los **tokens** en `:root`: todo lo
  demás debería referenciarlos.
- `static/src/js/theme.js` — comportamiento pequeño de la tienda.
- `static/src/img/` — logo, galería y fotos.

### Color

- **Azul Indigo `#1f4486`** = `--indigo-600` en el tema (`o-color-1` en Odoo):
  botones, enlaces, acentos. Escala completa `--indigo-50` … `--indigo-950`;
  `--indigo-500` (`#3a5ea3`) para hover y secundario.
- Neutros `--neutral-0` … (de blanco a tinta), sin tinte de color.
- Fondo blanco / `#f8f8f8`, tinta `#111111`.

### Tipografía

- **Noto Sans** para todo el texto (interfaz, navegación, botones, cuerpo).
- **Cormorant Garamond** solo para lo grande: `.h-display`, `.display-1…3`,
  títulos de tarjeta y de mosaico (`.c-card__title`, `.indigo-tile h3`) y cifras
  destacadas (`.indigo-stat-number`). Nunca en botones ni etiquetas.

### Catálogo

- Una tarjeta por familia de diseño, con selector de tipo de puerta, y los
  diseños **CUSTOM** primero. Detalle y migración en la memoria del proyecto
  (storefront / catálogo).
- Las fotos reales de puertas instaladas son el elemento visual de la tienda:
  nada de ilustraciones genéricas ni fondos decorativos.

## Panel

Ver `indigo-next/DESIGN.md`: Inter, neutros `slate`, el mismo `#1f4486` como
`indigo-700`, modo oscuro por redefinición de variables en `globals.css`, y la
tarjeta de cifras única (`kpi-card.tsx`).
