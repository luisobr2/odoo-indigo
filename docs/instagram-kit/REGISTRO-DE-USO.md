# Regla: no repetir puertas entre publicaciones

**Decidido por el cliente el 2026-09-14.** Una puerta que ya salió en una
publicación **no vuelve a salir** en la siguiente. Hay material de sobra: 16
fotos reales de instalación, 9 puertas de catálogo, 4 fotos de taller y los
clips de Veo.

Publicar siempre las mismas hace que la cuenta parezca tener tres puertas
en vez de un catálogo.

## Por qué esta tabla y no solo la regla

Una regla de «no repetir» **no se puede cumplir sin un registro**: nadie
recuerda dentro de un mes qué puerta salió en qué post. Esta tabla es lo que
hace la regla aplicable.

**Al publicar algo, añadir la fila.** Es el único paso obligatorio.

---

## Fotos reales de instalación

| # | Qué es | Usada en | Libre |
|---|---|---|---|
| 01 | DD blanca geométrica, fachada | — | ⚠️ pendiente de que Majela confirme si es diseño de Indigo |
| 02 | DD negra geométrica, interior | **reel `dealers` (22-sep)** | extendida a 9:16 y ampliada con Higgsfield, animada |
| 03 | SD negra líneas, interior | — | ⚠️ pendiente de Majela |
| 04 | DD negra sidelites | — | ❌ descartada (vidrio transparente, sin ornamento) |
| 05 | DD clara retícula | — | ❌ descartada (sin ornamento, sale el teclado de la alarma) |
| 06 | SD blanca geométrica, interior | **reel `dealers` (22-sep)** | ampliada con Higgsfield, animada |
| 07 | SD negra óvalo, fachada | **reel `dealers` (22-sep)** | ampliada con Higgsfield, animada |
| 08 | DD negra círculos, fachada | **vídeo `taller` (14-sep)** | usar `_limpias/` |
| 09 | DD clara geométrica, porche | **vídeo `taller` (14-sep)** | — |
| 10 | DD negra volutas, fachada | **vídeo `taller` (v1-v3, 14-sep)** | — |
| 11 | SD blanca flores, casa turquesa | **vídeo `taller` (v1-v3, 14-sep)** | — |
| 12 | SD negra volutas, taller | — | ✅ solo como PROCESO (lleva film protector) |
| 13 | DD blanca líneas, fachada | — | ⚠️ pendiente de Majela |
| 14 | SD negra flores, interior | **carrusel `estilos` (16-sep)** | ya animada (`resultado-interior.mp4`) |
| 15 | SD oscura, panel con ranura, fachada | **carrusel `estilos` (16-sep)** | nueva (WhatsApp 14-sep) |
| 16 | DD negra óvalos, montante a juego, fachada | **carrusel `estilos` (16-sep)** | nueva (WhatsApp 14-sep) |

⚠️ **Todas las de instalación siguen esperando el permiso del dealer.**

## Fotos del taller

| Archivo | Usada en | Libre |
|---|---|---|
| 20 CNC cortando | vídeo `taller`, carrusel `custom` | reutilizable, es la firma del taller |
| 21 acabado a mano | vídeo `taller`, carrusel `custom` | reutilizable |
| 22 montaje | — | ✅ (floja: no se ve ornamento) |
| 23 equipo oficina | — | ❌ sale el logo de otra empresa en un polo |

## Puertas de catálogo (`puertas/`)

| Usada en | Cuáles |
|---|---|
| Carrusel `acabados` y `anatomia` | ID13-SD |
| Carrusel `custom` | ID01-SD, ID02-DD, ID06-SD, ID08-SD, ID13-SD, ID19-DD, ID21-SD, ID26-SD, ID38-DD |
| Carrusel `estilos` (16-sep) | ID33, ID40, ID42 · ID43, ID44, ID52 · ID45, ID54, ID55 · ID32, ID49, ID53 · ID39, ID58, ID60 (todas SD) |
| Reel `dealers` (22-sep), muro del catálogo | ID31, 34, 36, 41, 46, 47, 48, 50, 51, 56, 57, 59, 61, 62, 63, 64 (SD) |
| Reel `dealers` (22-sep), tomas de estudio | ID36-DD (apertura), ID57-SD (detalle), ID41-SD (cierre), sobre fondo oscuro (`hero-puerta.py`, 4k) |
| Reel `entrada` (22-sep), tomas de estudio | ID46-DD negra (apertura), ID51-DD bronce (detalle), ID34-DD bronce (cierre) |
| Reel `entrada` (22-sep), muro de dobles | ID31, 47, 48, 50, 59, 61, 62, 63, 64, 41, 36, 57 (DD) |
| Reel `privacidad` (22-sep), casas generadas | ID47-SD bronce (recibidor de día), ID56-SD negra (fachada de noche) — `puerta-en-escena.py` |
| Carrusel `casas` (22-sep), fachadas generadas | ID68-SD negra (Art Deco), ID37-SD bronce (mediterránea), ID67-SD negra (moderna), ID70-SD bronce (Key West), ID93-SD bronce (mid-century) — `puerta-en-escena.py --caja` |

