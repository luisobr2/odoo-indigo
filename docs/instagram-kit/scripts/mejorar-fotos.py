"""Mejora fotos REALES de instalacion con gpt-image-2 (/v1/images/edits).

Para que sirve y para que no: las fotos que manda el cliente son de movil,
con luz irregular y algo de ruido. Esto corrige exposicion, color y nitidez.
NO es para cambiar nada de la foto: van en slides que dicen «real installs»,
y una puerta retocada que ya no es la que se instalo seria mentir.

El riesgo, documentado en API-GPT-IMAGE-2.md: /edits no «filtra» la foto, la
REGENERA entera. El ornamento aguanta cuando el encuadre se mantiene —que es
justo este caso—, pero aguantar no es garantia. Por eso este script solo
produce candidatas (`<foto>-mejorada.png`), y verificar-mejoradas.py las
compara con el original antes de que ninguna entre en una publicacion.

Modelo fijado al snapshot probado (gpt-image-2-2026-04-21), no al alias: en
la cuenta ya aparecen gpt-image-2.5-*, sin probar con ornamentos.

La clave se lee de OPENAI_API_KEY; nunca de un archivo del repositorio.

Uso:  python mejorar-fotos.py 16-dd-negra-ovalos-montante-fachada.jpg [...]
      Reanudable: si la mejorada ya existe, la salta.
"""
import base64
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

from PIL import Image

REALES = pathlib.Path(__file__).resolve().parent.parent / "reales"
MODELO = "gpt-image-2-2026-04-21"

PROMPT = (
    "Professionally retouch this real photograph of an installed front door, "
    "the way a real-estate photographer would: balance the exposure, lift "
    "the shadows gently, correct the white balance so whites are neutral, "
    "recover detail, remove noise and sharpen. Natural result, not HDR, not "
    "oversaturated.\n\n"
    "This is documentary proof of a real installation, so the CONTENT must "
    "not change at all. Keep the exact same framing and camera angle. Keep "
    "the door exactly as it is: the same decorative metal pattern over the "
    "glass, stroke for stroke, the same proportions, the same number of "
    "shapes, the same hardware, the same finish colour. Keep the walls, "
    "floor, ceiling, transom, lamps, plants, doorbell and every other object "
    "exactly where they are. Do not add, remove, move, straighten, clean up "
    "or redesign anything. Reflections in the glass stay as they are.\n\n"
    "Absolutely no text, letters, numbers, watermarks or logos."
)


def tamano_para(foto: pathlib.Path) -> str:
    """Misma proporcion que el original, lados multiplos de 16.

    Se apunta a ~1536 en el lado largo: mas resolucion que la caja donde va
    en la slide (970 px de alto), asi que al bajarla queda nitida.
    """
    w, h = Image.open(foto).size
    largo = 1536
    if w >= h:
        W, H = largo, round(largo * h / w)
    else:
        W, H = round(largo * w / h), largo
    return "%dx%d" % (W // 16 * 16, H // 16 * 16)


def editar(foto: pathlib.Path, size: str, clave: str) -> dict:
    boundary = "----indigo%d" % int(time.time() * 1000)
    b = boundary.encode()
    mime = "image/png" if foto.suffix.lower() == ".png" else "image/jpeg"
    partes = []
    for k, v in [("model", MODELO), ("prompt", PROMPT), ("size", size),
                 ("quality", "high"), ("output_format", "png")]:
        partes.append(b"--" + b + b"\r\n"
                      + ('Content-Disposition: form-data; name="%s"\r\n\r\n' % k).encode()
                      + v.encode() + b"\r\n")
    partes.append(b"--" + b + b"\r\n"
                  + ('Content-Disposition: form-data; name="image[]"; filename="%s"\r\n' % foto.name).encode()
                  + ("Content-Type: %s\r\n\r\n" % mime).encode()
                  + foto.read_bytes() + b"\r\n")
    partes.append(b"--" + b + b"--\r\n")
    req = urllib.request.Request(
        "https://api.openai.com/v1/images/edits", data=b"".join(partes),
        headers={"Authorization": "Bearer " + clave,
                 "Content-Type": "multipart/form-data; boundary=" + boundary})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def main():
    clave = os.environ.get("OPENAI_API_KEY", "").strip()
    if not clave:
        sys.exit("Falta OPENAI_API_KEY en el entorno.")
    fotos = sys.argv[1:]
    if not fotos:
        sys.exit(__doc__)

    fallidas = []
    for nombre in fotos:
        foto = REALES / nombre
        destino = foto.with_name(foto.stem + "-mejorada.png")
        if destino.exists():
            print("%-45s ya existe, salto" % nombre, flush=True)
            continue
        size = tamano_para(foto)
        print("%-45s %s ..." % (nombre, size), flush=True)
        t0 = time.time()
        try:
            d = editar(foto, size, clave)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:300]
            print("   FALLO HTTP %s: %s" % (e.code, msg), flush=True)
            fallidas.append(nombre)
            continue
        except Exception as e:  # timeout, red
            print("   FALLO: %s" % str(e)[:300], flush=True)
            fallidas.append(nombre)
            continue
        destino.write_bytes(base64.b64decode(d["data"][0]["b64_json"]))
        u = d.get("usage", {})
        print("   OK en %.0f s  -> %s  (tokens entrada %s, salida %s)"
              % (time.time() - t0, destino.name, u.get("input_tokens"), u.get("output_tokens")), flush=True)

    if fallidas:
        print("\nFallaron: %s" % ", ".join(fallidas), flush=True)


if __name__ == "__main__":
    main()
