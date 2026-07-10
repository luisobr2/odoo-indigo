# Spec — Filtros de Tipo + Color en /shop (storefront Indigo)

Fecha: 2026-07-09
Repos: `odoo-indigo` (`indigo_decors`, `indigo_theme`)

## Objetivo

En la tienda pública (`indigodecors.com/shop`) habilitar filtros por **tipo de
puerta** (Single/Double) y **color/acabado** (Negro/Blanco/Bronce). Además, por
defecto cada tarjeta de producto debe mostrar la foto **single door, color
negro**. Los filtros son **server-side** (parámetros en la URL, paginación
nativa, URLs compartibles).

## Contexto (estado actual)

- Catálogo: **49 tarjetas publicadas**, una por familia de diseño (se publica el
  producto **DD**; el SD queda despublicado pero sigue ordenable). Sin variantes
  de color (el color se sirve como imagen vía route, no como variante).
- Ruta de imagen por color/tipo ya existe:
  `/indigo/door_image/<design_id>/<color>?type=<SD|DD|sidelite>` (controlador
  `IndigoDesignImage` en `indigo_decors/controllers/website_sale_custom.py`).
- `product.template.indigo_family_types()` devuelve, por familia, los tipos
  disponibles con su `design_id` (`[{door_type, label, product_id, design_id}]`).
- **Datos de disponibilidad (auditados 2026-07-09):**
  - Solo **1 familia** (ID93-DD) es DD-only (no tiene single).
  - Los **92 diseños permiten los 3 colores** (ningún `allowed_colors`
    restrictivo). → El color **nunca oculta**; el tipo oculta solo DD-only.

## Comportamiento

- **Default** (sin `type` ni `color` en la URL): se ven **todas** las tarjetas,
  cada una con la foto **SD + negro**.
- **Filtros** (barra arriba del grid):
  - **Tipo**: Todos · Single (SD) · Double (DD).
  - **Color**: Todos · Negro · Blanco · Bronce.
- Al elegir un filtro → recarga `/shop?type=…&color=…` (preservando `search` y
  `category` existentes):
  - Las tarjetas muestran la foto de ese **tipo + color**.
  - **Ocultar**: solo por **tipo** — si `type=SD`, se ocultan las familias sin
    single (hoy solo ID93). `type=DD` no oculta nada (todas las tarjetas son DD).
    El **color no oculta** (dato-driven).
- **Imagen de cada tarjeta** = `/indigo/door_image/<design>/<color>?type=<type>`
  con `type = param o 'SD'` y `color = param o 'black'`, y `design` = el
  `design_id` de la familia para ese tipo (de `indigo_family_types()`), con
  fallback al diseño propio de la tarjeta si la familia no tiene ese tipo.

## Componentes

### 1. Campo stored `indigo_avail_types` (product.template) — `indigo_decors`
- `Char`, `store=True`, comma-separado con los tipos de la familia (ej. `"SD,DD"`
  o `"DD"`). Poblado desde `indigo_family_types()`.
- Se usa en el dominio del shop para ocultar por tipo:
  `type=SD → [('indigo_avail_types','like','SD')]`,
  `type=DD → [('indigo_avail_types','like','DD')]`.
- Recompute: al ser dependiente de productos hermanos (no un depends limpio), se
  recomputa con un script en el deploy (patrón de los scripts en `scripts/`), y
  se debe re-correr cuando se agreguen/cambien familias de diseño. (Optimización
  futura: engancharlo al guardado del editor de familias.)

### 2. Controller — hereda `WebsiteSale` — `indigo_decors`
- `_get_search_domain(...)`: llama a super y, si `request.params.get('type')` ∈
  {SD, DD}, agrega `('indigo_avail_types','like', type)`. El `color` **no** entra
  al dominio.
- `shop(**post)`: llama a super, y agrega al `response.qcontext`:
  `indigo_type` (SD/DD/'') y `indigo_color` (white/bronze/black/''), validados,
  para que el template arme imágenes y resalte el filtro activo.

### 3. QWeb — barra de filtros — `indigo_theme`
- Hereda `website_sale.products` (o el wrapper del grid) e inyecta una barra
  arriba del grid con dos grupos de links (Tipo, Color).
- Cada link construye el href preservando los params actuales (`search`,
  `category`, y el otro filtro) y toggle del suyo; "Todos" quita el param.
- Resalta visualmente el valor activo (`indigo_type` / `indigo_color`).

### 4. QWeb — imagen de tarjeta — `indigo_theme`
- Hereda la plantilla del ítem del grid (`website_sale.products_item`) y
  reemplaza el `src` de la imagen por la URL de `door_image`:
  ```
  itype  = indigo_type or 'SD'
  icolor = indigo_color or 'black'
  ift    = [f for f in product.indigo_family_types() if f['door_type']==itype]
  idesign= ift[0]['design_id'] if ift else product.indigo_design_id.id
  src    = '/indigo/door_image/%s/%s?type=%s' % (idesign, icolor, itype)
  ```

## Casos borde

- **ID93-DD** (DD-only): visible por defecto (foto cae a DD-negro vía fallback
  del route). Se oculta al filtrar `type=SD`.
- **CUSTOM** (diseño flexible, un solo design con fotos SD y DD): el `?type=`
  ya lo distingue (fix del 2026-07-09). `indigo_avail_types` de CUSTOM = "SD,DD".
- **Color nunca oculta**: la barra de color solo cambia imágenes.
- **Preservar** `search`/`category`: los links de filtro no deben perderlos.

## Verificación

- `/shop` (default) → todas las tarjetas en **single negro**.
- `/shop?type=DD` → fotos en **double** (mismas familias); `?type=SD` **oculta
  ID93**.
- `/shop?color=bronze` → fotos en **bronce**, sin ocultar.
- Combinado `?type=DD&color=black` → dobles en negro.
- Búsqueda/categoría preservadas al filtrar.
- Deploy: recompute `indigo_avail_types` + `-u indigo_decors,indigo_theme` +
  restart. Bump `theme.js`/`theme.css` `?v=` solo si cambian esos assets.

## Fuera de alcance

- Ocultar por color (no hay datos que lo justifiquen).
- Filtros nativos de Odoo por atributos (no encaja con 1 tarjeta/familia).
- Cachear `indigo_family_types()` en campos stored (optimización futura).
