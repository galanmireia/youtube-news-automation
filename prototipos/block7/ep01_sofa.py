"""BLOCK 7 · Ep. 1 — THE SOFA (~51 s, vertical, sin voz). Version centrada: Poke contra el sofa, y Bubble.

Comedia de vecinos. Poke llega con un sofa que no cabe en el ascensor. Mag,
el ligon del edificio, se ofrece a ayudar: a el se le pega todo lo metalico
por la escalera (las puertecitas de los buzones, la bici del vecino, la
sarten de Tosti). Las cotillas, Sal y Pimienta, lo espian por la mirilla.
Don Huevo les corta el paso y acaba aplastado contra la pared. En el 2o, Mag
señala la puerta equivocada: el sofa entra en casa de Bubble. Flechazo: Poke
se enamora... y Mag tambien. Sal y Pimienta lo han visto todo: "cactus +
corazon + globo" -> Ep. 2, THE RUMOR.
"""
import math, random, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mundo as Mu
import sonido as S
from mundo import T, W, H, suave, parpadeo, fuente

OUT = str(Path(__file__).resolve().parent) + "/salida/"
FPS = 25
SUELO = 1500
HP, HM = 520, 520

def estrellas(d, x, y, t, r=70):
    for k in range(3):
        a = t*5 + k*2.1
        d.regular_polygon((x + math.cos(a)*r, y + math.sin(a)*r*0.35, 20), 5, fill=(255, 220, 70), outline=T)

