"""BLOCK 7 — la cabecera de la serie (la misma en todos los capitulos, ~7.4 s).

Como en los culebrones: la fachada al atardecer, se encienden las ventanas una a
una, se abren las cortinas y en cada casa aparece un matrimonio con su nombre.
Al final, todas las ventanas encendidas (y en la 2B, el cactus soltero, asomado)
y el logo dorado. Cada capitulo va de un matrimonio; Poke los enreda a todos.
"""
import math
from PIL import Image, ImageDraw, ImageFont

import mundo as Mu
from mundo import T, W, H, suave

SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf"
ORO = (236, 196, 96)

def serif(px):
    return ImageFont.truetype(SERIF, int(px))

# ---------------------------------------------------------------- los matrimonios
def bubble_mag(img, w, h, t, k):
    fondo = (250, 214, 190)
    Mu.mag(img, w*0.7, h*1.08, h*0.85, dict(fondo=fondo, guino=1.0 if k > 0.45 else 0.0, mira=(-0.5, 0), feliz=0.0), t)
    Mu.bubble(img, w*0.3, h*0.52, h*0.62, dict(rubor=True, feliz=1.0 if k > 0.45 else 0.0, mira=(0.8, 0.0), cuerda=False), t)
    Mu.corazon(ImageDraw.Draw(img), w*0.5, h*0.16 - 10*math.sin(t*4), h*0.06)

def sal_pimienta(img, w, h, t, k):
    Mu.salero(img, w*0.28, h*1.02, h*0.68, dict(prismaticos=k > 0.45, mira=(0.6, 0), boca="o"), t)
    Mu.salero(img, w*0.72, h*1.02, h*0.68, dict(marido=True, mira=(-0.6, 0), boca="plana", ceja=0.4), t, pimienta=True)

def pop_cubi(img, w, h, t, k):
    Mu.pop(img, w*0.27, h*1.0, h*0.66, dict(pajarita=True, enfado=1.0 if k > 0.45 else 0.0, boca="dolor" if k > 0.45 else "sonrisa",
                                          mira=(0.7, 0)), t)
    if k > 0.45:
        Mu.humo_enfado(ImageDraw.Draw(img), w*0.27, h*0.3, h*0.07, t)
    Mu.cubi(img, w*0.74, h*1.0, h*0.6, dict(pestanas=1, lazo=True, gotas=True, mira=(0.6, -0.3) if k > 0.45 else (-0.7, 0),
                                           boca="sonrisa"), t)

def huevo_tosti(img, w, h, t, k):
    Mu.huevo_cara(img, w*0.28, h*0.6, h*0.6, dict(susto=1.0 if k > 0.45 else 0.0, mira=(0.7, 0), burbujas=True), t)
    Mu.tosti(img, w*0.74, h*1.04, h*0.72, dict(enfado=1.0 if k > 0.45 else 0.0, brazos_jarra=k > 0.45, mira=(-0.7, 0)), t)

def poke_solo(img, w, h, t, k):
    Mu.poke(img, w*0.5, h*1.25, h*1.0, dict(mira=(0.0, 0.0), boca="sonrisa", feliz=1.0 if k > 0.5 else 0.0), t)

PAREJAS = [  # (quien, nombre, piso, color de dentro, ventana en la fachada (columna, fila))
    (bubble_mag, "Bubble & Mag", "2A", (250, 214, 190), (0, 1)),
    (sal_pimienta, "Salt & Pepper", "2C", (236, 226, 200), (2, 1)),
    (pop_cubi, "Pop & Cubi", "3A", (214, 234, 246), (0, 0)),
    (huevo_tosti, "Mr. Egg & Tosti", "1B", (246, 230, 200), (1, 2)),
]

def interior(quien, color, w, h, t, k):
    im = Image.new("RGB", (int(w), int(h)), color); d = ImageDraw.Draw(im)
    d.rectangle([0, h*0.78, w, h], fill=tuple(int(v*0.85) for v in color))
    quien(im, w, h, t, k)
    return im

# ---------------------------------------------------------------- la fachada
VENT = (300, 290)

def ventana_xy(col, fila):
    return 70 + col*340, 300 + fila*420

def fachada(t, encendidas, k_poke=0.0, cielo=1.0):
    img = Image.new("RGB", (W, H), (250, 170, 120)); d = ImageDraw.Draw(img)
    for i in range(12):                              # el cielo del atardecer
        f = i/12
        d.rectangle([0, i*20, W, i*20 + 20], fill=(int(120 + 130*f), int(90 + 80*f), int(150 - 30*f)))
    d.rectangle([0, 200, W, H], fill=(206, 160, 136), outline=T, width=6)
    for fila in range(0, 40):
        for col in range(10):
            x = col*120 + (60 if fila % 2 else 0); y = 200 + fila*46
            d.rectangle([x, y, x + 116, y + 42], outline=(184, 140, 118), width=2)
    d.rounded_rectangle([W/2 - 210, 140, W/2 + 210, 250], radius=18, fill=(52, 50, 64), outline=T, width=6)
    d.text((W/2, 195), "Block 7", font=serif(80), fill=ORO, anchor="mm")
    for fila in range(3):
        for col in range(3):
            x, y = ventana_xy(col, fila)
            luz = None
            for j, (quien, nombre, piso, color, (c, f)) in enumerate(PAREJAS):
                if (c, f) == (col, fila) and j in encendidas:
                    luz = interior(quien, color, *VENT, t, 1.0)
            if (col, fila) == (1, 1) and k_poke > 0:
                luz = interior(poke_solo, (190, 220, 170), *VENT, t, k_poke)
            if luz is not None:
                img.paste(luz, (x, y))
            else:
                d.rectangle([x, y, x + VENT[0], y + VENT[1]], fill=(52, 56, 84))
            d.rectangle([x, y, x + VENT[0], y + VENT[1]], outline=T, width=8)
            d.line([(x + VENT[0]/2, y), (x + VENT[0]/2, y + VENT[1])], fill=T, width=5)
            d.rectangle([x - 14, y + VENT[1], x + VENT[0] + 14, y + VENT[1] + 20], fill=(240, 236, 228), outline=T, width=4)
            d.rounded_rectangle([x + VENT[0] - 70, y + 10, x + VENT[0] - 10, y + 50], radius=8, fill=(250, 246, 236), outline=T, width=3)
            d.text((x + VENT[0] - 40, y + 30), f"{3 - fila}{'ABC'[col]}", font=Mu.fuente(26), fill=T, anchor="mm")
    d.rectangle([W/2 - 150, 1560, W/2 + 150, H], fill=(120, 84, 60), outline=T, width=8)
    d.rectangle([0, 1820, W, H], fill=(150, 150, 160))
    return img

