"""Short: 3 puertas, 1 premio. ¿Cambiarías de puerta? (problema de Monty Hall)

Simulacion: 100.000 partidas. El presentador sabe donde esta el premio, abre
siempre una puerta vacia que no elegiste y siempre te deja cambiar.
Quedandote ganas ~1/3; cambiando, ~2/3.
"""
import numpy as np
from PIL import ImageDraw

from estilo import (AMARILLO, BLANCO, OSCURO, ROJO, TENUE, VERDE, F, agente, ease, etiqueta, sale, titular, tx)

ALEGRE = True
XS = (210, 540, 870)
MADERA, BORDE = (96, 62, 38), (170, 116, 72)


def prepara(C):
    global P_QUEDA, P_CAMBIA
    r = np.random.default_rng(3)
    premio, elige = r.integers(0, 3, 100000), r.integers(0, 3, 100000)
    P_QUEDA, P_CAMBIA = (premio == elige).mean(), (premio != elige).mean()
    print(f"puertas: quedarse {P_QUEDA:.3f}, cambiar {P_CAMBIA:.3f}", flush=True)


def estrella(d, x, y, r, col=AMARILLO):
    import math
    pts = []
    for k in range(10):
        a = -math.pi/2 + k*math.pi/5
        rr = r if k % 2 == 0 else r*0.45
        pts.append((x + rr*math.cos(a), y + rr*math.sin(a)))
    d.polygon(pts, fill=col + (255,))


def puerta(d, x, y, w, h, n, abierta=0.0, premio=False, marcada=False, alfa=255, etiqueta_txt=None):
    a = int(alfa)
    d.rectangle([x - w/2, y - h/2, x + w/2, y + h/2], fill=(12, 14, 28, a))
    if abierta > 0 and premio:
        estrella(d, x, y, w*0.32)
    if abierta > 0 and not premio:
        tx(d, (x, y), "vacía", int(w*0.2), TENUE, alfa=a)
    hw = w*(1 - 0.85*abierta)
    d.rectangle([x - w/2, y - h/2, x - w/2 + hw, y + h/2], fill=MADERA + (a,), outline=BORDE + (a,), width=6)
    if abierta < 0.5:
        d.ellipse([x + w*0.28, y, x + w*0.36, y + w*0.08], fill=AMARILLO + (a,))
        tx(d, (x, y - h*0.28), str(n), int(w*0.42), (232, 200, 160), alfa=a)
    if marcada:
        d.rectangle([x - w/2 - 10, y - h/2 - 10, x + w/2 + 10, y + h/2 + 10], outline=AMARILLO + (a,), width=8)


