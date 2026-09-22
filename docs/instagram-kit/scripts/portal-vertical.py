"""Capturas REALES del portal de dealers, montadas en vertical (1080x1920).

Las capturas del portal (video-production/public/projects/indigo/generated/
portal-*.png) son de escritorio, 1920x949, y a pantalla completa en un reel
vertical solo se veria una franja. Aqui se recorta lo que cuenta —la tabla de
pedidos y la ficha de un pedido con su etapa— y se apila en dos tarjetas
sobre el navy de la marca.

Salen del dealer de PRUEBAS (Miami Impact Doors LLC) y ya llevan difuminados
nombre, telefono y direccion del cliente: no hay datos reales a la vista.

Uso:  python portal-vertical.py <carpeta generated> <salida.png>
"""
import sys

from PIL import Image, ImageDraw, ImageFilter

NAVY = (22, 34, 55)
W, H = 1080, 1920
# 860 y no mas: la escena usa el movimiento `push` de ugcShot, que amplia
# hasta el 116 %. Con 1000 de ancho las tarjetas acababan en 1160 dentro de un
# encuadre de 1080 y se cortaban por los dos lados. 860 x 1,16 = 998.
ANCHO = 860
# Recortes medidos sobre las capturas de 1920x949: la columna de contenido va
# de x=300 a x=1620; en la de pedidos, cabecera + tabla; en la del detalle,
# desde el titulo del pedido hasta la tabla de piezas.
RECORTES = [("portal-orders.png", (300, 0, 1620, 440)),
            ("portal-detail.png", (300, 210, 1620, 600))]


def tarjeta(im, radio=22):
    mascara = Image.new("L", im.size, 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=radio, fill=255)
    return mascara


def main(carpeta, salida):
    lienzo = Image.new("RGB", (W, H), NAVY)
    piezas = []
    for nombre, caja in RECORTES:
        im = Image.open(f"{carpeta}/{nombre}").convert("RGB")
        # El total estimado es el PRECIO AL DEALER. En Instagram lo ven
        # tambien los clientes finales, y publicarlo le quita margen al
        # distribuidor: se difumina igual que ya lo estan los datos del
        # cliente. Coordenadas sobre la captura original de 1920x949.
        if nombre == "portal-detail.png":
            zona = (822, 405, 1060, 462)
            im.paste(im.crop(zona).filter(ImageFilter.GaussianBlur(9)), zona[:2])
        im = im.crop(caja)
        piezas.append(im.resize((ANCHO, round(im.height * ANCHO / im.width)), Image.LANCZOS))
    hueco = 44
    total = sum(p.height for p in piezas) + hueco * (len(piezas) - 1)
    y = round(H * 0.42 - total / 2)  # algo por encima del centro: abajo van los subtitulos
    x = (W - ANCHO) // 2
    for p in piezas:
        sombra = Image.new("L", (W, H), 0)
        ImageDraw.Draw(sombra).rounded_rectangle((x + 6, y + 16, x + ANCHO + 6, y + p.height + 16), radius=22, fill=150)
        sombra = sombra.filter(ImageFilter.GaussianBlur(22))
        lienzo = Image.composite(Image.new("RGB", (W, H), (6, 12, 24)), lienzo, sombra)
        lienzo.paste(p, (x, y), tarjeta(p))
        y += p.height + hueco
    lienzo.save(salida, optimize=True)
    print("portal vertical ->", salida)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
