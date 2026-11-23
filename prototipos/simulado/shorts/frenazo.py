"""Short: ¿Qué pasaría si frenas 1 segundo en la autopista?

Simulacion: trafico.py (modelo de velocidad optima, Bando 1995), 22 coches en
un anillo de 230 m como el experimento de Sugiyama (Japon, 2008), sin
frenazos al azar. En el segundo 10, UN coche frena (4 m/s2) durante 1 segundo. Con 22
coches la ola de frenazos no se va (5 minutos despues sigue); con 18, el
mismo frenazo se deshace solo.
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from trafico import LARGO_COCHE, Anillo  # noqa: E402

from estilo import (AMARILLO, BLANCO, OSCURO, ROJO, TENUE, VERDE, agente, brillo, ease, etiqueta, sale, titular,
                    tx)  # noqa: E402

ALEGRE = False
DT, CADA, FIN = 0.05, 2, 340.0


def corre(n):
    a = Anillo(n, ruido=0.0, semilla=1, frenazo=4.0)    # un frenazo firme de 1 s (4 m/s2)
    a.x = np.arange(n)*a.L/n
    a.v[:] = a.v_optima(a.L/n - LARGO_COCHE)
    xs, vs = [], []
    for k in range(int(FIN/DT)):
        if 10 <= a.t < 11:
            a.freno_hasta[0] = a.t + DT
        a.paso(DT)
        if k % CADA == 0:
            xs.append(a.x.copy())
            vs.append(a.v.copy())
    return np.array(xs), np.array(vs), a.L


def prepara(C):
    global S22, S18
    S22, S18 = corre(22), corre(18)
    for nombre, (xs, vs, L) in (("22", S22), ("18", S18)):
        print(f"frenazo {nombre}: parados a los 5 min {(vs[int(300/0.1)] < 0.5).sum()}, "
              f"v media final {vs[-300:].mean()*3.6:.0f} km/h", flush=True)


def estado(sim, ts):
    xs, vs, L = sim
    i = min(len(xs) - 1, max(0, int(ts/(DT*CADA))))
    return xs[i], vs[i], L


def color_v(v):
    if v > 7:
        return VERDE
    if v > 3:
        return AMARILLO
    return ROJO


def anillo(img, C, sim, ts, cx=540, cy=980, R=330, coche=22, tu=True, cara="normal", frenando=False):
    x, v, L = estado(sim, ts)
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([cx - R - 46, cy - R - 46, cx + R + 46, cy + R + 46], outline=(52, 60, 100, 255), width=92)
    for k in range(24):
        a = k*2*math.pi/24
        d.line([(cx + R*math.cos(a), cy + R*math.sin(a)), (cx + R*math.cos(a + 0.12), cy + R*math.sin(a + 0.12))],
               fill=(140, 150, 190, 150), width=3)
    pos = []
    for i in range(len(x)):
        ang = -math.pi/2 + x[i]/L*2*math.pi
        pos.append((cx + R*math.cos(ang), cy + R*math.sin(ang)))
    rojos = [(px, py, coche*0.8) for (px, py), vv in zip(pos, v) if vv < 3]
    brillo(img, rojos, 2.0, ROJO, 0.8)
    d = ImageDraw.Draw(img, "RGBA")
    for i, ((px, py), vv) in enumerate(zip(pos, v)):
        if tu and i == 0:
            continue
        d.rounded_rectangle([px - coche, py - coche, px + coche, py + coche], radius=coche*0.4, fill=color_v(vv) + (255,),
                            outline=OSCURO + (255,), width=3)
    if tu:
        px, py = pos[0]
        if frenando:
            brillo(img, [(px, py, 40)], 3.0, ROJO, 1.0)
        agente(img, px, py - 8, 40, cara, C.t, sombra=False)
    return pos


def ts_de(C, t):
    """El reloj de la simulacion, ajustado a la voz: el frenazo (segundo 10)
    cae justo cuando ella dice «frena»."""
    I = C.ini
    tf = C.en(2, "frena")
    pts = [(0.0, 0.0), (tf, 10.0), (tf + 1.2, 11.0), (I[3], 12.0), (I[4], 62.0), (I[5], 300.0), (I[5] + 60, 360.0)]
    xs, ys = zip(*pts)
    return float(np.interp(t, xs, ys))


def dibuja(img, C):
    e, t, I = C.esc, C.t, C.ini
    ts = ts_de(C, t)
    if e <= 4 or e == 6:
        frenando = 10 <= ts < 11
        _, v, _ = estado(S22, ts)
        cara = "susto" if frenando or (e >= 3 and v.min() < 1) else "normal"
        anillo(img, C, S22, ts, cara=cara, frenando=frenando)
        d = ImageDraw.Draw(img, "RGBA")
    if e == 0:
        titular(img, [[("¿Qué pasaría si", BLANCO)], [("frenas ", BLANCO), ("1 segundo", AMARILLO)],
                      [("en la autopista?", BLANCO)]], 170, 104)
    elif e == 1:
        tx(d, (540, 300), "22 coches", 96, BLANCO, borde=8)
        tx(d, (540, 400), "todos a la misma velocidad", 50, TENUE, borde=4)
        tj = C.en(1, "japon")
        if t > tj:
            etiqueta(img, 540, 1450 - 120, "como el experimento real · Japón, 2008", AMARILLO, 36, ease((t - tj)/0.3))
            if C.cruza(tj):
                C.son("pop", 0.6)
    elif e == 2:
        tf = C.en(2, "frena")
        if t > tf:
            q = sale((t - tf)/0.3)
            tx(d, (540, 330), "¡FRENA 1 SEGUNDO!", int(84*max(q, 0.05)), ROJO, borde=8)
            if C.cruza(tf):
                C.son("golpe", 0.7)
        tx(d, (540, 980), "solo uno", 56, BLANCO, borde=6, alfa=255*ease((t - C.en(2, "solo"))/0.3))
    elif e == 3:
        tx(d, (540, 300), "y el de detrás", 70, BLANCO, borde=8)
        tx(d, (540, 390), "frena un poco más…", 70, BLANCO, borde=8, alfa=255*ease((t - C.en(3, "siguiente"))/0.3))
        for k, (pal, s) in enumerate((("accidente", "sin accidente"), ("obras", "sin obras"), ("nada", "sin nada"))):
            tw = C.en(3, pal)
            if t > tw:
                etiqueta(img, 540, 880 + k*100, s, ROJO, 46, ease((t - tw)/0.25))
                if C.cruza(tw):
                    C.son("pop", 0.6)
        if C.cruza(I[3] + 1.0):
            C.son("whoosh", 0.5)
    elif e == 4:
        m, s = divmod(int(ts), 60)
        tx(d, (540, 300), f"{m}:{s:02d}", 130, BLANCO, borde=10)
        tx(d, (540, 410), "minutos después", 50, TENUE, borde=4)
        tx(d, (540, 980), "sigue ahí", 70, ROJO, borde=8, alfa=255*ease((t - C.en(4, "sigue"))/0.3))
    elif e == 5:
        t18, t22 = C.en(5, "dieciocho"), C.en(5, "veintidos")
        for k, (sim, n, tw, cx) in enumerate(((S18, 18, t18, 280), (S22, 22, t22, 800))):
            q = ease((t - tw + 0.3)/0.4)
            if q <= 0:
                continue
            anillo(img, C, sim, 300 + (t - I[5])*3, cx=cx, cy=1000, R=190, coche=14, tu=(n == 22), cara="susto")
            d = ImageDraw.Draw(img, "RGBA")
            tx(d, (cx, 690), f"{n} coches", 60, BLANCO, borde=6)
            ok = n == 18
            tx(d, (cx, 1310), "se arregla solo" if ok else "el atasco no se va", 40, VERDE if ok else ROJO, borde=4)
            if C.cruza(tw):
                C.son("ding", 0.7)
        d = ImageDraw.Draw(img, "RGBA")
        tx(d, (540, 330), "El mismo frenazo:", 74, BLANCO, borde=8)
    elif e == 6:
        q = ease((t - I[6])/0.3)
        tx(d, (540, 280), "Carretera llena", 80, BLANCO, borde=8, alfa=255*q)
        tx(d, (540, 380), "+ un frenazo de nada", 66, AMARILLO, borde=8, alfa=255*q)
        tx(d, (540, 480), "= ATASCO", 90, ROJO, borde=8, alfa=255*ease((t - C.en(6, "atasco"))/0.3))
    return img
