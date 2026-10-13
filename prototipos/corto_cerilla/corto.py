"""Ejemplo de corto sin voz (30 s): "ONE MORE".
La cerilla (protagonista) y la nube (su compañero de trabajo). Mundo en
blanco y negro; el único color es la cabeza roja y la llama de la cerilla.
Planos de cine: general, primer plano, por encima del hombro con desenfoque,
contraplano. Diálogo en texto corto sobre la cabeza y música de fondo."""
import math, random, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageEnhance

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app import escenarios

OUT = str(Path(__file__).resolve().parent) + "/salida/"
FPS, DUR = 25, 30.0
CW, CH = 1600, 900          # lienzo de trabajo
VW, VH = 1280, 720          # vídeo
T = (22, 22, 26)
ROJO, LLAMA, LLAMA2 = (205, 50, 45), (250, 150, 40), (255, 228, 110)
NUBE = (214, 216, 222)
FUENTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def fuente(px): return ImageFont.truetype(FUENTE, int(px))
def suave(x): x = min(1, max(0, x)); return x*x*(3 - 2*x)

# ---------------------------------------------------------------- fondos
def gris(nombre, oscuro=0.0, claro=0.0, espejo=False):
    im = Image.fromarray(escenarios.pinta(nombre, (CW, CH), int(CH*0.82)))
    im = ImageOps.grayscale(im).convert("RGB")
    im = ImageEnhance.Contrast(im).enhance(1.35)
    if oscuro: im = Image.blend(im, Image.new("RGB", im.size, (12, 13, 22)), oscuro)
    if claro: im = Image.blend(im, Image.new("RGB", im.size, (250, 250, 246)), claro)
    return ImageOps.mirror(im) if espejo else im

def de_dia(im):
    """La ventana del dormitorio es de noche: de día, cielo claro y sol."""
    d = ImageDraw.Draw(im)
    d.rectangle([642, 74, 958, 356], fill=(236, 236, 234))
    d.line([(642, 214), (958, 214)], fill=(150, 150, 150), width=4)
    d.ellipse([820, 100, 920, 200], fill=(255, 255, 255), outline=(170, 170, 170), width=4)
    return im.filter(ImageFilter.GaussianBlur(1.5))

FONDOS = {}
def fondo(clave):
    if clave not in FONDOS:
        FONDOS[clave] = {
            "noche": lambda: gris("dormitorio", oscuro=0.7),
            "manana": lambda: de_dia(gris("dormitorio", claro=0.25)),
            "oficina": lambda: gris("oficina", claro=0.05),
            "oficina_e": lambda: gris("oficina", claro=0.05, espejo=True),
        }[clave]()
    return FONDOS[clave].copy()

def recorte(im, cx, cy, zoom):
    """La cámara: un trozo de la imagen centrado en (cx, cy), al tamaño del lienzo."""
    w, h = CW/zoom, CH/zoom
    x0 = min(max(0, cx - w/2), CW - w); y0 = min(max(0, cy - h/2), CH - h)
    return im.resize((CW, CH), Image.LANCZOS, box=(x0, y0, x0 + w, y0 + h))