def suelo_baldosa(d):
    d.rectangle([0, SUELO, W, H], fill=(236, 232, 224))
    for i in range(0, W, 120):
        for j in range(SUELO, H, 120):
            if (i//120 + j//120) % 2 == 0:
                d.rectangle([i, j, i + 120, j + 120], fill=(70, 74, 86))
    d.line([(0, SUELO), (W, SUELO)], fill=T, width=6)

def mostrador_gato(img, x, t, despierto=0.0):
    Mu.gato(img, x, 1200, 360, dict(cansancio=1.0 - despierto, mira=(-0.6, 0.2)), t)
    d = ImageDraw.Draw(img)
    d.rectangle([x - 200, 1200, x + 200, SUELO + 30], fill=(150, 100, 70), outline=T, width=6)
    if despierto < 0.5:
        Mu.zzz(d, x + 90, 870, t, 46)

# ---------------------------------------------------------------- 1. la fachada
def p_fachada(lt, t):
    img = Image.new("RGB", (W, H), (180, 220, 244)); d = ImageDraw.Draw(img)
    d.rectangle([0, 160, W, SUELO], fill=(232, 196, 168), outline=T, width=6)
    for fila in range(0, 30):
        for col in range(10):
            x = col*120 + (60 if fila % 2 else 0); y = 160 + fila*46
            if y < SUELO - 40:
                d.rectangle([x, y, x + 116, y + 42], outline=(214, 176, 150), width=2)
    d.rounded_rectangle([W/2 - 210, 180, W/2 + 210, 280], radius=18, fill=(52, 50, 64), outline=T, width=6)
    Mu.texto(d, W/2, 230, "BLOCK 7", 66, (255, 214, 90))
    # la puerta de cristal con el gato dormido dentro
    d.rectangle([560, 900, 960, SUELO], fill=(170, 210, 220), outline=T, width=8)
    Mu.gato(img, 760, 1300, 220, dict(cansancio=1.0), t)
    d = ImageDraw.Draw(img)
    d.rectangle([640, 1300, 880, SUELO], fill=(150, 100, 70), outline=T, width=4)
    Mu.zzz(d, 830, 1100, t, 34)
    d.line([(760, 900), (760, SUELO)], fill=T, width=6)
    # la ventana del 1o: Sal y Pimienta espiando
    wx0, wy0, wx1, wy1 = 90, 420, 470, 820
    d.rectangle([wx0, wy0, wx1, wy1], fill=(246, 214, 200), outline=T, width=8)
    Mu.salero(img, 190, wy1 + 60, 300, dict(mira=(0.8, 0.6), boca="o", susto=1.0 if lt > 2.0 else 0.0), t)
    Mu.salero(img, 370, wy1 + 60, 300, dict(prismaticos=True), t, pimienta=True)
    d = ImageDraw.Draw(img)
    for lado in (-1, 1):            # las cortinas
        x = wx0 if lado < 0 else wx1
        d.polygon([(x, wy0), (x - lado*-70, wy0), (x - lado*-30, wy1), (x, wy1)], fill=(214, 120, 140), outline=T)
    d.rectangle([wx0 - 16, wy1, wx1 + 16, wy1 + 20], fill=(240, 236, 228), outline=T, width=4)
    Mu.ventana(d, 620, 420, 960, 760)
    # la acera y Poke empujando el sofa enorme
    d.rectangle([0, SUELO, W, H], fill=(196, 196, 204)); d.line([(0, SUELO), (W, SUELO)], fill=T, width=6)
    x = -260 + 560*suave(lt/3.2)
    Mu.sofa(img, x + 330, SUELO - 120, 560)
    st = dict(pose="abrazo" if lt < 3.2 else "caido", fase=lt*6 if lt < 3.2 else None, dir=0.6, mira=(0.8, 0.0), boca="dolor" if lt < 3.2 else "abierta",
              ceja=0.5 if lt < 3.2 else 0.0, inclina=0.08 if lt < 3.2 else 0.0, feliz=1.0 if lt > 3.6 else 0.0)
    info = Mu.poke(img, x, SUELO + 40, HP, st, t)
    Mu.sudor(ImageDraw.Draw(img), info["cara"][0] - 120, info["top"] + 40, 40, t)
    return img, (W/2, H/2, 1.0)

# ---------------------------------------------------------------- 2. el ascensor
def p_ascensor(lt, t):
    img = Image.new("RGB", (W, H), Mu.PAREDES["porteria"]); d = ImageDraw.Draw(img)
    suelo_baldosa(d)
    for f in range(2):
        for c in range(3):
            x, y = 50 + c*105, 520 + f*115
            d.rectangle([x, y, x + 92, y + 98], fill=(200, 168, 96), outline=T, width=4)
            d.rectangle([x + 18, y + 30, x + 74, y + 42], fill=(60, 56, 50))
    # el ascensor, pequeñito
    x0, x1, y0 = 380, 720, 900
    d.rectangle([x0 - 26, y0 - 26, x1 + 26, SUELO], fill=(150, 150, 160), outline=T, width=6)
    d.rectangle([x0, y0, x1, SUELO], fill=(214, 200, 176), outline=T, width=5)
    sobrecarga = 5.6 < lt < 7.0
    d.ellipse([x1 - 40, y0 - 110, x1, y0 - 70], fill=(240, 60, 50) if sobrecarga and (t*6) % 1.0 < 0.5 else (90, 90, 96), outline=T, width=3)
    mostrador_gato(img, 960, t, despierto=1.0 if 6.6 < lt < 7.4 else 0.0)
    d = ImageDraw.Draw(img)
    # los intentos con el sofa
    px = 180; ang = 0; sx = 520; sy = SUELO - 120; bonk = None; debajo = False
    if lt < 1.6:                         # 1. tumbado: no entra
        k = suave(lt/0.8) - 0.4*suave((lt - 0.8)/0.4); sx = 760 - 120*k + 80; sx = 900 - 220*k
        bonk = 0.8
    elif lt < 3.4:                       # 2. de pie: se da con el techo
        sx = 560; sy = SUELO - 300 - 60*math.sin(math.pi*suave((lt - 2.0)/0.6)); ang = 90; bonk = 2.4
    elif lt < 5.6:                       # 3. en diagonal: ¡entra!
        sx = 550; sy = SUELO - 300; ang = 55*suave((lt - 3.4)/0.8)
    elif lt < 7.0:                       # pero Poke no cabe: las puertas le pinchan, PITIDOS
        sx = 550; sy = SUELO - 300; ang = 55
    else:                                # el sofa sale disparado y cae encima de Poke
        k = suave((lt - 7.0)/0.4); sx = 550 - 360*k; sy = SUELO - 300 + 180*k; ang = 55*(1 - k); debajo = lt > 7.4
    if not debajo:
        st = dict(pose="abrazo", inclina=0.06, mira=(0.8, 0.0), boca="dolor" if lt < 5.6 else "o", ceja=0.4, dir=0.5)
        if 4.2 < lt < 5.6:
            st.update(boca="abierta", feliz=1.0, ceja=0.0, pose="arriba")
        if 5.6 <= lt < 7.0:
            st.update(susto=1.0, boca="grito", pose="arriba")
        pk = 180 if lt < 5.6 else 300 + 30*math.sin(t*25)
        Mu.poke(img, pk, SUELO + 40, HP, st, t)
    Mu.sofa(img, sx, sy, 560 if ang < 80 else 620, ang=ang, rasgado=0.3)
    d = ImageDraw.Draw(img)
    if debajo:                           # solo se le ven las patas y la flor
        Mu.piernas(d, 190, SUELO - 10, SUELO + 40, HP)
        for k in range(5):
            a = k/5*2*math.pi
            d.ellipse([110 + math.cos(a)*16 - 14, SUELO - 200 + math.sin(a)*16 - 14, 110 + math.cos(a)*16 + 14, SUELO - 200 + math.sin(a)*16 + 14],
                      fill=(244, 120, 160), outline=T, width=2)
        estrellas(d, 190, SUELO - 330, t)
    if bonk is not None and bonk < lt < bonk + 0.4:
        Mu.texto(d, 560, 820, "BONK!", 90, (255, 214, 60))
    if sobrecarga:
        Mu.texto(d, 550, 760, "BEEP! BEEP!", 70, (255, 90, 70))
    return img, (560, 1080, 1.04)

# ---------------------------------------------------------------- 3. llega Mag
def p_mag(lt, t):
    img = Image.new("RGB", (W, H), Mu.PAREDES["porteria"]); d = ImageDraw.Draw(img)
    suelo_baldosa(d)
    for k in range(8):                   # la escalera que baja por la derecha
        x = 640 + k*55; y = SUELO - k*90
        d.rectangle([x, y - 90, W + 10, y], fill=(206, 190, 168), outline=T, width=4)
    # Poke debajo del sofa
    levanta = suave((lt - 3.6)/0.6)
    sx = 250; sy = SUELO - 110 - 140*levanta
    Mu.sofa(img, sx, sy, 560, ang=8*levanta)
    d = ImageDraw.Draw(img)
    if levanta < 0.5:
        Mu.piernas(d, 230, SUELO - 10, SUELO + 40, HP)
    else:
        st = dict(pose="abrazo" if 4.6 < lt < 5.4 else "caido", feliz=1.0 if lt > 4.4 else 0.0, boca="abierta", mira=(0.8, -0.2), dir=0.5,
                  inclina=0.08 if 4.6 < lt < 5.4 else 0.0)
        Mu.poke(img, 230 + 150*suave((lt - 4.6)/0.6), SUELO + 40, HP, st, t)
    # Mag baja la escalera como en un anuncio
    baja = suave(lt/2.2)
    mx = 1000 - 300*baja; my = SUELO - 540*(1 - baja) + 40
    esquiva = suave((lt - 4.9)/0.3)*(1 - suave((lt - 5.7)/0.3))
    st_m = dict(gafas_sol=lt < 2.6, guino=2.8 < lt < 3.6, pistolas=2.8 < lt < 3.6, mira=(-0.8, 0.3), fondo=Mu.PAREDES["porteria"],
                tira=(sx + 280, sy) if 3.6 < lt < 4.6 else None)
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    Mu.mag(capa, mx, my, HM, st_m, t)
    if esquiva > 0:                      # se echa atras como en Matrix para que no le abrace
        capa = capa.rotate(-25*esquiva, center=(mx, my), resample=Image.BICUBIC)
    img.paste(capa, (0, 0), capa)
    d = ImageDraw.Draw(img)
    if lt < 2.4:
        Mu.texto(d, mx + 160, my - 640, "✦", 60, (255, 236, 140))
    if 4.9 < lt < 5.8:
        Mu.texto(d, mx - 40, my - 680, "NOPE.", 56, (250, 250, 250))
    return img, (560, 1060, 1.04)

# ---------------------------------------------------------------- 4. la escalera (dos tramos)
def escalera_fondo(pared, de_izq=True):
    img = Image.new("RGB", (W, H), pared); d = ImageDraw.Draw(img)
    a, b = ((60, 1760), (1020, 760)) if de_izq else ((1020, 1760), (60, 760))
    pasos = 12
    pts = []
    for k in range(pasos + 1):
        f = k/pasos
        x = a[0] + (b[0] - a[0])*f; y = a[1] + (b[1] - a[1])*f
        pts.append((x, y))
    poly = [(a[0], H)] + [p for k in range(pasos) for p in (pts[k], (pts[k + 1][0], pts[k][1]))] + [(b[0], H)]
    d.polygon(poly, fill=(206, 190, 168), outline=T)
    d.line(poly[1:-1], fill=T, width=5)
    return img, a, b

def tramo(lt, t, de_izq, pared, cosas_nuevas, cosas_viejas, extras=None, dur=7.0):
    img, a, b = escalera_fondo(pared, de_izq); d = ImageDraw.Draw(img)
    if extras: extras(img, lt, t)
    u = 0.05 + 0.6*suave(lt/(dur - 0.6))
    pos = lambda f: (a[0] + (b[0] - a[0])*f, a[1] + (b[1] - a[1])*f)
    pm = pos(u + 0.33); pp = pos(u)
    ang = math.degrees(math.atan2(a[1] - b[1], abs(b[0] - a[0])))*(1 if de_izq else -1)
    sc = ((pm[0] + pp[0])/2, (pm[1] + pp[1])/2 - 230)
    lado = 1 if de_izq else -1
    st_m = dict(mira=(lado*0.8, 0), gafas_sol=True, tira=(sc[0] + lado*120, sc[1] + 30), fondo=pared)
    Mu.mag(img, pm[0], pm[1] + 30, HM, st_m, t)
    Mu.sofa(img, sc[0], sc[1], 430, ang=ang, rasgado=0.4 + 0.6*min(1, lt/dur))
    d = ImageDraw.Draw(img)
    # lo que se ha ido pegando al sofa
    c, s_ = math.cos(math.radians(-ang)), math.sin(math.radians(-ang))
    rel = lambda dx, dy: (sc[0] + dx*c - dy*s_, sc[1] + dx*s_ + dy*c)
    for t0, de, donde, dibuja in cosas_viejas + cosas_nuevas:
        k = 1.0 if (t0 is None or lt > t0 + 0.5) else (suave((lt - t0)/0.5) if lt > t0 else 0.0)
        if k <= 0: continue
        dst = rel(*donde)
        if de:
            x = de[0] + (dst[0] - de[0])*k; y = de[1] + (dst[1] - de[1])*k - 150*math.sin(math.pi*k)
        else:
            x, y = dst
        dibuja(d, x, y)
    st_p = dict(pose="abrazo", mira=(lado*0.8, -0.3), boca="dolor", ceja=0.6, inclina=0.08*lado, fase=lt*6)
    info = Mu.poke(img, pp[0], pp[1] + 40, HP, st_p, t)
    Mu.sudor(ImageDraw.Draw(img), info["cara"][0] - lado*110, info["top"] + 30, 36, t)
    return img, (W/2, H/2, 1.0)

def puertecita(d, x, y):
    d.rectangle([x - 44, y - 46, x + 44, y + 46], fill=(200, 168, 96), outline=T, width=4)
    d.rectangle([x - 26, y - 14, x + 26, y - 2], fill=(60, 56, 50))

def carta(d, x, y):
    d.rectangle([x - 40, y - 26, x + 40, y + 26], fill=(250, 250, 246), outline=T, width=3)
    d.line([(x - 40, y - 26), (x, y + 4), (x + 40, y - 26)], fill=T, width=3)

def barrote(d, x, y):
    d.line([(x - 60, y + 50), (x + 60, y - 50)], fill=(90, 90, 100), width=12)

TRASTOS_1 = [
    (0.6, (160, 600), (-120, -90), puertecita), (0.9, (260, 600), (60, -110), puertecita), (1.1, (360, 600), (160, -60), carta),
    (2.6, (700, 1000), (-40, 40), barrote), (3.0, (800, 900), (100, 60), barrote),
]
def ex_tramo1(img, lt, t):
    d = ImageDraw.Draw(img)
    for c in range(3):                   # los buzones de la porteria, abajo a la izquierda
        x, y = 110 + c*100, 560
        d.rectangle([x - 46, y - 48, x + 46, y + 48], fill=(176, 146, 80), outline=T, width=4)
    for k in range(9):                   # la barandilla: los barrotes se doblan hacia Mag
        x = 120 + k*100; y0 = 1700 - k*104
        inc = 40*suave((lt - 2.2)/1.0) if 4 <= k <= 7 else 0
        d.line([(x, y0 - 40), (x + inc, y0 - 300)], fill=(90, 90, 100), width=10)
    d.line([(120, 1400), (1000, 480)], fill=(120, 84, 56), width=14)

def p_tramo1(lt, t):
    return tramo(lt, t, True, Mu.PAREDES["porteria"], TRASTOS_1, [], extras=ex_tramo1)

def sarten(d, x, y):
    d.line([(x, y), (x + 120, y - 40)], fill=T, width=18)
    d.ellipse([x - 70, y - 70, x + 70, y + 70], fill=(60, 60, 68), outline=T, width=5)

def bici_pegada(d, x, y):
    Mu.bici(d, x, y, 0.9)

TRASTOS_2 = [(1.4, (900, 1500), (-30, -150), bici_pegada), (4.2, (300, 900), (150, -60), sarten)]
def ex_tramo2(img, lt, t):
    d = ImageDraw.Draw(img)
    # la puerta del 1o con Tosti asomando, que pierde su sarten
    d.rectangle([60, 520, 380, 1100], fill=(40, 34, 40), outline=T, width=6)
    if lt > 3.4:
        Mu.texto(d, 220, 470, "#@%!", 60, (230, 60, 50)) if lt > 4.6 else None
        tosti(img, 230, 1100, 360, dict(enfado=1.0 if lt > 4.6 else 0.0, susto=1.0 if lt < 4.6 else 0.0), t)
    d = ImageDraw.Draw(img)
    d.rectangle([60 + 260*min(1, max(0, (lt - 3.2)/0.4)), 520, 380, 1100], fill=(132, 96, 70), outline=T, width=6)
    if lt < 1.6:                          # la bici aparcada, antes de salir rodando
        Mu.bici(d, 900 - 0*lt, 1500, 0.9)

def tosti(img, cx, suelo, h, st, t):
    """Tosti, la tostadora del 1o: mal genio, siempre echando humo."""
    d = ImageDraw.Draw(img)
    g = max(2, int(h*0.014))
    Mu.piernas(d, cx, suelo - h*0.18, suelo, h)
    w, hh = h*0.6, h*0.5
    y1 = suelo - h*0.16; y0 = y1 - hh
    d.rounded_rectangle([cx - w/2, y0, cx + w/2, y1], radius=int(w*0.2), fill=(206, 208, 216), outline=T, width=g)
    for k in (-1, 1):
        d.rounded_rectangle([cx + k*w*0.18 - w*0.08, y0 - h*0.02, cx + k*w*0.18 + w*0.08, y0 + h*0.04], radius=4, fill=T)
    d.rectangle([cx + w/2, y0 + hh*0.3, cx + w/2 + h*0.05, y0 + hh*0.45], fill=T)
    Mu.ojos(d, cx, y0 + hh*0.45, w*0.9, (206, 208, 216), st.get("mira", (0.5, 0)), 0, 0, 0, 0, st.get("susto", 0), st.get("enfado", 0))
    Mu.boca(d, cx, y0 + hh*0.75, w*0.9, "grito" if st.get("enfado") else "o")
    if st.get("enfado"):
        Mu.humo_enfado(d, cx, y0 - 10, 30, t)
    for lado in (-1, 1):
        hb = (cx + lado*w/2, y0 + hh*0.6)
        Mu.brazo_fino(d, hb, (hb[0] + lado*h*0.1, hb[1] - h*0.08), (hb[0] + lado*h*0.12, hb[1] - h*0.2), h)

def p_tramo2(lt, t):
    viejas = [(None, None, d_, f) for _, __, d_, f in TRASTOS_1]
    return tramo(lt, t, False, Mu.PAREDES["p1"], TRASTOS_2, viejas, extras=ex_tramo2)

# ---------------------------------------------------------------- 5. la mirilla
def p_mirilla(lt, t):
    if lt < 1.8:                          # lo que ven: el ojo de pez de la mirilla
        img, cam = p_tramo2(5.2 + lt*0.4, t)
        img = Mu.recorte(img, 560, 1050, 1.25)
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).ellipse([W/2 - 470, H/2 - 470, W/2 + 470, H/2 + 470], fill=255)
        out = Image.new("RGB", (W, H), (8, 8, 10))
        out.paste(img, (0, 0), m)
        d = ImageDraw.Draw(out)
        d.ellipse([W/2 - 470, H/2 - 470, W/2 + 470, H/2 + 470], outline=(40, 40, 46), width=30)
        return out, (W/2, H/2, 1.0)
    # y desde fuera: la puerta con DOS ojos apretados en una mirilla
    img = Image.new("RGB", (W, H), Mu.PAREDES["p2"]); d = ImageDraw.Draw(img)
    d.rectangle([140, 200, 940, H], fill=(132, 96, 70), outline=T, width=10)
    cx, cy = 540, 760
    d.ellipse([cx - 170, cy - 120, cx + 170, cy + 120], fill=(214, 176, 70), outline=T, width=8)
    d.ellipse([cx - 140, cy - 95, cx + 140, cy + 95], fill=(20, 20, 24))
    for lado, (col, k) in zip((-1, 1), (((250, 250, 250), 0.0), ((250, 250, 250), 0.4))):
        if lado > 0 and lt < 2.4: continue
        ex = cx + lado*55 if lt >= 2.4 else cx
        r = 62 if lt >= 2.4 else 80
        d.ellipse([ex - r, cy - r*0.8, ex + r, cy + r*0.8], fill=col, outline=T, width=4)
        pr = r*0.4
        d.ellipse([ex - pr + 10, cy - pr, ex + pr + 10, cy + pr], fill=T)
        if parpadeo(lt, 1.1, lado*0.3) > 0.5:
            d.rectangle([ex - r, cy - r*0.8, ex + r, cy + r*0.8], fill=(20, 20, 24))
    if lt > 2.4:
        Mu.texto(d, cx, cy - 260, "!", 120, (255, 214, 60))
    return img, (cx, cy, 1.0 + 0.1*lt)

