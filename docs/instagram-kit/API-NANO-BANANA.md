# Generar imágenes con Nano Banana (API de Gemini)

Todo **verificado llamando a la API** el 2026-09-03. Tercer documento de la
familia, junto a `API-GPT-IMAGE-2.md` (OpenAI) y `API-VEO-3.md` (vídeo).

Misma clave que Veo — vive **fuera del repo**, en la memoria del proyecto.

---

## Para qué sirve, frente a los otros dos

| | Fuerte en | Coste |
|---|---|---|
| **gpt-image-2** | Piezas de marca, texto horneado legible | ~6.400 tokens/imagen |
| **Nano Banana** | **Editar una foto real conservando el resto**, guiones visuales | **~1.280 tokens/imagen** |
| **Veo 3.1** | Movimiento | 85-120 s por clip de 8 s |

Nano Banana es **cinco veces más barato** que gpt-image-2 y mucho mejor
conservando una escena existente. Para guiones visuales, es la herramienta.

---

## La llamada

No hay método propio: va por `generate_content` y la imagen vuelve como una
parte `inline_data` mezclada con el texto.

```python
resp = client.models.generate_content(
    model="models/nano-banana-pro-preview",
    config=types.GenerateContentConfig(
        image_config=types.ImageConfig(aspect_ratio="9:16", image_size="2K")),
    contents=[
        types.Part.from_bytes(data=ref.read_bytes(), mime_type="image/png"),
        PROMPT,
    ],
)
for cand in resp.candidates:
    for part in cand.content.parts:
        if part.inline_data and part.inline_data.data:
            destino.write_bytes(part.inline_data.data)
```

### Valores admitidos (descubiertos gratis)

Mismo truco que con Veo: un valor inválido lo rechaza la validación **antes de
generar**. Y aquí el error además **enumera la lista completa**.

| Parámetro | Valores |
|---|---|
| `aspect_ratio` | 1:1, 1:4, 1:8, 2:3, 3:2, 3:4, 4:1, 4:3, **4:5**, 5:4, 8:1, **9:16**, 16:9 |
| `image_size` | **1K, 2K, 4K**, 512, 512P, 512PX |
| `person_generation` | **solo Enterprise** — no se puede usar |

Mucho más flexible que Veo, que solo acepta 9:16 y 16:9. Aquí **sí** hay 4:5,
que es el formato de publicación del feed de Instagram.

Modelos disponibles en la cuenta: `nano-banana-pro-preview`,
`gemini-3-pro-image`, `gemini-3.1-flash-image`, `gemini-3.1-flash-lite-image`,
`gemini-2.5-flash-image`.

---

## Lo que mejor hace: quitar y poner cosas sin tocar el resto

Se le pasó la foto real de la puerta ancla y se le pidió **la misma puerta sin
el ornamento**. Devolvió exactamente eso: mismo farol, mismo montante en arco,
mismas columnas, mismo ladrillo, mismas sillas azules, misma luz, mismo
ángulo — y el vidrio esmerilado liso.

Eso resuelve algo que Indigo **no puede fotografiar**: no existe ni una imagen
de las puertas antes de decorarlas.

---

## La técnica que hace posible un guion: ENCADENAR REFERENCIAS

Para que una secuencia parezca la misma casa, cada escena **parte de la
anterior**, no de cero:

```
foto real → escena 1 → escena 2 → escena 3 → escena 4
```

Con cinco generaciones independientes salen cinco casas distintas. Encadenando,
la luz, el encuadre y cada detalle del fondo se mantienen. Es la diferencia
entre un guion y un montón de imágenes sueltas.

## Las manos salen bien

`gpt-image-2` falló dos veces con manos (`B6`). Nano Banana devolvió a la
primera un guante de trabajo con anatomía correcta sujetando una cinta métrica
y otro presionando un panel. Aun así: **pedir guante y una sola mano**, y
revisarlas ampliadas.

## El texto dentro de la imagen sigue siendo basura

Los números de la cinta métrica son garabatos. Da igual a tamaño de vídeo,
pero **no se puede hacer un primer plano de nada que lleve texto**. Para
rótulos, componer aparte.

---

## El aviso que importa

Un «antes» generado es una **reconstrucción, no una fotografía**. Es fiel —el
vidrio esmerilado es lo que hay debajo del ornamento— pero publicarlo como un
antes/después real sin decirlo es engañoso.

Dos salidas: etiquetarlo como simulación, o —mejor y gratis— **que Indigo
fotografíe las puertas antes de decorarlas**. Un minuto por puerta y tienen
antes/después reales para siempre.

---

## Guion producido con esto

`scratchpad/gemini/guion/` — cuatro escenas de la secuencia «la
transformación»: la puerta lisa, la medición, el diseño sobre el vidrio y el
montaje del panel. Las otras dos escenas de la secuencia (el corte y el
resultado) ya eran fotos reales.

Coste total: **~5.100 tokens**, una fracción de un solo clip de vídeo.
