"""BURNOUT — segundo corto de STILL BURNING (sin voz).

La empresa es una caja de cerillas y el jefe es la caja: cada vez que hace
falta "fuego", frota a la cerilla contra su costado. Ella arde y su PALO (lo
que le queda de sí misma) se acorta. El jefe nunca se quema.
  día 1: palo 1.0 -> 0.95 · día 12: 0.85 · día 20: 0.8 · día 31: 0.72
  día 40: 0.68 · día 58: 0.62 · día 74: 0.55 · día 89: 0.5 (y ahí dice "No.")
"""
import math, random, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corto as C
import one_more as M
from corto import T, suave, parpadeo, fuente

OUT = str(Path(__file__).resolve().parent) + "/salida/"
FPS = 25
CW, CH = C.CW, C.CH
VW, VH = 1920, 1080
GRIS_CAB = (120, 120, 124)          # las cabezas de los compañeros: apagadas
CAJA = (186, 186, 190)
LENTO = 1.12                        # un poco más de aire en los planos con texto

# ---------------------------------------------------------------- el jefe: una caja de cerillas
def jefe(img, cx, suelo, h, st, t):
    d = ImageDraw.Draw(img); g = max(3, int(h*0.01))
    w, hb = h*0.46, h*0.62
    resp = math.sin(t*2*math.pi/3.4)*h*0.004
    y1 = suelo - h*0.18; y0 = y1 - hb + resp
    C.piernas(d, cx, y1 - 2, suelo, h, sep=0.08, fase=st.get("fase"))
    sx, dp = cx + w/2, w*0.2
    lado = [(sx, y0), (sx + dp, y0 - dp*0.5), (sx + dp, y1 - dp*0.5), (sx, y1)]
    d.polygon(lado, fill=(96, 86, 80))
    rnd = random.Random(3)
    for _ in range(int(60*h/600)):                 # la banda de frotar: rugosa
        u, v = rnd.random(), rnd.random()
        px = sx + u*dp; py = y0 - u*dp*0.5 + v*(y1 - y0)
        d.ellipse([px - 2, py - 2, px + 2, py + 2], fill=(60, 54, 50))
    d.polygon(lado, outline=T, width=g)
    tapa = [(cx - w/2, y0), (sx, y0), (sx + dp, y0 - dp*0.5), (cx - w/2 + dp, y0 - dp*0.5)]
    d.polygon(tapa, fill=(150, 150, 154), outline=T, width=g)
    d.rectangle([cx - w/2, y0, sx, y1], fill=CAJA, outline=T, width=g)
    # la etiqueta de la caja: una cerillita dibujada
    ly = y0 + hb*0.8
    d.rounded_rectangle([cx - w*0.28, ly - hb*0.07, cx + w*0.28, ly + hb*0.07], radius=6, fill=(160, 160, 164), outline=T, width=max(2, g - 1))
    d.line([(cx - w*0.15, ly), (cx + w*0.12, ly)], fill=(230, 226, 214), width=max(3, int(h*0.012)))
    d.ellipse([cx + w*0.1, ly - h*0.014, cx + w*0.16, ly + h*0.014], fill=(92, 92, 96))
    # la corbata
    ty = y0 + hb*0.4
    d.polygon([(cx - w*0.06, ty), (cx + w*0.06, ty), (cx + w*0.03, ty + hb*0.06), (cx - w*0.03, ty + hb*0.06)], fill=(52, 52, 58), outline=T)
    d.polygon([(cx - w*0.03, ty + hb*0.06), (cx + w*0.03, ty + hb*0.06), (cx + w*0.07, ty + hb*0.3), (cx, ty + hb*0.36), (cx - w*0.07, ty + hb*0.3)],
              fill=(52, 52, 58), outline=T)
    C.ojos(d, cx, y0 + hb*0.2, w*0.8, CAJA, st.get("cansancio", 0), st.get("parpadeo", 0), st.get("mira", (0, 0)),
           st.get("ceja", -0.0), st.get("dir", 0), st.get("feliz", 0), st.get("sorpresa", 0))
    if st.get("serio", True) and not st.get("feliz") and not st.get("sorpresa"):
        for l in (-1, 1):          # cejas rectas y gruesas: el jefe
            ex = cx + st.get("dir", 0)*w*0.8*0.16 + l*w*0.8*0.32
            d.line([(ex - w*0.11, y0 + hb*0.1), (ex + w*0.11, y0 + hb*0.1)], fill=T, width=max(4, int(h*0.016)))
    hombros = ((cx - w/2, y0 + hb*0.42), (cx + w/2, y0 + hb*0.42))
    pose = st.get("pose", "caido")
    if pose == "aplaude":
        a = abs(math.sin(t*11))
        for l, (hx, hy) in zip((-1, 1), hombros):
            m = (cx + l*(w*0.06 + w*0.12*a), y0 + hb*0.5)
            c = (hx + l*h*0.05, hy + h*0.1)
            d.line([(hx, hy), c, m], fill=T, width=max(4, int(h*0.018)), joint="curve")
            d.ellipse([m[0] - h*0.022, m[1] - h*0.022, m[0] + h*0.022, m[1] + h*0.022], fill=CAJA, outline=T, width=max(2, g - 1))
    else:
        C.brazos(d, hombros, h, pose, st.get("objeto"), piel=CAJA, fase=st.get("fase"))
        if st.get("carpeta"):
            fx, fy = st["objeto"]
            d.rectangle([fx - h*0.05, fy - h*0.07, fx + h*0.05, fy + h*0.05], fill=(220, 220, 224), outline=T, width=g)
    return (cx, y0 - h*0.08)

def companero(img, cx, cadera, suelo, h, st, t):
    s = dict(cabeza=GRIS_CAB, palo=0.33, cansancio=0.7, ceja=0.45, mira=(0, 0.8))
    s.update(st)
    return C.cerilla(img, cx, cadera, suelo, h, s, t)

# ---------------------------------------------------------------- objetos
def mesa2(img, cx, y, h, portatil=True, fondo_mesa=None):
    d = ImageDraw.Draw(img); g = max(3, int(h*0.006))
    w = h*0.82
    if portatil:
        px = cx + h*0.24
        lw, lh = h*0.3, h*0.15
        d.polygon([(px - lw/2, y), (px + lw/2, y), (px + lw*0.45, y - lh), (px - lw*0.45, y - lh)], fill=(70, 72, 78), outline=T)
        d.line([(px - lw/2, y), (px + lw/2, y)], fill=T, width=g + 1)
        d.ellipse([px - h*0.016, y - lh*0.6, px + h*0.016, y - lh*0.6 + h*0.032], fill=(120, 122, 128))
    d.rectangle([cx - w/2, y, cx + w/2, y + h*0.04], fill=(150, 146, 140), outline=T, width=g)
    d.rectangle([cx - w/2 + h*0.015, y + h*0.04, cx + w/2 - h*0.015, CH + 5], fill=(118, 116, 112), outline=T, width=g)

