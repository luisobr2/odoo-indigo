# Indigo Decors — Contexto de marca para generación de imágenes con IA

> **Cómo usar este documento.** Está escrito para pegarse como contexto en un
> agente de IA generador de imágenes (ChatGPT/DALL·E, Midjourney, Firefly,
> Nano Banana, Flux, etc.) antes de pedirle piezas. Los prompts concretos
> están en `PROMPTS.md`. Las imágenes de referencia están en `marca/` y
> `puertas/`.
>
> Todo lo que dice este documento sobre el negocio está verificado contra el
> sistema de producción de la empresa al 2026-08-24, no inventado. Donde algo
> **no** está confirmado, se dice explícitamente.

---

## 1. Qué es la empresa

**Indigo Decors** (razón social: *Indigo Publicity Corp.*) es un taller de
**Miami, Florida** que **decora puertas de impacto**: corta, pinta e instala
piezas decorativas —tipo herrería ornamental— sobre puertas de entrada.

No fabrica la puerta: la **transforma**. La puerta entra lisa y sale con un
diseño ornamental sobre el vidrio.

**Dato clave para el tono de las piezas:** el cliente principal **no es el
dueño de casa**, son **dealers** (Lock Tight, USA Windows, Safeguard Impact,
Impact Brothers, entre 11 activos) que venden e instalan puertas de impacto y
subcontratan la decoración. El consumidor final ve el resultado, pero quien
compra es un profesional del rubro.

| Dato | Valor |
|---|---|
| Ubicación | 2192 NW 26th Ave, Miami, FL 33142 |
| Teléfono | +1 786-302-2732 |
| Email | sales@indigodecors.com |
| Web | https://www.indigodecors.com |
| Mercado | Sur de Florida (Miami-Dade, Broward y alrededores) |
| Idioma | Inglés y español (Miami bilingüe) |

**Escala real (no inflar en el contenido):** 259 órdenes en el sistema, **185
puertas instaladas**, 11 dealers activos, catálogo de **163 diseños**. Es un
taller especializado, no una fábrica industrial. El contenido debe sentirse
**artesanal y preciso**, no corporativo masivo.

---

## 2. Identidad visual

### Logo

Archivos: `marca/logo-indigo-decors.png` (1920×1217, RGBA con transparencia)
y `.webp` (mismo archivo).

**Descripción para la IA:** un **arco de acuarela azul** pintado con pincel
—desde azul marino profundo hasta cian brillante, con textura de aguada,
salpicaduras y bordes irregulares— que se arquea sobre el wordmark. Debajo,
la palabra **"indigo"** en minúsculas, tipografía sans-serif muy pesada, azul
oscuro sólido; y a la derecha **"DECORS"** en mayúsculas más pequeñas, mismo
azul.

**Variantes, y por qué existen.** El logo original es **oscuro**
(luminosidad media 68/255) y **apaisado** (1.58:1). O sea: sobre los fondos
navy del kit sería casi invisible, y un recorte cuadrado para foto de perfil
lo corta. Por eso hay tres archivos más:

- `logo-blanco.png` — versión en blanco para fondos oscuros. No está pintado
  de blanco a secas: la textura de la acuarela vive en la **variación** de
  color y aplanarla la mata, así que se usa la oscuridad de cada píxel como
  opacidad del blanco. La aguada se conserva, invertida.
- `avatar-claro.png` / `avatar-navy.png` — cuadrados 1024×1024 para foto de
  perfil. Llevan el logo **completo**: el arco y el wordmark se solapan
  verticalmente, así que no existe un corte que deje solo el arco sin
  serrarle la cola.

**Reglas del logo:**
- Va **sobre fondo claro o sobre fondo navy oscuro**, nunca sobre una foto con
  ruido detrás del wordmark.
- **No recolorear, no rotar, no aplicar degradados encima.**
- El arco de acuarela es el elemento distintivo: si hace falta un ícono
  suelto, se usa el arco solo, sin el texto.
- Espacio libre alrededor: al menos la altura de la "i" de "indigo".

### Paleta

**Leé la columna "verificado" antes de usar un color.** No todo lo que
circula en documentos de la marca está realmente en uso.

#### Colores confirmados

| Rol | Hex | Verificado en |
|---|---|---|
| **Azul de marca** | `#1f4486` | El sitio indigodecors.com — 58 usos en el CSS del tema. Es *el* color de la empresa. |
| **Azul del wordmark** | `#002478` | Muestreado del archivo de logo. Es el azul de las letras "indigo", más puro y saturado que el anterior. |
| Azul del arco (medio) | `#0048B4` | Muestreado del logo |
| Azul del arco (claro) | `#0060C0` | Muestreado del logo |
| Azul oscuro secundario | `#162e5c` | CSS del tema |

