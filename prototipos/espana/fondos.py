"""Fondos y banderas de la España de 1868-1873, para los muñecos nuevos.

Banderas de la epoca, ondeando:
  - "espana": la rojigualda con el escudo coronado (la monarquia).
  - "republica": la rojigualda con el escudo SIN corona real (la Primera
    Republica puso corona mural; nada de la tricolor morada, que es de 1931).
  - "italia": la tricolor del Reino de Italia con el escudo de Saboya.
  - "francia" y "prusia" (negra y blanca, los colores de Prusia).
Fondos: el salon del trono (sin la cruz de Borgoña, que no pega en 1870), el
Congreso, el despacho de Prim con el mapa de Europa, el puerto de Cartagena
con la fragata Numancia, y una calle de Madrid.
"""
import math
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
TINTA = (38, 28, 30)
ORO = (226, 180, 60)
ROJO_ES, AMARILLO_ES = (190, 22, 34), (250, 196, 0)
SUELO = 0.80                 # donde pisan los muñecos (fraccion de H)
FUENTE = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"


def _escudo(d, cx, cy, s, corona=True):
    """Escudo simplificado: cuartelado de castillos y leones, granada y, en la
    monarquia, corona real cerrada; en la republica, corona mural (almenas)."""
    d.rounded_rectangle([cx - s*0.5, cy - s*0.55, cx + s*0.5, cy + s*0.6], radius=int(s*0.35),
                        fill=(200, 40, 40), outline=TINTA, width=max(2, int(s*0.05)))
    d.rectangle([cx, cy - s*0.55, cx + s*0.5, cy], fill=(240, 236, 228))
    d.rectangle([cx - s*0.5, cy, cx, cy + s*0.45], fill=(240, 236, 228))
    for qx, qy, col in ((-0.25, -0.27, ORO), (0.25, 0.22, ORO), (0.25, -0.27, (130, 40, 120)), (-0.25, 0.22, (130, 40, 120))):
        d.rectangle([cx + s*qx - s*0.1, cy + s*qy - s*0.1, cx + s*qx + s*0.1, cy + s*qy + s*0.12], fill=col)
    if corona:
        d.polygon([(cx - s*0.45, cy - s*0.6), (cx - s*0.5, cy - s*0.95), (cx - s*0.2, cy - s*0.75), (cx, cy - s*1.05),
                   (cx + s*0.2, cy - s*0.75), (cx + s*0.5, cy - s*0.95), (cx + s*0.45, cy - s*0.6)], fill=ORO, outline=TINTA)
    else:
        d.rectangle([cx - s*0.42, cy - s*0.85, cx + s*0.42, cy - s*0.6], fill=(200, 160, 70), outline=TINTA)
        for k in range(4):
            x0 = cx - s*0.42 + k*s*0.24
            d.rectangle([x0, cy - s*0.97, x0 + s*0.12, cy - s*0.85], fill=(200, 160, 70), outline=TINTA)


def _franjas(tipo):
    if tipo in ("espana", "republica"):
        return "h", [(ROJO_ES, 0.25), (AMARILLO_ES, 0.5), (ROJO_ES, 0.25)]
    if tipo == "italia":
        return "v", [((0, 140, 70), 1/3), ((250, 250, 250), 1/3), ((206, 43, 55), 1/3)]
    if tipo == "francia":
        return "v", [((0, 50, 150), 1/3), ((250, 250, 250), 1/3), ((226, 30, 40), 1/3)]
    if tipo == "prusia":
        return "h", [((20, 20, 22), 0.5), ((250, 250, 250), 0.5)]
    raise ValueError(tipo)