# ---------------------------------------------------------------- 6. Don Huevo
def p_huevo(lt, t):
    img = Image.new("RGB", (W, H), Mu.PAREDES["p2"]); d = ImageDraw.Draw(img)
    Mu.suelo_madera(d, SUELO, H)
    d.rectangle([0, 0, 160, H], fill=tuple(int(v*0.85) for v in Mu.PAREDES["p2"]), outline=T, width=6)    # la pared de la izquierda
    # Don Huevo con su cartel de PROHIBIDO SOFAS
    aplasta = suave((lt - 2.6)/0.25)*(1 - suave((lt - 4.2)/0.3))
    hx = 520 - 330*suave((lt - 2.2)/0.4)
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    Mu.huevo_cara(capa, hx, SUELO - 300, 520, dict(mira=(0.9, 0.0), enfado=1.0, boca="grito" if lt < 2.6 else "o", susto=1.0 if lt > 2.4 else 0.0), t)
    if aplasta > 0:
        bb = capa.getbbox()
        if bb:
            trozo = capa.crop(bb)
            nw = max(10, int(trozo.width*(1 - 0.75*aplasta)))
            trozo = trozo.resize((nw, int(trozo.height*(1 + 0.15*aplasta))))
            capa = Image.new("RGBA", (W, H), (0, 0, 0, 0)); capa.paste(trozo, (160, int(bb[1] - trozo.height*0.07)), trozo)
    img.paste(capa, (0, 0), capa)
    d = ImageDraw.Draw(img)
    if lt < 2.6:                          # el cartel: un sofa tachado
        x = hx + 230
        d.line([(x, SUELO - 300), (x, SUELO - 640)], fill=(120, 84, 56), width=12)
        d.rounded_rectangle([x - 130, SUELO - 820, x + 130, SUELO - 620], radius=16, fill=(252, 250, 240), outline=T, width=6)
        Mu.icono(d, "sofa", x, SUELO - 720, 150)
        d.line([(x - 100, SUELO - 800), (x + 100, SUELO - 640)], fill=(220, 40, 40), width=14)
    if 2.6 < lt < 3.4:
        Mu.texto(d, 300, 700, "SQUISH!", 90, (255, 214, 60))
    if 4.2 < lt < 5.0:
        Mu.texto(d, 300, 700, "BOING!", 80, (255, 214, 60))
    if lt > 4.4:
        estrellas(d, 300, SUELO - 700, t)
    # el sofa (con todos los trastos) pasa de derecha a izquierda empujado
    pasa = suave((lt - 1.8)/3.4)
    sx = 1350 - 1100*pasa
    Mu.mag(img, sx - 330, SUELO + 40, HM, dict(gafas_sol=True, mira=(-0.8, 0), tira=(sx - 220, SUELO - 330), fondo=Mu.PAREDES["p2"]), t)
    Mu.sofa(img, sx, SUELO - 330, 430, ang=0, rasgado=1.0)
    d = ImageDraw.Draw(img)
    Mu.bici(d, sx - 20, SUELO - 470, 0.9); sarten(d, sx + 150, SUELO - 400); puertecita(d, sx - 130, SUELO - 420)
    if lt > 3.0:                          # el cartel se queda pegado al sofa
        d.rounded_rectangle([sx + 40, SUELO - 560, sx + 220, SUELO - 420], radius=12, fill=(252, 250, 240), outline=T, width=5)
        Mu.icono(d, "sofa", sx + 130, SUELO - 490, 100)
        d.line([(sx + 60, SUELO - 545), (sx + 200, SUELO - 435)], fill=(220, 40, 40), width=10)
    Mu.poke(img, sx + 330, SUELO + 40, HP, dict(pose="abrazo", mira=(-0.8, 0), boca="dolor", ceja=0.6, inclina=-0.08, fase=lt*6), t)
    return img, (560, 1080, 1.04)

