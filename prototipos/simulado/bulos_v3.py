"""LO HE SIMULADO #2, version 3: el video de los bulos con su voz, pensado para
que la gente no se vaya en el primer medio minuto.

Lo que dijeron los datos del de los atascos: mas de la mitad se iba en los
primeros 30-40 s, y quien pasaba del minuto se quedaba hasta el final. Asi que:
  - se empieza con el gancho (el movil, «reenviar», la ciudad en rojo, BULO);
  - justo despues, el AVANCE del resultado: «con solo un 70 % mas de reenvios,
    llega a mas de diez veces mas gente» (su propia frase, sacada de la escena
    del resultado), con la grafica. Asi se sabe desde el segundo 10 que hay algo
    que descubrir;
  - sin pantalla de titulo: la pregunta se hace con la red ya en marcha.
Todo lo demas como la v2: sincronia con las pausas reales de la voz, camara
que sigue al bulo, capitulos, escenas nuevas, sonido propio y pantalla final.

    python3 bulos_v3.py salida.mp4 --audio X.mp3 --duraciones X.json
                        [--escenas 0,1] [--fotos hoja.png] [--procesos 4]
"""
import argparse
import json
import math
import multiprocessing as mp
import re
import subprocess
import sys
import tempfile
import unicodedata
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sonido as SN  # noqa: E402
from alinea import tiempos as alinear  # noqa: E402
from bulos import Cascada, Red  # noqa: E402
import bulos_video as V1  # noqa: E402  (textos y datos medidos)

W, H, FPS = 1920, 1080, 30
FUENTE = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FUENTE_B = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
GRIS, ROJO, VERDE, AZUL, AMARILLO = (100, 112, 152), (255, 66, 84), (60, 224, 160), (90, 160, 255), (255, 204, 44)
BLANCO, TENUE, OSCURO = (246, 248, 255), (160, 170, 205), (8, 10, 24)
VACUNADO = (240, 244, 255)
PV, PB = V1.PV, V1.PB
COLA = 10.0                         # segundos de pantalla final, sin voz
AVANCE = "avance"                   # el segmento extra que va tras el gancho

CAPITULO = {2: "LA RED", 5: "EXPERIMENTO 1 · VERDAD CONTRA BULO", 11: "EL PUNTO CRÍTICO",
            13: "EXPERIMENTO 2 · INFLUENCERS", 15: "¿SE PUEDE PARAR? · 1. EL DESMENTIDO",
            18: "¿SE PUEDE PARAR? · 2. LÍMITE DE REENVÍOS", 20: "¿SE PUEDE PARAR? · 3. VACUNARSE",
            22: "¿SE PUEDE PARAR? · 4. DUDAR", 24: None}
SIGUE = {6, 9, 14}                  # escenas que continuan la anterior sin corte

# ---------------------------------------------------------------- utilidades

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


def lerp(a, b, k):
    return a + (b - a)*k


def tx(d, xy, s, tam, col=BLANCO, anchor="mm", negra=True, borde=0, alfa=255):
    d.text(xy, s, font=F(tam, negra), fill=tuple(col[:3]) + (int(alfa),), anchor=anchor,
           stroke_width=borde, stroke_fill=OSCURO + (int(alfa),) if borde else None)


def caja(d, x0, y0, x1, y1, alfa=235, borde=(70, 86, 140), r=24):
    d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=(14, 18, 40, int(alfa)),
                        outline=tuple(borde) + (int(min(255, alfa)),), width=3)


def norm(p):
    p = unicodedata.normalize("NFD", p.lower())
    p = "".join(c for c in p if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w]", "", p)


def fondo():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt((xx - W/2)**2 + ((yy - H/2)*1.2)**2)/(W*0.6)
    k = np.clip(d, 0, 1)[..., None]**1.2
    img = np.array((30, 40, 86), np.float32)*(1 - k) + np.array((7, 9, 22), np.float32)*k
    img += np.random.default_rng(0).normal(0, 1.2, img.shape)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------- la red en pantalla

