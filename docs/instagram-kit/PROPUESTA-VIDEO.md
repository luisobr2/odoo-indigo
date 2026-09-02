# Indigo Decors — Propuesta de vídeo (primera vuelta)

**Fecha:** 2026-08-26 · **Estudio:** video-production (Remotion multi-proyecto)
**Base leída:** `CONTEXTO-MARCA.md`, `PROMPTS.md` + las 29 piezas de `generadas/`
mirada por mirada, `API-GPT-IMAGE-2.md`, y las 9 fotos reales de `puertas/`.

**Qué es este documento:** propuesta para decidir, no producción. Sin renders,
sin `projects/indigo/` todavía.

---

## A. Lectura crítica de lo que hay

Lo primero: el kit es mejor que la media de lo que circula como "contenido IA
para pymes", y la razón es una decisión técnica concreta — **las piezas de
producto se generaron con `edits` sobre la foto real de la puerta**, así que el
ornamento que se ve es el que Indigo vende. Eso se nota al comparar con
`puertas/ID13-SD.png` e `ID02-DD.png`. Pero no todas las piezas pasaron por ese
camino, y se nota igual de fuerte en la otra dirección.

### Las que aguantan (y aguantarían un frame de vídeo)

- **B1-fachada-doble** y **FB1-portada** — la doble blanca con los espirales de
  ID02 en fachada de Miami. Luz creíble, arquitectura correcta, ornamento
  fiel. Son el "hero" legítimo del kit.
- **B5-catalogo-negra**, **D3-portada-reel** — la ID13 real (arcos entrelazados),
  encuadre de catálogo limpio. D3 además ya está pensada como portada de reel:
  tercio superior vacío, rim light. Es prácticamente un frame de vídeo esperando
  su vídeo.
- **B4-cnc** y **FB4-taller** — las mejores piezas del kit, y no es casualidad:
  son las únicas con **movimiento implícito** (fresa, polvo, viruta). FB4 en
  particular ("gritty, not stock") clava el tono de taller.
- **B8/FB3-tres-acabados** y **B3/FB2-antes-después** — el montaje determinista
  con Pillow (una puerta por generación, composición después) fue la decisión
  correcta y además deja **capas separadas** (`_piezas/bare|blanca|bronce.png`)
  que para vídeo valen oro: se animan por separado.
- **B6-manos-pintor** — honesta, cálida, sin cara. Correcta.
- **C1-C5, D1, D2, A2, LI4** — iconos y fondos: cumplen. No son protagonistas
  ni lo pretenden.

### Las que se caen (con nombre)

- **B9-vidrio-contraluz.** La luz es preciosa, pero el ornamento en silueta
  **no es de Indigo** — son medialunas sueltas que no existen en el catálogo.
  En la pieza donde el ornamento ES el protagonista absoluto, es inventado.
  Para vídeo ni tocarla: cualquier movimiento le daría aún más protagonismo al
  dibujo falso. Se regenera con `edits` + ID21/ID26 (contraluz les va perfecto
  a los diseños de líneas) o se descarta.
- **LI1-portada.** La fila de puertas del fondo tiene **cuadrículas coloniales
  y una puerta dorada** — ni el patrón ni el acabado existen en el producto.
  Es exactamente la pieza que va a mirar un dealer (gente que vende puertas
  todo el día): la primera pantalla de LinkedIn no puede tener producto
  inventado. Regenerar componiendo la fila con montaje de puertas reales.
- **LI3-control.** El gesto (control de calidad) es el correcto para LinkedIn,
  pero la puerta está a **escala de maqueta** — dos manos sostienen una "puerta
  de entrada" del tamaño de una puerta de alacena. Un profesional lo ve al
  primer vistazo.
- **B7-instalacion.** Composición y luz bien, pero los espirales difieren de los
  de B1/FB1 (misma familia ID02, dibujo distinto) — la grilla junta las dos y
  el producto "cambia" entre posts. Además es el caso más claro de lo que el
  propio `PROMPTS.md` admite: una instalación generada es ilustración; la real,
  con un teléfono, vale el doble.