# ---------------------------------------------------------------- 7. el rellano: la puerta equivocada
def p_rellano(lt, t):
    img = Image.new("RGB", (W, H), Mu.PAREDES["p2"]); d = ImageDraw.Draw(img)
    Mu.suelo_madera(d, SUELO, H)
    # 2A (la de Bubble, entreabierta, con corona de corazones) y 2B (la de Poke)
    Mu.puerta(d, 280, SUELO, "2A", abre=0.25 if lt < 4.6 else 0.9, color=(176, 120, 150), alto=620, ancho=300)
    for k in range(8):
        a = k/8*2*math.pi
        Mu.corazon(d, 280 + math.cos(a)*70, SUELO - 470 + math.sin(a)*70, 18)
    Mu.puerta(d, 820, SUELO, "2B", alto=620, ancho=300)
    # Poke mira su llave: 2B
    st = dict(pose="caido", mira=(0.0, 0.8), boca="dolor", ceja=0.5)
    if 0.6 < lt < 2.4:
        st.update(pose="saluda", mira=(0.3, -0.6), boca="o", ceja=0.0)
    if 2.4 <= lt < 3.6:
        st.update(mira=(-0.8, 0.0), boca="o", ceja=0.3)
    if 3.6 <= lt < 4.4:
        st.update(pose="arriba", boca="sonrisa", ceja=0.0)       # se encoge de hombros: vale
    if lt >= 4.4:
        st.update(pose="abrazo", inclina=-0.08, boca="dolor", fase=lt*6)
    mueve = suave((lt - 4.4)/1.4)
    px = 720 - 300*mueve
    # el sofa: apoyado en el suelo junto a la 2B, hasta que lo cogen y lo meten en la 2A
    sx = 960 - 560*mueve; sy = SUELO - 130 - 200*suave((lt - 4.4)/0.3)
    Mu.sofa(img, sx, sy, 430, rasgado=1.0)
    d = ImageDraw.Draw(img)
    info = Mu.poke(img, px, SUELO + 40, HP, st, t)
    d = ImageDraw.Draw(img)
    if 0.6 < lt < 2.4:                    # la etiqueta de la llave, en grande
        mx, my = info["manos"][1]
        d.line([(mx, my), (mx + 40, my - 80)], fill=T, width=4)
        d.rounded_rectangle([mx - 10, my - 200, mx + 170, my - 80], radius=14, fill=(252, 236, 160), outline=T, width=5)
        d.text((mx + 80, my - 140), "2B", font=fuente(70), fill=T, anchor="mm")
    # Mag señala la otra, muy seguro: 2A
    st_m = dict(gafas_sol=True, guino=2.6 < lt < 3.6, pistolas=2.4 < lt < 3.8, mira=(-0.8, 0), fondo=Mu.PAREDES["p2"])
    if lt >= 4.4:
        st_m.update(pistolas=False, tira=(px - 260, SUELO - 330))
    mxx = 420 - 260*mueve
    if lt >= 4.4:
        st_m.update(tira=(sx - 200, sy))
    if st_m.get("pistolas"):            # señala hacia la 2A: se dibuja girado
        capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        Mu.mag(capa, W - mxx, SUELO + 40, HM, dict(st_m, fondo=Mu.PAREDES["p2"]), t)
        capa = ImageOpsMirror(capa)
        img.paste(capa, (0, 0), capa)
    else:
        Mu.mag(img, mxx, SUELO + 40, HM, st_m, t)
    d = ImageDraw.Draw(img)
    if lt > 5.8:
        Mu.texto(d, 280, 700, "CRASH!", 100, (255, 214, 60))
    return img, (560, 1080, 1.04)

