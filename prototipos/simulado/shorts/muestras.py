"""El primer segundo de cada Short (lo que decide si la gente se para o pasa).

    python3 muestras.py salida_dir
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from estilo import (AMARILLO, AZUL, BLANCO, H, OSCURO, PUNTO, ROJO, TENUE, VERDE, W, brillo, etiqueta, fondo,
                    marca, punto, titular, tu)


def cumple():
    img = fondo()
    d = ImageDraw.Draw(img, "RGBA")
    # 23 en clase: 5 filas de pupitres
    pos = [(150 + c*195, 900 + f*160) for f in range(5) for c in range(5)][:24]
    yo = 12
    pareja = (3, 19)
    for k, (x, y) in enumerate(pos):
        if k == yo:
            continue
        col = ROJO if k in pareja else PUNTO
        if k in pareja:
            brillo(img, [(x, y, 34)], 2.2, ROJO, 0.9)
        punto(d, x, y, 34, col)
    d = ImageDraw.Draw(img, "RGBA")
    a, b = pos[pareja[0]], pos[pareja[1]]
    d.line([a, b], fill=ROJO + (200,), width=6)
    etiqueta(img, (a[0] + b[0])/2 + 120, (a[1] + b[1])/2, "¡mismo día!", ROJO, 40)
    x, y = pos[yo]
    tu(img, x, y, 70, "susto", (0.6, -0.4), 1.0)
    etiqueta(img, x, y - 140, "tú", AMARILLO, 46, flecha_a=(x, y - 76))
    titular(img, [[("En tu clase", BLANCO)], [("sois ", BLANCO), ("23", AMARILLO), (".", BLANCO)],
                  [("¿Dos cumplen", BLANCO)], [("el mismo día?", BLANCO)]], 250, 112)
    marca(img)
    return img


def cola():
    img = fondo()
    d = ImageDraw.Draw(img, "RGBA")
    cajas = [240, 540, 840]
    for k, x in enumerate(cajas):
        d.rounded_rectangle([x - 110, 820, x + 110, 900], radius=16, fill=(40, 50, 90, 255), outline=TENUE + (255,), width=4)
        d.text((x, 860), f"CAJA {k + 1}", font=__import__("estilo").F(34), fill=TENUE + (255,), anchor="mm")
    for k, x in enumerate(cajas):
        n = 4 if k != 1 else 5
        for j in range(n):
            y = 990 + j*150
            if k == 1 and j == 4:
                tu(img, x, y, 62, "triste", (0, -1), 0.5)
                etiqueta(img, x + 190, y - 30, "tú", AMARILLO, 44, flecha_a=(x + 70, y - 10))
                continue
            punto(d, x, y, 46, PUNTO)
    # las otras colas avanzan
    for x in (240, 840):
        d.polygon([(x - 30, 960 - 10), (x + 30, 960 - 10), (x, 925)], fill=VERDE + (230,))
    titular(img, [[("¿Por qué tu cola", BLANCO)], [("SIEMPRE", AMARILLO), (" es", BLANCO)], [("la más lenta?", BLANCO)]], 300, 112)
    marca(img)
    return img


def dinero():
    img = fondo()
    d = ImageDraw.Draw(img, "RGBA")
    rnd = np.random.default_rng(2)
    cols, filas = 18, 16
    for f in range(filas):
        for c in range(cols):
            x = 70 + c*55 + (f % 2)*27
            y = 860 + f*55
            if abs(x - W/2) < 110 and abs(y - 1260) < 110:
                continue
            punto(d, x, y, 15, PUNTO)
            d.ellipse([x + 8, y - 22, x + 24, y - 6], fill=AMARILLO + (210,))
    tu(img, W/2, 1260, 80, "contento", (0, 0), 0.2)
    etiqueta(img, W/2, 1110, "100 €", AMARILLO, 48)
    titular(img, [[("Repartí el dinero", BLANCO)], [("a partes ", BLANCO), ("IGUALES", AMARILLO)],
                  [("entre 1.000", BLANCO)], [("personas.", BLANCO)]], 260, 108)
    marca(img)
    return img


def frenazo():
    img = fondo()
    d = ImageDraw.Draw(img, "RGBA")
    cx, cy, R = W/2, 1250, 360
    d.ellipse([cx - R - 50, cy - R - 50, cx + R + 50, cy + R + 50], outline=(60, 70, 110, 255), width=90)
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(120, 130, 170, 120), width=3)
    yo = 0
    for k in range(22):
        ang = -math.pi/2 + k*2*math.pi/22
        x, y = cx + R*math.cos(ang), cy + R*math.sin(ang)
        if k == yo:
            continue
        d.rounded_rectangle([x - 24, y - 24, x + 24, y + 24], radius=10, fill=PUNTO + (255,))
    x, y = cx, cy - R
    brillo(img, [(x + 60, y, 30)], 2.5, ROJO, 1.0)
    tu(img, x, y, 64, "susto", (1, 0), 1.0)
    d = ImageDraw.Draw(img, "RGBA")
    for dx in (-80, -110):
        d.ellipse([x + dx - 10, y - 10 + 30, x + dx + 10, y + 10 + 30], fill=ROJO + (255,))
    etiqueta(img, cx, cy, "¡FRENAS!", ROJO, 56)
    titular(img, [[("¿Qué pasaría si", BLANCO)], [("frenas ", BLANCO), ("1 segundo", AMARILLO)], [("en la autopista?", BLANCO)]], 300, 108)
    marca(img)
    return img


def puertas():
    img = fondo()
    d = ImageDraw.Draw(img, "RGBA")
    for k, x in enumerate((220, 540, 860)):
        d.rounded_rectangle([x - 130, 820, x + 130, 1300], radius=18, fill=(70, 46, 30, 255), outline=(160, 110, 70, 255), width=8)
        d.ellipse([x + 80, 1050, x + 104, 1074], fill=AMARILLO + (255,))
        d.text((x, 940), f"{k + 1}", font=__import__("estilo").F(110), fill=(230, 200, 160, 255), anchor="mm")
    tu(img, 540, 1520, 90, "pensando", (-0.8, -0.6), 0.9)
    etiqueta(img, 800, 1440, "¿cambio?", AMARILLO, 48, flecha_a=(640, 1500))
    titular(img, [[("3 puertas.", BLANCO)], [("1 premio.", AMARILLO)], [("¿Cambiarías", BLANCO)], [("de puerta?", BLANCO)]], 260, 112)
    marca(img)
    return img


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    fotos = [f() for f in (cumple, cola, dinero, frenazo, puertas)]
    for n, f in zip(("cumple", "cola", "dinero", "frenazo", "puertas"), fotos):
        f.save(out/f"gancho_{n}.png")
    hoja = Image.new("RGB", (5*432 + 4*20, 768), (255, 255, 255))
    for k, f in enumerate(fotos):
        hoja.paste(f.resize((432, 768), Image.LANCZOS), (k*452, 0))
    hoja.save(out/"ganchos.png")