# ---------------------------------------------------------------- ojos
def ojos(d, cx, cy, s, piel, cansancio=0.0, parpadeo=0.0, mira=(0, 0), ceja=0.0, dirx=0.0, feliz=0.0, sorpresa=0.0):
    cx = cx + dirx*s*0.16           # mira hacia un lado: los ojos se van a ese lado de la cara
    for lado in (-1, 1):
        ex = cx + lado*s*0.32; rx, ry = s*0.16, s*0.2
        if sorpresa:                 # cejas arriba, en arco
            y = cy - ry*(1.5 + 0.5*sorpresa)
            d.arc([ex - rx, y - ry*0.3, ex + rx, y + ry*0.5], 200, 340, fill=T, width=max(3, int(s*0.035)))
        if feliz > 0.5:              # ojos sonrientes: dos arcos
            d.arc([ex - rx, cy - ry*0.5, ex + rx, cy + ry*1.1], 200, 340, fill=T, width=max(4, int(s*0.045)))
            if ceja:
                y = cy - ry*1.2
                d.line([(ex - lado*rx*0.9, y - ceja*ry*0.35), (ex + lado*rx*1.0, y + ceja*ry*0.35)], fill=T, width=max(3, int(s*0.035)))
            continue
        d.ellipse([ex - rx, cy - ry, ex + rx, cy + ry], fill=(250, 250, 250), outline=T, width=max(3, int(s*0.025)))
        px, py = ex + mira[0]*s*0.06, cy + mira[1]*s*0.08
        d.ellipse([px - s*0.07, py - s*0.08, px + s*0.07, py + s*0.08], fill=T)
        f = max(cansancio*0.6, parpadeo)
        if f > 0.03:
            s0 = -1 + 2*min(1.0, f)
            a = math.degrees(math.asin(max(-1, min(1, s0))))
            caja = [ex - rx - 1, cy - ry - 1, ex + rx + 1, cy + ry + 1]
            if f >= 0.98:
                d.ellipse(caja, fill=piel); d.line([(ex - rx, cy + ry*0.6), (ex + rx, cy + ry*0.6)], fill=T, width=max(3, int(s*0.03)))
            else:
                d.chord(caja, 180 - a, 360 + a, fill=piel)
                yl = cy + ry*s0; xl = rx*math.sqrt(max(0, 1 - s0*s0))
                d.line([(ex - xl, yl), (ex + xl, yl)], fill=T, width=max(3, int(s*0.03)))
        if ceja:     # ceja: + = triste/cansado (cae hacia fuera), - = sorprendido (sube)
            y = cy - ry*1.45
            d.line([(ex - lado*rx*0.9, y - ceja*ry*0.35), (ex + lado*rx*1.0, y + ceja*ry*0.35)], fill=T, width=max(3, int(s*0.035)))

# ---------------------------------------------------------------- personajes
def llama(d, cx, base, tam, t):
    if tam <= 0.02: return
    rnd = random.Random(int(t*12)); fl = 1 + 0.08*rnd.uniform(-1, 1)
    hgt, w = tam*fl, tam*0.42
    sway = math.sin(t*9)*w*0.15
    d.polygon([(cx + sway, base - hgt), (cx + w, base - hgt*0.35), (cx + w*0.6, base), (cx - w*0.6, base), (cx - w, base - hgt*0.35)],
              fill=LLAMA, outline=T)
    d.polygon([(cx + sway*0.6, base - hgt*0.62), (cx + w*0.42, base - hgt*0.2), (cx, base), (cx - w*0.42, base - hgt*0.2)], fill=LLAMA2)

def humo(d, cx, base, s, t):
    for i in range(3):
        k = (t*0.6 + i/3) % 1.0
        y = base - k*s*1.6; x = cx + math.sin(k*6 + i)*s*0.15
        a = int(200*(1 - k))
        col = (a + 40, a + 40, a + 44) if a else None
        w = s*(0.18 + 0.2*k)
        d.arc([x - w, y - w*0.6, x + w, y + w*0.6], 200, 340, fill=(190, 190, 196), width=max(3, int(s*0.05)))

def piernas(d, cx, cad, suelo, h, sep=0.06, fase=None):
    if fase is not None:            # andando: cada pierna adelante y atrás, levantando el pie
        for lado in (-1, 1):
            f = fase + (0 if lado < 0 else math.pi)
            fx = cx + lado*h*sep*0.5 + math.sin(f)*h*0.07
            lev = max(0.0, math.cos(f))*h*0.035
            d.line([(cx + lado*h*sep*0.5, cad), (fx, suelo - h*0.01 - lev)], fill=T, width=max(4, int(h*0.018)))
            d.ellipse([fx - h*0.045, suelo - h*0.03 - lev, fx + h*0.045, suelo + h*0.01 - lev], fill=T)
        return
    for lado in (-1, 1):
        d.line([(cx + lado*h*sep, cad), (cx + lado*h*(sep + 0.01), suelo - h*0.01)], fill=T, width=max(4, int(h*0.018)))
        d.ellipse([cx + lado*h*(sep + 0.01) - h*0.045, suelo - h*0.03, cx + lado*h*(sep + 0.01) + h*0.045, suelo + h*0.01], fill=T)