def ImageOpsMirror(c):
    from PIL import ImageOps
    return ImageOps.mirror(c)

# ---------------------------------------------------------------- 8. el flechazo
def p_flechazo(lt, t):
    img = Image.new("RGB", (W, H), (226, 206, 236)); d = ImageDraw.Draw(img)
    Mu.suelo_madera(d, SUELO, H, color=(206, 170, 130))
    Mu.ventana(d, 560, 380, 960, 760, cielo=(250, 214, 190))
    Mu.planta(d, 960, SUELO, 1.3)
    for k, x in enumerate((140, 300)):    # cojines de corazon y un tocadiscos
        Mu.corazon(d, x, SUELO - 160, 60, (240, 130, 170))
    lento = 2.4 < lt < 6.0
    # el sofa ha entrado de golpe, con todos los trastos
    Mu.sofa(img, 300, SUELO - 130, 480, ang=-8, rasgado=1.0)
    d = ImageDraw.Draw(img)
    Mu.bici(d, 260, SUELO - 300, 0.9); sarten(d, 470, SUELO - 260); puertecita(d, 120, SUELO - 280)
    # Bubble, que estaba regando la planta
    by = 760 - 260*suave(lt/0.4)*(1 - suave((lt - 2.2)/1.2)) + 20*math.sin(t*2)
    st_b = dict(mira=(-0.8, 0.3), susto=1.0 if lt < 2.2 else 0.0, boca="grito" if lt < 1.2 else "o", cuerda=True,
                rubor=lt > 3.4, feliz=1.0 if 3.4 < lt < 6.2 else 0.0)
    if lt >= 6.4:
        st_b.update(feliz=0.0, boca="o", mira=((-1, 1)[int(lt/0.4) % 2]*0.6, 0.2), rubor=True)
    Mu.bubble(img, 760, by, 440, st_b, t)
    d = ImageDraw.Draw(img)
    # Poke asoma por encima del sofa
    sube = suave((lt - 1.4)/0.6)
    st_p = dict(pose="caido", mira=(0.8, -0.2), boca="o", amor=1.0 if lt > 3.0 else 0.0)
    if lt > 3.0:
        st_p.update(boca="abierta", pose="pecho")
    if lt >= 6.0:
        st_p.update(pose="caido", amor=0.0, susto=0.8, boca="o", mira=(-0.6, -0.4))
    px = 380 if lt < 6.0 else 380 - 200*suave((lt - 6.0)/0.4)
    Mu.poke(img, px, SUELO - 120 + 380*(1 - sube), HP, st_p, t)
    d = ImageDraw.Draw(img)
    if lento:                              # corazoncitos y destellos
        for k in range(5):
            f = ((lt - 2.4)*0.6 + k/5) % 1.0
            Mu.corazon(d, 380 + (k - 2)*90 + math.sin(t*2 + k)*20, 900 - f*500, 22*(1 - f) + 8)
    # Mag asoma por la puerta y tambien se enamora... y aparta a Poke
    if lt > 5.0:
        mx = 1300 - 650*suave((lt - 5.0)/0.8) if lt < 6.0 else 650 - 120*suave((lt - 6.0)/0.4)
        st_m = dict(amor=1.0 if lt > 5.6 else 0.0, gafas_sol=lt < 5.6, mira=(-0.6, -0.2), fondo=(226, 206, 236))
        Mu.mag(img, mx, SUELO + 40, HM, st_m, t)
        d = ImageDraw.Draw(img)
        if 5.5 < lt < 5.9:                  # se le caen las gafas
            k = (lt - 5.5)/0.4
            d.rounded_rectangle([mx - 70, SUELO - 520 + 300*k, mx + 70, SUELO - 470 + 300*k], radius=10, fill=(24, 24, 30), outline=T, width=4)
    if lt > 6.6:
        Mu.texto(d, 760, by - 330, "?", 110, (255, 214, 60))
    return img, (600, 1050, 1.04 + (0.14*suave((lt - 2.4)/1.2) if lt < 6.0 else 0.14*(1 - suave((lt - 6.0)/0.4))))

# ---------------------------------------------------------------- 9. las cotillas
def p_cotillas(lt, t):
    img = Image.new("RGB", (W, H), Mu.PAREDES["p2"]); d = ImageDraw.Draw(img)
    Mu.suelo_madera(d, SUELO, H)
    d.rectangle([180, 600, 900, SUELO], fill=(36, 30, 36), outline=T, width=8)          # su puerta, abierta del todo
    d.rectangle([900, 600, 1000, SUELO], fill=(132, 96, 70), outline=T, width=6)
    escandalo = suave((lt - 1.0)/0.3)
    Mu.salero(img, 380, SUELO + 30, 440, dict(mira=(0.9, 0.0), susto=escandalo, boca="o", tapa_boca=lt > 1.2), t)
    Mu.salero(img, 680, SUELO + 30, 440, dict(mira=(0.9, 0.0) if lt < 3.0 else (-0.6, -0.4), susto=escandalo,
              boca="grito" if lt > 3.4 else "o"), t, pimienta=True)
    d = ImageDraw.Draw(img)
    if lt > 1.3:                           # el cotilleo, en dibujos
        iconos = ["cactus", "corazon", "globo"] + (["+", "anillo"] if lt > 2.6 else [])
        Mu.bocadillo_dibujos(d, 540, 420, iconos, 100 if len(iconos) == 3 else 86, cola=(0, 1))
    if lt > 3.4:                           # ¡achis! la pimienta lo llena todo
        k = suave((lt - 3.4)/0.6)
        rnd = random.Random(3)
        for i in range(int(160*k)):
            x = 680 + rnd.uniform(-600, 600)*k; y = SUELO - 380 + rnd.uniform(-500, 500)*k
            d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(60, 50, 46))
        if lt < 4.4:
            Mu.texto(d, 680, 900, "ACHOO!", 120, (250, 250, 250))
    sacude = math.sin(t*50)*16 if 3.4 < lt < 4.0 else 0
    return img, (560 + sacude, 1000, 1.06)

