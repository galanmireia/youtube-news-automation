"""Short: ¿Por qué tu cola del súper siempre es la más lenta?

Simulacion: 3 cajas con 4 personas delante en cada una; tu eres el 5º de la
del medio. Cada cliente tarda un tiempo al azar (exponencial, media 1,5 min).
- tu cola acaba la primera ~1 de cada 3 veces;
- con una sola cola para las tres cajas (12 delante), la espera media baja
  de ~6 a ~5 minutos y esperar mas de 10 min pasa de ~10 % a ~0,4 %.
"""
import numpy as np
from PIL import ImageDraw

from estilo import (AMARILLO, AZUL, BLANCO, OSCURO, PUNTO, ROJO, TENUE, VERDE, agente, ease, etiqueta, punto, sale,
                    titular, tx)

ALEGRE = True
CAJAS = [240, 540, 840]
Y_CAJA = 700


def prepara(C):
    global GANA, MUESTRA, MEDIA_S, MEDIA_U, LARGA_S, LARGA_U
    rnd = np.random.default_rng(5)
    S, N = 1.5, 20000
    fin = rnd.exponential(S, (N, 3, 5)).sum(2)
    gana = fin.argmin(1) == 1
    GANA, MUESTRA = gana.mean(), gana[:30]
    sep = rnd.exponential(S, (N, 4)).sum(1)
    uni = []
    for _ in range(N):
        libres = list(rnd.exponential(S, 3))
        for _k in range(9):
            i = int(np.argmin(libres))
            libres[i] += rnd.exponential(S)
        uni.append(min(libres))
    uni = np.array(uni)
    MEDIA_S, MEDIA_U = sep.mean(), uni.mean()
    LARGA_S, LARGA_U = (sep > 10).mean(), (uni > 10).mean()
    print(f"cola: gana {GANA:.3f}; media {MEDIA_S:.2f} vs {MEDIA_U:.2f}; >10 min {LARGA_S:.3f} vs {LARGA_U:.3f}", flush=True)


def cajas(d, alfa=255):
    for k, x in enumerate(CAJAS):
        d.rounded_rectangle([x - 115, Y_CAJA - 45, x + 115, Y_CAJA + 45], radius=16, fill=(40, 50, 92, int(alfa)),
                            outline=TENUE + (int(alfa),), width=4)
        tx(d, (x, Y_CAJA), f"CAJA {k + 1}", 34, TENUE, alfa=alfa)


def colas(img, C, avance=0.0, cara="normal", alfa=255):
    """Tres colas de 4 + tu (5º en la del medio). avance: cuanto han avanzado las de los lados (0..1 = una persona)."""
    d = ImageDraw.Draw(img, "RGBA")
    cajas(d, alfa)
    for k, x in enumerate(CAJAS):
        a = avance if k != 1 else 0.0
        for j in range(4 if k != 1 else 4):
            y = Y_CAJA + 130 + j*125 - a*125
            if y < Y_CAJA + 60:
                continue
            punto(d, x, y, 44, PUNTO, alfa)
    agente(img, 540, Y_CAJA + 130 + 4*125 - 15, 52, cara, C.t, alfa=int(alfa))