def bandera(img, tipo, x, y, ancho, t=0.0, nombre=None, asta=True, alto_asta=1.55):
    """Bandera ondeando con su asta; (x, y) es el pie del asta."""
    alto = ancho*0.66
    tela = Image.new("RGBA", (int(ancho), int(alto)), (0, 0, 0, 0))
    d = ImageDraw.Draw(tela)
    sentido, franjas = _franjas(tipo)
    pos = 0.0
    for col, frac in franjas:
        if sentido == "h":
            d.rectangle([0, alto*pos, ancho, alto*(pos + frac)], fill=col)
        else:
            d.rectangle([ancho*pos, 0, ancho*(pos + frac), alto], fill=col)
        pos += frac
    if tipo in ("espana", "republica"):
        _escudo(d, ancho*0.33, alto*0.52, alto*0.3, corona=(tipo == "espana"))
    elif tipo == "italia":                       # escudo de Saboya: cruz blanca en rojo, borde azul
        cx, cy, s = ancho/2, alto/2, alto*0.22
        d.rectangle([cx - s*0.75, cy - s*0.9, cx + s*0.75, cy + s*0.9], fill=(30, 80, 170))
        d.rectangle([cx - s*0.62, cy - s*0.77, cx + s*0.62, cy + s*0.77], fill=(200, 30, 40))
        d.rectangle([cx - s*0.13, cy - s*0.77, cx + s*0.13, cy + s*0.77], fill=(250, 250, 250))
        d.rectangle([cx - s*0.62, cy - s*0.13, cx + s*0.62, cy + s*0.13], fill=(250, 250, 250))
        d.polygon([(cx - s*0.6, cy - s*0.9), (cx - s*0.65, cy - s*1.3), (cx, cy - s*1.05), (cx + s*0.65, cy - s*1.3),
                   (cx + s*0.6, cy - s*0.9)], fill=ORO, outline=TINTA)
    d.rectangle([0, 0, ancho - 1, alto - 1], outline=TINTA, width=3)
    # ondear: cada columna sube y baja, y se oscurece en los valles
    a = tela.load()
    ondeada = Image.new("RGBA", (int(ancho), int(alto + ancho*0.12)), (0, 0, 0, 0))
    for cxp in range(int(ancho)):
        fase = cxp/ancho
        dy = math.sin(fase*6.0 - t*5)*ancho*0.035*fase
        luz = 1 + 0.18*math.cos(fase*6.0 - t*5)*fase
        col = tela.crop((cxp, 0, cxp + 1, int(alto)))
        if luz != 1:
            px = col.load()
            for yy in range(col.height):
                r, g_, b, al = px[0, yy]
                px[0, yy] = (min(255, int(r*luz)), min(255, int(g_*luz)), min(255, int(b*luz)), al)
        ondeada.paste(col, (cxp, int(ancho*0.06 + dy)), col)
    top = y - ancho*alto_asta
    if asta:
        dd = ImageDraw.Draw(img)
        dd.line([(x, y), (x, top - ancho*0.06)], fill=(120, 90, 50), width=max(6, int(ancho*0.035)))
        dd.ellipse([x - ancho*0.04, top - ancho*0.12, x + ancho*0.04, top - ancho*0.04], fill=ORO, outline=TINTA)
    img.alpha_composite(ondeada, (int(x), int(top - ancho*0.06)))
    if nombre:
        f = ImageFont.truetype(FUENTE, int(ancho*0.2))
        ImageDraw.Draw(img).text((x + ancho/2, top + alto + ancho*0.2), nombre, font=f, fill=(255, 255, 255),
                                 stroke_width=6, stroke_fill=TINTA, anchor="mm")


def _gradiente(img, arriba, abajo, y0=0, y1=H):
    d = ImageDraw.Draw(img)
    for y in range(int(y0), int(y1)):
        k = (y - y0)/max(1, (y1 - y0))
        d.line([(0, y), (W, y)], fill=tuple(int(arriba[i]*(1 - k) + abajo[i]*k) for i in range(3)))


def _suelo_madera(img, y0):
    d = ImageDraw.Draw(img)
    _gradiente(img, (150, 100, 60), (110, 70, 40), y0, H)
    for k in range(-12, 13):
        d.line([(W/2 + k*40, y0), (W/2 + k*160, H)], fill=(96, 62, 36), width=3)
    for y in (y0 + 60, y0 + 160, y0 + 300):
        d.line([(0, y), (W, y)], fill=(96, 62, 36), width=2)


