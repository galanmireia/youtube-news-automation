"""ACROSS THE STREET — teaser (~38 s, 16:9, mudo con musica y golpes graves).

La calle de noche y el edificio de enfrente: se encienden las ventanas. En la 2A
una mano se levanta y la luz se apaga (¡BRAAM!). Titulo. Luego, ventana a ventana:
el marido que se va con la maleta, el amante con flores, el test de embarazo del
3A, los abuelos y el plato volando... y la 2B, a oscuras, alguien con prismaticos.
Tres cortes con golpes cada vez mas graves. Al final se enciende la 2B: vacia. Y
los prismaticos se giran hacia ti.
  python teaser.py fotos | en 5.0 12.3 | (sin nada: render)
"""
import math, random, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prueba_estilo as P
import prueba_horizontal as PH
from prueba_estilo import tramo, NEGRO, LUZ, LUZ2

W, H, FPS = 1920, 1080, 25
OUT = P.OUT
SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf"
SERIF_R = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
CALIDA = (255, 196, 120)

def serif(px, recta=False):
    return ImageFont.truetype(SERIF_R if recta else SERIF, int(px))

def suave(x):
    x = min(1, max(0, x)); return x*x*(3 - 2*x)

# ---------------------------------------------------------------- la silueta animable
def persona(d, x, suelo, h, mira=1, pelo="corto", falda=False, brazos=((12, 25), (-10, -4)), paso=None, salto=0.0,
            inclina=0.0, objeto=None, obj_k=0.0):
    """Silueta con brazos por angulos (delante, detras), piernas que caminan (paso) y un objeto en la mano."""
    u = h/100
    suelo -= salto*u
    x += inclina*u*4
    hx, hy = x + inclina*u*7, suelo - 92*u
    mujer = falda or pelo in ("largo", "coleta", "moño")
    sw = (9 if mujer else 11.5)*u; ww = (6.5 if mujer else 8.5)*u; hw = (10 if mujer else 9)*u
    ys, yw, yh = suelo - 81*u, suelo - 60*u, suelo - 50*u
    if pelo == "largo":
        d.polygon([(hx - 6.5*u, hy - 3*u), (hx + 6.5*u, hy - 3*u), (hx + 7.5*u - mira*3*u, hy + 15*u), (hx - 7.5*u - mira*3*u, hy + 15*u)], fill=NEGRO)
    elif pelo == "coleta":
        tramo(d, (hx - mira*4*u, hy - 3*u), (hx - mira*9*u, hy + 6*u + (paso is not None)*math.sin((paso or 0)*2)*2*u), 4.5*u, 2.5*u)
    for lado in (-1, 1):
        sw_ = math.sin(paso + (0 if lado < 0 else math.pi))*16 if paso is not None else 0
        r = math.radians(sw_)
        cad = (x + lado*4*u, yh)
        rod = (cad[0] + mira*math.sin(r)*23*u, cad[1] + math.cos(r)*23*u)
        r2 = math.radians(sw_ - abs(sw_)*0.6)
        tob = (rod[0] + mira*math.sin(r2)*24*u, min(suelo - 3*u, rod[1] + math.cos(r2)*24*u))
        tramo(d, cad, rod, 8.5*u, 6*u); tramo(d, rod, tob, 6*u, 3.6*u)
        d.ellipse([tob[0] - 2.5*u + mira*1.5*u, tob[1] - 0.5*u, tob[0] + 5*u + mira*1.5*u, tob[1] + 3.5*u], fill=NEGRO)
    d.polygon([(x - sw, ys + 2*u), (x + sw, ys + 2*u), (x + ww, yw), (x + hw, yh + 2*u), (x - hw, yh + 2*u), (x - ww, yw)], fill=NEGRO)
    d.rounded_rectangle([x - sw, ys - 0.5*u, x + sw, ys + 8*u], radius=int(4*u), fill=NEGRO)
    if falda:
        d.polygon([(x - hw, yh), (x + hw, yh), (x + hw + 5*u, suelo - 26*u), (x - hw - 5*u, suelo - 26*u)], fill=NEGRO)
    d.polygon([(hx - 2.2*u, hy + 5*u), (hx + 2.2*u, hy + 5*u), (x + 3*u, ys + 1*u), (x - 3*u, ys + 1*u)], fill=NEGRO)
    manos = {}
    for lado, (a1, a2), cual in ((-mira, brazos[1], "det"), (mira, brazos[0], "del")):
        hb = (x + lado*(sw - 1.5*u), ys + 2*u)
        r1, r2 = math.radians(a1), math.radians(a2)
        codo = (hb[0] + mira*math.sin(r1)*16*u, hb[1] + math.cos(r1)*16*u)
        mano = (codo[0] + mira*math.sin(r2)*15*u, codo[1] + math.cos(r2)*15*u)
        tramo(d, hb, codo, 5.2*u, 4*u); tramo(d, codo, mano, 4*u, 3*u)
        d.ellipse([mano[0] - 2.4*u, mano[1] - 2.6*u, mano[0] + 2.4*u, mano[1] + 2.6*u], fill=NEGRO)
        manos[cual] = mano
    m = manos["del"]
    if objeto == "test":
        d.rounded_rectangle([m[0] - 0.9*u, m[1] - 9*u, m[0] + 0.9*u, m[1] - 1*u], radius=int(u*0.8), fill=NEGRO)
    elif objeto == "maleta":
        mb = manos["det"]
        d.rounded_rectangle([mb[0] - 9*u, mb[1] - 1*u, mb[0] + 9*u, mb[1] + 14*u], radius=int(1.5*u), fill=NEGRO)
    elif objeto == "flores":
        for k in range(5):
            a = -1.2 + k*0.6
            fx, fy = m[0] + math.sin(a)*6*u + mira*2*u, m[1] - 9*u - math.cos(a)*3*u
            d.line([m, (fx, fy)], fill=NEGRO, width=int(u*0.9))
            d.ellipse([fx - 2.6*u, fy - 2.6*u, fx + 2.6*u, fy + 2.6*u], fill=NEGRO)
    elif objeto == "tarta":
        d.rectangle([m[0] - 8*u, m[1] - 7*u, m[0] + 8*u, m[1]], fill=NEGRO)
        d.line([(m[0], m[1] - 7*u), (m[0], m[1] - 11*u)], fill=NEGRO, width=int(u))
    elif objeto == "prismaticos":
        for k in (-1, 1):
            d.rounded_rectangle([hx + mira*6*u - 2*u, hy - 3*u + k*2.2*u - 1.6*u, hx + mira*13*u, hy - 3*u + k*2.2*u + 1.6*u], radius=int(u), fill=NEGRO)
    d.ellipse([hx - 5.6*u, hy - 6.8*u, hx + 5.6*u, hy + 6.2*u], fill=NEGRO)
    d.polygon([(hx + mira*4.8*u, hy - 1.5*u), (hx + mira*7.2*u, hy + 1.2*u), (hx + mira*5*u, hy + 2.2*u)], fill=NEGRO)
    d.ellipse([hx + mira*1.5*u - 3.5*u, hy + 1*u, hx + mira*1.5*u + 3.5*u, hy + 6.8*u], fill=NEGRO)
    if pelo == "moño":
        d.ellipse([hx - mira*2*u - 3.6*u, hy - 11*u, hx - mira*2*u + 3.6*u, hy - 4.5*u], fill=NEGRO)
    elif pelo == "corto":
        d.ellipse([hx - 6.2*u - mira*0.8*u, hy - 7.4*u, hx + 5.4*u - mira*0.8*u, hy + 1*u], fill=NEGRO)
    elif pelo == "largo":
        d.ellipse([hx - 6.6*u, hy - 7.6*u, hx + 6.2*u, hy + 2*u], fill=NEGRO)
    return manos