def brazos(d, hombros, h, pose, mano_obj=None, piel=(240, 236, 226), fase=None):
    """hombros: ((x,y),(x,y)); pose: movil / caido / mesa / anda / taza / brindis / arriba.
    Devuelve el punto medio de las manos."""
    manos = []
    lado_b = 1
    if pose == "brindis" and mano_obj is not None:     # brinda con el brazo del lado de la copa
        lado_b = 1 if mano_obj[0] >= (hombros[0][0] + hombros[1][0])/2 else -1
    for lado, (hx, hy) in zip((-1, 1), hombros):
        if pose == "brindis":
            if lado == lado_b:
                c = (hx + lado*h*0.09, hy + h*0.05); m = mano_obj
            else:
                c = (hx + lado*h*0.03, hy + h*0.14); m = (hx + lado*h*0.04, hy + h*0.28)
        elif pose == "anda" or (pose == "taza" and lado == -1 and fase is not None):
            f = (fase or 0) + (math.pi if lado < 0 else 0)
            c = (hx + lado*h*0.02 + math.sin(f)*h*0.04, hy + h*0.14); m = (hx + lado*h*0.02 + math.sin(f)*h*0.09, hy + h*0.27)
        elif pose == "brindis" and lado == 1:
            c = (hx + h*0.09, hy + h*0.05); m = mano_obj
        elif pose == "arriba":        # se estira por la mañana
            c = (hx + lado*h*0.05, hy - h*0.12); m = (hx + lado*h*0.08, hy - h*0.25)
        elif pose == "taza" and lado == 1:
            c = (hx + h*0.07, hy + h*0.15); m = mano_obj
        elif pose == "movil":
            c = (hx + lado*h*0.06, hy + h*0.13); m = (mano_obj[0] + lado*h*0.03, mano_obj[1])
        elif pose == "mesa":
            c = (hx + lado*h*0.08, hy + h*0.12); m = (hx + lado*h*0.02, mano_obj[1])
        else:
            c = (hx + lado*h*0.03, hy + h*0.14); m = (hx + lado*h*0.04, hy + h*0.28)
        d.line([(hx, hy), c, m], fill=T, width=max(4, int(h*0.018)), joint="curve")
        r = h*0.022
        d.ellipse([m[0] - r, m[1] - r, m[0] + r, m[1] + r], fill=piel, outline=T, width=max(2, int(h*0.008)))
        manos.append(m)
    return ((manos[0][0] + manos[1][0])/2, (manos[0][1] + manos[1][1])/2)

def movil(d, x, y, h, encendido=True):
    w, hh = h*0.04, h*0.07
    d.rounded_rectangle([x - w, y - hh, x + w, y + hh*0.4], radius=max(3, int(h*0.01)), fill=(18, 18, 22), outline=T, width=3)
    if encendido:
        d.rounded_rectangle([x - w*0.78, y - hh*0.88, x + w*0.78, y + hh*0.28], radius=max(2, int(h*0.007)), fill=(250, 250, 252))

def cerilla(img, cx, cadera, suelo, h, st, t):
    """cadera: donde acaba el palo (sentado = en el asiento). st: llama, humo, cansancio,
    parpadeo, mira, ceja, pose, espalda, inclina, sin_piernas."""
    d = ImageDraw.Draw(img)
    resp = 1 + 0.012*math.sin(t*2*math.pi/3.2)
    fase = st.get("fase")
    if fase is not None:
        cadera -= abs(math.sin(fase))*h*0.014
    largo = h*0.5*resp; r = h*0.13
    inc = st.get("inclina", 0.0)*h          # se encorva: la cabeza baja y se adelanta
    top = cadera - largo + abs(inc)*0.35
    if not st.get("sin_piernas"):
        piernas(d, cx, cadera - h*0.02, suelo, h, fase=fase)
    a = h*0.05
    d.polygon([(cx - a, cadera), (cx + a, cadera), (cx + a + inc*0.3, top + r*0.3), (cx - a + inc*0.3, top + r*0.3)],
              fill=(236, 228, 210), outline=T)
    d.line([(cx - a, cadera), (cx - a + inc*0.3, top + r*0.3)], fill=T, width=max(3, int(h*0.012)))
    d.line([(cx + a, cadera), (cx + a + inc*0.3, top + r*0.3)], fill=T, width=max(3, int(h*0.012)))
    hx, hy = cx + inc*0.4, top - r*0.35
    cab = ROJO if not st.get("espalda") else (150, 38, 36)
    d.ellipse([hx - r, hy - r*1.15, hx + r, hy + r*0.95], fill=cab, outline=T, width=max(3, int(h*0.012)))
    if st.get("llama", 0) > 0.02:
        llama(d, hx, hy - r*1.0, r*1.5*st["llama"], t)
    if st.get("humo"):
        humo(d, hx, hy - r*1.1, r, t)
    if not st.get("espalda"):
        ojos(d, hx, hy - r*0.05, r*1.5, cab, st.get("cansancio", 0), st.get("parpadeo", 0), st.get("mira", (0, 0.6)), st.get("ceja", 0),
             st.get("dir", 0.0), st.get("feliz", 0.0), st.get("sorpresa", 0.0))
    hombros = ((cx - a + inc*0.3, top + h*0.12), (cx + a + inc*0.3, top + h*0.12))
    pose = st.get("pose", "caido")
    obj = st.get("objeto") or (hx, top + h*0.16)
    if st.get("espalda"):
        return (hx, hy - r*1.3), None
    mano = brazos(d, hombros, h, pose, obj, fase=fase)
    return (hx, hy - r*1.3), mano

