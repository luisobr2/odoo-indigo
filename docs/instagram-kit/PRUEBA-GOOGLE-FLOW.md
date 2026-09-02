# Prueba de Google Flow para Indigo — protocolo de decisión

**Objetivo: decidir si vale la pena pagarlo.** No es un lote de producción.
Cada prompt responde una pregunta concreta y tiene un criterio de aprobado.

> **Sobre el modelo.** No tengo verificado que exista un modelo de Google
> llamado «Omni Flash»; el de vídeo de Flow es **Veo**. Da igual para esta
> prueba: el protocolo vale para el modelo de vídeo que Flow te ofrezca.
> Anotá cuál usaste al lado de cada resultado.

---

## Lo que hay que averiguar, en orden de importancia

**1. ¿Sobrevive el ornamento?** Es *la* pregunta. El producto de Indigo **es**
la filigrana. Si en 8 segundos de vídeo las volutas se deforman o se
reordenan, Flow no sirve para plano de producto — solo para ambiente.

Ya sabemos esto de las imágenes: `edits` conserva el ornamento **solo si no
hay que redibujar la puerta**. El vídeo añade deriva temporal, que es mucho
más difícil. Es perfectamente posible que falle.

**2. ¿Hace lo que el pipeline actual no puede?** Hoy Remotion monta Ken Burns
sobre fotos fijas. No puede hacer movimiento real: la fresadora cortando, la
pintura corriendo, una puerta abriéndose. **Ahí está el valor**, si lo hay.

**3. ¿Las manos?** `B6` falló dos veces por una mano deforme. En vídeo es peor.

---

## Bloque de marca — pegar en TODOS los prompts

```
Indigo Decors, Miami. The product is a DECORATIVE ORNAMENT APPLIED OVER
FROSTED PRIVACY GLASS on an impact-rated entry door. Door leaf and frame are
one solid colour with a subtle fibreglass texture. The ornament is the SAME
colour as the door, in relief, like forged ironwork but applied. Finishes:
warm bronze gradient #b5895a to #7d5a34, warm off-white #f3f1ea, matte black
#1a1a1a. Slim brushed lever hardware. South Florida light.
```

## Negative — pegar en TODOS

```
no wood grain, no clear see-through glass, no coloured stained glass, no
security bars in front of the door, no garage doors, no gates, no interior
doors, no text, no lettering, no logos, no warped or extra fingers, no faces
looking at camera, no oversaturation.
```

**Formato:** 9:16 (el Instagram de Indigo es vertical). Duración: la máxima
que dé la herramienta.

---

# BLOQUE A · La pregunta que decide la compra

Si A1 y A2 fallan, **no hace falta probar nada más para decidir**: Flow queda
como herramienta de ambiente, no de producto, y hay que valorarlo solo por eso.

### A1 · Fidelidad en cámara casi quieta
**Referencia:** `reales/10-dd-negra-curvas-fachada.jpg`

```
Hold on this exact door. Extremely slow push-in, the camera barely moves.
The ornamental scrollwork MUST NOT CHANGE: every scroll and curve stays
exactly where it is, same thickness, same spacing, for the whole clip. Warm
interior light glows through the frosted glass. Outside the frame, foliage
moves slightly in the breeze, casting soft moving shadows on the stucco.
Locked-off tripod feel, cinematic, photorealistic.
```

**Aprobado si:** superpones el primer y el último fotograma y las volutas
coinciden. **Suspenso si:** alguna espiral cambia de sitio, se engorda o
aparece/desaparece.

### A2 · Fidelidad con cámara en movimiento
**Referencia:** `reales/14-sd-negra-flores-interior.jpg`

```
Slow vertical tilt down this exact door, from the top medallion to the bottom
one, revealing the three medallions one by one. The medallions MUST stay
identical: same eight-pointed star frame, same flower inside, same count.
Warm interior light. Smooth gimbal move, photorealistic.
```

**Aprobado si:** siguen siendo **tres** rosetones y el patrón no muta al pasar.

---

# BLOQUE B · Lo que el pipeline actual NO puede hacer

Aquí está el valor real. Remotion no puede generar movimiento.

### B1 · La fresadora cortando
**Referencia:** `reales/20-taller-cnc-cortando.png`

```
The CNC router bit travels along a curved path, cutting a smooth arc through
a flat sheet. Fine aluminium chips fly and settle. The already-cut part of the
pattern stays exactly as it is. Cool machine light, shallow depth of field.
Nobody in frame. Photorealistic documentary footage.
```

**Aprobado si:** el corte avanza de forma continua y coherente, sin que la
parte ya cortada se reescriba sola.

### B2 · La pintura
**Referencia:** `reales/21-taller-acabado-a-mano.png`

```
Extreme close-up: a brush lays warm bronze paint along the curve of an
ornamental scroll, the wet edge advancing along the metal. Only the brush and
a gloved fingertip enter the frame. Soft window light catching the wet paint.
Shallow depth of field. Photorealistic.
```

### B3 · La puerta abriéndose — el plano que no existe
Sin referencia (o con `reales/_limpias/08-dd-negra-circulos-fachada.png`).

```
A double entry door with an interlocking-circles ornament over frosted glass
swings slowly open from the outside, revealing warm interior light spilling
onto a brick porch. The camera holds still. Late afternoon South Florida
light. Photorealistic, cinematic.
```

**Por qué importa:** ninguna foto fija puede hacer esto, y para una empresa de
puertas es *el* plano. Si sale bien, esto solo puede justificar el gasto.

---

# BLOQUE C · Los riesgos conocidos

### C1 · Manos
```
Gloved hands lift a finished bronze ornamental panel off a workbench and turn
it slowly towards the light, checking the finish. Only hands and forearms in
frame, no face. Warm workshop light. Photorealistic.
```
**Aprobado si:** los dedos se mantienen en número y forma durante todo el clip.

### C2 · Cámara recorriendo el taller
```
Slow tracking shot moving past a row of finished ornamental door panels
leaning against a workbench in a small metal workshop, warm late light from a
high window, fine dust in the air. Nobody in frame. Photorealistic.
```

---

# BLOQUE D · Ambiente

### D1 · La fachada con la luz cambiando
**Referencia:** `reales/_limpias/11-sd-blanca-flores-fachada.png`

```
Hold on this exact entrance. The light slowly warms as the sun drops, shadows
of palm fronds drifting across the turquoise stucco wall. The door and its
white medallion pattern stay completely unchanged. Photorealistic, cinematic,
locked-off camera.
```

---

## Cómo leer el resultado

| Qué pasó | Qué significa |
|---|---|
| A1 y A2 aprueban | Sirve para producto. **Es la compra fácil** |
| A falla, B aprueba | Solo B-roll y proceso. Sigue valiendo: es justo lo que Remotion no puede |
| A y B fallan, C y D aprueban | Solo ambiente. Se puede vivir sin ello |
| B3 aprueba | Por sí solo puede justificar el gasto |

**Antes de pagar, comprobá en la propia herramienta:** cuántas generaciones
entran en el plan, si el vídeo sale con marca de agua, la duración máxima del
clip, si permite 9:16, y si los clips se pueden usar comercialmente.
No me fío de dar cifras de precio de memoria — miralas en su web.

## Dónde guardar los resultados

`docs/instagram-kit/pruebas-flow/<fecha>-<A1|A2|...>.mp4`, y anotá aquí
debajo qué modelo usaste y si aprobó. Con eso decidimos con datos y no con
impresión.
