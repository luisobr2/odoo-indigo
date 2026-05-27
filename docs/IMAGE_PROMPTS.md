# Indigo Decors — Image generation prompts (v2)

> **Cambio de estrategia respecto a v1**: los prompts originales hacían que el
> modelo inventara patrones Art Deco que NO están en el catálogo real. Un
> dealer ve esas puertas en el hero y no las encuentra en `/shop` → expectativa
> falsa. Esta versión resuelve eso:
>
> - **Category cards** (Single / Double / Sidelites / Custom): usar **fotos
>   reales** del catálogo ya descargadas en `scraping/output/variant_images/`.
>   Sin prompts — sin invención.
> - **Heroes + Lifestyle + Workshop**: la puerta aparece como
>   **silueta, fuera-de-foco, backlight o parcialmente fuera de cuadro**. El
>   espectador siente "puerta hurricane-rated de Indigo" sin que el modelo
>   tenga que inventar un grille específico.

---

# 🚀 Quick start — por dónde empezar

Son 16 entries en este doc pero **no hace falta hacerlas todas**. Priorización
por impacto real:

## ⭐ Tier 1 — Sí o sí (5 imágenes · ~30 min de trabajo)

Las 5 que se ven en los primeros 3 segundos del home. Sin estas el sitio queda
en estado "stock photo". Con estas ya levanta visualmente.

| # | Sección del doc | Entry | Acción |
|---|---|---|---|
| 1 | A.1 | `cat-single-door.jpg` | Crop de catálogo (`magick` 1 línea) |
| 2 | A.2 | `cat-double-door.jpg` | Crop de catálogo (`magick` 1 línea) |
| 3 | A.3 | `cat-sidelites.jpg` | Pedir foto al cliente o saltar |
| 4 | A.4 | `cat-custom.jpg` | Crop de catálogo (`magick` 1 línea) |
| 5 | B.1 | `home-hero-miami-door.jpg` | Generar con AI (1 prompt) |

→ **1 prompt AI + 3 crops + 1 a pedir = 30 min**.

## 🟡 Tier 2 — Cuando entres a páginas internas (3 prompts AI)

Si el dealer entra a /page/dealer-program o /page/about (lo hacen los serios):

| # | Sección | Entry | Por qué |
|---|---|---|---|
| 6 | B.6 | `dealer-program-hero.jpg` | Hero de la página clave de B2B |
| 7 | B.8 | `about-hero-workshop.jpg` | About hero — credibilidad del taller |
| 8 | B.7 | `workshop-craftsman-side.jpg` | Aparece en home (sección dealer) + about |

→ **3 prompts AI más. Diferible hasta tener Tier 1 deployado**.

## 🟢 Tier 3 — Mosaicos decorativos (8 imágenes · baja prioridad)

Los lifestyle (B.2–B.5) y los workshop close-ups (B.9–B.12) van en bloques
chicos del home y about. En grid pequeño el placeholder Unsplash no es tan
notorio. Diferir hasta que el sitio tenga tráfico real y los demás tiers
estén deployados.

→ **8 prompts AI más. Hacer eventualmente, no urgente**.

---

## TL;DR

1. **Ahora**: 3 crops + 1 prompt AI (Tier 1) → deploy → ya cambió la primera impresión.
2. **Esta semana**: 3 prompts AI más (Tier 2) → páginas internas pulidas.
3. **Cuando haya tiempo**: 8 prompts AI más (Tier 3) → 100% libre de Unsplash.

---

## Reglas de marca (en todos los prompts)

Cada prompt ya las incluye:

- Florida natural light, sin flash, sin HDR.
- Sin personas mirando a cámara (solo manos / forearms / siluetas).
- **Nunca un grille decorativo en foco nítido** — siempre blurred, silhouette, partial-frame o backlit.
- Sin texto, sin logos, sin watermarks.
- Negative space para overlays donde aplica.

---

# PARTE A — Sin prompts (usar fotos reales del catálogo)

## A.1 Single doors — category card

- **Filename destino**: `cat-single-door.jpg`
- **Aspect ratio**: 1:1
- **Usado en**: `home_page.xml:50`, `gallery_page.xml:59`
- **Fuente**: copiar `scraping/output/variant_images/ID01-SD/black.jpg` (o el SKU favorito) y crop cuadrado.
- Alternativa: ID03-SD/black, ID09-SD/black, ID20-SD/black — elegí el que más impacto visual tenga.

