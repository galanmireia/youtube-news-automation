"""BLOCK 7 · Ep. 2 — THE ARGUMENT (~59 s, vertical, sin voz).

La bronca de Pop y Mag del 3o, contada desde dentro. Pop se arregla para una
cita; Mag se despierta y todo lo metalico de la casa sale volando hacia el,
nevera incluida. La pajarita de Pop tiene clip metalico: sale arrastrado y se
estampa contra Mag. Guerra de palomitas y cucharas. Siguen en el ascensor (el
momento del Ep. 1 visto desde dentro: Poke, la llave, POP POP POP), y al
volver al 3o salen surfeando una avalancha de palomitas. Son las 8: ding-dong,
y la cita es... Bubble, el globo. Pop hace un pop pequeñito.
"""
import math, random, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mundo as Mu
import sonido as S
from mundo import T, W, H, suave, parpadeo, fuente

OUT = str(Path(__file__).resolve().parent) + "/salida/"
FPS = 25
SUELO = 1500
HPOP, HMAG = 440, 480
PARED = Mu.PAREDES["p3"]

# ---------------------------------------------------------------- objetos de la casa
def nevera(d, x, suelo, s=1.0, tiembla=0.0, t=0.0):
    x += math.sin(t*50)*tiembla*8
    w, h = 250*s, 560*s
    d.rounded_rectangle([x - w/2, suelo - h, x + w/2, suelo], radius=int(26*s), fill=(246, 246, 248), outline=T, width=6)
    d.line([(x - w/2, suelo - h*0.62), (x + w/2, suelo - h*0.62)], fill=T, width=5)
    for y0, y1 in ((suelo - h*0.9, suelo - h*0.7), (suelo - h*0.5, suelo - h*0.2)):
        d.rounded_rectangle([x + w*0.3, y0, x + w*0.38, y1], radius=6, fill=(200, 200, 210), outline=T, width=3)
    return (x - w/2, suelo - h, x + w/2, suelo)

def nota_nevera(d, x, y, s=1.0):
    d.rectangle([x - 90*s, y - 70*s, x + 90*s, y + 70*s], fill=(252, 236, 160), outline=T, width=max(3, int(4*s)))
    d.text((x, y - 25*s), "DATE", font=fuente(36*s), fill=(60, 40, 40), anchor="mm")
    d.text((x, y + 20*s), "8 PM", font=fuente(36*s), fill=(60, 40, 40), anchor="mm")
    Mu.texto(d, x + 60*s, y + 50*s, "♥", int(44*s), (230, 70, 100))
    d.ellipse([x - 22*s, y - 92*s, x + 22*s, y - 50*s], fill=(240, 120, 60), outline=T, width=3)   # el iman de fruta

def cubierto(d, x, y, ang, tipo):
    c, s_ = math.cos(ang), math.sin(ang)
    p0, p1 = (x - c*55, y - s_*55), (x + c*55, y + s_*55)
    d.line([p0, p1], fill=T, width=14); d.line([p0, p1], fill=(206, 208, 214), width=8)
    if tipo == 0:      # tenedor
        for k in (-1, 0, 1):
            d.line([p1, (p1[0] + c*25 - s_*k*8, p1[1] + s_*25 + c*k*8)], fill=(206, 208, 214), width=5)
    elif tipo == 1:    # cuchara
        d.ellipse([p1[0] - 16, p1[1] - 16, p1[0] + 16, p1[1] + 16], fill=(206, 208, 214), outline=T, width=3)

def sarten(d, x, y, ang=0.0, s=1.0):
    c, s_ = math.cos(ang), math.sin(ang)
    d.line([(x, y), (x + c*150*s, y + s_*150*s)], fill=T, width=int(22*s))
    d.ellipse([x - 85*s, y - 85*s, x + 85*s, y + 85*s], fill=(60, 60, 68), outline=T, width=5)
    d.ellipse([x - 62*s, y - 62*s, x + 62*s, y + 62*s], fill=(84, 84, 92))

def tostadora(d, x, y, s=1.0):
    d.rounded_rectangle([x - 80*s, y - 90*s, x + 80*s, y], radius=int(20*s), fill=(200, 202, 210), outline=T, width=5)
    d.line([(x - 40*s, y - 90*s), (x - 40*s, y - 70*s)], fill=T, width=8); d.line([(x + 30*s, y - 90*s), (x + 30*s, y - 70*s)], fill=T, width=8)

def tostada(d, x, y, s=1.0):
    d.rounded_rectangle([x - 40*s, y - 44*s, x + 40*s, y + 40*s], radius=int(18*s), fill=(214, 160, 90), outline=T, width=4)
    d.rounded_rectangle([x - 28*s, y - 32*s, x + 28*s, y + 28*s], radius=int(12*s), fill=(240, 200, 130))

def llaves(d, x, y):
    d.ellipse([x - 18, y - 18, x + 18, y + 18], outline=(214, 170, 50), width=7)
    for k, a in enumerate((0.4, 1.2)):
        d.line([(x, y), (x + math.cos(a)*70, y + math.sin(a)*70)], fill=(214, 170, 50), width=8)

def movil(d, x, y):
    d.rounded_rectangle([x - 26, y - 46, x + 26, y + 46], radius=8, fill=(30, 30, 36), outline=T, width=3)
    d.rounded_rectangle([x - 20, y - 38, x + 20, y + 34], radius=5, fill=(120, 190, 236))

