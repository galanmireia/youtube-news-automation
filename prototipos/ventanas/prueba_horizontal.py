"""ACROSS THE STREET — prueba en horizontal (16:9) para los videos largos de YouTube.

  1) el edificio entero de noche (5 ventanas por planta, la 2B siempre a oscuras)
  2) un capitulo: la vista se mete en una ventana y sale el rotulo con la hora
"""
import math, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import prueba_estilo as P
from prueba_estilo import silueta, ventana, NEGRO

W, H = 1920, 1080
OUT = P.OUT
SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf"

def serif(px):
    return ImageFont.truetype(SERIF, int(px))

def pareja_cena(c, w, h):                     # 3A: los recien casados, cenando con una vela
    c.rectangle([w*0.2, h*0.66, w*0.8, h*0.7], fill=NEGRO)
    c.rectangle([w*0.48, h*0.56, w*0.52, h*0.66], fill=NEGRO)
    c.ellipse([w*0.485, h*0.5, w*0.515, h*0.56], fill=(255, 240, 200))
    silueta(c, w*0.24, h*1.0, h*0.82, "de_pie", "coleta", True, 1)
    silueta(c, w*0.78, h*1.0, h*0.9, "señala", "corto", False, -1)

def tele(c, w, h):                            # 2C: los abuelos, peleandose por el mando
    c.rounded_rectangle([w*0.3, h*0.52, w*0.75, h*0.75], radius=int(w*0.04), fill=NEGRO)
    silueta(c, w*0.25, h*1.0, h*0.8, "señala", "moño", True, 1)
    silueta(c, w*0.75, h*1.0, h*0.84, "brazo_arriba", "corto", False, -1)

def oscura_brillo(c, w, h):                   # 2B: a oscuras... solo el brillo de una pantalla
    pass

def edificio_h(t=0.0):
    img = Image.new("RGB", (W, H), (18, 22, 52)); d = ImageDraw.Draw(img)
    for j in range(0, 200):
        f = j/200
        d.line([(0, j), (W, j)], fill=(int(30 - 12*f), int(30 - 8*f), int(76 - 24*f)))
    rnd = random.Random(2)
    for _ in range(90):
        x, y = rnd.uniform(0, W), rnd.uniform(0, 150)
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(220, 220, 240))
    d.ellipse([1700, 30, 1800, 130], fill=(250, 240, 210))
    x0b, x1b = 150, W - 150
    d.rectangle([x0b, 140, x1b, 980], fill=(52, 44, 66))
    for fila in range(0, 30):
        for col in range(18):
            x = x0b + col*100 + (50 if fila % 2 else 0); y = 140 + fila*28
            if x < x1b - 96:
                d.rectangle([x, y, x + 96, y + 25], outline=(60, 52, 76), width=2)
    d.rectangle([x0b - 20, 115, x1b + 20, 150], fill=(66, 58, 82))
    plan = [  # (planta, columna) -> escena (None: apagada)
        [P.beso, None, pareja_cena, P.vacia, None],
        [P.amante, "2B", P.pelea, tele, None],
        [P.sola, P.maleta, None, P.test, P.vacia],
    ]
    for fila in range(3):
        for col in range(5):
            esc = plan[fila][col]
            vx, vy = 230 + col*310, 200 + fila*240
            if esc == "2B":                       # la 2B: siempre a oscuras, con el brillo de una pantalla
                ventana(img, vx, vy, 230, 170, None, encendida=False)
                d = ImageDraw.Draw(img)
                d.ellipse([vx + 140 - 6, vy + 110 - 4, vx + 140 + 6, vy + 110 + 4], fill=(150, 200, 255))
                img = P_luz(img, vx + 140, vy + 110, 26)
            else:
                ventana(img, vx, vy, 230, 170, esc or P.vacia, encendida=esc is not None)
            d = ImageDraw.Draw(img)
            d.text((vx + 115, vy - 22), f"{3 - fila}{'ABCDE'[col]}", fill=(150, 140, 170), anchor="mm")
    d.rectangle([W/2 - 110, 840, W/2 + 110, 980], fill=(30, 26, 40))
    d.rectangle([W/2 - 95, 855, W/2 + 95, 980], fill=(255, 196, 120))
    # la calle, en primer plano: la farola y un coche aparcado, tambien en silueta
    d.rectangle([0, 980, W, H], fill=(26, 26, 36))
    d.rectangle([0, 975, W, 990], fill=(40, 40, 52))
    d.rectangle([90, 520, 104, 1000], fill=(10, 10, 16))
    d.polygon([(60, 520), (134, 520), (118, 490), (76, 490)], fill=(10, 10, 16))
    img = P_luz(img, 97, 560, 120, (255, 210, 140), 0.35)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([1350, 930, 1760, 1040], radius=40, fill=(10, 10, 16))
    d.rounded_rectangle([1430, 870, 1660, 950], radius=40, fill=(10, 10, 16))
    for k in (1440, 1680):
        d.ellipse([k - 45, 1000, k + 45, 1080], fill=(6, 6, 10))
    return img

def P_luz(img, x, y, rad, color=(150, 200, 255), fuerza=0.5):
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).ellipse([x - rad, y - rad, x + rad, y + rad], fill=int(255*fuerza))
    m = m.filter(ImageFilter.GaussianBlur(rad*0.5))
    return Image.composite(Image.new("RGB", img.size, color), img, m)

def capitulo(escena, hora, piso):
    """La vista metida en una ventana, con el rotulo del capitulo (la hora y el piso)."""
    img = Image.new("RGB", (W, H), (52, 44, 66)); d = ImageDraw.Draw(img)
    for fila in range(0, 20):
        for col in range(12):
            x = col*180 + (90 if fila % 2 else 0); y = fila*56
            d.rectangle([x, y, x + 176, y + 52], outline=(62, 54, 78), width=4)
    ventana(img, 460, 90, 1000, 820, escena, cortina=0.28)
    img = img.filter(ImageFilter.GaussianBlur(0.3))
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0)); c = ImageDraw.Draw(capa)
    for k in range(40):                                  # oscurece los bordes (mirar de lejos, de noche)
        f = k/40
        c.rectangle([k*12, k*7, W - k*12, H - k*7], outline=(6, 6, 12, int(200*(1 - f)**2)), width=14)
    img = img.convert("RGBA"); img.alpha_composite(capa); img = img.convert("RGB")
    d = ImageDraw.Draw(img)
    d.text((90, 930), hora, font=serif(84), fill=(255, 214, 140), stroke_width=3, stroke_fill=(10, 8, 16))
    d.text((96, 1020), piso, font=serif(46), fill=(240, 230, 230), stroke_width=2, stroke_fill=(10, 8, 16))
    return img

if __name__ == "__main__":
    Path(OUT).mkdir(exist_ok=True)
    edificio_h().save(OUT + "h_edificio.png")
    capitulo(P.amante, "21:40", "Apartment 2A").save(OUT + "h_capitulo.png")
    print("ok")
