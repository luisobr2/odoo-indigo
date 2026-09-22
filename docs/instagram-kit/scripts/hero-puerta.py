"""Toma de heroe de una puerta del catalogo: estudio oscuro, foco y reflejo.

Para un anuncio la puerta tiene que llenar la pantalla y tener luz de
producto, no de foto de movil. Los renders del portafolio publico traen la
puerta sobre blanco puro, asi que se recorta con un alfa sacado del propio
render (lo que no es blanco es puerta) y se monta sobre un fondo navy casi
negro con un foco calido detras y un reflejo en el suelo. Nada lo dibuja una
IA: el ornamento es el del render, pixel a pixel.

Uso:  python hero-puerta.py <CODIGO> <bronze|black> <salida.png> [zoom] [centro_y]
      Con SRC=<ruta.png> en el entorno usa esa imagen (p. ej. el render ampliado
      a 4k con Higgsfield) en vez del jpg del portafolio: el render original es
      de 1024 px y a pantalla entera, con el movimiento de camara, se veia blando.
      zoom: fraccion de la altura del lienzo que ocupa la puerta (defecto 0.62)
      centro_y: donde queda el centro de la puerta (defecto 0.50; 0.58 deja el
                tercio superior libre para un titular)
"""
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageFilter

VARIANTES = __import__("pathlib").Path(__file__).resolve().parents[3] / "scraping" / "output" / "variant_images"
W, H = 1080, 1920
NAVY_DEEP = np.array([6, 12, 24], dtype=np.float32)
NAVY = np.array([14, 31, 60], dtype=np.float32)
BRONCE = np.array([181, 137, 90], dtype=np.float32)


def recorte(codigo, acabado):
    src = os.environ.get("SRC") or (VARIANTES / codigo / (acabado + ".jpg"))
    im = Image.open(src).convert("RGB")
    caja = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).convert("L") \
        .point(lambda v: 255 if v > 24 else 0).getbbox()
    im = im.crop(caja)
    a = np.asarray(im, dtype=np.float32)
    # Alfa: cuanto se aleja del blanco. La puerta (oscura) satura a 255; el
    # antialias del borde queda parcial; la sombra gris del render se descarta
    # por umbral, que en el fondo oscuro se veria como un halo claro.
    dist = 255 - a.min(axis=2)
    alfa = np.clip((dist - 30) / 60, 0, 1) * 255
    rgba = np.dstack([a, alfa]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def fondo():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # Foco calido detras de la puerta, algo por encima del centro.
    d = np.hypot((xx - W / 2) / (W * 0.62), (yy - H * 0.42) / (H * 0.42))
    foco = np.clip(1 - d, 0, 1) ** 1.6
    base = NAVY_DEEP[None, None, :] + (NAVY - NAVY_DEEP)[None, None, :] * foco[..., None] * 1.15
    base += BRONCE[None, None, :] * (foco[..., None] ** 2) * 0.18
    # Suelo: banda algo mas clara en el ultimo tercio, para que el reflejo se lea.
    suelo = np.clip((yy - H * 0.70) / (H * 0.30), 0, 1)
    base += (NAVY - NAVY_DEEP)[None, None, :] * suelo[..., None] * 0.35
    # Grano fino: un degradado limpio de navy a negro hace BANDAS al pasar por
    # el codec del video (H.264 a 1080p no tiene bits para 30 tonos casi
    # iguales). Un ruido de +-2 los rompe y ademas da textura de pared.
    rng = np.random.default_rng(7)
    base += rng.normal(0, 2.2, base.shape).astype(np.float32)
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")


def main(codigo, acabado, salida, zoom=0.62, centro_y=0.50):
    puerta = recorte(codigo, acabado)
    alto = round(H * zoom)
    ancho = round(puerta.width * alto / puerta.height)
    puerta = puerta.resize((ancho, alto), Image.LANCZOS)
    lienzo = fondo().convert("RGBA")
    x, y = (W - ancho) // 2, round(H * centro_y - alto / 2)

    # Sombra de contacto bajo la puerta.
    sombra = Image.new("L", (W, H), 0)
    from PIL import ImageDraw
    ImageDraw.Draw(sombra).ellipse((x - 30, y + alto - 26, x + ancho + 30, y + alto + 26), fill=200)
    sombra = sombra.filter(ImageFilter.GaussianBlur(24))
    lienzo = Image.composite(Image.new("RGBA", (W, H), (0, 0, 0, 255)), lienzo, sombra)

    # Reflejo: la puerta volteada, desvanecida hacia abajo y algo desenfocada.
    ref = puerta.transpose(Image.FLIP_TOP_BOTTOM)
    grad = np.linspace(0.42, 0.0, ref.height, dtype=np.float32)[:, None]
    ra = np.asarray(ref, dtype=np.float32)
    ra[..., 3] *= grad
    ref = Image.fromarray(ra.astype(np.uint8), "RGBA").filter(ImageFilter.GaussianBlur(2))
    lienzo.alpha_composite(ref, (x, y + alto + 4))

    lienzo.alpha_composite(puerta, (x, y))
    lienzo.convert("RGB").save(salida, optimize=True)
    print("%s %s -> %s  (puerta %dx%d)" % (codigo, acabado, salida, ancho, alto))


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3],
         float(sys.argv[4]) if len(sys.argv) > 4 else 0.62,
         float(sys.argv[5]) if len(sys.argv) > 5 else 0.50)
