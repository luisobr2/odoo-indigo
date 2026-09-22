"""Compara una foto con su version procesada por IA, ALINEANDOLAS primero.

verificar-mejoradas.py asume que la version procesada tiene el mismo encuadre
que el original. Eso vale para una mejora, pero no para una extension
(outpaint) o una ampliacion que reencuadra: ahi el original aparece a otra
escala y en otra posicion, y comparar pixel a pixel mide el desplazamiento,
no el contenido.

Aqui se localiza el original DENTRO de la procesada con puntos
caracteristicos (SIFT) y una homografia, se deforma el original a esa
posicion, y solo entonces se comparan los bordes en la zona que ambos
comparten. Asi un reencuadre legitimo no se confunde con un ornamento
redibujado.

Uso:  python comparar-alineado.py <original> <procesada> <hoja_salida.jpg>
"""
import sys

import cv2
import numpy as np


def bordes(gris):
    gx = cv2.Sobel(gris, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(gris, cv2.CV_32F, 0, 1)
    m = cv2.magnitude(gx, gy)
    return cv2.GaussianBlur(m, (0, 0), 2)


def main(ruta_o, ruta_p, salida):
    o = cv2.imread(ruta_o)
    p = cv2.imread(ruta_p)
    go = cv2.cvtColor(o, cv2.COLOR_BGR2GRAY)
    gp = cv2.cvtColor(p, cv2.COLOR_BGR2GRAY)

    sift = cv2.SIFT_create(6000)
    ko, do = sift.detectAndCompute(go, None)
    kp, dp = sift.detectAndCompute(gp, None)
    pares = cv2.BFMatcher().knnMatch(do, dp, k=2)
    buenos = [m for m, n in pares if m.distance < 0.7 * n.distance]
    if len(buenos) < 12:
        sys.exit("Muy pocos puntos en comun (%d): no se puede alinear." % len(buenos))

    src = np.float32([ko[m.queryIdx].pt for m in buenos]).reshape(-1, 1, 2)
    dst = np.float32([kp[m.trainIdx].pt for m in buenos]).reshape(-1, 1, 2)
    H, inl = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
    inliers = int(inl.sum())

    # El original deformado a donde esta en la procesada, y su mascara.
    h, w = gp.shape
    o_en_p = cv2.warpPerspective(go, H, (w, h))
    mascara = cv2.warpPerspective(np.full(go.shape, 255, np.uint8), H, (w, h)) > 0
    mascara = cv2.erode(mascara.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0

    esquinas = cv2.perspectiveTransform(
        np.float32([[0, 0], [go.shape[1], 0], [go.shape[1], go.shape[0]], [0, go.shape[0]]]).reshape(-1, 1, 2), H
    ).reshape(-1, 2)
    escala = np.linalg.norm(esquinas[1] - esquinas[0]) / go.shape[1]

    b1 = bordes(o_en_p)[mascara]
    b2 = bordes(gp)[mascara]
    corr = float(np.corrcoef(b1, b2)[0, 1])
    dif = float(np.abs(o_en_p[mascara].astype(float) - gp[mascara].astype(float)).mean())

    print("puntos en comun: %d (validos %d)" % (len(buenos), inliers))
    print("el original ocupa la procesada a escala %.3f" % escala)
    print("esquina sup-izq del original en la procesada: (%.0f, %.0f)" % tuple(esquinas[0]))
    print("zona comparada: %.0f %% de la procesada" % (100 * mascara.mean()))
    print("correlacion de bordes (1 = misma estructura): %.3f" % corr)
    print("diferencia media de luz: %.1f de 255" % dif)

    # Hoja: original alineado | procesada, recortadas a la zona comun.
    ys, xs = np.where(mascara)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    a = cv2.cvtColor(o_en_p[y0:y1, x0:x1], cv2.COLOR_GRAY2BGR)
    b = p[y0:y1, x0:x1]
    hoja = np.hstack([a, np.full((a.shape[0], 12, 3), 40, np.uint8), b])
    escala_hoja = 1600 / hoja.shape[1]
    if escala_hoja < 1:
        hoja = cv2.resize(hoja, None, fx=escala_hoja, fy=escala_hoja, interpolation=cv2.INTER_AREA)
    cv2.imwrite(salida, hoja)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
