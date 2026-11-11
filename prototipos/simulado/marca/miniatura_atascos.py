"""Miniaturas (1280x720) del video de los atascos: dos versiones para probar
cual atrae mas (Probar y comparar de YouTube).

A: autopista vista desde arriba: un atasco enorme de luces de freno... y
   delante, la carretera vacia, con un circulo rojo: "¿Y EL ACCIDENTE?".
B: el circuito del video con el atasco en rojo y una flecha enorme:
   "EL ATASCO FANTASMA".
"""
import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FUENTE = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
S = 2
W, H = 1280*S, 720*S
TINTA = (20, 20, 26)
AMARILLO = (255, 214, 0)
ROJO = (235, 40, 50)


def coche(d, brillo, x, y, ang, largo, ancho, col, frena):
    dx, dy = math.cos(ang), math.sin(ang)
    nx, ny = -dy, dx
    pt = lambda a, b: (x + dx*a + nx*b, y + dy*a + ny*b)
    sombra = [pt(-largo/2 + 6*S, -ancho/2 + 6*S), pt(largo/2 + 6*S, -ancho/2 + 6*S), pt(largo/2 + 6*S, ancho/2 + 6*S), pt(-largo/2 + 6*S, ancho/2 + 6*S)]
    d.polygon(sombra, fill=(30, 30, 34))
    cuerpo = [pt(-largo/2, -ancho/2), pt(largo/2 - ancho*0.3, -ancho/2), pt(largo/2, -ancho*0.3),
              pt(largo/2, ancho*0.3), pt(largo/2 - ancho*0.3, ancho/2), pt(-largo/2, ancho/2)]
    d.polygon(cuerpo, fill=col, outline=TINTA, width=3*S)
    d.polygon([pt(largo*0.08, -ancho*0.38), pt(largo*0.3, -ancho*0.33), pt(largo*0.3, ancho*0.33), pt(largo*0.08, ancho*0.38)],
              fill=(170, 210, 240), outline=TINTA)
    d.polygon([pt(-largo*0.36, -ancho*0.36), pt(-largo*0.22, -ancho*0.38), pt(-largo*0.22, ancho*0.38), pt(-largo*0.36, ancho*0.36)],
              fill=(140, 180, 210))
    for lado in (-1, 1):
        px, py = pt(-largo/2 + 2*S, lado*ancho*0.32)
        r = ancho*(0.16 if frena else 0.1)
        d.ellipse([px - r, py - r, px + r, py + r], fill=(255, 50, 50) if frena else (120, 20, 20))
        if frena:
            ImageDraw.Draw(brillo).ellipse([px - r*2.2, py - r*2.2, px + r*2.2, py + r*2.2], fill=(255, 30, 30, 255))


def texto_gordo(img, xy, s, tam, col, ang=0, borde=14, anchor="mm"):
    f = ImageFont.truetype(FUENTE, int(tam*S))
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    sombra = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sombra).text((xy[0]*S + 8*S, xy[1]*S + 10*S), s, font=f, fill=(0, 0, 0, 200), anchor=anchor,
                                stroke_width=borde*S, stroke_fill=(0, 0, 0, 200))
    d.text((xy[0]*S, xy[1]*S), s, font=f, fill=col, anchor=anchor, stroke_width=borde*S, stroke_fill=TINTA)
    if ang:
        capa = capa.rotate(ang, center=(xy[0]*S, xy[1]*S), resample=Image.BICUBIC)
        sombra = sombra.rotate(ang, center=(xy[0]*S, xy[1]*S), resample=Image.BICUBIC)
    img.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(6*S)))
    img.alpha_composite(capa)


def cesped(w, h):
    img = Image.new("RGB", (w, h), (96, 168, 78))
    d = ImageDraw.Draw(img)
    rnd = np.random.default_rng(2)
    for _ in range(3000):
        x, y = rnd.uniform(0, w), rnd.uniform(0, h)
        d.line([(x, y), (x + rnd.uniform(-5, 5), y - 14)], fill=(80, 150, 66), width=3)
    return img.convert("RGBA")


