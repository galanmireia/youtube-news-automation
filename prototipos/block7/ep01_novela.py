"""BLOCK 7 · Ep. 1 — THE SOFA, version telenovela (~58 s, vertical, mudo, rotulos en ingles).

Arranca por el final (Mag, con flores, en shock: ¡TAN!) y vuelve atras: Poke se
muda con un sofa que no cabe en el ascensor, lo sube a rastras y, a ciegas, entra
en la casa equivocada: la de Bubble. Flechazo a camara lenta, se sientan, las
manos se acercan sobre el cojin... y una sombra de herradura cae encima. Se abre
la puerta: Mag, el novio, con un ramo. Triple zoom, ¡TAN TAN TAAAN! Se le caen
las flores, la foto de los dos en la pared, a Poke se le cae un petalo, a Bubble
una lagrima. Las cotillas lo han visto todo. Imagen congelada: TO BE CONTINUED.
-> Ep. 2, THE SLAP.
"""
import math, random, re, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mundo as Mu
import sonido as S
import ep01_sofa as E
import cabecera as C
from mundo import T, W, H, suave, fuente

OUT = str(Path(__file__).resolve().parent) + "/salida/"
FPS = 25
SUELO = 1500
HP, HM = 520, 520
PARED, PASILLO = (226, 206, 236), (200, 186, 226)
ORO = (236, 196, 96)
SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf"

def serif(px):
    return ImageFont.truetype(SERIF, int(px))

# ---------------------------------------------------------------- los efectos de telenovela
def viñeta(img, color, fuerza):
    """Bordes tintados (rosa del amor, rojo del drama, azul de la pena)."""
    if fuerza <= 0.01:
        return img
    capa = Image.new("L", (W, H), 255); c = ImageDraw.Draw(capa)
    for k in range(14):
        f = k/14
        c.ellipse([-W*0.35 + f*W*0.3, -H*0.2 + f*H*0.2, W*1.35 - f*W*0.3, H*1.2 - f*H*0.2], fill=int(255*(1 - f)**1.6))
    capa = capa.point(lambda v: int(v*fuerza*0.85))
    return Image.composite(Image.new("RGB", (W, H), color), img, capa)

def flash(img, color, a):
    return Image.blend(img, Image.new("RGB", (W, H), color), max(0.0, min(1.0, a))) if a > 0.01 else img

def rayos(img, cx, cy, t, color=(255, 255, 255), alfa=90, n=34):
    """Las lineas radiales del zoom dramatico."""
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0)); c = ImageDraw.Draw(capa)
    rnd = random.Random(int(t*12))
    for k in range(n):
        a = k/n*2*math.pi + rnd.uniform(-0.05, 0.05); da = rnd.uniform(0.012, 0.03)
        r0 = rnd.uniform(560, 760)
        c.polygon([(cx + math.cos(a)*r0, cy + math.sin(a)*r0), (cx + math.cos(a - da)*1800, cy + math.sin(a - da)*1800),
                   (cx + math.cos(a + da)*1800, cy + math.sin(a + da)*1800)], fill=color + (alfa,))
    img = img.convert("RGBA"); img.alpha_composite(capa)
    return img.convert("RGB")

def destellos(d, t, zona, n=10, semilla=2):
    rnd = random.Random(semilla)
    for k in range(n):
        x = rnd.uniform(*zona[0]); y = rnd.uniform(*zona[1]); f = (t*0.8 + rnd.random()) % 1.0
        r = 22*math.sin(math.pi*f)
        if r > 2:
            d.polygon([(x, y - r*2), (x + r*0.4, y - r*0.4), (x + r*2, y), (x + r*0.4, y + r*0.4), (x, y + r*2),
                       (x - r*0.4, y + r*0.4), (x - r*2, y), (x - r*0.4, y - r*0.4)], fill=(255, 250, 220))

def sepia(img):
    return ImageOps.colorize(ImageOps.grayscale(img), black=(46, 30, 18), white=(250, 232, 196))

def ramo(d, x, y, s=1.0, petalos=1.0):
    for k in range(3):
        d.line([(x, y + 80*s), (x + (-30 + k*30)*s, y - 10*s)], fill=(70, 140, 70), width=int(6*s))
    d.polygon([(x - 40*s, y + 10*s), (x + 40*s, y + 10*s), (x + 10*s, y + 70*s), (x - 10*s, y + 70*s)], fill=(250, 240, 250), outline=T)
    for k, col in enumerate(((240, 90, 120), (255, 200, 70), (200, 120, 230))):
        cx, cy = x + (-34 + k*34)*s, y + (-20 - (k == 1)*20)*s
        for j in range(5):
            if j/5 < petalos:
                a = j/5*2*math.pi
                d.ellipse([cx + math.cos(a)*16*s - 12*s, cy + math.sin(a)*16*s - 12*s, cx + math.cos(a)*16*s + 12*s,
                           cy + math.sin(a)*16*s + 12*s], fill=col, outline=T, width=max(2, int(2*s)))
        d.ellipse([cx - 8*s, cy - 8*s, cx + 8*s, cy + 8*s], fill=(255, 230, 120), outline=T, width=max(2, int(2*s)))