def lerp_brazos(a, b, k):
    return tuple(tuple(x + (y - x)*k for x, y in zip(pa, pb)) for pa, pb in zip(a, b))

BR = {"caidos": ((12, 25), (-10, -4)), "saluda": ((150, 175), (-10, -4)), "alto": ((165, 178), (-10, -4)),
      "señala": ((80, 88), (-8, 2)), "abrazo": ((75, 125), (65, 115)), "cara": ((28, 150), (20, 150)),
      "lleva": ((55, 95), (-10, -4)), "test": ((120, 178), (-10, -4)), "jarras": ((-45, 50), (-45, 50))}

# ---------------------------------------------------------------- la ventana de cerca (16:9)
_FONDO = {}
def fondo_luz(w, h, apagada=False):
    clave = (w, h, apagada)
    if clave not in _FONDO:
        im = Image.new("RGB", (w, h)); d = ImageDraw.Draw(im)
        for j in range(h):
            f = abs(j - h*0.35)/h
            col = tuple(int(a - (a - b)*min(1, f*1.4)) for a, b in zip(LUZ2, LUZ))
            if apagada:
                col = (24 + int(10*(1 - f)), 30 + int(10*(1 - f)), 58 + int(14*(1 - f)))
            d.line([(0, j), (w, j)], fill=col)
        _FONDO[clave] = im
    return _FONDO[clave].copy()

