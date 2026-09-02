"""Genera la multimedia de Instagram de Indigo Decors con gpt-image-2.

DOS ENDPOINTS, a proposito:

  /v1/images/edits        para producto y escenas -> se le pasa la FOTO REAL
                          de la puerta como referencia. Probado: conserva el
                          ornamento exacto. Describir una filigrana con
                          palabras no se le acerca.
  /v1/images/generations  solo para lo abstracto (fondos, iconos), donde no
                          hay referencia posible.

Reanudable: si el archivo ya existe, lo saltea. Si una pieza falla, sigue
con las demas y lo reporta al final -- 19 imagenes a ~1 minuto cada una es
mucho para perderlo por un timeout.
"""
import base64
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).parent
KEY = (HERE / ".key").read_text(encoding="utf-8").strip()
KIT = pathlib.Path(r"C:\Trabajo\odoo-indigo\docs\instagram-kit")
REF = KIT / "puertas"
OUT = KIT / "generadas"
OUT.mkdir(exist_ok=True)

# Tamanos: gpt-image-2 acepta cualquier medida divisible por 16, asi que se
# pueden pedir proporciones EXACTAS de Instagram en vez de recortar despues.
SQ = "1024x1024"      # 1:1  feed cuadrado
V45 = "1088x1360"     # 4:5  feed vertical (el que mas pantalla ocupa)
V916 = "1152x2048"    # 9:16 stories y reels
# Apaisados y panoramicos: Instagram no los usa, Facebook y LinkedIn si.
LAND = "1200x624"     # feed apaisado de Facebook y LinkedIn (~1.91:1)
FB_COVER = "1632x848" # portada de pagina de Facebook
# LinkedIn pide 1128x384, pero esa medida cae POR DEBAJO del minimo de
# pixeles que acepta la API. Se genera al doble, misma proporcion, y se baja
# de escala al publicar -- que ademas deja el banner con mas resolucion.
LI_COVER = "2272x768" # 2x de ~1136x384 (~3:1)

MARCA = (
    "Brand context: Indigo Decors, a Miami workshop that decorates impact "
    "entry doors. Their product is an ornamental relief design applied over "
    "frosted privacy glass, always the same colour as the door frame. Never "
    "wood grain, never clear glass, never stained glass colours, never a "
    "separate security gate in front. Brand blue #1f4486. Finishes: bronze "
    "#b5895a to #7d5a34, warm off-white #f3f1ea, matte black #1a1a1a. "
    "The brand blue #1f4486 is for GRAPHICS ONLY and must never be used on a "
    "door: doors are only bronze, off-white or black. Keep the finish of the "
    "reference image exactly as it is. "
    "Absolutely no text, letters, words, numbers or logos anywhere in the image."
)

ICONO = (
    "Minimal line icon for a story highlight cover. Perfectly square, centred. "
    "Flat deep navy #0e1f3c background. In the centre, {}, drawn as a clean "
    "line icon in bright blue #0048B4 with one single accent detail in bronze "
    "#b5895a. Thin even stroke, geometric, no fills, no gradients, no shadows. "
    "Generous empty margin. Flat vector style. No text, no letters, no numbers."
)