def nube(img, cx, suelo, h, st, t):
    d = ImageDraw.Draw(img)
    resp = 1 + 0.012*math.sin(t*2*math.pi/3.6 + 1)
    fase = st.get("fase")
    r = h*0.11; cy = suelo - h*0.72*resp - (abs(math.sin(fase))*h*0.014 if fase is not None else 0)
    piernas(d, cx, suelo - h*0.22, suelo, h, fase=fase)
    cuerpo = (58, 58, 62) if not st.get("espalda") else (30, 30, 34)
    d.rounded_rectangle([cx - h*0.1, cy + r*0.9, cx + h*0.1, suelo - h*0.2], radius=int(h*0.05), fill=cuerpo, outline=T, width=max(3, int(h*0.01)))
    bolas = [(-1.1, 0.25, 0.85), (1.1, 0.25, 0.85), (-0.5, -0.4, 1.0), (0.5, -0.35, 1.05), (0, 0.3, 1.1)]
    col = NUBE if not st.get("espalda") else (92, 94, 100)
    for bx, by, br in bolas:
        d.ellipse([cx + bx*r - br*r, cy + by*r - br*r, cx + bx*r + br*r, cy + by*r + br*r], fill=T)
    for bx, by, br in bolas:
        b2 = br*r - max(3, h*0.009)
        d.ellipse([cx + bx*r - b2, cy + by*r - b2, cx + bx*r + b2, cy + by*r + b2], fill=col)
    if not st.get("espalda"):
        ojos(d, cx, cy + r*0.15, r*1.7, col, st.get("cansancio", 0), st.get("parpadeo", 0), st.get("mira", (0, 0)), st.get("ceja", 0),
             st.get("dir", 0.0), st.get("feliz", 0.0), st.get("sorpresa", 0.0))
        hombros = ((cx - h*0.1, cy + r*1.4), (cx + h*0.1, cy + r*1.4))
        pose = st.get("pose", "caido")
        if pose in ("taza", "brindis"):
            mx, my = (cx + h*0.09, cy + r*2.9) if pose == "taza" else (st.get("objeto") or (cx + h*0.2, cy - r*0.2))
            brazos(d, hombros, h, pose, (mx, my), piel=col, fase=fase)
            if st.get("vaso"):
                return (cx, cy - r*1.5)
            d.rounded_rectangle([mx - h*0.035, my - h*0.075, mx + h*0.035, my + h*0.01], radius=6, fill=(250, 250, 248), outline=T, width=4)
            d.arc([mx + h*0.02, my - h*0.06, mx + h*0.065, my - h*0.015], 270, 90, fill=T, width=4)
            for i in range(2):     # el vapor del café
                k = (t*0.7 + i*0.5) % 1.0
                d.arc([mx - 14 + i*10, my - h*0.12 - k*40, mx + 6 + i*10, my - h*0.08 - k*40], 200, 340, fill=(170, 170, 176), width=3)
        else:
            brazos(d, hombros, h, pose, piel=col, fase=fase)
    return (cx, cy - r*1.5)

def silla(img, cx, y0, y1, ancho):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([cx - ancho/2, y0, cx + ancho/2, y1], radius=int(ancho*0.18), fill=(52, 52, 58), outline=T, width=4)
    d.rounded_rectangle([cx - ancho*0.36, y0 + ancho*0.12, cx + ancho*0.36, y1 - ancho*0.1], radius=int(ancho*0.12), fill=(64, 64, 70))