- **El bronce de B8/FB3** salió caramelo plano, más claro que el degradado real
  `#b5895a→#7d5a34`. En foto pasa; en vídeo, donde la luz se mueve sobre la
  superficie, un metálico plano canta. Si se anima, regenerar la variante
  bronce.

### Lo que las fijas no pueden contar (el hueco real)

1. **El proceso como secuencia.** El kit tiene las estaciones (CNC, pintura,
   instalación) como fotos sueltas; la historia "entra lisa → sale Indigo" solo
   existe si algo se mueve de una estación a la siguiente. Ese arco es además
   EL argumento de venta al dealer: capacidad de entrega, no casa bonita.
2. **El relieve.** El producto es geometría en 3D sobre vidrio. Una foto lo
   congela en una sola luz; el relieve se entiende cuando la luz **viaja** por
   encima y la sombra se desplaza sobre el esmerilado.
3. **La transformación.** B3 parte la pantalla; un vídeo puede hacer que el
   ornamento **aparezca sobre** la puerta lisa. Es el mismo asset, contado en
   el tiempo en vez del espacio.
4. **Los números con peso.** "185 puertas, 163 diseños, 11 dealers" en una
   esquina de imagen es un dato; como contador que sube con corte a producto es
   un argumento. Escala de taller bien contada, sin inflar.

---

## B. Qué aporta el vídeo — con el motor que ya existe

Stack disponible hoy: Remotion (plantillas data-driven, subtítulos TikTok y de
barra, ducking de música), voz ElevenLabs o Chatterbox local, música ACE-Step
local, SFX, imágenes gpt-image-2/`edits` (el mismo pipeline del kit) +
SenseNova U1.5 local para ediciones por referencia, y clips image→video
locales.

**Nota de licencias (importa porque Indigo es cliente comercial en EE. UU.):**
MiniMax H3, el motor i2v más nuevo del estudio, tiene licencia comunitaria que
**excluye EE. UU. y la UE** para uso con pesos abiertos → **queda fuera de este
proyecto**. El motor i2v para Indigo es **LTX-13B** (vía ComfyUI, probado en
producción del estudio); SenseNova y ACE-Step son Apache-2.0 y Chatterbox MIT —
limpios para trabajo de cliente.

### La regla que ordena todo: qué se anima con i2v y qué se anima con cámara

El hallazgo del kit ("una puerta sí, varias no") tiene su equivalente en vídeo:
**el i2v mueve píxeles, y donde los píxeles SON el producto, moverlos es
deformarlos.** Un ornamento que tiembla o "respira" es una puerta que el dealer
no reconoce. Así que:

| Asset | Cómo se anima | Por qué |
|---|---|---|
| **B4-cnc, FB4-taller** | **i2v (LTX-13B)** — fresa, polvo, viruta | Movimiento orgánico contenido; es donde el i2v brilla. Los mejores candidatos del kit. |
| **B6-manos-pintor** | i2v corto (~2 s) — niebla del soplete | Riesgo de manos: clip breve y sutil. |
| **B1/FB1 fachadas** | i2v suave (palmera, luz) **o** solo Ken Burns | El ornamento queda chico en cuadro → riesgo bajo. |
| **B5, B8, _piezas, D3** (producto de catálogo) | **Remotion, no i2v**: push-in, paneo, barrido de luz como capa, sombra que se desplaza | La geometría del ornamento queda **pixel-perfect**. La cámara se mueve; el producto no. |
| **B3/FB2 antes-después** | **Reveal en Remotion** (wipe con máscara sobre las capas de `_piezas/`) | La transformación en el tiempo, determinista y repetible. |
| **B9, LI1, LI3** | No animar | Arrastran los defectos de origen (ver §A). Regenerar antes. |
| **B7-instalacion** | Mejor no: dos personas en i2v = deformación casi segura | Es exactamente el plano que hay que **filmar** (ver §D). |

