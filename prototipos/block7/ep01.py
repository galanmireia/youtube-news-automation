"""BLOCK 7 · Ep. 1 — THE NEW NEIGHBOUR (~53 s, vertical, sin voz).

Poke, un cactus que solo quiere abrazos, se muda al edificio. El gato portero
le da la llave con un palo, el globo del 2o huye volando (y el ladrillo le
cae en el pie), Don Huevo le cierra con tres cerrojos y le pasa una nota.
Solo en su piso, abraza la almohada... que revienta. Cubierto de plumas, por
fin es blandito.

Pistas para el siguiente: al subir por la escalera se ve por el corte del
edificio a Pop y Mag discutiendo en el 3o (Ep. 2, "The Argument").
"""
import math, random, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mundo as Mu
from mundo import T, W, H, suave, parpadeo, fuente

OUT = str(Path(__file__).resolve().parent) + "/salida/"
FPS = 25
SUELO = 1500                 # la linea del suelo en los interiores
HP = 560                     # el alto de Poke

# ---------------------------------------------------------------- objetos
def maleta(d, x, y, s=1.0):
    d.rounded_rectangle([x - 70*s, y, x + 70*s, y + 110*s], radius=int(14*s), fill=(214, 96, 84), outline=T, width=5)
    d.rounded_rectangle([x - 30*s, y - 28*s, x + 30*s, y + 4*s], radius=int(10*s), outline=T, width=6)
    d.line([(x - 70*s, y + 40*s), (x + 70*s, y + 40*s)], fill=(170, 70, 62), width=4)
    d.rectangle([x - 20*s, y + 30*s, x + 20*s, y + 52*s], fill=(240, 200, 90), outline=T, width=3)

def llave(d, x, y, s=1.0):
    d.ellipse([x - 22*s, y - 22*s, x + 22*s, y + 22*s], outline=(214, 170, 50), width=int(9*s))
    d.line([(x + 20*s, y), (x + 80*s, y)], fill=(214, 170, 50), width=int(9*s))
    d.line([(x + 62*s, y), (x + 62*s, y + 18*s)], fill=(214, 170, 50), width=int(8*s))
    d.line([(x + 76*s, y), (x + 76*s, y + 14*s)], fill=(214, 170, 50), width=int(8*s))

def bandeja(d, x, y):
    d.ellipse([x - 120, y - 22, x + 120, y + 22], fill=(220, 222, 228), outline=T, width=5)
    for k, dx in enumerate((-70, 0, 70)):
        d.ellipse([x + dx - 34, y - 46, x + dx + 34, y - 10], fill=(214, 160, 96), outline=T, width=4)
        for j in range(3):
            d.ellipse([x + dx - 16 + j*12, y - 36 + (j % 2)*8, x + dx - 10 + j*12, y - 30 + (j % 2)*8], fill=(90, 56, 40))

def estrellas(d, x, y, t, r=70):
    for k in range(3):
        a = t*5 + k*2.1
        px, py = x + math.cos(a)*r, y + math.sin(a)*r*0.35
        d.regular_polygon((px, py, 20), 5, fill=(255, 220, 70), outline=T)

def cerrojo(d, x, y, cerrado):
    d.rounded_rectangle([x - 34, y - 20, x + 34, y + 20], radius=6, fill=(214, 176, 70), outline=T, width=4)
    if cerrado:
        d.rectangle([x - 60, y - 7, x - 30, y + 7], fill=(180, 146, 60), outline=T, width=3)

def nota(d, x, y, s=1.0, rot=0, img=None):
    capa = Image.new("RGBA", (int(300*s), int(200*s)), (0, 0, 0, 0))
    c = ImageDraw.Draw(capa)
    c.rectangle([4, 4, 300*s - 4, 200*s - 4], fill=(252, 250, 236), outline=T, width=max(3, int(4*s)))
    for k in range(4):
        c.line([(20*s, 60*s + k*34*s), (280*s, 60*s + k*34*s)], fill=(196, 214, 236), width=2)
    c.text((150*s, 70*s), "NO VISITORS.", font=fuente(38*s), fill=(200, 40, 40), anchor="mm")
    c.text((170*s, 150*s), "- The President", font=fuente(20*s), fill=(60, 60, 70), anchor="mm")
    capa = capa.rotate(rot, expand=True, resample=Image.BICUBIC)
    img.paste(capa, (int(x - capa.width/2), int(y - capa.height/2)), capa)

def almohada(d, x, y, s=1.0):
    d.rounded_rectangle([x - 120*s, y - 55*s, x + 120*s, y + 55*s], radius=int(40*s), fill=(250, 250, 252), outline=T, width=5)
    d.arc([x - 100*s, y - 40*s, x + 100*s, y + 50*s], 200, 340, fill=(214, 214, 224), width=4)

# ---------------------------------------------------------------- el edificio en corte
PISOS = ["porteria", "p1", "p2", "p3", "p4", "atico"]
Y_TECHO, ALTO_PISO = 300, 230
def y_piso(i):               # suelo del piso i (0 = porteria)
    return Y_TECHO + ALTO_PISO*(len(PISOS) - i)