def mesa(img, x0, x1, y, portatil=True, px=None):
    d = ImageDraw.Draw(img)
    if portatil:
        cx = px if px is not None else (x0 + x1)/2
        d.polygon([(cx - 120, y), (cx + 120, y), (cx + 108, y - 120), (cx - 108, y - 120)], fill=(70, 72, 78), outline=T)
        d.line([(cx - 120, y), (cx + 120, y)], fill=T, width=5)
        d.ellipse([cx - 13, y - 72, cx + 13, y - 46], fill=(120, 122, 128))
    d.rectangle([x0, y, x1, y + 26], fill=(150, 146, 140), outline=T, width=4)
    d.rectangle([x0 + 10, y + 26, x1 - 10, CH], fill=(118, 116, 112), outline=T, width=4)
    d.line([(x0 + 10, y + 120), (x1 - 10, y + 120)], fill=(96, 94, 90), width=4)

def luz(img, x, y, rad, fuerza=0.5, color=(235, 238, 255)):
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).ellipse([x - rad, y - rad, x + rad, y + rad], fill=int(255*fuerza))
    m = m.filter(ImageFilter.GaussianBlur(rad*0.45))
    return Image.composite(Image.new("RGB", img.size, color), img, m)

# ---------------------------------------------------------------- textos
def dice(img, texto, x, y, t0, t, px=40):
    """Texto blanco con borde negro encima del que habla, que se escribe rápido."""
    if t < t0: return
    n = min(len(texto), int((t - t0)*38) + 1)
    d = ImageDraw.Draw(img)
    d.text((x, y), texto[:n], font=fuente(px), fill=(255, 255, 255), anchor="ms", stroke_width=max(3, int(px*0.12)), stroke_fill=T)

def reloj_tarjeta(img, hora, x, y, sacudida=0.0, t=0.0):
    d = ImageDraw.Draw(img)
    dx = math.sin(t*70)*sacudida*8
    d.rounded_rectangle([x - 150 + dx, y - 48, x + 150 + dx, y + 48], radius=16, fill=(248, 248, 246), outline=T, width=4)
    d.text((x + dx, y + 2), hora, font=fuente(50), fill=T, anchor="mm")

def parpadeo(t, cada=3.7, fase=0.0):
    k = (t + fase) % cada
    return max(0.0, 1 - abs(k - 0.09)/0.09) if k < 0.18 else 0.0

def desenfoca(capa, radio):
    return capa.filter(ImageFilter.GaussianBlur(radio))

# ---------------------------------------------------------------- los planos
def cama(img, k, ox, oy, st, t, luz_movil=0.0):
    """Sentada en la cama, apoyada en el cabecero, con la manta hasta la
    cintura y el móvil delante de la cara. Coordenadas de escena (0-1600)
    escaladas por k y movidas a (ox, oy)."""
    P = lambda x, y: (ox + x*k, oy + y*k)
    R = lambda x0, y0, x1, y1: [*P(x0, y0), *P(x1, y1)]
    d = ImageDraw.Draw(img); g = max(3, int(4*k))
    d.rounded_rectangle(R(170, 300, 560, 1000), radius=int(30*k), fill=(70, 70, 74), outline=T, width=g)   # cabecero
    d.rectangle(R(140, 640, 1500, 1000), fill=(96, 96, 100), outline=T, width=g)                         # somier
    d.rounded_rectangle(R(130, 590, 1500, 680), radius=int(24*k), fill=(205, 205, 208), outline=T, width=g)  # colchón
    d.rounded_rectangle(R(230, 410, 500, 600), radius=int(50*k), fill=(236, 236, 238), outline=T, width=g)   # almohada
    h = 560*k
    pose = st.get("pose")
    obj = P(385, 480) if pose == "movil" else None
    stc = dict(st, sin_piernas=True, objeto=obj, pose=pose or "caido")
    cab, mano = cerilla(img, *P(365, 640), P(0, 900)[1], h, stc, t)
    # la manta: tapa de la cintura para abajo, con el bulto de las piernas estiradas
    manta = [P(200, 690), P(215, 560), P(330, 545), P(430, 548), P(560, 556), P(800, 548), P(980, 540),
             P(1150, 556), P(1300, 572), P(1420, 580), P(1470, 690)]
    d = ImageDraw.Draw(img)
    d.polygon(manta, fill=(150, 150, 154))
    d.line(manta, fill=T, width=g)
    d.line([P(215, 600), P(1460, 620)], fill=(128, 128, 132), width=g)        # el embozo
    for x in (700, 1000, 1250):
        d.arc(R(x - 70, 560, x + 70, 640), 200, 330, fill=(120, 120, 124), width=g)
    if pose == "movil":
        movil(d, mano[0], mano[1], h)
    return cab, mano