**Ojo con esto:** el azul del logo (`#002478`) y el azul del sitio (`#1f4486`)
**no son el mismo color**. El del logo es más puro; el del sitio, más grisáceo.
Para piezas donde el logo aparece grande, usá la familia del logo. Para fondos
y elementos de interfaz, `#1f4486`.

#### Colores NO confirmados

Estos vienen del brief de marca que preparó la agencia, **no del material de
la empresa**. No aparecen ni una vez en el sitio. Sirven como sugerencia
coherente, pero no los presentes como identidad de Indigo:

`#0d1830` navy · `#132449` navy2 · `#3862b8` indigo claro ·
`#b0813f` bronce · `#f6efe4` fondo cálido

Si hace falta un navy de fondo, oscurecé el `#1f4486` real en vez de importar
uno inventado.

### Tipografía

La marca no tiene una tipografía comprada. Para las piezas: **sans-serif
geométrica o grotesca, de peso alto** para titulares (Inter, Poppins,
Montserrat o similar), en mayúsculas o sentence case. Nada de scripts,
caligráficas ni serifas decorativas — chocan con el wordmark.

---

## 3. El producto (lo que hay que saber para no dibujar mal una puerta)

### Tipos

| Tipo | Qué es |
|---|---|
| **Single Door (SD)** | Una hoja |
| **Double Door (DD)** | Dos hojas simétricas |
| **Door with Sidelites** | Hoja central con paneles fijos de vidrio a los lados |

### Colores de acabado — los hex REALES del producto

Estos salen de los selectores de color de indigodecors.com, o sea son los
colores con los que la empresa le muestra al cliente cómo queda su puerta.
**Usá estos, no un bronce genérico.**

| Acabado | Hex | Órdenes | Nota |
|---|---|---|---|
| **Bronze** | `#b5895a` → `#7d5a34` (degradado) | **152** | El más vendido con diferencia. Es un **marrón metálico**, no dorado ni cobre brillante. |
| **White** | `#f3f1ea` | 108 | Blanco cálido, tirando a hueso. No es blanco puro. |
| **Black** | `#1a1a1a` | 9 | Poco frecuente. Negro mate, no azabache. |

Que el bronce sea un degradado de `#b5895a` a `#7d5a34` importa: la puerta
tiene esa variación metálica según cómo le pega la luz. Un bronce plano se ve
falso.

### Cómo es una puerta Indigo — CRÍTICO

Mirá `puertas/` antes de generar nada. Las referencias reales muestran:

- **Marco y hoja de color sólido** (bronce oscuro, blanco o negro), superficie
  con textura sutil tipo fibra de vidrio, **no madera vetada**.
- **Un panel grande de vidrio esmerilado / privacidad** ocupando casi toda la
  hoja: translúcido, gris plateado, **no transparente y no espejado**.
- Sobre ese vidrio, un **diseño ornamental en relieve** del mismo color que la
  puerta: curvas, espirales, arcos entrelazados, líneas geométricas. Es el
  producto. Parece herrería forjada pero es aplicado.
- **Herrajes finos**, manija de palanca alargada en níquel o bronce cepillado.
- Bisagras visibles en el canto.

**Errores que arruinan la imagen (evitar siempre):**
- Puertas de **madera** con vetas.
- **Vidrio transparente** que deja ver el interior.
- Vitrales de **colores** (esto no es vitral, el ornamento es del color de la
  puerta).
- Rejas de seguridad **por delante** de la puerta — el diseño está *sobre el
  vidrio*, integrado.
- Puertas de garaje, portones, puertas de interior.
- Texto o letras generadas dentro de la imagen (ver §5).

### El proceso (material para contenido "detrás de escena")

```
Orden → Diseño → Medición → Digitalización → Corte CNC/Router
      → Pintura → Instalación
```

Etapas reales y visualmente ricas: la **máquina CNC cortando** el ornamento,
la **cabina de pintura**, la **instalación en obra**. Son las escenas más
honestas para contenido de taller.

---

## 3.bis Qué cambia en cada red

No es el tamaño: es a quién le habla la pieza.

| Red | Quién mira | Qué mostrarle |
|---|---|---|
| **Instagram** | Dueños de casa, descubrimiento visual | El resultado. Fachadas, detalle, antes/después. |
| **Facebook** | Local de Miami, servicios para el hogar | Lo mismo que Instagram pero apaisado, y más cercano: obra, taller, gente. |
| **LinkedIn** | **Los dealers — el cliente real** | Proceso, precisión, control de calidad, capacidad de entrega. **No** la casa soñada. |

Esa diferencia es la razón por la que las piezas de LinkedIn son taller y
banco de trabajo en vez de palmeras: quien compra es un profesional del rubro
que necesita saber que Indigo entrega bien y a tiempo.

## 4. Tono y posicionamiento

