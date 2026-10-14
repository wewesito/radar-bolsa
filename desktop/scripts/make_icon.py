"""Genera el icono de la app (1024×1024): radar blanco sobre azul, esquinas redondeadas.

Uso: python scripts/make_icon.py src-tauri/icons/app-icon.png
Después: npx tauri icon src-tauri/icons/app-icon.png  (crea todos los tamaños)
"""

import math
import sys

from PIL import Image, ImageDraw

S = 4096  # se dibuja a 4x y se reduce: bordes suaves
BLUE_TOP, BLUE_BOTTOM = (37, 99, 235), (29, 64, 175)


def main(out: str) -> None:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    # Fondo: degradado vertical dentro de un cuadrado redondeado (margen tipo macOS)
    margin, radius = int(S * 0.09), int(S * 0.2)
    grad = Image.new("RGBA", (S, S))
    gd = ImageDraw.Draw(grad)
    for y in range(S):
        t = y / S
        gd.line([(0, y), (S, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(BLUE_TOP, BLUE_BOTTOM)) + (255,))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([margin, margin, S - margin, S - margin], radius, fill=255)
    img.paste(grad, (0, 0), mask)

    d = ImageDraw.Draw(img)
    c = S / 2
    white = (255, 255, 255, 255)
    w = int(S * 0.028)
    for r in (0.30, 0.19):
        rr = S * r
        d.ellipse([c - rr, c - rr, c + rr, c + rr], outline=white, width=w)
    # Barrido del radar (cuña translúcida) y aguja
    sweep = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sweep)
    rr = S * 0.30
    sd.pieslice([c - rr, c - rr, c + rr, c + rr], -90, -45, fill=(255, 255, 255, 90))
    img.alpha_composite(sweep)
    ang = math.radians(-45)
    d.line([(c, c), (c + rr * math.cos(ang), c + rr * math.sin(ang))], fill=white, width=w)
    dot = S * 0.035
    d.ellipse([c - dot, c - dot, c + dot, c + dot], fill=white)
    # Punto detectado
    px, py, pr = c + S * 0.12, c - S * 0.2, S * 0.03
    d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=(134, 239, 172, 255))

    img = img.resize((1024, 1024), Image.LANCZOS)
    img.save(out)


if __name__ == "__main__":
    main(sys.argv[1])
