"""Carrusel «A door for every Miami house» — cinco casas, cinco puertas.

La idea que vende: el que mira reconoce SU casa y ve que puerta le va. Cinco
estilos de casa tipicos de Miami (Art Deco, mediterranea, moderna, Key West,
mid-century), cada uno con un diseno del catalogo que le pega.

Como se hizo (22-sep-2026):
  · La CASA la genero la IA (gpt_image_2_5 via Higgsfield, 4:5, ampliada a
    2k) con un panel de pared LISO donde va la entrada: sin puerta, sin
    ventana, sin ornamento. Las cinco estan en generadas/casas/.
  · La PUERTA es siempre el render real del catalogo, montado sobre el panel
    con puerta-en-escena.py (--caja 300,58,725,963 --lienzo 1080x1350). La
    IA nunca dibuja el ornamento: regla del kit.
  · Los montajes finales estan en generadas/casas/montadas/. Este script
    solo pone el texto y arma la portada y el cierre.

Regla del kit (REGISTRO-DE-USO.md): no repetir puertas entre publicaciones.
Los cinco disenos (ID68, 37, 67, 70, 93) no habian salido en nada.

Uso:  python carrusel-casas.py        (py -3.11: necesita numpy para los montajes)
"""
import importlib.util
import pathlib

from PIL import Image, ImageChops, ImageDraw, ImageFilter

AQUI = pathlib.Path(__file__).resolve().parent
KIT = AQUI.parent
MONTADAS = KIT / "generadas" / "casas" / "montadas"
MARCA = KIT / "marca"
SALIDA = KIT / "nuevos" / "carrusel-casas"

# Fuentes, colores y helpers de texto: los mismos del carrusel de estilos,
# para que en la rejilla del perfil parezcan de la misma casa.
_spec = importlib.util.spec_from_file_location("estilos", AQUI / "carrusel-estilos.py")
estilos = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(estilos)
W, H = estilos.W, estilos.H
CREMA, NAVY, NAVY_FONDO, BRONCE = estilos.CREMA, estilos.NAVY, estilos.NAVY_FONDO, estilos.BRONCE
CLARO_SOBRE_NAVY = estilos.CLARO_SOBRE_NAVY
display, etiqueta, cuerpo = estilos.display, estilos.etiqueta, estilos.cuerpo
texto_espaciado = estilos.texto_espaciado

CASAS = [
    ("01-artdeco-id68.png", "ART DECO", "Miami Beach's own. Rings and curves echo the streamline.", "ID68", "Black"),
    ("02-mediterranea-id37.png", "MEDITERRANEAN", "Warm stucco and terracotta, with a floral geometry to match.", "ID37", "Bronze"),
    ("03-moderna-id67.png", "MODERN", "Clean volumes call for straight lines and nothing extra.", "ID67", "Black"),
    ("04-keywest-id70.png", "KEY WEST", "Soft arcs for a breezy porch and a picket fence.", "ID70", "Bronze"),
    ("05-midcentury-id93.png", "MID-CENTURY", "Horizontal bands, like the roofline and the breeze blocks.", "ID93", "Bronze"),
]
TOTAL = len(CASAS) + 2


def foto(nombre):
    return Image.open(MONTADAS / nombre).convert("RGB").resize((W, H), Image.LANCZOS)


def scrim(lienzo, y0, y1, color, alfa_max, arriba=False):
    """Degradado vertical de color sobre la foto, para que el texto se lea."""
    capa = Image.new("L", (W, y1 - y0), 0)
    d = ImageDraw.Draw(capa)
    n = y1 - y0
    for i in range(n):
        t = i / max(1, n - 1)
        if arriba:
            t = 1 - t
        d.line((0, i, W, i), fill=round(alfa_max * t))
    mascara = Image.new("L", (W, H), 0)
    mascara.paste(capa, (0, y0))
    return Image.composite(Image.new("RGB", (W, H), color), lienzo, mascara)


def portada():
    """Cinco franjas verticales, una por casa, a sangre; banda navy con el titulo."""
    lienzo = Image.new("RGB", (W, H), NAVY_FONDO)
    banda = 790
    ancho = W // 5
    for i, (archivo, *_rest) in enumerate(CASAS):
        im = foto(archivo)
        # La franja se centra en la puerta de cada montaje (cx conocido).
        cx = [0.495, 0.465, 0.50, 0.50, 0.53][i] * W
        izq = round(min(max(0, cx - ancho / 2), W - ancho))
        franja = im.crop((izq, 140, izq + ancho, 140 + banda)).resize((ancho, banda), Image.LANCZOS)
        lienzo.paste(franja, (i * ancho, 0))
    # Separadores finos en crema, para que se lean como cinco fotos y no una.
    d = ImageDraw.Draw(lienzo)
    for i in range(1, 5):
        d.rectangle((i * ancho - 2, 0, i * ancho + 1, banda), fill=CREMA)
    lienzo = scrim(lienzo, 0, 150, NAVY_FONDO, 150, arriba=True)
    d = ImageDraw.Draw(lienzo)
    texto_espaciado(d, (80, 60), "INDIGO DECORS · HOUSE GUIDE", etiqueta(23), (255, 255, 255), 4)

    f = display(96)
    y = banda + 70
    for linea in ("A DOOR FOR", "EVERY MIAMI", "HOUSE."):
        d.text((74, y), linea, font=f, fill=(255, 255, 255))
        y += 104
    d.text((80, y + 24), "Five homes, five designs. Which one is yours?", font=cuerpo(34), fill=CLARO_SOBRE_NAVY)
    fs = etiqueta(30)
    y_sw = banda + 456
    largo, x_fin = 46, 1000
    texto_espaciado(d, (x_fin - largo - 18, y_sw), "swipe", fs, BRONCE, 2, "der")
    y_eje = y_sw + 22
    d.line((x_fin - largo, y_eje, x_fin, y_eje), fill=BRONCE, width=4)
    d.polygon([(x_fin + 2, y_eje), (x_fin - 13, y_eje - 10), (x_fin - 13, y_eje + 10)], fill=BRONCE)
    return lienzo


