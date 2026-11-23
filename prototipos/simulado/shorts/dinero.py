"""Short: Repartí el dinero a partes iguales entre 1.000 personas.

Modelo «yard-sale» (Chakraborti 2002; Boghosian): en cada ronda todos se
emparejan al azar y cada pareja se juega a cara o cruz el 10 % del dinero del
MAS POBRE de los dos. Es un juego justo (nadie gana de media), y aun asi el
dinero se concentra: tras 400 partidas por persona ~57 % tiene menos de 50 €;
tras 2.000, el 10 % mas rico tiene ~83 %.
"""
import math

import numpy as np
from PIL import ImageDraw

from estilo import (AMARILLO, AZUL, BLANCO, OSCURO, PUNTO, ROJO, TENUE, VERDE, agente, ease, etiqueta, sale, titular, tx)

ALEGRE = False
N, RONDAS, CADA = 1000, 2000, 5


def prepara(C):
    global FOTOS, YO, POS
    r = np.random.default_rng(11)
    w = np.full(N, 100.0)
    FOTOS = [w.copy()]
    for k in range(1, RONDAS + 1):
        p = r.permutation(N)
        a, b = p[:N//2], p[N//2:]
        d = 0.1*np.minimum(w[a], w[b])
        s = np.where(r.random(N//2) < 0.5, 1, -1)
        w[a] += s*d
        w[b] -= s*d
        if k % CADA == 0:
            FOTOS.append(w.copy())
    FOTOS = np.array(FOTOS)
    cols = 40
    POS = np.array([(52 + (i % cols)*25, 660 + (i//cols)*25) for i in range(N)], float)
    # «tú»: alguien del centro de la cuadricula; acaba como la mayoria (con poco)
    centro = [i for i in range(N) if 14 <= i % cols <= 25 and 9 <= i//cols <= 15]
    YO = min(centro, key=lambda i: abs(FOTOS[-1][i] - 6))
    f4, f20 = FOTOS[400//CADA], FOTOS[-1]
    o = np.sort(f20)[::-1]
    print(f"dinero: 400 -> {np.mean(f4 < 50):.1%} con <50; 2000 -> top10 {o[:100].sum()/o.sum():.1%}; tú acabas con {f20[YO]:.1f} €", flush=True)


def riqueza(ronda):
    k = min(len(FOTOS) - 1, max(0.0, ronda/CADA))
    i = int(k)
    j = min(i + 1, len(FOTOS) - 1)
    f = k - i
    return FOTOS[i]*(1 - f) + FOTOS[j]*f


def rejilla(img, C, ronda, dim=1.0, tu=True, cara="normal"):
    w = riqueza(ronda)
    d = ImageDraw.Draw(img, "RGBA")
    orden = np.argsort(w)              # los ricos, encima
    for i in orden:
        if tu and i == YO:
            continue
        x, y = POS[i]
        r = max(4.5, min(70.0, 9*math.sqrt(w[i]/100)))
        if w[i] < 50:
            col = (226, 120, 150)
        elif w[i] > 400:
            col = AMARILLO
        else:
            col = PUNTO
        d.ellipse([x - r, y - r, x + r, y + r], fill=col + (int(255*dim),))
    if tu:
        x, y = POS[YO]
        agente(img, x, y - 8, 30, cara, C.t, alfa=int(255*dim), sombra=False)


def dibuja(img, C):
    e, t, I = C.esc, C.t, C.ini
    if e == 0:
        rejilla(img, C, 0, dim=ease((t - 0.1)/0.6))
        titular(img, [[("Repartí el dinero", BLANCO)], [("a partes ", BLANCO), ("IGUALES", AMARILLO)],
                      [("entre 1.000", BLANCO)], [("personas.", BLANCO)]], 150, 100)
        etiqueta(img, POS[YO][0], POS[YO][1] - 90, "100 € cada uno", AMARILLO, 40, ease((t - C.en(0, "cien"))/0.3),
                 flecha_a=(POS[YO][0], POS[YO][1] - 40))
    elif e == 1:
        rejilla(img, C, 0, dim=0.25)
        d = ImageDraw.Draw(img, "RGBA")
        tz = C.en(1, "dos")
        k = ease((t - tz)/0.4)
        xa, xb, y = 270, 810, 930
        for x, nombre in ((xa, "A"), (xb, "B")):
            r = 90*sale(k)
            if r > 1:
                d.ellipse([x - r, y - r, x + r, y + r], fill=PUNTO + (255,))
                tx(d, (x, y), nombre, 70, BLANCO)
        # la moneda gira y cae: cara -> B le da a A
        tm = C.en(1, "cara")
        if t > tm:
            gira = t - tm
            if gira < 1.0:
                anch = abs(math.cos(gira*14))*70 + 4
                yy = y - 200 - math.sin(min(1, gira)*math.pi)*120
                d.ellipse([540 - anch, yy - 70, 540 + anch, yy + 70], fill=AMARILLO + (255,), outline=OSCURO + (255,), width=5)
            else:
                etiqueta(img, 540, y - 220, "¡cara! B le paga a A", AMARILLO, 44, ease((gira - 1)/0.3))
                q = ease((gira - 1.2)/0.6)
                d = ImageDraw.Draw(img, "RGBA")
                xm = xb + (xa - xb)*q
                d.ellipse([xm - 26, y - 150 - 26, xm + 26, y - 150 + 26], fill=AMARILLO + (255,))
                tx(d, (xm, y - 150), "€", 30, OSCURO)
            if C.cruza(tm):
                C.son("whoosh", 0.6)
        for palabra, s, yy in (("trampas", "sin trampas", 1150), ("listo", "nadie más listo", 1240), ("suerte", "solo suerte", 1330)):
            q = ease((t - C.en(1, palabra))/0.25)
            if q > 0:
                etiqueta(img, 540, yy, s, VERDE if palabra != "suerte" else AMARILLO, 46, q)
                if C.cruza(C.en(1, palabra)):
                    C.son("pop", 0.6)
        tx(ImageDraw.Draw(img, "RGBA"), (540, 380), "Un juego justo:", 74, BLANCO, borde=8)
        tx(ImageDraw.Draw(img, "RGBA"), (540, 470), "cara o cruz", 74, AMARILLO, borde=8)
    elif e in (2, 3, 4):
        if e == 2:
            ronda = 100*ease((t - I[2])/C.durs[2])
        elif e == 3:
            ronda = 100 + 300*ease((t - I[3])/max(0.5, C.en(3, "cuatrocientas") - I[3] + 0.6))
        else:
            ronda = 400 + 1600*ease((t - I[4])/max(0.5, C.en(4, "dos") - I[4] + 0.8))
        w = riqueza(ronda)
        rejilla(img, C, ronda, cara="triste" if w[YO] < 50 else "normal")
        d = ImageDraw.Draw(img, "RGBA")
        tx(d, (540, 230), f"{int(round(ronda))}", 120, BLANCO, borde=10)
        tx(d, (540, 320), "partidas por persona", 44, TENUE, borde=4)
        if e == 3:
            tm = C.en(3, "menos")
            if t > tm:
                q = sale((t - tm)/0.4)
                tx(d, (540, 450), f"{np.mean(w < 50)*100:.0f} % tiene menos de 50 €", int(52*max(q, 0.1)), (255, 120, 140), borde=6)
        if e == 4:
            tm = C.en(4, "rico")
            if t > tm:
                o = np.sort(w)[::-1]
                q = sale((t - tm)/0.4)
                tx(d, (540, 450), f"el 10 % más rico: {o[:100].sum()/o.sum()*100:.0f} %", int(60*max(q, 0.1)), AMARILLO, borde=6)
                tx(d, (540, 520), "de todo el dinero", 44, BLANCO, borde=4)
                if C.cruza(tm):
                    C.son("golpe", 0.7)
        if e in (3, 4):
            d = ImageDraw.Draw(img, "RGBA")
            d.ellipse([170, 1300, 194, 1324], fill=(226, 120, 150, 255))
            tx(d, (206, 1312), "menos de 50 €", 34, BLANCO, anchor="lm", negra=False)
            d.ellipse([600, 1295, 634, 1329], fill=AMARILLO + (255,))
            tx(d, (648, 1312), "más de 400 €", 34, BLANCO, anchor="lm", negra=False)
            etiqueta(img, POS[YO][0] + 10, POS[YO][1] - 80, f"tú: {w[YO]:.0f} €", AMARILLO, 36, 1.0,
                     flecha_a=(POS[YO][0], POS[YO][1] - 35))
        n_tics = int(ronda)//20
        if n_tics != int(ronda - 1e-6 - 4)//20 and e != 2:
            pass
        if C.cruza(I[e] + 0.05):
            C.son("whoosh", 0.5)
    elif e == 5:
        rejilla(img, C, RONDAS, dim=0.2)
        d = ImageDraw.Draw(img, "RGBA")
        tx(d, (540, 300), "¿Por qué?", 96, BLANCO, borde=8)
        tp = C.en(5, "pobre")
        xp, xr, y = 280, 760, 880
        k = ease((t - I[5] - 0.6)/0.5)
        if k > 0:
            d.ellipse([xp - 45, y - 45, xp + 45, y + 45], fill=(120, 70, 90, 255))
            tx(d, (xp, y + 100), "10 €", 56, BLANCO, borde=6)
            d.ellipse([xr - 150, y - 150, xr + 150, y + 150], fill=AMARILLO + (255,))
            tx(d, (xr, y + 200), "500 €", 56, BLANCO, borde=6)
        if t > tp:
            etiqueta(img, 540, 560, "se juegan 1 € (el 10 % del pobre)", BLANCO, 40, ease((t - tp)/0.3))
        tm, tc = C.en(5, "mucho"), C.en(5, "calderilla")
        if t > tm:
            tx(d, (xp, y + 220), "pierde el 10 %", 44, ROJO, borde=6)
            tx(d, (xp, y + 280), "de lo que tiene", 34, TENUE, borde=4)
            if C.cruza(tm):
                C.son("pop", 0.7)
        if t > tc:
            tx(d, (xr, y + 270), "pierde el 0,2 %", 44, VERDE, borde=6)
            if C.cruza(tc):
                C.son("pop", 0.7)
    else:
        rejilla(img, C, RONDAS, dim=0.55, cara="triste")
        d = ImageDraw.Draw(img, "RGBA")
        q = ease((t - I[6])/0.3)
        tx(d, (540, 300), "Un juego justo…", 80, BLANCO, borde=8, alfa=255*q)
        q2 = ease((t - C.en(6, "dinero"))/0.3)
        tx(d, (540, 420), "…y el dinero en", 70, BLANCO, borde=8, alfa=255*q2)
        tx(d, (540, 510), "muy pocas manos", 80, AMARILLO, borde=8, alfa=255*q2)
    return img