## A.2 Double doors — category card

- **Filename destino**: `cat-double-door.jpg`
- **Aspect ratio**: 1:1
- **Usado en**: `home_page.xml:59`, `gallery_page.xml:72`, `home_page.xml:102`
- **Fuente**: `scraping/output/variant_images/ID01-DD/bronze.jpg` (o ID05-DD/bronze, ID20-DD/black).

## A.3 Sidelites — category card

- **Filename destino**: `cat-sidelites.jpg`
- **Aspect ratio**: 1:1
- **Usado en**: `home_page.xml:68`, `gallery_page.xml:83`
- **Fuente**: no hay un SKU "Sidelite" puro en el catálogo scrapeado. **Pedirle al cliente 1 foto** de un install con sidelites, o usar `lifestyle-entrance-wide.jpg` (B.4 más abajo) recortado cuadrado como fallback.

## A.4 Custom — category card

- **Filename destino**: `cat-custom.jpg`
- **Aspect ratio**: 1:1
- **Usado en**: `home_page.xml:77`, `gallery_page.xml:94`
- **Fuente**: usar `CUSTOM-DD/black.jpg` o `CUSTOM-SD/black.jpg` (ya están en el scrape). O alternativa de B.5 más abajo.

> 💡 Para crops cuadrados manuales: `magick input.jpg -gravity center -crop 1024x1024+0+0 cat-XYZ.jpg` (ImageMagick).

---

# PARTE B — Prompts (la puerta es contexto, no protagonista detallado)

## B.1 Home hero · Gallery hero

- **Filename**: `home-hero-miami-door.jpg`
- **Aspect ratio**: 16:9 (2400×1350 px)
- **Usado en**: `home_page.xml:10`, `gallery_page.xml:10`, `home_page.xml:99`

```
Editorial architectural photograph of a high-end Miami modern home entrance at golden hour. The front door is fully BACKLIT from inside the house, appearing as a clean dark silhouette inside a rectangular doorway frame against a brightly-glowing white stucco interior wall behind it — only the outer rectangular shape of the door is visible, NO grille pattern, NO geometric detail. Wide-angle composition with the doorway positioned in the right third of the frame, leaving the left half as negative space (sunlit white stucco facade with a single palm leaf shadow) for headline overlay. Warm late-afternoon Florida sunlight rakes diagonally across the facade. Deep navy-blue sky above. No people, no cars, no signage, no text, no logos. Cinematic depth, premium real-estate publication aesthetic, shot on Sony A7R V with 24mm lens at f/4, ultra-sharp facade, ISO 100, color-graded warm with subtle indigo-blue shadow tones.
```

---

## B.2 Lifestyle — "Installed in modern home"

- **Filename**: `lifestyle-installed-modern.jpg`
- **Aspect ratio**: 4:3 (1600×1200 px)
- **Usado en**: `home_page.xml:99` (mosaic position 1), `gallery_page.xml:48`

```
Wide editorial photograph of a modern Coral Gables Florida home at evening blue hour, viewed from the front porch. A front door at the home's entrance is fully closed, viewed straight-on at a slight low angle, but the door's surface is RENDERED IN COMPLETE SHADOW (only its rectangular outline and matte black finish are visible — NO grille pattern, NO geometric detail, NO glass insert visible). Warm interior light spills out from the sides of the doorframe (top and bottom gap) casting a thin glowing rectangle of light onto the polished porch tiles directly in front of the door. The deep blue twilight sky in the background contrasts with the warm interior glow leaking from the doorframe. Minimal contemporary architecture: clean white stucco walls, a single concrete planter with a small palm to one side, polished travertine flooring. No people, no cars, no text, no logos, no visible house number. Premium lifestyle real-estate publication aesthetic, cinematic depth.
```

---

## B.3 Lifestyle — "Hallway with interior door"

- **Filename**: `lifestyle-hallway-door.jpg`
- **Aspect ratio**: 3:4 portrait (900×1200 px)
- **Usado en**: `home_page.xml:108`, `gallery_page.xml:118`

```
Tall portrait editorial photograph of an upscale Miami home interior hallway shot from the entrance looking toward the end of the corridor. At the far end of the corridor a closed interior door is visible, but it is far enough away to appear small in the composition and slightly out of focus due to a shallow depth of field — its surface reads as a flat dark rectangle with no visible pattern or grille. Mid-morning natural sunlight streams sideways through a hidden side window, hitting the polished cream-colored marble floor that catches reflections of the off-white walls. A single curated indoor plant in a terracotta pot sits halfway down the corridor in sharp focus in the foreground. Off-white plaster walls on both sides. No people, no text, no logos. Editorial interior design magazine aesthetic, color grading: warm whites and creams, the door reads as a distant focal point not a detailed subject.
```