def palacio(t=0.0, trono=True):
    """El salon del trono del Palacio Real: paredes de damasco rojo, zocalo y
    molduras doradas, cortinajes, el trono bajo su dosel y la rojigualda."""
    img = Image.new("RGBA", (W, H))
    _gradiente(img, (150, 30, 40), (110, 20, 30), 0, H*SUELO)
    d = ImageDraw.Draw(img)
    rnd = random.Random(4)
    for k in range(260):                         # el damasco
        x, y = rnd.uniform(0, W), rnd.uniform(0, H*SUELO*0.85)
        d.ellipse([x - 9, y - 14, x + 9, y + 14], outline=(170, 50, 58), width=3)
    d.rectangle([0, H*SUELO*0.86, W, H*SUELO], fill=(90, 18, 26))
    d.line([(0, H*SUELO*0.86), (W, H*SUELO*0.86)], fill=ORO, width=10)
    d.rectangle([0, 60, W, 90], fill=ORO)
    for x in (60, W - 60):                       # cortinajes
        d.polygon([(x - 90, 0), (x + 90, 0), (x + 40, H*SUELO), (x - 40, H*SUELO)], fill=(120, 18, 30), outline=TINTA)
        d.line([(x - 70, H*0.34), (x + 70, H*0.36)], fill=ORO, width=12)
    if trono:
        cx = W/2
        d.polygon([(cx - 230, 230), (cx + 230, 230), (cx + 200, 330), (cx - 200, 330)], fill=(150, 20, 34), outline=TINTA)
        d.line([(cx - 230, 232), (cx + 230, 232)], fill=ORO, width=10)
        _escudo(d, cx, 470, 120, corona=True)
        d.rounded_rectangle([cx - 150, 640, cx + 150, 1250], radius=40, fill=ORO, outline=TINTA, width=5)
        d.rounded_rectangle([cx - 115, 680, cx + 115, 1100], radius=30, fill=(170, 24, 40), outline=TINTA, width=4)
        d.rectangle([cx - 200, 1130, cx + 200, 1230], fill=(170, 24, 40), outline=TINTA, width=4)
    _suelo_madera(img, H*SUELO)
    d = ImageDraw.Draw(img)
    d.rectangle([W*0.15, H*SUELO + 40, W*0.85, H], fill=(150, 20, 34))        # la alfombra
    d.line([(W*0.15, H*SUELO + 40), (W*0.15, H)], fill=ORO, width=8)
    d.line([(W*0.85, H*SUELO + 40), (W*0.85, H)], fill=ORO, width=8)
    return img


def congreso(t=0.0, tipo_bandera="espana"):
    """El hemiciclo del Congreso: escaños rojos en gradas, la tribuna, la
    bandera, y las columnas."""
    img = Image.new("RGBA", (W, H))
    _gradiente(img, (232, 218, 190), (200, 182, 150), 0, H*SUELO)
    d = ImageDraw.Draw(img)
    for x in (80, W - 80):
        d.rectangle([x - 45, 120, x + 45, H*SUELO], fill=(240, 232, 214), outline=TINTA, width=4)
        for k in range(4):
            d.line([(x - 30 + 20*k, 140), (x - 30 + 20*k, H*SUELO - 20)], fill=(210, 200, 180), width=3)
        d.rectangle([x - 60, 100, x + 60, 140], fill=(220, 210, 190), outline=TINTA, width=4)
    for fila in range(5):                        # gradas con escaños
        y = H*0.42 + fila*110
        d.rectangle([140, y, W - 140, y + 100], fill=(140, 30, 40), outline=TINTA, width=3)
        for k in range(10):
            x = 160 + k*78
            d.rounded_rectangle([x, y + 10, x + 62, y + 70], radius=12, fill=(176, 40, 52), outline=TINTA, width=2)
    d.rectangle([W/2 - 200, H*0.25, W/2 + 200, H*0.36], fill=(120, 80, 50), outline=TINTA, width=4)
    d.text((W/2, H*0.305), "CONGRESO", font=ImageFont.truetype(FUENTE, 54), fill=ORO, anchor="mm")
    _suelo_madera(img, H*SUELO)
    bandera(img, tipo_bandera, W - 300, int(H*0.62), 200, t)
    return img


