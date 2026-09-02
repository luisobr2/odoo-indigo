"""Arma B3 (antes/despues) y B8 (tres acabados) COMPONIENDO, no generando.

Por que: gpt-image-2 con /edits conserva el ornamento de la referencia con
fidelidad total mientras haya UNA puerta en la salida. En cuanto se le piden
dos o tres copias en la misma imagen, lo pierde y se inventa una filigrana
geometrica -- probado dos veces con instrucciones cada vez mas enfaticas.

Asi que se genera cada puerta por separado (donde el modelo es fiable) y el
montaje se hace aca, que ademas es determinista: las tres quedan exactamente
del mismo tamano y perfectamente alineadas, cosa que un generador no
garantiza nunca.
"""
import base64
import json
import pathlib
import time
import urllib.request

from PIL import Image

HERE = pathlib.Path(__file__).parent
KEY = (HERE / ".key").read_text(encoding="utf-8").strip()
KIT = pathlib.Path(r"C:\Trabajo\odoo-indigo\docs\instagram-kit")
OUT = KIT / "generadas"
PIEZAS = OUT / "_piezas"          # intermedias, no son entregables
PIEZAS.mkdir(exist_ok=True)

BASE = (
    "Studio product photograph of this exact door, shot perfectly straight on "
    "and centred on a seamless pure white background with a soft shadow "
    "beneath. Even, soft, shadowless product lighting. The door fills most of "
    "the frame. Photorealistic, catalogue quality. Never wood grain, never "
    "clear glass. No text, letters, numbers or logos anywhere."
)

VARIANTES = [
    ("bare.png", "ID13-SD.png",
     BASE + " CHANGE ONE THING ONLY: remove the ornamental design from the "
     "glass completely, leaving a plain empty frosted glass panel. Keep the "
     "frame, the colour, the handle, the hinges and the proportions identical."),
    ("bronce.png", "ID13-SD.png",
     BASE + " CHANGE ONE THING ONLY: the finish colour becomes a metallic "
     "bronze brown (#b5895a shading to #7d5a34). The ornamental design on the "
     "glass must stay EXACTLY as it is, same shape, now in that bronze."),
    ("blanca.png", "ID13-SD.png",
     BASE + " CHANGE ONE THING ONLY: the finish colour becomes a warm "
     "off-white (#f3f1ea). The ornamental design on the glass must stay "
     "EXACTLY as it is, same shape, now in that off-white."),
]


def editar(prompt, ref, size="1088x1360"):
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
                    % ref.name).encode()
                 + b"Content-Type: image/png\r\n\r\n" + ref.read_bytes() + b"\r\n")
    parts.append(b"--" + b + b"--\r\n")
    req = urllib.request.Request(
        "https://api.openai.com/v1/images/edits", data=b"".join(parts),
        headers={"Authorization": "Bearer " + KEY,
                 "Content-Type": "multipart/form-data; boundary=" + boundary})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def recortar_puerta(img):
    """Recorta al contenido: el generador deja margenes blancos distintos en
    cada imagen y sin esto las puertas quedan de tamanos dispares."""
    gris = img.convert("L")
    # Todo lo que no sea casi blanco es puerta.
    mascara = gris.point(lambda p: 255 if p < 246 else 0)
    caja = mascara.getbbox()
    return img.crop(caja) if caja else img


def montar(fuentes, destino, size, fondo=(255, 255, 255)):
    imgs = [recortar_puerta(Image.open(f).convert("RGB")) for f in fuentes]
    W, H = size
    hueco = int(H * 0.80)                     # alto util de cada puerta
    esc = [im.resize((int(im.width * hueco / im.height), hueco), Image.LANCZOS)
           for im in imgs]
    total = sum(im.width for im in esc)
    sep = (W - total) // (len(esc) + 1)
    if sep < 8:                               # no entran: achicar parejo
        f = (W - 8 * (len(esc) + 1)) / total
        esc = [im.resize((int(im.width * f), int(im.height * f)), Image.LANCZOS)
               for im in esc]
        total = sum(im.width for im in esc)
        sep = (W - total) // (len(esc) + 1)
    lienzo = Image.new("RGB", size, fondo)
    x = sep
    y = (H - esc[0].height) // 2
    for im in esc:
        lienzo.paste(im, (x, y + (esc[0].height - im.height)))
        x += im.width + sep
    lienzo.save(destino)
    print("  montada", destino.name, lienzo.size)


def main():
    for nombre, ref, prompt in VARIANTES:
        destino = PIEZAS / nombre
        if destino.exists() and destino.stat().st_size > 10000:
            print("  ya existe:", nombre)
            continue
        t0 = time.time()
        d = editar(prompt, KIT / "puertas" / ref)
        destino.write_bytes(base64.b64decode(d["data"][0]["b64_json"]))
        print("  OK %-14s %4.0fs  %s tokens" % (nombre, time.time() - t0,
                                                d["usage"]["output_tokens"]))

    negra = OUT / "B5-catalogo-negra.png"
    bare, bronce, blanca = (PIEZAS / n for n in ("bare.png", "bronce.png", "blanca.png"))

    # Instagram: vertical y cuadrado.
    montar([bare, negra], OUT / "B3-antes-despues.png", (1088, 1360))
    montar([bronce, blanca, negra], OUT / "B8-tres-acabados.png", (1024, 1024))

    # Facebook y LinkedIn: los mismos mensajes en apaisado. Se reusan las
    # puertas ya generadas -- el montaje no cuesta tokens, asi que cada
    # formato nuevo sale gratis.
    montar([bare, negra], OUT / "FB2-antes-despues.png", (1200, 624))
    montar([bronce, blanca, negra], OUT / "FB3-tres-acabados.png", (1200, 624))


if __name__ == "__main__":
    main()