def pared(img):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, H], fill=(52, 44, 66))
    for fila in range(0, 20):
        for col in range(12):
            x = col*180 + (90 if fila % 2 else 0); y = fila*56
            d.rectangle([x, y, x + 176, y + 52], outline=(62, 54, 78), width=4)

def ventana_cerca(escena, encendida=True, cortina=0.28, x0=460, y0=90, w=1000, h=820, empuja=0.0):
    """Una ventana grande: escena(c, w, h) dibuja las siluetas (a triple tamaño, para que salgan suaves)."""
    img = Image.new("RGB", (W, H)); pared(img); d = ImageDraw.Draw(img)
    d.rectangle([x0 - 22, y0 - 22, x0 + w + 22, y0 + h + 22], fill=(70, 62, 80))
    SS = 2
    capa = fondo_luz(w*SS, h*SS, apagada=not encendida)
    if escena:
        escena(ImageDraw.Draw(capa), w*SS, h*SS)
    capa = capa.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.4 if encendida else 0.8))
    img.paste(capa, (x0, y0)); d = ImageDraw.Draw(img)
    if encendida:
        for lado in (-1, 1):
            xa = x0 if lado < 0 else x0 + w - w*cortina*0.5
            d.rectangle([xa, y0, xa + w*cortina*0.5, y0 + h], fill=(236, 140, 70))
            for k in range(1, 4):
                xx = xa + w*cortina*0.5*k/4
                d.line([(xx, y0), (xx, y0 + h)], fill=(214, 116, 56), width=4)
    d.line([(x0 + w/2, y0), (x0 + w/2, y0 + h)], fill=(70, 62, 80), width=12)
    d.line([(x0, y0 + h*0.42), (x0 + w, y0 + h*0.42)], fill=(70, 62, 80), width=12)
    d.rectangle([x0 - 34, y0 + h, x0 + w + 34, y0 + h + 30], fill=(90, 82, 100))
    return img

def bordes(img, fuerza=200):
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0)); c = ImageDraw.Draw(capa)
    for k in range(40):
        f = k/40
        c.rectangle([k*12, k*7, W - k*12, H - k*7], outline=(6, 6, 12, int(fuerza*(1 - f)**2)), width=14)
    img = img.convert("RGBA"); img.alpha_composite(capa)
    return img.convert("RGB")

def rotulo(img, hora, piso, lt):
    a = suave((lt - 0.2)/0.4)
    if a <= 0: return img
    d = ImageDraw.Draw(img)
    col = tuple(int(10 + (v - 10)*a) for v in (255, 214, 140)); col2 = tuple(int(10 + (v - 10)*a) for v in (240, 230, 230))
    d.text((90, 920), hora, font=serif(84), fill=col, stroke_width=3, stroke_fill=(10, 8, 16))
    d.text((96, 1010), piso, font=serif(46), fill=col2, stroke_width=2, stroke_fill=(10, 8, 16))
    return img

def camara(img, cx, cy, z):
    if z <= 1.001: return img
    w, h = W/z, H/z
    x0 = min(max(0, cx - w/2), W - w); y0 = min(max(0, cy - h/2), H - h)
    return img.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + w, y0 + h))

def golpe_cam(lt, fuerza=1.0):
    """El 'empujon' de camara de cada golpe grave: un zoom rapido y un temblor."""
    z = 1.0 + 0.06*fuerza*math.exp(-lt*6)
    sh = math.sin(lt*70)*10*fuerza*math.exp(-lt*8)
    return z, sh

# ---------------------------------------------------------------- las escenas
SUELO_V = lambda h: h*0.99

def esc_golpe(lt):                            # 2A: el marido levanta la mano...
    def e(c, w, h):
        k = suave((lt - 0.2)/0.7)
        persona(c, w*0.36, SUELO_V(h), h*0.82, 1, "moño", True, lerp_brazos(BR["caidos"], BR["cara"], suave((lt - 0.6)/0.3)))
        persona(c, w*0.62, SUELO_V(h), h*0.9, -1, "corto", False, lerp_brazos(BR["caidos"], BR["alto"], k), inclina=-0.4*k)
    return e