---

## B.4 Lifestyle — "Living room with door to terrace"

- **Filename**: `lifestyle-living-door.jpg`
- **Aspect ratio**: 3:2 (1800×1200 px)
- **Usado en**: `gallery_page.xml:131`

```
Editorial photograph of a Miami waterfront luxury home's living room with a double door opening onto a terrace. The two door panels are STANDING OPEN AT A WIDE ANGLE so we see them edge-on / in profile — only their thin matte bronze frames are visible as vertical slim bands at the left and right edges of the doorway, with NO frontal view of any grille pattern. The view through the open doorway dominates the frame: an ocean horizon in late afternoon golden Florida light. In the foreground, slightly out of focus, a white linen sofa with two indigo-blue throw cushions. On the polished travertine floor inside, a low brass coffee table with one stack of architecture books, no readable titles. No people, no text, no logos. Architectural Digest aesthetic, color grading: warm whites with deep indigo ocean tones, shallow depth of field on the foreground sofa.
```

---

## B.5 Lifestyle — "Entrance walkway"

- **Filename**: `lifestyle-entrance-wide.jpg`
- **Aspect ratio**: 3:2 (1800×1200 px)
- **Usado en**: `home_page.xml:102` (mosaic position 2), `gallery_page.xml:153`

```
Wide-angle exterior photograph of a luxury Floridian home entrance walkway, viewer's perspective walking toward the house. A flagstone path leads through lush tropical landscaping (mature royal palms, bird-of-paradise plants with orange flowers, low-mounded bromeliads) toward the home's front entrance. The front door is visible at the END of the walkway in the background, but it is SMALL in the frame and OUT OF FOCUS (shallow depth of field draws attention to the foreground tropical plants), reading as a dark rectangular shape inside its doorway — NO pattern or grille details visible. Midday Florida sun softened by light overcast creates even, flattering light across the entire scene. Clean white stucco facade behind the doorway. No people, no cars, no text, no logos, no signage, no visible house number, no mailbox. Composition pulls the eye down the path to the doorway as a focal vanishing point but the door itself remains undetailed. Premium real-estate lifestyle aesthetic.
```

---

## B.6 Dealer Program hero

- **Filename**: `dealer-program-hero.jpg`
- **Aspect ratio**: 16:9 (2400×1350 px)
- **Usado en**: `dealer_program_page.xml:11`

```
Wide editorial photograph of an Indigo Decors showroom interior in Miami, viewed at a slight three-quarter angle. Four large wooden door blanks (no decorative grilles installed yet — they are SOLID UNFINISHED DOORS in plain matte black, satin white, aged bronze and matte deep-navy finishes) are mounted vertically on a clean white display wall as finish samples, evenly spaced, each lit by a discreet overhead spotlight. The wall to the right of the display is painted a deep navy-blue accent. Polished concrete floor reflects the display subtly. In the foreground, a minimalist solid-oak bench with a single closed blank-cover brochure sitting on it. Soft daylight from skylights above creates an even premium gallery atmosphere. No people, no text, no logos, no signage, no watermarks. B2B premium catalog aesthetic. Composition leaves the left third as negative space (empty white wall) for headline overlay.
```

---

## B.7 Workshop — craftsman hands close-up

- **Filename**: `workshop-craftsman-side.jpg`
- **Aspect ratio**: 4:5 portrait (1200×1500 px)
- **Usado en**: `home_page.xml:195`, `about_page.xml:65`

```
Tall editorial documentary photograph of a craftsman's gloved hands (only the gloves and forearms are visible, never the face) carefully working with fine sandpaper on the surface of a heavy slab of unfinished wood / iron door blank laid flat on a wooden workbench. The focus is entirely on the sandpaper, the gloved hand and a small area of the door's matte surface — the door is shown in raw unfinished material, NO decorative grille, NO geometric pattern, just a solid flat panel being prepared. Warm tungsten shop lighting from above-side, fine sawdust and metal particles catch the light in the air. In the soft-focus background, an indigo-blue painter's apron hangs on a wall hook. No face, no other people, no text, no logos, no watermarks. Documentary craftsmanship aesthetic, color grading: warm amber dominant with a deliberate cool indigo-blue accent from the apron.
```