def con_luz(img, k, ox, oy, fuerza):
    if fuerza <= 0: return img
    x, y = ox + 380*k, oy + 400*k
    return luz(img, x, y, 230*k, fuerza)

def cuarto(clave):
    """El cuarto sin la cama del dibujo: la ventana y la mesilla."""
    return recorte(fondo(clave), 1050, 330, 1.4)

def plano_1(t):     # 0 - 4.5  general: en la cama con el móvil, de noche
    lt = t
    img = cuarto("noche")
    st = dict(llama=1.0, cansancio=0.1, parpadeo=parpadeo(lt), mira=(0.3, 0.9), pose="movil")
    k, ox, oy = 0.95, 60, 150
    img = con_luz(img, k, ox, oy, 0.45)
    cab, mano = cama(img, k, ox, oy, st, t)
    reloj_tarjeta(img, "11:58 PM", 1020, 230, 0, t)
    dice(img, "Just one more video.", cab[0] + 60, cab[1] - 70, 1.3, lt)
    return img, (560 + lt*12, 430, 1.25 + 0.025*lt)

HORAS2 = [(0.0, "12:40 AM", 0.75, 0.3), (1.5, "2:15 AM", 0.45, 0.55), (3.0, "3:47 AM", 0.2, 0.85)]
def plano_2(t):     # 4.5 - 9  primer plano: pasan las horas y la llama se va apagando
    lt = t - 4.5
    hora, tam, cans = HORAS2[0][1:]
    for t0, hh, ll, cc in HORAS2:
        if lt >= t0: hora, tam, cans = hh, ll, cc
    img = recorte(fondo("noche"), 1000, 250, 2.2)
    k, ox, oy = 2.3, -100, -380
    st = dict(llama=tam, cansancio=cans, parpadeo=parpadeo(lt, 2.4, 1.0), mira=(0.3, 0.9), pose="movil", ceja=0.4*cans,
              inclina=-0.03*cans)
    img = con_luz(img, k, ox, oy, 0.5)
    cama(img, k, ox, oy, st, t)
    reloj_tarjeta(img, hora, 1320, 140, 0, t)
    for t0, *_ in HORAS2[1:]:          # un parpadeo de la imagen al cambiar la hora
        if 0 <= lt - t0 < 0.12:
            img = Image.blend(img, Image.new("RGB", img.size, (0, 0, 0)), 0.5)
    return img, (800, 450, 1.0 + 0.012*lt)

def plano_3(t):     # 9 - 12  suena el despertador; la llama se ha apagado
    lt = t - 9.0
    img = cuarto("manana")
    img = luz(img, 800, 150, 500, 0.3, (255, 255, 250))
    st = dict(llama=0, humo=True, cansancio=0.95, parpadeo=0, mira=(0, 0.6), pose=None, ceja=0.8, inclina=-0.06)
    k, ox, oy = 0.95, 60, 150
    cama(img, k, ox, oy, st, t)
    suena = (lt % 0.5) < 0.3
    reloj_tarjeta(img, "7:00 AM", 1020, 230, 1.0 if suena else 0.0, t)
    if suena:
        d = ImageDraw.Draw(img)
        for lado in (-1, 1):
            for kk in range(3):
                x = 1020 + lado*(175 + kk*22)
                d.line([(x, 200 - kk*8), (x + lado*10, 260 + kk*8)], fill=T, width=5)
    return img, (560, 430, 1.3)

def plano_4(t):     # 12 - 17.5  oficina, por encima del hombro de la nube
    lt = t - 12.0
    img = fondo("oficina")
    st = dict(llama=0, humo=True, cansancio=0.85, parpadeo=parpadeo(lt, 3.1, 0.5), mira=(-0.5 if lt < 2.4 else -0.8, 0.3),
              pose="mesa", objeto=(0, 700), ceja=0.7, inclina=-0.05, sin_piernas=True)
    silla(img, 1040, 470, 760, 300)
    cab, _ = cerilla(img, 1040, 800, 900, 700, st, t)
    mesa(img, 760, 1320, 720, px=1040)
    # la nube, de espaldas, enorme y desenfocada delante a la izquierda
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    nube(capa, 250, 2000, 2000, dict(espalda=True), t)
    capa = desenfoca(capa, 12)
    img.paste(capa, (0, 0), capa)
    dice(img, "Rough night?", 420, 140, 0.5, lt, 46)
    dice(img, "Just one more video...", cab[0], cab[1] - 30, 2.6, lt, 42)
    return img, (900, 470, 1.0 + 0.01*lt)

