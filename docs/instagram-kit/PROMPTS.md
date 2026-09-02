# Prompts para generar la multimedia de Instagram — Indigo Decors

> **Antes de usar esto:** pegá primero `CONTEXTO-MARCA.md` en el chat del
> agente. Estos prompts asumen que ya conoce la marca, el producto y las
> reglas. Sin ese contexto van a salir puertas de madera con vidrio
> transparente.
>
> Los prompts están **en inglés a propósito** — todos los generadores
> responden mejor en inglés. El copy en español va superpuesto después.
>
> **Ninguno pide texto dentro de la imagen.** Donde hace falta lugar para
> copy, se pide espacio negativo.
>
> **Los hex de estos prompts son los verificados** (ver §2 y §3 del contexto):
> `#1f4486` azul de marca, `#0e1f3c` navy derivado de ese mismo azul,
> `#0048B4` azul del arco del logo, `#b5895a` bronce real del producto y
> `#f3f1ea` blanco real del acabado. No se usa ningún color del brief que no
> esté confirmado en el material de la empresa.

---

## Cómo está organizado

| Bloque | Para qué | Piezas |
|---|---|---|
| A | Identidad del perfil | 2 |
| B | Los 9 primeros posts (la grilla inicial) | 9 |
| C | Portadas de historias destacadas | 5 |
| D | Plantillas reutilizables | 3 |

Total: **19 imágenes** para abrir la cuenta con una grilla completa.

---

## Bloque A — Identidad del perfil

### A1. Foto de perfil — NO SE GENERA

> **Se intentó y se descartó.** El prompt pedía un arco de acuarela "curvado
> como una sonrisa", y el arco real de la marca va **al revés**: se arquea
> hacia arriba, como una ola, con una cola de pinceladas finas bajando por la
> derecha. Lo generado no era el logo con otro color — era otro dibujo, y
> encima sin el wordmark.
>
> Iba a ir de foto de perfil en las tres cuentas, o sea el sitio más visible
> de la marca.
>
> **Usar `marca/avatar-navy.png`** (fondo oscuro) o `marca/avatar-claro.png`.
> Son cuadrados de 1024×1024 hechos del logo real, con el arco y el wordmark
> completos. La regla de marca ya lo decía: si hace falta un ícono suelto, se
> usa el arco **del logo**, no uno nuevo.

### A2. Banner / imagen de fondo para posts de cita (1080×1350)

```
Vertical background for a social media quote card. Deep navy (#0e1f3c) to
indigo (#1f4486) diagonal gradient. A very subtle large watercolour texture
in a slightly lighter blue bleeds in from the top-right corner, low opacity,
like ink on wet paper. A single thin bronze (#b5895a) hairline runs
horizontally across the lower third. The centre of the frame is deliberately
empty and clean, reserved for text added later. No text, no letters, no
logos. Elegant, restrained, premium. 4:5.
```

---

## Bloque B — Los 9 primeros posts

Pensados como **grilla**: vistos juntos alternan producto, detalle y taller,
que es lo que hace que un perfil nuevo se vea cuidado.

### B1. Héroe — puerta doble blanca en fachada de Miami (1080×1350)

```
Photorealistic architectural photograph of a residential entrance in South
Florida. A double entry door, both leaves symmetrical, finished in warm
off-white (#f3f1ea). Each leaf holds one large panel of frosted privacy glass, and over
that glass sits an ornamental scrollwork design in raised relief, the same
off-white as the door — flowing spirals and curves, like forged ironwork but
applied flat onto the glass. Slim brushed-nickel lever handles meeting at the
centre. The house is light stucco with a tile roof; a palm frond enters from
the upper left. Late afternoon Florida sun, warm directional light, soft
shadows, blue sky. Shot straight on, slight low angle, 35mm, shallow depth of
field on the background. No text, no watermarks. 4:5.
```

### B2. Detalle macro del ornamento (1080×1080)

