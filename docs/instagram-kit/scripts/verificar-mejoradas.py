"""Comprueba que una foto «mejorada» sigue mostrando la MISMA puerta.

gpt-image-2 no filtra la foto, la regenera. Una mejora puede traer, sin
avisar, un ornamento con un trazo menos o una forma inventada, y eso en una
slide de «real installs» es mostrar una puerta que nadie instalo.

Que se mide: la ESTRUCTURA, no el color. Se compara la magnitud del
gradiente (donde hay bordes) del original y de la mejorada dentro de la zona
de la puerta, con correlacion de Pearson. Es insensible a que la mejorada
sea mas clara o mas contrastada —que es justo lo que se le pidio— y muy
sensible a que un borde aparezca, desaparezca o se mueva. Los mapas se
suavizan un poco para tolerar desplazamientos de uno o dos pixeles.

Una cifra suelta no significa nada, asi que cada corrida se calibra con dos
referencias sobre la misma zona:

  · techo  — el original contra si mismo aclarado y contrastado a mano.
             Misma estructura, otra luz: lo mejor que puede sacar una mejora.
  · suelo  — el original contra OTRA foto de puerta. Estructura distinta.

Una mejorada fiel queda cerca del techo. Una que reinvento el ornamento cae
hacia el suelo. Ademas genera una hoja con el ornamento ampliado lado a lado,
porque la decision final se toma MIRANDO, no con el numero.

Uso:  python verificar-mejoradas.py
"""
import pathlib

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

REALES = pathlib.Path(__file__).resolve().parent.parent / "reales"
SALIDA = REALES / "_verificacion"

# Zona de la puerta (incluido el montante, si lo hay) en fracciones del
# ancho y alto de la foto. Medidas sobre las slides montadas.
ZONAS = {
    "16-dd-negra-ovalos-montante-fachada.jpg": (0.21, 0.20, 0.79, 0.95),
    "15-sd-oscura-ranura-fachada.jpg": (0.14, 0.19, 0.84, 0.87),
    "14-sd-negra-flores-interior.jpg": (0.18, 0.02, 0.92, 0.98),
}
ANCHO_TRABAJO = 768


def gris(im, ancho):
    im = im.convert("L")
    return im.resize((ancho, round(im.height * ancho / im.width)), Image.LANCZOS)


def mapa_bordes(im):
    a = np.asarray(im, dtype=np.float64)
    gx = np.zeros_like(a)
    gy = np.zeros_like(a)
    gx[:, 1:-1] = a[:, 2:] - a[:, :-2]
    gy[1:-1, :] = a[2:, :] - a[:-2, :]
    mag = np.hypot(gx, gy)
    mag = mag / (mag.max() or 1) * 255
    suave = Image.fromarray(mag.astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))
    return np.asarray(suave, dtype=np.float64)


def recorte(arr, zona):
    h, w = arr.shape
    x0, y0, x1, y1 = zona
    return arr[round(y0 * h):round(y1 * h), round(x0 * w):round(x1 * w)]


def parecido(a_img, b_img, zona):
    a = recorte(mapa_bordes(a_img), zona).ravel()
    b = recorte(mapa_bordes(b_img), zona).ravel()
    return float(np.corrcoef(a, b)[0, 1])


def main():
    SALIDA.mkdir(exist_ok=True)
    nombres = list(ZONAS)
    for i, nombre in enumerate(nombres):
        original = Image.open(REALES / nombre).convert("RGB")
        mejorada_path = REALES / (pathlib.Path(nombre).stem + "-mejorada.png")
        if not mejorada_path.exists():
            print("%-42s sin mejorada todavia" % nombre)
            continue
        mejorada = Image.open(mejorada_path).convert("RGB")
        zona = ZONAS[nombre]

        o = gris(original, ANCHO_TRABAJO)
        m = gris(mejorada, ANCHO_TRABAJO).resize(o.size, Image.LANCZOS)

        # Techo: misma foto, solo luz y contraste distintos.
        retocada = ImageEnhance.Contrast(ImageEnhance.Brightness(original).enhance(1.25)).enhance(1.2)
        techo = parecido(o, gris(retocada, ANCHO_TRABAJO), zona)
        # Suelo: otra puerta distinta, llevada al mismo tamano.
        otra = Image.open(REALES / nombres[(i + 1) % len(nombres)]).convert("RGB")
        suelo = parecido(o, gris(otra, ANCHO_TRABAJO).resize(o.size, Image.LANCZOS), zona)
        valor = parecido(o, m, zona)
        posicion = (valor - suelo) / (techo - suelo) if techo != suelo else float("nan")

        print("%-42s mejorada %.3f   techo %.3f   suelo %.3f   -> %3.0f %% del camino al techo"
              % (nombre, valor, techo, suelo, posicion * 100))

        # Hoja visual: puerta completa lado a lado, y el ornamento ampliado.
        W, H = original.size
        x0, y0, x1, y1 = zona
        caja = (round(x0 * W), round(y0 * H), round(x1 * W), round(y1 * H))
        mej = mejorada.resize(original.size, Image.LANCZOS)
        a, b = original.crop(caja), mej.crop(caja)
        alto = 900
        a = a.resize((round(a.width * alto / a.height), alto), Image.LANCZOS)
        b = b.resize(a.size, Image.LANCZOS)
        hoja = Image.new("RGB", (a.width * 2 + 16, alto), (40, 40, 40))
        hoja.paste(a, (0, 0))
        hoja.paste(b, (a.width + 16, 0))
        hoja.save(SALIDA / (pathlib.Path(nombre).stem + "-comparar.jpg"), quality=90)
    print("\nhojas en:", SALIDA)


if __name__ == "__main__":
    main()