def edificio(t, noche=False, poke_calle=None, extras=None):
    img = Image.new("RGB", (W, H), (40, 46, 84) if noche else (176, 220, 246))
    d = ImageDraw.Draw(img)
    if not noche:
        for x, y in ((180, 160), (860, 110)):
            for dx, r in ((-40, 34), (0, 46), (44, 34)):
                d.ellipse([x + dx - r, y - r, x + dx + r, y + r], fill=(252, 252, 252))
    else:
        d.ellipse([860, 90, 960, 190], fill=(250, 240, 200))
        for x, y in ((120, 120), (300, 200), (640, 80), (980, 260)):
            d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(250, 250, 230))
    x0, x1 = 90, 990
    escalera_x = 740
    d.rectangle([x0 - 20, Y_TECHO - 30, x1 + 20, y_piso(0) + 10], fill=(214, 180, 150), outline=T, width=6)
    # el letrero
    d.rounded_rectangle([W/2 - 210, Y_TECHO - 150, W/2 + 210, Y_TECHO - 50], radius=18, fill=(52, 50, 64), outline=T, width=6)
    Mu.texto(d, W/2, Y_TECHO - 100, "BLOCK 7", 70, (255, 214, 90) if not noche else (255, 230, 120))
    for i, nombre in enumerate(PISOS):
        y1 = y_piso(i); y0 = y1 - ALTO_PISO + 14
        pared = Mu.PAREDES[nombre]
        if noche:
            pared = tuple(int(v*0.55) for v in pared)
        d.rectangle([x0, y0, escalera_x, y1], fill=pared)
        d.rectangle([escalera_x + 10, y0, x1, y1], fill=Mu.PAREDES["escalera"] if not noche else (110, 104, 96))
        # la escalera en zigzag
        for k in range(6):
            sx = escalera_x + 30 + k*36 if i % 2 == 0 else x1 - 40 - k*36
            sy = y1 - k*(ALTO_PISO - 14)/6
            d.rectangle([sx - 18, sy - 32, sx + 18, sy], fill=(196, 180, 160), outline=T, width=2)
        d.rectangle([x0 - 20, y1, x1 + 20, y1 + 14], fill=(150, 120, 100), outline=T, width=4)
        d.line([(escalera_x + 5, y0), (escalera_x + 5, y1)], fill=T, width=8)
    d.rectangle([x0 - 20, Y_TECHO - 30, x1 + 20, y_piso(0) + 10], outline=T, width=6)
    # la calle
    d.rectangle([0, y_piso(0) + 14, W, H], fill=(150, 150, 160) if not noche else (70, 70, 84))
    d.rectangle([0, y_piso(0) + 14, W, y_piso(0) + 60], fill=(196, 196, 204) if not noche else (96, 96, 110), outline=T, width=4)
    for k in range(0, W, 180):
        d.rectangle([k + 40, H - 120, k + 140, H - 100], fill=(240, 240, 240) if not noche else (150, 150, 160))
    # la gente del edificio, pequeña
    for fn in (extras or []):
        fn(img, t)
    if poke_calle is not None:
        Mu.poke(img, poke_calle, y_piso(0) + 50, 150, dict(pose="maleta", fase=t*8, dir=0.6, mira=(0.6, 0)), t)
        maleta(ImageDraw.Draw(img), poke_calle + 55, y_piso(0) + 4, 0.4)
    return img

def vecinos_pequeños(img, t, noche=False, poke_dentro=False):
    d = ImageDraw.Draw(img)
    # porteria: el gato y el mostrador
    yb = y_piso(0)
    Mu.gato(img, 560, yb - 60, 150, dict(mira=(0.3, 0.3)), t)
    d = ImageDraw.Draw(img); d.rectangle([460, yb - 60, 660, yb], fill=(150, 100, 70), outline=T, width=4)
    # 2o: el globo
    Mu.bubble(img, 380, y_piso(2) - 130, 150, dict(ladrillo=(390, y_piso(2)), mira=(0.4, 0)), t)
    # 3o: Pop y Mag discutiendo
    fondo3 = Mu.PAREDES["p3"] if not noche else tuple(int(v*0.55) for v in Mu.PAREDES["p3"])
    ex = 1.0 if (t % 2.4) > 2.0 else 0.0
    Mu.pop(img, 330, y_piso(3), 130, dict(enfado=1.0, explota=ex*0.6, brazos_arriba=True), t)
    Mu.mag(img, 520, y_piso(3), 130, dict(enfado=1.0, tenedor=True, brazos_arriba=(t % 1.0) > 0.5, fondo=fondo3), t)
    # 4o: Cubi con su ventilador
    Mu.cubi(img, 420, y_piso(4), 150, dict(feliz=1.0, gotas=True), t)
    # atico: Don Huevo
    Mu.huevo_cara(img, 420, y_piso(5) - 90, 130, dict(mira=(0.5, 0.3)), t)
    if poke_dentro:
        Mu.poke(img, 380, y_piso(1), 160, dict(pose="pecho", plumas=1.0, feliz=1.0), t)

# ---------------------------------------------------------------- los planos
def p_edificio(lt, t):
    img = edificio(t, poke_calle=40 + 160*lt, extras=[lambda im, tt: vecinos_pequeños(im, tt)])
    z = 1.0 + 0.9*suave((lt - 1.0)/2.0)
    return img, (W/2 + (300 - W/2)*suave((lt - 1.0)/2.0), H/2 + (y_piso(0) - 150 - H/2)*suave((lt - 1.0)/2.0), z)