def reloj_pulsera(d, x, y):
    d.rectangle([x - 14, y - 50, x + 14, y + 50], fill=(110, 80, 60), outline=T, width=3)
    d.ellipse([x - 30, y - 30, x + 30, y + 30], fill=(214, 214, 222), outline=T, width=5)
    d.line([(x, y), (x, y - 18)], fill=T, width=4); d.line([(x, y), (x + 14, y)], fill=T, width=4)

def reloj_pared(d, x, y, r, hora, minuto):
    d.ellipse([x - r, y - r, x + r, y + r], fill=(252, 252, 250), outline=T, width=8)
    for i in range(12):
        a = i*math.pi/6
        d.line([(x + math.sin(a)*r*0.8, y - math.cos(a)*r*0.8), (x + math.sin(a)*r*0.92, y - math.cos(a)*r*0.92)], fill=T, width=5)
    am = minuto/60*2*math.pi; ah = (hora % 12 + minuto/60)/12*2*math.pi
    d.line([(x, y), (x + math.sin(ah)*r*0.5, y - math.cos(ah)*r*0.5)], fill=T, width=10)
    d.line([(x, y), (x + math.sin(am)*r*0.78, y - math.cos(am)*r*0.78)], fill=T, width=6)

def ramo(d, x, y, petalos=1.0):
    for k in range(3):
        d.line([(x, y + 80), (x - 30 + k*30, y - 10)], fill=(70, 140, 70), width=6)
    for k, col in enumerate(((240, 90, 120), (255, 200, 70), (200, 120, 230))):
        cx, cy = x - 34 + k*34, y - 20 - (k == 1)*20
        for j in range(5):
            if j/5 < petalos:
                a = j/5*2*math.pi
                d.ellipse([cx + math.cos(a)*16 - 12, cy + math.sin(a)*16 - 12, cx + math.cos(a)*16 + 12, cy + math.sin(a)*16 + 12], fill=col, outline=T, width=2)
        d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=(255, 230, 120), outline=T, width=2)

def cocina_fondo(revuelta=0.0):
    img = Image.new("RGB", (W, H), PARED); d = ImageDraw.Draw(img)
    Mu.suelo_madera(d, SUELO, H)
    # la encimera con el cajon y el fuego
    d.rectangle([0, SUELO - 380, 400, SUELO], fill=(214, 206, 196), outline=T, width=6)
    d.rectangle([0, SUELO - 400, 420, SUELO - 380], fill=(150, 146, 140), outline=T, width=5)
    d.rectangle([40, SUELO - 300, 360, SUELO - 200], fill=(226, 218, 208), outline=T, width=5)
    d.rounded_rectangle([170, SUELO - 260, 230, SUELO - 240], radius=6, fill=(170, 170, 180), outline=T, width=3)
    d.rectangle([200, SUELO - 420, 360, SUELO - 400], fill=(60, 60, 66))
    # el gancho de las llaves y una estanteria con platos
    d.rectangle([440, 860, 560, 880], fill=(150, 110, 80), outline=T, width=4)
    d.rectangle([60, 640, 380, 660], fill=(150, 110, 80), outline=T, width=4)
    if revuelta < 0.5:
        for k in range(4):
            d.ellipse([80 + k*75, 560, 150 + k*75, 640], fill=(246, 246, 250), outline=T, width=4)
    Mu.ventana(d, 620, 380, 980, 720)
    return img