def puesto(img, cx, y, h, quien, st, t, portatil=True):
    """Un puesto de trabajo: silla, alguien sentado y la mesa con su portátil delante."""
    palo = st.get("palo", 1.0 if quien == "cerilla" else 0.33)
    largo = h*0.5*(0.25 + 0.75*palo)
    top = min(y + h*0.115 - largo, y - h*0.26)       # los de palo corto suben la silla: que se les vea
    cad = top + largo
    C.silla(img, cx, top + h*0.1, y + h*0.06, h*0.43)
    fn = C.cerilla if quien == "cerilla" else companero
    s = dict(st, sin_piernas=True, palo=palo, pose=st.get("pose", "mesa"), objeto=st.get("objeto", (0, y)))
    cab, mano = fn(img, cx, cad, CH + 200, h, s, t)
    mesa2(img, cx, y, h, portatil)
    return cab, mano

def papelera(d, cx, base, s, t=0.0):
    """Una papelera llena de cerillas quemadas hasta el final."""
    rnd = random.Random(9)
    for i in range(10):
        ang = rnd.uniform(-0.5, 0.5); l = s*rnd.uniform(0.55, 0.9)
        x0 = cx + rnd.uniform(-s*0.28, s*0.28); y0 = base - s*0.7
        x1, y1 = x0 + math.sin(ang)*l*0.6, y0 - math.cos(ang)*l*0.6
        d.line([(x0, y0 + s*0.2), (x1, y1)], fill=(36, 32, 30), width=max(4, int(s*0.05)))
        d.arc([x1 - s*0.08, y1 - s*0.1, x1 + s*0.08, y1 + s*0.04], 180, 360 + 120*rnd.random(), fill=(20, 20, 20), width=max(4, int(s*0.05)))
    d.polygon([(cx - s*0.42, base - s*0.75), (cx + s*0.42, base - s*0.75), (cx + s*0.32, base), (cx - s*0.32, base)],
              fill=(150, 150, 154), outline=T)
    d.line([(cx - s*0.42, base - s*0.75), (cx + s*0.42, base - s*0.75)], fill=T, width=max(4, int(s*0.03)))
    for k in range(4):
        x = cx - s*0.24 + k*s*0.16
        d.line([(x, base - s*0.65), (x - s*0.02, base - s*0.08)], fill=(128, 128, 132), width=max(2, int(s*0.015)))

def pantalla_grafica(d, x0, y0, x1, y1, k=1.0):
    d.rectangle([x0, y0, x1, y1], fill=(246, 246, 244), outline=T, width=5)
    n = 5; w = (x1 - x0)/(n*1.6)
    for i in range(n):
        hh = (y1 - y0)*0.15*(i + 1)*min(1, k*1.5 - i*0.15) if k > i*0.12 else 0
        bx = x0 + w*0.6 + i*w*1.55
        if hh > 0:
            d.rectangle([bx, y1 - 18 - hh, bx + w, y1 - 18], fill=(80, 80, 86))
    if k >= 0.95:
        d.line([(x0 + w, y1 - 40), (x1 - w*1.5, y0 + 40)], fill=T, width=6)
        d.polygon([(x1 - w*1.5, y0 + 40), (x1 - w*1.5 - 34, y0 + 46), (x1 - w*1.5 - 10, y0 + 74)], fill=T)

def postit(d, cx, cy, s, texto=None):
    d.polygon([(cx - s/2, cy - s/2), (cx + s/2, cy - s/2 + s*0.03), (cx + s/2 - s*0.02, cy + s/2), (cx - s/2 + s*0.02, cy + s/2 - s*0.02)],
              fill=(242, 240, 226), outline=T)
    if texto:
        d.text((cx, cy), texto, font=fuente(s*0.13), fill=(30, 30, 34), anchor="mm")

def cafetera(d, x, suelo, h):
    d.rectangle([x - h*0.14, suelo - h*0.78, x + h*0.14, suelo], fill=(70, 70, 74), outline=T, width=4)
    d.rectangle([x - h*0.1, suelo - h*0.7, x + h*0.1, suelo - h*0.55], fill=(40, 40, 44), outline=T, width=3)
    d.rectangle([x - h*0.08, suelo - h*0.42, x + h*0.08, suelo - h*0.24], fill=(30, 30, 32))
    d.rounded_rectangle([x - h*0.03, suelo - h*0.33, x + h*0.03, suelo - h*0.25], radius=4, fill=(248, 248, 246), outline=T, width=2)

def ceniza(d, x, y, k):
    """Una motita de ceniza que cae: el primer aviso."""
    if 0 < k < 1:
        yy = y + k*160; xx = x + math.sin(k*9)*14
        d.ellipse([xx - 5, yy - 4, xx + 5, yy + 4], fill=(110, 108, 104))

# ---------------------------------------------------------------- planos reutilizables
def bg_ofi(noche=0.0, espejo=False):
    img = M.bg("oficina", claro=0.05, espejo=espejo)
    return M.oscurece(img, noche) if noche else img

def frote(lt, t, prende=0.9, fallo=False, tam=1.0):
    """Primer plano: el jefe arrastra la cabeza de la cerilla por su costado. Chispas y ¡fuu!"""
    img = Image.new("RGB", (CW, CH), (44, 44, 48)); d = ImageDraw.Draw(img)
    banda = [(120, 420), (1520, 330), (1520, 640), (120, 730)]
    d.polygon([(120, 300), (1520, 210), (1520, 330), (120, 420)], fill=CAJA, outline=T)       # la cara de la caja
    d.polygon(banda, fill=(96, 86, 80))
    rnd = random.Random(5)
    for _ in range(420):
        u, v = rnd.random(), rnd.random()
        px = 120 + u*1400; py = 420 - u*90 + v*310
        d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=(62, 56, 52))
    d.polygon(banda, outline=T, width=6)
    intentos = [(0.0, prende, not fallo)] if not fallo else [(0.0, 0.75, False), (0.95, 1.7, True)]
    pos = None; ardiendo = 0.0
    for a, b, prende_aqui in intentos:
        if a <= lt < b:
            k = suave((lt - a)/(b - a))
            pos = (300 + 1000*k, 600 - 70*k)
            M.chispas(d, pos[0] + 40, pos[1], ((lt - a)*5) % 1.0, 150, semilla=int(lt*10))
        elif lt >= b and prende_aqui:
            pos = (1300, 530); ardiendo = suave((lt - b)/0.25)
    if pos is None:
        pos = (1300, 530)
    hx, hy = pos
    hh = 300
    # la mano del jefe sujetando el palo, y el palo
    d.line([(hx - 560, hy + 120), (hx - 20, hy + 6)], fill=T, width=46)
    d.line([(hx - 560, hy + 120), (hx - 20, hy + 6)], fill=(236, 228, 210), width=36)
    d.ellipse([hx - 600, hy + 70, hx - 500, hy + 170], fill=CAJA, outline=T, width=5)
    r = 80
    if ardiendo > 0:
        img = C.luz(img, hx, hy - 120, 420*ardiendo, 0.45*ardiendo, (255, 190, 110)); d = ImageDraw.Draw(img)
        C.llama(d, hx, hy - r*0.95, r*2.6*tam*ardiendo, t)
    d.ellipse([hx - r, hy - r*1.05, hx + r, hy + r], fill=C.ROJO, outline=T, width=6)
    C.ojos(d, hx, hy, r*1.5, C.ROJO, cansancio=1.0 if ardiendo < 0.5 else 0.0, sorpresa=ardiendo, mira=(0.2, -0.2))
    if 0 < ardiendo < 0.3:
        img = M.oscurece(img, 0.4*(1 - ardiendo/0.3), (255, 240, 220))
    sac = math.sin(t*50)*10*max(0, 1 - (lt - prende)/0.4) if lt > prende - 0.2 else 0
    return img, (800 + sac, 450, 1.03)