def porteria(lt):
    img = Image.new("RGB", (W, H), Mu.PAREDES["porteria"]); d = ImageDraw.Draw(img)
    # suelo de baldosas
    d.rectangle([0, SUELO, W, H], fill=(236, 232, 224))
    for i in range(0, W, 120):
        for j in range(SUELO, H, 120):
            if (i//120 + j//120) % 2 == 0:
                d.rectangle([i, j, i + 120, j + 120], fill=(70, 74, 86))
    d.line([(0, SUELO), (W, SUELO)], fill=T, width=6)
    # buzones
    for f in range(3):
        for c in range(4):
            x, y = 90 + c*110, 560 + f*120
            d.rectangle([x, y, x + 96, y + 100], fill=(200, 168, 96), outline=T, width=4)
            d.rectangle([x + 18, y + 30, x + 78, y + 44], fill=(60, 56, 50))
    Mu.texto(d, 310, 500, "MAIL", 40, (250, 246, 236))
    Mu.planta(d, 120, SUELO, 1.2)
    return img

def p_porteria(lt, t):
    img = porteria(lt)
    d = ImageDraw.Draw(img)
    # Poke entra
    x = -150 + 520*suave(lt/2.0)
    anda = lt < 2.0
    st = dict(pose="maleta", fase=lt*8 if anda else None, dir=0.6, mira=(0.7, -0.2), parpadeo=parpadeo(lt))
    if 2.2 <= lt < 3.3:
        st.update(pose="saluda", onda=True, feliz=1.0, boca="abierta")
    elif 3.3 <= lt < 4.6:
        st.update(pose="abrazo", feliz=1.0, boca="abierta", inclina=0.05)
        x += 60*suave((lt - 3.3)/0.5)
    elif lt >= 4.6:
        x += 60
        st.update(pose="caido", mira=(0.7, 0.6) if lt < 6.2 else (0.3, -0.2), feliz=1.0 if lt > 6.4 else 0.0,
                  boca="sonrisa" if lt > 6.4 else "plana")
    info = Mu.poke(img, x, SUELO + 40, HP, st, t)
    d = ImageDraw.Draw(img)
    if st["pose"] == "maleta":
        maleta(d, info["manos"][0][0] - 10, info["manos"][0][1] + 10, 1.0)
    else:
        maleta(d, x - 200, SUELO - 90, 1.0)
    # el gato detras del mostrador, impasible
    mira_g = (-0.8, 0.2) if lt > 1.2 else (0, 0.3)
    cab = Mu.gato(img, 820, 1180, 420, dict(mira=mira_g, parpadeo=parpadeo(lt, 4.0, 1.2), cansancio=0.8), t)
    d = ImageDraw.Draw(img)
    d.rectangle([600, 1180, 1080, SUELO + 40], fill=(150, 100, 70), outline=T, width=6)
    d.rectangle([600, 1180, 1080, 1210], fill=(176, 124, 90), outline=T, width=5)
    d.ellipse([650, 1140, 710, 1186], fill=(230, 196, 90), outline=T, width=4)                  # el timbre
    # la llave, empujada con un palo para no acercarse
    if lt > 4.4:
        k = suave((lt - 4.6)/1.2)
        kx = 860 - 330*k
        if lt < 6.2:
            d.line([(cab["pata"][0], cab["pata"][1] - 60), (kx + 40, 1168)], fill=(120, 84, 56), width=12)
            llave(d, kx - 40, 1168, 0.9)
        else:
            llave(d, info["manos"][1][0], info["manos"][1][1], 0.9)
    if 3.5 < lt < 4.4:
        Mu.texto(d, 820, 640, "...", 80, (250, 250, 250))
    return img, (560, 1100, 1.12)

def pasillo(nombre, puerta_num, abre=0.0):
    img = Image.new("RGB", (W, H), Mu.PAREDES[nombre]); d = ImageDraw.Draw(img)
    Mu.suelo_madera(d, SUELO, H)
    d.rectangle([0, SUELO - 40, W, SUELO], fill=tuple(int(v*0.8) for v in Mu.PAREDES[nombre]), outline=T, width=4)
    Mu.puerta(d, 300, SUELO - 40, puerta_num, abre=abre)
    Mu.cuadro(d, 620, 760, 820, 920)
    # la escalera que sube, a la derecha
    for k in range(7):
        x = 840 + k*30; y = SUELO - 40 - k*110
        d.rectangle([x, y - 110, W + 10, y], fill=(206, 190, 168), outline=T, width=4)
    d.line([(820, SUELO - 220), (1100, SUELO - 1000)], fill=(120, 84, 56), width=14)
    return img

def p_pasillo2(lt, t):
    abre = suave((lt - 1.6)/0.5)
    img = pasillo("p2", "2", abre)
    d = ImageDraw.Draw(img)
    # Poke llega desde la escalera
    x = 1150 - 450*suave(lt/1.6)
    st = dict(pose="maleta", fase=lt*8 if lt < 1.6 else None, dir=-0.6, mira=(-0.7, -0.1), parpadeo=parpadeo(lt))
    huye = lt > 3.9
    cae = lt > 5.0
    if 2.9 <= lt < 3.9:
        st.update(pose="abrazo", feliz=1.0, boca="abierta", inclina=-0.06)
    elif huye and not cae:
        st.update(pose="caido", mira=(-0.3, -1.0), susto=0.6, boca="o")
    elif cae:
        st.update(pose="pie", susto=0.0, boca="dolor", ceja=0.7, mira=(0, 0))
        st["salta"] = abs(math.sin((lt - 5.0)*7))*50
    info = Mu.poke(img, x, SUELO + 40, HP, st, t)
    d = ImageDraw.Draw(img)
    if st["pose"] == "maleta":
        maleta(d, info["manos"][1][0] + 10, info["manos"][1][1] + 10)
    else:
        maleta(d, x + 230, SUELO - 90)
    # Bubble sale de su piso con su ladrillo
    if lt > 2.0:
        if not huye:
            bx = 300 + 80*suave((lt - 2.0)/0.8); by = 1050
            st_b = dict(ladrillo=(bx + 20, SUELO - 40), mira=(0.7, 0.0), parpadeo=parpadeo(lt, 3.0, 0.5),
                        susto=1.0 if lt > 3.4 else 0.0, boca="grito" if lt > 3.4 else "sonrisa", tiembla=1.0 if lt > 3.4 else 0.0,
                        pose="arriba" if lt > 3.4 else "caido")
            Mu.bubble(img, bx, by, 380, st_b, t)
            if lt > 3.4:
                Mu.texto(ImageDraw.Draw(img), bx + 30, by - 300, "!", 130, (255, 80, 70))
        else:
            k = (lt - 3.9)/1.0
            bx = 380 + 420*suave(k); by = 1050 - 1500*k*k
            lad = None
            if lt < 5.0:          # el ladrillo colgando de la cuerda, hasta que se suelta encima de Poke
                lad = (bx + 10, by + 380*0.36 + 260)
            Mu.bubble(img, bx, by, 380, dict(ladrillo=lad, susto=1.0, boca="grito", pose="arriba", cuerda=lad is not None), t)
            if lt >= 4.6:
                kk = suave((lt - 4.6)/0.4)
                ly = (1050 - 1500*(0.7**2) + 380*0.36 + 260)*(1 - kk) + (SUELO + 30)*kk
                if lt > 5.0:
                    ly = SUELO + 30
                d = ImageDraw.Draw(img)
                d.rectangle([x - 60, ly - 40, x + 60, ly], fill=Mu.LADRILLO, outline=T, width=5)
                d.line([(x - 60, ly - 20), (x + 60, ly - 20)], fill=(140, 64, 46), width=3)
    if cae:
        estrellas(ImageDraw.Draw(img), x, info["top"] - 60, t)
        if lt < 5.6:
            Mu.texto(ImageDraw.Draw(img), x + 160, SUELO - 120, "BONK!", 80, (255, 210, 60))
    return img, (640, 1050, 1.08)

def p_globo_techo(lt, t):
    img = Image.new("RGB", (W, H), Mu.PAREDES["escalera"]); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 300], fill=(214, 206, 190), outline=T, width=6)          # el techo de la escalera
    d.line([(0, 300), (W, 300)], fill=T, width=8)
    for k in range(5):
        d.rectangle([k*260 - 40, 1300 + k*0, k*260 + 200, 1340], fill=(196, 180, 160))
    Mu.bubble(img, 540, 300 + 380*0.36 + 10, 760, dict(susto=1.0, boca="grito", mira=(0, 1.0), tiembla=1.0, pose="arriba", cuerda=True), t)
    return img, (540, 700, 1.0)

