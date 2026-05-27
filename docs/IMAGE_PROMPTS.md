# Indigo Decors — Image generation prompts

5 imágenes para reemplazar los Unsplash placeholders más visibles del home
(above-the-fold: hero + 4 category cards). Cuando estén estas, el sitio ya se
ve "real". El resto de Unsplash (heroes internos + mosaicos del about) queda
para una segunda iteración.

**Estrategia anti bait-and-switch**: las category cards usan **fotos reales del
catálogo** ya descargadas (sin invención). El hero del home usa AI pero la
puerta aparece como **silueta backlit** — sin grille en foco, sin riesgo de
prometer un diseño que no existe.

---

## 1. Single doors — category card (foto del catálogo)

- **Filename destino**: `cat-single-door.jpg`
- **Aspect ratio**: 1:1 (1024×1024 px)
- **Usado en**: `home_page.xml:50`, `gallery_page.xml:59`
- **Fuente**: `scraping/output/variant_images/ID01-SD/black.jpg`
  (alternativas: ID03-SD, ID09-SD, ID20-SD — elegir el más impactante)

```bash
magick scraping/output/variant_images/ID01-SD/black.jpg \
  -resize 1024x1024^ -gravity center -crop 1024x1024+0+0 \
  addons/indigo_theme/static/src/img/photo/cat-single-door.jpg
```

---

## 2. Double doors — category card (foto del catálogo)

- **Filename destino**: `cat-double-door.jpg`
- **Aspect ratio**: 1:1 (1024×1024 px)
- **Usado en**: `home_page.xml:59`, `gallery_page.xml:72`, `home_page.xml:102`
- **Fuente**: `scraping/output/variant_images/ID01-DD/bronze.jpg`
  (alternativas: ID05-DD/bronze, ID20-DD/black)

```bash
magick scraping/output/variant_images/ID01-DD/bronze.jpg \
  -resize 1024x1024^ -gravity center -crop 1024x1024+0+0 \
  addons/indigo_theme/static/src/img/photo/cat-double-door.jpg
```

---

## 3. Sidelites — category card (pedir foto al cliente)

- **Filename destino**: `cat-sidelites.jpg`
- **Aspect ratio**: 1:1 (1024×1024 px)
- **Usado en**: `home_page.xml:68`, `gallery_page.xml:83`
- **Acción**: no hay un SKU "Sidelite" puro en el scrape. Pedirle al cliente 1
  foto real de un install con sidelites. Si no hay nada inmediato, dejar la
  imagen Unsplash hasta que llegue — es 1 sola card.

---

## 4. Custom — category card (foto del catálogo)

- **Filename destino**: `cat-custom.jpg`
- **Aspect ratio**: 1:1 (1024×1024 px)
- **Usado en**: `home_page.xml:77`, `gallery_page.xml:94`
- **Fuente**: `scraping/output/variant_images/CUSTOM-DD/black.jpg`

```bash
magick scraping/output/variant_images/CUSTOM-DD/black.jpg \
  -resize 1024x1024^ -gravity center -crop 1024x1024+0+0 \
  addons/indigo_theme/static/src/img/photo/cat-custom.jpg
```

---

## 5. Home hero · Gallery hero (prompt AI)

- **Filename destino**: `home-hero-miami-door.jpg`
- **Aspect ratio**: 16:9 (2400×1350 px)
- **Usado en**: `home_page.xml:10`, `gallery_page.xml:10`, `home_page.xml:99`
- **Acción**: pegar este prompt en Imagen 3 / ChatGPT / Flux. La puerta sale
  backlit como silueta — no se ve grille — así no compromete con un patrón
  inventado.

```
Editorial architectural photograph of a high-end Miami modern home entrance at golden hour. The front door is fully BACKLIT from inside the house, appearing as a clean dark silhouette inside a rectangular doorway frame against a brightly-glowing white stucco interior wall behind it — only the outer rectangular shape of the door is visible, NO grille pattern, NO geometric detail. Wide-angle composition with the doorway positioned in the right third of the frame, leaving the left half as negative space (sunlit white stucco facade with a single palm leaf shadow) for headline overlay. Warm late-afternoon Florida sunlight rakes diagonally across the facade. Deep navy-blue sky above. No people, no cars, no signage, no text, no logos. Cinematic depth, premium real-estate publication aesthetic, shot on Sony A7R V with 24mm lens at f/4, ultra-sharp facade, ISO 100, color-graded warm with subtle indigo-blue shadow tones.
```

---

## Aplicar al sitio

Crear la carpeta destino si no existe, hacer los crops y reemplazar las URLs:

```bash
cd c:/Trabajo/odoo-indigo
mkdir -p addons/indigo_theme/static/src/img/photo

# 1, 2, 4 — crops del catálogo (correr los snippets magick de cada bloque)

# 5 — subir el .jpg generado por AI a:
# addons/indigo_theme/static/src/img/photo/home-hero-miami-door.jpg

# Reemplazar las URLs de Unsplash en los XMLs
declare -A MAP=(
  [cat-single-door.jpg]="photo-1558618666"
  [cat-double-door.jpg]="photo-1505691938895"
  [cat-custom.jpg]="photo-1571939228382"
  [home-hero-miami-door.jpg]="photo-1600585154340"
)
for filename in "${!MAP[@]}"; do
  slug="${MAP[$filename]}"
  sed -i "s|https://images.unsplash.com/${slug}[^\"\']*|/indigo_theme/static/src/img/photo/${filename}|g" \
    addons/indigo_theme/data/pages/*.xml
done

# Bump cache version del CSS (en addons/indigo_theme/views/layout/templates.xml: ?v=38 → ?v=39)
# Bump manifest (en addons/indigo_theme/__manifest__.py: '17.0.2.4.0' → '17.0.2.5.0')

git add -A && git commit -m "indigo_theme: replace Unsplash placeholders with real catalog photos + AI hero"
git push origin main

# Deploy via Coolify + upgrade módulo (ver indigo_prod_credentials.md en memory)
```

---

## Notas

- Para Sidelites (#3), cuando llegue la foto del cliente: mismo `magick` y
  agregar `[cat-sidelites.jpg]="photo-1517472292914"` al `MAP` del sed.
- Si más adelante querés reemplazar también los heroes de about/dealer-program
  y los mosaicos decorativos: ver versiones anteriores de este doc en git
  history (`git log -- docs/IMAGE_PROMPTS.md`) — están los 11 prompts faltantes.