# ---------------------------------------------------------------- los planos
def p_espejo(lt, t):
    """Pop se arregla delante del espejo para su cita. Por la ventana llega el taxi de Poke."""
    img = Image.new("RGB", (W, H), PARED); d = ImageDraw.Draw(img)
    Mu.suelo_madera(d, SUELO, H)
    # la ventana con la calle: el taxi del capitulo 1
    wx0, wy0, wx1, wy1 = 70, 300, 430, 640
    d.rectangle([wx0, wy0, wx1, wy1], fill=(186, 222, 246), outline=T, width=6)
    d.rectangle([wx0 + 6, wy1 - 90, wx1 - 6, wy1 - 6], fill=(150, 150, 160))
    tx = wx0 - 160 + 260*suave(lt/2.5)
    d.rounded_rectangle([tx, wy1 - 80, tx + 150, wy1 - 30], radius=12, fill=(250, 210, 60), outline=T, width=3)
    d.rectangle([tx + 40, wy1 - 100, tx + 110, wy1 - 80], fill=(250, 210, 60), outline=T, width=3)
    if lt > 2.7:
        Mu.poke(img, tx + 190 + 20*(lt - 2.7), wy1 - 8, 70, dict(pose="maleta", fase=lt*8), t)
    d = ImageDraw.Draw(img)
    d.line([((wx0 + wx1)/2, wy0), ((wx0 + wx1)/2, wy1)], fill=T, width=5)
    # el espejo y el reflejo
    mx0, my0, mx1, my1 = 600, 520, 1010, 1360
    d.rounded_rectangle([mx0 - 20, my0 - 20, mx1 + 20, my1 + 20], radius=30, fill=(196, 150, 104), outline=T, width=6)
    d.rectangle([mx0, my0, mx1, my1], fill=(214, 232, 240))
    st = dict(mira=(0.9, 0.0), boca="sonrisa", pajarita=lt > 1.4, feliz=0.0, brazos_arriba=False)
    if lt < 1.4:
        st.update(boca="plana")
    if 1.4 <= lt < 2.2:
        st.update(feliz=1.0, boca="abierta")
    if 2.2 <= lt < 3.4:          # ensaya sonrisas
        st.update(boca=("sonrisa", "abierta", "o", "abierta")[int((lt - 2.2)/0.3) % 4], feliz=1.0 if int((lt - 2.2)/0.3) % 2 else 0.0)
    if 3.4 <= lt < 4.4:          # nervios: se le escapa una palomita
        st.update(susto=0.8, boca="o")
    if lt >= 4.4:
        st.update(brazos_arriba=True, feliz=1.0, boca="abierta")
    refl = Image.new("RGB", (mx1 - mx0, my1 - my0), (214, 232, 240))
    Mu.pop(refl, (mx1 - mx0)*0.42, (my1 - my0) + 60, HPOP*1.05, dict(st, mira=(-0.9, 0.0)), t)
    refl = ImageOps.mirror(refl)
    img.paste(Image.blend(refl, Image.new("RGB", refl.size, (214, 232, 240)), 0.15), (mx0, my0))
    d = ImageDraw.Draw(img)
    d.line([(mx0 + 40, my0 + 60), (mx0 + 160, my0 + 20)], fill=(250, 250, 255), width=10)
    Mu.pop(img, 330, SUELO + 40, HPOP, st, t)
    d = ImageDraw.Draw(img)
    if 1.4 <= lt < 1.9:
        for k in range(4):
            a = k*math.pi/2 + lt*4
            Mu.texto(d, 330 + math.cos(a)*120, SUELO - 300 + math.sin(a)*60, "✦", 40, (255, 230, 90))
    if 3.5 <= lt < 4.4:          # la palomita que sale disparada de la cabeza
        k = (lt - 3.5)/0.9
        Mu.palomita_suelta(d, 330 + 60*k, SUELO - 520 - 300*math.sin(math.pi*k) + 400*k*k, 22)
        if lt < 3.8:
            Mu.texto(d, 400, SUELO - 640, "pop!", 50, (255, 214, 60))
    return img, (540, 1050, 1.0)

def p_nota(lt, t):
    img = Image.new("RGB", (W, H), (246, 246, 248)); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, H], fill=(246, 246, 248))
    d.line([(0, 1300), (W, 1300)], fill=T, width=8)
    nota_nevera(d, 540, 820, 3.0)
    return img, (540, 860, 1.0 + 0.03*lt)

# a donde se pega cada cosa en Mag (relativo a su centro), y de donde sale
COSAS_MAG = [  # (t, de, a_rel, dibujo)
    (2.0, (200, SUELO - 250), (-120, -180), ("cub", 0)), (2.1, (200, SUELO - 250), (110, -200), ("cub", 1)),
    (2.2, (200, SUELO - 250), (-60, -320), ("cub", 2)), (2.3, (200, SUELO - 250), (150, -60), ("cub", 0)),
    (2.4, (200, SUELO - 250), (-150, -40), ("cub", 1)),
    (2.7, (280, SUELO - 420), (-10, -120), ("sarten",)),
    (3.2, (500, 900), (120, -300), ("llaves",)),
    (3.6, (720, SUELO - 300), (-140, -260), ("movil",)),
    (4.0, (110, SUELO - 400), (40, 20), ("tostadora",)),
]

def dibuja_cosa(d, que, x, y, t):
    if que[0] == "cub":
        cubierto(d, x, y, 0.6 + que[1], que[1] % 3)
    elif que[0] == "sarten":
        sarten(d, x, y, -0.5, 0.8)
    elif que[0] == "llaves":
        llaves(d, x, y)
    elif que[0] == "movil":
        movil(d, x, y)
    elif que[0] == "tostadora":
        tostadora(d, x, y + 40, 0.9)

def cosas_pegadas(d, mx, my, lt, t, hasta=None):
    for t0, de, rel, que in COSAS_MAG:
        if hasta is not None and t0 > hasta: continue
        if lt < t0: continue
        k = suave((lt - t0)/0.4)
        x = de[0] + (mx + rel[0] - de[0])*k; y = de[1] + (my + rel[1] - de[1])*k - 140*math.sin(math.pi*k)
        dibuja_cosa(d, que, x, y, t)

