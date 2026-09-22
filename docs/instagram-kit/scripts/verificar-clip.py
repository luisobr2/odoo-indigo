"""¿La puerta sigue siendo la misma durante TODO el clip animado?

Un modelo de imagen a video (Veo, seedance) parte de la foto real, pero cada
fotograma lo inventa. Con Veo ya paso: el ornamento se fue deshaciendo con
los segundos y la puerta acabo abriendose. Por eso no basta con mirar el
primer fotograma.

Para cada instante (cada medio segundo) se localiza la foto de partida DENTRO
del fotograma con SIFT y una homografia —la camara se acerca, asi que la
puerta crece y se desplaza— y se comparan los bordes en la zona comun. Si el
acercamiento es lo unico que cambia, la correlacion se mantiene alta todo el
clip. Si el ornamento se deforma, cae. Tambien se reporta cuantos puntos
casan: cuando se desploman, algo en la imagen dejo de parecerse a la foto.

Genera una hoja de contacto con los fotogramas para mirarla: la cifra
senala, la decision se toma mirando.

Uso:  python verificar-clip.py <foto_de_partida> <clip.mp4> <hoja.jpg>
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np


def bordes(g):
    m = cv2.magnitude(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1))
    return cv2.GaussianBlur(m, (0, 0), 2)


def main(foto, clip, hoja):
    ref = cv2.imread(foto)
    duracion = float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", clip]).decode())
    tmp = Path(tempfile.mkdtemp())
    subprocess.run(["ffmpeg", "-v", "error", "-i", clip, "-vf", "fps=2", str(tmp / "f%03d.png")], check=True)
    frames = sorted(tmp.glob("f*.png"))

    h0, w0 = cv2.imread(str(frames[0])).shape[:2]
    ref = cv2.resize(ref, (w0, h0), interpolation=cv2.INTER_AREA)
    gr = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)
    sift = cv2.SIFT_create(5000)
    kr, dr = sift.detectAndCompute(gr, None)

    print("clip de %.1f s, %d fotogramas analizados (2 por segundo)" % (duracion, len(frames)))
    print(" seg   puntos  escala  bordes")
    miniaturas = []
    for i, f in enumerate(frames):
        img = cv2.imread(str(f))
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        kf, df = sift.detectAndCompute(g, None)
        pares = cv2.BFMatcher().knnMatch(dr, df, k=2) if df is not None else []
        buenos = [m for m, n in (p for p in pares if len(p) == 2) if m.distance < 0.7 * n.distance]
        corr, escala = float("nan"), float("nan")
        if len(buenos) >= 12:
            src = np.float32([kr[m.queryIdx].pt for m in buenos]).reshape(-1, 1, 2)
            dst = np.float32([kf[m.trainIdx].pt for m in buenos]).reshape(-1, 1, 2)
            H, _ = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
            if H is not None:
                r_en_f = cv2.warpPerspective(gr, H, (w0, h0))
                mascara = cv2.warpPerspective(np.full(gr.shape, 255, np.uint8), H, (w0, h0)) > 0
                mascara = cv2.erode(mascara.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
                if mascara.sum() > 1000:
                    corr = float(np.corrcoef(bordes(r_en_f)[mascara], bordes(g)[mascara])[0, 1])
                esquinas = cv2.perspectiveTransform(np.float32([[0, 0], [w0, 0]]).reshape(-1, 1, 2), H).reshape(-1, 2)
                escala = float(np.linalg.norm(esquinas[1] - esquinas[0]) / w0)
        print("%4.1f   %5d   %5.2f   %s" % (i / 2, len(buenos), escala, "%.3f" % corr if corr == corr else " --  "))
        m = cv2.resize(img, (216, round(216 * h0 / w0)), interpolation=cv2.INTER_AREA)
        cv2.putText(m, "%.1fs" % (i / 2), (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        miniaturas.append(m)

    filas = [np.hstack(miniaturas[k:k + 6] + [np.zeros_like(miniaturas[0])] * (6 - len(miniaturas[k:k + 6])))
             for k in range(0, len(miniaturas), 6)]
    cv2.imwrite(hoja, np.vstack(filas))
    print("hoja:", hoja)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