def jefe_y_cerilla(lt, t, texto=None, st_c=None, st_j=None, x_c=560, x_j=1060, fondo=None, linea_c=None):
    """Plano medio de pie: la cerilla a la izquierda, el jefe a la derecha."""
    img = fondo.copy() if fondo is not None else bg_ofi()
    hj, hc = 760, 600
    cabj = jefe(img, x_j, 860, hj, dict(dict(mira=(-0.6, 0.1), dir=-0.6, parpadeo=parpadeo(lt, 3.3, 1.0)), **(st_j or {})), t)
    sc = dict(dict(mira=(0.6, 0.0), dir=0.6, parpadeo=parpadeo(lt, 3.9)), **(st_c or {}))
    cab, _ = C.cerilla(img, x_c, 860 - 0.2*hc, 860, hc, sc, t)
    if texto:
        C.dice(img, texto[0], cabj[0], cabj[1], texto[1], lt, 44)
    if linea_c:
        C.dice(img, linea_c[0], cab[0], cab[1] - 40, linea_c[1], lt, 44)
    return img, cab, cabj

def jefe_pide(lt, t, texto, palo, llama, humo=False):
    """El jefe se acerca a su mesa con algo que pedir (la cerilla sentada)."""
    img = bg_ofi()
    st = dict(palo=palo, llama=llama, humo=humo, cansancio=0.35 + (1 - palo)*0.8, ceja=(1 - palo)*0.9, mira=(0.7, -0.1), dir=0.6,
              parpadeo=parpadeo(lt, 3.7))
    cab, _ = puesto(img, 640, 720, 680, "cerilla", st, t)
    cabj = jefe(img, 1180, 880, 820, dict(mira=(-0.7, 0.3), dir=-0.7, pose="brindis", objeto=(1000, 560), carpeta=True,
                                         parpadeo=parpadeo(lt, 3.3, 1.0)), t)
    C.dice(img, texto, cabj[0], cabj[1], 0.5, lt, 46)
    return img, (880, 460, 1.04 + 0.01*lt)

def tarjeta_dia(texto):
    return lambda lt, t: M.tarjeta(lt, 1.6, texto, 70)

# ---------------------------------------------------------------- los planos
def p_calle_dia1(lt, t):
    return M.calle(lt, t, "dia", dict(x0=120, v=200, paso=8.0,
                   st=dict(palo=1.0, llama=0.0, cansancio=0.0, pose="anda", dir=0.6, mira=(0.3, 0.1),
                           feliz=1.0 if 2.0 < lt < 4.2 else 0.0)), sol=True)

def p_ofi_llega(lt, t):
    y, h = 760, 520
    img2 = bg_ofi()
    for cx, st in ((330, dict(mira=(-0.7, 0.1) if lt > 2.6 else (0, 0.8), dir=-0.7 if lt > 2.6 else 0, ceja=0.65)),
                   (1270, dict(mira=(-0.6, 0.2) if lt > 3.4 else (0, 0.8), dir=-0.5 if lt > 3.4 else 0, palo=0.4))):
        puesto(img2, cx, y, h, "comp", st, t)
    C.silla(img2, 800, y - h*0.3, y + h*0.06, h*0.43)      # su mesa, vacía todavía
    mesa2(img2, 800, y, h)
    x = -100 + 760*suave(lt/3.2)
    andando = lt < 3.2
    C.cerilla(img2, x, 880 - 0.2*560, 880, 560, dict(palo=1.0, llama=0.0, pose="anda" if andando else "caido",
              fase=lt*8 if andando else None, dir=0.6 if andando else 0.3, mira=(0.4, 0.0), feliz=1.0 if lt > 3.8 else 0.0), t)
    return img2, (800, 450, 1.02)

def p_bienvenida(lt, t):
    img, cab, cabj = jefe_y_cerilla(lt, t, ("Welcome to the team!", 0.5),
                                    st_c=dict(palo=1.0, llama=0.0, feliz=1.0 if lt > 2.2 else 0.0),
                                    st_j=dict(pose="brindis", objeto=(860, 520), feliz=1.0 if 0.4 < lt < 2.6 else 0.0, serio=True))
    return img, (800, 450, 1.03 + 0.01*lt)

def p_jefe_cerca(lt, t):
    img = bg_ofi()
    cabj = jefe(img, 800, 1500, 1500, dict(mira=(-0.3, 0.2), dir=-0.2, parpadeo=parpadeo(lt, 9, 2.4), pose="caido"), t)
    C.dice(img, "We need some fire on this project.", 800, 160, 0.4, lt, 48)
    return img, (800, 450, 1.0 + 0.015*lt)

def p_frote1(lt, t):
    return frote(lt, t, prende=0.9)

def p_encendido(lt, t):
    s = suave(lt/0.3)
    img, cab, cabj = jefe_y_cerilla(lt, t, None,
                                    st_c=dict(palo=1.0, llama=1.0, sorpresa=1.0 if lt < 1.4 else 0.0, feliz=1.0 if lt >= 1.4 else 0.0),
                                    st_j=dict(feliz=1.0 if lt > 1.0 else 0.0))
    img = C.luz(img, cab[0], cab[1] + 40, 260, 0.25, (255, 190, 110))
    img2, cab, cabj = jefe_y_cerilla(lt, t, None,
                                     st_c=dict(palo=1.0, llama=1.0, sorpresa=1.0 if lt < 1.4 else 0.0, feliz=1.0 if lt >= 1.4 else 0.0),
                                     st_j=dict(feliz=1.0 if lt > 1.0 else 0.0), fondo=img)
    return img2, (800, 450, 1.05)

def p_presenta(lt, t):
    img = M.bg("oficina", claro=0.05, espejo=True)
    d = ImageDraw.Draw(img)
    pantalla_grafica(d, 520, 70, 1080, 400, k=min(1, lt/2.4))
    C.cerilla(img, 380, 860 - 0.2*600, 860, 600, dict(palo=0.97, llama=1.0, pose="brindis", objeto=(560, 330), dir=0.7,
              mira=(0.6, -0.3) if lt < 2.6 else (0.6, 0.0), feliz=1.0 if lt > 3.4 else 0.0), t)
    img = C.luz(img, 380, 420, 220, 0.2, (255, 190, 110))
    cabj = jefe(img, 1280, 880, 760, dict(pose="aplaude" if lt > 3.0 else "caido", feliz=1.0 if lt > 3.0 else 0.0, dir=-0.6,
                                         mira=(-0.6, 0)), t)
    C.dice(img, "Great work!", cabj[0], cabj[1], 3.1, lt, 46)
    return img, (820, 450, 1.03)