def p_escalera_3(lt, t):
    """La escalera a la izquierda y, por el corte del edificio, el piso del 3o con la bronca de Pop y Mag."""
    img = Image.new("RGB", (W, H), Mu.PAREDES["escalera"]); d = ImageDraw.Draw(img)
    split = 470
    d.rectangle([split, 0, W, H], fill=Mu.PAREDES["p3"])
    Mu.suelo_madera(d, SUELO, H)
    for k in range(9):           # los peldaños, subiendo hacia la izquierda
        x = split - 60 - k*52; y = SUELO + 200 - k*90
        d.rectangle([-10, y - 90, x, y], fill=(206, 190, 168), outline=T, width=4)
    d.rectangle([split - 12, 0, split + 12, H], fill=(150, 120, 100), outline=T, width=5)
    Mu.ventana(d, 650, 650, 960, 950)
    # Pop y Mag
    fondo3 = Mu.PAREDES["p3"]
    explota = suave((lt - 3.2)/0.3) if 3.2 < lt < 4.4 else 0.0
    Mu.mag(img, 640, SUELO, 330, dict(enfado=1.0, tenedor=True, brazos_arriba=(t % 0.8) > 0.4, mira=(0.8, 0), fondo=fondo3), t)
    Mu.pop(img, 900, SUELO, 330, dict(enfado=1.0 if explota == 0 else 0.0, susto=explota, explota=explota, brazos_arriba=(t % 0.7) > 0.35,
                                      mira=(-0.8, 0)), t)
    # Poke sube cojeando
    paso = 2.6*min(lt, 3.3)/3.3 + (0.9*(lt - 4.8)/1.2 if lt > 4.8 else 0.0)
    x = split - 120 - 52*paso; y = SUELO + 200 - 90*paso
    para = 3.3 <= lt < 4.8
    st = dict(pose="maleta", fase=lt*7 if not para else None, dir=-0.5 if not para else 0.7,
              mira=(-0.6, -0.3) if not para else (1.0, 0.0), susto=0.7 if 3.4 < lt < 4.0 else 0.0,
              boca="o" if 3.4 < lt < 4.0 else "plana", ceja=0.3)
    info = Mu.poke(img, x, y, 470, st, t)
    maleta(ImageDraw.Draw(img), info["manos"][0][0] - 10, info["manos"][0][1] + 10, 0.85)
    if 4.0 < lt < 4.8:
        Mu.texto(ImageDraw.Draw(img), x + 120, info["top"] - 60, "?", 110, (255, 220, 70))
    return img, (540, 1000, 1.0)