**Hay renders de sobra.** Antes este registro decía que solo 9 diseños tenían
render y que ese era el cuello de botella. No era cierto: el portafolio público
de la web está descargado en `scraping/output/variant_images/`, **142 diseños,
cada uno en negro, blanco y bronce**. Son imágenes de catálogo propias, así que
no esperan el permiso del dealer.

Los de **ID31 en adelante** salen todos de la misma plantilla: fondo blanco puro
y la puerta siempre en la caja (302,60,723,961). Se componen sin recortar, y
tres puertas distintas quedan alineadas al píxel. Los anteriores a ID31 tienen
otro encuadre (más pequeños, con suelo gris): no mezclarlos en la misma slide.

## Clips de Veo ya generados

| Clip | De qué foto | Usado en |
|---|---|---|
| `resultado-negra` | 10 | vídeo `taller` v1-v3 — **retirado el 14-sep** |
| `resultado-turquesa` | 11 | vídeo `taller` v1-v3 — **retirado el 14-sep** |
| `resultado-interior` | 14 | — libre |
| `resultado-porche-claro` | 09 | **retirado el 15-sep** — recortaba la foto |
| `resultado-circulos-claro` | 08 | **retirado el 15-sep** — recortaba la foto |
| `acabado-limpio` | 21 | vídeo `taller`, `intro` |
| `instalada-ovalo-hf-claro` | 07 | reel `dealers` — seedance 1080p, gamma 1,18 (luz 96 → 109) |
| `instalada-doble-hf` | 02 | reel `dealers` — seedance 1080p |
| `instalada-blanca-hf` | 06 | reel `dealers` — seedance 1080p |
| `entrada-id46dd-luz-v3` | render ID46-DD | reel `entrada` — seedance sobre el hero 4k; reencuadrado ×1,45 desde 1,5 s porque salía pequeña |
| `entrada-id34dd-luz-v3` | render ID34-DD | reel `entrada` — seedance, reencuadrado ×1,25 |
| `priv-interior-luz` | ID47 en recibidor IA | reel `privacidad` — seedance, solo cambia la luz del suelo |
| `priv-exterior-noche` | ID56 en fachada IA | reel `privacidad` — seedance, palmeras y luz cálida |

---

## Una foto cuadrada NO se recorta a 9:16

Las fotos de instalación son **1600 × 1600**, y las originales de la carpeta
del cliente también: no existe una versión más ancha. Un recorte a 9:16
conserva solo el **56 % del ancho**, y eso no quita «un poco de margen»: en la
del porche se llevaba el árbol de la izquierda entero y media pared, que es
justo lo que hacía buena la foto. El cliente lo vio a la primera.

**En vez de quitar ancho, se añade alto.** La foto va a ancho completo sobre
un lienzo 1080 × 1920 y las zonas nuevas se rellenan estirando una franja
fina del propio borde (24 px), desenfocada y algo más oscura. Continúa solo
la textura real —pared arriba, suelo abajo— sin duplicar nada reconocible.

Se probaron antes dos rellenos que **no** sirven:

| Relleno | Por qué no |
|---|---|
| La imagen entera desenfocada de fondo | Queda turbia y se reconoce la puerta repetida |
| Espejo de una banda gruesa del borde | Copia parte de la puerta: fantasma visible |

Estas dos escenas quedan como **foto con empuje de cámara**, no como clip de
Veo. Los créditos de Gemini están agotados (`429 RESOURCE_EXHAUSTED`), así que
ni se pueden extender las fotos con Nano Banana ni volver a animarlas.

## La píldora de la web se solapaba con el subtítulo

En la escena final coincidían el botón `indigodecors.com` y el subtítulo, que
además decía exactamente lo mismo. La plantilla anclaba el botón a 300 y la
barra de subtítulos ocupa hasta 260, así que se rozaban. Subido a 430.

## Al elegir la puerta siguiente: MIDE EL BRILLO

Las dos primeras que se eligieron para rotar (09 y 08) resultaron ser mucho
más oscuras que el resto del vídeo: los clips de taller van a **135-147** de
luminancia media y esas dos a **81 y 86**. En el montaje el vídeo caía en
picado al llegar a ellas y el ornamento no se leía.

Se arregló con `eq=gamma=1.55` — **gamma, no brillo**: sube medios y sombras
dejando el negro del ornamento donde está. Un aumento plano de brillo lo
grisea y el patrón pierde justo el contraste que lo hace legible.

**Comprobar antes de montar:**

```bash
ffmpeg -v error -i <clip>.mp4   -vf "signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-" -f null -
```

Si la media baja de ~100, hay que aclararla o elegir otra foto.

## Cómo aplicarla sin rehacer el vídeo entero

Las escenas del vídeo referencian el clip por nombre, así que **cambiar de
puerta es cambiar una línea** en `projects/indigo/campaigns.ts` y volver a
renderizar. No hace falta tocar la voz ni la música: la narración no nombra
ninguna puerta en concreto, a propósito.

Ese fue justo el motivo de escribir los textos sin mencionar color ni diseño.