def p_orgullo(lt, t):
    img = C.recorte(bg_ofi(), 700, 330, 1.8)
    st = dict(palo=0.95, llama=1.0, feliz=1.0, pose="caido", sin_piernas=True)
    cab, _ = C.cerilla(img, 800, 1250, 2000, 1100, st, t)
    img = C.luz(img, 800, 260, 300, 0.25, (255, 190, 110))
    cab, _ = C.cerilla(img, 800, 1250, 2000, 1100, st, t)
    ceniza(ImageDraw.Draw(img), 880, cab[1] + 120, (lt - 1.2)/1.6)
    return img, (800, 450, 1.0 + 0.01*lt)

def p_comida(lt, t):
    img = M.bg("cocina", claro=0.05)
    d = ImageDraw.Draw(img)
    # la mesita del comedor, delante
    y, h = 700, 560
    cabezas = {}
    for cx, quien, st in ((420, "comp", dict(palo=0.33, mira=(0.6, 0.2) if lt > 2.6 else (0, 0.9), dir=0.5 if lt > 2.6 else 0)),
                          (800, "cerilla", dict(palo=0.95, llama=0.8, mira=(-0.6, 0), dir=-0.6, feliz=0.0)),
                          (1180, "comp", dict(palo=0.38, mira=(0, 0.9)))):
        largo = h*0.5*(0.25 + 0.75*st["palo"])
        top = min(y + h*0.115 - largo, y - h*0.26)
        C.silla(img, cx, top + h*0.1, y + h*0.06, h*0.43)
        fn = C.cerilla if quien == "cerilla" else companero
        cab, _ = fn(img, cx, top + largo, CH + 200, h, dict(st, sin_piernas=True, pose="mesa", objeto=(0, y)), t)
        cabezas[cx] = cab
    d = ImageDraw.Draw(img)
    d.rectangle([180, y, 1420, y + 26], fill=(160, 156, 150), outline=T, width=4)
    d.rectangle([200, y + 26, 1400, CH + 5], fill=(128, 126, 122), outline=T, width=4)
    for cx in (420, 800, 1180):          # los táper
        d.rounded_rectangle([cx - 60, y - 34, cx + 60, y + 2], radius=8, fill=(230, 230, 228), outline=T, width=3)
    if lt < 3.3:
        C.dice(img, "So... how long have you been here?", 800, cabezas[800][1] - 40, 0.5, lt, 40)
    C.dice(img, "Too long.", 420, cabezas[420][1] - 30, 3.4, lt, 46)
    return img, (800, 460, 1.03)

def p_noche_ofi(lt, t, hora="9:40 PM", palo=0.85, llama=0.85):
    img = bg_ofi(noche=0.72)
    st = dict(palo=palo, llama=llama, cansancio=0.55, ceja=0.4, mira=(0, 0.6), parpadeo=parpadeo(lt, 3.1))
    tmp = img.copy(); cab, _ = puesto(tmp, 800, 720, 680, "cerilla", st, t)
    img = C.luz(img, cab[0], cab[1] + 80, 330, 0.3, (255, 180, 100))
    puesto(img, 800, 720, 680, "cerilla", st, t)
    C.reloj_tarjeta(img, hora, 1300, 160, 0, t)
    return img, (800, 460, 1.06 + 0.01*lt)

def p_llamada(lt, t):
    img = M.oscurece(C.recorte(M.bg("dormitorio", claro=0.1), 1000, 250, 2.2).filter(ImageFilter.GaussianBlur(8)), 0.3)
    coge = lt > 2.4
    def ui(pant):
        W, H = pant.size; p = ImageDraw.Draw(pant)
        p.rectangle([0, 0, W, H], fill=(30, 30, 34))
        p.text((W/2, H*0.25), "BOSS", font=fuente(W*0.16), fill=(250, 250, 250), anchor="mm")
        p.text((W/2, H*0.34), "calling..." if not coge else "00:0" + str(int(lt - 2.4)), font=fuente(W*0.07), fill=(170, 170, 176), anchor="mm")
        if not coge:
            for x, col in ((W*0.28, (210, 70, 60)), (W*0.72, (230, 230, 230))):
                p.ellipse([x - W*0.1, H*0.78 - W*0.1, x + W*0.1, H*0.78 + W*0.1], fill=col)
    pulgar = None
    k = (lt - 1.8)/0.6
    if 0 <= k <= 1.2:
        pulgar = (800 + 98*suave(min(1, k)), 470 + 780*0.28 + 120*(1 - suave(min(1, k))))
    M.movil_grande(img, 800, 470, 780, "negro", lt, fondo_pantalla=ui, pulgar=pulgar)
    C.reloj_tarjeta(img, "7:00 AM", 1300, 140, 0, t)
    return img, (800, 460, 1.0)

def p_cama_llamada(lt, t):
    st = dict(palo=0.8, llama=0.3, humo=True, cansancio=0.85, ceja=0.6, mira=(0.3, 0.6), pose="movil")
    img, cam = M.cama_ancha(lt, t, st, None, clave="manana", luz=0.0, texto=("On my way.", 1.0))
    return img, (560, 430, 1.25)

def p_finde(lt, t):
    return p_noche_ofi(lt, t, "SAT 11:20 PM", 0.72, 0.65)

def p_chat_cancela(lt, t):
    img = M.fondo_chat(); img = C.luz(img, 800, 450, 420, 0.35)
    datos = [(-1, "Dinner tonight?", 0.5, 0), (1, "Can't. Work.", 2.9, 1.2), (-1, "Again?", 4.2, 0)]
    pulgar = (820 + 40*math.sin(lt*14), 790) if 1.7 <= lt < 2.9 else None
    M.movil_grande(img, 800, 470, 780, "chat", lt, datos, pulgar)
    return img, (800, 460, 1.0 + 0.015*lt)

def p_robo(lt, t):
    img = M.bg("oficina", claro=0.05, espejo=True)
    d = ImageDraw.Draw(img)
    pantalla_grafica(d, 520, 70, 1080, 400, k=1.0)
    cabj = jefe(img, 800, 880, 780, dict(pose="brindis", objeto=(640, 330), dir=-0.3, feliz=1.0 if lt > 0.6 else 0.0), t)
    C.dice(img, "Here's MY idea.", cabj[0], cabj[1], 0.6, lt, 46)
    for cx in (230, 1400):                 # los compañeros aplauden sin ganas
        companero(img, cx, 900 - 0.2*480, 900, 480, dict(palo=0.35, pose="caido"), t)
    C.cerilla(img, 1180, 900 - 0.2*520, 900, 520, dict(palo=0.68, llama=0.35, sorpresa=1.0 if 1.6 < lt < 3.4 else 0.0,
              cansancio=0.0 if lt < 3.4 else 0.6, ceja=0.0 if lt < 3.4 else 0.7, dir=-0.7, mira=(-0.8, -0.2)), t)
    return img, (800, 450, 1.03)

def p_frote_falla(lt, t):
    return frote(lt, t, fallo=True, tam=0.55)

def p_insomnio(lt, t):
    st = dict(palo=0.62, llama=0.15, humo=True, cansancio=0.3, ceja=0.6, mira=(0, -0.9), pose="caido",
              parpadeo=parpadeo(lt, 9, 3.6))
    return M.cama_ancha(lt, t, st, "3:12 AM", clave="noche", luz=0.0)