def p_atico(lt, t):
    img = Image.new("RGB", (W, H), Mu.PAREDES["atico"]); d = ImageDraw.Draw(img)
    Mu.suelo_madera(d, SUELO, H)
    d.rectangle([0, SUELO - 40, W, SUELO], fill=(196, 190, 140), outline=T, width=4)
    rendija = suave((lt - 2.2)/0.3)*(1 - suave((lt - 4.0)/0.12))
    px = 330
    # el felpudo
    d.rounded_rectangle([px - 200, SUELO + 10, px + 200, SUELO + 90], radius=14, fill=(150, 110, 70), outline=T, width=5)
    Mu.texto(d, px, SUELO + 50, "GO AWAY", 44, (240, 220, 180), (90, 60, 40))
    # la puerta: entreabierta con la cadena, y Don Huevo asomando
    if rendija > 0:
        d.rectangle([px - 165, SUELO - 680, px - 165 + 120*rendija, SUELO - 40], fill=(26, 22, 30))
        if rendija > 0.6:
            sust = suave((lt - 3.3)/0.25)
            Mu.huevo_cara(img, px - 165 + 120*rendija - 30, SUELO - 400, 300,
                          dict(mira=(1.0, 0.2 + 0.8*suave((lt - 2.8)/0.4)), susto=sust, boca="o" if sust > 0.5 else None, dir=0.4), t)
            d = ImageDraw.Draw(img)
            d.line([(px - 165 + 120*rendija, SUELO - 430), (px - 165 + 120*rendija + 40, SUELO - 400)], fill=(200, 200, 206), width=8)
    d.rectangle([px - 165 + 120*rendija, SUELO - 680, px + 165, SUELO - 40], fill=(120, 86, 64), outline=T, width=6)
    d.rectangle([px - 183, SUELO - 698, px + 183, SUELO - 40], outline=T, width=6)
    d.rounded_rectangle([px - 80, SUELO - 640, px + 80, SUELO - 590], radius=8, fill=(214, 176, 70), outline=T, width=4)
    Mu.texto(d, px, SUELO - 615, "PRES.", 30, T, (214, 176, 70))
    for k, tc in enumerate((4.3, 4.6, 4.9)):
        cerrojo(d, px + 110, SUELO - 470 + k*80, lt > tc)
    if 4.3 < lt < 5.4:
        Mu.texto(d, px + 300, SUELO - 520 + int((lt - 4.3)/0.3)*70, "CLACK!", 54, (255, 214, 70))
    if 4.0 < lt < 4.3:
        Mu.texto(d, px, SUELO - 760, "SLAM!", 90, (255, 90, 70))
    # Poke, con la bandeja de galletas
    x = 1150 - 400*suave(lt/1.2)
    st = dict(pose="bandeja", fase=lt*8 if lt < 1.2 else None, dir=-0.6, mira=(-0.8, -0.1), feliz=1.0 if 1.2 < lt < 3.6 else 0.0,
              boca="abierta" if 2.4 < lt < 3.6 else "sonrisa", parpadeo=parpadeo(lt, 3.3))
    if lt >= 4.0:
        st.update(feliz=0.0, boca="plana", mira=(-0.9, 0.0), parpadeo=1.0 if 5.1 < lt < 5.25 or 5.4 < lt < 5.55 else 0.0)
    if lt >= 7.0:
        st.update(pose="caido", inclina=-0.1*suave((lt - 7.0)/0.5), mira=(-0.5, 1.0))
    if 1.4 < lt < 2.1:             # llama a la puerta
        st.update(pose="saluda")
    info = Mu.poke(img, x, SUELO + 40, HP, st, t)
    d = ImageDraw.Draw(img)
    if st["pose"] == "bandeja":
        bandeja(d, (info["manos"][0][0] + info["manos"][1][0])/2, min(info["manos"][0][1], info["manos"][1][1]) - 10)
    else:
        bandeja(d, x + 250, SUELO - 20)
    if 1.4 < lt < 2.1:
        Mu.texto(d, px + 230, SUELO - 600, "KNOCK KNOCK", 48, (250, 250, 250))
    # la nota que sale por debajo de la puerta
    if lt > 6.0:
        k = suave((lt - 6.0)/0.8)
        nota(d, px + 60 + 300*k, SUELO + 20, 0.6, rot=8, img=img)
    return img, (600, 1050, 1.06)

def p_nota(lt, t):
    img = Image.new("RGB", (W, H), Mu.PAREDES["atico"]); d = ImageDraw.Draw(img)
    img = Mu.luz(img, 540, 900, 600, 0.25)
    d = ImageDraw.Draw(img)
    nota(d, 540, 900, 2.6, rot=-4, img=img)
    for lado in (-1, 1):            # las manos verdes de cactus sujetandola
        d.ellipse([540 + lado*360 - 60, 1050 - 60, 540 + lado*360 + 60, 1050 + 60], fill=Mu.VERDE, outline=T, width=6)
        for k in range(3):
            a = math.radians(200 + k*40) if lado < 0 else math.radians(-20 - k*40)
            d.line([(540 + lado*360 + math.cos(a)*60, 1050 + math.sin(a)*60), (540 + lado*360 + math.cos(a)*85, 1050 + math.sin(a)*85)], fill=T, width=4)
    return img, (540, 900, 1.0 + 0.02*lt)

