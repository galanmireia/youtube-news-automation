"""Tres propuestas de personaje para los Shorts, para que elija ella.

A «Bolita»: la bolita amarilla, pero de cuerpo entero (brazos, piernas, un
  pelo de punta) y nítida, sin el halo que la emborronaba.
B «Píxel»: un cuadradito con patas, como el punto de una simulación que
  ha cobrado vida.
C «Agente»: un robotito redondo con antena y pantalla por cara, como los
  agentes que se mueven en las simulaciones.

    python3 personajes.py salida.png
"""
import math
import sys

from PIL import Image, ImageDraw

from estilo import AMARILLO, AZUL, BLANCO, F, OSCURO, PUNTO, VERDE, W, fondo

S = 2   # se dibuja al doble y se reduce: bordes limpios


def _ojos(d, x, y, r, mira=(0.3, -0.2), sep=0.36, tam=0.27):
    for sx in (-1, 1):
        ex, ey = x + sx*r*sep, y
        er = r*tam
        d.ellipse([ex - er, ey - er*1.1, ex + er, ey + er*1.1], fill=(255, 255, 255), outline=OSCURO, width=int(r*0.05))
        pr = er*0.58
        px, py = ex + mira[0]*er*0.45, ey + mira[1]*er*0.45
        d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=OSCURO)
        d.ellipse([px - pr*0.15, py - pr*0.75, px + pr*0.45, py - pr*0.15], fill=(255, 255, 255))


def bolita(d, x, y, r):
    lw = int(r*0.07)
    # piernas y brazos
    for sx in (-1, 1):
        d.line([(x + sx*r*0.35, y + r*0.85), (x + sx*r*0.45, y + r*1.45)], fill=OSCURO, width=lw)
        d.ellipse([x + sx*r*0.45 - r*0.2, y + r*1.38, x + sx*r*0.45 + r*0.2, y + r*1.55], fill=OSCURO)
    d.line([(x - r*0.95, y + r*0.1), (x - r*1.45, y - r*0.35)], fill=OSCURO, width=lw)
    d.line([(x + r*0.95, y + r*0.1), (x + r*1.4, y + r*0.55)], fill=OSCURO, width=lw)
    for hx, hy in ((x - r*1.45, y - r*0.35), (x + r*1.4, y + r*0.55)):
        d.ellipse([hx - r*0.14, hy - r*0.14, hx + r*0.14, hy + r*0.14], fill=OSCURO)
    # pelo de punta
    d.polygon([(x - r*0.1, y - r*0.95), (x + r*0.05, y - r*1.45), (x + r*0.2, y - r*0.92)], fill=AMARILLO, outline=OSCURO, width=lw)
    d.ellipse([x - r, y - r, x + r, y + r], fill=AMARILLO, outline=OSCURO, width=lw)
    d.ellipse([x - r*0.6, y - r*0.72, x - r*0.15, y - r*0.42], fill=(255, 245, 190))
    _ojos(d, x, y - r*0.1, r)
    d.chord([x - r*0.3, y + r*0.25, x + r*0.3, y + r*0.62], 0, 180, fill=OSCURO)
    d.chord([x - r*0.18, y + r*0.42, x + r*0.18, y + r*0.6], 0, 180, fill=(255, 110, 120))
    for sx in (-1, 1):
        d.ellipse([x + sx*r*0.62 - r*0.13, y + r*0.2, x + sx*r*0.62 + r*0.13, y + r*0.36], fill=(255, 150, 100))