# ---------------------------------------------------------------- los planos de la cabecera
def cortinas(d, x0, y0, x1, y1, k):
    """Cortinas de terciopelo rojo que se abren (k: 0 cerradas, 1 abiertas)."""
    ancho = (x1 - x0)/2*(1 - 0.82*k)
    for lado in (-1, 1):
        xa = x0 if lado < 0 else x1 - ancho
        d.rectangle([xa, y0, xa + ancho, y1], fill=(150, 20, 40), outline=T, width=5)
        for j in range(1, 5):
            xx = xa + ancho*j/5
            d.line([(xx, y0), (xx, y1)], fill=(110, 10, 28), width=6)
    d.rectangle([x0 - 20, y0 - 40, x1 + 20, y0 + 20], fill=(212, 170, 70), outline=T, width=5)

def p_ventana(i):
    quien, nombre, piso, color, _ = PAREJAS[i]
    def plano(lt, t, dur=1.25):
        img = Image.new("RGB", (W, H), (206, 160, 136)); d = ImageDraw.Draw(img)
        for fila in range(0, 42):
            for col in range(10):
                x = col*120 + (60 if fila % 2 else 0); y = fila*46
                d.rectangle([x, y, x + 116, y + 42], outline=(184, 140, 118), width=2)
        x0, y0, x1, y1 = 80, 330, 1000, 1330
        img.paste(interior(quien, color, x1 - x0, y1 - y0, t, suave((lt - 0.2)/0.6)), (x0, y0))
        d = ImageDraw.Draw(img)
        cortinas(d, x0, y0, x1, y1, suave(lt/0.35))
        d.rectangle([x0, y0, x1, y1], outline=T, width=14)
        d.rectangle([x0 - 30, y1, x1 + 30, y1 + 40], fill=(240, 236, 228), outline=T, width=6)
        a = suave((lt - 0.25)/0.3)
        if a > 0:                                   # el nombre, como en los creditos de una telenovela
            yy = 1520 + 30*(1 - a)
            d.rounded_rectangle([100, yy - 90, W - 100, yy + 110], radius=30, fill=(60, 10, 24), outline=ORO, width=6)
            d.text((W/2, yy - 10), nombre, font=serif(96), fill=ORO, anchor="mm")
            d.text((W/2, yy + 70), f"Apartment {piso}", font=serif(44), fill=(240, 226, 226), anchor="mm")
        return img, (W/2, H/2, 1.0 + 0.04*lt/dur)
    return plano

def p_fachada(lt, t):
    return fachada(t, set()), (W/2, 900, 1.0 + 0.05*lt)

def logo(titulo):
    def plano(lt, t, dur=2.0):
        img = fachada(t, {0, 1, 2, 3}, k_poke=suave((lt - 0.5)/0.4))
        d = ImageDraw.Draw(img)
        if lt > 0.5:                                # el soltero de la 2B: un signo de interrogacion
            Mu.texto(d, 540 + 110, 790 - 20*math.sin(t*5), "?", 70, (255, 214, 60))
        a = suave((lt - 0.15)/0.35)
        capa = Image.new("RGBA", (W, H), (0, 0, 0, 0)); c = ImageDraw.Draw(capa)
        c.rectangle([0, 1470, W, 1840], fill=(40, 6, 16, int(225*a)))
        img = img.convert("RGBA"); img.alpha_composite(capa); img = img.convert("RGB"); d = ImageDraw.Draw(img)
        if a > 0:
            col = tuple(int(40 + (v - 40)*a) for v in ORO)
            d.text((W/2, 1580), "Block 7", font=serif(170), fill=col, anchor="mm", stroke_width=5, stroke_fill=(40, 6, 16))
            d.text((W/2, 1700), "Love. Lies. Neighbours.", font=serif(56), fill=tuple(int(40 + (v - 40)*a) for v in (250, 236, 236)), anchor="mm")
        b = suave((lt - 0.9)/0.4)
        if b > 0 and titulo:
            d.text((W/2, 1790), titulo, font=serif(50), fill=tuple(int(40 + (v - 40)*b) for v in (255, 150, 170)), anchor="mm")
        return img, (W/2, H/2, 1.0)
    return plano

def planos(titulo):
    """La cabecera lista para meter en el GUION de cualquier capitulo: [(fn, dur, sfx), ...]."""
    out = [(p_fachada, 0.9, [(0.0, "cabecera7.95")])]
    out += [(p_ventana(i), 1.25, [(0.05, "swip")]) for i in range(4)]
    out += [(logo(titulo), 1.25 + 1.0, [])]
    return out