def piso_poke(lt, noche=0.0):
    img = Image.new("RGB", (W, H), Mu.PAREDES["p1"]); d = ImageDraw.Draw(img)
    Mu.suelo_madera(d, SUELO, H)
    Mu.ventana(d, 620, 520, 960, 860, cielo=(250, 196, 150))          # el atardecer
    for x, y, w_, h_ in ((80, SUELO - 200, 220, 200), (130, SUELO - 360, 160, 160)):
        d.rectangle([x, y, x + w_, y + h_], fill=(206, 168, 120), outline=T, width=5)
        d.line([(x, y + h_*0.3), (x + w_, y + h_*0.3)], fill=(170, 130, 90), width=4)
    # la cama
    d.rectangle([520, SUELO - 260, 1080, SUELO - 120], fill=(246, 246, 248), outline=T, width=6)
    d.rectangle([520, SUELO - 120, 1080, SUELO - 70], fill=(150, 106, 76), outline=T, width=5)
    d.rectangle([1000, SUELO - 520, 1080, SUELO - 70], fill=(150, 106, 76), outline=T, width=5)
    return img

def p_piso(lt, t):
    img = piso_poke(lt)
    d = ImageDraw.Draw(img)
    poof = lt > 4.3
    if not poof:
        almohada(d, 900, SUELO - 300, 0.95) if lt < 3.6 else None
    sentado = lt > 1.8
    x = -120 + 640*suave(lt/1.8) if not sentado else 520 + 140*suave((lt - 1.8)/0.6)
    suelo_p = SUELO + 40 if not sentado else SUELO - 140
    st = dict(pose="maleta" if lt < 1.8 else "triste", fase=lt*7 if lt < 1.8 else None, dir=0.4, mira=(0.5, 0.6),
              ceja=0.6 if sentado else 0.0, boca="triste" if sentado else "sonrisa", parpadeo=parpadeo(lt, 3.1))
    if 3.0 <= lt < 3.6:
        st.update(mira=(1.0, 0.2), ceja=0.0, boca="o")
    if 3.6 <= lt < 4.3:
        st.update(pose="pecho", feliz=1.0, boca="sonrisa")
    if poof:
        st.update(pose="caido", plumas=suave((lt - 4.6)/0.8), susto=1.0 if lt < 5.6 else 0.0, boca="o" if lt < 5.6 else "abierta",
                  feliz=1.0 if lt > 6.4 else 0.0, ceja=0.0, mira=(0, 0.9) if 5.6 < lt < 6.4 else (0, 0))
        if lt > 6.4:
            st["pose"] = "pecho"
    info = Mu.poke(img, x, suelo_p, HP, st, t)
    d = ImageDraw.Draw(img)
    if lt < 1.8:
        maleta(d, info["manos"][0][0] - 10, info["manos"][0][1] + 10)
    else:
        maleta(d, 380, SUELO - 90)
    if 3.6 <= lt < 4.3:
        almohada(d, info["cara"][0], info["cara"][1] + 220, 0.9)
    if poof:
        k = (lt - 4.3)/1.8
        rnd = random.Random(11)
        for i in range(60):
            a = rnd.uniform(0, 2*math.pi); v = rnd.uniform(200, 900)
            px = info["cara"][0] + math.cos(a)*v*min(k, 0.4)*2.4 + math.sin(t*3 + i)*30*k
            py = info["cara"][1] + 220 + math.sin(a)*v*min(k, 0.4)*2.0 + 260*max(0, k - 0.3)
            if py < SUELO + 120:
                Mu.pluma_suelta(d, px, py, rnd.uniform(16, 28), a + t)
        if lt < 4.9:
            Mu.texto(d, info["cara"][0], info["cara"][1] - 330, "POOF!", 110, (250, 250, 250))
    if lt > 6.6:
        for k in range(3):                 # corazoncitos
            yy = info["top"] - 80 - ((lt - 6.6)*120 + k*70) % 220
            Mu.texto(d, info["cara"][0] - 120 + k*120, yy, "♥", 60, (244, 110, 150))
    return img, (640, 1050, 1.08 + 0.01*lt)

def p_noche(lt, t):
    img = edificio(t, noche=True, extras=[lambda im, tt: vecinos_pequeños(im, tt, noche=True, poke_dentro=True)])
    d = ImageDraw.Draw(img)
    # el globo, todavia pegado al techo de la escalera
    Mu.bubble(img, 900, y_piso(5) - 160, 120, dict(susto=1.0, boca="o", tiembla=1.0, mira=(0, 1)), t)
    # ventanas encendidas en el 3o (la bronca sigue)
    z = 1.0 + 1.6*suave((lt - 1.5)/1.8)
    if lt > 3.0:      # el gato mira a camara y levanta una ceja
        pass
    return img, (W/2 + (560 - W/2)*suave((lt - 1.5)/1.8), H/2 + (y_piso(0) - 160 - H/2)*suave((lt - 1.5)/1.8), z)

def p_fin(lt, t, dur=3.5):
    img = Image.new("RGB", (W, H), (34, 32, 44)); d = ImageDraw.Draw(img)
    a = suave(lt/0.5)*suave((dur - lt)/0.4)
    c = lambda col: tuple(int(34 + (v - 34)*a) for v in col)
    d.rounded_rectangle([W/2 - 300, 640, W/2 + 300, 790], radius=24, fill=c((52, 50, 64)), outline=c((255, 214, 90)), width=6)
    d.text((W/2, 715), "BLOCK 7", font=fuente(100), fill=c((255, 214, 90)), anchor="mm")
    d.text((W/2, 880), "Ep. 1 · The New Neighbour", font=fuente(48), fill=c((240, 240, 240)), anchor="mm")
    b = suave((lt - 1.0)/0.5)*suave((dur - lt)/0.4)
    cb = lambda col: tuple(int(34 + (v - 34)*b) for v in col)
    d.text((W/2, 1130), "NEXT:", font=fuente(40), fill=cb((200, 200, 210)), anchor="mm")
    d.text((W/2, 1200), "The Argument", font=fuente(66), fill=cb((255, 140, 120)), anchor="mm")
    return img, (W/2, H/2, 1.0)