La composición multi-puerta en vídeo ni siquiera necesita al generador: las
tres puertas de `_piezas/` entran como **capas separadas en Remotion**
(entrada escalonada, una luz por acabado) — la limitación de "varias puertas"
desaparece porque el montaje lo hace el motor de render, no el modelo.

### Lo demás que el motor pone sobre la mesa

- **Narración bilingüe**: Miami es bilingüe; ElevenLabs multilingual permite
  versión EN y ES del mismo guion (la voz manda la duración, el resto se
  recalcula solo). LinkedIn en inglés; IG/FB se puede publicar doble.
- **Subtítulos**: word-by-word (TikTok) para IG/Reels; barra sobria para
  LinkedIn. Ya son dos estilos soportados por proyecto.
- **Música**: ACE-Step local — cama "workshop / craft, warm minimal" para IG,
  "corporate minimal tech" para LinkedIn. Sin coste por iteración.
- **SFX**: whoosh/impact ya en biblioteca; el CNC pide un router real (ver §D,
  se captura con el mismo teléfono que filma).
- **Cortes**: el motor deriva 30 s y 15 s del máster reutilizando el mismo
  audio (cero coste extra de voz).

---

## C. Piezas propuestas

Formatos del motor: Vertical 1080×1920 · Cuadrado 1080×1080 · Horizontal
1920×1080. Duraciones: máster ~30-60 s + cortes 30/15 s.

### C1. "De lisa a Indigo" — la pieza ancla
**Vertical 30 s + corte 15 s · IG Reels / FB · versión ES y EN**

La transformación completa, contada una vez y bien:

| Beat | seg | Asset | Origen |
|---|---|---|---|
| Puerta lisa, frontal | 0-4 | `_piezas/bare.png` + push-in Remotion | existe |
| "En Miami la decoramos" — CNC corta | 4-11 | B4-cnc **animada con LTX-13B** | existe + i2v |
| Pintura bronce | 11-16 | B6-manos **i2v sutil** | existe + i2v |
| El ornamento aparece sobre la lisa | 16-22 | reveal por máscara: bare → ID13 (capas) | existe |
| Fachada terminada, palmera | 22-27 | B1 con Ken Burns (o i2v suave) | existe |
| Cartón de cierre: arco del logo + CTA | 27-30 | logo-blanco + plantilla de cierre | existe |

Todo sale de assets ya generados + 2 clips i2v. **Cero rodaje necesario** para
la v1; si después llega metraje real del taller (§D), los beats 2-3 se
reemplazan y la pieza sube un escalón de honestidad sin rehacer nada más.

### C2. "163 diseños, 3 acabados" — catálogo en 15 s
**Cuadrado + Vertical 15 s · IG/FB**

Puro Remotion, cero i2v, cero riesgo: las tres puertas de `_piezas/` entran
escalonadas (bronce → blanca → negra), un barrido de luz por acabado,
contadores sobrios ("163 diseños · 3 acabados · el tuyo"). Regenerar antes la
variante bronce con el degradado real (una llamada a `edits`). Pieza
serializable: cambiando la puerta (otro `edits` con otra referencia de
`puertas/`) sale **un vídeo por diseño** — contenido para meses con el
pipeline ya probado del kit.

### C3. "Cómo entrega Indigo" — la pieza para dealers
**Horizontal 45-60 s · LinkedIn (inglés) + versión 30 s**

El argumento B2B: proceso y capacidad, no casa soñada. Orden → diseño (LI2:
pantalla CAD, único uso donde su fondo pasa) → corte CNC (FB4 animada) →
pintura → control (LI3 **regenerada** a escala real por `edits`) → instalación
→ números: **259 órdenes · 185 instaladas · 11 dealers activos** como
contadores, tipografía sobria, sin música épica. Cierre: "Trabajamos para los
que venden puertas." Caption de barra, voz EN seria (no la de anuncio).
Requiere regenerar LI1/LI3 (los defectos de §A) — 3-4 llamadas a `edits`.

