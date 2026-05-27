# Indigo Decors — Image generation prompts

Inventario completo de imágenes hardcoded que **no son coherentes con la marca**
(stock Unsplash genérico: casas modernas, talleres random, contractors sin
contexto). Reemplazarlas por fotos brand-coherentes — generadas con AI o
fotografía real — eleva instantáneamente la percepción del sitio.

---

## Cómo usar este doc

Cada bloque trae:

1. **Filename** sugerido para subir al theme (`addons/indigo_theme/static/src/img/photo/`).
2. **Aspect ratio** y dónde se usa (página + sección).
3. **Prompt universal** — descriptivo, sirve para Google Imagen 3 / Veo /
   ChatGPT image generator / Flux / cualquier modelo moderno.
4. **Versión Midjourney v6** con flags (`--ar`, `--style raw`, `--s`, etc.).
5. **Notas** sobre composición / paleta / iconografía.

Marca a respetar en todas:
- **Negative space friendly** (siempre dejar zona donde overlay copy negro o blanco).
- **Florida natural light** — golden hour warm tones, no flash dura, no HDR.
- **Doors are the hero** — la puerta domina la composición; entornos minimal.
- **No people-as-models**. Solo manos / siluetas / espaldas si hace falta presencia humana. Evita stock-photo contractors sonriendo a cámara.
- **Indigo color accents** — un detalle azul Indigo (#1f4486) si aparece naturalmente (puerta, sky, glass tint). No forzado.
- **Sin texto sobreimpreso, logos, watermarks, sin Coca-Cola / Apple visibles**.

---

## 1. Home hero · Gallery hero

- **Filename**: `home-hero-miami-door.jpg`
- **Aspect**: 16:9 ultra-wide → ideal 2400×1350 px
- **Usado en**: `home_page.xml:10`, `gallery_page.xml:10`, `home_page.xml:99` (mosaic)
- **Reemplaza**: `unsplash.com/photo-1600585154340` (casa moderna genérica)

### Prompt universal
> Editorial architectural photograph of a high-end Miami modern home entrance at golden hour, featuring a wrought-iron-and-glass decorative front door with intricate geometric pattern, painted matte black, hurricane-rated, set into a clean white stucco facade with subtle palm tree shadows. Wide-angle composition, door positioned in the right third, soft warm late-afternoon Florida sunlight raking across the door's metalwork, deep navy-blue sky, no people, no text, no logos. Cinematic depth, shallow background blur, premium real estate publication aesthetic. Shot on Sony A7R V, 24mm lens, f/4.

### Midjourney v6
> `editorial architectural photograph, modern Miami home entrance at golden hour, decorative wrought-iron-and-glass front door with geometric pattern matte black hurricane-rated, white stucco facade, palm tree shadows, door in right third, warm raking Florida sunlight, deep navy-blue sky, no people, cinematic depth, shallow background blur, premium real-estate magazine aesthetic --ar 16:9 --style raw --s 250 --v 6`

### Notas
- Lado izquierdo debe quedar limpio para overlay del titular *"A door that tells your story."*
- Si la puerta sale demasiado pequeña, regenerar con "tighter framing, door dominates the frame".

---

## 2. Single doors — category card

- **Filename**: `cat-single-door.jpg`
- **Aspect**: 1:1 (600×600 px mínimo)
- **Usado en**: `home_page.xml:50`, `gallery_page.xml:59`
- **Reemplaza**: `unsplash.com/photo-1558618666` (puerta de madera close-up genérica)

### Prompt universal
> Studio product shot of a single-leaf Indigo decorative front door, matte black wrought-iron frame with intricate Art Deco geometric grille and frosted glass insert, square 1:1 composition, door centered against soft cream-colored seamless backdrop, gentle gradient lighting from above, no people, no text, no shadows on background. Premium catalog photography aesthetic. Door fills 80% of frame.

### Midjourney v6
> `studio product shot, single-leaf decorative front door, matte black wrought-iron Art Deco geometric grille, frosted glass insert, cream seamless backdrop, gentle top lighting, no people, no text, premium catalog aesthetic, door fills frame --ar 1:1 --style raw --s 200 --v 6`

### Notas
- Evitar grain, evitar bokeh, evitar manos sosteniendo nada.
- Si el grille sale demasiado ornamentado, regenerar pidiendo "clean modern Art Deco lines".

---

## 3. Double doors — category card

- **Filename**: `cat-double-door.jpg`
- **Aspect**: 1:1 (600×600)
- **Usado en**: `home_page.xml:59`, `gallery_page.xml:72`, `home_page.xml:102`
- **Reemplaza**: `unsplash.com/photo-1505691938895`

### Prompt universal
> Studio product shot of a symmetric double-leaf decorative front door, two large iron-and-glass panels with matching mirror-image geometric grille pattern, matte bronze finish, square 1:1 composition, doors centered against soft warm-grey seamless backdrop, even diffused lighting, no people, no text, no environmental context. Premium architectural catalog aesthetic. Doors fill 85% of frame, dramatic but not theatrical.

### Midjourney v6
> `studio product shot, symmetric double-leaf decorative front door, two iron-and-glass panels mirror-image geometric grille, matte bronze finish, warm-grey seamless backdrop, even diffused lighting, no people, no text, premium architectural catalog, doors fill frame --ar 1:1 --style raw --s 200 --v 6`

---

## 4. Sidelites — category card

- **Filename**: `cat-sidelites.jpg`
- **Aspect**: 1:1 (600×600)
- **Usado en**: `home_page.xml:68`, `gallery_page.xml:83`
- **Reemplaza**: `unsplash.com/photo-1517472292914`

### Prompt universal
> Studio product shot showing a central decorative door flanked by two narrow vertical sidelite panels, matching iron-and-glass geometric pattern in white finish, square composition, full assembly centered against pale-blue seamless backdrop, soft architectural lighting, no people, no text. The sidelites are clearly visible as separate slim glass panels beside the main door. Premium catalog aesthetic.

### Midjourney v6
> `studio product shot, central decorative door flanked by two narrow vertical sidelite panels, iron-and-glass geometric pattern white finish, full assembly centered, pale-blue seamless backdrop, soft architectural lighting, no people, no text, premium catalog --ar 1:1 --style raw --s 200 --v 6`

### Notas
- Clave: que se vea claramente la asimetría puerta-grande + dos paneles laterales delgados (que es lo que define "sidelites" como producto).

---

## 5. Custom design — category card

- **Filename**: `cat-custom.jpg`
- **Aspect**: 1:1 (600×600)
- **Usado en**: `home_page.xml:77`, `gallery_page.xml:94`
- **Reemplaza**: `unsplash.com/photo-1571939228382`

### Prompt universal
> Editorial overhead shot of a designer's worktable with hand-drawn pencil sketches of decorative door designs, brass drafting instruments, paint chip samples in black/white/bronze, fabric swatch of indigo blue, and a small carved wood door sample at one corner. Square composition, warm natural window light from upper-left, no people, no text on visible papers, premium architectural studio aesthetic, color grading: warm earth tones with indigo accent.

### Midjourney v6
> `editorial overhead shot, designer worktable, hand-drawn pencil sketches of decorative door designs, brass drafting instruments, paint chips black/white/bronze, indigo blue fabric swatch, small carved wood door sample in corner, warm natural window light from upper-left, no people, no text, premium architectural studio aesthetic, warm earth tones with indigo accent --ar 1:1 --style raw --s 250 --v 6`

---

## 6. Lifestyle mosaic · "See it installed" / "Where it all happens"

Cuatro imágenes para los mosaicos lifestyle del home y about page. Cada una
muestra una situación distinta. Aspect ratio variado (el mosaico CSS las
combina con diferentes tamaños).

### 6a. `lifestyle-installed-modern.jpg`  ·  Aspect 4:3
- **Usado en**: home mosaic position 1, gallery mosaic
- **Reemplaza**: `unsplash.com/photo-1582268611958`

> Wide editorial photograph of a modern Coral Gables home with a decorative iron-and-glass Indigo door installed as the main entrance, evening blue hour, warm interior light glowing through the door's frosted glass insert and casting geometric patterns onto the front porch tiles. No people, no cars, no text. Composition emphasizes the door as the focal point against minimal contemporary architecture. Premium lifestyle real-estate aesthetic.

> `wide editorial photo, modern Coral Gables home, decorative iron-and-glass Indigo door main entrance, evening blue hour, warm interior light through frosted glass casting geometric patterns on porch tiles, no people, no cars, no text, door is focal point, minimal contemporary architecture, premium lifestyle real-estate aesthetic --ar 4:3 --style raw --s 220 --v 6`

### 6b. `lifestyle-hallway-door.jpg`  ·  Aspect 3:4 (portrait)
- **Usado en**: home mosaic position 4, gallery mosaic
- **Reemplaza**: `unsplash.com/photo-1567016432779`

> Tall portrait photograph of an upscale Miami home interior hallway with a decorative iron-and-glass interior door at the end of the corridor, mid-morning natural light streaming through, polished marble floor reflecting the door's geometric grille, off-white walls, single curated indoor plant. No people, no text. Editorial interior magazine aesthetic, indigo accent in the door frame.

> `tall portrait, upscale Miami home interior hallway, decorative iron-and-glass door at corridor end, mid-morning natural light, polished marble floor reflecting geometric grille, off-white walls, single indoor plant, no people, no text, editorial interior magazine aesthetic, indigo accent in door frame --ar 3:4 --style raw --s 220 --v 6`

### 6c. `lifestyle-living-door.jpg`  ·  Aspect 3:2
- **Usado en**: gallery additional tile
- **Reemplaza**: `unsplash.com/photo-1600573472556`

> Editorial photograph of a Miami waterfront home's living room with a custom Indigo French double door opening to a terrace, late afternoon golden light, ocean view in background, white linen sofa in foreground out of focus, no people, no text. Architectural Digest aesthetic, color grading: warm whites with indigo blue ocean.

> `editorial photo, Miami waterfront home living room, custom French double door opening to terrace, late afternoon golden light, ocean view background, white linen sofa foreground out of focus, no people, no text, Architectural Digest aesthetic, warm whites with indigo blue ocean --ar 3:2 --style raw --s 220 --v 6`

### 6d. `lifestyle-entrance-wide.jpg`  ·  Aspect 3:2
- **Usado en**: home mosaic position 2, gallery additional tile
- **Reemplaza**: `unsplash.com/photo-1554995207`

> Wide-angle exterior photograph of a luxury Floridian home entrance walkway leading to a double Indigo decorative door, lush tropical landscaping (palms and bird-of-paradise) framing both sides, midday Florida sun softened by overcast, no people, no cars, no text. Composition: viewer is walking toward the door, depth and invitation. Premium lifestyle aesthetic.

> `wide-angle exterior photo, luxury Floridian home entrance walkway leading to double decorative door, lush tropical landscaping palms and bird-of-paradise framing both sides, midday Florida sun softened by overcast, no people, no cars, no text, viewer walking toward door, depth and invitation, premium lifestyle aesthetic --ar 3:2 --style raw --s 220 --v 6`

---

## 7. Dealer program hero · About workshop column · Home dealer column

Tres usos diferentes del mismo placeholder (dos personas hablando). Hacen falta
DOS imágenes nuevas para diferenciar contextos.

### 7a. `dealer-program-hero.jpg`  ·  Aspect 16:9
- **Filename usado en**: `dealer_program_page.xml:11`
- **Reemplaza**: `unsplash.com/photo-1556909114` (uso #1)

> Wide editorial photograph of an Indigo Decors showroom in Miami, multiple decorative iron-and-glass doors mounted vertically on a clean white display wall, soft daylight from skylights, a single Indigo brochure on a minimalist wooden bench in foreground, navy-blue accent wall on one side, no people, no text. B2B premium catalog aesthetic, composition leaves the left third negative for overlay copy.

> `wide editorial photo, Indigo Decors showroom Miami, multiple decorative iron-and-glass doors mounted vertically on clean white display wall, soft skylight daylight, single brochure on minimalist wooden bench foreground, navy-blue accent wall on one side, no people, no text, B2B premium catalog, left third negative space for copy --ar 16:9 --style raw --s 220 --v 6`

### 7b. `workshop-craftsman-side.jpg`  ·  Aspect 4:5 (portrait)
- **Filename usado en**: `home_page.xml:195`, `about_page.xml:65`
- **Reemplaza**: `unsplash.com/photo-1556909114` (usos #2 y #3)

> Tall editorial photograph of a craftsman's gloved hands (forearms visible only, no face) carefully sanding the wrought-iron grille of a decorative door panel laid flat on a workbench, warm shop lighting, sawdust particles in the air catching light, indigo-blue painter's apron on a hook in background out of focus, no other people, no text. Documentary craftsmanship aesthetic, color grading: warm amber with cool blue accent.

> `tall editorial photo, craftsman gloved hands forearms only no face, sanding wrought-iron grille of decorative door panel on workbench, warm shop lighting, sawdust particles catching light, indigo-blue painter apron on hook background out of focus, no other people, no text, documentary craftsmanship aesthetic, warm amber with cool blue accent --ar 4:5 --style raw --s 240 --v 6`

---

## 8. About hero · About workshop "Painting"

### 8a. `about-hero-workshop.jpg`  ·  Aspect 16:9
- **Filename usado en**: `about_page.xml:10`
- **Reemplaza**: `unsplash.com/photo-1581094288338` (uso #1)

> Wide cinematic photograph of the Indigo Decors workshop interior in Miami, several decorative iron-and-glass doors in various stages of completion arranged across the polished concrete floor, large industrial windows letting in soft afternoon Florida light, dust particles catching the light shafts, no people visible, no text, no signage. Documentary feel, depth and atmosphere, premium artisan workshop aesthetic. Left half of frame is the brightest area (negative space for overlay headline).

> `wide cinematic photo, Indigo Decors workshop interior Miami, several decorative iron-and-glass doors in various stages of completion across polished concrete floor, large industrial windows soft afternoon Florida light, dust particles catching light shafts, no people, no text, no signage, documentary feel, depth and atmosphere, premium artisan workshop aesthetic, left half brightest for overlay copy --ar 16:9 --style raw --s 240 --v 6`

### 8b. `workshop-painting.jpg`  ·  Aspect 3:4
- **Filename usado en**: `about_page.xml:139` ("Painting" mosaic tile)
- **Reemplaza**: `unsplash.com/photo-1581094288338` (uso #2)

> Tall close-up photograph of a craftsman's brush applying matte black paint to the iron grille of a decorative door, brush mid-stroke, paint texture visible, sharp focus on the brush and a small section of grille, rest of door blurred out of focus. Warm shop lighting from above. No face, only the brush and hand. No text. Documentary craftsmanship aesthetic.

> `tall close-up photo, craftsman brush applying matte black paint to iron grille of decorative door, brush mid-stroke, paint texture visible, sharp focus on brush and small grille section rest blurred, warm shop lighting from above, no face only brush and hand, no text, documentary craftsmanship aesthetic --ar 3:4 --style raw --s 240 --v 6`

---

## 9. About workshop mosaic — additional tiles

### 9a. `workshop-wide-floor.jpg`  ·  Aspect 16:9
- **Filename usado en**: `about_page.xml:133` ("Workshop" tile)
- **Reemplaza**: `unsplash.com/photo-1572019354566`

> Wide elevated angle photograph looking down at the Indigo workshop floor, six or seven decorative doors laid out on padded sawhorses in different stages (sanding, painting, glass installation), polished concrete floor, racks of iron grilles in soft focus on far walls, large fans hanging from ceiling, warm afternoon Florida light from skylights, no people visible, no text. Industrial-artisan aesthetic.

> `wide elevated angle photo, Indigo workshop floor from above, six or seven decorative doors on padded sawhorses different stages sanding painting glass installation, polished concrete floor, racks of iron grilles soft focus far walls, large ceiling fans, warm afternoon Florida light from skylights, no people, no text, industrial-artisan aesthetic --ar 16:9 --style raw --s 240 --v 6`

### 9b. `workshop-cnc-cutting.jpg`  ·  Aspect 3:4
- **Filename usado en**: `about_page.xml:136` ("Cutting" tile)
- **Reemplaza**: `unsplash.com/photo-1605000797499`

> Tall close-up photograph of a CNC router precision-cutting a geometric pattern into a flat iron door panel, sparks and metal shavings flying in slow-motion freeze, industrial blue-grey machine in soft focus background, warm spotlights on the work surface. No people, no text. Documentary precision-craft aesthetic, color grading: cool industrial blue with warm sparks.

> `tall close-up photo, CNC router precision-cutting geometric pattern into flat iron door panel, sparks and metal shavings flying frozen mid-air, industrial blue-grey machine soft focus background, warm spotlights on work surface, no people, no text, documentary precision-craft aesthetic, cool industrial blue with warm sparks --ar 3:4 --style raw --s 240 --v 6`

### 9c. `workshop-qc-detail.jpg`  ·  Aspect 1:1
- **Filename usado en**: `about_page.xml:142` ("QC" tile)
- **Reemplaza**: `unsplash.com/photo-1581092335397`

> Square close-up photograph of gloved hands using a stainless-steel digital caliper to measure the gap of a decorative iron door panel's grille, sharp focus on the caliper LCD reading and the grille edge, rest of door softly blurred, warm overhead shop light, no faces or other body parts, no text. Premium quality-control documentary aesthetic, color grading: cool metallic with warm shop accents.

> `square close-up photo, gloved hands stainless-steel digital caliper measuring gap of decorative iron door panel grille, sharp focus on caliper LCD reading and grille edge, rest of door softly blurred, warm overhead shop light, no faces or other body parts, no text, premium quality-control documentary aesthetic, cool metallic with warm shop accents --ar 1:1 --style raw --s 240 --v 6`

---

## Total: **14 imágenes nuevas a generar**

| Categoría | Cantidad |
|---|---|
| Heroes (home/gallery/about/dealer) | 4 |
| Category cards (single/double/sidelites/custom) | 4 |
| Lifestyle mosaic (installed/hallway/living/entrance) | 4 |
| Workshop close-ups (craftsman/painting/cnc/qc) | 4 |
| Showroom B2B | 1 |
| Workshop wide | 1 |
| **(Algunas comparten archivo → 14 únicas)** | — |

---

## Después de generar — cómo aplicarlas

1. Subir los `.jpg` a `addons/indigo_theme/static/src/img/photo/` con los
   filenames sugeridos.
2. Sed sobre los XML para reemplazar las URLs de Unsplash:
   ```bash
   # Ejemplo (ajustar URL/filename según mapping de arriba)
   sed -i 's|https://images.unsplash.com/photo-1600585154340[^"]*|/indigo_theme/static/src/img/photo/home-hero-miami-door.jpg|g' \
     addons/indigo_theme/data/pages/home_page.xml \
     addons/indigo_theme/data/pages/gallery_page.xml
   ```
3. Bump versión del módulo + CSS cache (`?v=39`).
4. `git commit`, push, deploy Coolify, `-u indigo_theme` para que las
   referencias en views recarguen.

---

## Recomendación práctica

Si vas a usar **Imagen 3** o **ChatGPT** (DALL·E 3), tirá los **prompts
universales** directo. Si usás **Midjourney**, usá la versión con flags. Si la
primera generación sale demasiado "stock", agregá:

- `--style raw` (ya está, fuerza menos estilización)
- `--s 50` o `--s 150` (menos stylize = más realista)
- `--no people, no text, no logos, no watermark` (negative prompt)
- `--seed <numero>` (para regenerar variaciones consistentes)

Para coherencia entre todas las imágenes del lote, **usar el mismo seed**
una vez encontrado uno que funcione, y solo cambiar el `--ar` y la sección
descriptiva del subject.