# ---------------------------------------------------------------- el montaje
GUION = [
    (p_edificio, 3.2, [(0.0, "tema")]),
    (p_porteria, 7.5, [(0.3, "pasos2.0"), (2.3, "boing"), (4.6, "raspa1.4"), (6.2, "tin")]),
    (p_pasillo2, 8.2, [(0.0, "pasos1.6"), (1.6, "puerta"), (3.4, "susto"), (3.9, "silbido"), (5.0, "bonk"), (5.1, "pito")]),
    (p_globo_techo, 2.2, [(0.0, "tiembla")]),
    (p_escalera_3, 6.0, [(0.0, "bronca3.2"), (3.2, "pop")]),
    (p_atico, 9.0, [(0.0, "pasos1.2"), (1.45, "toc"), (1.7, "toc"), (1.95, "toc"), (2.2, "cruje"), (3.3, "susto"),
                    (4.0, "portazo"), (4.3, "clack"), (4.6, "clack"), (4.9, "clack"), (6.0, "papel")]),
    (p_nota, 2.6, []),
    (p_piso, 8.5, [(0.0, "pasos1.8"), (2.0, "suspiro"), (4.3, "poof"), (6.6, "tema_feliz")]),
    (p_noche, 3.6, []),
    (lambda lt, t: p_fin(lt, t, 3.5), 3.5, [(0.0, "fin")]),
]

def tabla():
    t = 0.0; out = []
    for fn, dur, sfx in GUION:
        out.append((t, t + dur, fn, sfx)); t += dur
    return out, t

TABLA, DUR = tabla()

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

# ---------------------------------------------------------------- sonido
SR = 44100
def nota_f(m): return 440*2**((m - 69)/12)