def viñeta(img, fuerza=0.55):
    yy, xx = np.mgrid[0:img.height, 0:img.width].astype(np.float32)
    d = np.sqrt(((xx - img.width/2)/(img.width/2))**2 + ((yy - img.height/2)/(img.height/2))**2)
    a = (np.clip(d - 0.55, 0, 1)/0.6*fuerza*255).astype(np.uint8)
    v = Image.new("RGBA", img.size, (0, 0, 0, 0))
    v.putalpha(Image.fromarray(a))
    return Image.alpha_composite(img, v)


def version_a(salida):
    img = cesped(W, H)
    brillo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # autopista diagonal de 3 carriles, de abajo-izquierda a arriba-derecha
    ang = -math.radians(24)
    ux, uy = math.cos(ang), math.sin(ang)
    nx, ny = -uy, ux
    cx, cy = W*0.5, H*0.56
    ancho_c = 120*S
    def P(a, b):
        return (cx + ux*a + nx*b, cy + uy*a + ny*b)
    L = W*1.2
    d.polygon([P(-L, -ancho_c*1.75), P(L, -ancho_c*1.75), P(L, ancho_c*1.75), P(-L, ancho_c*1.75)], fill=(64, 66, 72))
    for b in (-1.65, 1.65):
        d.line([P(-L, b*ancho_c), P(L, b*ancho_c)], fill=(240, 240, 235), width=6*S)
    for b in (-0.5, 0.5):
        for a in np.arange(-L, L, 120*S):
            d.line([P(a, b*ancho_c*1.1), P(a + 60*S, b*ancho_c*1.1)], fill=(245, 245, 240), width=6*S)
    # el atasco: muchos coches pegados, casi todos rojos de freno
    rnd = np.random.default_rng(4)
    colores = [(230, 230, 235), (60, 110, 200), (40, 40, 46), (200, 40, 40), (240, 200, 60), (150, 150, 160)]
    for carril in (-1.1, 0, 1.1):
        a = -L*0.95
        while a < W*0.06:
            coche(d, brillo, *P(a, carril*ancho_c*1.0), ang, 150*S, 74*S, colores[int(rnd.integers(len(colores)))], frena=True)
            a += (162 + rnd.uniform(0, 14))*S
    img = Image.alpha_composite(img, brillo.filter(ImageFilter.GaussianBlur(7*S)))
    d = ImageDraw.Draw(img)
    # delante: carretera VACIA con un circulo rojo
    ox, oy = P(W*0.36, 0)
    r = 175*S
    for k in range(3):
        d.ellipse([ox - r - k*2*S, oy - r*0.8 - k*2*S, ox + r + k*2*S, oy + r*0.8 + k*2*S], outline=ROJO, width=14*S)
    img = viñeta(img)
    texto_gordo(img, (930, 120), "¿Y EL", 100, (255, 255, 255), ang=0)
    texto_gordo(img, (880, 228), "ACCIDENTE?", 104, AMARILLO, ang=0)
    texto_gordo(img, (ox/S, oy/S + 205), "NADA", 74, (255, 255, 255))
    img.convert("RGB").resize((1280, 720), Image.LANCZOS).save(salida)