def p_cafe(lt, t):
    img = bg_ofi()
    d = ImageDraw.Draw(img)
    cafetera(d, 260, 860, 700)
    companero(img, 560, 860 - 0.2*560, 860, 560, dict(palo=0.25, dir=0.6, mira=(0.7, 0.0), pose="taza" if False else "caido"), t)
    cab, _ = C.cerilla(img, 1000, 860 - 0.2*600, 860, 600, dict(palo=0.58, llama=0.3, humo=True, cansancio=0.5, ceja=0.5,
                        dir=-0.6, mira=(-0.7, 0.0), sorpresa=0.7 if lt > 3.6 else 0.0), t)
    C.dice(img, "I was like you.", 560, 400, 1.0, lt, 46)
    return img, (760, 460, 1.04)

def p_se_va(lt, t):
    img = bg_ofi()
    d = ImageDraw.Draw(img)
    papelera(d, 300, 860, 150)
    # la cerilla, en su mesa, mirando cómo se va
    cab, _ = puesto(img, 1150, 740, 560, "cerilla", dict(palo=0.55, llama=0.3, humo=True, cansancio=0.4, ceja=0.6,
                    dir=-0.8, mira=(-0.8, 0.2)), t)
    if lt < 1.6:            # recoge sus cosas
        x = 760; fase = None
    else:
        x = 760 - 520*((lt - 1.6)/3.4); fase = (lt - 1.6)*6
    st = dict(palo=0.18, pose="caja", fase=fase, dir=-0.7, mira=(-0.6, 0.3), cansancio=0.8)
    cabc, _ = companero(img, x, 880 - 0.2*560, 880, 560, st, t)
    d = ImageDraw.Draw(img)
    by = 880 - 0.2*560 - 560*0.5*(0.25 + 0.75*0.18) + 560*0.32
    d.rectangle([x - 70, by - 50, x + 70, by + 40], fill=(176, 160, 132), outline=T, width=4)       # la caja de cartón
    d.line([(x - 70, by - 20), (x + 70, by - 20)], fill=(150, 134, 108), width=3)
    return img, (760, 460, 1.02)

def p_papelera(lt, t):
    img = C.recorte(bg_ofi(), 500, 560, 1.5)
    k = suave((lt - 0.8)/1.2)
    C.cerilla(img, 560, 900 - 0.2*900, 900, 900, dict(palo=0.55, llama=0.3, humo=True, cansancio=0.3 + 0.3*k, ceja=0.8*k,
              dir=0.7, mira=(0.7, 0.4 + 0.6*k), inclina=0.04*k, pose="caido"), t)
    papelera(ImageDraw.Draw(img), 1080, 900, 480)
    return img, (820, 470, 1.0 + 0.02*lt)

def p_espejo(lt, t):
    img = C.recorte(M.bg("bano", claro=0.05), 430, 420, 1.15)
    k = suave((lt - 1.4)/0.6)
    st = dict(palo=0.5, llama=0.25, humo=True, cansancio=0.4*(1 - k), sorpresa=k, mira=(0, 0.2 + 0.8*suave((lt - 0.6)/0.8)),
              ceja=0.0, pose="caido", parpadeo=parpadeo(lt, 9, 4.2))
    C.cerilla(img, 800, 860 - 0.2*640, 860, 640, st, t)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([450, 850, 1150, 960], radius=30, fill=(236, 236, 238), outline=T, width=5)
    return img, (800, 450, 1.0 + 0.01*lt)

def p_jefe_viene(lt, t):
    img = bg_ofi()
    st = dict(palo=0.5, llama=0.25, humo=True, cansancio=0.5, ceja=0.6, mira=(0.7, -0.1), dir=0.6)
    cab, _ = puesto(img, 640, 720, 680, "cerilla", st, t)
    xj = 1500 - 320*suave(lt/1.6)
    cabj = jefe(img, xj, 880, 820, dict(fase=lt*6 if lt < 1.6 else None, mira=(-0.7, 0.3), dir=-0.7,
                                       pose="brindis", objeto=(xj - 230, 500 - 40*suave((lt - 2.6)/0.8)), carpeta=lt < 2.6), t)
    C.dice(img, "One more thing tonight?", cabj[0], cabj[1], 1.0, lt, 46)
    return img, (900, 460, 1.04)

def p_duda(lt, t):
    img = C.recorte(bg_ofi(), 640, 330, 1.9)
    d_ = -1 if 0.8 < lt < 1.9 else (1 if 1.9 <= lt < 2.9 else 0)
    st = dict(palo=0.5, llama=0.25, humo=True, cansancio=0.3, ceja=0.5, dir=d_*0.9, mira=(d_*0.8, 0.0), pose="caido", sin_piernas=True)
    C.cerilla(img, 800, 830, 2000, 1100, st, t)
    return img, (800, 450, 1.0 + 0.012*lt)

def p_reloj6(lt, t):
    img = C.recorte(bg_ofi(), 1265, 170, 3.2)
    d = ImageDraw.Draw(img)
    cx, cy, r = 800, 450, 330           # el reloj de la pared, en grande: las 6 en punto
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(248, 248, 246), outline=T, width=12)
    for i in range(12):
        a = i*math.pi/6
        d.line([(cx + math.sin(a)*r*0.82, cy - math.cos(a)*r*0.82), (cx + math.sin(a)*r*0.92, cy - math.cos(a)*r*0.92)], fill=T, width=8)
    d.line([(cx, cy), (cx, cy - r*0.72)], fill=T, width=12)
    d.line([(cx, cy), (cx, cy + r*0.5)], fill=T, width=16)
    return img, (800, 450, 1.0)

def p_papelera_flash(lt, t):
    img = C.recorte(bg_ofi(), 300, 700, 2.6)
    papelera(ImageDraw.Draw(img), 800, 980, 640)
    return img, (800, 450, 1.0)

def p_no(lt, t):
    img = bg_ofi()
    st = dict(palo=0.5, llama=0.3 + 0.1*suave((lt - 0.8)/0.6), cansancio=0.0, ceja=-0.0, mira=(0.7, -0.2), dir=0.7,
              pose="para", objeto=(900, 470))
    cab, _ = puesto(img, 640, 720, 680, "cerilla", st, t)
    cabj = jefe(img, 1180, 880, 820, dict(mira=(-0.7, 0.3), dir=-0.7, pose="brindis", objeto=(930, 480),
                                         sorpresa=suave((lt - 1.0)/0.3)), t)
    C.dice(img, "No.", cab[0] + 30, cab[1] - 30, 0.8, lt, 60)
    return img, (840, 460, 1.04 + 0.01*lt)

def p_pasmados(lt, t):
    img = bg_ofi()
    y, h = 760, 520
    for cx, st in ((330, dict(dir=0.7, mira=(0.8, -0.2), sorpresa=suave((lt - 0.6)/0.3), cansancio=0.0, ceja=0.0)),
                   (1270, dict(dir=-0.7, mira=(-0.8, -0.2), sorpresa=suave((lt - 1.0)/0.3), cansancio=0.0, ceja=0.0, palo=0.4))):
        puesto(img, cx, y, h, "comp", st, t)
    cabj = jefe(img, 800, 900, 640, dict(sorpresa=1.0, mira=(0, 0.2), pose="caido"), t)
    return img, (800, 450, 1.02)