def p_cocina(lt, t):
    """Mag se despierta y TODO lo metalico de la casa vuela hacia el. Nevera incluida."""
    img = cocina_fondo(); d = ImageDraw.Draw(img)
    mx = -200 + 640*suave(lt/2.0)
    # la mesa de Pop, con su tostada
    d.rectangle([600, SUELO - 260, 960, SUELO - 236], fill=(170, 124, 90), outline=T, width=5)
    for x in (630, 930):
        d.line([(x, SUELO - 236), (x, SUELO)], fill=T, width=10)
    pop_st = dict(mira=(-0.9, 0.0) if lt > 2.0 else (0.2, 0.4), boca="abierta" if lt < 2.0 else "o", feliz=1.0 if lt < 2.0 else 0.0,
                  pajarita=True, susto=0.6 if 2.0 < lt < 6.4 else 0.0)
    if lt >= 6.4:
        pop_st.update(enfado=1.0, susto=0.0, boca="grito", brazos_arriba=lt > 7.4)
    Mu.pop(img, 800, SUELO + 40, HPOP, pop_st, t)
    d = ImageDraw.Draw(img)
    d.ellipse([700, SUELO - 270, 860, SUELO - 240], fill=(250, 250, 252), outline=T, width=4)
    if lt < 3.6:
        movil(d, 720, SUELO - 300)
    if lt < 4.0:
        tostada(d, 900, SUELO - 300, 0.8)
    if lt < 6.5:               # el tenedor en la mano de Pop
        cubierto(d, 900, SUELO - 420, -1.1, 0)
    # la nevera
    if lt < 5.2:
        nevera(d, 1000, SUELO, 0.95, tiembla=1.0 if lt > 4.6 else 0.0, t=t)
        if lt > 4.6:
            Mu.texto(d, 1000, SUELO - 620, "?!", 70, (255, 214, 60))
    # Mag, bostezando, y lo que se le pega
    st = dict(mira=(0.6, 0.0), cansancio=1.0 if lt < 2.0 else 0.0, brazos_arriba=lt < 2.0, susto=1.0 if 2.0 < lt < 6.4 else 0.0,
              fondo=PARED)
    Mu.mag(img, mx, SUELO + 40, HMAG, st, t)
    d = ImageDraw.Draw(img)
    my = SUELO - 220
    cosas_pegadas(d, mx, my, lt, t)
    if 4.0 <= lt < 4.8:        # la tostada sale despedida de la tostadora... a la cabeza de Pop
        k = (lt - 4.0)/0.8
        tostada(d, 110 + (800 - 110)*k, SUELO - 500 - 500*math.sin(math.pi*k) + (SUELO - 760 - (SUELO - 500))*k, 0.8)
    elif lt >= 4.8:
        tostada(d, 800, SUELO - 690, 0.8)
    if lt >= 5.2:              # la nevera cruza la cocina y se le pega encima
        k = suave((lt - 5.2)/0.7)
        nevera(d, 1000 + (mx - 1000)*k, SUELO, 1.05)
        if 5.9 < lt < 6.4:
            Mu.texto(d, mx, SUELO - 700, "SLAM!", 100, (255, 90, 70))
        if lt > 5.9:            # solo se le ven los ojos por un lado
            d.ellipse([mx - 160, SUELO - 520, mx - 110, SUELO - 470], fill=Mu.BLANCO, outline=T, width=4)
            d.ellipse([mx - 145, SUELO - 505, mx - 125, SUELO - 485], fill=T)
    if 6.5 <= lt < 7.0:        # hasta el tenedor de Pop se va
        k = (lt - 6.5)/0.5
        cubierto(d, 900 + (mx - 900)*k, SUELO - 420 - 100*math.sin(math.pi*k), -1.1 + 3*k, 0)
    if lt > 7.2:
        Mu.vena(d, 860, SUELO - 560, 140, t)
    for k, tc in enumerate((2.0, 2.2, 2.4)):
        if tc < lt < tc + 0.3:
            Mu.texto(d, mx + 120 - k*80, SUELO - 640 + k*40, "CLINK!", 54, (250, 250, 250))
    if 2.7 < lt < 3.1:
        Mu.texto(d, mx - 60, SUELO - 700, "CLANG!", 70, (255, 214, 60))
    return img, (540, 1060, 1.04)

def p_reloj(lt, t):
    """El reloj de Pop esta pegado en Mag. La pajarita de Pop tiene clip metalico..."""
    img = cocina_fondo(revuelta=0.0); d = ImageDraw.Draw(img)
    mx = 330
    # Mag se sacude las cosas, que caen
    for i, (t0, de, rel, que) in enumerate(COSAS_MAG):
        k = suave(lt/0.6)
        x = mx + rel[0] + (i - 4)*30*k; y = SUELO - 220 + rel[1] + (SUELO - 40 - (SUELO - 220 + rel[1]))*k
        dibuja_cosa(d, que, x, y, t)
    sacude = math.sin(t*50)*12 if lt < 0.7 else 0
    st_m = dict(mira=(0.8, 0.0) if lt > 1.0 else (0, 0), enfado=1.0 if lt > 4.2 else 0.0, susto=1.0 if 3.4 < lt < 4.2 else 0.0, fondo=PARED)
    Mu.mag(img, mx + sacude, SUELO + 40, HMAG, st_m, t)
    d = ImageDraw.Draw(img)
    if lt < 3.4:
        reloj_pulsera(d, mx + 150, SUELO - 300)
    if lt < 0.8:
        Mu.texto(d, mx, SUELO - 720, "CRASH!", 90, (255, 214, 60))
    # Pop
    if lt < 2.3:
        px = 820; st_p = dict(pajarita=True, mira=((-1, 1)[int(lt/0.5) % 2]*0.9, 0.0), boca="o", ceja=0.4)
    elif lt < 3.3:
        px = 820 - 150*suave((lt - 2.3)/0.9); st_p = dict(pajarita=True, mira=(-0.9, 0), enfado=1.0, boca="plana")
    elif lt < 3.8:              # la pajarita tira de el: sale volando hacia Mag
        k = suave((lt - 3.3)/0.5); px = 670 - (670 - (mx + 190))*k
        st_p = dict(pajarita=True, mira=(-0.9, 0), susto=1.0, boca="grito", pajarita_dx=-40*k)
    else:
        px = mx + 190 + 40*suave((lt - 4.4)/0.6)
        st_p = dict(pajarita=True, mira=(-0.9, 0), enfado=1.0 if lt > 4.4 else 0.0, boca="grito" if lt > 4.4 else "dolor", torcida=1.0)
    if 2.0 <= lt < 2.4:
        Mu.texto(d, 820, SUELO - 640, "!", 110, (255, 80, 70))
    Mu.pop(img, px, SUELO + 40, HPOP, st_p, t)
    d = ImageDraw.Draw(img)
    if 3.3 <= lt < 3.8:
        for k in range(4):
            d.line([(px + 120 + k*40, SUELO - 400 + k*40), (px + 260 + k*40, SUELO - 400 + k*40)], fill=(150, 150, 160), width=6)
        Mu.texto(d, px + 100, SUELO - 640, "ZZZIP!", 60, (250, 250, 250))
    if 3.8 <= lt < 4.4:
        Mu.texto(d, (mx + px)/2, SUELO - 700, "SPLAT!", 100, (255, 214, 60))
        Mu.estrellas_simple(d, px, SUELO - 560, t) if hasattr(Mu, "estrellas_simple") else None
    if lt > 4.6:
        Mu.rayo(d, (mx + 40, SUELO - 380), (px - 30, SUELO - 300), t)
    return img, (560, 1080, 1.06 + 0.04*suave((lt - 4.0)/1.0))