def esc_adios(lt):                            # 2A: el marido se va con la maleta; ella dice adios
    def e(c, w, h):
        ola = math.sin(lt*8)*12
        persona(c, w*0.38, SUELO_V(h), h*0.82, 1, "moño", True, ((150 + ola, 175 + ola), (-10, -4)) if lt > 0.6 else BR["caidos"])
        x = w*(0.58 + 0.55*suave((lt - 0.4)/2.6))
        persona(c, x, SUELO_V(h), h*0.9, 1 if lt > 0.4 else -1, "corto", False, BR["caidos"], paso=lt*7 if lt > 0.4 else None, objeto="maleta")
    return e

def esc_amante(lt):                           # 2A: llega el otro, con flores. Beso.
    def e(c, w, h):
        x = w*(1.15 - 0.55*suave(lt/1.6))
        beso = suave((lt - 1.9)/0.6)
        persona(c, w*0.4 + w*0.04*beso, SUELO_V(h), h*0.82, 1, "moño", True, lerp_brazos(BR["caidos"], BR["abrazo"], beso), inclina=0.5*beso)
        persona(c, x - w*0.02*beso, SUELO_V(h), h*0.9, -1, "corto", False, lerp_brazos(BR["lleva"], BR["abrazo"], beso),
                paso=lt*7 if lt < 1.6 else None, inclina=-0.4*beso, objeto="flores" if beso < 0.5 else None)
    return e

def esc_test(lt):                             # 3A: Lucy, el test, ¡positivo!
    def e(c, w, h):
        salto = abs(math.sin((lt - 1.2)*6))*10 if lt > 1.2 else 0
        persona(c, w*0.5, SUELO_V(h), h*0.82, 1, "coleta", True, lerp_brazos(BR["lleva"], BR["test"], suave((lt - 0.5)/0.4)),
                salto=salto, objeto="test")
    return e

def esc_abuelos(lt):                          # 2C: pelea por el mando, plato volando... y al cristal
    def e(c, w, h):
        if lt < 1.8:
            persona(c, w*0.28, SUELO_V(h), h*0.8, 1, "moño", True, BR["señala"] if (lt % 0.6) < 0.3 else BR["jarras"])
            persona(c, w*0.74, SUELO_V(h), h*0.85, -1, "corto", False, BR["alto"] if lt > 0.5 else BR["señala"])
            if 0.6 < lt < 1.4:                # el plato
                u = (lt - 0.6)/0.8
                px, py = w*(0.68 - 0.5*u), h*(0.35 - 0.25*math.sin(math.pi*u))
                c.ellipse([px - w*0.05, py - w*0.012, px + w*0.05, py + w*0.012], fill=NEGRO)
        else:                                 # han visto algo: los dos pegados al cristal, de frente
            k = suave((lt - 1.8)/0.4)
            for x, pelo, falda, hh in ((0.42, "moño", True, 0.95), (0.6, "corto", False, 1.0)):
                persona(c, w*x, h*(0.99 + 0.25*k), h*hh*(1 + 0.25*k), 1 if x < 0.5 else -1, pelo, falda, BR["cara"] if k > 0.5 else BR["caidos"])
    return e

def esc_2b(lt):                               # 2B: a oscuras. El brillo de una pantalla. Alguien con prismaticos.
    def e(c, w, h):
        persona(c, w*0.5, SUELO_V(h), h*0.9, 1, "corto", False, BR["cara"], objeto="prismaticos")
    return e

def esc_tarta(lt):                            # 3A: se le cae la tarta
    def e(c, w, h):
        persona(c, w*0.45, SUELO_V(h), h*0.82, 1, "coleta", True, BR["cara"] if lt > 0.25 else BR["lleva"], objeto=None if lt > 0.15 else "tarta")
        if lt > 0.15:
            u = min(1.0, (lt - 0.15)/0.35)
            tx, ty = w*0.56, h*(0.55 + 0.4*u*u)
            if u < 1:
                c.rectangle([tx - w*0.045, ty - h*0.05, tx + w*0.045, ty], fill=NEGRO)
            else:
                c.ellipse([tx - w*0.09, h*0.96, tx + w*0.09, h*1.0], fill=NEGRO)
    return e