def p_atardecer(lt, t):
    return M.calle(lt, t, "tarde", dict(x0=150, v=170, paso=6.5,
                   st=dict(palo=0.5, llama=0.3, cansancio=0.2, pose="anda", dir=0.6, mira=(0.3, -0.3) if lt > 3 else (0.3, 0.2))),
                   extras=[("gorro", 1700, -150, 0.3, 450, 785)])

def p_chat_cena(lt, t):
    img = M.fondo_chat(); img = C.luz(img, 800, 450, 420, 0.35)
    datos = [(-1, "Dinner tonight?", -1, 0), (1, "Can't. Work.", -1, 0), (-1, "Again?", -1, 0),
             (1, "Dinner tonight?", 2.0, 1.2), (-1, "FINALLY.", 3.4, 0)]
    pulgar = (820 + 40*math.sin(lt*14), 790) if 0.8 <= lt < 2.0 else None
    M.movil_grande(img, 800, 470, 780, "chat", lt, datos, pulgar)
    return img, (800, 460, 1.0 + 0.015*lt)

def p_bar(lt, t):
    img = M.bg("fiesta", claro=0.0)
    img = C.luz(img, 640, 420, 260, 0.2, (255, 170, 90))
    brinda = suave((lt - 2.6)/0.5); centro = (820, 400)
    def copa(x, y): return (x + (centro[0] - x)*0.35*brinda, y + (centro[1] - y)*0.35*brinda)
    M.extra(img, 330, 850, 520, "gorro", dict(pose="brindis", objeto=copa(440, 420), feliz=1.0, dir=0.6), t)
    C.nube(img, 1040, 850, 560, dict(feliz=1.0, dir=-0.5, pose="brindis", objeto=copa(930, 440), vaso=True), t)
    M.vaso(ImageDraw.Draw(img), *copa(930, 440), 560)
    M.extra(img, 1290, 850, 540, "capsula", dict(pose="brindis", objeto=copa(1180, 430), feliz=1.0, dir=-0.6), t)
    C.cerilla(img, 640, 850 - 0.2*600, 850, 600, dict(palo=0.5, llama=0.45, feliz=1.0 if lt > 0.8 else 0.0, pose="brindis",
              objeto=copa(740, 430), dir=0.3), t)
    M.vaso(ImageDraw.Draw(img), *copa(740, 430), 600)
    return img, (800, 470, 1.04 + 0.012*lt)

def p_parque(lt, t):
    img = M.bg("parque", claro=0.0)
    img = C.luz(img, 1200, 150, 420, 0.3, (255, 235, 210))
    x = 250 + 150*lt
    C.nube(img, x + 230, 830, 560, dict(fase=lt*6.5, dir=-0.5, feliz=1.0 if 1.5 < lt < 3.5 else 0.0, pose="anda"), t)
    C.cerilla(img, x, 830 - 0.2*560, 830, 560, dict(palo=0.5, llama=0.45, fase=lt*6.5 + 1.2, pose="anda", dir=0.6,
              mira=(0.7, 0.0), feliz=1.0 if 2.0 < lt < 3.8 else 0.0), t)
    return img, (min(max(x + 100, 700), 900), 460, 1.08)

def p_lee(lt, t):
    st = dict(palo=0.5, llama=0.4, cansancio=0.2 + 0.8*suave((lt - 2.4)/1.6), mira=(0.3, 0.9), pose="movil")
    img = C.cuarto("noche")
    k, ox, oy = 0.95, 60, 150
    img = C.luz(img, ox + 400*k, oy + 420*k, 220, 0.25, (255, 200, 140))
    cab, mano = C.cama(img, k, ox, oy, st, t)
    d = ImageDraw.Draw(img)
    mx, my = mano          # un libro en vez del móvil
    d.polygon([(mx - 52, my - 34), (mx, my - 24), (mx + 52, my - 34), (mx + 52, my + 14), (mx, my + 22), (mx - 52, my + 14)],
              fill=(240, 238, 230), outline=T)
    d.line([(mx, my - 24), (mx, my + 22)], fill=T, width=3)
    if lt > 3.0:
        img = M.oscurece(img, 0.6*suave((lt - 3.0)/1.0))
    return img, (560, 430, 1.25)

def p_nueva(lt, t):
    img = bg_ofi()
    st_n = dict(palo=1.0, llama=suave((lt - 1.4)/0.25), sorpresa=1.0 if 1.4 < lt < 2.6 else 0.0, feliz=1.0 if lt >= 2.6 else 0.0,
                dir=0.5, mira=(0.6, -0.1))
    cab, _ = puesto(img, 620, 720, 640, "cerilla", st_n, t)
    if st_n["llama"] > 0:
        img = C.luz(img, cab[0], cab[1] + 60, 260, 0.2*st_n["llama"], (255, 190, 110))
        cab, _ = puesto(img, 620, 720, 640, "cerilla", st_n, t)
    d = ImageDraw.Draw(img)
    if 0.6 < lt < 1.5:
        M.chispas(d, cab[0] + 30, cab[1] + 40, ((lt - 0.6)*4) % 1.0, 140, semilla=int(lt*10))
    xj = 1140 + (0 if lt < 3.2 else 500*((lt - 3.2)/1.8))
    jefe(img, xj, 880, 800, dict(pose="brindis" if lt < 1.6 else "caido", objeto=(cab[0] + 80, cab[1] + 60), dir=-0.6 if lt < 3.2 else 0.6,
                                 mira=(-0.7, 0.2), fase=(lt - 3.2)*6 if lt > 3.2 else None, feliz=1.0 if 1.6 < lt < 3.2 else 0.0), t)
    return img, (860, 460, 1.04)

def p_deja_postit(lt, t):
    img = bg_ofi()
    st_n = dict(palo=1.0, llama=0.9, feliz=0.0, cansancio=0.0, dir=0.6 if lt > 1.6 else 0.0, mira=(0.6, 0.0) if lt > 1.6 else (0, 0.6))
    cab, _ = puesto(img, 620, 720, 640, "cerilla", st_n, t)
    d = ImageDraw.Draw(img)
    pega = lt > 2.6
    if pega:
        postit(d, 620, 660, 70)
    if lt < 2.2:
        x = 1500 - 560*suave(lt/2.2); fase = lt*6.5; dir_ = -0.7
    elif lt < 3.0:
        x = 940; fase = None; dir_ = -0.6
    else:
        x = 940 + 700*((lt - 3.0)/2.0); fase = (lt - 3.0)*6.5; dir_ = 0.7
    pose = "brindis" if 2.0 < lt < 2.8 else ("anda" if fase is not None else "caido")
    C.cerilla(img, x, 880 - 0.2*600, 880, 600, dict(palo=0.5, llama=0.45, pose=pose, objeto=(700, 640), fase=fase, dir=dir_,
              mira=(dir_, 0.3), feliz=1.0 if lt > 3.4 else 0.0), t)
    if 2.0 < lt <= 2.6:
        k = suave((lt - 2.0)/0.6)
        postit(ImageDraw.Draw(img), 760 - 140*k, 640 + 20*k, 70)
    return img, (840, 460, 1.03)