def despacho(t=0.0):
    """El despacho de Prim: paneles de madera, el mapa de EUROPA (busca rey
    por toda ella), una ventana y un velon."""
    img = Image.new("RGBA", (W, H))
    _gradiente(img, (226, 210, 180), (196, 176, 140), 0, H*SUELO)
    d = ImageDraw.Draw(img)
    d.rectangle([0, H*SUELO*0.62, W, H*SUELO], fill=(120, 76, 44))
    for k in range(6):
        d.rectangle([20 + k*180, H*SUELO*0.65, 170 + k*180, H*SUELO*0.97], outline=(90, 56, 30), width=6)
    # mapa de Europa (siluetas sencillas) con las capitales candidatas
    mx, my, mw, mh = 120, 220, 560, 420
    d.rectangle([mx, my, mx + mw, my + mh], fill=(150, 200, 220), outline=(90, 60, 30), width=14)
    tierra = (236, 220, 170)
    d.polygon([(mx + 60, my + 300), (mx + 200, my + 280), (mx + 210, my + 360), (mx + 90, my + 380)], fill=tierra)   # Iberia
    d.polygon([(mx + 190, my + 180), (mx + 320, my + 150), (mx + 330, my + 270), (mx + 210, my + 280)], fill=tierra) # Francia
    d.polygon([(mx + 320, my + 120), (mx + 470, my + 100), (mx + 520, my + 240), (mx + 340, my + 250)], fill=tierra) # Alemania
    d.polygon([(mx + 330, my + 260), (mx + 360, my + 255), (mx + 420, my + 380), (mx + 395, my + 395)], fill=tierra) # Italia
    d.polygon([(mx + 230, my + 40), (mx + 290, my + 30), (mx + 280, my + 130), (mx + 220, my + 125)], fill=tierra)   # Gran Bretaña
    for px, py in ((150, 320), (260, 220), (420, 180), (380, 320)):
        d.ellipse([mx + px - 10, my + py - 10, mx + px + 10, my + py + 10], fill=(200, 30, 40), outline=TINTA)
    d.text((mx + mw/2, my - 40), "EUROPA", font=ImageFont.truetype(FUENTE, 44), fill=(90, 60, 30), anchor="mm")
    d.rectangle([780, 240, 980, 620], fill=(60, 90, 140), outline=(90, 60, 30), width=14)
    d.line([(880, 240), (880, 620)], fill=(90, 60, 30), width=10)
    d.line([(780, 430), (980, 430)], fill=(90, 60, 30), width=10)
    _suelo_madera(img, H*SUELO)
    return img


