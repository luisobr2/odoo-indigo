"""Carrusel «Which style is yours?» — el catalogo ordenado en cinco estilos.

Se monta SOLO con renders del catalogo publico de indigodecors.com
(scraping/output/variant_images/), sin generar nada con IA: no depende de
creditos de Gemini, y como son imagenes de catalogo propias no necesitan el
permiso del dealer que siguen esperando las fotos de instalacion.

Por que se puede componer sin recortar a mano: los renders de ID31 en
adelante salen todos de la misma plantilla — fondo blanco PURO (255,255,255)
y la puerta siempre en la misma caja, (302,60,723,961), medido en los 15 que
se usan. Asi que:

  · se pegan con MULTIPLICAR sobre la crema de la marca. Blanco por crema da
    crema, de modo que el fondo del render desaparece sin recortes ni halos,
    y la sombra y el antialias del borde se conservan tal cual.
  · las tres puertas de cada slide quedan alineadas al pixel.

Lo que multiplicar NO permite: una puerta mas clara que el fondo. Por eso no
hay puertas blancas: sobre la crema desaparecerian. El acabado ya lo cubre el
carrusel de acabados; este va de ESTILO.

Regla del kit (REGISTRO-DE-USO.md): no repetir puertas entre publicaciones.
Quedan fuera las 9 de la rejilla del carrusel custom (ID01, 02, 06, 08, 13,
19, 21, 26, 38) y la ID13 de acabados y anatomia.

Uso:  python carrusel-estilos.py
"""
import pathlib
import urllib.request

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

AQUI = pathlib.Path(__file__).resolve().parent
KIT = AQUI.parent
REPO = KIT.parent.parent
VARIANTES = REPO / "scraping" / "output" / "variant_images"
MARCA = KIT / "marca"
SALIDA = KIT / "nuevos" / "carrusel-estilos"
FUENTES = AQUI / ".fuentes"

W, H = 1080, 1350  # 4:5. Ocupa mas pantalla en el feed que el 1:1, y la
                   # rejilla del perfil (3:4) casi no lo recorta.

# Muestreados de los PNG de los carruseles de acabados y custom, para que en
# la rejilla del perfil los tres parezcan de la misma casa.
CREMA = (250, 249, 246)
NAVY = (14, 31, 60)
NAVY_FONDO = (22, 34, 55)
BRONCE = (181, 137, 90)


def mezcla(a, b, t):
    return tuple(round(x * (1 - t) + y * t) for x, y in zip(a, b))


TENUE = mezcla(CREMA, NAVY, 0.62)
MUY_TENUE = mezcla(CREMA, NAVY, 0.40)
CLARO_SOBRE_NAVY = mezcla(NAVY_FONDO, (255, 255, 255), 0.72)

CAJA_PUERTA = (300, 58, 725, 963)  # la caja medida, con 2 px de aire

ESTILOS = [
    ("CURVES", "bronze", ["ID33-SD", "ID40-SD", "ID42-SD"],
     "Flowing arcs. Soft, never plain.",
     "Transitional and coastal homes"),
    ("GEOMETRIC", "black", ["ID43-SD", "ID44-SD", "ID52-SD"],
     "Diamonds, zigzags and sharp angles.",
     "Contemporary homes with bold lines"),
    ("RINGS", "bronze", ["ID45-SD", "ID54-SD", "ID55-SD"],
     "Circles in rhythm, calm and balanced.",
     "Art Deco and coastal homes"),
    ("LINEAR", "black", ["ID32-SD", "ID49-SD", "ID53-SD"],
     "Straight lines and nothing extra.",
     "Modern and minimalist homes"),
    ("CLASSIC", "bronze", ["ID39-SD", "ID58-SD", "ID60-SD"],
     "Scrollwork and arches, old-world charm.",
     "Mediterranean and Spanish-style homes"),
]

# Una puerta por estilo para la portada, en el mismo orden 01..05.
PORTADA = [("ID40-SD", "bronze"), ("ID44-SD", "black"), ("ID55-SD", "bronze"),
           ("ID53-SD", "black"), ("ID39-SD", "bronze")]

TOTAL = 2 + len(ESTILOS)


# ---------------------------------------------------------------- fuentes

URLS = {
    "Montserrat-ExtraBold.ttf": "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-ExtraBold.ttf",
    "Montserrat-SemiBold.ttf": "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-SemiBold.ttf",
    "Inter.ttf": "https://github.com/google/fonts/raw/main/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf",
}