def pixel(d, x, y, r):
    lw = int(r*0.07)
    for sx in (-1, 1):
        d.rectangle([x + sx*r*0.45 - r*0.1, y + r*0.9, x + sx*r*0.45 + r*0.1, y + r*1.4], fill=OSCURO)
        d.rectangle([x + sx*r*0.45 - r*0.22, y + r*1.35, x + sx*r*0.45 + r*0.22, y + r*1.5], fill=OSCURO)
        d.rectangle([min(x + sx*r*0.95, x + sx*r*1.35), y - r*0.05, max(x + sx*r*0.95, x + sx*r*1.35), y + r*0.12], fill=OSCURO)
    d.rounded_rectangle([x - r, y - r, x + r, y + r], radius=r*0.22, fill=(46, 214, 160), outline=OSCURO, width=lw)
    # pixeles de brillo
    d.rectangle([x - r*0.75, y - r*0.75, x - r*0.45, y - r*0.45], fill=(170, 250, 220))
    d.rectangle([x - r*0.45, y - r*0.75, x - r*0.25, y - r*0.6], fill=(170, 250, 220))
    _ojos(d, x, y - r*0.12, r, tam=0.25)
    d.rectangle([x - r*0.28, y + r*0.38, x + r*0.28, y + r*0.52], fill=OSCURO)
    d.rectangle([x - r*0.28, y + r*0.28, x - r*0.16, y + r*0.4], fill=OSCURO)
    d.rectangle([x + r*0.16, y + r*0.28, x + r*0.28, y + r*0.4], fill=OSCURO)


def agente(d, x, y, r):
    lw = int(r*0.07)
    # antena
    d.line([(x, y - r), (x + r*0.15, y - r*1.5)], fill=OSCURO, width=lw)
    d.ellipse([x + r*0.15 - r*0.17, y - r*1.5 - r*0.17, x + r*0.15 + r*0.17, y - r*1.5 + r*0.17], fill=(255, 80, 96), outline=OSCURO, width=lw)
    for sx in (-1, 1):
        d.line([(x + sx*r*0.4, y + r*0.85), (x + sx*r*0.4, y + r*1.4)], fill=OSCURO, width=lw)
        d.ellipse([x + sx*r*0.4 - r*0.22, y + r*1.32, x + sx*r*0.4 + r*0.22, y + r*1.52], fill=OSCURO)
        d.line([(x + sx*r*0.98, y + r*0.15), (x + sx*r*1.35, y + r*0.5)], fill=OSCURO, width=lw)
        d.ellipse([x + sx*r*1.35 - r*0.13, y + r*0.5 - r*0.13, x + sx*r*1.35 + r*0.13, y + r*0.5 + r*0.13], fill=OSCURO)
    d.ellipse([x - r, y - r, x + r, y + r], fill=(236, 240, 250), outline=OSCURO, width=lw)
    # pantalla
    d.rounded_rectangle([x - r*0.72, y - r*0.55, x + r*0.72, y + r*0.45], radius=r*0.3, fill=(20, 28, 60))
    for sx in (-1, 1):
        d.rounded_rectangle([x + sx*r*0.3 - r*0.13, y - r*0.32, x + sx*r*0.3 + r*0.13, y + r*0.0], radius=r*0.08, fill=(110, 200, 255))
    d.arc([x - r*0.25, y - r*0.05, x + r*0.25, y + r*0.3], 20, 160, fill=(110, 200, 255), width=int(r*0.07))


if __name__ == "__main__":
    base = fondo().resize((W*S, 1920*S))
    d = ImageDraw.Draw(base)
    nombres = [("A · Bolita", bolita), ("B · Píxel", pixel), ("C · Agente", agente)]
    for k, (nombre, f) in enumerate(nombres):
        y = (250 + k*580)*S
        # en grande
        f(d, 330*S, y + 170*S, 120*S)
        # y en pequeño entre los demas puntos, que es como se vera en la simulacion
        for j in range(9):
            px, py = (620 + (j % 3)*130)*S, (y + 60*S + (j//3)*120*S)
            if j == 4:
                f(d, px, py, 44*S)
            else:
                d.ellipse([px - 26*S, py - 26*S, px + 26*S, py + 26*S], fill=PUNTO)
        d.text((W*S/2, y - 30*S), nombre, font=F(64*S), fill=BLANCO, anchor="mm")
    base.resize((W, 1920), Image.LANCZOS).save(sys.argv[1])
