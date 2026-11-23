"""Short: ¿Dos en tu clase cumplen el mismo día? (la paradoja del cumpleaños)

Simulacion: 10.000 clases de 23 con cumpleaños al azar (365 dias). Sale
~50,7 %, que es lo que da la cuenta exacta. Con 30, ~70,6 %; con 41, ~90,3 %.
"""
import math

import numpy as np
from PIL import ImageDraw

from estilo import (AMARILLO, BLANCO, OSCURO, PUNTO, ROJO, TENUE, VERDE, W, agente, brillo, ease, etiqueta, punto,
                    sale, titular, tx)

ALEGRE = True
N_CLASES = 10000
ASIENTOS = [(220 + c*160, 720 + f*150) for f in range(5) for c in range(5)]
ASIENTOS = ASIENTOS[:12] + ASIENTOS[13:24]          # 23 sitios; el centro (12) es "tú"
YO = (540, 1020)
PAREJA = (2, 17)                                     # los dos que coinciden en la clase de ejemplo


def prepara(C):
    rnd = np.random.default_rng(23)
    global REPITE, PCT, MINI
    clases = rnd.integers(0, 365, (N_CLASES, 23))
    REPITE = np.array([len(set(c)) < 23 for c in clases])
    PCT = REPITE.mean()*100
    MINI = REPITE[:120]
    print(f"cumple: {PCT:.1f}% de {N_CLASES} clases", flush=True)


def clase(img, C, k_aparece=1.0, dim=1.0, pareja=False, cara="normal"):
    d = ImageDraw.Draw(img, "RGBA")
    for n, (x, y) in enumerate(ASIENTOS):
        q = ease(k_aparece*24 - n)
        if q <= 0:
            continue
        col = ROJO if (pareja and n in PAREJA) else PUNTO
        if pareja and n in PAREJA:
            brillo(img, [(x, y, 34)], 2.2, ROJO, 0.9)
            d = ImageDraw.Draw(img, "RGBA")
        punto(d, x, y, 34*sale(q), col, 255*dim)
    agente(img, YO[0], YO[1] - 10, 58, cara, C.t, alfa=int(255*dim))


