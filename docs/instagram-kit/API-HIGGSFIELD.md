# Mejorar y animar fotos reales con Higgsfield

Todo verificado generando de verdad el **2026-09-22**, con las fotos de
instalación 02, 06 y 07 para el reel `dealers`. El proceso general (créditos,
recetas, montaje en Remotion) está en la skill `higgsfield-brand-video`; aquí
va solo lo específico de **fotos de puertas reales**, donde lo que no se puede
tocar es el ornamento.

---

## Qué herramienta para qué

| Necesidad | Herramienta | Créditos | Resultado medido |
|---|---|---|---|
| Mejorar calidad de una foto real | `upscale_image` (bytedance), 2k | 2 | **Conserva la forma**: 100 % y 98 % del camino al techo |
| Pasar una foto cuadrada a 9:16 sin recortar | `outpaint_image`, 9:16 | 2 | Conserva la puerta (0,93), pero **encoge** la foto, ver abajo |
| Animar la foto | `generate_video`, `seedance_2_5`, 5 s | 35 (720p) / 60 (1080p) | Ornamento intacto en **3 de 3** clips con prompt de solo cámara |

**Para mejorar, el upscaler y no gpt-image.** gpt-image regenera la foto
entera y en una de cada tres se inventó el ornamento (ver `API-GPT-IMAGE-2.md`).
El upscaler está hecho para ganar resolución sin recomponer, y en las pruebas
no cambió ni un trazo.

## Cómo se verifica cada paso

Nunca a ojo en miniatura: a ese tamaño una puerta redibujada «parece la misma».

| Paso | Script | Qué hace |
|---|---|---|
| Mejora con el mismo encuadre | `verificar-mejoradas.py` | Bordes del original contra la mejorada, calibrado entre techo y suelo |
| Extensión o cambio de encuadre | `comparar-alineado.py` | Localiza el original dentro del resultado (SIFT + homografía) y compara ahí |
| Clip animado | `verificar-clip.py` | Alinea cada medio segundo del vídeo con la foto (la cámara se mueve) y mide |

Las cifras señalan; la decisión se toma **mirando** las hojas que generan.

### Trampas de la verificación, las tres encontradas hoy

- **Una ampliación comparada a su tamaño da cifras falsamente bajas.** Añade
  textura fina que el original estirado no tiene, y cada detalle nuevo cuenta
  como borde distinto: la 06 daba 0,53 y era idéntica. Hay que bajar la
  ampliada al tamaño original y comparar ahí (salió 100 %).
- **Comparar una extensión píxel a píxel mide el desplazamiento, no el
  contenido.** El outpaint encoge el original, así que superponerlo a ancho
  completo daba una diferencia de 55 sobre 255 con la puerta intacta. Alineado
  con puntos característicos: 0,93.
- **En una puerta blanca y lisa la alineación puede fallar** (escala 0,01,
  correlación 0): hay tan pocos puntos que casar que la homografía sale
  degenerada. Es un fallo de la medida, no de la puerta: mirar la hoja.

## El outpaint no solo añade: también encoge y recorta

Pedido 9:16 sobre la foto 02 (1600×1600), devolvió 1536×2752 con el original a
escala **0,97** y desplazado: **se pierden unos 60 px por un lado** y se
inventan unos 40 por el otro, además del techo y el suelo. Y en el suelo nuevo,
brillante, **dibujó el reflejo de la puerta**. Aquí era aceptable (la foto
original ya asomaba ese reflejo), pero es contenido inventado: revisarlo
siempre.

## seedance: lo que funcionó

```
model: seedance_2_5, mode: omni_reference, medias: [{role: start_image, value: <job_id del still>}]
duration: 5, resolution: 1080p, aspect_ratio: 9:16, generate_audio: false
declined_preset_id: 24bae836-2c4a-48e0-89b6-49fcc0b21612
```

El prompt que mantuvo el ornamento en los tres: decir **explícitamente** que la
puerta está cerrada e inmóvil y que el ornamento no cambia, y que **solo se
mueven la cámara y el entorno** (acercamiento lento y continuo, palmeras, luz).
Añadir siempre «the door never opens»: Veo ya la abrió una vez.

El acercamiento no es uniforme: la puerta de óvalo creció un 20 % en 5 s, la
doble un **54 %** y la blanca parecido. En escenas cortas se usa el tramo
inicial; si hace falta todo el clip, pedir el acercamiento más suave.

### Entrega y tiempos

- **1080p llega en HEVC 10 bits.** Remotion no lo lee y cae en silencio a la
  foto fija: convertir a H.264 8 bits (receta en la skill).
- **La cola es impredecible**: el primer clip pasó ~20 min en cola antes de
  empezar; los dos siguientes, lanzados juntos, arrancaron enseguida y
  tardaron unos 8. El crédito se descuenta al aceptar el trabajo.
- Luz: la de óvalo salió con media 96, por debajo del mínimo del registro. Se
  aclaró con `eq=gamma=1.18` (→ 109), con nombre de archivo nuevo porque
  Remotion cachea por nombre.

## Coste real del reel `dealers`

| Concepto | Créditos |
|---|---|
| 3 ampliaciones + 1 extensión | 8 |
| 3 clips seedance 1080p | 180 |
| **Total** | **188** |

Voz (ElevenLabs) y música (ElevenLabs Music) van aparte, fuera de Higgsfield.

## Puertas de catálogo en escena (reels `entrada` y `privacidad`, 22-sep)

Cuando no hay foto real que valga, la puerta sigue siendo el render del
catálogo: **la IA nunca dibuja el ornamento**. Lo que sí genera es el
entorno, y la puerta se monta encima con los scripts del kit.

| Paso | Herramienta | Coste |
|---|---|---|
| Ampliar el render a 4k | `upscale_image` (bytedance, `4k`) | 2 cr por puerta |
| Toma de estudio (fondo navy, foco, reflejo, grano) | `scripts/hero-puerta.py` con `SRC=<4k>` | 0 |
| Casa generada (recibidor, fachada) con un **hueco de pared liso** donde irá la puerta | `generate_image` `gpt_image_2_5`, quality high, 9:16 | ~2 cr |
| Montar la puerta en el hueco, sombra del ornamento en el suelo, vidrio cálido | `scripts/puerta-en-escena.py --sombra --brillo` | 0 |
| Animar solo luz y cámara | seedance (receta de arriba) | 60 cr por clip |

Pedir el fondo **sin puerta** y con la pared lisa es lo que evita que gpt-image
invente un ornamento que luego habría que tapar. `outpaint_image` (2 cr) sirve
para llevar un cuadrado a 9:16, pero encoge el original un ~3 % e inventa
reflejos: verificar con `comparar-alineado.py`.

Los dobles con seedance arrancan con la puerta al 67-88 % del tamaño y crecen
durante el clip: se reencuadraron con ffmpeg (×1,45 desde 1,5 s / ×1,25) antes
de montar, en lugar de gastar otro clip.

## Coste real de los reels `entrada` y `privacidad`

| Concepto | Créditos |
|---|---|
| 5 ampliaciones a 4k (3 DD + 2 SD) | 10 |
| 1 ampliación de fondo a 2k + 2 fondos gpt-image | ~8 |
| 4 clips seedance 1080p | 240 |
| **Total** | **~258** |

Saldo tras los dos reels: **1302 créditos** (medido con `balance`).

