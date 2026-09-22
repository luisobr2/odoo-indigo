"""Muro de puertas del catalogo, 1080x1920, para la escena "150+ designs".

Sale del portafolio publico (scraping/output/variant_images/) y solo con
diseños que no han salido en ninguna publicacion (ver REGISTRO-DE-USO.md):
el muro dice "hay muchas", y se vería raro que repitiera las que ya
protagonizaron otro post. Todos de ID31 en adelante, que comparten plantilla
de render, asi que se pegan multiplicando sobre la crema sin recortar a mano
(mismo metodo que carrusel-estilos.py).

Damero de bronce y negro: sin blancas, porque sobre la crema desaparecen.

Uso:  python muro-catalogo.py <salida.png> [dd]
      Con "dd" hace el muro de puertas DOBLES (3x4, otra caja de render).
"""
import pathlib
import sys

from PIL import Image, ImageChops

VARIANTES = pathlib.Path(__file__).resolve().parents[3] / "scraping" / "output" / "variant_images"
CREMA = (250, 249, 246)
CAJA = (300, 58, 725, 963)
DISENOS = [31, 34, 36, 41, 46, 47, 48, 50, 51, 56, 57, 59, 61, 62, 63, 64]
W, H = 1080, 1920
COLS, FILAS = 4, 4
ALTO, HUECO_X, HUECO_Y = 440, 22, 22

# Dobles sin publicar (las de los heroes del reel `entrada`, 46/51/34, fuera).
DD = dict(CAJA=(88, 67, 936, 959), DISENOS=[31, 47, 48, 50, 59, 61, 62, 63, 64, 41, 36, 57],
          COLS=3, FILAS=4, ALTO=420, HUECO_X=24, HUECO_Y=24, SUFIJO="-DD")


def main(salida, dd=False):
    global CAJA, DISENOS, COLS, FILAS, ALTO, HUECO_X, HUECO_Y
    sufijo = "-SD"
    if dd:
        CAJA, DISENOS, COLS, FILAS, ALTO, HUECO_X, HUECO_Y, sufijo = (DD[k] for k in ("CAJA", "DISENOS", "COLS", "FILAS", "ALTO", "HUECO_X", "HUECO_Y", "SUFIJO"))
    lienzo = Image.new("RGB", (W, H), CREMA)
    ancho = round((CAJA[2] - CAJA[0]) * ALTO / (CAJA[3] - CAJA[1]))
    total_w = COLS * ancho + (COLS - 1) * HUECO_X
    total_h = FILAS * ALTO + (FILAS - 1) * HUECO_Y
    x0, y0 = (W - total_w) // 2, (H - total_h) // 2
    for i, n in enumerate(DISENOS):
        fila, col = divmod(i, COLS)
        acabado = "bronze" if (fila + col) % 2 == 0 else "black"
        im = Image.open(VARIANTES / ("ID%02d%s" % (n, sufijo)) / (acabado + ".jpg")).convert("RGB")
        im = im.crop(CAJA).resize((ancho, ALTO), Image.LANCZOS)
        x, y = x0 + col * (ancho + HUECO_X), y0 + fila * (ALTO + HUECO_Y)
        zona = lienzo.crop((x, y, x + ancho, y + ALTO))
        lienzo.paste(ImageChops.multiply(zona, im), (x, y))
    lienzo.save(salida, optimize=True)
    print("muro de %d puertas -> %s" % (len(DISENOS), salida))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], dd=(len(sys.argv) > 2 and sys.argv[2] == "dd"))