def p_guerra(lt, t):
    """Humo por las orejas, #@%!, metralleta de palomitas y lluvia de cucharas."""
    img = cocina_fondo(revuelta=1.0 if lt > 6.0 else 0.0); d = ImageDraw.Draw(img)
    tiembla = math.sin(t*37)*14 if 2.5 < lt < 7.0 else 0
    mx, px = 300, 800
    sale = suave((lt - 7.2)/1.2)
    mx += 900*sale; px += 900*sale
    st_m = dict(enfado=1.0, mira=(0.9, 0), brazos_arriba=4.5 < lt < 6.5 and (t % 0.3) < 0.15, fondo=PARED)
    st_p = dict(enfado=1.0 if lt < 2.5 else 0.0, susto=1.0 if 2.5 <= lt < 4.5 else 0.0, mira=(-0.9, 0), pajarita=True, torcida=1.0,
                boca="grito", brazos_arriba=lt < 2.5 and (t % 0.4) < 0.2, explota=0.4 if 2.5 <= lt < 4.5 and (t*8) % 1.0 < 0.5 else 0.0)
    Mu.mag(img, mx + tiembla, SUELO + 40, HMAG, st_m, t)
    Mu.pop(img, px - tiembla, SUELO + 40, HPOP, st_p, t)
    d = ImageDraw.Draw(img)
    if lt < 2.5 or lt > 6.5:
        Mu.humo_enfado(d, mx, SUELO - 560, 50, t); Mu.humo_enfado(d, px, SUELO - 560, 50, t + 0.4)
        k = min(1.0, lt/2.5) if lt < 2.5 else 1.0
        if (t*3) % 1.0 < 0.5:
            Mu.grawlix(d, mx + 40, SUELO - 780, 70 + 60*k, t, "#@%!", semilla=1)
        else:
            Mu.grawlix(d, px - 40, SUELO - 760, 70 + 60*k, t, "$&!?", semilla=2)
    if 2.5 <= lt < 4.5:          # la metralleta de palomitas
        rnd = random.Random(int(t*12))
        for i in range(9):
            f = ((t*3 + i/9) % 1.0)
            Mu.palomita_suelta(d, px - 60 - (px - mx - 120)*f, SUELO - 300 + rnd.uniform(-60, 60), 20)
        Mu.texto(d, (mx + px)/2, SUELO - 780, "POP POP POP POP", 56, (255, 214, 60))
    if 4.5 <= lt < 6.5:          # y la lluvia de cucharas de vuelta
        for i in range(6):
            f = ((t*2 + i/6) % 1.0)
            cubierto(d, mx + 80 + (px - mx - 120)*f, SUELO - 420 - 160*math.sin(math.pi*f), f*8 + i, 1)
    if 6.0 <= lt < 6.6:
        Mu.texto(d, 230, 520, "CRASH!", 90, (255, 214, 60))
        for k in range(5):
            x = 100 + k*70
            d.polygon([(x, 640 + (lt - 6.0)*900), (x + 40, 650 + (lt - 6.0)*900), (x + 20, 690 + (lt - 6.0)*900)], fill=(246, 246, 250), outline=T)
    if 8.4 < lt < 9.0:
        Mu.texto(d, 900, 900, "SLAM!", 100, (255, 90, 70))
    return img, (560 + 200*sale, 1080, 1.08 if 2.5 < lt < 7.0 else 1.02)

# el ascensor en corte: los pisos a la izquierda, el hueco a la derecha
FILA = 330
def y_suelo_piso(i):         # 0 = porteria, 3 = el 3o
    return 280 + FILA*(4 - i)