# (archivo, referencia|None, tamano, prompt)
PIEZAS = [
    # ---- A. Identidad ----
    # A1 (avatar generado) SE ELIMINO. El prompt pedia un arco "como una
    # sonrisa" y el arco real de la marca va al reves, como una cupula: lo
    # generado no era el logo, era otro dibujo. La foto de perfil sale de
    # marca/avatar-navy.png, hecho del logo de verdad.

    ("A2-fondo-cita.png", None, V45,
     "Vertical background for a quote card. Diagonal gradient from deep navy "
     "#0e1f3c to blue #1f4486. A large subtle watercolour texture in lighter "
     "blue bleeds from the top-right corner at low opacity, like ink on wet "
     "paper. One thin bronze #b5895a hairline runs horizontally across the "
     "lower third. The centre is deliberately empty and clean, reserved for "
     "text added later. Elegant, restrained. No text, no letters, no logos."),

    # ---- B. Los 9 primeros posts ----
    ("B1-fachada-doble.png", "ID02-DD.png", V45,
     MARCA + " Place this exact double door, unchanged in design, colour and "
     "proportion, into the entrance of a South Florida home. Light stucco "
     "wall, barrel tile roof, a palm frond entering from the upper left, "
     "tropical planting. Late afternoon sun, warm directional light, soft "
     "long shadows, blue sky. Shot straight on from a slight low angle, 35mm, "
     "background softly out of focus. Photorealistic architectural photograph."),

    ("B2-macro-ornamento.png", "ID13-SD.png", SQ,
     MARCA + " Extreme macro close-up of one corner where the ornamental "
     "relief meets the frosted glass on this door. Keep the exact shape of the "
     "ornament. The relief is dark and matte with a crisp machined edge; the "
     "glass behind is silvery, translucent and softly textured. Raking side "
     "light reveals the thickness of the relief and casts a thin shadow onto "
     "the glass. Fills the frame, tack sharp, shallow depth of field."),

    ("B3-antes-despues.png", "ID06-SD.png", V45,
     MARCA + " TWO SEPARATE SINGLE-LEAF DOORS standing side by side, each one a "
     "complete door with its own frame, clearly separated by a gap. This is "
     "NOT a double door. The door on the RIGHT is the reference door exactly "
     "as given, ornament unchanged. The door on the LEFT is that same door "
     "with its glass completely BARE: identical frame, identical frosted "
     "glass, absolutely no ornament on it, plain and empty. Same size, same "
     "angle, same lighting for both. Neutral light grey studio background, "
     "soft frontal light, gentle shadows beneath. No arrows, no labels."),

    ("B4-cnc.png", None, SQ,
     MARCA + " Photorealistic workshop photograph. A CNC router head mid-cut, "
     "tracing a curved ornamental pattern into a flat panel. Fine dust rises "
     "through the beam of a work lamp. The cut edge is crisp. Machine bed and "
     "clamps visible, industrial but tidy. Cool machine light mixed with a warm "
     "lamp, high contrast, dramatic. Close, slightly above the cutting head, "
     "50mm. Nobody in frame. Gritty and real, not a stock factory photo."),

    ("B5-catalogo-negra.png", "ID13-SD.png", V45,
     MARCA + " Studio product photograph of this exact door, unchanged, shot "
     "perfectly straight on and centred on a seamless white background with a "
     "soft gradient shadow beneath. Even, soft, shadowless product lighting. "
     "The door occupies the central 70% of the frame with clean empty space "
     "above and below. Catalogue quality, photorealistic."),

    ("B6-manos-pintor.png", None, SQ,
     MARCA + " Photorealistic close-up of a craftsman's hands in nitrile "
     "gloves holding a spray gun, laying an even coat of dark bronze finish "
     "onto a door panel lying flat. Fine atomised mist catches the light; the "
     "coated surface is flawless and satin. Shallow depth of field, hands and "
     "nozzle sharp, workshop soft behind. Warm practical lighting. Only hands "
     "and forearms, no face. An honest craft photograph, not a stock model."),

    ("B7-instalacion.png", "ID02-DD.png", V45,
     MARCA + " Documentary photograph of two installers fitting this exact "
     "double door, unchanged, into the opening of a South Florida home. Seen "
     "from outside, slightly wide. One steadies a leaf, the other works at the "
     "hinge side. Everyday work clothes, tools on the ground. Bright midday "
     "Florida light, strong shadows, stucco wall, a hint of palm. Real and "
     "unposed, faces turned away or out of frame. No visible brand logos."),

    ("B8-tres-acabados.png", "ID21-SD.png", SQ,
     MARCA + " CRITICAL: reproduce the ornamental pattern of the reference door "
     "EXACTLY, stroke for stroke, three times. Three copies of that same door "
     "side by side on a seamless light grey background, evenly spaced, all "
     "straight on, all carrying the identical ornament of the reference. The "
     "ONLY difference between them is the finish colour: metallic bronze "
     "brown #b5895a on the left, warm off-white #f3f1ea in the centre, matte "
     "black #1a1a1a on the right. Do not simplify or replace the ornament. "
     "Even soft lighting, consistent floor shadows, symmetrical. No labels."),

    ("B9-vidrio-contraluz.png", "ID08-SD.png", V45,
     MARCA + " Close-up of the frosted privacy glass of this exact door, "
     "photographed from inside the house looking out. Daylight floods through "
     "the textured glass and turns it into a luminous silver sheet; the "
     "ornament on the outside reads as a crisp dark silhouette against that "
     "glow, its shape unchanged. Warm interior shadow at the frame edges. "
     "Serene, minimal, high contrast. Vertical, filling the frame."),

    # ---- C. Portadas de destacadas ----
    ("C1-destacada-catalogo.png", None, SQ,
     ICONO.format("a simple front door seen straight on with a decorative "
                  "swirl on its glass panel")),
    ("C2-destacada-proceso.png", None, SQ,
     ICONO.format("a CNC router head above a flat panel cutting a curved line")),
    ("C3-destacada-instalaciones.png", None, SQ,
     ICONO.format("a house facade reduced to its simplest outline with the "
                  "door highlighted")),
    ("C4-destacada-acabados.png", None, SQ,
     ICONO.format("three small paint swatch squares overlapping in a row")),
    ("C5-destacada-dealers.png", None, SQ,
     ICONO.format("a handshake reduced to two simple interlocking shapes")),

    # ---- D. Plantillas ----
    ("D1-fondo-producto.png", None, V45,
     "Empty vertical background for a product post. Soft gradient from very "
     "light warm grey at the top to pure white at the bottom, with a barely "
     "visible elliptical shadow across the lower third where a product will be "
     "placed. In the top-right corner a very faint large watercolour arc in "
     "pale blue at low opacity, like a watermark. The centre is completely "
     "clean and empty. Nothing else. No text, no objects, no letters."),

    ("D2-fondo-carrusel.png", None, SQ,
     "Empty square background for an educational carousel slide. Flat warm "
     "off-white #f3f1ea with a subtle paper grain. One thin bronze #b5895a "
     "rule across the bottom eighth of the frame. A small faint blue "
     "watercolour smudge in the top-left corner at very low opacity. The whole "
     "centre is empty and clean, reserved for text added later. Nothing else. "
     "No text, no letters, no numbers."),

    ("D3-portada-reel.png", "ID13-SD.png", V916,
     MARCA + " Cinematic vertical cover. This exact door, ornament unchanged, "
     "stands in the lower two thirds, dramatically side-lit from the right: "
     "mostly in shadow with a strong rim of light along its edge and across "
     "the ornament. The upper third fades into near-black empty space reserved "
     "for a headline added later. Moody, cinematic, high contrast."),

    # =================================================================
    # FACEBOOK — publico local y mixto, mas cercano a Instagram.
    # Lo que cambia de verdad: los formatos apaisados y las ZONAS SEGURAS
    # de la portada, donde la interfaz encima el avatar y el nombre.
    # =================================================================
    ("FB1-portada.png", "ID02-DD.png", FB_COVER,
     MARCA + " Wide panoramic architectural photograph. Place this exact "
     "double door, unchanged, in the entrance of a South Florida home, "
     "positioned in the RIGHT half of the frame. The LEFT third must stay "
     "visually calm and uncluttered -- plain sunlit stucco wall and sky, no "
     "detail there -- because a profile picture and the page name are laid "
     "over that area. Barrel tile roof, palms, tropical planting on the right. "
     "Late afternoon sun, warm light, blue sky. Wide, cinematic."),

    ("FB4-taller.png", None, LAND,
     MARCA + " Wide workshop photograph. A CNC router bed seen along its "
     "length, an ornamental curve half cut into a flat panel in the "
     "foreground, the machine gantry receding into a tidy workshop behind. "
     "Fine dust in a shaft of light. Cool machine light with warm lamps, "
     "high contrast. Nobody in frame. Landscape, cinematic, photorealistic. "
     "Real workshop, not a stock factory."),

    ("FB5-detalle.png", "ID21-SD.png", LAND,
     MARCA + " Wide horizontal macro of the ornamental relief on this door "
     "where it meets the frosted glass, keeping the exact shape of the "
     "ornament. The relief runs diagonally across the frame. Raking light "
     "from the left picks out its thickness and casts a thin shadow on the "
     "silvery translucent glass. Extremely sharp, shallow depth of field, "
     "landscape crop."),

    # =================================================================
    # LINKEDIN — le habla a los DEALERS, que son el cliente real. No es
    # la casa sonada: es proceso, precision y capacidad de entrega.
    # =================================================================
    ("LI1-portada.png", None, LI_COVER,
     MARCA + " Very wide panoramic banner, three times wider than tall. The "
     "interior of a clean decorative-door workshop seen across its length: "
     "finished doors standing upright in a row on the right, a work bench "
     "with tools in the middle distance, soft daylight from high windows on "
     "the left. Calm, orderly, professional -- a place where careful work "
     "happens. The LEFT quarter stays uncluttered for a logo laid over it. "
     "Muted, desaturated, documentary. No people."),

    ("LI2-proceso.png", None, LAND,
     MARCA + " Wide photograph of a technician in a clean workshop studying "
     "an ornamental door design on a large monitor, the CNC machine visible "
     "and out of focus behind. The screen shows abstract curved vector "
     "linework with no readable text or numbers. Calm professional lighting, "
     "muted palette. Seen from behind and to the side, face not visible. "
     "Competence and precision, not drama. Landscape."),

    ("LI3-control.png", "ID13-SD.png", LAND,
     MARCA + " Wide photograph of this exact door, unchanged, standing "
     "upright in a workshop while a pair of gloved hands checks the edge of "
     "its ornamental relief with a straight edge. Only hands and forearms, no "
     "face. Clean bench, good light, tools set down neatly. The message is "
     "quality control before delivery. Landscape, photorealistic, honest."),

    ("LI4-fondo-dato.png", None, LAND,
     "Wide empty background for a corporate statistic post. Deep navy #0e1f3c "
     "to blue #1f4486 diagonal gradient. A very subtle watercolour texture in "
     "lighter blue bleeds from the right edge at low opacity. One thin bronze "
     "#b5895a hairline runs vertically down the right third. The left two "
     "thirds are completely empty and clean, reserved for a large figure and "
     "a line of text added later. Restrained, corporate, premium. Landscape. "
     "No text, no letters, no numbers, no logos."),

    ("LI5-precision.png", "ID06-SD.png", LAND,
     MARCA + " Wide extreme close-up of the machined edge of the ornamental "
     "relief on this door, keeping the ornament's exact shape, where it meets "
     "the frosted glass. The cut edge is crisp and clean, the finish flawless "
     "and satin. Strong raking light along the length of the frame reveals "
     "the depth of the relief. Almost abstract, industrial elegance. "
     "Landscape, tack sharp."),
]