def p_postit_cerca(lt, t):
    img = C.recorte(bg_ofi(), 620, 640, 3.2)
    d = ImageDraw.Draw(img)
    d.polygon([(300, 900), (1300, 900), (1220, 160), (380, 160)], fill=(70, 72, 78), outline=T)    # la tapa del portátil
    d.ellipse([760, 380, 840, 460], fill=(120, 122, 128))
    postit(d, 800, 560, 420, "Leave at 6.")
    return img, (800, 480, 1.0 + 0.02*lt)

def p_final(lt, t, dur=8.0):
    img = Image.new("RGB", (CW, CH), (8, 8, 10)); d = ImageDraw.Draw(img)
    for t0, txt, y, px in ((0.5, "You only get one stick.", 380, 66), (1.8, "Don't let anyone burn it for you.", 470, 60)):
        a = suave((lt - t0)/0.7)*suave((dur - lt)/0.8); c = int(8 + 242*a)
        d.text((CW/2, y), txt, font=fuente(px), fill=(c, c, c), anchor="mm")
    a = suave((lt - 3.6)/0.8)*suave((dur - lt)/0.8)
    if a > 0:
        c = int(8 + 150*a)
        d.text((CW/2 + 25, 690), "STILL BURNING", font=fuente(34), fill=(c, c, c), anchor="mm")
        x = CW/2 - 175
        d.rounded_rectangle([x - 5, 670, x + 5, 720], radius=4, fill=tuple(int(8 + (v - 8)*a) for v in (225, 218, 200)))
        d.ellipse([x - 12, 652, x + 12, 678], fill=tuple(int(8 + (v - 8)*a) for v in C.ROJO))
        if a > 0.6: C.llama(d, x, 655, 30*a, t)
    return img, (CW/2, CH/2, 1.0)

# ---------------------------------------------------------------- el montaje
L = LENTO
GUION = [
    (tarjeta_dia("DAY 1"), 2.0, [(0.2, "tic")]),
    (p_calle_dia1, 6.0, []),
    (p_ofi_llega, 6.5, []),
    (p_bienvenida, 4.5*L, []),
    (p_jefe_cerca, 4.0*L, []),
    (p_frote1, 2.4, [(0.0, "frote0.9"), (0.9, "fuu")]),
    (p_encendido, 3.5, []),
    (p_presenta, 6.0, [(3.0, "aplauso")]),
    (p_orgullo, 3.0, []),
    (p_comida, 6.5*L, []),
    (tarjeta_dia("DAY 12"), 1.6, [(0.2, "tic")]),
    (lambda lt, t: jefe_pide(lt, t, "Can you stay late?", 0.95, 0.0), 4.0*L, []),
    (lambda lt, t: frote(lt, t, prende=0.8, tam=0.9), 1.8, [(0.0, "frote0.8"), (0.8, "fuu")]),
    (p_noche_ofi, 4.5, []),
    (tarjeta_dia("DAY 20"), 1.6, [(0.2, "tic")]),
    (p_llamada, 4.0, [(0.0, "tono2.4"), (2.4, "tap")]),
    (p_cama_llamada, 3.5*L, []),
    (tarjeta_dia("DAY 31"), 1.6, [(0.2, "tic")]),
    (lambda lt, t: jefe_pide(lt, t, "Just this weekend.", 0.78, 0.2, True), 3.5*L, []),
    (lambda lt, t: frote(lt, t, prende=0.8, tam=0.8), 1.6, [(0.0, "frote0.8"), (0.8, "fuu")]),
    (p_finde, 4.0, []),
    (p_chat_cancela, 6.0, [(0.5, "ding"), (2.9, "envia"), (4.2, "ding")]),
    (tarjeta_dia("DAY 40"), 1.6, [(0.2, "tic")]),
    (p_robo, 6.0*L, [(0.8, "aplauso")]),
    (tarjeta_dia("DAY 58"), 1.6, [(0.2, "tic")]),
    (lambda lt, t: jefe_pide(lt, t, "Quick favour?", 0.66, 0.15, True), 3.5*L, []),
    (p_frote_falla, 3.0, [(0.0, "frote0.75"), (0.95, "frote0.75"), (1.7, "fuu")]),
    (p_insomnio, 5.0, []),
    (p_cafe, 6.0*L, []),
    (tarjeta_dia("DAY 74"), 1.6, [(0.2, "tic")]),
    (p_se_va, 7.0, []),
    (p_papelera, 5.0, []),
    (p_espejo, 5.0, []),
    (tarjeta_dia("DAY 89"), 1.6, [(0.2, "tic")]),
    (p_jefe_viene, 4.5*L, []),
    (p_duda, 3.5, [(0.8, "tic"), (1.9, "tic")]),
    (p_reloj6, 1.8, [(0.0, "tic")]),
    (p_papelera_flash, 1.5, []),
    (p_no, 4.5*L, []),
    (p_pasmados, 4.0, []),
    (p_atardecer, 6.0, []),
    (p_chat_cena, 5.0, [(2.0, "envia"), (3.4, "ding")]),
    (p_bar, 6.0, [(3.1, "clink")]),
    (p_parque, 4.5, []),
    (p_lee, 4.5, []),
    (tarjeta_dia("DAY 90"), 1.6, [(0.2, "tic")]),
    (p_nueva, 5.0, [(0.6, "frote0.8"), (1.4, "fuu")]),
    (p_deja_postit, 5.0, []),
    (p_postit_cerca, 3.0*L, []),
    (lambda lt, t: p_final(lt, t, 8.0), 8.0, []),
    (M.negro, 2.0, []),
]

def tabla():
    t = 0.0; out = []
    for fn, dur, sfx in GUION:
        out.append((t, t + dur, fn, sfx)); t += dur
    return out, t

TABLA, DUR = tabla()
_I = {fn: a for a, b, fn, s in TABLA}
ACTO2 = TABLA[10][0]            # DAY 12
CAIDA = TABLA[22][0]            # DAY 40
CLIMAX = _I[p_no]
ACTO3 = _I[p_atardecer]
FINAL = DUR - 10.0

def fotograma(t):
    for a, b, fn, _ in TABLA:
        if a <= t < b:
            img, (cx, cy, z) = fn(t - a, t)
            break
    else:
        img, (cx, cy, z) = M.negro(0)
    img = C.recorte(img, cx, cy, z) if z > 1.001 or abs(cx - CW/2) > 1 else img
    img = img.resize((VW, VH), Image.LANCZOS)
    if t < 0.5:
        img = M.oscurece(img, 1 - t/0.5)
    return M.vineta(img)

