# Generar el kit con `gpt-image-2` (API de OpenAI)

Todo lo de este documento está **verificado llamando a la API** el 2026-08-25,
no sacado de documentación.

---

## Modelos disponibles en la cuenta

```
gpt-image-2            ← el que usamos
gpt-image-2-2026-04-21 ← snapshot fijo del mismo
gpt-image-1.5
gpt-image-1
gpt-image-1-mini
chatgpt-image-latest
```

Para producción conviene fijar el snapshot (`gpt-image-2-2026-04-21`) y no el
alias: así una actualización del modelo no cambia el aspecto de la cuenta de
un día para el otro.

---

## Parámetros reales

Descubiertos mandando valores inválidos a propósito, que la API rechaza sin
generar nada (y sin cobrar):

| Parámetro | Valores | Nota |
|---|---|---|
| `size` | **cualquier ancho×alto divisible por 16** | No es una lista fija como en `gpt-image-1`. Es el hallazgo más útil. |
| `quality` | `low`, `medium`, `high`, `auto` | |
| `output_format` | `png`, `webp`, `jpeg` | |
| respuesta | siempre `b64_json` | No devuelve URL; hay que decodificar base64. |

**Hay un mínimo de píxeles.** Divisible por 16 no alcanza: la portada de
LinkedIn (1136×384 ≈ 436 k px) fue rechazada con *"Requested resolution is
below the current minimum pixel budget"*. Para banners muy apaisados hay que
pedir la **misma proporción al doble** (2272×768) y bajar de escala al
publicar — que además deja más resolución.

### Tamaños por plataforma

Como el único requisito es que ambos lados sean múltiplos de 16, se pueden
pedir las proporciones **exactas** en vez de generar cuadrado y recortar:

| Formato | Medida a pedir | Proporción |
|---|---|---|
| Feed cuadrado | `1024x1024` | 1:1 exacto |
| Feed vertical | `1088x1360` | 4:5 exacto |
| Stories / Reels | `1152x2048` | 9:16 exacto |
| Feed apaisado (FB y LinkedIn) | `1200x624` | ~1.91:1 |
| Portada de página de Facebook | `1632x848` | ~1.92:1 |
| Portada de empresa en LinkedIn | `2272x768` | 3:1 (2×, ver el mínimo de píxeles) |

**Las portadas tienen zonas seguras.** Facebook encima el avatar y el nombre
sobre el tercio izquierdo; LinkedIn pone el logo sobre el cuarto izquierdo. Al
prompt hay que pedirle explícitamente que esa franja quede **visualmente
calma** — cielo, pared lisa, piso — o el elemento importante queda tapado. Se
pidió y funcionó en las dos.

---

## Los dos endpoints, y cuál usar

### `/v1/images/generations` — solo para lo abstracto

Fondos, iconos, texturas. No hay referencia posible, así que va todo por
texto.

```bash
curl https://api.openai.com/v1/images/generations \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-image-2","prompt":"...","size":"1088x1360",
       "quality":"high","output_format":"png"}'
```

### `/v1/images/edits` — para TODA pieza con una puerta

**Este es el que importa.** Acepta una imagen de referencia y conserva el
producto real.

```bash
curl https://api.openai.com/v1/images/edits \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F "model=gpt-image-2" \
  -F "image[]=@C:/ruta/puertas/ID13-SD.png;type=image/png" \
  -F "prompt=Place this exact door into..." \
  -F "size=1088x1360" -F "quality=high"
```

> En Windows, curl necesita la ruta con `C:/...`. Con la forma de Git Bash
> (`/c/Trabajo/...`) falla sin mensaje claro.

**Por qué importa tanto:** el ornamento de una puerta Indigo es una filigrana
concreta. Describirla con palabras da *una* filigrana; pasar la foto da *la*
de ellos. En la prueba, `edits` con `ID13-SD.png` devolvió la puerta con su
patrón de arcos entrelazados intacto, montada en una fachada de Miami. Con
solo texto eso no se consigue.

Regla simple: **si en la pieza aparece una puerta, va por `edits` con la foto
real.** Si no, `generations`.

---

## Consumo medido

| Pieza | Tokens de salida |
|---|---|
| 1024×1024 `low` | 196 |
| 1024×1024 `high` | ~7.000 |
| 1088×1360 `high` | 6.431 |
| imagen de referencia (entrada) | 1.024 |

El kit completo (19 piezas en `high`) ronda **130.000 tokens de imagen de
salida**. El precio por token hay que mirarlo en el panel de OpenAI — la API
reporta el consumo pero no lo que cuesta.

**Tiempo:** entre 15 s (`low`) y ~115 s (`high`). Las 19 piezas son cerca de
media hora. Conviene correrlo en segundo plano.

---

## El script

`scripts/generar-instagram.py` (copia en el scratchpad de la sesión). Lo que
resuelve más allá de llamar a la API:

- **Elige el endpoint solo** según la pieza tenga referencia o no.
- **Es reanudable**: saltea lo que ya existe. 19 piezas a un minuto cada una
  es demasiado para perderlo por un timeout.