def puerto(t=0.0):
    """El puerto de Cartagena en 1870: mar, montes y la fragata blindada
    Numancia (casco negro, tres palos y chimenea), en la que llego Amadeo."""
    img = Image.new("RGBA", (W, H))
    _gradiente(img, (150, 196, 230), (220, 230, 236), 0, H*0.52)
    _gradiente(img, (60, 110, 150), (40, 80, 120), H*0.52, H*SUELO)
    d = ImageDraw.Draw(img)
    d.polygon([(0, H*0.52), (180, H*0.4), (420, H*0.47), (650, H*0.38), (900, H*0.46), (W, H*0.42), (W, H*0.52)],
              fill=(150, 130, 100), outline=TINTA)
    # la Numancia
    by = H*0.57 + math.sin(t*1.5)*6
    d.polygon([(140, by - 60), (900, by - 60), (860, by + 30), (190, by + 30)], fill=(30, 30, 34), outline=TINTA)
    d.rectangle([140, by - 72, 900, by - 60], fill=(140, 30, 30))
    for x in (300, 520, 740):
        d.line([(x, by - 60), (x, by - 520)], fill=(70, 50, 30), width=10)
        for yy in (by - 450, by - 330, by - 210):
            d.line([(x - 90, yy), (x + 90, yy)], fill=(70, 50, 30), width=6)
            d.polygon([(x - 85, yy + 6), (x + 85, yy + 6), (x + 70, yy + 100), (x - 70, yy + 100)], fill=(240, 236, 220), outline=TINTA)
    d.rectangle([600, by - 170, 650, by - 60], fill=(40, 40, 44), outline=TINTA)
    for k in range(4):
        r = 26 + k*12
        cx_, cy_ = 625 + k*30 + math.sin(t*2 + k)*6, by - 200 - k*60
        d.ellipse([cx_ - r, cy_ - r, cx_ + r, cy_ + r], fill=(200, 200, 205))
    bandera(img, "espana", 860, int(by - 60), 90, t, asta=True)
    # el muelle
    d.rectangle([0, H*SUELO - 10, W, H], fill=(150, 130, 110))
    for k in range(9):
        d.line([(k*130, H*SUELO - 10), (k*130 - 60, H)], fill=(120, 100, 80), width=4)
    d.line([(0, H*SUELO - 10), (W, H*SUELO - 10)], fill=TINTA, width=4)
    return img


def calle(t=0.0):
    """Una calle de Madrid hacia 1870: fachadas con balcones de hierro,
    farolas de gas y adoquines."""
    img = Image.new("RGBA", (W, H))
    _gradiente(img, (160, 200, 232), (220, 230, 240), 0, H*0.4)
    d = ImageDraw.Draw(img)
    colores = [(236, 200, 150), (222, 170, 130), (240, 222, 190), (210, 150, 120)]
    x = -40
    k = 0
    while x < W:
        ancho = 300
        top = H*0.18 + (k % 2)*80
        d.rectangle([x, top, x + ancho, H*SUELO], fill=colores[k % 4], outline=TINTA, width=4)
        d.rectangle([x - 10, top - 30, x + ancho + 10, top], fill=(150, 80, 60), outline=TINTA, width=3)
        for fy in range(3):
            for fx in range(2):
                wx, wy = x + 50 + fx*130, top + 70 + fy*230
                if wy > H*SUELO - 200:
                    continue
                d.rectangle([wx, wy, wx + 80, wy + 150], fill=(60, 80, 110), outline=TINTA, width=3)
                d.rectangle([wx - 15, wy + 150, wx + 95, wy + 160], fill=(40, 40, 44))
                for b in range(6):
                    d.line([(wx - 10 + b*20, wy + 120), (wx - 10 + b*20, wy + 155)], fill=(40, 40, 44), width=3)
        d.rectangle([x + 110, H*SUELO - 230, x + 190, H*SUELO], fill=(100, 60, 40), outline=TINTA, width=3)
        x += ancho
        k += 1
    for fx in (160, 920):                        # farolas de gas
        d.line([(fx, H*SUELO), (fx, H*SUELO - 420)], fill=(30, 34, 36), width=12)
        d.polygon([(fx - 40, H*SUELO - 480), (fx + 40, H*SUELO - 480), (fx + 26, H*SUELO - 410), (fx - 26, H*SUELO - 410)],
                  fill=(250, 230, 150), outline=TINTA)
    _gradiente(img, (170, 160, 150), (130, 120, 115), H*SUELO, H)
    d = ImageDraw.Draw(img)
    for yy in range(int(H*SUELO), H, 40):
        off = 0 if (yy//40) % 2 else 40
        for xx in range(-80 + off, W, 80):
            d.rounded_rectangle([xx + 3, yy + 3, xx + 77, yy + 37], radius=8, outline=(110, 100, 95), width=2)
    return img