def plano_5(t):     # 17.5 - 22  contraplano: la nube, por encima del hombro de la cerilla
    lt = t - 17.5
    img = fondo("oficina_e")
    st = dict(cansancio=0.15 + 0.35*suave((lt - 1.8)/0.4), parpadeo=parpadeo(lt, 2.9, 1.8), mira=(0.7, 0.1), ceja=0.15,
              pose="taza")
    cab = nube(img, 640, 790, 560, st, t)
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    cerilla(capa, 1380, 1500, 2400, 1500, dict(espalda=True, humo=True), t)
    capa = desenfoca(capa, 12)
    img.paste(capa, (0, 0), capa)
    dice(img, "You said that yesterday.", cab[0] + 30, cab[1] - 20, 0.6, lt, 44)
    return img, (760, 450, 1.0 + 0.012*lt)

def plano_6(t):     # 22 - 25.5  solo en su mesa: mira el móvil... y lo deja boca abajo
    lt = t - 22.0
    img = fondo("oficina")
    deja = suave((lt - 1.6)/0.5)
    vuelve = suave((lt - 2.3)/0.8)        # una chispa: la llama vuelve, pequeñita
    obj = (805 + 50*deja, 640 + 70*deja)
    st = dict(llama=0.35*vuelve, humo=vuelve < 0.3, cansancio=0.8 - 0.35*vuelve, parpadeo=parpadeo(lt, 9, 2.9),
              mira=(0.2, 1.0 - 1.3*vuelve), pose="movil", objeto=obj, ceja=0.7 - 0.6*vuelve, sin_piernas=True)
    if deja < 0.5:
        tmp = img.copy(); silla(tmp, 800, 520, 760, 270); cerilla(tmp, 800, 800, 900, 600, st, t)
        img = luz(img, obj[0], obj[1] - 60, 200, 0.45*(1 - deja*2))
    silla(img, 800, 520, 760, 270)
    cab, mano = cerilla(img, 800, 800, 900, 600, st, t)
    mesa(img, 450, 1150, 720, portatil=False)
    d = ImageDraw.Draw(img)
    if deja < 0.95:
        movil(d, mano[0], mano[1], 600, encendido=deja < 0.5)
    else:
        d.rounded_rectangle([830, 708, 910, 721], radius=4, fill=(18, 18, 22), outline=T, width=2)   # boca abajo
    return img, (800, 480, 1.08 - 0.02*lt)

def plano_7(t):     # 25.5 - 30  la frase final
    lt = t - 25.5
    img = Image.new("RGB", (CW, CH), (10, 10, 12)); d = ImageDraw.Draw(img)
    for t0, txt, y, px, col in ((0.4, "One more video", 400, 64, (255, 255, 255)),
                                (1.3, "always costs one more morning.", 490, 64, (255, 255, 255)),
                                (2.6, "WHY THOUGH", 720, 30, (150, 150, 155))):
        a = suave((lt - t0)/0.6)
        if a > 0:
            c = tuple(int(10 + (v - 10)*a) for v in col)
            d.text((CW/2, y), txt, font=fuente(px), fill=c, anchor="mm")
    llama(d, CW/2 + 210, 455 - 0, 0, t)
    return img, (CW/2, CH/2, 1.0)

PLANOS = [(0, 4.5, plano_1), (4.5, 9.0, plano_2), (9.0, 12.0, plano_3), (12.0, 17.5, plano_4),
          (17.5, 22.0, plano_5), (22.0, 25.5, plano_6), (25.5, 30.0, plano_7)]

def fotograma(t):
    for a, b, fn in PLANOS:
        if a <= t < b:
            img, (cx, cy, z) = fn(t)
            break
    img = recorte(img, cx, cy, z) if z > 1.001 else img
    img = img.resize((VW, VH), Image.LANCZOS)
    # fundidos a negro: entre la noche y la mañana, y al final
    neg = 0.0
    if 8.75 <= t < 9.25: neg = 1 - abs(t - 9.0)/0.25
    if t < 0.4: neg = 1 - t/0.4
    if t > DUR - 0.6: neg = (t - (DUR - 0.6))/0.6
    if neg > 0:
        img = Image.blend(img, Image.new("RGB", img.size, (0, 0, 0)), min(1, neg))
    # viñeta suave: más de cine
    return img