---

## B.8 About hero — workshop wide

- **Filename**: `about-hero-workshop.jpg`
- **Aspect ratio**: 16:9 (2400×1350 px)
- **Usado en**: `about_page.xml:10`

```
Wide cinematic photograph of an artisan metal-and-wood workshop interior in Miami at mid-afternoon. Long heavy wooden workbenches stretch across a polished concrete floor, with neat stacks of UNFINISHED FLAT IRON PANELS (plain rectangular sheets, no decorative cutouts visible — these are pre-fabrication blanks) and racks of hand tools (hammers, files, sandpaper rolls, brushes). Large industrial-style windows on the left wall let in soft Florida sunlight that creates visible light shafts cutting through fine airborne dust particles. The space feels open, organized and premium-artisan. The lighting is brightest on the left half of the frame (negative space for headline overlay) and naturally falls off toward the right. No people visible, no doors with patterns visible, no text, no logos, no signage. Documentary craftsmanship aesthetic with cinematic depth and atmosphere.
```

---

## B.9 Workshop — painting close-up

- **Filename**: `workshop-painting.jpg`
- **Aspect ratio**: 3:4 portrait (900×1200 px)
- **Usado en**: `about_page.xml:139` (mosaic "Painting" tile)

```
Tall close-up documentary photograph of a craftsman's hand holding a fine artist's brush, mid-stroke applying matte black paint to a FLAT PLAIN IRON SURFACE — the panel is undecorated and rectangular, no grille pattern, no geometric design. The brush bristles are slightly splayed against the metal showing the painting action in progress. The paint texture is clearly visible, glossy where wet, matte where it has just settled. Sharp focus on the brush tip and a small section of the panel, the rest of the panel is softly blurred. Warm overhead shop lighting from above. Only the hand and the brush are visible (no face, no arms beyond the wrist). No text, no logos, no watermarks. Documentary craftsmanship aesthetic, color grading: warm shop tones with deep matte black paint as the visual anchor.
```

---

## B.10 Workshop — wide elevated floor view

- **Filename**: `workshop-wide-floor.jpg`
- **Aspect ratio**: 16:9 (2400×1350 px)
- **Usado en**: `about_page.xml:133` (mosaic "Workshop" tile)

```
Wide elevated three-quarter angle photograph looking down at an artisan workshop floor in Miami. Several large heavy flat wooden boards and unfinished rectangular iron panels (no decorative cutouts, no patterns — these are raw pre-fabrication materials) are laid out neatly on padded sawhorses across a polished concrete floor. Tall racks of basic tools in soft focus along the far wall. Two large industrial ceiling fans hang above. Warm afternoon Florida sunlight enters from skylights above, creating soft diagonal light pools across the floor. The space is clearly organized, premium-artisan, not industrial-cold. No people visible, no finished doors with patterns, no text, no logos, no signage. Industrial-artisan aesthetic with depth and atmosphere, cinematic color grading.
```

---

## B.11 Workshop — CNC cutting close-up

- **Filename**: `workshop-cnc-cutting.jpg`
- **Aspect ratio**: 3:4 portrait (900×1200 px)
- **Usado en**: `about_page.xml:136` (mosaic "Cutting" tile)

```
Tall close-up documentary photograph of a CNC router head precision-cutting metal, viewed extremely close. Sharp blue-white sparks and bright metal shavings are flying outward in a frozen-mid-air burst, caught by high-speed photography. The router head and a tiny section of the metal surface being worked are the only sharp elements — what is being cut is intentionally ambiguous (could be the start of any panel, no recognizable pattern emerging yet). The industrial blue-grey CNC machine is partially visible and slightly out of focus in the background. Two warm focused spotlights illuminate the work surface from above, creating dramatic contrast against the cooler metallic surroundings. No people, no hands, no text, no logos, no watermarks. Documentary precision-craft aesthetic, color grading: cool industrial blue dominant with warm orange sparks as the visual accent.
```

---

## B.12 Workshop — QC caliper close-up

- **Filename**: `workshop-qc-detail.jpg`
- **Aspect ratio**: 1:1 (1200×1200 px)
- **Usado en**: `about_page.xml:142` (mosaic "QC" tile)

