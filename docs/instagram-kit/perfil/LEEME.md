# Actualizar el perfil de Instagram — @indigo.decors

Todo lo que hace falta para dejar el perfil montado. Los archivos de esta
carpeta ya están en el orden en que se usan.

**Qué se puede hacer desde el ordenador y qué no:**

| Tarea | Ordenador (instagram.com) | Teléfono |
|---|---|---|
| Foto de perfil, nombre, bio, enlace | Sí | Sí |
| Categoría y datos de contacto | Sí (cuenta profesional) | Sí |
| **Historias destacadas** | **No** | **Sí, solo aquí** |
| Fijar publicaciones | No | Sí |

Las destacadas y los posts fijados son lo único que obliga a coger el móvil.
Manda esta carpeta al teléfono (AirDrop, Drive o Telegram a ti mismo) antes de
empezar.

---

## 1. Foto de perfil

`01-foto-de-perfil.png` — el logo completo sobre navy, 1024×1024.

Es la versión **navy** y no la clara a propósito: la interfaz de Instagram es
blanca, así que un avatar de fondo blanco pierde el borde del círculo y el logo
queda flotando sin forma. El navy recorta un disco nítido. Comprobado
renderizando ambas a los tamaños reales de Instagram (110 px en el perfil,
32 px junto a cada publicación).

El recorte de Instagram es circular. Este archivo está verificado: nada del
logo se sale del círculo.

## 2. Textos del perfil

**Nombre** (el campo que se busca, 30 caracteres — usa 21):

```
Indigo Decors · Miami
```

**Bio** (150 caracteres — usa 125):

```
Your home's first impression.
Decorative designs for impact doors — cut, painted & installed in Miami.
Bronze · White · Black
```

En inglés porque es el idioma de todo el contenido del calendario. La línea
uno es la misma frase con la que cierra el vídeo `intro`, así que perfil y
contenido dicen lo mismo.

**Enlace:** `https://www.indigodecors.com`

**Categoría:** Home Improvement (o Home Decor). Evita "Contractor": Indigo no
instala la puerta, la decora.

**Datos de contacto:**

- Email: `sales@indigodecors.com`
- Teléfono: `+1 786-302-2732`
- Dirección: `2192 NW 26th Ave, Miami, FL 33142`

> Sobre la dirección: es pública en indigodecors.com, así que ponerla no
> revela nada nuevo. Pero publicarla en Instagram sí invita a que un dueño de
> casa se presente en el taller, y el cliente de Indigo es el dealer, no él.
> Si eso molesta, deja email y teléfono y quita la dirección.

## 3. Historias destacadas (solo desde el móvil)

Cinco portadas en `destacadas/`, generadas en la misma tanda para que se vean
como un juego.

**No son los archivos `C1`–`C5` tal cual.** En los originales el icono ocupa
la mitad del cuadro, y una destacada se muestra en un círculo de unos 60 px:
eso dejaba iconos de ~30 px, ilegibles. Están reencuadrados para que en las
cinco el punto más lejano del icono quede a la misma distancia del borde
(82 % del radio), que es lo que hace que se vean como juego y no como cinco
piezas sueltas. Comprobado a 60 px reales: nada se sale del círculo.

Los originales siguen intactos en `generadas/`.

| Archivo | Destacada | Qué va dentro |
|---|---|---|
| `1-catalog.png` | Catalog | Vídeos `dw-id*` + `reales/14`, `reales/08`, `reales/07` |
| `2-process.png` | Process | **Serie `generadas/taller/` T1-T6** + `taller-vertical.mp4`, `reales/12` |
| `3-installs.png` | Installs | **`reales/10`, `11`, `04`, `09`, `08`** — fotos reales |
| `4-finishes.png` | Finishes | `B8-tres-acabados.png` + `reales/14` (negro) y `reales/11` (blanco) |
| `5-dealers.png` | Dealers | `portal-horizontal.mp4`, el one-pager |

Las fotos reales están en `../reales/` y su LEEME dice cuáles se pueden
publicar y cuáles no. **Ojo: falta pedir permiso a los dealers** antes de
publicar la instalación de un cliente suyo.

**Una destacada no existe sin al menos una historia dentro.** El orden es:

1. Publica una historia (vale cualquier pieza del bloque que toque).
2. Perfil → **+** debajo de la bio → Historia destacada → selecciónala.
3. Ponle nombre (una palabra, se corta sobre los 10 caracteres).
4. **Editar portada** → elige de la galería → el PNG de esta carpeta.

Repite las cinco. Instagram las ordena por la última actualización, así que
créalas en orden inverso (Dealers primero, Catalog al final) si quieres que
Catalog quede a la izquierda.

## 4. Publicaciones para fijar

En `fijar/`, en el orden en que deben quedar. Instagram permite fijar tres.

| Archivo | Por qué |
|---|---|
| `1-intro-who-we-are.mp4` | La pieza de presentación. Quien llega al perfil sin saber qué es Indigo, lo sabe en 30 s |
| `2-transformacion.mp4` | El antes/después: lo que la empresa hace, en una toma |
| `3-temporada.mp4` | "Impact-rated doesn't have to mean plain" — estacional, pico de huracanes |

Los copys y hashtags de cada uno ya están escritos en
`C:\merktop\video-production\output\indigo\metadata\<pieza>.txt`, y los
subtítulos en `srt/`. Súbelos con el vídeo.

Para fijar: publica → en el post, **⋯** → *Fijar en tu perfil*.

## 5. Qué NO poner todavía

- Los números (185 instaladas · 163 diseños · 11 dealers) y los nombres de
  dealers están **pendientes del OK del cliente** (ver `CALENDARIO-EDITORIAL.md`).
  No van en la bio ni en las destacadas hasta que Majela confirme.
- Piezas descartadas por defectos: **B7, B9, LI1, LI3**. No usar.
- `B6-manos-pintor.png` tiene una mano mal generada. No publicar sin
  sustituirla por una foto real.

---

Fuente de todo: `docs/instagram-kit/`. Contexto de marca en
`CONTEXTO-MARCA.md`, calendario en `CALENDARIO-EDITORIAL.md`.