_VIN = None
def vineta(img):
    global _VIN
    if _VIN is None:
        m = Image.new("L", (VW, VH), 0)
        ImageDraw.Draw(m).ellipse([-VW*0.15, -VH*0.2, VW*1.15, VH*1.2], fill=255)
        _VIN = m.filter(ImageFilter.GaussianBlur(120))
    return Image.composite(img, Image.blend(img, Image.new("RGB", img.size, (0, 0, 0)), 0.45), _VIN)

# ---------------------------------------------------------------- la música (hecha aquí, sin derechos)
def musica(ruta):
    sr = 44100; n = int(sr*DUR); t = np.arange(n)/sr
    out = np.zeros(n)
    def nota(f): return 440*2**((f - 69)/12)
    # La menor lo-fi: Am7 - Fmaj7 - Cmaj7 - G6, 2,5 s cada uno
    acordes = [[57, 60, 64, 67], [53, 57, 60, 64], [48, 55, 59, 64], [55, 59, 62, 64]]
    dur = 2.5
    for i in range(int(DUR/dur) + 1):
        ac = acordes[i % 4]; t0 = i*dur
        s0, s1 = int(t0*sr), min(n, int((t0 + dur + 0.6)*sr))
        if s0 >= n: break
        tt = t[s0:s1] - t0
        env = np.minimum(1, tt/0.8)*np.exp(-np.maximum(0, tt - dur)*4)
        for m in ac:   # colchón suave
            f = nota(m)
            out[s0:s1] += 0.05*env*(np.sin(2*np.pi*f*tt) + 0.3*np.sin(2*np.pi*2*f*tt + 0.5))
        out[s0:s1] += 0.07*env*np.sin(2*np.pi*nota(ac[0] - 12)*tt)    # bajo
        for k, m in enumerate([ac[0] + 12, ac[2] + 12, ac[1] + 12, ac[3] + 12]):   # piano tenue
            a0 = int((t0 + k*0.625)*sr); a1 = min(n, a0 + int(1.6*sr))
            if a0 >= n: continue
            ta = t[a0:a1] - (t0 + k*0.625); f = nota(m)
            out[a0:a1] += 0.06*np.exp(-ta*2.6)*(np.sin(2*np.pi*f*ta) + 0.25*np.sin(2*np.pi*3*f*ta))
    out += 0.004*np.random.default_rng(1).standard_normal(n)      # el siseo del vinilo
    # el despertador (9 - 12 s)
    for k in range(6):
        b0 = 9.0 + k*0.5; s0, s1 = int(b0*sr), int((b0 + 0.3)*sr)
        tt = t[s0:s1] - b0
        out[s0:s1] += 0.10*np.sign(np.sin(2*np.pi*1800*tt))*np.minimum(1, tt/0.01)*np.minimum(1, (0.3 - tt)/0.01)
    fade = np.ones(n); fi = int(0.5*sr); fo = int(1.5*sr)
    fade[:fi] = np.linspace(0, 1, fi); fade[-fo:] = np.linspace(1, 0, fo)
    out = np.convolve(out*fade, np.ones(6)/6, mode="same")       # un pelín más cálido
    out = out/np.max(np.abs(out))*0.6
    pcm = (out*32767).astype(np.int16)
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())

def main(solo_fotos=False):
    Path(OUT).mkdir(exist_ok=True)
    if solo_fotos:
        for s in (2.5, 6.0, 8.0, 10.5, 15.5, 19.5, 22.8, 25.0, 28.5):
            vineta(fotograma(s)).save(OUT + f"foto_{s:04.1f}.jpg", quality=88)
        return
    musica(OUT + "musica.wav")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}",
                          "-r", str(FPS), "-i", "-", "-i", OUT + "musica.wav", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                          "-crf", "20", "-preset", "medium", "-c:a", "aac", "-b:a", "160k", "-shortest",
                          OUT + "one_more_ejemplo.mp4"], stdin=subprocess.PIPE)
    for i in range(int(DUR*FPS)):
        p.stdin.write(vineta(fotograma(i/FPS)).tobytes())
    p.stdin.close(); p.wait()

if __name__ == "__main__":
    main(solo_fotos="fotos" in sys.argv)