def p_ascensor(lt, t):
    """Lo del Ep. 1, visto desde el hueco del ascensor: bajan discutiendo, Poke, SHWIP, POP POP POP."""
    img = Image.new("RGB", (W, H), (70, 66, 74)); d = ImageDraw.Draw(img)
    colores = {3: Mu.PAREDES["p3"], 2: Mu.PAREDES["p2"], 1: Mu.PAREDES["p1"], 0: Mu.PAREDES["porteria"]}
    for i in range(4):
        y1 = y_suelo_piso(i); y0 = y1 - FILA + 18
        d.rectangle([0, y0, 640, y1], fill=colores[i])
        d.rectangle([0, y1, 660, y1 + 18], fill=(150, 120, 100), outline=T, width=4)
        Mu.texto(d, 60, y0 + 50, "3210"[3 - i] if False else str(i) if i else "0", 40, (250, 250, 250))
    d.rectangle([640, 200, 660, H], fill=(120, 110, 100), outline=T, width=4)
    d.rectangle([0, y_suelo_piso(0) + 18, W, H], fill=(120, 120, 130))
    # vecinos de fondo: Bubble en su piso con las flores (la cita), cajas en el 1o
    Mu.bubble(img, 300, y_suelo_piso(2) - 170, 190, dict(feliz=1.0, cuerda=True, mira=(0.5, 0), rubor=True), t)
    ramo(ImageDraw.Draw(img), 390, y_suelo_piso(2) - 140)
    d = ImageDraw.Draw(img)
    for x in (120, 220):
        d.rectangle([x, y_suelo_piso(1) - 110, x + 90, y_suelo_piso(1)], fill=(206, 168, 120), outline=T, width=4)
    # la cabina
    if lt < 3.0:
        k = suave(lt/3.0); piso_f = 3 - 3*k
    elif lt < 6.9:
        piso_f = 0
    else:
        piso_f = 3*suave((lt - 6.9)/2.3)
    cy1 = y_suelo_piso(0) - (y_suelo_piso(0) - y_suelo_piso(3))*piso_f/3
    cx0, cx1 = 680, 1050; cy0 = cy1 - 300
    d.line([((cx0 + cx1)/2, 0), ((cx0 + cx1)/2, cy0)], fill=(40, 40, 46), width=8)
    d.rectangle([cx0, cy0, cx1, cy1], fill=(214, 200, 176), outline=T, width=6)
    discuten = lt < 3.5
    lleno = suave((lt - 5.2)/1.0)
    Mu.pop(img, cx0 + 100 + (math.sin(t*40)*6 if discuten else 0), cy1, 200, dict(enfado=1.0 if lt < 4.6 else 0.0, susto=1.0 if lt >= 4.6 else 0.0,
           mira=(0.9, 0) if discuten else (-0.9, 0), pajarita=True, torcida=1.0, brazos_arriba=discuten and (t % 0.5) < 0.25), t)
    Mu.mag(img, cx1 - 90, cy1, 210, dict(enfado=1.0 if discuten else 0.0, susto=1.0 if 4.2 < lt < 5.0 else 0.0, mira=(-0.9, 0),
           fondo=(214, 200, 176)), t)
    d = ImageDraw.Draw(img)
    if discuten:
        Mu.grawlix(d, (cx0 + cx1)/2, cy0 - 70, 60, t, "#@%!" if (t*3) % 1.0 < 0.5 else "$&!?", semilla=4)
    if lt > 4.6:
        llaves_k = 1.0
        d.ellipse([cx1 - 110, cy1 - 150, cx1 - 80, cy1 - 120], outline=(214, 170, 50), width=6)
    if lleno > 0:
        rnd = random.Random(3)
        nivel = cy1 - 300*lleno*1.05
        for i in range(90):
            x = rnd.uniform(cx0 + 15, cx1 - 15); y = rnd.uniform(cy0 + 10, cy1 - 10)
            if y > nivel:
                Mu.palomita_suelta(d, x, y, 18)
        if 6.9 < lt:           # palomitas que se escapan mientras sube
            for i in range(6):
                f = ((t*1.2 + i/6) % 1.0)
                Mu.palomita_suelta(d, cx0 + 40 + i*50, cy1 + f*500, 14)
    # la puerta de la cabina, a la izquierda (se abre en la porteria)
    abre = suave((lt - 3.1)/0.3)*(1 - suave((lt - 6.3)/0.4))
    d.rectangle([cx0 - 12, cy0 + 300*abre*0.9, cx0 + 12, cy1], fill=(170, 172, 180), outline=T, width=3)
    # Poke en la porteria, con la llave en la cabeza
    pk = dict(pose="caido", mira=(0.9, 0.0), boca="sonrisa", parpadeo=parpadeo(lt))
    if 3.4 < lt < 4.2:
        pk.update(boca="sonrisa")
    if lt > 4.2:
        pk.update(susto=0.6, boca="o")
    if lt > 5.2:
        pk.update(susto=1.0, boca="grito", pose="arriba")
    info = Mu.poke(img, 520, y_suelo_piso(0), 230, pk, t)
    d = ImageDraw.Draw(img)
    vuela = suave((lt - 4.2)/0.4)
    kx = 540 + (cx1 - 100 - 540)*vuela; ky = (info["top"] + 4) + (cy1 - 140 - info["top"] - 4)*vuela
    if lt < 4.65:
        d.ellipse([kx - 12, ky - 12, kx + 12, ky + 12], outline=(214, 170, 50), width=6)
        d.line([(kx + 10, ky), (kx + 40, ky)], fill=(214, 170, 50), width=6)
    if 4.2 < lt < 4.7:
        Mu.texto(d, 640, info["top"] - 60, "SHWIP!", 50, (200, 220, 255))
    if lt > 5.6:
        Mu.palomitas_pegadas(img, info, suave((lt - 5.6)/0.6))
        d = ImageDraw.Draw(img)
    if 5.2 < lt < 6.4:
        Mu.texto(d, 860, cy0 - 90, "POP! POP! POP!", 56, (255, 214, 60))
    return img, (W/2, H/2, 1.0)