```
Square close-up documentary photograph of gloved hands using a stainless-steel digital caliper to precisely measure the edge thickness of an iron panel. The caliper's LCD reading is sharply legible (showing a generic measurement like 23.45 mm), and the panel edge being measured is in sharp focus, while the rest of the panel is softly blurred and visibly UNFINISHED / PLAIN (no decorative pattern, no grille, no holes — just a clean flat metal edge). Warm overhead shop light catches the polished steel of the caliper. Only the gloved hands and the caliper are visible (no face, no arms beyond the wrist). No text on the panel, no logos, no brand stickers, no watermarks. Premium quality-control documentary aesthetic, color grading: cool metallic dominant with warm shop accents reflecting off the steel.
```

---

# Total: 4 fotos reales (catálogo) + 12 prompts AI

Vs. la v1 que tenía 14 prompts AI, ahora:
- **4 fotos del scrape** ya descargadas → cero invención en las category cards
- **12 prompts AI** rediseñados → la puerta aparece pero **nunca con grille en foco**

---

## Después de generar / preparar — cómo aplicarlas

1. **Categorías** (A.1–A.4): copiar de `scraping/output/variant_images/...` y crop cuadrado:
   ```bash
   cd c:/Trabajo/odoo-indigo
   mkdir -p addons/indigo_theme/static/src/img/photo
   # Ajustá los SKU que prefieras
   magick scraping/output/variant_images/ID01-SD/black.jpg -resize 1024x1024^ -gravity center -crop 1024x1024+0+0 addons/indigo_theme/static/src/img/photo/cat-single-door.jpg
   magick scraping/output/variant_images/ID01-DD/bronze.jpg -resize 1024x1024^ -gravity center -crop 1024x1024+0+0 addons/indigo_theme/static/src/img/photo/cat-double-door.jpg
   magick scraping/output/variant_images/CUSTOM-DD/black.jpg -resize 1024x1024^ -gravity center -crop 1024x1024+0+0 addons/indigo_theme/static/src/img/photo/cat-custom.jpg
   # Sidelites: pedir al cliente o usar lifestyle-entrance-wide cropped
   ```

2. **Heroes / Lifestyle / Workshop** (B.1–B.12): generar con Imagen / ChatGPT / Flux, guardar en `addons/indigo_theme/static/src/img/photo/` con los filenames indicados.

3. Reemplazar las URLs de Unsplash en los XMLs:

```bash
cd c:/Trabajo/odoo-indigo
declare -A MAP=(
  [cat-single-door.jpg]="photo-1558618666"
  [cat-double-door.jpg]="photo-1505691938895"
  [cat-sidelites.jpg]="photo-1517472292914"
  [cat-custom.jpg]="photo-1571939228382"
  [home-hero-miami-door.jpg]="photo-1600585154340"
  [lifestyle-installed-modern.jpg]="photo-1582268611958"
  [lifestyle-hallway-door.jpg]="photo-1567016432779"
  [lifestyle-living-door.jpg]="photo-1600573472556"
  [lifestyle-entrance-wide.jpg]="photo-1554995207"
  [dealer-program-hero.jpg]="photo-1556909114"
  [workshop-craftsman-side.jpg]="photo-1556909114"
  [about-hero-workshop.jpg]="photo-1581094288338"
  [workshop-painting.jpg]="photo-1581094288338"
  [workshop-wide-floor.jpg]="photo-1572019354566"
  [workshop-cnc-cutting.jpg]="photo-1605000797499"
  [workshop-qc-detail.jpg]="photo-1581092335397"
)
for filename in "${!MAP[@]}"; do
  slug="${MAP[$filename]}"
  sed -i "s|https://images.unsplash.com/${slug}[^\"\']*|/indigo_theme/static/src/img/photo/${filename}|g" \
    addons/indigo_theme/data/pages/*.xml
done
```

4. Bump CSS cache (`?v=39`) + manifest a `17.0.2.5.0`. Commit, push, deploy Coolify, `-u indigo_theme`.

---

## ¿Por qué este cambio?

| Problema v1 | Solución v2 |
|---|---|
| Imagen inventa patrones Art Deco que no existen en el catálogo | Heroes/lifestyle: puertas en silueta / blur / backlight. Cards: foto real del catálogo |
| Dealer ve hero, va al shop, no encuentra esos diseños → desconfianza | Lo que muestra el hero ES lo que el shop entrega, o no se compromete con un diseño puntual |
| Inconsistencia de estilo entre 14 puertas AI generadas | Estilo único en heroes (luz + ambiente Miami), catálogo real en cards |