### C4. Bumper de marca — 3-4 s
**Los tres formatos · abre o cierra todas las piezas**

El arco de acuarela **pintándose** (reveal por máscara sobre el logo real,
Remotion puro) + wordmark. Barato, y resuelve la consistencia de cierre de
todo lo que venga después. El azul: familia del logo (`#002478`), como manda
el contexto para logo grande.

### C5 (opcional, segunda tanda). "Un diseño por semana"
La serie derivada de C2: plantilla data-driven donde cada entrega es un JSON
(id de diseño, acabado, claim). Es el mismo modelo de fábrica que el estudio
usa en otros canales y lo que convierte esto de "4 vídeos" a "canal con
cadencia".

**Prioridad sugerida:** C4 (un día) → C1 (la ancla) → C2 → C3. C1+C2+C4
salen íntegramente de lo generado; C3 requiere las regeneraciones de §A.

---

## D. Qué hace falta del cliente

### Decisiones (bloquean antes que el material)
1. **Números en público**: ¿se pueden decir "185 instaladas / 163 diseños / 11
   dealers"? Están verificados internamente, pero publicarlos es otra cosa.
2. **Idioma**: ¿IG/FB doble ES+EN, o solo uno? LinkedIn asumo EN.
3. **Dealers por nombre**: ¿se puede decir "Lock Tight, USA Windows…" en la
   pieza B2B o se habla de "11 dealers activos" sin nombres?
4. **El azul que manda** cuando logo y fondo conviven grande (`#002478` vs
   `#1f4486`) — el contexto lo deja abierto; para motion hay que fijarlo.

### Rodaje mínimo en el taller (una visita de ~2 h, un teléfono en 4K)
Lo que ninguna IA debe fingir — y lo único que pido filmado de verdad:

| Plano | Duración | Cómo |
|---|---|---|
| **CNC cortando un ornamento real** — general de la máquina, luego cerca de la fresa con viruta saliendo | 2 tomas × 30 s, horizontal | Luz del taller tal cual; si hay una lámpara de trabajo, encendida y de costado. Teléfono apoyado o en mini-trípode, SIN paneos: plano fijo. Capturar también el **audio** del router (será el SFX real). |
| **El panel recién cortado** levantado de la mesa, se ve el calado | 15 s, vertical | A favor de la ventana, contraluz suave. |
| **Pintura**: la pistola aplicando bronce sobre panel plano | 20 s, horizontal | Un paso de pistola completo, plano fijo, que se vea la niebla. |
| **Instalación real**: colgado de hoja + cierre final con la puerta puesta | 3-4 clips × 15-20 s, vertical | Mediodía Florida, desde fuera. Caras fuera de cuadro o de espaldas (sin releases no publicamos rostros). |
| **5-8 fotos verticales de obras entregadas** | — | Frontal, sin coche en el driveway, a la hora que la fachada no esté a plena sombra. |

Con eso los beats generados de C1/C3 se van reemplazando por realidad — que es
exactamente lo que `PROMPTS.md` ya reconocía: *"esas tres valen más tomadas con
un teléfono en el taller real que generadas"*. La propuesta funciona sin el
rodaje (v1 100 % generada, declarada como ilustración de proceso), pero el
techo de honestidad y de conversión lo pone el material real.

### Qué NO pido
Estudio de foto, drone, actores, guion aprobado por comité. Escala de taller,
también en la producción.

---

## Siguiente paso

Si esta dirección va: (1) decisiones de §D, (2) creo `projects/indigo/` en el
estudio (marca + voz + guiones de C1/C2/C4 como datos), (3) storyboard de C1
en stills para aprobar ANTES de animar (regla de la casa: la historia se
aprueba en imágenes, la GPU se gasta después).