```
Extreme close-up, photorealistic. The corner where an ornamental relief
scroll meets frosted privacy glass on a decorative entry door. The scrollwork
is dark bronze (#b5895a shading to #7d5a34) — a deep metallic brown, not
gold, not copper — with a matte
finish and a crisp machined edge. Behind it the glass is silvery, translucent,
softly textured, letting diffuse light through without revealing anything
beyond. Raking side light picks out the thickness of the relief and casts a
thin shadow onto the glass. Fills the frame. Tack sharp. Shallow depth of
field. No text. 1:1.
```

### B3. Antes / después conceptual (1080×1350)

```
Photorealistic split composition, one vertical door filling the frame,
divided exactly down the middle. The left half is a plain, undecorated entry
door: flat dark bronze frame, plain frosted glass panel, completely bare and
ordinary. The right half is the same door transformed: the same bronze, the
same glass, but now carrying an elaborate ornamental relief design of
interlacing curves and spirals. The seam between halves is clean and
invisible — it reads as one door, half finished. Neutral studio background,
soft even light from the front, gentle shadow beneath. No text, no arrows, no
labels. 4:5.
```

### B4. La máquina CNC cortando (1080×1080)

```
Photorealistic workshop photograph. A CNC router head mid-cut, tracing a
curved ornamental pattern into a flat panel. Fine dust rises in the beam of a
work lamp. The cut edge is crisp and clean. Industrial but tidy: you can see
the machine bed, the clamps, the traced curve emerging. Cool machine light
mixed with a warm lamp, high contrast, dramatic. Close, slightly above the
cutting head, 50mm. Nobody in frame. Gritty and real, not a stock-photo
factory. No text. 1:1.
```

### B5. Puerta simple negra, plano frontal de catálogo (1080×1350)

```
Photorealistic product photograph of a single entry door, shot perfectly
straight on and centred, on a seamless white studio background with a soft
gradient shadow underneath. The door is deep matte black (#1a1a1a) with a subtle
fibreglass grain. One large frosted privacy glass panel fills most of the
leaf; over it, an ornamental relief design in the same black — long vertical
lines that bow outward and cross in interlacing arcs toward the centre.
Slim brushed-nickel lever handle and cylinder lock on the left. Visible
hinges on the right edge. Even, soft, shadowless product lighting. The door
occupies the central 70% of the frame with clean empty space above and below.
No text. 4:5.
```

### B6. Las manos del pintor (1080×1080)

```
Photorealistic close-up of a craftsman's hands in nitrile gloves holding a
spray gun, applying an even coat of dark bronze finish to a door panel laid
flat. Fine atomised mist catches the light. The surface already coated is
flawless and satin. Shallow depth of field: hands and nozzle sharp, the
workshop behind soft. Warm practical lighting. Only hands and forearms — no
face. Honest craft photograph, not a stock model. No text. 1:1.
```

### B7. Instalación en obra (1080×1350)

```
Photorealistic documentary photograph of two installers fitting a decorated
double entry door into the opening of a South Florida home. Seen from
outside, slightly wide. The door is warm off-white with ornamental relief
scrollwork over frosted glass. One installer steadies the leaf, the other
works at the hinge side. Everyday work clothes, tools on the ground. Bright
midday Florida light, strong shadows, stucco wall, a hint of palm. Real and
unposed, faces turned away or out of frame. No text, no visible brand logos
on clothing. 4:5.
```

### B8. Tres acabados lado a lado (1080×1080)

```
Photorealistic studio composition: three identical single entry doors
standing side by side against a seamless light grey background, evenly
spaced, all shot straight on. They carry the same ornamental relief design
over frosted privacy glass, but in three finishes — deep metallic bronze brown (#b5895a shading to
#7d5a34) on the left, warm off-white (#f3f1ea) in the centre, matte black
(#1a1a1a) on the right. Even soft
lighting across all three, consistent shadows on the floor. Perfectly aligned
and symmetrical. No text, no labels. 1:1.
```

### B9. Detalle del vidrio a contraluz (1080×1350)