# ---------------------------------------------------------------- sonido
SR = 44100
def musica():
    n = int(DUR*SR); t = np.arange(n)/SR; out = np.zeros(n)
    nota = M.nota
    secciones = [
        (0, ACTO2, [[48, 55, 60, 64], [53, 57, 60, 65], [55, 59, 62, 67], [48, 55, 60, 64]], 2.0, 0.06, 24),       # ilusión
        (ACTO2, CAIDA, [[57, 60, 64, 67], [53, 57, 60, 64], [48, 55, 60, 64], [55, 59, 62, 64]], 2.5, 0.05, 12),  # rutina
        (CAIDA, CLIMAX, [[57, 60, 64], [50, 53, 57, 60], [52, 55, 59], [57, 60, 64]], 3.2, 0.035, 12),             # se apaga
        (CLIMAX, ACTO3, [[45, 52, 57]], 6.0, 0.0, 12),                                                              # silencio tenso
        (ACTO3, FINAL, [[48, 55, 60, 64], [55, 59, 62, 67], [57, 60, 64, 69], [53, 57, 60, 65]], 2.5, 0.05, 12),  # calma
        (FINAL, DUR, [[48, 55, 60, 64], [53, 57, 60, 65]], 3.0, 0.035, 12),
    ]
    for a, b, acordes, dur, vp, octava in secciones:
        i = 0; t0 = a
        while t0 < b:
            ac = acordes[i % len(acordes)]
            s0, s1 = int(t0*SR), min(n, int((min(b, t0 + dur) + 0.8)*SR))
            tt = t[s0:s1] - t0; fin = min(b, t0 + dur) - t0
            env = np.minimum(1, tt/0.9)*np.exp(-np.maximum(0, tt - fin)*5)
            vol = 0.045 if vp else 0.03
            for m in ac:
                f = nota(m); out[s0:s1] += vol*env*(np.sin(2*np.pi*f*tt) + 0.25*np.sin(2*np.pi*2*f*tt + 0.4))
            out[s0:s1] += 0.06*env*np.sin(2*np.pi*nota(ac[0] - 12)*tt)
            if vp:
                paso = dur/4
                for k, m in enumerate([ac[0], ac[-2], ac[1], ac[-1]]):
                    pa = t0 + k*paso
                    if pa >= b: break
                    a0 = int(pa*SR); a1 = min(n, a0 + int(1.8*SR)); ta = t[a0:a1] - pa; f = nota(m + octava)
                    out[a0:a1] += vp*np.exp(-ta*2.4)*(np.sin(2*np.pi*f*ta) + 0.2*np.sin(2*np.pi*3*f*ta))
            t0 += dur; i += 1
    ir_n = int(1.8*SR)
    ir = np.random.default_rng(2).standard_normal(ir_n)*np.exp(-np.arange(ir_n)/SR*3.2); ir[0] = 1.0; ir /= np.sqrt(np.sum(ir**2))
    Ln = n + ir_n
    wet = np.fft.irfft(np.fft.rfft(out, Ln)*np.fft.rfft(ir, Ln), Ln)[:n]
    out = 0.65*out + 0.35*wet/np.max(np.abs(wet))*np.max(np.abs(out))
    return out + 0.003*np.random.default_rng(1).standard_normal(n)

def efectos():
    n = int(DUR*SR); out = np.zeros(n); rnd = np.random.default_rng(5)
    def pon(t0, *xs):
        for x in xs:
            s0 = int(t0*SR); s1 = min(n, s0 + len(x))
            if s0 < n: out[s0:s1] += x[:s1 - s0]
    def tono(f, d, vol, at=0.005, ca=8.0):
        tt = np.arange(int(d*SR))/SR
        return vol*np.sin(2*np.pi*f*tt)*np.minimum(1, tt/at)*np.exp(-tt*ca)
    def ruido(d, vol, suav=20):
        return vol*np.convolve(rnd.standard_normal(int(d*SR)), np.ones(suav)/suav, mode="same")
    for a, b, fn, sfx in TABLA:
        for t0, tipo in sfx:
            T0 = a + t0
            if tipo.startswith("frote"):          # el raspado contra la caja
                d = float(tipo[5:]); x = ruido(d, 0.22, 3)
                x *= (0.5 + 0.5*np.abs(np.sin(np.arange(len(x))/SR*2*np.pi*23)))*np.minimum(1, np.arange(len(x))/(0.05*SR))
                pon(T0, x)
            elif tipo == "fuu":                   # se enciende
                x = ruido(0.8, 0.35, 60); env = np.minimum(1, np.arange(len(x))/(0.04*SR))*np.exp(-np.arange(len(x))/SR*4)
                pon(T0, x*env)
            elif tipo.startswith("tono"):         # el móvil sonando
                d = float(tipo[4:]); k = 0.0
                while k < d:
                    pon(T0 + k, tono(880, 0.35, 0.06, 0.01, 2) + 0, tono(1320, 0.35, 0.04, 0.01, 2)); k += 0.9
            elif tipo == "aplauso":
                for _ in range(70):
                    pon(T0 + rnd.uniform(0, 2.0), ruido(0.03, 0.12, 2)*np.exp(-np.arange(int(0.03*SR))/SR*90))
            elif tipo == "tap":
                pon(T0, ruido(0.03, 0.25, 3), tono(1200, 0.04, 0.05, 0.001, 60))
            elif tipo == "ding":
                pon(T0, tono(1318, 0.6, 0.08, 0.002, 5), tono(1976, 0.5, 0.04, 0.002, 6))
            elif tipo == "envia":
                tt = np.arange(int(0.18*SR))/SR; pon(T0, 0.06*np.sin(2*np.pi*(700 + 2600*tt)*tt)*np.exp(-tt*10))
            elif tipo == "tic":
                pon(T0, tono(880, 0.25, 0.05, 0.002, 12))
            elif tipo == "clink":
                pon(T0, tono(2637, 0.9, 0.06, 0.001, 4), tono(3520, 0.7, 0.04, 0.001, 5))
    return out

def audio(ruta):
    mus = musica(); fx = efectos()
    mix = mus/np.max(np.abs(mus))*0.42 + fx
    fo = int(2.5*SR); mix[-fo:] *= np.linspace(1, 0, fo)
    pcm = (np.clip(mix, -0.98, 0.98)*32767).astype(np.int16)
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

def main():
    Path(OUT).mkdir(exist_ok=True)
    args = sys.argv[1:]
    if args and args[0] == "fotos":
        for i, (a, b, fn, _) in enumerate(TABLA):
            fotograma((a + b)/2).resize((960, 540)).save(OUT + f"bo_{i:02d}.jpg", quality=85)
        print(f"{len(TABLA)} planos, {DUR:.1f} s"); return
    if args and args[0] == "en":
        for s in args[1:]:
            fotograma(float(s)).resize((960, 540)).save(OUT + f"bo_en_{float(s):06.2f}.jpg", quality=85)
        return
    audio(OUT + "burnout_audio.wav")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}", "-r", str(FPS),
                          "-i", "-", "-i", OUT + "burnout_audio.wav", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19",
                          "-preset", "medium", "-c:a", "aac", "-b:a", "192k", "-shortest", OUT + "BURNOUT.mp4"], stdin=subprocess.PIPE)
    for i in range(int(DUR*FPS)):
        p.stdin.write(fotograma(i/FPS).tobytes())
    p.stdin.close(); p.wait()
    print(f"hecho: {DUR:.1f} s")

if __name__ == "__main__":
    main()