def esc_puerta(lt):                           # 2A: se abre la puerta del fondo: el marido. Nunca se fue.
    def e(c, w, h):
        ab = suave(lt/0.3)
        c.rectangle([w*0.4, h*0.3, w*0.62, h*0.99], fill=(150, 80, 40))
        c.rectangle([w*0.4, h*0.3, w*0.4 + w*0.22*ab, h*0.99], fill=(255, 244, 220))
        if ab > 0.6:
            persona(c, w*0.51, h*0.99, h*0.66, -1, "corto", False, BR["caidos"], objeto="maleta")
        persona(c, w*0.24, SUELO_V(h), h*0.88, 1, "moño", True, BR["cara"])
        persona(c, w*0.82, SUELO_V(h), h*0.92, -1, "corto", False, BR["caidos"])
    return e

# ---------------------------------------------------------------- el edificio de enfrente (con luces que se encienden)
def edificio(t, encendidas, luz_2b=False, prism_k=0.0):
    img = PH.edificio_h()
    if luz_2b or len(encendidas) < 13:            # tapa las que aun estan apagadas
        d = ImageDraw.Draw(img)
        for fila in range(3):
            for col in range(5):
                vx, vy = 230 + col*310, 200 + fila*240
                clave = f"{3 - fila}{'ABCDE'[col]}"
                if clave not in encendidas and clave != "2B":
                    d.rectangle([vx, vy, vx + 230, vy + 170], fill=(28, 34, 60))
                    d.line([(vx + 230*0.2, vy + 170*0.1), (vx + 230*0.45, vy + 170*0.4)], fill=(50, 60, 96), width=6)
                    d.line([(vx + 115, vy), (vx + 115, vy + 170)], fill=(70, 62, 80), width=8)
    if luz_2b:
        P.ventana(img, 230 + 310, 200 + 240, 230, 170, lambda c, w, h: c.rectangle([w*0.3, h*0.7, w*0.5, h*0.95], fill=NEGRO))
    return img

TODAS = ["3A", "3C", "3D", "2A", "2C", "2D", "1A", "1B", "1D", "1E"]

# ---------------------------------------------------------------- los planos
def p_calle(lt, t):
    n = sum(1 for k in (0.6, 1.1, 1.5, 1.9, 2.3, 2.6, 3.0, 3.3, 3.6, 3.9) if lt > k)
    img = edificio(t, set(TODAS[:n]))
    return camara(img, W/2, 520, 1.0 + 0.08*lt/4.5)

def p_golpe(lt, t):
    apagada = lt > 0.9
    img = ventana_cerca(None if apagada else esc_golpe(lt), encendida=not apagada)
    z, sh = golpe_cam(lt - 0.9, 1.6) if apagada else (1.0 + 0.02*lt, 0)
    return bordes(camara(img, W/2 + sh, H/2, z))

def p_titulo(lt, t):
    img = Image.new("RGB", (W, H), (6, 6, 12)); d = ImageDraw.Draw(img)
    a = suave((lt - 0.3)/0.8)
    col = tuple(int(6 + (v - 6)*a) for v in CALIDA)
    d.text((W/2, 470), "ACROSS THE STREET", font=serif(150, recta=True), fill=col, anchor="mm")
    b = suave((lt - 1.4)/0.6)
    d.text((W/2, 620), "Everyone has a window.", font=serif(58), fill=tuple(int(6 + (v - 6)*b) for v in (230, 222, 230)), anchor="mm")
    z, sh = golpe_cam(lt, 0.8)
    return camara(img, W/2 + sh, H/2, z)

def capitulo_plano(escena_fn, hora, piso, encendida=True, golpe=False):
    def plano(lt, t):
        img = ventana_cerca(escena_fn(lt), encendida=encendida)
        if golpe:
            z, sh = golpe_cam(lt, 1.0)
            img = camara(img, W/2 + sh, H/2, z)
        else:
            img = camara(img, W/2, H/2, 1.0 + 0.03*lt)
        img = bordes(img)
        return rotulo(img, hora, piso, lt) if hora else img
    return plano

def p_2b(lt, t):
    img = ventana_cerca(esc_2b(lt), encendida=False)
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).ellipse([W/2 + 40 - 160, 420 - 160, W/2 + 40 + 160, 420 + 160], fill=int(150 + 40*math.sin(t*3)))
    m = m.filter(ImageFilter.GaussianBlur(80))
    img = Image.composite(Image.new("RGB", (W, H), (120, 170, 255)), img, m)        # el brillo azul de la pantalla
    img = camara(img, W/2, 470, 1.0 + 0.08*lt/4.0)
    img = bordes(img, 230)
    return rotulo(img, "??:??", "Apartment 2B", lt)