def fuente(nombre, tam, peso=None):
    FUENTES.mkdir(exist_ok=True)
    ruta = FUENTES / nombre
    if not ruta.exists():
        urllib.request.urlretrieve(URLS[nombre], ruta)
    f = ImageFont.truetype(str(ruta), tam)
    if peso is not None:  # Inter es variable: tamano optico y peso
        f.set_variation_by_axes([min(32, max(14, tam)), peso])
    return f


def display(t):
    return fuente("Montserrat-ExtraBold.ttf", t)


def etiqueta(t):
    return fuente("Montserrat-SemiBold.ttf", t)


def cuerpo(t, peso=400):
    return fuente("Inter.ttf", t, peso)


# ---------------------------------------------------------------- dibujo

def ancho_espaciado(texto, f, tracking):
    return sum(f.getlength(c) for c in texto) + tracking * (len(texto) - 1)


def texto_espaciado(d, xy, texto, f, color, tracking, alinear="izq"):
    """PIL no tiene interletraje: se dibuja letra a letra."""
    x, y = xy
    total = ancho_espaciado(texto, f, tracking)
    if alinear == "centro":
        x -= total / 2
    elif alinear == "der":
        x -= total
    for c in texto:
        d.text((x, y), c, font=f, fill=color)
        x += f.getlength(c) + tracking


def puerta(codigo, acabado, alto):
    im = Image.open(VARIANTES / codigo / (acabado + ".jpg")).convert("RGB")
    im = im.crop(CAJA_PUERTA)
    ancho = round(im.width * alto / im.height)
    return im.resize((ancho, alto), Image.LANCZOS)


def sombra_suelo(lienzo, cx, y, ancho):
    """Sombra de contacto bajo la puerta, como en la slide de bronce."""
    capa = Image.new("L", lienzo.size, 0)
    ImageDraw.Draw(capa).ellipse((cx - ancho / 2, y - 14, cx + ancho / 2, y + 14), fill=70)
    capa = capa.filter(ImageFilter.GaussianBlur(13))
    oscuro = Image.new("RGB", lienzo.size, mezcla(CREMA, NAVY, 0.55))
    return Image.composite(oscuro, lienzo, capa)


def pegar_multiplicando(lienzo, im, x, y):
    """Blanco x crema = crema: el fondo del render desaparece solo."""
    zona = lienzo.crop((x, y, x + im.width, y + im.height))
    lienzo.paste(ImageChops.multiply(zona, im), (x, y))


def fila_de_puertas(lienzo, puertas, y, alto, hueco):
    ims = [puerta(c, a, alto) for c, a in puertas]
    total = sum(i.width for i in ims) + hueco * (len(ims) - 1)
    x = (W - total) // 2
    centros = []
    for im in ims:
        lienzo = sombra_suelo(lienzo, x + im.width / 2, y + alto - 2, im.width * 1.08)
        pegar_multiplicando(lienzo, im, x, y)
        centros.append(x + im.width / 2)
        x += im.width + hueco
    return lienzo, centros


# ---------------------------------------------------------------- slides

def portada():
    lienzo = Image.new("RGB", (W, H), CREMA)

    # Cinco puertas, una por estilo, a sangre por los lados: las de los
    # extremos se cortan a proposito, dicen «hay mas, desliza».
    alto, paso = 600, 300
    y = 150
    for i, (codigo, acabado) in enumerate(PORTADA):
        im = puerta(codigo, acabado, alto)
        cx = W / 2 + (i - 2) * paso
        x = round(cx - im.width / 2)
        lienzo = sombra_suelo(lienzo, cx, y + alto - 2, im.width * 1.08)
        # Recortar a lo que cae dentro del lienzo antes de multiplicar.
        izq, der = max(0, x), min(W, x + im.width)
        trozo = im.crop((izq - x, 0, der - x, alto))
        pegar_multiplicando(lienzo, trozo, izq, y)

    d = ImageDraw.Draw(lienzo)
    texto_espaciado(d, (80, 70), "INDIGO DECORS · STYLE GUIDE", etiqueta(23), BRONCE, 4)

    # Banda navy: el borde hace de suelo para la fila de puertas.
    banda = 820
    d.rectangle((0, banda, W, H), fill=NAVY_FONDO)
    f = display(108)
    d.text((74, banda + 70), "WHICH STYLE", font=f, fill=(255, 255, 255))
    d.text((74, banda + 186), "IS YOURS?", font=f, fill=(255, 255, 255))
    d.text((80, banda + 350), "Our catalog, sorted into five styles.", font=cuerpo(36), fill=CLARO_SOBRE_NAVY)
    # La flecha se dibuja: el glifo "→" de Montserrat sale diminuto.
    fs = etiqueta(30)
    y_sw = banda + 430
    largo = 46
    x_fin = 1000
    texto_espaciado(d, (x_fin - largo - 18, y_sw), "swipe", fs, BRONCE, 2, "der")
    y_eje = y_sw + 22
    d.line((x_fin - largo, y_eje, x_fin, y_eje), fill=BRONCE, width=4)
    d.polygon([(x_fin + 2, y_eje), (x_fin - 13, y_eje - 10), (x_fin - 13, y_eje + 10)], fill=BRONCE)
    return lienzo


