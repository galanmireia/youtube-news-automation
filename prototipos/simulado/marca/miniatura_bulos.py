"""Miniatura (1280x720) del video largo de los bulos.

La idea en un vistazo: una red ENORME en rojo (el bulo) frente a una red
pequeñita en verde (la verdad), «LA MENTIRA GANA ×11» en grande, y el Agente
asustado delante (el personaje del canal, para que se reconozca).

    python3 miniatura_bulos.py salida.png
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"shorts"))
from estilo import agente  # noqa: E402

FUENTE = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FUENTE_B = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
S = 2
W, H = 1280*S, 720*S
ROJO, VERDE, GRIS, AMARILLO, BLANCO, OSCURO = (255, 60, 80), (60, 226, 160), (84, 98, 146), (255, 210, 40), (250, 250, 255), (8, 10, 24)


def fondo():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt((xx - W*0.33)**2 + (yy - H*0.5)**2)/(W*0.65)
    k = np.clip(d, 0, 1)[..., None]
    img = np.array((70, 22, 40), np.float32)*(1 - k) + np.array((8, 8, 22), np.float32)*k
    return Image.fromarray(img.astype(np.uint8)).convert("RGBA")


def red(img, cx, cy, radio, n, encendido_hasta, semilla, col):
    rnd = np.random.default_rng(semilla)
    pts = []
    while len(pts) < n:
        a, r = rnd.uniform(0, 2*math.pi), radio*math.sqrt(rnd.uniform(0, 1))
        p = (cx + r*math.cos(a), cy + r*math.sin(a)*0.9)
        if all(math.dist(p, q) > radio*0.085 for q in pts):
            pts.append(p)
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    halo = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d, dh = ImageDraw.Draw(capa), ImageDraw.Draw(halo)
    P = np.array(pts)
    on = [math.dist(p, (cx, cy)) < encendido_hasta for p in pts]
    for i, p in enumerate(pts):
        dist = np.hypot(*(P - p).T)
        for j in np.argsort(dist)[1:4]:
            if j > i:
                c = col if (on[i] and on[j]) else (70, 84, 130)
                d.line([p, tuple(P[j])], fill=c + (190 if c == col else 110,), width=3*S)
    r0 = radio*0.028
    for p, o in zip(pts, on):
        r = r0*(1.25 if o else 0.9)
        if o:
            dh.ellipse([p[0] - r*3.2, p[1] - r*3.2, p[0] + r*3.2, p[1] + r*3.2], fill=col + (255,))
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=(col if o else GRIS) + (255,))
    halo = halo.filter(ImageFilter.GaussianBlur(12*S))
    halo.putalpha(halo.getchannel("A").point(lambda v: int(v*0.65)))
    return Image.alpha_composite(Image.alpha_composite(img, halo), capa)


def texto(img, xy, s, tam, col, borde=14, anchor="mm", fuente=FUENTE):
    f = ImageFont.truetype(fuente, int(tam*S))
    sombra = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sombra).text((xy[0]*S + 8*S, xy[1]*S + 10*S), s, font=f, fill=(0, 0, 0, 230), anchor=anchor,
                                stroke_width=borde*S, stroke_fill=(0, 0, 0, 230))
    img.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(7*S)))
    ImageDraw.Draw(img).text((xy[0]*S, xy[1]*S), s, font=f, fill=col, anchor=anchor,
                             stroke_width=borde*S, stroke_fill=OSCURO)


if __name__ == "__main__":
    img = fondo()
    img = red(img, W*0.30, H*0.50, H*0.47, 170, H*0.46, 5, ROJO)        # el bulo: casi toda encendida
    img = red(img, W*0.70, H*0.80, H*0.12, 22, H*0.08, 8, VERDE)        # la verdad: pequeñita (lejos de la esquina de la duracion)
    texto(img, (905, 120), "LA MENTIRA", 100, BLANCO)
    texto(img, (905, 250), "GANA", 150, ROJO, borde=16)
    texto(img, (1020, 400), "×11", 150, AMARILLO, borde=16)
    texto(img, (735, 668), "la verdad", 40, VERDE, borde=8, fuente=FUENTE_B)
    base = img.convert("RGB").resize((1280, 720), Image.LANCZOS)
    agente(base, 175, 520, 120, "susto", 1.0, "arriba")
    base.save(sys.argv[1])