def p_corte_apagon(lt, t):
    apagada = lt > 0.45
    img = ventana_cerca(None if apagada else esc_golpe(0.9 + lt), encendida=not apagada)
    z, sh = golpe_cam(lt - 0.45, 2.2) if apagada else golpe_cam(lt, 1.0)
    return bordes(camara(img, W/2 + sh, H/2, z))

def p_final_ancho(lt, t):
    img = edificio(t, set(TODAS), luz_2b=lt > 1.5)
    return camara(img, 230 + 310 + 115, 200 + 240 + 85, 1.0 + 0.6*suave((lt - 1.6)/0.6))

def p_prismaticos(lt, t):
    """La 2B, encendida y vacia. En el alfeizar, unos prismaticos... que se giran hacia ti."""
    def e(c, w, h):
        c.rectangle([w*0.55, h*0.62, w*0.75, h*0.99], fill=NEGRO)                      # la silla vacia
        c.rectangle([w*0.55, h*0.35, w*0.58, h*0.62], fill=NEGRO)
    img = ventana_cerca(e, encendida=True, cortina=0.2)
    d = ImageDraw.Draw(img)
    gira = suave((lt - 1.0)/0.8)
    cx, cy = W/2, 860
    if gira < 0.5:                                       # de perfil
        for k in (-1, 1):
            d.rounded_rectangle([cx - 150, cy + k*40 - 34, cx + 150, cy + k*40 + 34], radius=30, fill=(14, 12, 18))
    else:                                                # de frente: dos lentes que te miran
        for k in (-1, 1):
            d.ellipse([cx + k*95 - 85, cy - 85, cx + k*95 + 85, cy + 85], fill=(14, 12, 18))
            d.ellipse([cx + k*95 - 55, cy - 55, cx + k*95 + 55, cy + 55], fill=(40, 50, 80))
            if lt > 2.2:                                 # el destello
                d.ellipse([cx + k*95 - 30, cy - 40, cx + k*95 - 5, cy - 15], fill=(240, 250, 255))
    z, sh = golpe_cam(lt - 2.2, 2.6) if lt > 2.2 else (1.0 + 0.05*lt, 0)
    return bordes(camara(img, cx + sh, 700, max(z, 1.0)))

def p_fin(lt, t):
    img = Image.new("RGB", (W, H), (6, 6, 12)); d = ImageDraw.Draw(img)
    a = suave((lt - 0.2)/0.6)
    d.text((W/2, 420), "ACROSS THE STREET", font=serif(120, recta=True), fill=tuple(int(6 + (v - 6)*a) for v in CALIDA), anchor="mm")
    b = suave((lt - 0.7)/0.5)
    d.text((W/2, 560), "Night 1 · The Man in 2B", font=serif(64), fill=tuple(int(6 + (v - 6)*b) for v in (240, 230, 230)), anchor="mm")
    c_ = suave((lt - 1.3)/0.5)
    d.text((W/2, 700), "COMING SOON", font=serif(44, recta=True), fill=tuple(int(6 + (v - 6)*c_) for v in (200, 120, 120)), anchor="mm")
    return img

GUION = [
    (p_calle, 4.5),
    (p_golpe, 1.9),
    (p_titulo, 3.2),
    (capitulo_plano(esc_adios, "21:00", "Apartment 2A"), 3.4),
    (capitulo_plano(esc_amante, "21:20", "Apartment 2A"), 3.4),
    (capitulo_plano(esc_test, "21:40", "Apartment 3A"), 3.0),
    (capitulo_plano(esc_abuelos, "22:30", "Apartment 2C"), 3.0),
    (p_2b, 4.0),
    (capitulo_plano(esc_tarta, None, None, golpe=True), 1.0),
    (capitulo_plano(esc_puerta, None, None, golpe=True), 1.0),
    (p_corte_apagon, 1.6),
    (p_final_ancho, 2.4),
    (p_prismaticos, 3.4),
    (p_fin, 3.0),
]

def tabla():
    t = 0.0; out = []
    for fn, dur in GUION:
        out.append((t, t + dur, fn)); t += dur
    return out, t

TABLA, DUR = tabla()
T0 = {fn: a for a, b, fn in TABLA}

def fotograma(t):
    for a, b, fn in TABLA:
        if a <= t < b:
            return fn(t - a, t)
    return Image.new("RGB", (W, H))

# ---------------------------------------------------------------- el sonido: ciudad de noche, piano, y golpes graves
SR = 44100
def nf(m): return 440*2**((m - 69)/12)

