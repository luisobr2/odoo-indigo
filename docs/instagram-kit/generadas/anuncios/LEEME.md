# Anuncios con texto (2026-09-02)

Cuatro piezas publicitarias con el titular **horneado en la imagen**, público
dueño de casa (Instagram). Las de dealer no están hechas.

| Pieza | Titular | Base |
|---|---|---|
| `AD1-temporada-navy.png` | Impact-rated doesn't have to mean plain. | Navy tipográfico, sin foto |
| `AD2-temporada-foto.png` | Impact-rated doesn't have to mean plain. | `reales/_limpias/08` |
| `AD3-came-plain.png` | Your door came plain. It doesn't have to stay that way. | `reales/10` (la ancla) |
| `AD4-tres-acabados.png` | Pick your finish. + BRONZE / WHITE / BLACK | `taller/T3` |

`AD1` y `AD2` dicen lo mismo en dos formatos: uno tipográfico y otro sobre
foto. **Publicar solo uno**; el otro sirve de espejo para Facebook.

`AD1` y `AD2` son **estacionales** — pico de temporada de huracanes,
agosto-septiembre. Su momento es ahora.

---

## La regla de «nada de texto» ya no aplica

Todos los prompts del kit prohíben texto. Esa regla se escribió cuando los
modelos garabateaban letras. `gpt-image-2` renderiza titulares correctos:
ortografía, guiones, apóstrofos, interletraje parejo, y hasta tres etiquetas
cortas alineadas bajo tres objetos distintos (`AD4`).

**Pero hornear el texto tiene un coste, y ya se nota en este mismo lote:**
`AD3` salió con la URL en mayúsculas (`INDIGODECORS.COM`) y un apóstrofo recto,
mientras las otras tres llevan minúsculas y apóstrofo tipográfico. **No se
puede corregir editando**: hay que regenerar la pieza entera, y la nueva no va
a coincidir con la anterior.

### Cuándo hornear y cuándo componer

| | Hornear (API) | Componer (Pillow) |
|---|---|---|
| Anuncio de campaña, una pieza | ✔ | |
| Texto que convive con la escena | ✔ | |
| Serie que se repite (diseño de la semana, carruseles) | | ✔ |
| Traducir ES/EN | | ✔ |
| Corregir una errata | | ✔ |
| Tipografía de marca exacta | | ✔ |

Los carruseles y las quote cards del kit ya están compuestos con Pillow. Ese
sigue siendo el camino para todo lo que se repita.

## Preservación del ornamento

Las tres piezas sobre foto se pidieron **en la misma proporción que su
referencia** (`AD2` y `AD3` cuadradas, `AD4` en 4:5). Cambiar de proporción
obliga al modelo a recomponer, y recomponer es lo que hace que se invente la
filigrana. Con el encuadre respetado, el ornamento aguantó en las tres.

## Lo que NO se puso, a propósito

- **Plazos y precios.** No están verificados, y un anuncio que promete una
  fecha de entrega es una promesa que alguien tiene que cumplir.
- **Los números** (185 instaladas · 163 diseños · 11 dealers): pendientes del
  OK de Majela.
- **Nombres de dealers.**