def musica():
    """El tema de la serie: un pizzicato saltarin en Do mayor, con un bajo que camina.
    Se calla en los golpes de comedia (el portazo, el POOF) y vuelve despues."""
    n = int(DUR*SR); out = np.zeros(n)
    bpm = 116; negra = 60/bpm
    melodia = [72, 76, 79, 76, 77, 74, 71, 74, 72, 76, 79, 84, 83, 79, 77, 74]
    bajos = [48, 55, 53, 55, 48, 52, 55, 43]
    silencios = []
    _I = {fn: a for a, b, fn, s in TABLA}
    t_portazo = _I[p_atico] + 4.0; t_poof = _I[p_piso] + 4.3; t_triste = _I[p_piso] + 1.8
    silencios = [(t_portazo - 0.05, t_portazo + 2.6), (t_triste, t_poof + 2.0)]
    def callado(tt): return any(a <= tt < b for a, b in silencios)
    k = 0; tt = 0.0
    while tt < DUR - 2.0:
        if not callado(tt):
            m = melodia[k % len(melodia)]
            s0 = int(tt*SR); L = int(0.45*SR); x = np.arange(L)/SR
            env = np.exp(-x*9)
            tono = np.sin(2*np.pi*nota_f(m)*x) + 0.35*np.sin(2*np.pi*nota_f(m)*2*x) + 0.1*np.sin(2*np.pi*nota_f(m)*3*x)
            out[s0:s0 + L] += 0.09*env*tono[:max(0, min(L, n - s0))] if s0 + L <= n else 0
            if k % 2 == 0:
                b = bajos[(k//2) % len(bajos)]
                Lb = int(0.6*SR); xb = np.arange(Lb)/SR
                if s0 + Lb <= n:
                    out[s0:s0 + Lb] += 0.12*np.exp(-xb*5)*np.sin(2*np.pi*nota_f(b)*xb)
        tt += negra/2 if (k % 4) != 3 else negra
        k += 1
    # la parte triste: unas notas lentas en menor
    for j, m in enumerate([69, 67, 64, 62, 64]):
        s0 = int((t_triste + 0.3 + j*0.55)*SR); L = int(1.0*SR); x = np.arange(L)/SR
        if s0 + L <= n:
            out[s0:s0 + L] += 0.07*np.exp(-x*3)*np.sin(2*np.pi*nota_f(m)*x)
    return out

def efectos():
    n = int(DUR*SR); out = np.zeros(n); rnd = np.random.default_rng(3)
    def pon(t0, x):
        s0 = int(t0*SR); s1 = min(n, s0 + len(x))
        if 0 <= s0 < n: out[s0:s1] += x[:s1 - s0]
    def tono(f, d, vol, ca=8.0, at=0.004):
        x = np.arange(int(d*SR))/SR
        return vol*np.sin(2*np.pi*f*x)*np.minimum(1, x/at)*np.exp(-x*ca)
    def barrido(f0, f1, d, vol, ca=3.0):
        x = np.arange(int(d*SR))/SR; f = f0 + (f1 - f0)*x/d
        return vol*np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-x*ca)
    def ruido(d, vol, suav=10):
        return vol*np.convolve(rnd.standard_normal(int(d*SR)), np.ones(suav)/suav, mode="same")
    for a, b, fn, sfx in TABLA:
        for t0, tipo in sfx:
            T0 = a + t0
            if tipo.startswith("pasos"):
                d = float(tipo[5:]); k = 0.0
                while k < d:
                    pon(T0 + k, tono(180, 0.08, 0.10, 40) + ruido(0.08, 0.04, 8)*np.exp(-np.arange(int(0.08*SR))/SR*50)); k += 0.26
            elif tipo == "boing":
                pon(T0, barrido(300, 700, 0.35, 0.12, 4))
            elif tipo.startswith("raspa"):
                d = float(tipo[5:]); x = ruido(d, 0.06, 4); x *= 0.5 + 0.5*np.sin(np.arange(len(x))/SR*2*np.pi*6)
                pon(T0, x)
            elif tipo == "tin":
                pon(T0, tono(2093, 0.6, 0.08, 5)); pon(T0 + 0.08, tono(2637, 0.6, 0.06, 5))
            elif tipo == "puerta":
                pon(T0, barrido(500, 380, 0.6, 0.05, 2))
            elif tipo == "susto":
                pon(T0, barrido(400, 1400, 0.25, 0.1, 2))
            elif tipo == "silbido":
                pon(T0, barrido(500, 2200, 1.0, 0.09, 1.5))
            elif tipo == "bonk":
                pon(T0, tono(110, 0.3, 0.35, 12) + ruido(0.3, 0.2, 30)*np.exp(-np.arange(int(0.3*SR))/SR*20))
            elif tipo == "pito":                 # el "¡ay!" de dibujo: un pito de goma
                pon(T0, barrido(900, 1300, 0.18, 0.1, 6)); pon(T0 + 0.22, barrido(900, 1300, 0.18, 0.1, 6))
            elif tipo == "tiembla":
                x = np.arange(int(2.0*SR))/SR; pon(T0, 0.04*np.sin(2*np.pi*90*x)*(0.5 + 0.5*np.sign(np.sin(2*np.pi*12*x))))
            elif tipo.startswith("bronca"):          # la discusion del 3o, amortiguada tras la pared
                d = float(tipo[6:]); k = 0.0
                while k < d:
                    f = rnd.uniform(220, 420); pon(T0 + k, barrido(f, f*rnd.uniform(0.7, 1.3), 0.18, 0.05, 4)); k += rnd.uniform(0.15, 0.3)
            elif tipo == "pop":
                pon(T0, ruido(0.12, 0.6, 2)*np.exp(-np.arange(int(0.12*SR))/SR*40))
            elif tipo == "toc":
                pon(T0, tono(160, 0.1, 0.3, 40) + ruido(0.1, 0.25, 20)*np.exp(-np.arange(int(0.1*SR))/SR*60))
            elif tipo == "cruje":
                pon(T0, barrido(300, 200, 0.5, 0.05, 2))
            elif tipo == "portazo":
                pon(T0, tono(70, 0.5, 0.5, 9) + ruido(0.5, 0.35, 40)*np.exp(-np.arange(int(0.5*SR))/SR*14))
            elif tipo == "clack":
                pon(T0, ruido(0.05, 0.4, 3)*np.exp(-np.arange(int(0.05*SR))/SR*80) + tono(900, 0.05, 0.1, 60))
            elif tipo == "papel":
                pon(T0, ruido(0.7, 0.08, 6)*np.exp(-np.arange(int(0.7*SR))/SR*3))
            elif tipo == "suspiro":
                x = ruido(1.2, 0.1, 80); x *= np.sin(np.linspace(0, np.pi, len(x))); pon(T0, x)
            elif tipo == "poof":
                x = ruido(0.6, 0.6, 60); x *= np.exp(-np.arange(len(x))/SR*6); pon(T0, x)
            elif tipo == "tema_feliz":
                for j, m in enumerate([72, 76, 79, 84]):
                    pon(T0 + j*0.14, tono(nota_f(m), 0.5, 0.08, 5))
            elif tipo == "fin":
                for j, m in enumerate([79, 76, 72]):
                    pon(T0 + 0.2 + j*0.18, tono(nota_f(m), 0.6, 0.08, 4))
    return out

def audio(ruta):
    # La musica a un nivel fijo y los efectos con un limitador suave: si no,
    # el portazo marcaba el maximo y todo lo demas quedaba a -30 dB.
    mus = musica(); fx = efectos()
    mus = mus/max(1e-6, np.sqrt(np.mean(mus**2)))*0.08
    fx = np.tanh(fx*2.2)*0.55
    mix = np.tanh((mus + fx)*1.3)*0.92
    fo = int(1.0*SR); mix[-fo:] *= np.linspace(1, 0, fo)
    pcm = (np.clip(mix, -0.98, 0.98)*32767).astype(np.int16)
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

def main():
    Path(OUT).mkdir(exist_ok=True)
    args = sys.argv[1:]
    if args and args[0] == "fotos":
        for i, (a, b, fn, _) in enumerate(TABLA):
            for k, f in enumerate((0.25, 0.55, 0.9)):
                fotograma(a + (b - a)*f).resize((270, 480)).save(OUT + f"e1_{i:02d}_{k}.jpg", quality=85)
        print(f"{len(TABLA)} planos, {DUR:.1f} s"); return
    if args and args[0] == "en":
        for s in args[1:]:
            fotograma(float(s)).resize((540, 960)).save(OUT + f"e1_en_{float(s):05.1f}.jpg", quality=88)
        return
    audio(OUT + "ep01_audio.wav")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-i", OUT + "ep01_audio.wav", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19",
                          "-preset", "medium", "-c:a", "aac", "-b:a", "192k", "-shortest", OUT + "BLOCK7_ep01.mp4"], stdin=subprocess.PIPE)
    for i in range(int(DUR*FPS)):
        p.stdin.write(fotograma(i/FPS).tobytes())
    p.stdin.close(); p.wait()
    print(f"hecho: {DUR:.1f} s")

if __name__ == "__main__":
    main()