def post(url, data, headers, timeout=600):
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def generar(prompt, size):
    body = json.dumps({
        "model": "gpt-image-2", "prompt": prompt, "size": size,
        "quality": "high", "output_format": "png",
    }).encode()
    return post("https://api.openai.com/v1/images/generations", body,
                {"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})


def editar(prompt, size, ref_path):
    """multipart a mano: no hay requests instalado y esto no justifica una dep."""
    boundary = "----indigo" + str(int(time.time() * 1000))
    b = boundary.encode()
    parts = []
    for k, v in [("model", "gpt-image-2"), ("prompt", prompt),
                 ("size", size), ("quality", "high")]:
        parts.append(b"--" + b + b"\r\n"
                     + ('Content-Disposition: form-data; name="%s"\r\n\r\n' % k).encode()
                     + v.encode() + b"\r\n")
    parts.append(b"--" + b + b"\r\n"
                 + ('Content-Disposition: form-data; name="image[]"; filename="%s"\r\n'
                    % ref_path.name).encode()
                 + b"Content-Type: image/png\r\n\r\n"
                 + ref_path.read_bytes() + b"\r\n")
    parts.append(b"--" + b + b"--\r\n")
    body = b"".join(parts)
    return post("https://api.openai.com/v1/images/edits", body,
                {"Authorization": "Bearer " + KEY,
                 "Content-Type": "multipart/form-data; boundary=" + boundary})


def main():
    solo = sys.argv[1] if len(sys.argv) > 1 else None
    tokens_out = tokens_in = 0
    hechas = saltadas = []
    hechas, saltadas, fallidas = [], [], []

    for nombre, ref, size, prompt in PIEZAS:
        if solo and solo not in nombre:
            continue
        destino = OUT / nombre
        if destino.exists() and destino.stat().st_size > 10000:
            saltadas.append(nombre)
            print("  saltada (ya existe): %s" % nombre, flush=True)
            continue
        t0 = time.time()
        try:
            if ref:
                d = editar(prompt, size, REF / ref)
            else:
                d = generar(prompt, size)
            destino.write_bytes(base64.b64decode(d["data"][0]["b64_json"]))
            u = d.get("usage", {})
            tokens_out += u.get("output_tokens", 0)
            tokens_in += u.get("input_tokens", 0)
            hechas.append(nombre)
            print("  OK %-32s %s  %5.0fs  %s tokens%s"
                  % (nombre, size, time.time() - t0, u.get("output_tokens", 0),
                     "  (ref: %s)" % ref if ref else ""), flush=True)
        except urllib.error.HTTPError as e:
            detalle = e.read().decode("utf-8", "replace")[:200]
            fallidas.append((nombre, detalle))
            print("  FALLO %-30s %s" % (nombre, detalle), flush=True)
        except Exception as e:  # noqa: BLE001
            fallidas.append((nombre, str(e)[:200]))
            print("  FALLO %-30s %s" % (nombre, str(e)[:200]), flush=True)

    print("\n=== RESUMEN ===")
    print("generadas: %s | ya existian: %s | fallidas: %s"
          % (len(hechas), len(saltadas), len(fallidas)))
    print("tokens de salida (imagen): %s | de entrada: %s" % (tokens_out, tokens_in))
    for n, err in fallidas:
        print("  ! %s -> %s" % (n, err))


if __name__ == "__main__":
    main()
