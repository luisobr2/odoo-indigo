"""
Generate subtle procedural textures for the 3D customizer scene.
Photo-real renders read as "real" largely because nothing is a flat
color — these maps add that micro-variation.

Outputs (to indigo-next/public/3d/tex/):
  stucco.jpg   1024x1024 — warm off-white wall stucco (color + bump)
  concrete.jpg 1024x1024 — light concrete pavers with grout lines (floor)
  rough.jpg     512x512  — mid-gray fractal noise (roughnessMap for metal/glass)

Usage: python scripts/generate_textures.py
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

OUT = Path(r'C:/Trabajo/indigo-next/public/3d/tex')

rng = np.random.default_rng(42)


def fractal_noise(size, octaves=5, persistence=0.55):
    """Simple value-noise fractal: random grids upscaled and blended."""
    acc = np.zeros((size, size), dtype=np.float64)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        cells = 2 ** (o + 2)
        grid = rng.random((cells, cells))
        img = Image.fromarray((grid * 255).astype(np.uint8), 'L')
        img = img.resize((size, size), Image.BICUBIC)
        acc += np.asarray(img, dtype=np.float64) / 255.0 * amp
        total += amp
        amp *= persistence
    return acc / total


def to_img(arr):
    return Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8))


def stucco(size=1024):
    n = fractal_noise(size, octaves=6, persistence=0.6)
    fine = fractal_noise(size, octaves=8, persistence=0.8)
    # warm off-white base with +-6% variation
    base = np.array([0.92, 0.90, 0.86])
    v = 0.94 + (n - 0.5) * 0.10 + (fine - 0.5) * 0.05
    rgb = np.stack([v * base[0], v * base[1], v * base[2]], axis=-1)
    to_img(rgb).save(OUT / 'stucco.jpg', quality=88)


def concrete(size=1024, pavers=2):
    n = fractal_noise(size, octaves=6, persistence=0.65)
    v = 0.78 + (n - 0.5) * 0.16
    # blotchy darker stains
    stains = fractal_noise(size, octaves=3, persistence=0.7)
    v -= np.clip(stains - 0.62, 0, 1) * 0.25
    # grout lines (texture repeats, so lines land on tile borders)
    step = size // pavers
    for i in range(pavers + 1):
        c = min(i * step, size - 1)
        for d in (-1, 0, 1):
            cc = np.clip(c + d, 0, size - 1)
            v[cc, :] *= 0.82
            v[:, cc] *= 0.82
    rgb = np.stack([v * 0.96, v * 0.97, v * 1.0], axis=-1)
    img = to_img(rgb).filter(ImageFilter.GaussianBlur(0.6))
    img.save(OUT / 'concrete.jpg', quality=88)


def rough(size=512):
    n = fractal_noise(size, octaves=7, persistence=0.75)
    # centered on mid-gray, mild contrast — multiplies the material's
    # base roughness without crushing it
    v = 0.5 + (n - 0.5) * 0.35
    to_img(v).convert('L').save(OUT / 'rough.jpg', quality=90)


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    stucco()
    concrete()
    rough()
    for f in OUT.iterdir():
        print(f'{f.name}: {f.stat().st_size:,} bytes')