**Lo que la marca es:** precisa, artesanal, orgullosa del oficio. Transforma
una puerta funcional en la primera impresión de una casa.

**Cómo hablar:** directo y concreto. Muestra el trabajo. Antes/después.
Detalle del corte. Nada de superlativos vacíos ni lenguaje de agencia.

**Lo que la marca NO es:**
- No es lujo europeo aspiracional ni mansiones de revista.
- No es industrial barato ni de volumen.
- No es marketing agresivo de descuentos.

**Ambientación correcta para escenas:** arquitectura residencial del sur de
Florida — estuco claro, techo de teja o plano, palmeras, luz cálida y fuerte,
cielo azul. **No** casas de ladrillo del noreste, ni chalets, ni nieve.

---

## 5. Reglas técnicas para el generador

1. **No pidas texto dentro de la imagen.** Los generadores deforman letras. El
   copy y el logo se superponen después en el editor. Si el prompt necesita
   espacio para texto, pedí **espacio negativo limpio**, no el texto.
2. **Formatos de Instagram:** feed cuadrado `1080×1080` (1:1), feed vertical
   `1080×1350` (4:5, el que más pantalla ocupa), stories y reels
   `1080×1920` (9:16).
3. **Zona segura:** dejá márgenes libres arriba y abajo en los 9:16 — la
   interfaz de Instagram tapa esas franjas.
4. **Consistencia entre piezas:** una cuenta se ve profesional cuando todos los
   posts comparten iluminación y encuadre. Repetí la misma descripción de luz
   en todos los prompts de una tanda.
5. **Fotorrealismo para producto, ilustración plana para educativos.** No
   mezclar los dos estilos en la misma pieza.
6. **Usá las referencias.** Si el generador acepta imagen de referencia,
   pasale una de `puertas/` — describir un ornamento con palabras es mucho
   menos fiable que mostrarlo.

---

## 6. Inventario de este kit

```
instagram-kit/
├─ CONTEXTO-MARCA.md      ← este archivo
├─ PROMPTS.md             ← los prompts listos para pegar
├─ marca/
│  ├─ logo-indigo-decors.png    (1920×1217, transparente, ORIGINAL)
│  ├─ logo-blanco.png           (para fondos oscuros — ver abajo)
│  ├─ avatar-claro.png          (1024², logo sobre blanco)
│  └─ avatar-navy.png           (1024², logo blanco sobre navy)
├─ generadas/                   ← LAS 29 PIEZAS YA GENERADAS
│  ├─ Instagram: A1-A2 · B1-B9 · C1-C5 · D1-D3
│  ├─ Facebook:  FB1 portada · FB2-FB5 feed apaisado
│  ├─ LinkedIn:  LI1 portada · LI2-LI5 feed apaisado
│  └─ _piezas/  (puertas sueltas usadas para componer B3 y B8)
├─ scripts/
│  ├─ generar-instagram.py      (llama a gpt-image-2, reanudable)
│  └─ componer-variantes.py     (variantes de color + montaje)
├─ API-GPT-IMAGE-2.md           ← cómo se generó, con los límites hallados
└─ puertas/                     (fotos reales de producto, 1024×1024)
   ├─ ID01-SD.png   ID06-SD.png   ID08-SD.png
   ├─ ID13-SD.png   ID21-SD.png   ID26-SD.png
   └─ ID02-DD.png   ID19-DD.png   ID38-DD.png
```

Las 9 puertas son **producto real de la empresa**, elegidas entre las más
vendidas: 6 simples y 3 dobles, en bronce oscuro y blanco.

---

## 7. Lo que NO está confirmado

Honestidad sobre los huecos, para que nadie los invente:

- **No hay fotos de obra terminada ni de instalación real** en este kit. Las 9
  imágenes son de catálogo sobre fondo blanco. Cualquier escena de casa habrá
  que generarla o fotografiarla.
- **No hay fotos del taller, del equipo ni de la máquina CNC.** Son el mejor
  material posible para redes y hay que salir a tomarlas.
- **No hay testimonios ni casos con nombre de cliente** autorizados.
- **La tipografía de marca no está definida** — la recomendación de §2 es
  criterio, no una decisión de la empresa.
- **No hay manual de marca formal.** Por eso §2 separa los colores
  confirmados de los que no lo están: de la paleta que circula en el brief,
  el único que aparece en el material real de la empresa es `#1f4486`. El
  resto lo eligió la agencia para ese documento.
- **El azul del logo y el del sitio no coinciden** (`#002478` vs `#1f4486`).
  Nadie decidió cuál manda; hasta que alguien lo haga, §2 dice cuándo usar
  cada uno.
- **83 de 162 productos no están publicados** en indigodecors.com, así que
  buena parte del catálogo no es visible públicamente hoy.