- **Una pieza que falla no corta la corrida**: se reporta al final.
- **Suma el consumo** de todas las llamadas.
- Acepta un filtro por nombre para regenerar una sola: `python generar.py B5`.

Uso:

```bash
python generar.py          # todas las que falten
python generar.py B5       # solo las que contengan "B5" en el nombre
```

La clave va en un archivo `.key` junto al script, **fuera del repositorio**.

---

## El límite de `edits`, corregido: no es cuántas puertas, es cuánto cambias

> **Corrección del 2026-09-01.** La regla de abajo decía que el ornamento
> sobrevive "mientras haya UNA sola puerta en la salida". Es incompleto y
> costó dos generaciones descubrirlo.

Al regenerar B6 se pidió **una sola puerta** metida en una cabina de pintura,
en ángulo y sobre un caballete. El modelo devolvió la puerta con **cuatro
barras lisas**: perdió el ornamento entero. Segundo intento, esta vez pidiendo
"cambia SOLO el color y el fondo" y manteniendo el plano frontal: **volvió a
perderlo**.

Lo que de verdad predice si el ornamento sobrevive no es el número de puertas,
es **cuánto tiene que reconstruir el modelo**:

| Lo que se pide | Ornamento |
|---|---|
| Cambiar el color, fondo plano igual | se conserva (bronce, blanca, B5) |
| Meter la puerta en una fachada o una obra | se conserva (B1, B7, FB1) |
| **Cambiar el entorno a un interior nuevo** | **se pierde** (los dos intentos de B6) |
| Varias copias de la puerta en la misma imagen | se pierde |

La diferencia entre "fachada" y "cabina de pintura" parece caprichosa, pero
tiene sentido: en la fachada la puerta sigue de frente y encajada en un hueco,
o sea que el modelo la pega; en la cabina hay que redibujarla con otra luz y
otra perspectiva, y al redibujarla se inventa el patrón.

**Regla práctica:** si el encuadre de la referencia se mantiene, el ornamento
aguanta. Si hay que rehacer la puerta, no. Cuando haga falta un entorno nuevo,
generar el fondo por separado y **componer**, igual que con las tres puertas.

---

## El límite de `edits`: una puerta sí, varias no

El hallazgo más caro de la sesión, encontrado generando de verdad.

`edits` reproduce el ornamento de la referencia **con fidelidad total mientras
haya UNA sola puerta en la imagen de salida**. En cuanto se le piden dos o
tres copias —un antes/después, tres acabados lado a lado— **pierde la
filigrana y se inventa una geométrica**. Se intentó dos veces, la segunda con
instrucciones en mayúsculas del tipo *"reproduce the ornament EXACTLY, stroke
for stroke"*. Falló igual.

La solución no es insistir con el prompt, es no pedírselo:

1. Generar **cada puerta por separado** con `edits`, cambiando una sola cosa
   por vez ("mismo diseño, ahora en bronce"). Ahí es fiable.
2. **Montar la composición con Pillow.**

Y sale mejor que si funcionara: el montaje es determinista, así que las tres
puertas quedan exactamente del mismo alto y perfectamente alineadas —cosa que
un generador no garantiza nunca— y se puede rehacer sin volver a pagar tokens.

`scripts/componer-variantes.py` hace las dos cosas. Un detalle que importa:
recorta cada puerta a su contenido antes de montar, porque el generador deja
márgenes blancos distintos en cada imagen y sin eso quedan de tamaños
dispares. Y compone **sobre blanco**, no sobre gris: el fondo de las fuentes
es blanco y cualquier resto de margen que el recorte no atrape se vuelve
invisible.

## Cosas que aprendimos por las malas

**El contexto de marca va en cada prompt, no solo al principio.** La API no
tiene conversación: cada llamada es independiente. Por eso el script antepone
un bloque fijo con el producto, los colores y las prohibiciones a cada prompt
de producto.

**Hay que prohibir el texto explícitamente y en cada pieza.** Si no, el modelo
mete letras deformadas. El bloque fijo termina en *"absolutely no text,
letters, words, numbers or logos anywhere in the image"*.

**El azul de marca no puede estar suelto en el mismo bloque que los
acabados.** La primera versión del contexto decía "Brand blue #1f4486.
Finishes: bronze..., off-white..., black..." y el modelo pintó una puerta de
**azul**. Hubo que decirlo explícito: *"the brand blue is for GRAPHICS ONLY
and must never be used on a door"*.

**"Mitades" se lee como "dos hojas".** Pedir "una puerta dividida por la mitad,
izquierda sin decorar" devolvió una puerta doble. Hay que decir "DOS PUERTAS
SEPARADAS de una hoja cada una, esto NO es una puerta doble".

**`quality: high` no es opcional para producto.** En `low` el ornamento sale
como una mancha; la diferencia de tokens es enorme (196 contra 7.000) pero en
valor absoluto sigue siendo poco.

**Fijá el snapshot para reproducibilidad.** Si dentro de tres meses hay que
regenerar una pieza para que combine con las otras, `gpt-image-2` a secas
puede haber cambiado.