def slide_estilo(n, nombre, acabado, codigos, frase, casas):
    lienzo = Image.new("RGB", (W, H), CREMA)
    # 612 de alto y 32 de hueco hacen 922 px de fila: de x=79 a x=1001, el
    # mismo margen de 80 que el texto. Con 640 la fila se salia a 50 y el
    # desfase entre el borde de las puertas y el del texto se notaba.
    lienzo, centros = fila_de_puertas(lienzo, [(c, acabado) for c in codigos], y=404, alto=612, hueco=32)
    d = ImageDraw.Draw(lienzo)

    texto_espaciado(d, (80, 70), "INDIGO DECORS · STYLE GUIDE", etiqueta(23), BRONCE, 4)
    texto_espaciado(d, (1000, 70), "%02d / %02d" % (n, len(ESTILOS)), etiqueta(23), TENUE, 3, "der")

    # Numero grande en bronce y el nombre al lado: es el numero que se pide
    # comentar al final, asi que tiene que verse.
    num = "%02d" % n
    fnum = display(150)
    d.text((72, 104), num, font=fnum, fill=BRONCE)
    x_titulo = 72 + fnum.getlength(num) + 26
    tam = 104
    while display(tam).getlength(nombre) > W - 80 - x_titulo:
        tam -= 4
    ft = display(tam)
    # Alinear las lineas base del numero y del titulo.
    base_num = 104 + fnum.getmetrics()[0]
    d.text((x_titulo, base_num - ft.getmetrics()[0]), nombre, font=ft, fill=NAVY)

    d.text((80, 292), frase, font=cuerpo(36), fill=TENUE)

    # El codigo bajo cada puerta es util de verdad: es como se piden.
    for cx, cod in zip(centros, codigos):
        texto_espaciado(d, (cx, 1046), cod.replace("-SD", ""), etiqueta(22), MUY_TENUE, 3, "centro")

    d.rectangle((80, 1150, 80 + 44, 1153), fill=BRONCE)
    texto_espaciado(d, (80, 1172), "PAIRS WITH", etiqueta(20), BRONCE, 3)
    d.text((80, 1204), casas, font=cuerpo(38, 500), fill=NAVY)
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
    for linea, color in (("Which style is yours?", (255, 255, 255)),
                         ("Tell us in the comments: 01 to 05.", CLARO_SOBRE_NAVY)):
        d.text(((W - fc.getlength(linea)) / 2, y), linea, font=fc, fill=color)
        y += 58

    # Pastilla con la web, igual que la del carrusel custom.
    fp = etiqueta(34)
    web = "indigodecors.com"
    pw, ph = fp.getlength(web) + 88, 82
    px, py = (W - pw) / 2, y + 90
    d.rounded_rectangle((px, py, px + pw, py + ph), radius=ph / 2, fill=BRONCE)
    d.text((px + 44, py + (ph - 34) / 2 - 6), web, font=fp, fill=(12, 25, 48))

    # Centrar en vertical MIDIENDO lo dibujado, no sumando alturas a mano:
    # con las alturas estimadas quedaban 175 px arriba y 310 abajo.
    fondo = Image.new("RGB", lienzo.size, (12, 25, 48))
    arriba, abajo = ImageChops.difference(lienzo, fondo).getbbox()[1::2]
    banda = lienzo.crop((0, arriba, W, abajo))
    centrado = Image.new("RGB", (W, H), (12, 25, 48))
    centrado.paste(banda, (0, (H - banda.height) // 2))
    return centrado


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    slides = [("01-portada.png", portada())]
    for i, (nombre, acabado, codigos, frase, casas) in enumerate(ESTILOS, start=1):
        slides.append(("%02d-%s.png" % (i + 1, nombre.lower()),
                       slide_estilo(i, nombre, acabado, codigos, frase, casas)))
    slides.append(("%02d-cierre.png" % TOTAL, cierre()))
    for nombre, im in slides:
        im.save(SALIDA / nombre, optimize=True)
        print("  ", nombre, im.size)
    print("en:", SALIDA)


if __name__ == "__main__":
    main()