def dibuja(img, C):
    e, t, I = C.esc, C.t, C.ini
    if e == 0:
        tl = C.en(0, "lado")
        av = ease((t - tl)/0.8)
        if C.cruza(tl):
            C.son("whoosh", 0.6)
        colas(img, C, av, "triste" if t >= tl else "normal")
        k = 1 - ease((t - 4.0)/0.5)
        if k > 0:
            titular(img, [[("¿Por qué tu cola", BLANCO)], [("SIEMPRE", AMARILLO), (" es", BLANCO)], [("la más lenta?", BLANCO)]],
                    200, 108, alfa=255*k)
        else:
            d = ImageDraw.Draw(img, "RGBA")
            for x in (240, 840):
                d.polygon([(x - 34, Y_CAJA + 80), (x + 34, Y_CAJA + 80), (x, Y_CAJA + 50)], fill=VERDE + (240,))
            tx(d, (540, 400), "…y la de al lado", 70, BLANCO, borde=8)
            tx(d, (540, 490), "va más rápido", 70, VERDE, borde=8)
    elif e == 1:
        colas(img, C, 1.0, "triste", alfa=70)
        d = ImageDraw.Draw(img, "RGBA")
        q = sale((t - I[1] - 0.1)/0.35)
        tx(d, (540, 330), "¿Mala suerte?", int(90*max(q, 0.05)), BLANCO, borde=8)
        ts = C.en(1, "simulado")
        if t > ts:
            k = ease((t - ts)/1.6)
            tx(d, (540, 520), "LO HE SIMULADO", 80, AMARILLO, borde=8)
            tx(d, (540, 1000), f"{int(20000*k):,}".replace(",", "."), 170, BLANCO, borde=12)
            tx(d, (540, 1120), "veces", 60, TENUE, borde=6)
            if C.cruza(ts):
                C.son("golpe", 0.7)
    elif e == 2:
        d = ImageDraw.Draw(img, "RGBA")
        tu = C.en(2, "una", exacta=True)
        q = sale((t - tu)/0.4)
        tx(d, (540, 300), "Tu cola fue la más rápida", 58, BLANCO, borde=6)
        if q > 0:
            tx(d, (540, 450), "1 de cada 3", int(130*q), AMARILLO, borde=10)
            if C.cruza(tu):
                C.son("golpe", 0.6)
        # 30 de las simulaciones: amarillo si gano tu cola
        k = ease((t - I[2])/1.8)
        for m in range(30):
            if k*30 <= m:
                continue
            x, y = 160 + (m % 6)*152, 700 + (m//6)*130
            if MUESTRA[m]:
                agente(img, x, y, 40, "contento", t, sombra=False)
            else:
                d = ImageDraw.Draw(img, "RGBA")
                punto(d, x, y, 40, AZUL)
            if C.cruza(I[2] + 1.8*m/30):
                C.son("tic", 2)
        d = ImageDraw.Draw(img, "RGBA")
        tx(d, (540, 1380), f"ganó tu cola: {GANA*100:.0f} % de las veces".replace(".", ","), 44, TENUE, borde=4,
           alfa=255*ease((t - I[2] - 2)/0.4))
    elif e == 3:
        colas(img, C, 0.0, "pensando")
        d = ImageDraw.Draw(img, "RGBA")
        tu, dos = C.en(3, "tu", exacta=True), C.en(3, "dos")
        q1, q2 = ease((t - tu)/0.3), ease((t - dos)/0.3)
        if q1 > 0:
            d.rounded_rectangle([430, Y_CAJA + 70, 650, Y_CAJA + 680], radius=30, outline=AMARILLO + (int(255*q1),), width=6)
            etiqueta(img, 540, 430, "TÚ: 1 cola", AMARILLO, 56, q1)
        if q2 > 0:
            for x in (240, 840):
                d.rounded_rectangle([x - 100, Y_CAJA + 70, x + 100, Y_CAJA + 560], radius=30, outline=AZUL + (int(255*q2),), width=6)
            etiqueta(img, 540, 300, "ELLAS: 2 colas", AZUL, 56, q2)
            if C.cruza(dos):
                C.son("pop", 0.7)
    elif e == 4:
        d = ImageDraw.Draw(img, "RGBA")
        cajas(d)
        # una sola cola en zigzag hacia las tres cajas
        pts = []
        for j in range(13):
            fila, col = j//4, j % 4
            x = 300 + (col if fila % 2 == 0 else 3 - col)*160
            pts.append((x, Y_CAJA + 200 + fila*120))
        k = ease((t - I[4] - 0.2)/1.0)
        for j, (x, y) in enumerate(pts[:-1]):
            if k*13 > j:
                punto(d, x, y, 40, PUNTO)
        d.line([(300, Y_CAJA + 140), (840, Y_CAJA + 140)], fill=TENUE + (160,), width=4)
        if k > 0.9:
            agente(img, pts[-1][0], pts[-1][1] - 10, 48, "normal", t, sombra=False)
        tx(d, (540, 290), "UNA sola cola", 80, AMARILLO, borde=8)
        tx(d, (540, 380), "para todas las cajas", 54, BLANCO, borde=6)
        ts, tc = C.en(4, "seis"), C.en(4, "cinco")
        d = ImageDraw.Draw(img, "RGBA")
        if t > ts:
            tx(d, (540, 1250), "espera media", 44, TENUE, borde=4)
            tx(d, (380, 1350), f"{MEDIA_S:.0f} min", 84, ROJO, borde=8)
            if C.cruza(ts):
                C.son("ding", 0.6)
        if t > tc:
            tx(d, (540, 1350), "→", 84, BLANCO, borde=8)
            tx(d, (720, 1350), f"{MEDIA_U:.0f} min", int(84*sale((t - tc)/0.3)), VERDE, borde=8)
            if C.cruza(tc):
                C.son("ding", 0.9)
        tx(d, (540, 1660), "(si cada cliente tarda de media minuto y medio)", 30, TENUE, negra=False)
    else:
        d = ImageDraw.Draw(img, "RGBA")
        tx(d, (540, 300), "Esperar más de", 66, BLANCO, borde=6)
        tx(d, (540, 390), "10 minutos", 90, AMARILLO, borde=8)
        tdiez, tnunca = C.en(5, "una", exacta=True), C.en(5, "nunca")
        for k, (et, v, col, ts) in enumerate((("3 colas", LARGA_S, ROJO, tdiez), ("1 cola", LARGA_U, VERDE, tnunca))):
            y = 620 + k*260
            q = ease((t - ts)/0.5)
            if q <= 0:
                continue
            tx(d, (180, y + 60), et, 56, col, borde=6)
            d.rounded_rectangle([330, y + 10, 980, y + 110], radius=50, fill=(30, 38, 76, 255))
            d.rounded_rectangle([330, y + 10, 330 + max(30, 650*v/0.12*q), y + 110], radius=50, fill=col + (255,))
            lab = "1 de cada 10" if k == 0 else "casi nunca"
            tx(d, (655, y + 175), lab, 54, col, borde=6)
            if C.cruza(ts):
                C.son("ding", 0.8)
        agente(img, 540, 1290, 70, "contento" if t > tnunca else "normal", t, "arriba" if t > tnunca else "abajo")
    return img