class Vista:
    """La red dentro de una caja de la pantalla, con camara (cx, cy, zoom)."""

    def __init__(self, red, x0, y0, w, r0, ss=2):
        self.red, self.r0, self.ss, self.w = red, r0, ss, w
        self.p = np.column_stack([x0 + red.pos[:, 0]*w, y0 + red.pos[:, 1]*w])
        a = np.array(red.enlaces)
        self.ea, self.eb = a[:, 0], a[:, 1]
        self.largo = np.hypot(*(self.p[self.ea] - self.p[self.eb]).T)
        hubs = set(red.influencers)
        self.de_hub = np.array([(x in hubs) or (y in hubs) for x, y in red.enlaces])
        self.lejano = (self.largo > w*0.12) & ~self.de_hub
        capa = Image.new("RGBA", (W*ss, H*ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        for k, (a_, b_) in enumerate(red.enlaces):
            (x1, y1), (x2, y2) = self.p[a_]*ss, self.p[b_]*ss
            alfa = 30 if self.de_hub[k] else (40 if self.lejano[k] else 70)
            d.line([(x1, y1), (x2, y2)], fill=(125, 145, 210, alfa), width=max(1, ss*w//1700))
        self.cache = capa
        self.cache1 = capa.resize((W, H), Image.LANCZOS)

    def xy(self, cam):
        cx, cy, z = cam
        return (self.p - [cx, cy])*z + [W/2, H/2]

    def enlaces(self, img, cam, alfa=1.0):
        cx, cy, z = cam
        if abs(z - 1) < 1e-3 and abs(cx - W/2) < 0.5 and abs(cy - H/2) < 0.5:
            capa = self.cache1
        else:
            s = self.ss
            caja_ = ((cx - W/2/z)*s, (cy - H/2/z)*s, (cx + W/2/z)*s, (cy + H/2/z)*s)
            caja_ = (max(0.0, caja_[0]), max(0.0, caja_[1]), min(W*s, caja_[2]), min(H*s, caja_[3]))
            capa = self.cache.resize((W, H), Image.BILINEAR, box=caja_)
        if alfa < 1:
            m = capa.getchannel("A").point(lambda v: int(v*alfa))
            img.paste(capa, (0, 0), m)
        else:
            img.paste(capa, (0, 0), capa)

    def nodos(self, img, cam, col, brillo, edad, grandes=(), alfa=1.0, aros=True):
        xy = self.xy(cam)
        z = cam[2]
        r = float(self.r0*float(z)**0.7)
        vis = np.where((xy[:, 0] > -20) & (xy[:, 0] < W + 20) & (xy[:, 1] > -20) & (xy[:, 1] < H + 20))[0]
        lit = [i for i in vis if brillo[i] > 0.02]
        if lit:
            h = Image.new("RGBA", (W//2, H//2), (0, 0, 0, 0))
            dh = ImageDraw.Draw(h)
            for i in lit:
                x, y = xy[i]/2
                rr = r*(0.8 + 1.2*brillo[i])
                dh.ellipse([x - rr, y - rr, x + rr, y + rr], fill=tuple(int(v) for v in col[i]) + (int(min(255, 90 + 150*brillo[i])*alfa),))
            h = h.filter(ImageFilter.GaussianBlur(max(2.0, r*0.7))).resize((W, H), Image.BILINEAR)
            img.paste(h, (0, 0), h)
        d = ImageDraw.Draw(img, "RGBA")
        gr = set(grandes)
        for i in vis:
            e = edad[i]
            salto = 1 + 1.1*max(0.0, 1 - e/0.3) if e >= 0 else 1.0
            rr = r*salto*(1.9 if i in gr else 1.0)
            x, y = xy[i]
            c = tuple(int(v) for v in col[i])
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=c + (int(255*alfa),))
            if i in gr:
                d.ellipse([x - rr - 5, y - rr - 5, x + rr + 5, y + rr + 5], outline=AMARILLO + (int(255*alfa),), width=3)
            if aros and 0 <= e < 0.8:
                k = e/0.8
                ra = r*(1.5 + 6*k)
                d.ellipse([x - ra, y - ra, x + ra, y + ra], outline=c + (int(200*(1 - k)*alfa),), width=2)
        return xy

    def pulsos(self, img, cam, casc, tr, col):
        ronda, frac = int(tr), tr - int(tr)
        xy = self.xy(cam)
        d = ImageDraw.Draw(img, "RGBA")
        for j in np.where(casc.cuando == ronda + 1)[0]:
            i = casc.de_quien[j]
            if i < 0:
                continue
            (x1, y1), (x2, y2) = xy[i], xy[j]
            x, y = x1 + (x2 - x1)*frac, y1 + (y2 - y1)*frac
            d.line([(x1, y1), (x, y)], fill=tuple(col) + (200,), width=max(2, int(cam[2]*1.5)))
            rr = 3 + cam[2]
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(255, 255, 255, 255))


def estado(claves, tr, spr, vac_alfa=1.0):
    n = RED.n
    col = np.tile(np.array(GRIS, float), (n, 1))
    brillo = np.zeros(n)
    edad = np.full(n, -1.0)
    fijo = np.zeros(n, bool)
    for k in claves:
        for j in CASC[k].vacunados:
            col[j] = np.array(GRIS)*(1 - vac_alfa) + np.array(VACUNADO)*vac_alfa
            fijo[j] = True
    for k in claves:
        c = CASC[k]
        tiene = np.where((c.cuando >= 0) & (c.cuando <= tr) & ~fijo)[0]
        col[tiene] = COLOR[k]
        edad[tiene] = (tr - c.cuando[tiene])*spr
        brillo[tiene] = np.maximum(0.18, 1 - (tr - c.cuando[tiene])/2.2)
        if k == "desm":
            fijo[tiene] = True
    return col, brillo, edad


def cuantos(clave, tr):
    c = CASC[clave]
    return int(((c.cuando >= 0) & (c.cuando <= tr)).sum())


def limita(cam):
    cx, cy, z = cam
    cx = min(max(cx, W/(2*z)), W - W/(2*z))
    cy = min(max(cy, H/(2*z)), H - H/(2*z))
    return (cx, cy, z)


def cam_sigue(vista, clave, tr, zmax=2.4):
    c = CASC[clave]
    acc = []
    for s in np.linspace(max(0.0, tr - 3), tr, 7):
        P = vista.p[(c.cuando >= 0) & (c.cuando <= s)]
        if len(P) < 3:
            P = np.vstack([P, vista.p[c.cuando == 0]])
            lo, hi = P.min(0) - 120, P.max(0) + 120
        else:
            lo, hi = np.percentile(P, 8, axis=0) - 110, np.percentile(P, 92, axis=0) + 110
        z = min(W*0.8/max(hi[0] - lo[0], 1), H*0.75/max(hi[1] - lo[1], 1), zmax)
        acc.append(((lo[0] + hi[0])/2, (lo[1] + hi[1])/2, max(1.0, z)))
    cx, cy, z = np.mean(acc, 0)
    return limita((float(cx), float(cy), float(z)))


CAM0 = (W/2, H/2, 1.0)

# ---------------------------------------------------------------- simulaciones


def prepara():
    """Las mismas reglas que bulos.py; el que lanza el mensaje, cerca del centro."""
    red = Red(alto=0.5)
    normales = [i for i in range(red.n) if i not in red.influencers]
    centro = np.array([0.5, 0.25])
    orden = sorted(normales, key=lambda i: np.hypot(*(red.pos[i] - centro)))
    origen = sem = None
    for o in orden:
        if red.grado[o] < 7:
            continue
        for s in range(6):
            v = Cascada(red, o, PV, semilla=s).corre().alcance()
            b = Cascada(red, o, PB, semilla=s).corre().alcance()
            if 4 <= v <= 14 and 600 <= b <= 760:
                origen, sem = o, s
                break
        if origen is not None:
            break
    c = {"verdad": Cascada(red, origen, PV, semilla=sem).corre(80),
         "bulo": Cascada(red, origen, PB, semilla=sem).corre(80)}

    def llega_a(cc, n):
        r = np.sort(cc.cuando[cc.cuando >= 0])
        return r[n - 1] if len(r) >= n else 99
    # Las tiradas son «todo o nada» (o se apaga pronto o llega a ~600-750): la
    # media de 471 mezcla las dos. Se compara una tirada que si arranca con una
    # del influencer, y se ensenan las medias de verdad (471 y 663).
    c["bulo_med"] = c["bulo"]
    inf = None
    for s in range(50):
        for i in red.influencers:
            x = Cascada(red, i, PB, semilla=s).corre(80)
            if c["bulo"].alcance() <= x.alcance() <= 780 and llega_a(x, 300) + 3 <= llega_a(c["bulo_med"], 300):
                inf, c["bulo_inf"] = i, x
                break
        if inf is not None:
            break
    for s in range(2000):       # dudando (30 % menos): una tirada cerca de su media (93)
        c["bulo_duda"] = Cascada(red, origen, PB*0.7, semilla=s).corre(80)
        if 60 <= c["bulo_duda"].alcance() <= 130:
            break
    for s in range(200):
        c["bulo_lim"] = Cascada(red, origen, PB, semilla=s, limite=5).corre(80)
        if 8 <= c["bulo_lim"].alcance() <= 20:
            break
    vac = set(int(x) for x in np.random.default_rng(9).choice(red.n, 300, replace=False)) - {origen}
    for s in range(2000):
        c["bulo_vac"] = Cascada(red, origen, PB, semilla=s, vacunados=vac).corre(80)
        if 50 <= c["bulo_vac"].alcance() <= 110:
            break
    D = 2
    corr = Cascada(red, inf, PB, semilla=1000 + sem)
    corr.cuando[:] = -1
    corr.cuando[inf] = D
    corr.frente = []
    bulo = Cascada(red, origen, PB, semilla=sem, inmunes=lambda i, ronda: 0 <= corr.cuando[i] <= ronda)
    for ronda in range(80):
        if ronda == D:
            corr.frente = [inf]
            corr.ronda = D
        if ronda >= D and corr.frente:
            corr.paso()
        if bulo.frente:
            bulo.paso()
    c["desm"], c["desm_bulo"] = corr, bulo
    print("demo:", {k: v.alcance() for k, v in c.items()}, "origen", origen, "influencer", inf, flush=True)
    return red, c, origen, inf


COLOR = {"verdad": VERDE, "bulo": ROJO, "bulo_inf": ROJO, "bulo_med": ROJO, "bulo_duda": ROJO,
         "desm_bulo": ROJO, "desm": AZUL, "bulo_lim": ROJO, "bulo_vac": ROJO}

# ---------------------------------------------------------------- contexto de un segmento


class Ctx:
    def __init__(self, i, dur, palabras, t0, voz):
        self.i, self.dur, self.pal, self.t0, self.voz = i, dur, palabras, t0, voz
        self.t = 0.0
        self.eventos = []
        self.prev = {}

    def en(self, palabra, n=1, exacta=False, tras=0.0):
        q = norm(palabra)
        vistos = 0
        for p, a, _ in self.pal:
            if a + 1e-6 < tras:
                continue
            w = norm(p)
            if (w == q) if exacta else w.startswith(q):
                vistos += 1
                if vistos == n:
                    return a
        print(f"  ! escena {self.i}: no encuentro «{palabra}»", flush=True)
        return self.dur*0.5

    def fin(self, palabra, n=1, exacta=False):
        q = norm(palabra)
        vistos = 0
        for p, _, b in self.pal:
            if (norm(p) == q) if exacta else norm(p).startswith(q):
                vistos += 1
                if vistos == n:
                    return b
        return self.dur*0.5

    def cruza(self, te):
        return self.t <= te < self.t + 1/FPS

    def son(self, tipo, vol=1.0, en=None):
        self.eventos.append((self.t0 + (self.t if en is None else en), tipo, vol))

    def tics(self, clave, tr, vol=1.0):
        antes = self.prev.get(clave)
        self.prev[clave] = tr
        if antes is None:
            return
        c = CASC[clave]
        n = int(((c.cuando > antes) & (c.cuando <= tr)).sum())
        if n:
            self.eventos.append((self.t0 + self.t, "tic", min(6, n)*vol))


def red_completa(img, C, claves, tr, spr, cam=CAM0, vista=None, grandes=None, vac_alfa=1.0, sonar=True, alfa=1.0):
    vista = vista or GRANDE
    vista.enlaces(img, cam, alfa)
    for k in claves:
        vista.pulsos(img, cam, CASC[k], tr, COLOR[k])
    col, brillo, edad = estado(claves, tr, spr, vac_alfa)
    if grandes is None:
        grandes = (ORIGEN,) if claves else ()
    xy = vista.nodos(img, cam, col, brillo, edad, grandes=grandes, alfa=alfa)
    if sonar:
        for k in claves:
            C.tics(k, tr)
    return xy


def contador(d, n, col, hora=None, x=1660, y=70, texto="lo han recibido"):
    caja(d, x - 230, y, x + 230, y + 210)
    tx(d, (x, y + 72), f"{n}", 96, col)
    tx(d, (x, y + 140), f"de 1.000 {texto}", 30, (205, 214, 240), negra=False)
    if hora is not None:
        tx(d, (x, y + 182), f"hora {hora}", 26, TENUE, negra=False)


def chip(d, x, y, s, col, tam=34, k=1.0, fondo_=(14, 18, 40), anchor="mm"):
    if k <= 0:
        return
    esc = sale(k)
    f = F(tam*esc)
    w = d.textlength(s, font=f)
    hh = tam*esc*1.5
    if anchor == "lm":
        x = x + w/2 + 26*esc
    a = int(255*min(1, k*2))
    d.rounded_rectangle([x - w/2 - 26*esc, y - hh/2, x + w/2 + 26*esc, y + hh/2], radius=hh/2,
                        fill=tuple(fondo_) + (int(235*min(1, k*2)),), outline=tuple(col) + (a,), width=3)
    d.text((x, y), s, font=f, fill=tuple(col) + (a,), anchor="mm")


def flecha_reenviar(d, x, y, s, col):
    d.arc([x - s, y - s*0.2, x + s*0.6, y + s*1.4], 200, 300, fill=col, width=max(2, int(s/5)))
    d.polygon([(x + s*0.45, y - s*0.15), (x + s*1.05, y + s*0.25), (x + s*0.4, y + s*0.65)], fill=col)


def check(d, x, y, s, col, w=6):
    d.line([(x - s, y), (x - s*0.3, y + s*0.7), (x + s, y - s*0.8)], fill=col, width=w, joint="curve")


def cruz(d, x, y, s, col, w=5):
    d.line([(x - s, y - s), (x + s, y + s)], fill=col, width=w)
    d.line([(x - s, y + s), (x + s, y - s)], fill=col, width=w)


def barras(img, C, titulo, datos, revela, nota="personas de cada 1.000", dim=0.0):
    d = ImageDraw.Draw(img, "RGBA")
    k0 = ease(C.t/0.4)
    tx(d, (W/2, 108 - 20*(1 - k0)), titulo, 50, alfa=255*k0)
    n = len(datos)
    ancho = min(240, 1400/n - 50)
    x0 = W/2 - (n*(ancho + 50) - 50)/2
    base = 800
    vmax = max(v for _, v, _ in datos)
    escala = 520/vmax
    d.line([(x0 - 40, base), (x0 + n*(ancho + 50) - 10, base)], fill=(110, 122, 170, 255), width=3)
    ultima = max([r for r in revela if r <= C.t], default=None)
    for k, ((et, v, col), r) in enumerate(zip(datos, revela)):
        x = x0 + k*(ancho + 50)
        q = ease((C.t - r)/0.7)
        if C.cruza(r):
            C.son("ding", 0.8, en=r)
        al = 255*(1 - 0.7*dim)
        if q > 0:
            alto = max(6, v*escala*q)
            if r == ultima and C.t - r < 2.5:
                g = Image.new("RGBA", (W//2, H//2), (0, 0, 0, 0))
                ImageDraw.Draw(g).rounded_rectangle([x/2 - 10, (base - alto)/2 - 10, (x + ancho)/2 + 10, base/2],
                                                    radius=10, fill=tuple(col) + (int(150*(1 - (C.t - r)/2.5)),))
                g = g.filter(ImageFilter.GaussianBlur(14)).resize((W, H), Image.BILINEAR)
                img.paste(g, (0, 0), g)
                d = ImageDraw.Draw(img, "RGBA")
            d.rounded_rectangle([x, base - alto, x + ancho, base], radius=14, fill=tuple(col) + (int(al),))
            tx(d, (x + ancho/2, base - alto - 44), f"{int(round(v*q))}", 58, col, alfa=al)
        else:
            d.rounded_rectangle([x, base - 6, x + ancho, base], radius=3, fill=(70, 80, 120, int(al)))
        tx(d, (x + ancho/2, base + 42), et, 34 if n > 3 else 42, (215, 222, 245), negra=False,
           alfa=(255 if q > 0 else 120)*(1 - 0.6*dim))
    tx(d, (W/2, base + 100), nota, 28, TENUE, negra=False, alfa=200*k0*(1 - 0.6*dim))
    return d

# ---------------------------------------------------------------- escenas


def sello(img, texto, esc, alfa, col=ROJO, ang=-8, x=W/2, y=H/2 - 30):
    f = F(190*esc)
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    w = d.textlength(texto, font=f)
    hh = 190*esc
    d.rounded_rectangle([x - w/2 - 50*esc, y - hh*0.75, x + w/2 + 50*esc, y + hh*0.75], radius=30*esc,
                        outline=tuple(col) + (int(255*alfa),), width=int(16*esc))
    d.text((x, y), texto, font=f, fill=tuple(col) + (int(255*alfa),), anchor="mm")
    capa = capa.rotate(ang, resample=Image.BICUBIC, center=(x, y))
    img.paste(capa, (0, 0), capa)


def e_gancho(img, C):
    tr_ini, t_ciudad, t_ment = C.en("reenviar"), C.fin("ciudad"), C.en("mentira")
    span = max(1.0, t_ciudad + 0.3 - tr_ini)
    u = max(0.0, (C.t - tr_ini)/span)
    tr = 24*min(1.0, u**1.15)
    spr = span/24
    ox, oy = GRANDE.p[ORIGEN]
    cam_ini = limita((ox, oy, 3.2))
    k = ease((C.t - tr_ini - 0.2)/(span*0.9))
    cam = limita((lerp(cam_ini[0], W/2, k), lerp(cam_ini[1], H/2, k), lerp(3.2, 1.0, k)))
    xy = red_completa(img, C, ["bulo"], tr, spr, cam)
    d = ImageDraw.Draw(img, "RGBA")
    a = ease(C.t/0.35)*(1 - ease((C.t - tr_ini - 0.5)/0.5))
    if a > 0:
        x, y = xy[ORIGEN]
        bx, by = x + 40, y - 250
        d.rounded_rectangle([bx, by, bx + 470, by + 200], radius=26, fill=(220, 248, 198, int(250*a)))
        d.polygon([(bx + 10, by + 200), (bx + 50, by + 200), (x + 12, y - 12)], fill=(220, 248, 198, int(250*a)))
        flecha_reenviar(d, bx + 30, by + 22, 16, (110, 120, 120, int(255*a)))
        tx(d, (bx + 64, by + 34), "Reenviado muchas veces", 24, (110, 120, 120), anchor="lm", negra=False, alfa=255*a)
        tx(d, (bx + 28, by + 92), "¡¡URGENTE!!", 44, (200, 30, 40), anchor="lm", alfa=255*a)
        tx(d, (bx + 28, by + 150), "Pásalo a todos tus contactos", 32, (30, 30, 30), anchor="lm", alfa=255*a)
        pk = max(0.0, 1 - abs(C.t - tr_ini)/0.25)
        cx_, cy_ = bx + 470 + 50, by + 100
        rr = 36*(1 + 0.25*pk)
        d.ellipse([cx_ - rr, cy_ - rr, cx_ + rr, cy_ + rr], fill=(40, 46, 60, int(240*a)), outline=(220, 248, 198, int(255*a)), width=3)
        flecha_reenviar(d, cx_ - 14, cy_ - 14, 18, (220, 248, 198, int(255*a)))
    if C.cruza(tr_ini):
        C.son("pop", 1.2)
    n = cuantos("bulo", tr)
    ka = ease((C.t - tr_ini - 0.6)/0.4)
    if ka > 0:
        caja(d, 1430, 60, 1890, 270, alfa=235*ka)
        tx(d, (1660, 132), f"{n}", 96, ROJO, alfa=255*ka)
        tx(d, (1660, 200), "lo han recibido", 30, (205, 214, 240), negra=False, alfa=255*ka)
        tx(d, (1660, 240), f"hora {int(tr)}", 26, TENUE, negra=False, alfa=255*ka)
    if C.t >= t_ment:
        k = (C.t - t_ment)/0.22
        if C.cruza(t_ment):
            C.son("golpe", 1.0)
        sello(img, "BULO", 2.2 - 1.2*ease(k), min(1.0, k*1.5))
    return img


def e_avance(img, C):
    """Tras el gancho: el resultado, ya. «Con solo un 70 % mas de reenvios,
    llega a mas de diez veces mas gente.»"""
    t70, tdiez = C.en("setenta"), C.en("diez")
    d = ImageDraw.Draw(img, "RGBA")
    k = ease(C.t/0.3)
    tx(d, (W/2, 120), "1.000 personas simuladas · media de 60 lanzamientos", 34, TENUE, negra=False, alfa=255*k)
    base, x1, x2, ancho = 860, 620, 1060, 240
    q1 = ease((C.t - 0.1)/0.5)
    q2 = ease((C.t - t70)/0.9)
    alto_v = V1.MEDIA_VERDAD/V1.MEDIA_BULO*560*q1
    alto_b = 560*q2
    d.line([(x1 - 80, base), (x2 + ancho + 80, base)], fill=(110, 122, 170, 255), width=3)
    d.rounded_rectangle([x1, base - max(6, alto_v), x1 + ancho, base], radius=14, fill=VERDE + (255,))
    tx(d, (x1 + ancho/2, base - alto_v - 44), f"{int(V1.MEDIA_VERDAD*q1)}", 58, VERDE)
    tx(d, (x1 + ancho/2, base + 42), "la verdad", 42, (215, 222, 245), negra=False)
    d.rounded_rectangle([x2, base - max(6, alto_b), x2 + ancho, base], radius=14, fill=ROJO + (255,))
    if q2 > 0:
        tx(d, (x2 + ancho/2, base - alto_b - 44), f"{int(V1.MEDIA_BULO*q2)}", 58, ROJO)
        if C.cruza(t70):
            C.son("whoosh", 0.7)
    tx(d, (x2 + ancho/2, base + 42), "el bulo", 42, (215, 222, 245), negra=False)
    tx(d, (x2 + ancho/2, base + 90), "+70 % de reenvíos", 30, ROJO, negra=False, alfa=255*ease((C.t - t70)/0.3))
    q = sale((C.t - tdiez)/0.45)
    if q > 0:
        tx(d, (380, 430), "×11", int(170*q) + 1, AMARILLO, borde=10)
        tx(d, (380, 560), "más gente", 52, AMARILLO, borde=6, alfa=255*min(1, q))
        if C.cruza(tdiez):
            C.son("golpe", 0.9)
    return img


def e_pregunta(img, C):
    """La pregunta, con la red ya delante (sin pantalla de titulo)."""
    t_para, t_solt = C.en("para"), C.en("soltado")
    k_red = ease((C.t - t_para + 0.3)/0.8)
    GRANDE.enlaces(img, CAM0, max(0.05, k_red))
    col = np.tile(np.array(GRIS, float), (RED.n, 1))
    brillo = np.zeros(RED.n)
    edad = np.full(RED.n, -1.0)
    if C.t >= t_solt:
        edad[ORIGEN] = C.t - t_solt
        col[ORIGEN] = ROJO
        brillo[ORIGEN] = 1.0
        if C.cruza(t_solt):
            C.son("pop", 1.2)
    GRANDE.nodos(img, CAM0, col, brillo, edad, grandes=(ORIGEN,) if C.t >= t_solt else (), alfa=max(0.05, k_red))
    d = ImageDraw.Draw(img, "RGBA")
    a = 1 - ease((C.t - t_para)/0.5)
    if a > 0:
        q = sale(C.t/0.4)
        tx(d, (W/2, H/2 - 60), "¿Por qué los bulos llegan tan lejos", int(70*max(q, 0.05)), BLANCO, borde=8, alfa=255*a)
        tx(d, (W/2, H/2 + 40), "y la verdad casi nunca?", int(70*max(q, 0.05)), ROJO, borde=8, alfa=255*a*ease((C.t - 1.0)/0.4))
    ka = ease((C.t - t_para - 0.3)/0.5)
    if ka > 0:
        chip(d, W/2, 50, "LO HE SIMULADO · 1.000 personas", AMARILLO, 34, ka)
    return img


def e_red(img, C):
    t_linea, t_fam, t_ami, t_trab = C.en("linea"), C.en("familia"), C.en("amigos"), C.en("trabajo")
    t_may, t_lej, t_primo = C.en("mayoria"), C.en("lejano"), C.en("primo")
    ox, oy = GRANDE.p[ORIGEN]
    k = ease((C.t - t_may)/1.4)
    cam = limita((lerp(ox, W/2, k), lerp(oy, H/2, k), lerp(3.0, 1.0, k)))
    GRANDE.enlaces(img, cam)
    xy = GRANDE.xy(cam)
    d = ImageDraw.Draw(img, "RGBA")
    vec = RED.vecinos[ORIGEN]
    kl = ease((C.t - t_linea)/0.5)*(1 - k)
    for j in vec:
        if kl > 0:
            (x1, y1), (x2, y2) = xy[ORIGEN], xy[j]
            d.line([(x1, y1), (x1 + (x2 - x1)*kl, y1 + (y2 - y1)*kl)], fill=AMARILLO + (230,), width=5)
    kj = (C.t - t_lej)/1.6
    if kj > 0:
        idx = np.where(GRANDE.lejano)[0]
        for m, e in enumerate(idx):
            q = ease(kj*1.6 - (m/len(idx))*0.9)
            if q <= 0:
                continue
            (x1, y1), (x2, y2) = xy[GRANDE.ea[e]], xy[GRANDE.eb[e]]
            d.line([(x1, y1), (x1 + (x2 - x1)*q, y1 + (y2 - y1)*q)], fill=AMARILLO + (55,), width=2)
        if C.cruza(t_lej):
            C.son("whoosh", 0.8)
    col = np.tile(np.array(GRIS, float), (RED.n, 1))
    brillo = np.zeros(RED.n)
    edad = np.full(RED.n, -1.0)
    col[ORIGEN] = AMARILLO
    brillo[ORIGEN] = 0.8*(1 - k)
    for j, t_ in zip(vec[:3], (t_fam, t_ami, t_trab)):
        if C.t >= t_:
            col[j] = BLANCO
            edad[j] = C.t - t_
    GRANDE.nodos(img, cam, col, brillo, edad)
    d = ImageDraw.Draw(img, "RGBA")
    ka = ease((C.t - 0.2)/0.4)*(1 - k)
    if ka > 0:
        x, y = xy[ORIGEN]
        chip(d, x, y - 70, "una persona", AMARILLO, 34, ka)
    for j, t_, s in zip(vec[:3], (t_fam, t_ami, t_trab), ("familia", "amigos", "trabajo")):
        q = ease((C.t - t_)/0.3)*(1 - k)
        if q > 0:
            x, y = xy[j]
            dx, dy = x - xy[ORIGEN][0], y - xy[ORIGEN][1]
            nn = math.hypot(dx, dy) or 1
            chip(d, x + dx/nn*90, y + dy/nn*60, s, BLANCO, 30, q)
            if C.cruza(t_):
                C.son("pop", 0.7)
    kp = ease((C.t - t_primo)/0.4)
    if kp > 0:
        e = PRIMO
        (x1, y1), (x2, y2) = xy[GRANDE.ea[e]], xy[GRANDE.eb[e]]
        d.line([(x1, y1), (x2, y2)], fill=AMARILLO + (int(255*kp),), width=6)
        for (x, y) in ((x1, y1), (x2, y2)):
            d.ellipse([x - 12, y - 12, x + 12, y + 12], fill=AMARILLO + (int(255*kp),))
        chip(d, (x1 + x2)/2, (y1 + y2)/2 - 50, "el primo de otra ciudad", AMARILLO, 32, kp)
    if C.t > t_lej:
        chip(d, W/2, 50, "contactos lejanos", AMARILLO, 34, ease((C.t - t_lej)/0.4))
    return img


def e_influencers(img, C):
    t_inf = C.en("influencers")
    GRANDE.enlaces(img, CAM0)
    xy = GRANDE.xy(CAM0)
    d = ImageDraw.Draw(img, "RGBA")
    hubs = RED.influencers
    for h_, hub in enumerate(hubs):
        q = ease((C.t - 0.3 - 0.25*h_)/1.0)
        if q <= 0:
            continue
        for j in RED.vecinos[hub]:
            (x1, y1), (x2, y2) = xy[hub], xy[j]
            d.line([(x1, y1), (x1 + (x2 - x1)*q, y1 + (y2 - y1)*q)], fill=AMARILLO + (90,), width=2)
        if C.cruza(0.3 + 0.25*h_):
            C.son("whoosh", 0.5)
    col = np.tile(np.array(GRIS, float), (RED.n, 1))
    brillo = np.zeros(RED.n)
    edad = np.full(RED.n, -1.0)
    for h_, hub in enumerate(hubs):
        if C.t > 0.3 + 0.25*h_:
            col[hub] = AMARILLO
            brillo[hub] = 1.0
            edad[hub] = C.t - 0.3 - 0.25*h_
    GRANDE.nodos(img, CAM0, col, brillo, edad, grandes=hubs)
    d = ImageDraw.Draw(img, "RGBA")
    chip(d, W/2, 50, "INFLUENCERS: casi 100 contactos cada uno", AMARILLO, 36, ease((C.t - t_inf)/0.4))
    return img


def e_regla(img, C):
    t_llega, t_cada, t_veces = C.en("llega"), C.en("cada"), C.en("veces")
    t_no = C.en("no", exacta=True, tras=t_veces)
    ox, oy = GRANDE.p[ORIGEN]
    cam = limita((ox, oy, 3.3))
    GRANDE.enlaces(img, cam)
    xy = GRANDE.xy(cam)
    d = ImageDraw.Draw(img, "RGBA")
    vec = sorted(RED.vecinos[ORIGEN], key=lambda j: math.atan2(*(GRANDE.p[j] - GRANDE.p[ORIGEN])[::-1]))
    v = CASC["verdad"]
    exito = {j: (v.cuando[j] == 1 and v.de_quien[j] == ORIGEN) for j in vec}
    paso = (t_veces - t_cada)/max(1, len(vec))
    col = np.tile(np.array(GRIS, float), (RED.n, 1))
    brillo = np.zeros(RED.n)
    edad = np.full(RED.n, -1.0)
    if C.t >= t_llega:
        col[ORIGEN] = VERDE
        brillo[ORIGEN] = 1.0
        edad[ORIGEN] = C.t - t_llega
        if C.cruza(t_llega):
            C.son("pop", 1.0)
    marcas = []
    for m, j in enumerate(vec):
        ts = t_cada + m*paso
        q = (C.t - ts)/0.55
        if q <= 0:
            continue
        (x1, y1), (x2, y2) = xy[ORIGEN], xy[j]
        if exito[j]:
            qq = min(1.0, q)
            d.line([(x1, y1), (x1 + (x2 - x1)*qq, y1 + (y2 - y1)*qq)], fill=VERDE + (230,), width=6)
            if q >= 1:
                col[j] = VERDE
                brillo[j] = 1.0
                edad[j] = (q - 1)*0.55
                marcas.append((j, True))
                if C.cruza(ts + 0.55):
                    C.son("ding", 0.7)
            else:
                x, y = x1 + (x2 - x1)*qq, y1 + (y2 - y1)*qq
                d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=(255, 255, 255, 255))
        else:
            qq = min(0.55, q)
            fade = 1 - ease((q - 0.55)/0.6)
            d.line([(x1, y1), (x1 + (x2 - x1)*qq, y1 + (y2 - y1)*qq)], fill=(150, 160, 190, int(200*fade)), width=5)
            if q >= 0.55:
                marcas.append((j, False))
                if C.cruza(ts + 0.3):
                    C.son("pop", 0.35)
    GRANDE.nodos(img, cam, col, brillo, edad)
    d = ImageDraw.Draw(img, "RGBA")
    for j, ok in marcas:
        x, y = xy[j]
        if ok:
            check(d, x + 40, y - 40, 16, VERDE, 7)
        else:
            cruz(d, x + 40, y - 40, 12, (230, 90, 100), 6)
    k = ease(C.t/0.4)
    caja(d, 560, 40, 1360, 160, alfa=230*k)
    tx(d, (W/2, 82), "La regla", 30, AMARILLO, alfa=255*k)
    tx(d, (W/2, 126), "Cada contacto: UNA oportunidad de reenviárselo", 38, alfa=255*k)
    if C.t > t_no:
        chip(d, W/2, 910, "a veces lo hace… y a veces no", BLANCO, 32, ease((C.t - t_no)/0.3))
    return img


def e_verdad(img, C, parte):
    v = CASC["verdad"]
    ox, oy = GRANDE.p[ORIGEN]
    if parte == 0:
        t0 = C.en("lanza")
        tr = 4*ease((C.t - t0)/max(0.5, C.dur - t0))
        cam = limita((ox, oy, 2.4))
        spr = (C.dur - t0)/4
    else:
        tr = 4 + 10*min(1.0, C.t/(C.dur*0.75))
        k = ease((C.t - C.dur*0.6)/(C.dur*0.35))
        cam = limita((lerp(ox, W/2, k), lerp(oy, H/2, k), lerp(2.4, 1.0, k)))
        spr = C.dur*0.75/10
    red_completa(img, C, ["verdad"], tr, spr, cam)
    d = ImageDraw.Draw(img, "RGBA")
    contador(d, cuantos("verdad", tr), VERDE, hora=int(tr))
    if parte == 0:
        chip(d, 80, 140, "la verdad", VERDE, 34, ease((C.t - 0.2)/0.4), anchor="lm")
    if parte == 1 and C.t > C.en("pocas"):
        chip(d, W/2, 900, f"Se apagó: solo {v.alcance()} personas", VERDE, 40, ease((C.t - C.en("pocas"))/0.4))
    return img


def e_mit(img, C):
    t_2018, t_cien, t_verd, t_fals = C.en("2018"), C.en("ciento"), C.en("verdaderas"), C.en("falsas")
    t_70, t_sorp, t_ind, t_prim = C.en("setenta"), C.en("sorprenden"), C.en("indignan"), C.en("primeros")
    d = ImageDraw.Draw(img, "RGBA")
    a = 1 - ease((C.t - t_2018 + 0.3)/0.4)
    if a > 0:
        tx(d, (W/2, H/2 - 40), "Ahora, un bulo.", 110*(0.92 + 0.08*sale(C.t/0.4)), ROJO, alfa=255*a*ease(C.t/0.25))
    k = ease((C.t - t_2018 + 0.2)/0.5)
    if k <= 0:
        return img
    caja(d, 90, 60 + 30*(1 - k), 1830, 210 + 30*(1 - k), alfa=235*k)
    tx(d, (W/2, 112 + 30*(1 - k)), "ESTUDIO REAL · MIT · 2018", 50, AMARILLO, alfa=255*k)
    tx(d, (W/2, 170 + 30*(1 - k)), "Vosoughi, Roy y Aral · revista Science", 30, TENUE, negra=False, alfa=255*k)
    tipo = np.random.default_rng(4).random(12*9) < 0.5
    kc = (C.t - t_cien)/1.0
    for m in range(12*9):
        fx, fy = m % 12, m//12
        q = ease(kc*2 - (fx + fy)/20*1.2)
        if q <= 0:
            continue
        x, y = 140 + fx*62, 300 + fy*58
        kv = ease((C.t - (t_verd if not tipo[m] else t_fals))/0.3)
        c = tuple(int(v_) for v_ in np.array((70, 84, 130))*(1 - kv) + np.array(ROJO if tipo[m] else VERDE)*kv)
        s = 0.6 + 0.4*sale(q)
        d.rounded_rectangle([x, y, x + 50*s, y + 40*s], radius=8, fill=c + (int(255*q),))
        d.line([(x + 8*s, y + 13*s), (x + 40*s, y + 13*s)], fill=(255, 255, 255, int(160*q)), width=3)
        d.line([(x + 8*s, y + 25*s), (x + 30*s, y + 25*s)], fill=(255, 255, 255, int(160*q)), width=3)
    if kc > 0:
        n = int(126000*ease(kc/1.2))
        tx(d, (510, 860), f"{n:,}".replace(",", ".") + " historias", 54, BLANCO)
        tx(d, (510, 915), "compartidas en Twitter", 30, TENUE, negra=False)
        if C.cruza(t_cien):
            C.son("whoosh", 0.7)
    if C.t > t_verd:
        chip(d, 330, 260, "verdaderas", VERDE, 28, ease((C.t - t_verd)/0.3))
    if C.t > t_fals:
        chip(d, 690, 260, "falsas", ROJO, 28, ease((C.t - t_fals)/0.3))
    k7 = ease((C.t - t_70 + 0.2)/0.5)
    if k7 > 0:
        tx(d, (1430, 300), "Probabilidad de ser compartida", 34, TENUE, negra=False, alfa=255*k7)
        for m, (et, val, col) in enumerate((("verdaderas", 1.0, VERDE), ("falsas", 1.7, ROJO))):
            y = 380 + m*120
            q = ease((C.t - t_70 - 0.1 - m*0.5)/0.6)
            tx(d, (1190, y + 35), et, 34, col, anchor="rm", negra=False, alfa=255*k7)
            d.rounded_rectangle([1215, y, 1215 + 380*val*q, y + 70], radius=12, fill=tuple(col) + (int(255*k7),))
        q = sale((C.t - t_70 - 0.9)/0.4)
        if q > 0:
            tx(d, (1430, 690), "+70%", int(150*q) + 1, ROJO)
            if C.cruza(t_70 + 0.9):
                C.son("golpe", 0.6)
    for t_, s, x in ((t_sorp, "SORPRENDEN", 1130), (t_ind, "INDIGNAN", 1440), (t_prim, "SER EL PRIMERO", 1700)):
        q = ease((C.t - t_)/0.3)
        if q > 0:
            chip(d, x, 860, s, AMARILLO, 32, q)
            if C.cruza(t_):
                C.son("pop", 0.8)
    return img


def e_bulo(img, C, parte):
    if parte == 0:
        t0 = C.en("lanza")
        tr = 6*ease((C.t - t0)/max(0.5, C.dur - t0))
        spr = (C.dur - t0)/6
        chip_k = ease((C.t - 0.1)/0.4)
    else:
        tr = 6 + 24*min(1.0, C.t/(C.dur*0.85))
        spr = C.dur*0.85/24
        chip_k = 1.0
    cam = cam_sigue(GRANDE, "bulo", tr)
    red_completa(img, C, ["bulo"], tr, spr, cam)
    d = ImageDraw.Draw(img, "RGBA")
    contador(d, cuantos("bulo", tr), ROJO, hora=int(tr))
    chip(d, 80, 140, "el bulo · +70% de reenvíos", ROJO, 34, chip_k, anchor="lm")
    return img


def e_media(img, C):
    t_60, t_40, t_470, t_10 = C.en("sesenta"), C.en("cuarenta"), C.en("cuatrocientas"), C.en("diez")
    d = barras(img, C, "¿A cuánta gente llega? Media de 60 lanzamientos",
               [("La verdad", V1.MEDIA_VERDAD, VERDE), ("El bulo", V1.MEDIA_BULO, ROJO)], [t_40, t_470])
    q = (C.t - t_60)/1.0
    if q > 0 and C.t < t_40 + 0.5:
        a = 1 - ease((C.t - t_40)/0.5)
        for m in range(60):
            if q*60 > m:
                x = W/2 - 59*14 + m*28
                d.ellipse([x - 8, 186, x + 8, 202], fill=AMARILLO + (int(230*a),))
        tx(d, (W/2, 240), "60 personas distintas lanzan el mensaje", 30, TENUE, negra=False, alfa=255*a*ease(q))
    k = sale((C.t - t_10)/0.5)
    if k > 0:
        tx(d, (1500, 420), "más de 10 veces", 64*k + 1, AMARILLO)
        tx(d, (1500, 490), "más gente", 52*k + 1, AMARILLO)
        if C.cruza(t_10):
            C.son("golpe", 0.6)
    return img


def arbol(gens, x0, y0, w, h):
    nodos, aristas, prev = [], [], []
    paso = w/max(1, len(gens) - 1)
    for g, n in enumerate(gens):
        idx = []
        for k in range(n):
            nodos.append((g, x0 + g*paso, y0 + h*(k + 0.5)/n))
            idx.append(len(nodos) - 1)
            if prev:
                aristas.append((prev[min(len(prev) - 1, k*len(prev)//n)], idx[-1]))
        prev = idx
    return nodos, aristas


def pinta_arbol(d, nodos, aristas, t_ini, paso, t, col):
    for a, b in aristas:
        gb = nodos[b][0]
        q = ease((t - t_ini - (gb - 1)*paso)/(paso*0.8))
        if q <= 0:
            continue
        (_, x1, y1), (_, x2, y2) = nodos[a], nodos[b]
        d.line([(x1, y1), (x1 + (x2 - x1)*q, y1 + (y2 - y1)*q)], fill=tuple(col) + (200,), width=4)
    for g, x, y in nodos:
        q = ease((t - t_ini - g*paso)/0.2)
        if q > 0:
            r = 13*sale(q)
            d.ellipse([x - r, y - r, x + r, y + r], fill=tuple(col) + (255,))


def e_critico(img, C):
    t_punto, t_menos, t_apaga = C.en("punto"), C.en("menos"), C.en("apaga")
    t_mas, t_expl, t_verd = C.en("mas", exacta=True), C.en("explota"), C.en("verdad")
    d = ImageDraw.Draw(img, "RGBA")
    a = 1 - ease((C.t - t_verd + 0.2)/0.5)
    if a > 0:
        if C.t < t_punto:
            q = ease(C.t/0.4)
            tx(d, (W/2, H/2 - 60), "+70% de reenvíos", 90, ROJO, alfa=255*q)
            tx(d, (W/2, H/2 + 50), "→  más de 10 veces más gente", 64, AMARILLO, alfa=255*ease((C.t - 1.2)/0.4))
            tx(d, (W/2, H/2 + 140), "¿cómo?", 54, BLANCO, alfa=255*ease((C.t - 2.0)/0.4))
        else:
            kp = ease((C.t - t_punto)/0.4)
            tx(d, (W/2, 95), "EL PUNTO CRÍTICO", 64, AMARILLO, alfa=255*kp*a)
            if C.cruza(t_punto):
                C.son("whoosh", 0.8)
            nl, al_ = arbol([1, 1, 2, 1], 140, 330, 480, 420)
            caja(d, 60, 190, 930, 880, alfa=200*kp*a)
            tx(d, (495, 245), "Cada uno se lo pasa a", 34, BLANCO, negra=False, alfa=255*kp*a)
            tx(d, (495, 295), "MENOS de 1 persona nueva", 40, VERDE, alfa=255*kp*a)
            if C.t > t_menos:
                pinta_arbol(d, nl, al_, t_menos, 0.45, C.t, VERDE)
                fin = t_menos + 3*0.45 + 0.4
                if C.t > fin:
                    cruz(d, nl[-1][1] + 110, nl[-1][2], 18, (230, 90, 100), 6)
                    chip(d, 495, 820, "SE APAGA", VERDE, 40, ease((C.t - max(fin, t_apaga))/0.3))
            nr, ar_ = arbol([1, 2, 3, 5, 8, 13], 1060, 330, 760, 420)
            caja(d, 990, 190, 1860, 880, alfa=200*kp*a)
            tx(d, (1425, 245), "Cada uno se lo pasa a", 34, BLANCO, negra=False, alfa=255*kp*a)
            tx(d, (1425, 295), "MÁS de 1 persona nueva", 40, ROJO, alfa=255*kp*a)
            if C.t > t_mas:
                pinta_arbol(d, nr, ar_, t_mas, 0.32, C.t, ROJO)
                for g in range(1, 6):
                    if C.cruza(t_mas + g*0.32):
                        C.son("pop", 0.3 + 0.12*g)
                chip(d, 1425, 820, "EXPLOTA", ROJO, 40, ease((C.t - t_expl)/0.3))
                if C.cruza(t_expl):
                    C.son("golpe", 0.6)
    k = ease((C.t - t_verd + 0.2)/0.5)
    if k > 0:
        grafica(d, C, k, C.t - t_verd)
    return img


def grafica(d, C, k, t):
    B = V1.BARRIDO
    tx(d, (W/2, 95), "¿A cuánta gente llega, según cuánto se reenvía?", 50, alfa=255*k)
    x0, y0, ww, hh = 230, 800, 1480, 580
    X = lambda pr: x0 + (pr - 6)/34*ww  # noqa: E731
    Y = lambda v: y0 - v/1000*hh  # noqa: E731
    xc = X(14)
    d.rectangle([x0, y0 - hh, xc, y0], fill=(60, 224, 160, int(22*k)))
    d.rectangle([xc, y0 - hh, x0 + ww, y0], fill=(255, 66, 84, int(22*k)))
    tx(d, ((x0 + xc)/2, y0 - hh + 40), "SE APAGA", 30, VERDE, alfa=255*k)
    tx(d, ((xc + x0 + ww)/2, y0 - hh + 40), "EXPLOTA", 30, ROJO, alfa=255*k)
    d.line([(x0, y0), (x0 + ww, y0)], fill=(150, 160, 200, int(255*k)), width=4)
    d.line([(x0, y0), (x0, y0 - hh)], fill=(150, 160, 200, int(255*k)), width=4)
    for v in (250, 500, 750, 1000):
        tx(d, (x0 - 20, Y(v)), f"{v}", 26, TENUE, anchor="rm", negra=False, alfa=255*k)
    for pr in (6, 10, 14, 18, 22, 26, 30, 34, 38):
        tx(d, (X(pr), y0 + 36), f"{pr}%", 28, TENUE, negra=False, alfa=255*k)
    tx(d, (W/2, y0 + 86), "probabilidad de reenviárselo a cada contacto", 30, TENUE, negra=False, alfa=255*k)
    p = ease(t/2.2)
    xs = np.linspace(6, 6 + 34*p, 80)
    ys = np.interp(xs, [b[0] for b in B], [b[1] for b in B])
    if p > 0.02:
        d.line([(X(a), Y(b)) for a, b in zip(xs, ys)], fill=AMARILLO + (255,), width=8, joint="curve")
    d.line([(xc, y0), (xc, y0 - hh)], fill=(255, 255, 255, int(150*k)), width=3)
    tx(d, (xc + 14, y0 - hh + 90), "PUNTO CRÍTICO", 30, BLANCO, anchor="lm", alfa=255*k)
    for pr, nombre, col, tt in ((13, "LA VERDAD", VERDE, C.en("verdad")), (22, "EL BULO", ROJO, C.en("bulo"))):
        q = sale((C.t - tt)/0.4)
        if q > 0 and p > (pr - 6)/34:
            v = np.interp(pr, [b[0] for b in B], [b[1] for b in B])
            x, y = X(pr), Y(v)
            r = 18*q
            d.ellipse([x - r, y - r, x + r, y + r], fill=tuple(col) + (255,), outline=BLANCO + (255,), width=3)
            tx(d, (x + (-30 if pr == 13 else 30), y - 60), nombre, 40, col, anchor="rm" if pr == 13 else "lm", borde=6)
            if C.cruza(tt):
                C.son("ding", 0.7)


def e_carrera(img, C):
    t_antes, t_seis = C.en("antes"), C.en("seis")
    d = ImageDraw.Draw(img, "RGBA")
    k = ease(C.t/0.4)
    caja(d, 90, 60, 1830, 210, alfa=235*k)
    tx(d, (W/2, 112), "ESTUDIO REAL · MIT · 2018", 50, AMARILLO, alfa=255*k)
    tx(d, (W/2, 170), "Vosoughi, Roy y Aral · revista Science", 30, TENUE, negra=False, alfa=255*k)
    tx(d, (W/2, 300), "¿Cuánto tardan en llegar a 1.500 personas?", 50, alfa=255*ease((C.t - 0.4)/0.4))
    x0, x1 = 420, 1640
    t0 = max(0.6, t_antes - 0.5)
    T = max(1.2, (t_seis - t0)*0.55)
    for m, (et, col, vel) in enumerate((("Falsas", ROJO, 1.0), ("Verdaderas", VERDE, 1/6))):
        y = 430 + m*200
        tx(d, (x0 - 30, y + 45), et, 44, col, anchor="rm")
        d.rounded_rectangle([x0, y, x1, y + 90], radius=45, fill=(30, 36, 70, 255))
        q = min(1.0, max(0.0, (C.t - t0)/T*vel))
        if q > 0:
            d.rounded_rectangle([x0, y, x0 + max(90, (x1 - x0)*q), y + 90], radius=45, fill=tuple(col) + (255,))
        tx(d, (x1 + 30, y + 45), f"{int(1500*q):,}".replace(",", "."), 40, col, anchor="lm")
        if m == 0 and C.cruza(t0 + T):
            C.son("ding", 1.0)
    tx(d, (x1, 395), "meta: 1.500", 28, TENUE, anchor="rm", negra=False, alfa=255*ease((C.t - 0.6)/0.4))
    q = sale((C.t - t_seis)/0.45)
    if q > 0:
        tx(d, (W/2, 870), "la verdad tarda unas 6 VECES más", 60*q + 1, AMARILLO)
        if C.cruza(t_seis):
            C.son("golpe", 0.5)
    return img


def dos(img, C, claves, etiquetas, tr, spr, sonar=True):
    d = None
    for vista, clave, et, m in ((IZQ, claves[0], etiquetas[0], 0), (DER, claves[1], etiquetas[1], 1)):
        vista.enlaces(img, CAM0)
        vista.pulsos(img, CAM0, CASC[clave], tr, COLOR[clave])
        col, brillo, edad = estado([clave], tr, spr)
        grandes = (int(np.where(CASC[clave].cuando == 0)[0][0]),)
        vista.nodos(img, CAM0, col, brillo, edad, grandes=grandes)
        if sonar:
            C.tics(clave, tr, 0.6)
        d = ImageDraw.Draw(img, "RGBA")
        cx = vista.p[:, 0].min()/2 + vista.p[:, 0].max()/2
        tx(d, (cx, 215), et, 40, AMARILLO if m else BLANCO)
        tx(d, (cx, 800), f"{cuantos(clave, tr)}", 92, ROJO)
        tx(d, (cx, 868), "lo han recibido", 30, (205, 214, 240), negra=False)
    d.line([(W/2, 260), (W/2, 900)], fill=(70, 86, 140, 200), width=3)
    tx(d, (W/2, 935), f"hora {int(tr)}", 28, TENUE, negra=False)
    return d


def llega_300(clave):
    r = np.sort(CASC[clave].cuando[CASC[clave].cuando >= 0])
    return int(r[299]) if len(r) >= 300 else None


def e_influencer(img, C, parte):
    if parte == 0:
        t_izq = C.en("izquierda")
        tr = 5*ease((C.t - t_izq)/max(0.5, C.dur - t_izq))
        spr = (C.dur - t_izq)/5
    else:
        tr = 5 + 21*min(1.0, C.t/(C.dur*0.8))
        spr = C.dur*0.8/21
    d = dos(img, C, ("bulo_med", "bulo_inf"), ("Lo lanza una persona normal", "Lo lanza un influencer"), tr, spr)
    for vista, clave in ((IZQ, "bulo_med"), (DER, "bulo_inf")):
        h = llega_300(clave)
        if h is not None and tr >= h:
            cx = vista.p[:, 0].min()/2 + vista.p[:, 0].max()/2
            chip(d, cx, 268, f"llega a 300 personas en la hora {h}", AMARILLO, 30, ease((tr - h)/1.0))
    if parte == 1:
        t_m = C.en("media")
        q = ease((C.t - t_m)/0.4)
        if q > 0:
            caja(d, 560, 380, 1360, 640, alfa=240*q)
            tx(d, (W/2, 430), "De media (60 lanzamientos)", 34, TENUE, negra=False, alfa=255*q)
            tx(d, (760, 520), "471", 90, ROJO, alfa=255*q)
            tx(d, (760, 590), "persona normal", 30, BLANCO, negra=False, alfa=255*q)
            tx(d, (1160, 520), "663", 90, ROJO, alfa=255*q)
            tx(d, (1160, 590), "influencer", 30, AMARILLO, negra=False, alfa=255*q)
            if C.cruza(t_m):
                C.son("ding", 0.8)
    return img


def e_desmentido(img, C):
    t0 = C.en("probemos")
    t_inf = C.en("influencer")
    tr = 24*min(1.0, max(0.0, (C.t - t0)/(C.dur - t0)))
    spr = (C.dur - t0)/24
    grandes = (ORIGEN, INF) if C.t > t_inf else (ORIGEN,)
    red_completa(img, C, ["desm_bulo", "desm"], tr, spr, CAM0, grandes=grandes)
    d = ImageDraw.Draw(img, "RGBA")
    k = ease((C.t - t0)/0.4)
    caja(d, 1400, 60, 1890, 300, alfa=235*k)
    tx(d, (1645, 125), f"Bulo: {cuantos('desm_bulo', tr)}", 58, ROJO, alfa=255*k)
    tx(d, (1645, 200), f"Desmentido: {cuantos('desm', tr)}", 50, AZUL, alfa=255*k)
    tx(d, (1645, 262), f"hora {int(tr)}", 26, TENUE, negra=False, alfa=255*k)
    chip(d, 80, 140, "el desmentido sale 2 horas después", AZUL, 30, k, anchor="lm")
    if C.t > t_inf:
        x, y = GRANDE.p[INF]
        chip(d, x, y - 60, "influencer", AZUL, 28, ease((C.t - t_inf)/0.3)*(1 - ease((C.t - t_inf - 2.5)/0.4)))
    return img


def e_desm_barras(img, C, final=False):
    if not final:
        rv = [C.en("vez"), C.en("dos"), C.en("seis") - 0.6, C.en("seis"), C.en("diez"), 0.3]
    else:
        rv = [-9]*6
    datos = [(f"{h} h" if h else "a la vez", v, AZUL if h <= 2 else ROJO) for h, v in V1.DESMENTIDO] + \
            [("sin desmentido", V1.MEDIA_BULO, (150, 60, 72))]
    dim = ease((C.t - 0.2)/0.4) if final else 0
    d = barras(img, C, "¿A cuánta gente llega el bulo, según cuándo sale el desmentido?", datos, rv,
               nota="horas de retraso del desmentido · personas de cada 1.000", dim=dim)
    if final:
        q = sale((C.t - 0.2)/0.45)
        caja(d, 420, 350, 1500, 600, alfa=240*ease((C.t - 0.2)/0.3))
        tx(d, (W/2, 430), "Solo sirve si llega PRONTO", 88*max(q, 0.01), AMARILLO, borde=8)
        t_casi = C.en("casi")
        q2 = ease((C.t - t_casi)/0.3)
        if q2 > 0:
            tx(d, (W/2, 540), "…y casi nunca llega pronto", 54, BLANCO, borde=6, alfa=255*q2)
        if C.cruza(0.2):
            C.son("golpe", 0.5)
    return img


def movil(d, x0, y0, w, h):
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=50, fill=(24, 26, 32, 255), outline=(90, 94, 106, 255), width=5)
    d.rounded_rectangle([x0 + 16, y0 + 50, x0 + w - 16, y0 + h - 36], radius=24, fill=(240, 242, 245, 255))


def e_whatsapp(img, C):
    t_19, t_5, t_20, t_uno, t_prob = C.en("2019"), C.en("cinco"), C.en("2020"), C.en("uno", exacta=True), C.en("probarlo")
    kd = ease((C.t - t_prob - 0.4)/0.5)
    if kd < 1:
        d = ImageDraw.Draw(img, "RGBA")
        x0, y0, w, h = 260, 90, 470, 820
        movil(d, x0, y0, w, h)
        fase2 = C.t >= t_20
        tx(d, (x0 + 46, y0 + 100), "Reenviar a…", 36, (30, 30, 30), anchor="lm")
        chats = ["Familia", "Trabajo", "Amigos", "Vecinos", "Clase 2ºB", "Pádel", "Primos", "Comunidad"]
        maximo = 1 if fase2 else 5
        t_ini = t_19 + 0.3 if not fase2 else t_20 + 0.3
        t_lim = t_5 if not fase2 else t_uno
        marcados = int(max(0, min(len(chats), (C.t - t_ini)/max(0.2, (t_lim - t_ini))*(maximo + 1)))) if C.t > t_ini else 0
        for m, s in enumerate(chats):
            y = y0 + 170 + m*82
            d.ellipse([x0 + 40, y - 26, x0 + 92, y + 26], fill=(180, 190, 200, 255))
            tx(d, (x0 + 112, y), s, 32, (30, 30, 30), anchor="lm", negra=False)
            on = m < min(marcados, maximo)
            bx = x0 + w - 80
            d.ellipse([bx - 20, y - 20, bx + 20, y + 20], fill=((37, 180, 100) if on else (255, 255, 255)) + (255,),
                      outline=(150, 160, 170, 255), width=3)
            if on:
                check(d, bx, y, 10, (255, 255, 255), 4)
        if marcados > maximo:
            ka = ease((C.t - t_lim)/0.3)
            d.rounded_rectangle([x0 + 30, y0 + h - 200, x0 + w - 30, y0 + h - 70], radius=20, fill=(40, 40, 46, int(240*ka)))
            tx(d, (x0 + w/2, y0 + h - 158), "Solo puedes reenviar", 30, (255, 255, 255), negra=False, alfa=255*ka)
            tx(d, (x0 + w/2, y0 + h - 112), f"a {maximo} chat{'s' if maximo > 1 else ''}", 36, (255, 255, 255), alfa=255*ka)
        for m, (t_, ano, s, col) in enumerate(((t_19, "2019", "máximo 5 chats a la vez", AMARILLO),
                                               (t_20, "2020", "los muy reenviados: 1 chat", ROJO))):
            q = ease((C.t - t_)/0.4)
            if q > 0:
                y = 330 + m*260
                tx(d, (900 - 40*(1 - q), y), ano, 110, col, anchor="lm", alfa=255*q)
                tx(d, (900 - 40*(1 - q), y + 95), s, 50, BLANCO, anchor="lm", alfa=255*q)
                if C.cruza(t_):
                    C.son("whoosh", 0.7)
        tx(d, (900, 840), "límites reales de WhatsApp", 30, TENUE, anchor="lm", negra=False)
        if kd > 0:
            velo = Image.new("RGBA", (W, H), (7, 9, 22, int(255*kd)))
            img.paste(velo, (0, 0), velo)
    if kd > 0:
        t0 = t_prob + 0.4
        tr = 26*min(1.0, max(0.0, (C.t - t0)/(C.dur - t0)))
        spr = (C.dur - t0)/26
        capa = BASE.copy()
        dos(capa, C, ("bulo", "bulo_lim"), ("Sin límite", "Como mucho, a 5 contactos"), tr, spr)
        img = Image.blend(img, capa, kd)
    return img


def e_limite_barras(img, C):
    t_470, t_doc, t_vida, t_grupo, t_cont = C.en("cuatrocientas"), C.en("docena"), C.en("vida"), C.en("grupo"), C.en("conto")
    datos = [(et, v, ROJO if v > 200 else (AMARILLO if v > 100 else VERDE)) for et, v in V1.LIMITE]
    rv = [t_470, t_doc + 0.9, t_doc, t_doc + 1.6]
    dim = ease((C.t - t_vida)/0.4)
    d = barras(img, C, "¿A cuánta gente llega el bulo, con un límite de reenvíos?", datos, rv, dim=dim,
               nota="en mi red · personas de cada 1.000")
    if dim > 0:
        caja(d, 260, 300, 1660, 740, alfa=240*dim)
        tx(d, (W/2, 370), "En la vida real, el efecto es menor:", 46, BLANCO, alfa=255*dim)
        q = ease((C.t - t_grupo)/0.8)
        tx(d, (W/2, 440), "un chat puede ser un grupo enorme", 40, TENUE, negra=False, alfa=255*dim)
        rnd = np.random.default_rng(2)
        for m in range(200):
            if q*200 > m:
                x = 640 + (m % 40)*16 + rnd.uniform(-2, 2)
                y = 500 + (m//40)*22
                d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=AMARILLO + (int(230*dim),))
        if q > 0:
            tx(d, (1340, 545), "1 chat =", 34, BLANCO, anchor="lm", alfa=255*dim)
            tx(d, (1340, 590), "200 personas", 34, AMARILLO, anchor="lm", alfa=255*dim)
        kc = ease((C.t - t_cont)/0.4)
        if kc > 0:
            tx(d, (W/2, 680), "WhatsApp: los mensajes muy reenviados bajaron un 70%", 40, VERDE, alfa=255*kc)
            if C.cruza(t_cont):
                C.son("ding", 0.8)
    return img


def escudo(d, x, y, s, col, alfa=255):
    pts = [(x, y - s), (x + s*0.85, y - s*0.65), (x + s*0.75, y + s*0.25), (x, y + s), (x - s*0.75, y + s*0.25), (x - s*0.85, y - s*0.65)]
    d.polygon(pts, fill=tuple(col) + (int(alfa),))
    check(d, x, y, s*0.4, (14, 18, 40), max(3, int(s/8)))


def e_vacuna(img, C):
    t_vamos, t_blancos = C.en("vamos"), C.en("blancos")
    t_juegos, t_cae = C.en("juegos"), C.en("cae")
    kn = ease((C.t - t_vamos + 0.3)/0.5)
    if kn < 1:
        d = ImageDraw.Draw(img, "RGBA")
        a = 1 - kn
        q = sale(C.t/0.5)
        escudo(d, W/2, 330, 120*max(q, 0.01), VACUNADO, 255*a)
        tx(d, (W/2, 520), "«Vacunarse» contra los bulos", 70, BLANCO, alfa=255*a*ease(C.t/0.4))
        tx(d, (W/2, 620), "Juegos que te enseñan los trucos de los bulos", 44, AMARILLO, alfa=255*a*ease((C.t - t_juegos)/0.4))
        tx(d, (W/2, 700), "quien juega, luego cae bastante menos", 40, TENUE, negra=False, alfa=255*a*ease((C.t - t_cae)/0.4))
        if C.cruza(t_juegos):
            C.son("pop", 0.8)
    if kn > 0:
        capa = BASE.copy()
        t0 = t_blancos + 0.3
        tr = 26*min(1.0, max(0.0, (C.t - t0)/max(0.5, C.dur - t0)))
        spr = max(0.5, C.dur - t0)/26
        va = ease((C.t - t_vamos)/1.2)
        red_completa(capa, C, ["bulo_vac"], tr, spr, CAM0, vac_alfa=va)
        d = ImageDraw.Draw(capa, "RGBA")
        contador(d, cuantos("bulo_vac", tr), ROJO, hora=int(tr))
        chip(d, 80, 140, "30% vacunados: no lo reenvían", VACUNADO, 30, va, anchor="lm")
        if C.cruza(t_vamos):
            C.son("whoosh", 0.7)
        img = Image.blend(img, capa, kn) if kn < 1 else capa
    return img


def e_vac_barras(img, C):
    t10, t30, t40, t_prot = C.en("diez"), C.en("treinta"), C.en("cuarenta"), C.en("proteger")
    datos = [("nadie" if p == 0 else f"{p}% vacunados", v, ROJO if v > 200 else (AMARILLO if v > 100 else VERDE)) for p, v in V1.VACUNA]
    d = barras(img, C, "¿A cuánta gente llega el bulo, si una parte está «vacunada»?", datos, [0.3, t10, t30 - 0.7, t30, t40])
    q = ease((C.t - t_prot)/0.4)
    if q > 0:
        chip(d, W/2, 900, "protege también a los que no están vacunados", AMARILLO, 32, q)
    return img


def e_duda(img, C):
    t_diez, t_esto = C.en("diez"), C.en("esto")
    tr = 26*min(1.0, C.t/(C.dur*0.9))
    spr = C.dur*0.9/26
    d = dos(img, C, ("bulo", "bulo_duda"), ("Todos reenvían sin pensar", "Todos dudan un poco: 30% menos"), tr, spr)
    q = sale((C.t - t_diez)/0.4)
    if q > 0:
        x, y, r = 1430, 560, 70*q
        d.ellipse([x - r, y - r, x + r, y + r], fill=(14, 18, 40, 230), outline=AMARILLO + (255,), width=5)
        tx(d, (x, y), "10 s", int(44*q) + 1, AMARILLO)
    q2 = ease((C.t - t_esto)/0.3)
    if q2 > 0:
        chip(d, 1430, 680, "¿Esto será verdad?", BLANCO, 34, q2)
        if C.cruza(t_esto):
            C.son("pop", 0.8)
    return img


def e_duda_barras(img, C):
    t470, t140, t100, t_apaga = C.en("cuatrocientas"), C.en("ciento"), C.en("cien", exacta=True), C.en("apaga")
    datos = [("sin dudar" if p == 0 else f"{p}% menos", v, ROJO if v > 200 else (VERDE if v < 100 else AMARILLO)) for p, v in V1.DUDA]
    d = barras(img, C, "¿A cuánta gente llega el bulo, si dudamos antes de reenviar?", datos,
               [t470, t140 - 0.7, t140, t100, t100 + 0.7], nota="cuánto menos reenvía cada persona · personas de cada 1.000")
    q = sale((C.t - t_apaga)/0.4)
    if q > 0:
        tx(d, (1450, 380), "…y se apaga solo", 60*q + 1, VERDE, borde=6)
        if C.cruza(t_apaga):
            C.son("ding", 1.0)
    return img


def e_leccion(img, C):
    t_ind, t_sor, t_tipo, t_esp, t_apaga = C.en("indigne"), C.en("sorprenda"), C.en("tipo"), C.en("espera"), C.en("tu", exacta=True)
    tr = 20*min(1.0, C.t/(C.dur*0.9))
    spr = C.dur*0.9/20
    red_completa(img, C, ["bulo_duda"], tr, spr, CAM0)
    velo = Image.new("RGBA", (W, H), OSCURO + (int(150*ease((C.t - t_esp + 0.3)/0.5)),))
    img.paste(velo, (0, 0), velo)
    d = ImageDraw.Draw(img, "RGBA")
    for t_, s, x in ((t_ind, "TE INDIGNA", 700), (t_sor, "TE SORPRENDE", 1220)):
        q = ease((C.t - t_)/0.3)*(1 - ease((C.t - t_esp + 0.3)/0.4))
        if q > 0:
            chip(d, x, 160, s, AMARILLO, 40, q)
            if C.cruza(t_):
                C.son("pop", 0.7)
    q = ease((C.t - t_tipo)/0.3)*(1 - ease((C.t - t_esp + 0.3)/0.4))
    if q > 0:
        tx(d, (W/2, 250), "= lo que más se reenvía", 44, BLANCO, borde=6, alfa=255*q)
    k = ease((C.t - t_esp)/0.4)
    if k > 0:
        x, y, r = W/2, 430, 110
        d.ellipse([x - r, y - r, x + r, y + r], outline=(60, 70, 110, int(255*k)), width=14)
        frac = min(1.0, (C.t - t_esp)/max(1.0, C.dur - t_esp - 0.5))
        d.arc([x - r, y - r, x + r, y + r], -90, -90 + 360*(1 - frac), fill=AMARILLO + (int(255*k),), width=14)
        tx(d, (x, y), "10 s", 64, AMARILLO, alfa=255*k)
        tx(d, (W/2, 620), "Espera 10 segundos.", 80, BLANCO, borde=8, alfa=255*k)
        if C.cruza(t_esp):
            C.son("ding", 0.9)
    q = ease((C.t - t_apaga)/0.4)
    if q > 0:
        tx(d, (W/2, 730), "A lo mejor eres tú quien lo apaga.", 54, VERDE, borde=6, alfa=255*q)
    return img


def e_final(img, C):
    cam = (W/2 + 30*math.sin(C.t/7), H/2, 1.0 + 0.04*C.t/C.dur)
    red_completa(img, C, [], 0, 1, limita(cam), sonar=False)
    rnd = np.random.default_rng(int(C.t*2))
    d = ImageDraw.Draw(img, "RGBA")
    xy = GRANDE.xy(limita(cam))
    for j in rnd.choice(RED.n, 25, replace=False):
        x, y = xy[j]
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(AMARILLO if j % 2 else AZUL) + (200,))
    velo = Image.new("RGBA", (W, H), OSCURO + (175,))
    img.paste(velo, (0, 0), velo)
    d = ImageDraw.Draw(img, "RGBA")
    k = ease(C.t/0.5)
    f = F(92)
    w1 = d.textlength("LO HE ", font=f)
    d.text((140, 200), "LO HE ", font=f, fill=BLANCO + (int(255*k),), anchor="lm")
    d.text((140 + w1, 200), "SIMULADO", font=f, fill=AMARILLO + (int(255*k),), anchor="lm")
    tx(d, (140, 360), "¿Qué simulo", 70, BLANCO, anchor="lm", alfa=255*ease((C.t - 0.3)/0.4))
    tx(d, (140, 445), "en el próximo vídeo?", 70, BLANCO, anchor="lm", alfa=255*ease((C.t - 0.5)/0.4))
    tx(d, (140, 545), "Déjamelo en los comentarios", 44, AMARILLO, anchor="lm", negra=False, alfa=255*ease((C.t - 0.9)/0.4))
    kf = ease((C.t - C.voz - 0.2)/0.6)
    if kf > 0:
        d.rounded_rectangle([1060, 180, 1800, 596], radius=18, outline=(255, 255, 255, int(110*kf)), width=3)
        tx(d, (1430, 388), "siguiente vídeo", 34, TENUE, negra=False, alfa=200*kf)
        d.ellipse([1290, 660, 1570, 940], outline=(255, 255, 255, int(110*kf)), width=3)
        tx(d, (1430, 800), "suscríbete", 34, TENUE, negra=False, alfa=200*kf)
    return img


VISTAS = {0: e_gancho, AVANCE: e_avance, 1: e_pregunta, 2: e_red, 3: e_influencers, 4: e_regla,
          5: lambda i, c: e_verdad(i, c, 0), 6: lambda i, c: e_verdad(i, c, 1), 7: e_mit,
          8: lambda i, c: e_bulo(i, c, 0), 9: lambda i, c: e_bulo(i, c, 1), 10: e_media, 11: e_critico,
          12: e_carrera, 13: lambda i, c: e_influencer(i, c, 0), 14: lambda i, c: e_influencer(i, c, 1),
          15: e_desmentido, 16: e_desm_barras, 17: lambda i, c: e_desm_barras(i, c, True), 18: e_whatsapp,
          19: e_limite_barras, 20: e_vacuna, 21: e_vac_barras, 22: e_duda, 23: e_duda_barras, 24: e_leccion,
          25: e_final}

# ---------------------------------------------------------------- capas comunes


def lineas_sub(pal):
    out, cur = [], []
    for p in pal:
        cur.append(p)
        largo = sum(len(x[0]) + 1 for x in cur)
        if (re.search(r"[.,:;!?…]$", p[0]) and len(cur) >= 2) or largo > 40:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def subtitulo(img, filas, t):
    fila = None
    for k, f in enumerate(filas):
        ini = f[0][1] - 0.12
        fin = filas[k + 1][0][1] - 0.12 if k + 1 < len(filas) else f[-1][2] + 0.5
        if ini <= t < fin:
            fila = f
            break
    if fila is None:
        return
    d = ImageDraw.Draw(img, "RGBA")
    f = F(46)
    anchos = [d.textlength(p + " ", font=f) for p, _, _ in fila]
    x = W/2 - (sum(anchos) - d.textlength(" ", font=f))/2
    for (p, a, b), w in zip(fila, anchos):
        col = AMARILLO if a <= t < b + 0.05 else BLANCO
        d.text((x, 1022), p, font=f, fill=col + (255,), anchor="lm", stroke_width=7, stroke_fill=OSCURO + (255,))
        x += w


def capitulo(img, i, t):
    if not isinstance(i, int):
        return
    claves = [k for k in CAPITULO if k <= i]
    if not claves:
        return
    k = max(claves)
    s = CAPITULO[k]
    if s is None:
        return
    d = ImageDraw.Draw(img, "RGBA")
    q = ease((t - 0.1)/0.5) if k == i else 1.0
    if q <= 0:
        return
    f = F(26)
    w = d.textlength(s, font=f)
    x = 40 - 60*(1 - q)
    d.rounded_rectangle([x, 34, x + w + 44, 84], radius=25, fill=(14, 18, 40, int(225*q)), outline=AMARILLO + (int(255*q),), width=2)
    d.text((x + 22, 59), s, font=f, fill=AMARILLO + (int(255*q),), anchor="lm")

# ---------------------------------------------------------------- render


def render_segmento(args):
    n, salida = args
    sg = SEGS[n]
    C = Ctx(sg["vista"], sg["dur"], sg["pal"], sg["t0"], sg["voz"])
    filas = lineas_sub(sg["pal"])
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                           "-pix_fmt", "yuv420p", salida], stdin=subprocess.PIPE)
    i = sg["vista"]
    for fr in range(sg["frames"]):
        t = fr/FPS
        C.t = t
        img = BASE.copy()
        img = VISTAS[i](img, C)
        capitulo(img, i, t)
        if not SIN_SUBS:
            subtitulo(img, filas, t)
        if i not in SIGUE and n > 0 and t < 0.25:
            velo = Image.new("RGBA", (W, H), OSCURO + (int(200*(1 - t/0.25)),))
            img.paste(velo, (0, 0), velo)
        ff.stdin.write(img.tobytes())
    ff.stdin.close()
    ff.wait()
    print(f"segmento {n + 1}/{len(SEGS)} listo ({sg['dur']:.1f}s)", flush=True)
    return C.eventos


def foto(n, t):
    sg = SEGS[n]
    C = Ctx(sg["vista"], sg["dur"], sg["pal"], sg["t0"], sg["voz"])
    C.t = t
    img = VISTAS[sg["vista"]](BASE.copy(), C)
    capitulo(img, sg["vista"], t)
    subtitulo(img, lineas_sub(sg["pal"]), t)
    return img


def mezcla(total, voz, eventos):
    pista = np.zeros(int((total + 1)*SN.SR), np.float32)
    v = np.zeros_like(pista)
    v[:min(len(voz), len(v))] = voz[:len(v)]
    musi = SN.musica(total + 1, bpm=92, alegre=False)[:len(pista)]
    musi = np.pad(musi, (0, len(pista) - len(musi)))
    env = np.convolve(np.abs(v), np.ones(int(0.3*SN.SR))/int(0.3*SN.SR), mode="same")
    duck = 0.16 - 0.10*np.clip(env*10, 0, 1)
    tt = np.arange(len(pista))/SN.SR
    duck *= np.clip(tt/1.5, 0, 1)
    duck = np.where(tt > total - COLA, duck*1.5, duck)
    duck *= np.clip((total + 0.5 - tt)/2.5, 0, 1)
    efectos = np.zeros_like(pista)
    rnd = np.random.default_rng(7)
    for t, tipo, vol in eventos:
        s = {"tic": lambda: SN.tic(rnd, 0.05*math.sqrt(vol)), "ding": lambda: SN.ding(rnd.choice([1046.5, 1174.7, 1318.5]), 0.5*vol),
             "pop": lambda: SN.pop(0.55*vol), "golpe": lambda: SN.golpe(0.7*vol), "whoosh": lambda: SN.whoosh(vol=0.8*vol)}.get(tipo)
        if s:
            SN.suma(efectos, s(), t)
    for k, sg in enumerate(SEGS):
        if k and sg["vista"] not in SIGUE:
            SN.suma(efectos, SN.whoosh(vol=0.5), sg["t0"] - 0.15)
    return np.tanh((v + musi*duck + efectos)*1.1)*0.92


def main():
    global RED, CASC, ORIGEN, INF, GRANDE, IZQ, DER, BASE, PRIMO, SEGS
    ap = argparse.ArgumentParser()
    ap.add_argument("salida")
    ap.add_argument("--audio", required=True)
    ap.add_argument("--duraciones", required=True)
    ap.add_argument("--segmentos", default="")
    ap.add_argument("--fotos", default="")
    ap.add_argument("--tiempos", default="0.3,0.6,0.9")
    ap.add_argument("--procesos", type=int, default=4)
    ap.add_argument("--sin-subtitulos", action="store_true", help="para recortar trozos (el Short de los bulos)")
    args = ap.parse_args()
    global SIN_SUBS
    SIN_SUBS = args.sin_subtitulos

    RED, CASC, ORIGEN, INF = prepara()
    BASE = fondo()
    GRANDE = Vista(RED, 110, 80, 1700, 6.5)
    IZQ = Vista(RED, 50, 300, 880, 4.2)
    DER = Vista(RED, 990, 300, 880, 4.2)
    cerca = [e for e in np.where(GRANDE.lejano)[0]
             if min(np.hypot(*(GRANDE.p[GRANDE.ea[e]] - GRANDE.p[ORIGEN])), np.hypot(*(GRANDE.p[GRANDE.eb[e]] - GRANDE.p[ORIGEN]))) < 260]
    PRIMO = max(cerca, key=lambda e: GRANDE.largo[e]) if cerca else int(np.argmax(GRANDE.largo*GRANDE.lejano))

    info = json.loads(Path(args.duraciones).read_text())
    assert len(info["duraciones"]) == 26
    crudo = subprocess.run(["ffmpeg", "-v", "error", "-i", args.audio, "-f", "f32le", "-ac", "1", "-ar", str(SN.SR), "-"],
                           capture_output=True, check=True).stdout
    narr = np.frombuffer(crudo, np.float32).copy()
    narr /= max(1e-6, np.abs(narr).max())/0.9
    durs = list(info["duraciones"])
    textos = info["textos"]
    ini = list(np.cumsum([0] + durs[:-1]))

    def trozo(a, b):
        return narr[int(a*SN.SR):int(b*SN.SR)]

    # el avance: la ultima frase de la escena 10, tal cual la dijo ella
    p10 = alinear(textos[10], trozo(ini[10], ini[10] + durs[10]), SN.SR)
    k_con = next(k for k, (p, _, _) in enumerate(p10) if norm(p) == "con")
    a_av = max(0.0, p10[k_con][1] - 0.12)
    texto_av = " ".join(p for p, _, _ in p10[k_con:])
    orden = [(0, ini[0], durs[0], textos[0]),
             (AVANCE, ini[10] + a_av, durs[10] - a_av + 0.5, texto_av)] + \
            [(k, ini[k], durs[k], textos[k]) for k in range(1, 26)]
    SEGS = []
    t0 = 0.0
    voz = []
    for vista, a, dv, texto in orden:
        audio = trozo(a, a + dv)
        if vista == AVANCE:
            fin_voz = (p10[-1][2] - a_av) + 0.1
            audio = audio[:int(fin_voz*SN.SR)]
            audio = np.concatenate([audio*np.clip((fin_voz - np.arange(len(audio))/SN.SR)/0.08, 0, 1),
                                    np.zeros(int((dv - fin_voz)*SN.SR), np.float32)])
        pal = alinear(texto, audio, SN.SR)
        dur = dv + (COLA if vista == 25 else 0.0)
        SEGS.append(dict(vista=vista, t0=t0, dur=dur, voz=dv, pal=pal))
        voz.append(audio)
        t0 += dv
    voz = np.concatenate(voz)
    total = t0 + COLA
    fr = [int(round(s["t0"]*FPS)) for s in SEGS] + [int(round(total*FPS))]
    for k, s in enumerate(SEGS):
        s["frames"] = fr[k + 1] - fr[k]
    print("capítulos:", [(s["vista"], f"{int(s['t0'])//60}:{int(s['t0']) % 60:02d}") for s in SEGS], flush=True)
    cuales = [int(x) for x in args.segmentos.split(",")] if args.segmentos else list(range(len(SEGS)))

    if args.fotos:
        ts = [float(x) for x in args.tiempos.split(",")]
        fotos = [foto(n, f*SEGS[n]["voz"]).resize((640, 360), Image.LANCZOS) for n in cuales for f in ts]
        cols = len(ts)
        hoja = Image.new("RGB", (640*cols, 360*((len(fotos) + cols - 1)//cols)), "white")
        for k, f in enumerate(fotos):
            hoja.paste(f, ((k % cols)*640, (k//cols)*360))
        hoja.save(args.fotos)
        return

    tmp = Path(tempfile.mkdtemp(prefix="bulos_v3_"))
    trabajos = sorted([(n, str(tmp/f"seg{n:02d}.mp4")) for n in cuales], key=lambda x: -SEGS[x[0]]["dur"])
    print(f"duración: {total/60:.2f} min; {len(trabajos)} segmentos en {args.procesos} procesos", flush=True)
    with mp.get_context("fork").Pool(args.procesos) as pool:
        listas = pool.map(render_segmento, trabajos, chunksize=1)
    eventos = [ev for lst in listas for ev in lst]
    trabajos.sort()
    (tmp/"lista.txt").write_text("".join(f"file '{p}'\n" for _, p in trabajos))
    if len(cuales) == len(SEGS):
        pista = mezcla(total, voz, eventos)
    else:
        pista = np.concatenate([np.pad(voz[int(SEGS[n]["t0"]*SN.SR):int((SEGS[n]["t0"] + SEGS[n]["voz"])*SN.SR)],
                                       (0, int((SEGS[n]["dur"] - SEGS[n]["voz"])*SN.SR))) for n in cuales])
    wav = tmp/"pista.wav"
    with wave.open(str(wav), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SN.SR)
        f.writeframes((np.clip(pista, -1, 1)*32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp/"lista.txt"),
                    "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", args.salida], check=True)
    print(f"hecho: {args.salida}", flush=True)


RED = CASC = ORIGEN = INF = GRANDE = IZQ = DER = BASE = PRIMO = SEGS = None
SIN_SUBS = False

if __name__ == "__main__":
    main()
