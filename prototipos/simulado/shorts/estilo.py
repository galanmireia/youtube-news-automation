"""Estilo de los Shorts de «¿Qué pasaría si…?» (Lo he simulado).

El personaje: «tú». Una bolita amarilla que brilla, con ojos grandes, metida
en un mundo de puntos azules (todos los demás). Cada vídeo empieza igual:
«Este eres tú», y la simulación le pasa a él. Es nuestro, no se parece a
ninguna mascota conocida, y sale del logo del canal (los puntos de la red).
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
FUENTE = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FUENTE_B = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
AMARILLO, AZUL, ROJO, VERDE = (255, 206, 46), (92, 150, 255), (255, 70, 90), (60, 226, 160)
BLANCO, TENUE, OSCURO = (248, 250, 255), (160, 172, 210), (8, 10, 24)
PUNTO = (88, 112, 178)

_F = {}


def F(tam, negra=True):
    k = (max(1, int(tam)), negra)
    if k not in _F:
        _F[k] = ImageFont.truetype(FUENTE if negra else FUENTE_B, k[0])
    return _F[k]


def ease(x):
    x = min(1.0, max(0.0, x))
    return x*x*(3 - 2*x)


def sale(x):
    x = min(1.0, max(0.0, x))
    return 1 + 2.2*(x - 1)**3 + 1.2*(x - 1)**2 if x < 1 else 1.0


_FONDO = None


def fondo():
    global _FONDO
    if _FONDO is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt((xx - W/2)**2 + ((yy - H*0.45)*0.75)**2)/(W*0.95)
        k = np.clip(d, 0, 1)[..., None]**1.1
        img = np.array((34, 44, 96), np.float32)*(1 - k) + np.array((6, 8, 20), np.float32)*k
        img += np.random.default_rng(0).normal(0, 1.3, img.shape)
        _FONDO = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    return _FONDO.copy()


def tx(d, xy, s, tam, col=BLANCO, anchor="mm", negra=True, borde=0, alfa=255):
    d.text(xy, s, font=F(tam, negra), fill=tuple(col[:3]) + (int(alfa),), anchor=anchor,
           stroke_width=borde, stroke_fill=OSCURO + (int(alfa),) if borde else None)


def titular(img, lineas, y, tam=104, alfa=255, k=1.0):
    """Texto grande con borde y sombra. lineas: [[(texto, color), ...], ...]"""
    d = ImageDraw.Draw(img, "RGBA")
    f = F(tam*(0.9 + 0.1*sale(k)))
    alto = tam*1.12
    for n, partes in enumerate(lineas):
        f = F(tam*(0.9 + 0.1*sale(k)))
        ancho = sum(d.textlength(s, font=f) for s, _ in partes)
        if ancho > W - 90:                      # que nunca se salga por los lados
            f = F(tam*(0.9 + 0.1*sale(k))*(W - 90)/ancho)
            ancho = sum(d.textlength(s, font=f) for s, _ in partes)
        x = W/2 - ancho/2
        yy = y + n*alto
        for s, col in partes:
            d.text((x + 6, yy + 8), s, font=f, fill=(0, 0, 0, int(140*alfa/255)), anchor="lm",
                   stroke_width=12, stroke_fill=(0, 0, 0, int(140*alfa/255)))
            d.text((x, yy), s, font=f, fill=tuple(col) + (int(alfa),), anchor="lm",
                   stroke_width=12, stroke_fill=OSCURO + (int(alfa),))
            x += d.textlength(s, font=f)


def brillo(img, puntos, radio, col, fuerza=1.0):
    """Halo suave detras de una lista de (x, y, r)."""
    if not puntos:
        return
    h = Image.new("RGBA", (W//2, H//2), (0, 0, 0, 0))
    dh = ImageDraw.Draw(h)
    for x, y, r in puntos:
        rr = r*radio/2
        dh.ellipse([x/2 - rr, y/2 - rr, x/2 + rr, y/2 + rr], fill=tuple(col) + (int(200*fuerza),))
    h = h.filter(ImageFilter.GaussianBlur(max(3, radio*4))).resize((W, H), Image.BILINEAR)
    img.paste(h, (0, 0), h)


def tu(img, x, y, r, cara="normal", mira=(0.0, 0.0), t=0.0, col=AMARILLO, halo=True, alfa=255):
    """El personaje. cara: normal, contento, susto, triste, pensando, guiño."""
    if halo:
        brillo(img, [(x, y, r)], 2.4, col, 0.8*alfa/255)
    d = ImageDraw.Draw(img, "RGBA")
    a = int(alfa)
    # respira un poco
    s = 1 + 0.025*math.sin(t*3.1)
    rx, ry = r*s, r/s
    d.ellipse([x - rx, y - ry, x + rx, y + ry], fill=tuple(col) + (a,))
    # brillo de bola
    d.ellipse([x - rx*0.55, y - ry*0.75, x - rx*0.05, y - ry*0.35], fill=(255, 255, 230, int(a*0.55)))
    # parpadeo cada ~3 s
    parpado = 1.0 if (t % 3.2) > 0.12 else 0.12
    ox = r*0.36
    for sx in (-1, 1):
        ex, ey = x + sx*ox, y - r*0.08
        er = r*0.27
        if cara == "contento":
            d.arc([ex - er, ey - er*0.6, ex + er, ey + er*0.9], 200, 340, fill=OSCURO + (a,), width=max(3, int(r*0.09)))
            continue
        if cara == "guiño" and sx == 1:
            d.line([ex - er, ey, ex + er, ey], fill=OSCURO + (a,), width=max(3, int(r*0.09)))
            continue
        d.ellipse([ex - er, ey - er*parpado, ex + er, ey + er*parpado], fill=(255, 255, 255, a))
        if parpado > 0.5:
            pr = er*(0.62 if cara != "susto" else 0.42)
            px, py = ex + mira[0]*er*0.4, ey + mira[1]*er*0.4
            d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=OSCURO + (a,))
            d.ellipse([px - pr*0.35 + pr*0.3, py - pr*0.35 - pr*0.3, px + pr*0.35 + pr*0.3, py + pr*0.35 - pr*0.3],
                      fill=(255, 255, 255, a))
        # cejas
        if cara in ("susto", "triste", "pensando"):
            inc = {"susto": -0.25, "triste": 0.35, "pensando": 0.15*sx}[cara]
            cy = ey - er*1.45
            d.line([ex - er*0.9, cy + sx*inc*er, ex + er*0.9, cy - sx*inc*er], fill=OSCURO + (a,), width=max(3, int(r*0.08)))
    # boca
    my = y + r*0.42
    if cara in ("normal", "pensando"):
        d.arc([x - r*0.22, my - r*0.16, x + r*0.22, my + r*0.12], 20, 160, fill=OSCURO + (a,), width=max(3, int(r*0.08)))
    elif cara in ("contento", "guiño"):
        d.chord([x - r*0.32, my - r*0.22, x + r*0.32, my + r*0.26], 0, 180, fill=OSCURO + (a,))
        d.chord([x - r*0.2, my + r*0.02, x + r*0.2, my + r*0.24], 0, 180, fill=(255, 110, 120, a))
    elif cara == "susto":
        d.ellipse([x - r*0.13, my - r*0.12, x + r*0.13, my + r*0.2], fill=OSCURO + (a,))
    elif cara == "triste":
        d.arc([x - r*0.22, my - r*0.02, x + r*0.22, my + r*0.3], 200, 340, fill=OSCURO + (a,), width=max(3, int(r*0.08)))
    # mofletes
    for sx in (-1, 1):
        cx = x + sx*r*0.62
        d.ellipse([cx - r*0.13, my - r*0.2, cx + r*0.13, my - r*0.04], fill=(255, 140, 90, int(a*0.45)))


def punto(d, x, y, r, col=PUNTO, alfa=255):
    d.ellipse([x - r, y - r, x + r, y + r], fill=tuple(col) + (int(alfa),))


def etiqueta(img, x, y, s, col=AMARILLO, tam=44, k=1.0, flecha_a=None):
    """Bocadillo pequeño; flecha_a=(x, y) apunta a algo."""
    if k <= 0:
        return
    d = ImageDraw.Draw(img, "RGBA")
    f = F(tam*sale(k))
    w = d.textlength(s, font=f)
    hh = tam*sale(k)*1.5
    a = int(255*min(1, k*2))
    if flecha_a:
        d.polygon([(x - 18, y + hh/2 - 2), (x + 18, y + hh/2 - 2), flecha_a], fill=OSCURO + (int(a*0.9),))
    d.rounded_rectangle([x - w/2 - 28, y - hh/2, x + w/2 + 28, y + hh/2], radius=hh/2, fill=OSCURO + (int(a*0.92),),
                        outline=tuple(col) + (a,), width=4)
    d.text((x, y), s, font=f, fill=tuple(col) + (a,), anchor="mm")


def marca(img, alfa=255):
    d = ImageDraw.Draw(img, "RGBA")
    f = F(34)
    w1 = d.textlength("LO HE ", font=f)
    w2 = d.textlength("SIMULADO", font=f)
    x0 = W/2 - (w1 + w2)/2
    d.text((x0, 1800), "LO HE ", font=f, fill=BLANCO + (int(alfa*0.8),), anchor="lm")
    d.text((x0 + w1, 1800), "SIMULADO", font=f, fill=AMARILLO + (int(alfa*0.8),), anchor="lm")


def agente(img, x, y, r, cara="normal", t=0.0, brazos="abajo", alfa=255, sombra=True):
    """El personaje elegido (C, «Agente»): robotito blanco con antena y una
    pantalla por cara. Se dibuja al doble en un trozo aparte y se reduce, para
    que los bordes salgan limpios a cualquier tamaño.
    cara: normal, contento, susto, pensando, guiño, triste
    brazos: abajo, arriba, señala (a la derecha), cadera"""
    S = 2
    R = r*S
    tam = int(R*4.4)
    capa = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    cx, cy = tam/2, tam/2 - R*0.15
    bote = math.sin(t*3.0)*R*0.03
    cy += bote
    lw = max(2, int(R*0.075))
    ink = OSCURO + (255,)
    # sombra en el suelo
    if sombra:
        d.ellipse([cx - R*0.9, cy + R*1.5, cx + R*0.9, cy + R*1.72], fill=(0, 0, 0, 90))
    # piernas
    for sx in (-1, 1):
        d.line([(cx + sx*R*0.4, cy + R*0.8), (cx + sx*R*0.42, cy + R*1.4)], fill=ink, width=lw)
        d.ellipse([cx + sx*R*0.42 - R*0.24, cy + R*1.32, cx + sx*R*0.42 + R*0.24, cy + R*1.54], fill=ink)
    # brazos
    pos = {"abajo": ((-1.38, 0.62), (1.38, 0.62)), "arriba": ((-1.35, -0.75), (1.35, -0.75)),
           "señala": ((-1.35, 0.6), (1.6, -0.2)), "cadera": ((-1.15, 0.55), (1.15, 0.55))}[brazos]
    for sx, (hx, hy) in zip((-1, 1), pos):
        ox, oy = cx + sx*R*0.95, cy + R*0.15
        mx, my = cx + hx*R, cy + hy*R + (math.sin(t*6)*R*0.06 if brazos == "arriba" else 0)
        if brazos == "cadera":
            d.line([(ox, oy), (cx + sx*R*1.35, cy + R*0.15), (mx, my)], fill=ink, width=lw, joint="curve")
        else:
            d.line([(ox, oy), (mx, my)], fill=ink, width=lw)
        d.ellipse([mx - R*0.15, my - R*0.15, mx + R*0.15, my + R*0.15], fill=ink)
    # antena (se balancea)
    ax = cx + R*0.15 + math.sin(t*4)*R*0.08
    d.line([(cx, cy - R*0.97), (ax, cy - R*1.5)], fill=ink, width=lw)
    luz = (255, 80, 96) if cara != "contento" else (60, 226, 160)
    d.ellipse([ax - R*0.18, cy - R*1.5 - R*0.18, ax + R*0.18, cy - R*1.5 + R*0.18], fill=luz + (255,), outline=ink, width=lw)
    # cuerpo
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(238, 242, 252, 255), outline=ink, width=lw)
    d.ellipse([cx - R*0.75, cy - R*0.85, cx - R*0.25, cy - R*0.6], fill=(255, 255, 255, 255))
    # pantalla
    d.rounded_rectangle([cx - R*0.72, cy - R*0.55, cx + R*0.72, cy + R*0.47], radius=R*0.3, fill=(18, 26, 58, 255))
    ojo = (110, 205, 255, 255)
    parp = (t % 3.4) < 0.12
    for sx in (-1, 1):
        ex, ey = cx + sx*R*0.3, cy - R*0.16
        if cara == "contento" or (cara == "guiño" and sx == 1):
            d.arc([ex - R*0.15, ey - R*0.1, ex + R*0.15, ey + R*0.2], 200, 340, fill=ojo, width=max(2, int(R*0.07)))
        elif parp:
            d.line([(ex - R*0.13, ey), (ex + R*0.13, ey)], fill=ojo, width=max(2, int(R*0.07)))
        elif cara == "susto":
            d.ellipse([ex - R*0.15, ey - R*0.19, ex + R*0.15, ey + R*0.19], outline=ojo, width=max(2, int(R*0.06)))
            d.ellipse([ex - R*0.06, ey - R*0.06, ex + R*0.06, ey + R*0.06], fill=ojo)
        elif cara == "pensando":
            h = 0.16 if sx == -1 else 0.07
            d.rounded_rectangle([ex - R*0.12, ey - R*h, ex + R*0.12, ey + R*h], radius=R*0.06, fill=ojo)
        elif cara == "triste":
            d.rounded_rectangle([ex - R*0.12, ey - R*0.1, ex + R*0.12, ey + R*0.16], radius=R*0.06, fill=ojo)
            d.line([(ex - R*0.16, ey - R*0.2 - sx*R*0.05), (ex + R*0.16, ey - R*0.2 + sx*R*0.05)], fill=ojo, width=max(2, int(R*0.05)))
        else:
            d.rounded_rectangle([ex - R*0.12, ey - R*0.17, ex + R*0.12, ey + R*0.15], radius=R*0.07, fill=ojo)
    my = cy + R*0.2
    if cara in ("normal", "guiño"):
        d.arc([cx - R*0.22, my - R*0.14, cx + R*0.22, my + R*0.14], 20, 160, fill=ojo, width=max(2, int(R*0.07)))
    elif cara == "contento":
        d.chord([cx - R*0.26, my - R*0.16, cx + R*0.26, my + R*0.2], 0, 180, fill=ojo)
    elif cara == "susto":
        d.ellipse([cx - R*0.1, my - R*0.06, cx + R*0.1, my + R*0.18], outline=ojo, width=max(2, int(R*0.06)))
    elif cara == "pensando":
        d.line([(cx - R*0.15, my + R*0.05), (cx + R*0.18, my - R*0.02)], fill=ojo, width=max(2, int(R*0.07)))
    elif cara == "triste":
        d.arc([cx - R*0.2, my + R*0.02, cx + R*0.2, my + R*0.3], 200, 340, fill=ojo, width=max(2, int(R*0.07)))
    capa = capa.resize((tam//S, tam//S), Image.LANCZOS)
    if alfa < 255:
        capa.putalpha(capa.getchannel("A").point(lambda v: v*alfa//255))
    img.paste(capa, (int(x - tam/S/2), int(y - tam/S/2 + r*0.15)), capa)
