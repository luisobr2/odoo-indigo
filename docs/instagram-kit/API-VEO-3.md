# Generar vídeo con Veo 3.1 (API de Gemini)

Todo lo de este documento está **verificado llamando a la API** el 2026-09-02,
no sacado de documentación. Hermano del `API-GPT-IMAGE-2.md`, que es el de
imagen.

La clave vive **fuera del repo** (este es público). Está en la memoria del
proyecto.

---

## Antes de gastar: los valores se descubren gratis

La API valida antes de generar. Un valor inválido devuelve 400 **sin cobrar**.
Y hay un truco mejor: para saber si un valor concreto es bueno, se manda
acompañado de `duration_seconds=999`, que siempre es inválido. Si el error
habla solo de la duración, el otro valor era correcto y la petición nunca
llegó a generar.

Así salió toda esta tabla sin gastar un céntimo:

| Parámetro | Valores admitidos |
|---|---|
| `aspect_ratio` | **9:16** y 16:9. **No** 1:1 ni 4:5 |
| `duration_seconds` | 4 a 8 |
| `resolution` | 720p, 1080p, 4k |
| `person_generation` | `allow_all`, `allow_adult` |

**`1080p` no admite 4 segundos.** La resolución alta obliga a 8. Si hacen
falta planos cortos, se generan de 8 y se recortan.

**`dont_allow` no vale si se pasa imagen de referencia.** Que no salga gente
depende entonces solo del negativo.

### Rechazados en modo Developer (solo existen en Enterprise)

`seed` · `fps` · `generate_audio` · `mask` · `labels` ·
`compression_quality` · `output_gcs_uri` · `pubsub_topic` · `resize_mode`

### Y uno que rechaza el modelo

**`enhance_prompt`**: `veo-3.1-fast` lo rechaza directamente. O sea que **no
se puede impedir que Veo reescriba el prompt**. Consecuencia práctica: las
instrucciones críticas van **cortas y en mayúsculas**. Una cláusula larga se
diluye en el reescritor; una de seis palabras sobrevive.

### Sin `seed` no hay repetición

Dos llamadas con el mismo prompt dan resultados distintos. **Lo que salga
bien, se guarda**: no se puede volver a conseguir.

---

## La decisión que más importa: pasar la foto

```python
client.models.generate_videos(
    model="models/veo-3.1-fast-generate-preview",
    source=types.GenerateVideosSource(
        prompt=PROMPT,
        image=types.Image(image_bytes=ref.read_bytes(), mime_type="image/png"),
    ),
    config=types.GenerateVideosConfig(
        aspect_ratio="9:16", resolution="1080p", duration_seconds=8,
        negative_prompt=NEGATIVO, person_generation="allow_adult",
    ),
)
```

Con `image=`, **el primer fotograma es la foto real** y el ornamento arranca
perfecto. Solo con texto, el modelo inventa *una* filigrana en vez de
reproducir *la* de Indigo — es el mismo problema que en imagen, y por el mismo
motivo.

**La referencia debe ir ya en 9:16.** Si se pasa cuadrada, el modelo
recompone y ahí es donde se deforma.

⚠️ **No usar como referencia una imagen con bandas** (una foto cuadrada
montada sobre lienzo vertical con fondo desenfocado): Veo **reproduce las
bandas dentro del vídeo**. Pasó con `real-doble.png` y hubo que recortar.

---

## La deriva necesita tiempo

El hallazgo que arregló el anuncio.

El primer lote pedía quietud —«cámara casi inmóvil», «trípode fijo»— para
proteger el ornamento. Funcionó: fiel y **soso**. Objetivo equivocado.

Lo cierto es que **el ornamento no se deshace de golpe, se degrada con los
segundos**. Así que se puede tener energía Y fidelidad:

> Generar 8 segundos pidiendo **movimiento fuerte**, y usar solo los 2-3
> primeros.