def petalo(d, x, y, r, ang, col=(240, 90, 120)):
    ca, sa = math.cos(ang), math.sin(ang)
    pts = [(x + ca*r*math.cos(u) - sa*r*0.55*math.sin(u), y + sa*r*math.cos(u) + ca*r*0.55*math.sin(u))
           for u in [i/12*2*math.pi for i in range(12)]]
    d.polygon(pts, fill=col, outline=T)

def foto(img, x0, y0, x1, y1):
    """La foto de la boda en la pared: Bubble con su velo y Mag, felices, con un corazon."""
    d = ImageDraw.Draw(img)
    g = max(4, int((x1 - x0)*0.05))
    d.rectangle([x0, y0, x1, y1], fill=(212, 170, 70), outline=T, width=max(3, g//3))
    fondo = (196, 226, 244)
    d.rectangle([x0 + g, y0 + g, x1 - g, y1 - g], fill=fondo, outline=T, width=max(2, g//4))
    w, h = x1 - x0, y1 - y0
    Mu.bubble(img, x0 + w*0.33, y0 + h*0.45, h*0.56, dict(feliz=1.0, rubor=True, mira=(0.8, 0), cuerda=False, velo=True), 0.0)
    Mu.mag(img, x0 + w*0.68, y1 - g - h*0.02, h*0.68, dict(feliz=1.0, fondo=fondo, mira=(-0.8, 0)), 0.0)
    Mu.corazon(ImageDraw.Draw(img), x0 + w*0.5, y0 + h*0.2, h*0.09)

# ---------------------------------------------------------------- el piso de Bubble
SOFA_X, SEAT = 430, SUELO - 120
PUERTA_X, PUERTA_W, PUERTA_A = 900, 290, 640

def salon(abre=0.0):
    img = Image.new("RGB", (W, H), PARED); d = ImageDraw.Draw(img)
    Mu.suelo_madera(d, SUELO, H, color=(206, 170, 130))
    Mu.ventana(d, 470, 380, 760, 700, cielo=(250, 214, 190))
    x0, y0 = PUERTA_X - PUERTA_W/2, SUELO - PUERTA_A
    d.rectangle([x0 - 18, y0 - 18, x0 + PUERTA_W + 18, SUELO], fill=(240, 236, 228), outline=T, width=5)
    d.rectangle([x0, y0, x0 + PUERTA_W, SUELO], fill=PASILLO)
    d.line([(x0, SUELO - 60), (x0 + PUERTA_W, SUELO - 60)], fill=(170, 156, 196), width=4)
    a = PUERTA_W*(1 - 0.85*abre)                      # la hoja gira hacia dentro, bisagra a la derecha
    d.polygon([(x0 + PUERTA_W - a, y0 - 10*abre), (x0 + PUERTA_W, y0), (x0 + PUERTA_W, SUELO), (x0 + PUERTA_W - a, SUELO + 10*abre)],
              fill=(176, 120, 150), outline=T)
    if abre < 0.3:
        d.ellipse([x0 + 30 - 16, SUELO - PUERTA_A*0.47 - 16, x0 + 30 + 16, SUELO - PUERTA_A*0.47 + 16], fill=(232, 196, 90), outline=T, width=4)
    foto(img, 100, 420, 320, 600)
    return img

def mag_puerta(img, st, t, flores=True):
    top = SUELO + 20 - HM*0.95; w = HM*0.5
    m = (PUERTA_X, top + w*0.85)
    if flores:
        st = dict(st, tira=m)
    Mu.mag(img, PUERTA_X, SUELO + 20, HM, dict(dict(fondo=PASILLO), **st), t)
    if flores:
        ramo(ImageDraw.Draw(img), m[0], m[1] - 30, 1.5)

# ---------------------------------------------------------------- los planos nuevos
def p_titulo(lt, t, dur=2.6):
    img = Image.new("RGB", (W, H), (70, 10, 24)); d = ImageDraw.Draw(img)
    for k in range(24):                               # el telon de terciopelo
        x = k*W/24
        d.rectangle([x, 0, x + W/48, H], fill=(96, 16, 34))
    img = viñeta(img, (20, 0, 6), 1.0); d = ImageDraw.Draw(img)
    a = suave((lt - 0.9)/0.4)
    if a > 0:
        col = tuple(int(70 + (v - 70)*a) for v in ORO)
        d.text((W/2, 820), "Block 7", font=serif(190), fill=col, anchor="mm", stroke_width=6, stroke_fill=(40, 6, 14))
        Mu.corazon(d, W/2, 640 - 30*(1 - a), 46*a + 1)
        d.text((W/2, 990), "Love. Lies. Neighbours.", font=serif(62), fill=(250, 236, 236), anchor="mm")
        destellos(d, t, ((180, 900), (700, 1000)), 8)
    b = suave((lt - 1.7)/0.4)
    if b > 0:
        d.text((W/2, 1400), "Earlier that day…", font=serif(70), fill=tuple(int(70 + (v - 70)*b) for v in (250, 250, 250)), anchor="mm")
    return img, (W/2, H/2, 1.0 + 0.04*lt/dur)

def p_amor(lt, t):
    """Entra con el sofa en la cabeza: CRASH. Bubble. Flechazo a camara lenta. Se sientan, cada uno en una punta."""
    img = salon(abre=1.0 if lt < 1.6 else max(0.0, 1 - (lt - 1.6)/0.5))
    lenta = 1.6 <= lt < 4.6
    if lt < 1.0:
        x = 900 - 380*suave(lt/1.0)
        info = Mu.poke(img, x, SUELO + 40, HP, dict(pose="arriba", fase=lt*6, boca="o"), t)
        Mu.sofa(img, x, info["cara"][1] - 40, 470, rasgado=0.9)
    else:
        Mu.sofa(img, SOFA_X, SUELO - 130, 520, rasgado=0.9)
    # Bubble
    if lt < 4.6:
        bx = 290; by = 820 - 260*suave((lt - 1.0)/0.25)*(1 - suave((lt - 1.4)/0.6))
    else:
        k = suave((lt - 4.6)/0.9); bx = 290; by = 820 + (SEAT - 250 - 820)*k
    st_b = dict(mira=(0.8, 0.2), susto=1.0 if 1.0 < lt < 1.7 else 0.0, boca="grito" if 1.0 < lt < 1.6 else "sonrisa",
                rubor=lt > 2.2, pose="caido", amor=1.0 if 3.0 < lt < 4.4 else 0.0)
    if 5.5 < lt < 6.3:
        st_b["pose"] = "cuerda"                       # da palmaditas al cojin: sientate
    if lt > 6.6:
        st_b.update(mira=(0.0, 0.3) if (lt % 1.6) < 0.8 else (0.8, 0.2), rubor=True)
    if lt > 1.0:
        Mu.bubble(img, bx, by + (math.sin(t*0.7)*10 if lenta else 0), 420, st_b, t*(0.3 if lenta else 1.0))
    # Poke
    if lt >= 1.0:
        st = dict(pose="caido", mira=(-0.8, -0.3), boca="o", susto=1.0 if lt < 1.6 else 0.0)
        if 1.8 <= lt < 4.6:
            st.update(amor=1.0, boca="abierta", pose="pecho", susto=0.0)
        if lt < 5.6:
            px, suelo_p = 720, SUELO + 40
        else:
            k = suave((lt - 5.6)/0.8); px = 720 + (590 - 720)*k; suelo_p = SUELO + 40 + (SEAT - 30 - SUELO - 40)*k
            st.update(mira=(-0.8, 0.0), boca="sonrisa", fase=(lt - 5.6)*6 if k < 0.95 else None)
        if lt > 6.6:
            st.update(mira=(-0.8, 0.0) if (lt % 1.6) >= 0.8 else (0.0, 0.3), rubor=True, boca="sonrisa")
        info = Mu.poke(img, px, suelo_p, HP, st, t)
    d = ImageDraw.Draw(img)
    if 1.0 < lt < 1.6:
        Mu.texto(d, 520, 1000, "CRASH!", 100, (255, 214, 60))
    if lenta or 4.6 <= lt < 5.4:
        for k in range(6):
            f = ((lt - 1.6)*0.25 + k/6) % 1.0
            Mu.corazon(d, 480 + (k - 2.5)*60 + math.sin(t + k)*20, 1100 - f*600, 26*(1 - f) + 8)
        destellos(d, t*0.5, ((80, 1000), (300, 1300)), 12)
    if lt > 6.6:
        Mu.corazon(d, 440, SEAT - 480 - ((lt - 6.6)*60) % 200, 26)
    pink = 0.7*suave((lt - 1.6)/0.5)*(1 - suave((lt - 4.6)/0.8)) + 0.25*suave((lt - 5.0)/1.0)
    img = viñeta(img, (250, 150, 200), pink)
    zoom = 1.04 + 0.14*suave((lt - 1.6)/2.0)*(1 - suave((lt - 4.6)/0.6))
    return img, (470, 1020, zoom)

def p_manos(lt, t, dur=4.2):
    """El cojin, de cerca: las dos manos se acercan... y cae encima una sombra con forma de herradura."""
    img = Image.new("RGB", (W, H), (150, 40, 52)); d = ImageDraw.Draw(img)
    d.rounded_rectangle([-60, 300, W + 60, 1800], radius=120, fill=(170, 50, 62), outline=T, width=10)
    d.line([(W/2, 300), (W/2, 1800)], fill=(120, 30, 40), width=8)
    for x in (W*0.25, W*0.75):
        d.ellipse([x - 16, 1040 - 16, x + 16, 1040 + 16], fill=(120, 30, 40))
    # cuanto se acercan: a tirones, con vergüenza
    k = 0.0
    for t0, t1, k0, k1 in ((0.3, 1.1, 0.0, 0.35), (1.5, 2.2, 0.35, 0.65), (2.6, 3.4, 0.65, 0.9)):
        if lt >= t0:
            k = k0 + (k1 - k0)*suave((lt - t0)/(t1 - t0))
    yb = 1180
    xb = 200 + 210*k                                   # la mano de Bubble (guante blanco)
    d.line([(-40, 560), (xb - 140, 900), (xb - 30, yb)], fill=T, width=34, joint="curve")
    d.ellipse([xb - 85, yb - 70, xb + 85, yb + 70], fill=Mu.BLANCO, outline=T, width=8)
    for j in range(3):
        d.arc([xb - 60 + j*42, yb - 20, xb - 20 + j*42, yb + 70], 20, 160, fill=T, width=5)
    xp = 880 - 210*k                                   # la mano de Poke (verde, con pinchos)
    pts = [(W + 60, 600), (xp + 120, 950), (xp + 30, yb)]
    d.line(pts, fill=T, width=170, joint="curve")
    for p in pts[1:]:
        d.ellipse([p[0] - 85, p[1] - 85, p[0] + 85, p[1] + 85], fill=T)
    d.line(pts, fill=Mu.VERDE, width=150, joint="curve")
    for p in pts[1:]:
        d.ellipse([p[0] - 75, p[1] - 75, p[0] + 75, p[1] + 75], fill=Mu.VERDE)
    for j, (sx, sy, ex, ey) in enumerate(((xp - 40, yb - 50, xp - 80, yb - 80), (xp - 45, yb + 30, xp - 90, yb + 50),
                                          (xp + 60, 1000, xp + 30, 960), (xp + 150, 860, xp + 120, 820), (xp + 170, 960, xp + 210, 930))):
        d.line([(sx, sy), (ex, ey)], fill=T, width=6)
    if lt > 1.1:
        Mu.corazon(d, (xb + xp)/2, 900 - (lt - 1.1)*40, 30 + 10*abs(math.sin(t*5)))
    img = viñeta(img, (250, 150, 200), 0.6)
    if lt > 3.3:                                       # la sombra de Mag entra desde la puerta
        s = suave((lt - 3.3)/0.7)
        capa = Image.new("L", (W, H), 0); c = ImageDraw.Draw(capa)
        cx, top, w = W + 500 - 820*s, 250, 700
        c.pieslice([cx - w/2, top, cx + w/2, top + w], 180, 360, fill=150)
        c.rectangle([cx - w/2, top + w/2, cx + w/2, H], fill=150)
        c.pieslice([cx - w/2 + 230, top + 230, cx + w/2 - 230, top + w - 230], 180, 360, fill=0)
        c.rectangle([cx - w/2 + 230, top + w/2, cx + w/2 - 230, H], fill=0)
        img = Image.composite(Image.new("RGB", (W, H), (20, 10, 24)), img, capa)
    return img, (W/2, H/2, 1.0 + 0.05*lt/dur)

def p_puerta(lt, t):
    """Plano general: la puerta abierta, Mag con su ramo, sonriendo. Ellos dos, en el sofa, de la mano."""
    img = salon(abre=1.0)
    st_m = dict(feliz=1.0 if lt < 1.3 else 0.0, mira=(-0.8, 0.1))
    mag_puerta(img, st_m, t)
    Mu.sofa(img, SOFA_X, SUELO - 130, 520, rasgado=0.9)
    gira = lt > 0.8
    Mu.bubble(img, 330, SEAT - 250, 420, dict(mira=(0.9, 0.0), rubor=True, amor=0.0 if gira else 1.0, feliz=0.0,
                                               boca="o" if gira else "sonrisa", susto=0.6 if lt > 1.3 else 0.0), t)
    Mu.poke(img, 560, SEAT - 30, HP, dict(mira=(0.9, -0.2) if gira else (-0.8, 0.0), amor=0.0 if gira else 1.0, rubor=True,
                                           boca="o" if gira else "sonrisa"), t)
    d = ImageDraw.Draw(img)
    Mu.corazon(d, 445, SEAT - 30, 22)                  # las manos juntas, entre los dos
    return img, (560, 1080, 1.02)

def primer_plano(lt, t, quien, color):
    """El zoom dramatico: un golpe de camara hacia la cara, temblor, rayos y un fogonazo de color."""
    pum = 0.82 + 0.18*suave(lt/0.18) + 0.04*lt
    sh = math.sin(t*90)*14*max(0.0, 1 - lt/0.35)
    if quien == "mag":
        img = Image.new("RGB", (W, H), PASILLO); d = ImageDraw.Draw(img)
        d.rectangle([0, 0, 120, H], fill=(240, 236, 228), outline=T, width=6)
        d.rectangle([W - 120, 0, W, H], fill=(240, 236, 228), outline=T, width=6)
        h = 1450*pum; w = h*0.5; top = 700 - w*0.2 - h*0.1
        m = (W/2 + sh, top + w*0.85)
        Mu.mag(img, W/2 + sh, top + h*0.95, h, dict(fondo=PASILLO, susto=1.0, mira=(-0.7, 0.1), tira=m), t)
        ramo(ImageDraw.Draw(img), m[0], m[1] - 60, 3.6)
        Mu.sudor(ImageDraw.Draw(img), W/2 - w*0.62, top + 40, 60, t)
        cara = (W/2, 700)
    elif quien == "bubble":
        img = Image.new("RGB", (W, H), PARED); d = ImageDraw.Draw(img)
        Mu.ventana(d, 600, 120, 1100, 640, cielo=(250, 214, 190))
        h = 1250*pum
        Mu.bubble(img, W/2 + sh, 860, h, dict(susto=1.0, mira=(0.8, 0.0), boca="o", rubor=True, pose="arriba"), t)
        cara = (W/2, 820)
    else:
        img = Image.new("RGB", (W, H), PARED); d = ImageDraw.Draw(img)
        h = 1500*pum
        info = Mu.poke(img, W/2 + sh, 760 + h*1.04, h, dict(mira=(0.8, -0.1) if (lt % 0.6) < 0.3 else (-0.8, -0.1), boca="o",
                                                              ceja=0.4, rubor=True), t)
        if lt > 0.35:
            Mu.texto(ImageDraw.Draw(img), W/2 + 330, info["top"] + 60, "?", 150, (255, 214, 60))
        cara = info["cara"]
    img = rayos(img, cara[0], cara[1], t, alfa=70)
    img = viñeta(img, color, 0.75)
    img = flash(img, color, 0.55*max(0.0, 1 - lt/0.3))
    return img, (W/2, H/2, 1.0)

def p_flores(lt, t):
    """A camara lenta: el ramo se le cae de las manos y se deshace contra el suelo."""
    img = Image.new("RGB", (W, H), PASILLO); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 110, H], fill=(240, 236, 228), outline=T, width=6)
    d.rectangle([W - 110, 0, W, H], fill=(240, 236, 228), outline=T, width=6)
    suelo = 1680
    Mu.suelo_madera(d, suelo, H, color=(206, 170, 130))
    h = 1050; w = h*0.5; top = suelo - h*0.95
    m = (W/2, top + w*0.85)
    suelta = lt > 0.25
    Mu.mag(img, W/2, suelo, h, dict(fondo=PASILLO, susto=1.0, mira=(-0.6, 0.3), **({} if suelta else dict(tira=m))), t)
    d = ImageDraw.Draw(img)
    k = min(1.0, max(0.0, (lt - 0.25)/1.2))
    y = m[1] - 50 + (suelo - 120 - m[1] + 50)*k*k
    if k < 1.0:
        ramo(d, m[0] + 40*k, y, 2.6)
    else:                                              # en el suelo, desparramado
        ramo(d, m[0] + 60, suelo - 120, 2.6, petalos=0.4)
        rnd = random.Random(3)
        for j in range(9):
            f = min(1.0, (lt - 1.45)/0.6)
            ang = rnd.uniform(math.pi*1.05, math.pi*1.95); r = rnd.uniform(120, 380)*f
            petalo(d, m[0] + 60 + math.cos(ang)*r, suelo - 60 + math.sin(ang)*r*0.4 - 120*math.sin(math.pi*f),
                   26, rnd.uniform(0, 3), random.Random(j).choice(((240, 90, 120), (255, 200, 70), (200, 120, 230))))
    img = viñeta(img, (60, 20, 60), 0.5)
    return img, (W/2, 1300, 1.12)

def p_foto(lt, t, dur=2.6):
    """La foto de la pared, de cerca: Bubble... y Mag."""
    img = Image.new("RGB", (W, H), PARED)
    foto(img, 140, 560, 940, 1220)
    img = viñeta(img, (40, 40, 90), 0.5*suave(lt/1.0))
    return img, (W/2, 900, 1.0 + 0.18*suave(lt/dur))

def corazon_roto(img, x, y, r, k):
    capa = Image.new("RGBA", (int(r*3), int(r*3)), (0, 0, 0, 0)); c = ImageDraw.Draw(capa)
    ox, oy = capa.width/2, capa.height/2
    Mu.corazon(c, ox, oy, r)
    zig = [(ox, oy - r*0.6), (ox - r*0.15, oy - r*0.2), (ox + r*0.15, oy + r*0.1), (ox - r*0.1, oy + r*0.5), (ox, oy + r*1.1)]
    if k <= 0:
        c.line(zig, fill=T, width=max(3, int(r*0.08)))
        img.paste(capa, (int(x - ox), int(y - oy)), capa); return
    for lado in (-1, 1):
        mask = Image.new("L", capa.size, 0); m = ImageDraw.Draw(mask)
        borde = zig + ([(0, capa.height), (0, 0)] if lado < 0 else [(capa.width, capa.height), (capa.width, 0)])
        m.polygon(borde, fill=255)
        mitad = Image.new("RGBA", capa.size, (0, 0, 0, 0)); mitad.paste(capa, (0, 0), mask)
        mitad = mitad.rotate(-lado*25*k, resample=Image.BICUBIC, center=(ox, oy + r))
        img.paste(mitad, (int(x - ox + lado*r*0.5*k), int(y - oy + r*0.3*k)), mitad)

def p_petalo(lt, t):
    """Poke lo entiende. Se le parte el corazon y se le cae un petalo de la flor."""
    img = Image.new("RGB", (W, H), PARED); d = ImageDraw.Draw(img)
    Mu.sofa(img, W/2, 1820, 1300, rasgado=0.9)
    h = 1500
    st = dict(mira=(-0.7, -0.6), boca="o", ceja=0.3)
    if lt > 0.7:
        st = dict(mira=(0.0, 0.4), boca="triste", ceja=0.9, pose="triste")
    info = Mu.poke(img, W/2, 760 + h*1.04, h, st, t)
    d = ImageDraw.Draw(img)
    fx, fy = info["cuerpo"][0] + (info["cuerpo"][2] - info["cuerpo"][0])*0.68, info["top"] + 10
    if lt > 0.9:                                       # el petalo cae balanceandose
        f = min(1.0, (lt - 0.9)/1.9)
        petalo(d, fx + math.sin(f*9)*110*f, fy + f*900, 42, math.sin(f*9)*0.8 + 0.4, (244, 120, 160))
    corazon_roto(img, W/2 - 230, info["top"] - 10, 90, suave((lt - 1.0)/0.4) if lt > 1.0 else 0.0)
    img = viñeta(img, (40, 50, 110), 0.55*suave(lt/0.8))
    return img, (W/2, H/2, 1.0 + 0.03*lt)

def p_lagrima(lt, t, dur=3.2):
    """Bubble, de cerca. Una lagrima."""
    img = Image.new("RGB", (W, H), PARED); d = ImageDraw.Draw(img)
    Mu.ventana(d, 620, 120, 1100, 620, cielo=(170, 180, 210))
    h = 1350; cx, cy = W/2, 900
    info = Mu.bubble(img, cx, cy, h, dict(mira=(-0.2, 0.5), boca="triste", ceja=0.9, rubor=True), t)
    d = ImageDraw.Draw(img)
    rx, ry = h*0.3, h*0.36; s = rx*1.7
    ey = info["cara"][1] - ry*0.12
    for lado in (-1, 1):                               # los ojos aguados
        ex = info["cara"][0] + lado*s*0.2
        d.arc([ex - s*0.12, ey - s*0.02, ex + s*0.12, ey + s*0.17], 20, 160, fill=(170, 220, 250), width=10)
    f = min(1.0, max(0.0, (lt - 0.6)/2.2))
    if lt > 0.4:
        tx = info["cara"][0] + s*0.2 + 30*f; ty = ey + s*0.18 + f*f*ry*1.1; r = 40 + 16*f
        d.polygon([(tx, ty - r*1.9), (tx + r*0.85, ty), (tx - r*0.85, ty)], fill=(170, 220, 250))
        d.ellipse([tx - r, ty - r*0.6, tx + r, ty + r*1.1], fill=(170, 220, 250), outline=T, width=5)
        d.ellipse([tx - r*0.5, ty - r*0.3, tx - r*0.1, ty + r*0.1], fill=(240, 250, 255))
    img = viñeta(img, (40, 50, 110), 0.6)
    return img, (W/2, 960, 1.0 + 0.08*suave(lt/dur))

def p_cotillas(lt, t):
    img, cam = E.p_ojos(lt + 0.6, t)
    return img, cam

def escena_final(t):
    img = salon(abre=1.0)
    mag_puerta(img, dict(susto=1.0, mira=(-0.8, 0.1)), t, flores=False)
    d = ImageDraw.Draw(img)
    ramo(d, PUERTA_X + 30, SUELO - 40, 1.4, petalos=0.4)
    Mu.sofa(img, SOFA_X, SUELO - 130, 520, rasgado=0.9)
    Mu.bubble(img, 330, SEAT - 250, 420, dict(mira=(0.9, 0.0), susto=1.0, boca="o", rubor=True, pose="arriba"), t)
    Mu.poke(img, 560, SEAT - 30, HP, dict(mira=(-0.9, -0.3), boca="triste", ceja=0.9), t)
    return img

def flecha(d, x, y, k):
    """La flecha de 'continuara' de los culebrones."""
    w = 820*k
    d.polygon([(x, y), (x + 90, y - 80), (x + 90, y - 46), (x + w, y - 46), (x + w, y + 46), (x + 90, y + 46), (x + 90, y + 80)],
              fill=(250, 232, 196), outline=T)
    d.line([(x, y), (x + 90, y - 80), (x + 90, y - 46), (x + w, y - 46), (x + w, y + 46), (x + 90, y + 46), (x + 90, y + 80), (x, y)],
           fill=T, width=8)
    if k > 0.95:
        d.text((x + 100 + (w - 100)/2, y + 4), "TO BE CONTINUED…", font=serif(64), fill=(60, 34, 20), anchor="mm")

def p_continuara(lt, t, dur=3.4):
    t0 = 0.4
    img = escena_final(t if lt < t0 else t - lt + t0)
    if lt > t0:                                        # imagen congelada, en sepia
        img = Mu.recorte(img, 560, 1080, 1.06)
        img = sepia(img)
        flecha(ImageDraw.Draw(img), 40, 1660, suave((lt - t0 - 0.3)/0.5))
        return img, (W/2, H/2, 1.0)
    img = viñeta(img, (200, 30, 50), 0.5)
    return img, (560, 1080, 1.06)

def p_fin(lt, t, dur=3.0):
    img = Image.new("RGB", (W, H), (40, 8, 18)); d = ImageDraw.Draw(img)
    a = suave(lt/0.4)*suave((dur - lt)/0.4)
    c = lambda col: tuple(int(40 + (v - 40)*a) for v in col)
    d.text((W/2, 700), "Block 7", font=serif(150), fill=c(ORO), anchor="mm")
    d.text((W/2, 860), "Episode 1 · The Sofa", font=serif(60), fill=c((240, 230, 230)), anchor="mm")
    b = suave((lt - 0.8)/0.5)*suave((dur - lt)/0.4)
    cb = lambda col: tuple(int(40 + (v - 40)*b) for v in col)
    d.text((W/2, 1140), "NEXT EPISODE", font=serif(46), fill=cb((210, 190, 190)), anchor="mm")
    d.text((W/2, 1240), "The Slap", font=serif(110), fill=cb((255, 120, 140)), anchor="mm")
    return img, (W/2, H/2, 1.0)

# ---------------------------------------------------------------- el montaje
def antes(fn):
    """El primer plano de la historia, con el rotulo de flashback encima."""
    def plano(lt, t):
        img, cam = fn(lt, t)
        a = suave(lt/0.3)*suave((1.9 - lt)/0.3)
        if a > 0:
            img = Mu.recorte(img, *cam[:2], max(1.0, cam[2])) if cam[2] > 1.001 else img
            capa = Image.new("RGBA", (W, H), (0, 0, 0, 0)); c = ImageDraw.Draw(capa)
            c.rounded_rectangle([170, 150, W - 170, 290], radius=30, fill=(40, 6, 16, int(210*a)))
            img = img.convert("RGBA"); img.alpha_composite(capa); img = img.convert("RGB")
            ImageDraw.Draw(img).text((W/2, 220), "Earlier that day…", font=serif(66), fill=tuple(int(40 + (v - 40)*a) for v in (250, 250, 250)), anchor="mm")
            return img, (W/2, H/2, 1.0)
        return img, cam
    return plano

def escala(fn, dur, sfx, k):
    """El mismo plano de la version comedia, k veces mas rapido (y sus efectos, con el)."""
    def num(tipo):
        m = re.match(r"([a-z_]+?)(\d+\.\d+)$", tipo)
        return f"{m.group(1)}{float(m.group(2))/k:.2f}" if m else tipo
    return (lambda lt, t: fn(lt*k, t), dur/k, [(t0/k, num(tp)) for t0, tp in sfx])

COMEDIA = [
    escala(E.p_ascensor, 8.5, [(0.8, "bonk"), (2.4, "bonk"), (4.2, "tin"), (5.6, "sirena1.4"), (7.0, "silbido_corto"), (7.4, "bonk"),
                               (7.5, "pito")], 1.55),
    escala(E.p_tira, 6.0, [(0.0, "raspa3.6"), (0.0, "pasos3.6"), (3.8, "boing"), (4.0, "pasos2.0")], 1.3),
    escala(E.p_rellano2, 5.4, [(0.0, "pasos1.8"), (1.8, "bonk"), (2.4, "pasos2.6")], 1.3),
]
COMEDIA[0] = (antes(COMEDIA[0][0]),) + COMEDIA[0][1:]
CABECERA = C.planos("Episode 1 · The Sofa")
GUION = [(lambda lt, t: primer_plano(lt, t, "mag", (200, 30, 50)), 1.3, [(0.0, "dun0"), (0.0, "caen_flores")])] + CABECERA + COMEDIA + [
    (p_amor, 7.6, [(0.0, "pasos1.0"), (1.0, "crash"), (1.1, "susto"), (1.6, "romance6.0"), (1.7, "flechazo"), (5.6, "pasos0.8"),
                   (5.6, "tin")]),
    (p_manos, 4.2, [(0.0, "romance3.4"), (0.3, "latido"), (1.5, "latido"), (2.6, "latido"), (3.0, "latido"), (3.3, "cruje")]),
    (p_puerta, 2.4, [(0.0, "tremolo2.4")]),
    (lambda lt, t: primer_plano(lt, t, "mag", (200, 30, 50)), 1.0, [(0.0, "dun0")]),
    (lambda lt, t: primer_plano(lt, t, "bubble", (130, 40, 170)), 1.0, [(0.0, "dun1")]),
    (lambda lt, t: primer_plano(lt, t, "poke", (40, 120, 90)), 1.2, [(0.0, "dun2")]),
    (p_flores, 2.2, [(0.0, "caen_flores")]),
    (p_foto, 2.6, [(0.0, "violin8.6")]),
    (p_petalo, 2.8, []),
    (p_lagrima, 3.2, []),
    (p_cotillas, 2.0, [(0.1, "susto"), (0.0, "tremolo2.0")]),
    (p_continuara, 3.4, [(0.0, "tremolo0.4"), (0.4, "dun3")]),
    (lambda lt, t: p_fin(lt, t, 2.6), 2.6, [(0.2, "romance2.4")]),
]

def tabla():
    t = 0.0; out = []
    for fn, dur, sfx in GUION:
        out.append((t, t + dur, fn, sfx)); t += dur
    return out, t

TABLA, DUR = tabla()
T_COMEDIA = (TABLA[1 + len(CABECERA)][0], TABLA[1 + len(CABECERA) + len(COMEDIA)][0])
SILENCIOS = [(0.0, T_COMEDIA[0]), (T_COMEDIA[1] - 0.3, DUR)]

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
                fotograma(a + (b - a)*f).resize((270, 480)).save(OUT + f"n1_{i:02d}_{k}.jpg", quality=85)
        print(f"{len(TABLA)} planos, {DUR:.1f} s"); return
    if args and args[0] == "en":
        for s in args[1:]:
            fotograma(float(s)).resize((540, 960)).save(OUT + f"n1_en_{float(s):05.1f}.jpg", quality=88)
        return
    S.audio(OUT + "novela_audio.wav", TABLA, DUR, SILENCIOS, zona_tema=T_COMEDIA)
    if args and args[0] == "audio":
        return
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-i", OUT + "novela_audio.wav", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19",
                          "-preset", "medium", "-c:a", "aac", "-b:a", "192k", "-shortest", OUT + "BLOCK7_ep01_novela.mp4"], stdin=subprocess.PIPE)
    for i in range(int(DUR*FPS)):
        p.stdin.write(fotograma(i/FPS).tobytes())
    p.stdin.close(); p.wait()
    print(f"hecho: {DUR:.1f} s")

if __name__ == "__main__":
    main()