def p_avalancha(lt, t):
    """Se abren las puertas en el 3o: avalancha de palomitas, y ellos encima, surfeando."""
    img = Image.new("RGB", (W, H), Mu.PAREDES["p3"]); d = ImageDraw.Draw(img)
    Mu.suelo_madera(d, SUELO, H)
    d.rectangle([60, SUELO - 760, 440, SUELO], fill=(196, 198, 206), outline=T, width=6)          # las puertas del ascensor
    abre = suave(lt/0.4)
    if abre > 0:
        d.rectangle([250 - 180*abre, SUELO - 760, 250 + 180*abre, SUELO], fill=(250, 248, 236))
    minuto = 59 if lt < 4.8 else 0
    reloj_pared(d, 760, 520, 120, 7 if minuto else 8, minuto)
    Mu.puerta(d, 860, SUELO - 40, "3", alto=600, ancho=280)
    # la ola de palomitas
    frente = 250 + 950*suave((lt - 0.4)/2.6)
    alto = 640*(1 - 0.6*suave((lt - 2.4)/1.2))
    rnd = random.Random(8)
    for i in range(340):
        x = rnd.uniform(40, 1200); y = rnd.uniform(SUELO - 760, SUELO + 40)
        top = SUELO + 40 - alto*max(0.0, 1 - max(0, x - frente + 300)/300)*(0.6 + 0.4*math.sin(x/90 + t*3)**2)
        if x < frente and y > top:
            Mu.palomita_suelta(d, x, y, 24)
    # Pop y Mag encima, surfeando (Mag en la sarten)
    sx = min(frente - 220, 640) if lt < 3.2 else 640
    sy = SUELO + 40 - alto*0.95 + 30
    sarten(d, sx - 120, sy + 10, 0.0, 1.1)
    st_m = dict(susto=1.0 if lt < 3.2 else 0.0, brazos_arriba=lt < 3.2, mira=(0.6, -0.3) if lt < 4.2 else (0.4, 0.2), fondo=Mu.PAREDES["p3"])
    Mu.mag(img, sx - 120, sy, 300, st_m, t)
    st_p = dict(susto=1.0 if lt < 3.2 else 0.0, brazos_arriba=lt < 3.2, pajarita=True, torcida=1.0, boca="grito" if lt < 3.2 else "o",
                mira=(0.7, -0.4) if lt > 4.2 else (0.6, 0))
    if lt >= 5.0:
        st_p.update(susto=1.0, boca="grito", mira=(0.9, 0.0), brazos_arriba=False)
    Mu.pop(img, sx + 100, sy, 280, st_p, t)
    d = ImageDraw.Draw(img)
    if lt < 2.6:
        Mu.texto(d, 640, 820, "WHOOOOSH!", 80, (250, 250, 250))
    if 5.0 < lt < 5.6:
        Mu.texto(d, sx + 100, sy - 360, "!!", 120, (255, 80, 70))
    if lt > 5.6:
        Mu.texto(d, 860, 760, "DING-DONG!", 70, (255, 214, 60))
    return img, (560, 1080, 1.04)

def p_cita(lt, t):
    """Ding-dong. La cita de Pop es... Bubble. Pop hace un pop pequeñito."""
    img = Image.new("RGB", (W, H), PARED); d = ImageDraw.Draw(img)
    Mu.suelo_madera(d, SUELO, H)
    rnd = random.Random(5)
    for i in range(30):                       # el desastre del suelo
        Mu.palomita_suelta(d, rnd.uniform(0, W), rnd.uniform(SUELO + 20, H - 40), 18)
    dx0, dx1 = 520, 900
    abre = suave((lt - 2.2)/0.4)
    d.rectangle([dx0 - 20, SUELO - 760, dx1 + 20, SUELO], fill=(240, 236, 228), outline=T, width=6)
    d.rectangle([dx0, SUELO - 740, dx1, SUELO], fill=Mu.PAREDES["p3"] if abre > 0 else (132, 96, 70))
    if abre > 0:
        tiembla = 1.0 if lt > 4.2 else 0.0
        Mu.bubble(img, (dx0 + dx1)/2, SUELO - 470, 420, dict(mira=(-0.7, 0.2), rubor=lt < 4.2, feliz=1.0 if 2.8 < lt < 4.0 else 0.0,
                  susto=1.0 if lt > 4.2 else 0.0, boca="o" if lt > 4.2 else "sonrisa", tiembla=tiembla, cuerda=True), t)
        d = ImageDraw.Draw(img)
        ramo(d, (dx0 + dx1)/2 + 150, SUELO - 380, petalos=1.0 if lt < 4.4 else max(0.0, 1 - (lt - 4.4)))
        if lt > 4.4:                          # los petalos se caen del susto
            for k in range(6):
                f = (lt - 4.4 + k*0.15) % 1.2
                d.ellipse([(dx0 + dx1)/2 + 130 + k*12 - 10, SUELO - 380 + f*500 - 10, (dx0 + dx1)/2 + 130 + k*12 + 10, SUELO - 380 + f*500 + 10],
                          fill=(240, 90, 120), outline=T, width=2)
    d.rectangle([dx0, SUELO - 740, dx0 + (dx1 - dx0)*(1 - 0.85*abre), SUELO], fill=(132, 96, 70), outline=T, width=6)
    # Pop
    px = 260 + 120*suave(lt/1.2)
    st = dict(pajarita=True, torcida=1.0 if lt < 1.4 else 1.0 - suave((lt - 1.4)/0.6), mira=(0.9, 0.0), boca="o", ceja=0.3)
    if 2.6 <= lt < 3.8:
        st.update(boca="abierta", feliz=1.0, ceja=0.0)
    if lt >= 3.8:
        st.update(susto=0.7, boca="sonrisa", feliz=0.0)
    Mu.pop(img, px, SUELO + 40, HPOP, st, t)
    d = ImageDraw.Draw(img)
    if 4.0 <= lt < 4.6:
        k = (lt - 4.0)/0.6
        Mu.palomita_suelta(d, px + 40*k, SUELO - 560 - 200*math.sin(math.pi*k), 18)
        Mu.texto(d, px + 30, SUELO - 700, "pop.", 50, (255, 214, 60))
    if lt > 4.8:
        Mu.texto(d, 540, 520, "...", 100, (250, 250, 250))
    return img, (600, 1050, 1.0 + 0.1*suave((lt - 3.8)/1.5))