def dibuja(img, C):
    e, t = C.esc, C.t
    I = C.ini
    if e == 0:
        k = (t - 0.15)/1.3
        clase(img, C, k)
        for n in range(23):
            if C.cruza(0.15 + n*1.3/24):
                C.son("pop", 0.25)
        etiqueta(img, YO[0] + 150, YO[1] - 110, "tú", AMARILLO, 46, ease((t - 1.4)/0.3), flecha_a=(YO[0] + 50, YO[1] - 50))
        titular(img, [[("En tu clase", BLANCO)], [("sois ", BLANCO), ("23", AMARILLO), (".", BLANCO)],
                      [("¿Dos cumplen", BLANCO)], [("el mismo día?", BLANCO)]], 170, 108)
    elif e == 1:
        clase(img, C, 1.0, dim=0.25)
        tp, t365 = C.en(1, "poquisima"), C.en(1, "trescientos")
        agente(img, 540, 1030, 130, "pensando" if t < tp else "normal", t, "cadera")
        if t >= tp:
            etiqueta(img, 540, 760, "«¡Poquísima!»", BLANCO, 64, ease((t - tp)/0.25))
            if C.cruza(tp):
                C.son("pop", 0.8)
        q = sale((t - t365)/0.35)
        if q > 0:
            d = ImageDraw.Draw(img, "RGBA")
            d.rounded_rectangle([290, 230, 790, 560], radius=36, fill=(240, 242, 248, 255), outline=OSCURO + (255,), width=6)
            d.rounded_rectangle([290, 230, 790, 330], radius=36, fill=ROJO + (255,))
            d.rectangle([290, 300, 790, 330], fill=ROJO + (255,))
            tx(d, (540, 280), "1 AÑO", 52, BLANCO)
            tx(d, (540, 445), "365", int(150*q), OSCURO)
            tx(d, (540, 530), "días", 40, OSCURO, negra=False)
            if C.cruza(t365):
                C.son("ding", 0.7)
    elif e in (2, 3):
        d = ImageDraw.Draw(img, "RGBA")
        t0 = I[2]
        if e == 2:
            q = sale((t - t0)/0.35)*(1 - ease((t - t0 - 1.4)/0.4))
            if q > 0:
                tx(d, (540, 330), "LO HE SIMULADO", int(96*max(q, 0.05)), AMARILLO, borde=10)
                if C.cruza(t0):
                    C.son("golpe", 0.7)
        kc = ease((t - C.en(2, "diez"))/2.6)
        n_vis = int(120*kc) if e == 2 else 120
        rojo = ease((t - C.en(3, "mitad"))/0.6) if e == 3 else 0
        for m in range(n_vis):
            fx, fy = m % 10, m//10
            x, y = 95 + fx*99, 620 + fy*66
            col = np.array((52, 66, 120))
            if MINI[m]:
                col = col*(1 - rojo) + np.array(ROJO)*rojo
            d.rounded_rectangle([x - 42, y - 26, x + 42, y + 26], radius=10, fill=tuple(int(v) for v in col) + (255,))
            for j in range(23):
                px, py = x - 34 + (j % 8)*9.7, y - 16 + (j//8)*14
                d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=(200, 210, 240, 200))
        if e == 2 or t < C.en(3, "mitad"):
            n = int(N_CLASES*kc) if e == 2 else N_CLASES
            if kc > 0:
                tx(d, (540, 500), f"{n:,} clases".replace(",", "."), 80, BLANCO, borde=8)
            if e == 2:
                for m in range(0, 120, 6):
                    if C.cruza(C.en(2, "diez") + 2.6*m/120):
                        C.son("tic", 2)
        if e == 3:
            tm = C.en(3, "mitad")
            q = sale((t - tm)/0.4)
            if q > 0:
                tx(d, (540, 350), "50%", int(220*q), ROJO, borde=12)
                tx(d, (540, 500), f"{PCT:.1f}".replace(".", ",") + " % de las clases", 46, BLANCO, borde=6, alfa=255*ease((t - tm - 0.3)/0.3))
                if C.cruza(tm):
                    C.son("golpe", 0.8)
    elif e == 4:
        d = ImageDraw.Draw(img, "RGBA")
        tx(d, (540, 300), "¿Cuántas clases tienen", 62, BLANCO, borde=6)
        tx(d, (540, 380), "dos que coinciden?", 62, BLANCO, borde=6)
        filas = [(23, PCT, I[4] - 0.2), (30, 70.6, C.en(4, "treinta")), (41, 90.3, C.en(4, "cuarenta"))]
        for k, (n, p, ts) in enumerate(filas):
            y = 600 + k*220
            q = ease((t - ts)/0.6)
            if t < ts:
                continue
            tx(d, (150, y + 60), f"{n}", 92, AMARILLO, borde=6)
            tx(d, (150, y + 135), "personas", 30, TENUE, negra=False)
            d.rounded_rectangle([270, y + 15, 970, y + 115], radius=50, fill=(30, 38, 76, 255))
            col = ROJO if p > 80 else (AMARILLO if p > 60 else (255, 140, 70))
            d.rounded_rectangle([270, y + 15, 270 + max(100, 700*p/100*q), y + 115], radius=50, fill=col + (255,))
            if q > 0.3:
                tx(d, (270 + max(100, 700*p/100*q) - 80, y + 65), f"{int(round(p*q))}%", 52, OSCURO)
            if C.cruza(ts):
                C.son("ding", 0.7)
    elif e == 5:
        d = ImageDraw.Draw(img, "RGBA")
        t_tu, t_cual, t_253 = C.en(5, "tu", exacta=True), C.en(5, "cualquier"), C.en(5, "doscientas")
        todos = ASIENTOS + [YO]
        yo = len(todos) - 1
        if t < t_cual:
            # solo tus parejas (22): lo que todos imaginamos
            q = ease((t - t_tu + 0.6)/1.0)
            for n in range(22):
                if q*22 > n:
                    d.line([YO, ASIENTOS[n]], fill=AMARILLO + (170,), width=4)
            if q > 0:
                tx(d, (540, 400), "No solo contigo:", 64, BLANCO, borde=6, alfa=255*q)
        else:
            q = ease((t - t_cual)/(max(1.0, t_253 - t_cual + 0.8)))
            pares = [(a, b) for a in range(24) for b in range(a + 1, 24)]
            k = int(q*len(pares))
            for a, b in pares[:k]:
                d.line([todos[a], todos[b]], fill=(255, 206, 46, 70), width=2)
            if C.cruza(t_cual):
                C.son("whoosh", 0.8)
            n = int(253*ease((t - t_cual)/max(0.5, t_253 - t_cual + 0.6)))
            tx(d, (540, 330), "cualquier pareja", 64, BLANCO, borde=6)
            tx(d, (540, 450), f"{n} parejas", 104 if t >= t_253 else 90, AMARILLO, borde=10)
            if C.cruza(t_253):
                C.son("golpe", 0.6)
        clase(img, C, 1.0, cara="susto" if t >= t_cual else "normal")
    else:
        clase(img, C, 1.0, dim=0.3, pareja=True)
        agente(img, 540, 1040, 140, "guiño", t, "señala")
        titular(img, [[("Mañana,", BLANCO)], [("pregunta", AMARILLO)], [("en clase.", BLANCO)]], 260, 120, k=(t - I[6])/0.3)
    return img
