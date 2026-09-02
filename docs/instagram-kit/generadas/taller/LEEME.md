# Serie de proceso — el taller (generada, 2026-09-02)

Seis piezas que cubren el flujo de Indigo. Cubren el hueco que las 14 fotos
reales no cubrían: todas ellas son de obra terminada, ninguna del proceso.

| Pieza | Etapa |
|---|---|
| `T1-digitalizacion.png` | El diseño pasa a archivo CNC |
| `T2-cnc-ancho.png` | Fresadora cortando el panel |
| `T3-pintura-secado.png` | Tres paneles secando: bronce, blanco, negro |
| `T4-control-calidad.png` | Revisión del acabado |
| `T5-listo-para-salir.png` | Paneles envueltos, listos para cargar |
| `T6-medicion.png` | Medición en obra |

Coste: 38.586 + 19.293 tokens (la segunda cifra es rehacer tres, ver abajo).

---

## ⚠️ Son ILUSTRATIVAS

Representan operaciones que Indigo hace de verdad, pero **no son su taller, ni
sus máquinas, ni sus manos**. Valen como imagen de apoyo, igual que una foto de
banco.

**No se pueden publicar con un copy que diga «nuestro taller», «nuestro
equipo» o «así trabajamos».** Eso convierte una imagen ilustrativa en una
afirmación falsa. Copy admisible: describir el proceso en tercera persona
(«every panel is cut to the millimetre»), no señalar la foto como propia.

Para poder decir «este es nuestro taller» hacen falta las fotos que pide el
brief y que siguen sin llegar: taller real, CNC real, el equipo. Una foto de
móvil de Javier vale más que estas seis.

## Dos reglas que se aplicaron, y por qué

**Sin caras.** Manos, antebrazos o espalda. Generar personas reconocibles y
publicarlas como el equipo de Indigo es la línea que no conviene cruzar, y
además las caras de IA en contenido de marca envejecen fatal.

**Sin texto ni logos.** El modelo escribe basura, y cualquier letra legible en
una pieza de marca obliga a descartarla entera.

## T2, T3 y T4 están rehechas

La primera versión (en `../_descartes/`) salió con **filigrana victoriana de
hierro fundido**: hojas de acanto, relieve, volumen. Ese no es el producto de
Indigo. El catálogo real —comprobado contra las 14 fotos— es **plano, cortado
de chapa de espesor uniforme**: rosetones de flor en marco de estrella,
elipses y círculos entrelazados, rectángulos encajados, curvas limpias.

Además el corte salía por plasma, con chispas. Indigo usa **fresadora**.

La corrección fue un bloque de estilo repetido **entero** en los tres prompts.
Repartirlo o abreviarlo deja pasar el acanto otra vez.

Las descartadas se conservan como referencia de en qué se equivoca el modelo
por defecto cuando se le dice «ornamental».

## Sobre las manos

`T4` y `T6` llevan manos, que es lo que arruinó `B6`. La mitigación fue
**guante y una sola mano en cuadro**. En `T6` sale bien; `T4` se rehízo pidiendo
explícitamente una sola mano de dedos distinguibles, y mejoró.

Si hace falta otra pieza con manos, pedir siempre: guante, una sola mano,
entrando por el borde del cuadro.