def p_fin(lt, t, dur=3.5):
    img = Image.new("RGB", (W, H), (34, 32, 44)); d = ImageDraw.Draw(img)
    a = suave(lt/0.5)*suave((dur - lt)/0.4)
    c = lambda col: tuple(int(34 + (v - 34)*a) for v in col)
    d.rounded_rectangle([W/2 - 300, 640, W/2 + 300, 790], radius=24, fill=c((52, 50, 64)), outline=c((255, 214, 90)), width=6)
    d.text((W/2, 715), "BLOCK 7", font=fuente(100), fill=c((255, 214, 90)), anchor="mm")
    d.text((W/2, 880), "Ep. 2 · The Argument", font=fuente(52), fill=c((240, 240, 240)), anchor="mm")
    b = suave((lt - 1.0)/0.5)*suave((dur - lt)/0.4)
    cb = lambda col: tuple(int(34 + (v - 34)*b) for v in col)
    d.text((W/2, 1130), "NEXT:", font=fuente(40), fill=cb((200, 200, 210)), anchor="mm")
    d.text((W/2, 1200), "The Date", font=fuente(66), fill=cb((255, 140, 160)), anchor="mm")
    return img, (W/2, H/2, 1.0)

# ---------------------------------------------------------------- el montaje
GUION = [
    (p_espejo, 6.0, [(0.0, "tema"), (1.4, "tin"), (3.5, "popito")]),
    (p_nota, 1.8, []),
    (p_cocina, 9.0, [(0.0, "bostezo"), (2.0, "clink"), (2.2, "clink"), (2.4, "clink"), (2.7, "clang"), (3.2, "clink"), (3.6, "swip"),
                     (4.0, "clang"), (4.6, "tiembla_corto"), (5.2, "screech"), (5.9, "slam"), (6.5, "swip")]),
    (p_reloj, 6.2, [(0.0, "crash"), (2.0, "susto"), (3.3, "zip"), (3.8, "splat")]),
    (p_guerra, 9.0, [(0.0, "bronca2.4"), (2.5, "metralla2.0"), (4.5, "cucharas2.0"), (6.0, "crash"), (6.6, "bronca1.6"), (8.4, "slam")]),
    (p_ascensor, 9.4, [(0.0, "bronca3.0"), (0.0, "motor3.0"), (3.0, "ding_asc"), (3.1, "puerta_asc"), (4.2, "swip"), (4.6, "tiembla_corto"),
                       (5.2, "pops"), (6.3, "puerta_asc"), (6.9, "motor2.3")]),
    (p_avalancha, 7.0, [(0.0, "ding_asc"), (0.4, "avalancha2.8"), (4.8, "tic"), (5.0, "susto"), (5.6, "dingdong")]),
    (p_cita, 6.2, [(0.0, "pasos1.2"), (2.2, "puerta"), (4.0, "popito"), (4.3, "susto")]),
    (lambda lt, t: p_fin(lt, t, 3.5), 3.5, [(0.0, "fin")]),
]

def tabla():
    t = 0.0; out = []
    for fn, dur, sfx in GUION:
        out.append((t, t + dur, fn, sfx)); t += dur
    return out, t

TABLA, DUR = tabla()
_I = {fn: a for a, b, fn, s in TABLA}
SILENCIOS = [(_I[p_ascensor] + 3.4, _I[p_ascensor] + 5.2), (_I[p_cita] + 4.0, _I[p_cita] + 6.2)]

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
                fotograma(a + (b - a)*f).resize((270, 480)).save(OUT + f"e2_{i:02d}_{k}.jpg", quality=85)
        print(f"{len(TABLA)} planos, {DUR:.1f} s"); return
    if args and args[0] == "en":
        for s in args[1:]:
            fotograma(float(s)).resize((540, 960)).save(OUT + f"e2_en_{float(s):05.1f}.jpg", quality=88)
        return
    S.audio(OUT + "ep02_audio.wav", TABLA, DUR, SILENCIOS)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-i", OUT + "ep02_audio.wav", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19",
                          "-preset", "medium", "-c:a", "aac", "-b:a", "192k", "-shortest", OUT + "BLOCK7_ep02.mp4"], stdin=subprocess.PIPE)
    for i in range(int(DUR*FPS)):
        p.stdin.write(fotograma(i/FPS).tobytes())
    p.stdin.close(); p.wait()
    print(f"hecho: {DUR:.1f} s")

if __name__ == "__main__":
    main()