def p_fin(lt, t, dur=3.5):
    img = Image.new("RGB", (W, H), (34, 32, 44)); d = ImageDraw.Draw(img)
    a = suave(lt/0.5)*suave((dur - lt)/0.4)
    c = lambda col: tuple(int(34 + (v - 34)*a) for v in col)
    d.rounded_rectangle([W/2 - 300, 640, W/2 + 300, 790], radius=24, fill=c((52, 50, 64)), outline=c((255, 214, 90)), width=6)
    d.text((W/2, 715), "BLOCK 7", font=fuente(100), fill=c((255, 214, 90)), anchor="mm")
    d.text((W/2, 880), "Ep. 1 · The Sofa", font=fuente(54), fill=c((240, 240, 240)), anchor="mm")
    b = suave((lt - 1.0)/0.5)*suave((dur - lt)/0.4)
    cb = lambda col: tuple(int(34 + (v - 34)*b) for v in col)
    d.text((W/2, 1130), "NEXT:", font=fuente(40), fill=cb((200, 200, 210)), anchor="mm")
    d.text((W/2, 1200), "The Rumor", font=fuente(66), fill=cb((255, 140, 160)), anchor="mm")
    return img, (W/2, H/2, 1.0)

# ---------------------------------------------------------------- el montaje
# ---------------------------------------------------------------- version centrada: Poke contra el sofa
def bombilla(d, x, y, s=1.0):
    d.ellipse([x - 50*s, y - 60*s, x + 50*s, y + 40*s], fill=(255, 236, 120), outline=T, width=5)
    d.rectangle([x - 24*s, y + 36*s, x + 24*s, y + 70*s], fill=(180, 180, 190), outline=T, width=4)
    for a in range(-150, -20, 30):
        r = math.radians(a)
        d.line([(x + math.cos(r)*75*s, y - 10*s + math.sin(r)*75*s), (x + math.cos(r)*110*s, y - 10*s + math.sin(r)*110*s)],
               fill=(255, 214, 60), width=8)

def etiqueta(d, mx, my, texto="2B"):
    d.line([(mx, my), (mx + 40, my - 80)], fill=T, width=4)
    d.rounded_rectangle([mx - 10, my - 200, mx + 170, my - 80], radius=14, fill=(252, 236, 160), outline=T, width=5)
    d.text((mx + 80, my - 140), texto, font=fuente(70), fill=T, anchor="mm")

def p_fachada2(lt, t):
    img = Image.new("RGB", (W, H), (180, 220, 244)); d = ImageDraw.Draw(img)
    d.rectangle([0, 160, W, SUELO], fill=(232, 196, 168), outline=T, width=6)
    for fila in range(0, 30):
        for col in range(10):
            x = col*120 + (60 if fila % 2 else 0); y = 160 + fila*46
            if y < SUELO - 40:
                d.rectangle([x, y, x + 116, y + 42], outline=(214, 176, 150), width=2)
    d.rounded_rectangle([W/2 - 210, 180, W/2 + 210, 280], radius=18, fill=(52, 50, 64), outline=T, width=6)
    Mu.texto(d, W/2, 230, "BLOCK 7", 66, (255, 214, 90))
    d.rectangle([560, 900, 960, SUELO], fill=(170, 210, 220), outline=T, width=8)
    d.line([(760, 900), (760, SUELO)], fill=T, width=6)
    Mu.ventana(d, 90, 420, 470, 780); Mu.ventana(d, 620, 420, 960, 760)
    d.rectangle([0, SUELO, W, H], fill=(196, 196, 204)); d.line([(0, SUELO), (W, SUELO)], fill=T, width=6)
    x = -260 + 520*suave(lt/2.6)
    Mu.sofa(img, x + 330, SUELO - 120, 560)
    st = dict(pose="abrazo" if lt < 2.6 else "saluda", fase=lt*6 if lt < 2.6 else None, dir=0.6, mira=(0.8, 0.0),
              boca="dolor" if lt < 2.6 else "abierta", ceja=0.5 if lt < 2.6 else 0.0, inclina=0.08 if lt < 2.6 else 0.0,
              feliz=1.0 if lt > 2.8 else 0.0)
    info = Mu.poke(img, x, SUELO + 40, HP, st, t)
    d = ImageDraw.Draw(img)
    if lt < 2.6:
        Mu.sudor(d, info["cara"][0] - 120, info["top"] + 40, 40, t)
    else:
        etiqueta(d, *info["manos"][1])
    return img, (W/2, H/2, 1.0)

ANG_ESCALERA = math.degrees(math.atan2(1000, 960))

def p_empuja(lt, t):
    """Solo, empujando el sofa escalera arriba. Se le resbala encima. Otra vez. Y otra."""
    img, a, b = escalera_fondo(Mu.PAREDES["porteria"], True); d = ImageDraw.Draw(img)
    d.line([(120, 1400), (1000, 480)], fill=(120, 84, 56), width=14)
    pos = lambda f: (a[0] + (b[0] - a[0])*f, a[1] + (b[1] - a[1])*f)
    # sube un poco... y se resbala
    tramos = [(0.0, 1.6, 0.14, 0.32), (1.6, 2.1, 0.32, 0.10), (2.4, 4.2, 0.10, 0.40), (4.2, 4.7, 0.40, 0.08),
              (5.0, 6.0, 0.08, 0.20), (6.0, 6.4, 0.20, 0.0)]
    us = 0.14
    resbala = False
    for t0, t1, u0, u1 in tramos:
        if t0 <= lt < t1:
            k = (lt - t0)/(t1 - t0)
            us = u0 + (u1 - u0)*(suave(k) if u1 > u0 else k*k); resbala = u1 < u0
            break
        if lt >= t1:
            us = u1
    debajo = lt > 6.3
    sc = pos(us); sc = (sc[0] + 60, sc[1] - 200)
    if not debajo:
        pp = pos(max(0.0, us - 0.17))
        if resbala:
            pp = pos(max(0.0, us - 0.13))
        st = dict(pose="abrazo", inclina=0.1, mira=(0.8, -0.4), boca="dolor" if not resbala else "grito", ceja=0.6,
                  susto=1.0 if resbala else 0.0, fase=None if resbala else lt*6)
        info = Mu.poke(img, pp[0], pp[1] + 40, HP, st, t)
        Mu.sudor(ImageDraw.Draw(img), info["cara"][0] - 110, info["top"] + 30, 34 + 8*(lt/6), t)
    Mu.sofa(img, sc[0], sc[1], 470, ang=ANG_ESCALERA, rasgado=0.2 + 0.5*lt/6.4)
    d = ImageDraw.Draw(img)
    for t0 in (1.6, 4.2, 6.0):
        if t0 < lt < t0 + 0.5:
            Mu.texto(d, 540, 700, "WHEEE-BONK!" if t0 < 6 else "BONK!", 80, (255, 214, 60))
    if debajo:
        Mu.piernas(d, 150, 1720, 1780, HP)
        estrellas(d, 170, 1450, t)
    return img, (W/2, H/2, 1.0)