Para que Veo se mueva de verdad hay que nombrarlo con velocidad —
`FAST dolly push straight in, accelerating`, `the camera ARCS quickly
sideways`, `sunlight SWEEPS RAPIDLY across` — y meter en el negativo
`static camera, still frame, frozen shot`.

### Qué aguanta y qué no

| Plano | Ornamento |
|---|---|
| Cámara quieta, luz cambiando | intacto los 8 s |
| Push-in rápido, arco lateral | intacto en los primeros 3-4 s |
| Barrido de luz | intacto (la cámara casi no se mueve) |
| **Puerta abriéndose** | **solo los 3 primeros segundos**: luego las hojas quedan de canto y el ornamento deja de verse |

---

---

## Revisar los clips CADA MEDIO SEGUNDO, no por segundos

El aviso mas caro de todos, y por poco no se detecta.

En el anuncio del 3-sep, Veo metio **un hombre con americana azul cruzando
delante de la puerta**, tapandola. Estaba solo entre el segundo 0,2 y el 0,9.
Se reviso el clip muestreando en segundos enteros -0, 1, 2, 3...- y se dio por
limpio **dos veces**: el muestreo caia justo antes y justo despues. Aparecio al
montar una hoja de contactos cada 0,5 s.

**Un elemento no deseado puede durar menos de un segundo.** Revisar siempre a
0,5 s o menos, y mirar la hoja: las metricas automaticas de "cambio entre
fotogramas" NO sirven cuando la camara se mueve, porque entonces todo cambia
mucho y lo raro no destaca.

### No se puede impedir que salga gente

`person_generation="dont_allow"` **lo rechaza la API cuando se pasa imagen de
referencia** (400). Solo queda `allow_adult`. Y el negativo con
`people, hands, faces` **no basta**: en el caso de arriba estaba puesto y aun
asi la genero. Como ademas `enhance_prompt` no se puede desactivar, el
reescritor puede diluir la intencion.

Conclusion practica: **con Veo no hay garantia de que no aparezcan personas.**
Hay que revisar cada clip antes de usarlo. Si sale gente y el resto del plano
sirve, casi siempre basta con recortar el tramo (`ffmpeg -ss`): el intruso
suele cruzar en un momento concreto, no estar todo el clip.

## El empuje se rompe pasado el segundo 4

`dyn-01-push` -"FAST dolly push, accelerating"- funciona hasta ~3,5 s. A
partir de ahi la camara se ha acercado tanto que la puerta deja de leerse como
puerta y queda una forma abstracta.

O sea que un movimiento agresivo da **3 segundos utiles de los 8 generados**,
no ocho. Conviene contarlo asi al planificar cuantos clips hacen falta.

## Lo que sale, y lo que hay que hacerle

Los clips salen **1080×1920, 24 fps, `yuv420p`, sin etiquetas de color**, con
audio nativo de Veo que no se puede desactivar.

Para Instagram hay que pasarlos por ffmpeg:

```
-color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv
-movflags +faststart
-af loudnorm=I=-14:TP=-1.5:LRA=11
```

⚠️ **El ffmpeg de Remotion no sirve para montar**: es una compilación mínima,
**sin `drawtext` ni `drawbox`**. Para rotular hay que usar el del sistema
(`...\Microsoft\WinGet\Links\ffmpeg.exe`).

Y al escribir expresiones de `drawtext`, **las comas de `max()`/`min()` van
escapadas o entrecomilladas**: ffmpeg separa filtros por coma y el filterchain
no compila.

---

## Consumo medido

| Pieza | Tiempo |
|---|---|
| clip 8 s, 1080p, `veo-3.1-fast` | 85-120 s |

La API **no devuelve coste**, solo tiempo. El precio está en el panel de
Google AI Studio.

El material generado está en
`C:\merktop\video-production\output\indigo\veo\` — 6 clips y 2 anuncios.
**No regenerables** (sin `seed`).