def audio(ruta):
    n = int(DUR*SR); out = np.zeros(n + 6*SR); rnd = np.random.default_rng(7)
    tt = np.arange(len(out))/SR
    def pon(t0, x, v=1.0):
        s0 = int(t0*SR); out[s0:s0 + len(x)] += v*x[:max(0, len(out) - s0)]
    def lp(x, k):                                  # filtro paso bajo barato (media movil)
        return np.convolve(x, np.ones(k)/k, mode="same")
    def env(L, at, ca):
        x = np.arange(L)/SR; return np.minimum(1, x/at)*np.exp(-x*ca)
    # el fondo: rumor de ciudad y viento
    amb = lp(rnd.standard_normal(len(out)), 400)*3.0
    amb *= 0.5 + 0.5*np.sin(2*np.pi*0.07*tt)
    out += amb*0.08
    for tc in (2.0, 11.0, 19.0, 33.0):            # un coche que pasa a lo lejos
        L = int(3*SR); x = lp(rnd.standard_normal(L), 60)*np.sin(np.linspace(0, np.pi, L))**2
        pon(tc, x, 0.08)
    # el dron grave, que va creciendo
    dron = (np.sin(2*np.pi*55*tt) + 0.5*np.sin(2*np.pi*82.4*tt + 0.3) + 0.3*np.sin(2*np.pi*110*tt))*(0.5 + 0.5*np.sin(2*np.pi*0.15*tt))
    curva = np.interp(tt, [0, 4, 6, 9, 22, 26, 29, 31, 34, DUR + 6], [0.2, 0.6, 0.2, 0.25, 0.35, 0.9, 1.0, 0.0, 0.0, 0.0])
    out += dron*curva*0.05
    # los golpes graves (BRAAM): metal grave + sub que cae + ruido
    def braam(fuerza=1.0, base=41.2):
        L = int(3.5*SR); x = np.arange(L)/SR
        f = base*(1 + 0.4*np.exp(-x*6))
        ph = 2*np.pi*np.cumsum(f)/SR
        s = sum(np.sin(k*ph)/k for k in range(1, 12))*np.minimum(1, x/0.03)*np.exp(-x*1.1)
        sub = np.sin(2*np.pi*np.cumsum(70*np.exp(-x*1.5) + 28)/SR)*np.exp(-x*1.0)
        imp = rnd.standard_normal(L)*np.exp(-x*25)*0.6
        return np.tanh((0.55*s + 0.9*sub + imp)*1.6*fuerza)*0.6
    def subcaida(fuerza=1.0):
        L = int(1.6*SR); x = np.arange(L)/SR
        return np.sin(2*np.pi*np.cumsum(90*np.exp(-x*2.5) + 25)/SR)*np.exp(-x*1.4)*0.7*fuerza
    def whoosh(d=0.5):
        L = int(d*SR); x = rnd.standard_normal(L); x = x - lp(x, 8); x = lp(x, 3)
        return x*np.sin(np.linspace(0, np.pi, L))**2*0.25
    def riser(d=1.5):
        L = int(d*SR); x = np.arange(L)/SR
        r = rnd.standard_normal(L); r = r - lp(r, 6)
        return (r*0.15 + 0.12*np.sin(2*np.pi*np.cumsum(200 + 900*(x/d)**2)/SR))*(x/d)**2
    def latido(t0, n, cada):
        for i in range(n):
            for j in (0.0, 0.2):
                L = int(0.3*SR); x = np.arange(L)/SR
                pon(t0 + i*cada + j, np.sin(2*np.pi*48*x)*np.exp(-x*14), 0.6)
    def click(t0):
        L = int(0.05*SR); pon(t0, rnd.standard_normal(L)*np.exp(-np.arange(L)/SR*90), 0.12)
    def piano(t0, notas, cada=0.55, v=0.12):
        for i, m in enumerate(notas):
            L = int(2.5*SR); x = np.arange(L)/SR; f = nf(m)
            tono = (np.sin(2*np.pi*f*x) + 0.4*np.sin(2*np.pi*2*f*x) + 0.15*np.sin(2*np.pi*3*f*x))*np.exp(-x*2.2)*np.minimum(1, x/0.005)
            pon(t0 + i*cada, tono, v)
    # 1. la calle: se encienden las luces
    for k in (0.6, 1.1, 1.5, 1.9, 2.3, 2.6, 3.0, 3.3, 3.6, 3.9):
        click(k)
    piano(0.3, [57, 64, 60, 64, 57, 64, 60, 64], 0.5, 0.13)
    # 2. el golpe: la mano, la luz que se apaga
    a = T0[p_golpe]
    pon(a - 1.0, riser(1.4), 0.9)
    pon(a + 0.9, braam(1.3))
    # 3. el titulo
    a = T0[p_titulo]
    pon(a, subcaida(1.0)); pon(a + 0.2, braam(0.7, 55.0), 0.6)
    # 4. los capitulos: piano triste, un whoosh en cada salto de ventana
    for fn, notas in ((GUION[3][0], [69, 67, 64, 67]), (GUION[4][0], [72, 71, 69, 64]), (GUION[5][0], [76, 74, 72, 74]), (GUION[6][0], [69, 72, 71, 67])):
        a = T0[fn]
        pon(a - 0.25, whoosh(0.5), 1.0)
        pon(a, subcaida(0.45))
        piano(a + 0.2, notas, 0.7, 0.11)
    pon(T0[GUION[4][0]] + 2.0, subcaida(0.6))                       # el beso
    a = T0[GUION[6][0]]
    pon(a + 1.35, rnd.standard_normal(int(0.3*SR))*np.exp(-np.arange(int(0.3*SR))/SR*14), 0.25)   # el plato roto
    # 5. la 2B: latido y tension
    a = T0[p_2b]
    pon(a - 0.25, whoosh(0.6))
    latido(a + 0.3, 6, 0.62)
    pon(a + 2.4, riser(1.6), 1.0)
    # 6. los tres cortes, cada golpe mas grave
    for i, fn in enumerate((GUION[8][0], GUION[9][0], p_corte_apagon)):
        a = T0[fn] + (0.45 if fn is p_corte_apagon else 0.0)
        pon(a, braam(0.9 + 0.25*i, 49.0 - i*4))
    # 7. el final: silencio... la luz de la 2B, y el golpe mas grave
    a = T0[p_final_ancho]
    click(a + 1.5)
    pon(a + 1.6, whoosh(0.7))
    a = T0[p_prismaticos]
    pon(a + 0.6, riser(1.6), 1.1)
    pon(a + 2.2, braam(1.6, 32.7)); pon(a + 2.2, subcaida(1.4))
    a = T0[p_fin]
    piano(a + 0.3, [57, 60, 64], 0.6, 0.08)
    # silencios dramaticos: justo antes de cada golpe, se corta el fondo
    mix = out[:n]
    for tg in (T0[p_golpe] + 0.75, T0[p_prismaticos] + 1.9):
        s0, s1 = int(tg*SR), int((tg + 0.25)*SR)
        mix[s0:s1] *= np.linspace(1, 0.15, s1 - s0)
    mix = mix/np.sqrt(np.mean(mix**2))*0.12
    mix = np.tanh(mix*1.4)*0.92
    mix[-int(1.2*SR):] *= np.linspace(1, 0, int(1.2*SR))
    est = np.stack([mix, np.roll(mix, int(0.012*SR))*0.96], 1)      # un poco de amplitud estereo
    with wave.open(ruta, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(est, -1, 1)*32767).astype(np.int16).tobytes())