def p_idea(lt, t):
    """Se mira los pinchos... y se le enciende la bombilla."""
    img, a, b = escalera_fondo(Mu.PAREDES["porteria"], True); d = ImageDraw.Draw(img)
    Mu.sofa(img, 330, 1560, 470, ang=ANG_ESCALERA, rasgado=0.7)
    st = dict(pose="caido", mira=(0, 0), boca="dolor", ceja=0.6)
    if lt < 1.0:
        st.update(mira=(math.sin(t*8), math.cos(t*8)))
    if 1.0 <= lt < 2.4:
        st.update(pose="saluda", mira=(0.9, -0.9), boca="o", ceja=0.0)
    if lt >= 2.4:
        st.update(pose="arriba", feliz=1.0, boca="abierta", ceja=0.0)
    info = Mu.poke(img, 700, 1760, 640, st, t)
    d = ImageDraw.Draw(img)
    if lt < 1.0:
        estrellas(d, 700, info["top"] - 60, t)
    if 1.2 < lt < 2.4:                    # mira de cerca sus pinchos
        Mu.texto(d, 900, info["top"] - 20, "?", 90, (255, 214, 60))
    if lt >= 2.4:
        bombilla(d, 700, info["top"] - 160, 1.1)
    return img, (640, 1350, 1.25)

def p_tira(lt, t):
    """Ahora tira desde arriba con los brazos clavados en el sofa. Sube volando. Y luego, el sofa en la cabeza."""
    img, a, b = escalera_fondo(Mu.PAREDES["p1"], False); d = ImageDraw.Draw(img)
    d.line([(960, 1400), (80, 480)], fill=(120, 84, 56), width=14)
    pos = lambda f: (a[0] + (b[0] - a[0])*f, a[1] + (b[1] - a[1])*f)
    if lt < 3.8:
        up = 0.22 + 0.55*suave(lt/3.6)
        pp = pos(up); us = up - 0.2
        sc = pos(us); sc = (sc[0] - 40, sc[1] - 200)
        Mu.sofa(img, sc[0], sc[1], 470, ang=-ANG_ESCALERA, rasgado=0.9)
        d = ImageDraw.Draw(img)
        rnd = random.Random(int(t*10))
        for i in range(5):                # trocitos de espuma volando
            ex_, ey_ = sc[0] + rnd.uniform(-200, 200), sc[1] + rnd.uniform(-150, 150)
            d.ellipse([ex_ - 12, ey_ - 10, ex_ + 12, ey_ + 10], fill=(250, 248, 230), outline=(180, 176, 160), width=2)
        st = dict(pose="abrazo", mira=(0.8, 0.6), feliz=1.0, boca="abierta", inclina=0.1, fase=lt*10)
        Mu.poke(img, pp[0], pp[1] + 40, HP, st, t)
        if lt < 2.6:
            Mu.texto(ImageDraw.Draw(img), 540, 600, "ZOOM!", 90, (255, 214, 60))
        return img, (W/2, H/2, 1.0)
    # el sofa a la cabeza: ya no ve nada
    pp = pos(0.77)
    tamb = math.sin(t*6)*30
    info = Mu.poke(img, pp[0] + tamb, pp[1] + 40, HP, dict(pose="arriba", fase=lt*6, boca="o"), t)
    Mu.sofa(img, pp[0] + tamb, info["cara"][1] - 40, 470, ang=math.sin(t*6)*6, rasgado=0.9)
    return img, (W/2, H/2, 1.0)

def p_rellano2(lt, t):
    """A ciegas: se pasa su puerta (2B)... y entra en la que esta abierta (2A)."""
    img = Image.new("RGB", (W, H), Mu.PAREDES["p2"]); d = ImageDraw.Draw(img)
    Mu.suelo_madera(d, SUELO, H)
    Mu.puerta(d, 260, SUELO, "2A", abre=0.85, color=(176, 120, 150), alto=620, ancho=300)
    for k in range(8):
        aa = k/8*2*math.pi
        Mu.corazon(d, 260 + math.cos(aa)*70, SUELO - 470 + math.sin(aa)*70, 18)
    Mu.puerta(d, 820, SUELO, "2B", alto=620, ancho=300)
    if lt < 1.8:
        x = 1300 - 400*suave(lt/1.6)
    elif lt < 2.4:                        # BONK contra su propia puerta, y rebota
        x = 900 + 60*suave((lt - 1.8)/0.3)
    else:
        x = 960 - 700*suave((lt - 2.4)/2.6)
    tamb = math.sin(t*6)*25
    info = Mu.poke(img, x + tamb, SUELO + 40, HP, dict(pose="arriba", fase=lt*6, boca="o"), t)
    Mu.sofa(img, x + tamb, info["cara"][1] - 40, 470, ang=math.sin(t*6)*6, rasgado=0.9)
    d = ImageDraw.Draw(img)
    if 1.8 < lt < 2.3:
        Mu.texto(d, 820, 760, "BONK!", 90, (255, 214, 60))
    return img, (W/2, H/2, 1.0)

def p_flechazo2(lt, t):
    """En casa de Bubble. CRASH. Flechazo. El error. Y ella se sienta en el sofa: quedate."""
    img = Image.new("RGB", (W, H), (226, 206, 236)); d = ImageDraw.Draw(img)
    Mu.suelo_madera(d, SUELO, H, color=(206, 170, 130))
    Mu.ventana(d, 560, 380, 960, 760, cielo=(250, 214, 190))
    Mu.planta(d, 980, SUELO, 1.2)
    sx = 480; seat = SUELO - 120
    if lt < 1.2:                          # entra con el sofa en la cabeza
        x = 1300 - 700*suave(lt/1.1)
        info = Mu.poke(img, x, SUELO + 40, HP, dict(pose="arriba", fase=lt*6, boca="o"), t)
        Mu.sofa(img, x, info["cara"][1] - 40, 470, rasgado=0.9)
    else:
        Mu.sofa(img, sx, SUELO - 130, 520, rasgado=0.9)
    d = ImageDraw.Draw(img)
    # Bubble
    if lt < 6.0:
        by = 800 - 300*suave((lt - 1.2)/0.3)*(1 - suave((lt - 1.9)/1.0)) + 20*math.sin(t*2)
        bx = 760
    else:                                 # baja y se sienta en una punta del sofa
        k = suave((lt - 6.0)/0.8); bx = 760 - 440*k; by = 800 + (seat - 250 - 800)*k
    st_b = dict(mira=(-0.8, 0.3), susto=1.0 if 1.2 < lt < 2.2 else 0.0, boca="grito" if 1.2 < lt < 1.8 else "sonrisa", cuerda=True,
                rubor=lt > 3.0, feliz=1.0 if 3.0 < lt < 4.6 or lt > 7.0 else 0.0, pose="caido")
    if 6.8 < lt < 7.8:                    # da palmaditas en el sofa: siéntate
        st_b["pose"] = "cuerda"
    if lt > 1.2:
        Mu.bubble(img, bx, by, 420, st_b, t)
    d = ImageDraw.Draw(img)
    # Poke
    if lt >= 1.2:
        st = dict(pose="caido", mira=(0.8, -0.2), boca="o")
        if 2.4 <= lt < 4.4:
            st.update(amor=1.0, boca="abierta", pose="pecho")
        if 4.4 <= lt < 5.2:               # mira la llave: 2B... ¿y esta puerta?
            st.update(pose="saluda", mira=(0.5, -0.8), boca="o")
        if 5.2 <= lt < 6.8:               # vergüenza: se va
            st.update(pose="abrazo", mira=(-0.8, 0.0), boca="dolor", ceja=0.6, susto=0.4)
        if lt >= 6.8:
            st.update(pose="caido", mira=(-0.8, -0.2), amor=1.0 if lt > 7.4 else 0.0, boca="abierta")
        if lt < 7.6:
            px = 830 if lt < 5.2 else 830 + 120*suave((lt - 5.2)/0.6)*(1 - suave((lt - 6.8)/0.4))
            suelo_p = SUELO + 40
        else:                             # se sienta en la otra punta
            k = suave((lt - 7.6)/0.6); px = 830 + (650 - 830)*k; suelo_p = SUELO + 40 + (seat - 30 - SUELO - 40)*k
        info = Mu.poke(img, px, suelo_p, HP, st, t)
        d = ImageDraw.Draw(img)
        if 4.4 <= lt < 5.2:
            etiqueta(d, *info["manos"][1])
        if 5.2 <= lt < 6.8:
            Mu.sudor(d, info["cara"][0] - 110, info["top"] + 30, 36, t)
    if 1.2 < lt < 1.7:
        Mu.texto(d, 520, 900, "CRASH!", 100, (255, 214, 60))
    if 2.4 < lt < 4.4:
        for k in range(5):
            f = ((lt - 2.4)*0.6 + k/5) % 1.0
            Mu.corazon(d, 800 + (k - 2)*70 + math.sin(t*2 + k)*20, 900 - f*500, 22*(1 - f) + 8)
    if lt > 8.2:                          # un corazoncito entre los dos
        Mu.corazon(d, 490, seat - 520 - (lt - 8.2)*80, 30)
    zoom = 1.04 + 0.12*suave((lt - 2.4)/1.0)*(1 - suave((lt - 4.4)/0.5))
    return img, (640, 1050, zoom)

