"""Monta un render de puerta (recortado) sobre un fondo generado por IA.

La IA hace la CASA (un recibidor, una fachada) con un hueco de pared liso
donde va la puerta, y la puerta es siempre el render real del catalogo:
la IA nunca dibuja el ornamento. Tres extras opcionales, para el video de
privacidad («light in, eyes out»):

  --sombra    proyecta el ornamento en el suelo, hacia la camara, como si el
              sol entrara por el vidrio: se toma la mascara de las partes
              OSCURAS de la puerta (marco y ornamento), se voltea, se abre en
              trapecio y se multiplica sobre el suelo con desenfoque.
  --brillo    el vidrio (las partes CLARAS) se calienta y se ilumina, como si
              hubiera luz dentro: es la toma nocturna desde la calle, donde
              el ornamento se ve a contraluz y el interior no.

Uso:  python puerta-en-escena.py <fondo> <render.png> <salida.png> \
        --cx 0.54 --bottom 0.615 --alto 0.46 [--sombra 0.5] [--brillo 0.6]
"""
import argparse

import numpy as np
from PIL import Image, ImageChops, ImageFilter

W, H = 1080, 1920


def recorte(src):
    im = Image.open(src).convert("RGB")
    caja = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).convert("L") \
        .point(lambda v: 255 if v > 24 else 0).getbbox()
    im = im.crop(caja)
    a = np.asarray(im, dtype=np.float32)
    dist = 255 - a.min(axis=2)
    alfa = np.clip((dist - 30) / 60, 0, 1) * 255
    return Image.fromarray(np.dstack([a, alfa]).astype(np.uint8), "RGBA")


def trapecio(mascara, w_top, w_bot, alto):
    """Deforma una mascara (ya volteada) a un trapecio: estrecho arriba (junto
    a la puerta), ancho abajo (hacia la camara)."""
    src = mascara.resize((w_bot, alto), Image.BILINEAR)
    # transformacion perspectiva con Pillow: coeficientes de 4 puntos
    x0 = (w_bot - w_top) / 2
    ancho, h = w_bot, alto
    origen = [(0, 0), (ancho, 0), (ancho, h), (0, h)]
    destino = [(x0, 0), (x0 + w_top, 0), (ancho, h), (0, h)]
    A = []
    for (x, y), (u, v) in zip(destino, origen):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    B = np.array([c for p in origen for c in p], dtype=np.float64)
    coef = np.linalg.solve(np.array(A, dtype=np.float64), B)
    return src.transform((ancho, h), Image.PERSPECTIVE, tuple(coef), Image.BILINEAR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fondo"); ap.add_argument("render"); ap.add_argument("salida")
    ap.add_argument("--cx", type=float, default=0.5)
    ap.add_argument("--bottom", type=float, default=0.62)
    ap.add_argument("--alto", type=float, default=0.45)
    ap.add_argument("--sombra", type=float, default=0.0)
    ap.add_argument("--brillo", type=float, default=0.0)
    a = ap.parse_args()

    fondo = Image.open(a.fondo).convert("RGB").resize((W, H), Image.LANCZOS)
    puerta = recorte(a.render)
    alto = round(H * a.alto)
    ancho = round(puerta.width * alto / puerta.height)
    puerta = puerta.resize((ancho, alto), Image.LANCZOS)
    x = round(W * a.cx - ancho / 2)
    y = round(H * a.bottom - alto)

    pa = np.asarray(puerta, dtype=np.float32)
    lum = pa[..., :3].mean(axis=2)
    alfa = pa[..., 3] / 255

    if a.brillo > 0:
        # Vidrio = zonas claras de la puerta. Se calientan y suben de luz.
        vidrio = np.clip((lum - 120) / 80, 0, 1) * alfa
        calido = np.array([255, 214, 150], dtype=np.float32)
        rgb = pa[..., :3] * (1 - vidrio[..., None] * a.brillo) + calido * vidrio[..., None] * a.brillo
        pa[..., :3] = np.clip(rgb, 0, 255)
        puerta = Image.fromarray(pa.astype(np.uint8), "RGBA")

    lienzo = fondo.convert("RGBA")

    if a.sombra > 0:
        # Ornamento y marco = zonas oscuras. Proyectadas al suelo hacia la
        # camara: volteadas, en trapecio, desenfocadas, multiplicadas.
        oscuro = (np.clip((150 - lum) / 60, 0, 1) * alfa * 255).astype(np.uint8)
        m = Image.fromarray(oscuro, "L").transpose(Image.FLIP_TOP_BOTTOM)
        largo = round(H - H * a.bottom)          # hasta el borde inferior
        m = trapecio(m, ancho, round(ancho * 1.9), largo)
        m = m.filter(ImageFilter.GaussianBlur(6))
        # desvanecer con la distancia
        grad = np.linspace(1.0, 0.25, m.height, dtype=np.float32)[:, None]
        ma = (np.asarray(m, dtype=np.float32) * grad * a.sombra).astype(np.uint8)
        m = Image.fromarray(ma, "L")
        oscurecido = Image.fromarray((np.asarray(fondo, dtype=np.float32) * 0.55).astype(np.uint8), "RGB").convert("RGBA")
        capa = Image.new("L", (W, H), 0)
        capa.paste(m, (round(W * a.cx - m.width / 2), y + alto))
        lienzo = Image.composite(oscurecido, lienzo, capa)

    # sombra de contacto suave bajo la puerta
    from PIL import ImageDraw
    s = Image.new("L", (W, H), 0)
    ImageDraw.Draw(s).ellipse((x - 20, y + alto - 18, x + ancho + 20, y + alto + 18), fill=160)
    s = s.filter(ImageFilter.GaussianBlur(18))
    lienzo = Image.composite(Image.new("RGBA", (W, H), (20, 15, 10, 255)), lienzo, s)

    lienzo.alpha_composite(puerta, (x, y))
    lienzo.convert("RGB").save(a.salida, optimize=True)
    print("puerta %dx%d en (%d,%d) -> %s" % (ancho, alto, x, y, a.salida))


if __name__ == "__main__":
    main()