def slide_casa(n, archivo, nombre, frase, codigo, acabado):
    lienzo = foto(archivo)
    # Arriba: scrim corto para el rotulo. Abajo: banda navy semitransparente
    # que empieza por debajo de todas las puertas (la mas baja acaba en 1107).
    lienzo = scrim(lienzo, 0, 190, NAVY_FONDO, 170, arriba=True)
    lienzo = scrim(lienzo, 1112, 1150, NAVY_FONDO, 235)
    d = ImageDraw.Draw(lienzo)
    d.rectangle((0, 1150, W, H), fill=NAVY_FONDO)
    # el degradado anterior llega a 235; el rectangulo cierra a opaco.

    texto_espaciado(d, (80, 60), "INDIGO DECORS · HOUSE GUIDE", etiqueta(23), (255, 255, 255), 4)
    texto_espaciado(d, (1000, 60), "%02d / %02d" % (n, len(CASAS)), etiqueta(23), (255, 255, 255), 3, "der")

    # Pastilla con el codigo: es como se pide la puerta. Se mide ANTES que el
    # titulo, porque «MEDITERRANEAN» a 64 se le montaba encima.
    fp = etiqueta(24)
    texto = "%s · %s" % (codigo, acabado.upper())
    pw, ph = fp.getlength(texto) + 56 + 3 * (len(texto) - 1), 56
    px, py = 1000 - pw, 1182
    d.rounded_rectangle((px, py, px + pw, py + ph), radius=ph / 2, outline=BRONCE, width=3)
    texto_espaciado(d, (px + 28, py + 14), texto, fp, BRONCE, 3)

    num = "%02d" % n
    fnum = display(72)
    d.text((74, 1174), num, font=fnum, fill=BRONCE)
    x_titulo = 74 + fnum.getlength(num) + 20
    tam = 64
    while display(tam).getlength(nombre) > px - 30 - x_titulo:
        tam -= 2
    ft = display(tam)
    base = 1174 + fnum.getmetrics()[0]
    d.text((x_titulo, base - ft.getmetrics()[0]), nombre, font=ft, fill=(255, 255, 255))
    d.text((80, 1262), frase, font=cuerpo(28), fill=CLARO_SOBRE_NAVY)
    return lienzo


def cierre():
    lienzo = Image.new("RGB", (W, H), (12, 25, 48))
    d = ImageDraw.Draw(lienzo)
    logo = Image.open(MARCA / "logo-blanco.png").convert("RGBA")
    logo = logo.crop(logo.getchannel("A").getbbox())
    ancho = 400
    logo = logo.resize((ancho, round(logo.height * ancho / logo.width)), Image.LANCZOS)
    lienzo.paste(logo, ((W - ancho) // 2, 170), logo)

    y = 170 + logo.height + 110
    f = display(78)
    for linea in ("MORE THAN 150", "DESIGNS."):
        d.text(((W - f.getlength(linea)) / 2, y), linea, font=f, fill=(255, 255, 255))
        y += 92
    y += 40
    fc = cuerpo(38)
    for linea, color in (("Which house is yours?", (255, 255, 255)),
                         ("Tell us in the comments: 01 to 05.", CLARO_SOBRE_NAVY)):
        d.text(((W - fc.getlength(linea)) / 2, y), linea, font=fc, fill=color)
        y += 58
    fp = etiqueta(34)
    web = "indigodecors.com"
    pw, ph = fp.getlength(web) + 88, 82
    px, py = (W - pw) / 2, y + 90
    d.rounded_rectangle((px, py, px + pw, py + ph), radius=ph / 2, fill=BRONCE)
    d.text((px + 44, py + (ph - 34) / 2 - 6), web, font=fp, fill=(12, 25, 48))

    fondo = Image.new("RGB", lienzo.size, (12, 25, 48))
    arriba, abajo = ImageChops.difference(lienzo, fondo).getbbox()[1::2]
    banda = lienzo.crop((0, arriba, W, abajo))
    centrado = Image.new("RGB", (W, H), (12, 25, 48))
    centrado.paste(banda, (0, (H - banda.height) // 2))
    return centrado


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    slides = [("01-portada.png", portada())]
    for i, (archivo, nombre, frase, codigo, acabado) in enumerate(CASAS, start=1):
        slides.append(("%02d-%s.png" % (i + 1, nombre.lower().replace(" ", "-")),
                       slide_casa(i, archivo, nombre, frase, codigo, acabado)))
    slides.append(("%02d-cierre.png" % TOTAL, cierre()))
    for viejo in SALIDA.glob("*.png"):
        viejo.unlink()
    for nombre, im in slides:
        im.save(SALIDA / nombre, optimize=True)
        print("  ", nombre, im.size)
    print("en:", SALIDA)


if __name__ == "__main__":
    main()