def p_ojos(lt, t):
    """Dos segundos: la puerta de enfrente, dos ojos en la mirilla... y el cotilleo ya en marcha."""
    img = Image.new("RGB", (W, H), Mu.PAREDES["p2"]); d = ImageDraw.Draw(img)
    d.rectangle([140, 380, 940, H], fill=(132, 96, 70), outline=T, width=10)
    d.rounded_rectangle([440, 420, 640, 500], radius=10, fill=(250, 246, 236), outline=T, width=4)
    d.text((540, 460), "2C", font=fuente(50), fill=T, anchor="mm")
    cx, cy = 540, 900
    d.ellipse([cx - 170, cy - 120, cx + 170, cy + 120], fill=(214, 176, 70), outline=T, width=8)
    d.ellipse([cx - 140, cy - 95, cx + 140, cy + 95], fill=(20, 20, 24))
    for lado in (-1, 1):
        ex = cx + lado*55; r = 62
        d.ellipse([ex - r, cy - r*0.8, ex + r, cy + r*0.8], fill=(250, 250, 250), outline=T, width=4)
        d.ellipse([ex - 25 - 14, cy - 25, ex + 25 - 14, cy + 25], fill=T)
    if lt > 0.8:
        Mu.bocadillo_dibujos(d, 540, 640, ["cactus", "corazon", "globo"], 100, cola=(0, 1))
    return img, (cx, cy - 100, 1.0 + 0.06*lt)

GUION = [
    (p_fachada2, 4.0, [(0.0, "tema"), (0.0, "raspa2.6"), (2.8, "tin")]),
    (p_ascensor, 8.5, [(0.8, "bonk"), (2.4, "bonk"), (4.2, "tin"), (5.6, "sirena1.4"), (7.0, "silbido_corto"), (7.4, "bonk"), (7.5, "pito")]),
    (p_empuja, 7.0, [(0.0, "raspa1.6"), (1.6, "desliza"), (2.0, "bonk"), (2.4, "raspa1.8"), (4.2, "desliza"), (4.6, "bonk"),
                     (5.0, "raspa1.0"), (6.0, "desliza"), (6.3, "bonk"), (6.4, "pito")]),
    (p_idea, 4.0, [(1.0, "susto"), (2.4, "ding")]),
    (p_tira, 6.0, [(0.0, "raspa3.6"), (0.0, "pasos3.6"), (3.8, "boing"), (4.0, "pasos2.0")]),
    (p_rellano2, 5.4, [(0.0, "pasos1.8"), (1.8, "bonk"), (2.4, "pasos2.6")]),
    (p_flechazo2, 9.4, [(1.2, "crash"), (1.3, "susto"), (2.4, "flechazo"), (4.4, "tin"), (5.2, "susto"), (6.8, "tin"), (7.4, "flechazo")]),
    (p_ojos, 3.0, [(0.8, "tin")]),
    (lambda lt, t: p_fin(lt, t, 3.5), 3.5, [(0.0, "fin")]),
]

def tabla():
    t = 0.0; out = []
    for fn, dur, sfx in GUION:
        out.append((t, t + dur, fn, sfx)); t += dur
    return out, t

TABLA, DUR = tabla()
_I = {fn: a for a, b, fn, s in TABLA}
SILENCIOS = [(_I[p_flechazo2] + 2.4, _I[p_flechazo2] + 4.4), (_I[p_idea] + 1.0, _I[p_idea] + 2.4)]

def fotograma(t):
    for a, b, fn, _ in TABLA:
        if a <= t < b:
            img, (cx, cy, z) = fn(t - a, t)
            break
    else:
        img, (cx, cy, z) = Image.new("RGB", (W, H)), (W/2, H/2, 1.0)
    if z > 1.001 or abs(cx - W/2) > 1 or abs(cy - H/2) > 1:
        img = Mu.recorte(img, cx, cy, max(1.0, z))
    return img

def main():
    Path(OUT).mkdir(exist_ok=True)
    args = sys.argv[1:]
    if args and args[0] == "fotos":
        for i, (a, b, fn, _) in enumerate(TABLA):
            for k, f in enumerate((0.25, 0.55, 0.9)):
                fotograma(a + (b - a)*f).resize((270, 480)).save(OUT + f"s1_{i:02d}_{k}.jpg", quality=85)
        print(f"{len(TABLA)} planos, {DUR:.1f} s"); return
    if args and args[0] == "en":
        for s in args[1:]:
            fotograma(float(s)).resize((540, 960)).save(OUT + f"s1_en_{float(s):05.1f}.jpg", quality=88)
        return
    S.audio(OUT + "sofa_audio.wav", TABLA, DUR, SILENCIOS)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-i", OUT + "sofa_audio.wav", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19",
                          "-preset", "medium", "-c:a", "aac", "-b:a", "192k", "-shortest", OUT + "BLOCK7_ep01_sofa.mp4"], stdin=subprocess.PIPE)
    for i in range(int(DUR*FPS)):
        p.stdin.write(fotograma(i/FPS).tobytes())
    p.stdin.close(); p.wait()
    print(f"hecho: {DUR:.1f} s")

if __name__ == "__main__":
    main()