def dibuja(img, C):
    e, t, I = C.esc, C.t, C.ini
    d = ImageDraw.Draw(img, "RGBA")
    if e in (0, 1, 2):
        t_uno = C.en(0, "uno")
        abre = ease((t - C.en(1, "abre"))/0.6) if e >= 1 else 0
        for k, x in enumerate(XS):
            puerta(d, x, 900, 260, 470, k + 1, abierta=abre if k == 2 else 0, marcada=(k == 0 and t >= t_uno))
        if C.cruza(t_uno):
            C.son("pop", 0.8)
        if e >= 1 and C.cruza(C.en(1, "abre")):
            C.son("whoosh", 0.8)
        cara = "pensando" if e == 2 else ("susto" if e == 1 and t > C.en(1, "cambiar") else "normal")
        agente(img, 380, 1290, 78, cara, t, "señala" if e == 0 else "abajo")
        d = ImageDraw.Draw(img, "RGBA")
        if e == 0:
            titular(img, [[("3 puertas.", BLANCO)], [("1 premio.", AMARILLO)], [("¿Cambiarías", BLANCO)], [("de puerta?", BLANCO)]],
                    150, 100)
        elif e == 1:
            tc = C.en(1, "cambiar")
            agente_p = C.en(1, "presentador")
            tx(d, (540, 330), "El presentador SABE", 70, BLANCO, borde=8, alfa=255*ease((t - agente_p)/0.3))
            tx(d, (540, 420), "dónde está el premio", 54, TENUE, borde=6, alfa=255*ease((t - agente_p)/0.3))
            if t > tc:
                etiqueta(img, 700, 1210, "¿quieres cambiar?", AMARILLO, 50, ease((t - tc)/0.3), flecha_a=(560, 1250))
                if C.cruza(tc):
                    C.son("ding", 0.8)
        else:
            tc = C.en(2, "cincuenta")
            tx(d, (540, 330), "«Da igual:", 80, BLANCO, borde=8)
            tx(d, (540, 430), "quedan dos»", 80, BLANCO, borde=8)
            if t > tc:
                for x in XS[:2]:
                    etiqueta(img, x, 610, "50 %", BLANCO, 64, ease((t - tc)/0.3))
                if C.cruza(tc):
                    C.son("pop", 0.7)
    elif e == 3:
        ts = I[3]
        q = sale((t - ts)/0.35)*(1 - ease((t - ts - 1.6)/0.3))
        if q > 0:
            tx(d, (540, 330), "LO HE SIMULADO", int(90*max(q, 0.05)), AMARILLO, borde=8)
            if C.cruza(ts):
                C.son("golpe", 0.7)
        k = ease((t - C.en(3, "cien"))/1.2)
        tx(d, (540, 470), f"{int(100000*k):,} partidas".replace(",", "."), 74, BLANCO, borde=8)
        filas = (("QUEDARTE", P_QUEDA, ROJO, C.en(3, "quedandote")), ("CAMBIAR", P_CAMBIA, VERDE, C.en(3, "cambiando")))
        for m, (et, p, col, tw) in enumerate(filas):
            y = 700 + m*260
            qq = ease((t - tw)/0.6)
            if qq <= 0:
                continue
            tx(d, (540, y), et, 64, col, borde=6)
            d.rounded_rectangle([140, y + 50, 940, y + 150], radius=50, fill=(30, 38, 76, 255))
            d.rounded_rectangle([140, y + 50, 140 + max(100, 800*p*qq), y + 150], radius=50, fill=col + (255,))
            lab = "1 de cada 3" if m == 0 else "2 de cada 3"
            tx(d, (140 + max(100, 800*p*qq) - 30, y + 100), lab, 46, OSCURO, anchor="rm")
            if C.cruza(tw):
                C.son("ding", 0.8)
        tdoble = C.en(3, "doble")
        if t > tdoble:
            tx(d, (540, 1300), "¡EL DOBLE!", int(110*sale((t - tdoble)/0.3)) + 1, AMARILLO, borde=10)
            if C.cruza(tdoble):
                C.son("golpe", 0.7)
    elif e == 4:
        t1, t2 = C.en(4, "acertaste"), C.en(4, "otras")
        if t < t1 - 0.2:
            tx(d, (540, 800), "¿Por qué?", int(130*sale((t - I[4])/0.3)) + 1, BLANCO, borde=10)
        else:
            tx(d, (540, 250), "Eliges la 1. Hay 3 casos:", 60, BLANCO, borde=6)
        tq = C.en(4, "quitarte")
        casos = [(0, None, t1), (1, 2, t2), (2, 1, t2 + 0.6)]      # (donde esta el premio, puerta que abre, cuando sale)
        for fila, (premio, abre, tw) in enumerate(casos):
            y = 470 + fila*290
            q = ease((t - tw)/0.4)
            if q <= 0:
                continue
            for k, x in enumerate((150, 330, 510)):
                ab = 1.0 if (k == premio and t > tq + 0.4) else (1.0 if k == abre and t > tq else 0.0)
                if abre is None and k == 1 and t > tq:
                    ab = 1.0
                puerta(d, x, y + 40, 140, 220, k + 1, abierta=ab, premio=(k == premio), marcada=(k == 0), alfa=255*q)
            if t > tq + 0.4:
                gana = premio != 0
                tx(d, (800, y + 10), "cambiar:", 44, BLANCO, borde=4)
                tx(d, (800, y + 80), "GANAS" if gana else "pierdes", 60, VERDE if gana else ROJO, borde=6)
                if C.cruza(tq + 0.4) and fila == 0:
                    C.son("ding", 0.9)
            if C.cruza(tw):
                C.son("pop", 0.6)
    else:
        agente(img, 540, 1000, 150, "contento", t, "arriba")
        titular(img, [[("CAMBIA", AMARILLO)], [("SIEMPRE.", BLANCO)]], 330, 150, k=(t - I[5])/0.3)
    return img
