# Regla: no repetir puertas entre publicaciones

**Decidido por el cliente el 2026-09-14.** Una puerta que ya salió en una
publicación **no vuelve a salir** en la siguiente. Hay material de sobra: 14
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
| 02 | DD negra geométrica, interior | — | ✅ |
| 03 | SD negra líneas, interior | — | ⚠️ pendiente de Majela |
| 04 | DD negra sidelites | — | ❌ descartada (vidrio transparente, sin ornamento) |
| 05 | DD clara retícula | — | ❌ descartada (sin ornamento, sale el teclado de la alarma) |
| 06 | SD blanca geométrica, interior | — | ✅ (usar el recorte de `_limpias/`) |
| 07 | SD negra óvalo, fachada | — | ✅ (ya recortada 9:16) |
| 08 | DD negra círculos, fachada | **vídeo `taller` (14-sep)** | usar `_limpias/` |
| 09 | DD clara geométrica, porche | **vídeo `taller` (14-sep)** | — |
| 10 | DD negra volutas, fachada | **vídeo `taller` (v1-v3, 14-sep)** | — |
| 11 | SD blanca flores, casa turquesa | **vídeo `taller` (v1-v3, 14-sep)** | — |
| 12 | SD negra volutas, taller | — | ✅ solo como PROCESO (lleva film protector) |
| 13 | DD blanca líneas, fachada | — | ⚠️ pendiente de Majela |
| 14 | SD negra flores, interior | — | ✅ **ya animada** (`resultado-interior.mp4`) |

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
| Carrusel `acabados` | el diseño de las tres variantes de color |
| Carrusel `custom` | las 9 en rejilla |

Hay **163 diseños en el catálogo** y solo 9 tienen render. Si hace falta
variedad, el cuello de botella son los renders, no los diseños.

## Clips de Veo ya generados

| Clip | De qué foto | Usado en |
|---|---|---|
| `resultado-negra` | 10 | vídeo `taller` v1-v3 — **retirado el 14-sep** |
| `resultado-turquesa` | 11 | vídeo `taller` v1-v3 — **retirado el 14-sep** |
| `resultado-interior` | 14 | — libre |
| `resultado-porche-claro` | 09 | **retirado el 15-sep** — recortaba la foto |
| `resultado-circulos-claro` | 08 | **retirado el 15-sep** — recortaba la foto |
| `acabado-limpio` | 21 | vídeo `taller`, `intro` |

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
