# Piezas nuevas (2026-09-02)

Cinco piezas generadas con `gpt-image-2` para tapar los dos huecos que las
fotos reales no cubren: **el bronce** y **el proceso**.

| Pieza | Qué es | Cómo se hizo |
|---|---|---|
| `P1-bronce-flores.png` | Los tres rosetones en bronce | `edits` sobre `reales/14` |
| `P2-bronce-ovalo.png` | El óvalo en bronce | `edits` sobre `reales/07` |
| `P3-cnc-macro.png` | Broca cortando una curva en chapa | `generations` |
| `P4-pintura-macro.png` | Pincel dando bronce a una voluta | `generations` |
| `P5-taller.png` | Taller al final del día, paneles apoyados | `generations` |

Coste: 32.155 tokens de salida, ~2 min por pieza.

## Por qué están hechas así

**El bronce sale de puertas reales, no de renders.** Hasta ahora la única
pieza en bronce del kit (`_piezas/bronce.png`) venía de un render de catálogo.
Estas dos parten del ornamento de una puerta instalada de verdad, así que el
bronce que se enseña es el de un diseño que Indigo vende.

Funcionó porque se respetó la regla que costó dos generaciones descubrir
(`API-GPT-IMAGE-2.md`): **`edits` conserva el ornamento mientras no haya que
redibujar la puerta.** Cambiar el color manteniendo encuadre, ángulo y luz,
sí. Cambiar el entorno, no.

**El proceso va en macro, y eso es deliberado.** `B6-manos-pintor` falló dos
veces porque pedía una puerta entera en una cabina de pintura: el modelo tenía
que rehacer la puerta y se inventaba el ornamento. En un plano cerrado no hay
puerta que reconstruir, así que ese modo de fallo desaparece. Además se pidió
mano enguantada o fuera de cuadro — la mano deforme fue justo el defecto de B6.

**`P4-pintura-macro` sustituye a `B6`.** Sin manos deformes.

## Qué son y qué no

`P3`, `P4` y `P5` son **ilustrativas**: representan operaciones que Indigo hace
de verdad, pero no son su taller ni sus manos. Sirven como imagen de apoyo,
igual que una foto de banco. **No se pueden presentar como «así trabajamos
nosotros»** — para eso hacen falta las fotos que pide el brief y que siguen sin
llegar: taller real, CNC real, el equipo.