def version_b(salida):
    img = cesped(W, H)
    brillo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy, r, anc = W*0.30, H*0.53, 230*S, 84*S
    d.ellipse([cx - r - anc*0.62, cy - r - anc*0.62, cx + r + anc*0.62, cy + r + anc*0.62], fill=(240, 240, 235))
    d.ellipse([cx - r - anc*0.55, cy - r - anc*0.55, cx + r + anc*0.55, cy + r + anc*0.55], fill=(64, 66, 72))
    d.ellipse([cx - r + anc*0.55, cy - r + anc*0.55, cx + r - anc*0.55, cy + r - anc*0.55], fill=(240, 240, 235))
    d.ellipse([cx - r + anc*0.62, cy - r + anc*0.62, cx + r - anc*0.62, cy + r - anc*0.62], fill=(96, 168, 78))
    # 20 coches: un grupo pegado en rojo (arriba a la derecha) y el resto suelto en verde
    angs = [k*0.075 for k in range(9)] + [0.9 + k*0.48 for k in range(10)]
    for k, a0 in enumerate(angs):
        a = -1.1 + a0
        x, y = cx + r*math.cos(a), cy + r*math.sin(a)
        atasco = k < 9
        col = (235, 50, 50) if atasco else (70, 200, 100)
        coche(d, brillo, x, y, a + math.pi/2, 100*S, 52*S, col, frena=atasco)
    img = Image.alpha_composite(img, brillo.filter(ImageFilter.GaussianBlur(10*S)))
    d = ImageDraw.Draw(img)
    # flecha enorme, del atasco hacia atras
    fx, fy = cx + (r + 150*S)*math.cos(-0.75), cy + (r + 150*S)*math.sin(-0.75)
    d.arc([cx - r - 150*S, cy - r - 150*S, cx + r + 150*S, cy + r + 150*S], math.degrees(-0.75), math.degrees(0.35),
          fill=ROJO, width=26*S)
    d.polygon([(fx - 40*S, fy + 10*S), (fx + 50*S, fy - 50*S), (fx + 46*S, fy + 52*S)], fill=ROJO)
    img = viñeta(img, 0.45)
    texto_gordo(img, (930, 210), "EL ATASCO", 104, (255, 255, 255))
    texto_gordo(img, (930, 330), "FANTASMA", 120, AMARILLO)
    texto_gordo(img, (930, 470), "0 accidentes", 64, (255, 255, 255), borde=10)
    img.convert("RGB").resize((1280, 720), Image.LANCZOS).save(salida)


def version_c(salida):
    """'TU SOLO puedes acabar con un atasco': el circuito con el atasco en
    rojo y UN coche azul marcado como 'TU', que es el que lo deshace."""
    img = cesped(W, H)
    brillo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy, r, anc = W*0.29, H*0.55, 228*S, 84*S
    d.ellipse([cx - r - anc*0.62, cy - r - anc*0.62, cx + r + anc*0.62, cy + r + anc*0.62], fill=(240, 240, 235))
    d.ellipse([cx - r - anc*0.55, cy - r - anc*0.55, cx + r + anc*0.55, cy + r + anc*0.55], fill=(64, 66, 72))
    d.ellipse([cx - r + anc*0.55, cy - r + anc*0.55, cx + r - anc*0.55, cy + r - anc*0.55], fill=(240, 240, 235))
    d.ellipse([cx - r + anc*0.62, cy - r + anc*0.62, cx + r - anc*0.62, cy + r - anc*0.62], fill=(96, 168, 78))
    # el atasco (rojo, pegados) delante del coche azul; detras, verdes
    angs = [k*0.075 for k in range(10)] + [0.95 + k*0.5 for k in range(9)]
    azul_ang = None
    for k, a0 in enumerate(angs):
        a = -1.0 + a0
        x, y = cx + r*math.cos(a), cy + r*math.sin(a)
        atasco = k < 10
        coche(d, brillo, x, y, a + math.pi/2, 100*S, 52*S, (235, 50, 50) if atasco else (70, 200, 100), frena=atasco)
    a = -1.0 - 0.42                                   # el tuyo, justo antes del atasco y con hueco
    bx, by = cx + r*math.cos(a), cy + r*math.sin(a)
    ImageDraw.Draw(brillo).ellipse([bx - 120*S, by - 120*S, bx + 120*S, by + 120*S], fill=(80, 160, 255, 255))
    img = Image.alpha_composite(img, brillo.filter(ImageFilter.GaussianBlur(26*S)))
    d = ImageDraw.Draw(img)
    coche(d, Image.new("RGBA", (W, H)), bx, by, a + math.pi/2, 112*S, 58*S, (60, 140, 255), frena=False)
    img = viñeta(img, 0.45)
    texto_gordo(img, (945, 200), "TÚ SOLO", 140, AMARILLO)
    texto_gordo(img, (945, 340), "PUEDES ACABAR", 74, (255, 255, 255), borde=11)
    texto_gordo(img, (945, 430), "CON UN ATASCO", 74, (255, 255, 255), borde=11)
    img.convert("RGB").resize((1280, 720), Image.LANCZOS).save(salida)


if __name__ == "__main__":
    version_a(sys.argv[1])
    version_b(sys.argv[2])
    if len(sys.argv) > 3:
        version_c(sys.argv[3])