```
Photorealistic close-up of frosted privacy glass on a decorative entry door,
photographed from inside the house looking out. Daylight floods through the
textured glass, turning it into a luminous silver sheet. The ornamental
relief on the outside reads as a crisp dark silhouette against that glow —
elegant interlacing curves. Warm interior shadow at the frame edges. Serene,
minimal, high contrast between the bright glass and the dark ornament.
Vertical, filling the frame. No text. 4:5.
```

---

## Bloque C — Portadas de historias destacadas

Cinco portadas que tienen que verse **como un juego**. Generá las cinco en la
misma tanda para que la iluminación coincida.

Prompt base (reemplazá `[ÍCONO]` por cada línea de la tabla):

```
Minimal icon illustration for a social media story highlight cover. Perfectly
square, centred composition. Deep navy (#0e1f3c) flat background. In the
centre, [ÍCONO] drawn as a clean line icon in bright indigo (#0048B4), with
one single accent detail in bronze (#b5895a). Thin, even stroke weight,
geometric, no fills, no gradients, no shadows. Generous empty margin around
the icon. Flat vector style. No text, no letters. 1:1.
```

| Destacada | `[ÍCONO]` |
|---|---|
| Catálogo | `a simple front door seen straight on, with a decorative swirl on its glass panel` |
| Proceso | `a CNC router head above a flat panel, cutting a curved line` |
| Instalaciones | `a house facade reduced to its simplest outline, with the door highlighted` |
| Acabados | `three small paint swatch squares overlapping in a row` |
| Dealers | `a handshake reduced to two simple interlocking shapes` |

---

## Bloque D — Plantillas reutilizables

### D1. Fondo para post de producto (1080×1350)

```
Empty vertical background for a product post. Soft gradient from very light
warm grey at the top to pure white at the bottom, with a barely visible
elliptical shadow across the lower third where a product will be placed. In
the top-right corner, a very faint large watercolour arc in pale indigo, low
opacity, like a watermark. Nothing else. Completely clean and empty in the
centre. No text, no objects. 4:5.
```

### D2. Fondo para carrusel educativo (1080×1080)

```
Empty square background for an educational carousel slide. Flat warm off-white
(#f3f1ea) with a subtle paper grain texture. A single thin bronze (#b5895a)
rule runs across the bottom eighth of the frame. Top-left corner carries a
small faint indigo watercolour smudge at very low opacity. The whole centre is
empty and clean, reserved for text and diagrams added later. Nothing else. No
text. 1:1.
```

### D3. Portada de reel (1080×1920)

```
Vertical cinematic background for a short-form video cover. Deep navy to
indigo vertical gradient. A decorative entry door with ornamental relief over
frosted glass stands in the lower two thirds, dramatically side-lit from the
right, mostly in shadow with a strong rim of light along its edge and across
the ornament. The top third fades into near-black empty space for a headline
added later. Moody, cinematic, high contrast. Vertical. No text. 9:16.
```

---

## Notas de uso

**Referencia de imagen.** Si el generador la acepta (Midjourney `--cref`,
Firefly, Nano Banana), pasale `puertas/ID13-SD.png` para el ornamento oscuro
o `puertas/ID02-DD.png` para la puerta doble blanca. Es mucho más fiable que
describir un ornamento con palabras.

**Si sale mal, casi siempre es una de estas cuatro:**

| Problema | Qué agregar al prompt |
|---|---|
| Salió de madera | `fiberglass door, solid painted finish, no wood grain` |
| Se ve el interior | `opaque frosted privacy glass, cannot see through` |
| Ornamento de colores | `the ornament is the same colour as the door frame` |
| Parece una reja | `the design is applied flat onto the glass surface, not a separate security gate` |

**Consistencia de la tanda.** Si generás varias piezas en sesiones distintas
van a salir con luces distintas. Generá cada bloque completo de una sentada.

**Lo que este kit no puede darte.** No hay fotos reales de obra, del taller ni
del equipo. Los prompts B4, B6 y B7 las **generan**, y una imagen generada de
tu propio taller es honesta como ilustración pero **no** para decir "este es
nuestro equipo". Esas tres valen más tomadas con un teléfono en el taller real
que generadas — y son, de lejos, el mejor contenido que Indigo podría publicar.