def main():
    Path(OUT).mkdir(exist_ok=True)
    a = sys.argv[1:]
    if a and a[0] == "fotos":
        ims = []
        for x0, x1, fn in TABLA:
            for f in (0.3, 0.85):
                ims.append(fotograma(x0 + (x1 - x0)*f).resize((384, 216)))
        cols = 4; filas = (len(ims) + cols - 1)//cols
        hoja = Image.new("RGB", (384*cols, 216*filas))
        for i, im in enumerate(ims):
            hoja.paste(im, ((i % cols)*384, (i//cols)*216))
        hoja.save(OUT + "teaser_hoja.jpg", quality=85); print(f"{DUR:.1f} s"); return
    if a and a[0] == "en":
        for s in a[1:]:
            fotograma(float(s)).resize((960, 540)).save(OUT + f"teaser_{float(s):05.1f}.jpg", quality=88)
        return
    audio(OUT + "teaser.wav")
    if a and a[0] == "audio":
        return
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", OUT + "teaser.wav", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19", "-preset", "medium",
                          "-c:a", "aac", "-b:a", "192k", "-shortest", OUT + "ACROSS_teaser.mp4"], stdin=subprocess.PIPE)
    for i in range(int(DUR*FPS)):
        p.stdin.write(fotograma(i/FPS).tobytes())
    p.stdin.close(); p.wait()
    print(f"hecho: {DUR:.1f} s")

if __name__ == "__main__":
    main()
