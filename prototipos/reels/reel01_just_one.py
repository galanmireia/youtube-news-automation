"""Reel de memes #1 — JUST ONE (~11 s, vertical, ingles).

Una hucha-cerdito (el muñeco de la cuenta) se da caprichos: "just one coffee",
"just one snack", "just one tiny order"... y con cada uno se le escapa una moneda
por la ranura sin que se entere. Al final la ponen boca abajo: no cae nada, solo
sale una polilla. Tumbada en el suelo: "why am i broke??".

Montado a 120 bpm (un golpe cada 0,5 s) para poder ponerle encima un audio de
moda de Instagram. Salen dos versiones: con musica propia y muda.
  python reel01_just_one.py fotos | en 1.0 6.5 | (sin nada: render)
"""
import math, random, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
DUR = 19.5
BEAT = 0.5
OUT = str(Path(__file__).resolve().parent) + "/salida/"
T = (30, 26, 32)
ROSA, ROSA_OSC, ROSA_CLA = (248, 176, 196), (226, 132, 162), (255, 214, 224)
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def fuente(px):
    return ImageFont.truetype(BOLD, int(px))

def suave(x):
    x = min(1, max(0, x)); return x*x*(3 - 2*x)

def ovalo(cx, cy, rx, ry, semilla, temblor, n=48):
    """Puntos de un ovalo con el 'temblor' del dibujo a mano (cambia 8 veces por segundo)."""
    rnd = random.Random(semilla)
    return [(cx + math.cos(a)*rx + rnd.uniform(-temblor, temblor), cy + math.sin(a)*ry + rnd.uniform(-temblor, temblor))
            for a in [i/n*2*math.pi for i in range(n)]]

def trazo(d, pts, relleno, g):
    d.polygon(pts, fill=relleno)
    d.line(pts + [pts[0]], fill=T, width=g, joint="curve")

# ---------------------------------------------------------------- el muñeco: la hucha-cerdito
def cerdito(img, cx, cy, s, st, t):
    """st: ojos (punto, feliz, x, corazon, grandes), boca (sonrisa, o, plana, triste, abierta), aplasta, rot, coge (cafe, donut)."""
    L = int(s*2.4)
    capa = Image.new("RGBA", (L, L), (0, 0, 0, 0)); d = ImageDraw.Draw(capa)
    o = L/2; g = max(6, int(s*0.03)); tb = s*0.006
    sem = int(t*8)*7 + 1
    rx, ry = s*0.5, s*0.42
    for k, lado in enumerate((-0.3, 0.3, -0.14, 0.14)):          # las patitas (atras y delante)
        x = o + lado*s; y0 = o + ry*0.6; y1 = o + ry + s*0.13 - (k < 2)*s*0.03
        col = ROSA_OSC if k < 2 else ROSA
        d.rounded_rectangle([x - s*0.07, y0, x + s*0.07, y1], radius=int(s*0.05), fill=col, outline=T, width=g)
    for lado in (-1, 1):                                            # las orejas
        x = o + lado*s*0.27
        trazo(d, [(x - s*0.1, o - ry*0.72), (x + lado*s*0.06, o - ry*1.22), (x + s*0.1, o - ry*0.78)], ROSA, g)
    espalda = st.get("espalda")
    if not espalda:
        d.arc([o + rx*0.85, o - s*0.08, o + rx*1.15, o + s*0.12], 250, 160, fill=T, width=g)   # el rabito
    trazo(d, ovalo(o, o, rx, ry, sem, tb), ROSA, g)
    if espalda:                                                     # de espaldas: el culete y el rabito rizado
        d.rounded_rectangle([o - s*0.1, o - ry*0.9, o + s*0.1, o - ry*0.9 + s*0.045], radius=int(s*0.02), fill=T)
        d.line([(o, o + ry*0.5), (o - s*0.012, o + ry*0.75), (o, o + ry*0.97)], fill=T, width=g, joint="curve")   # la raja
        for lado in (-1, 1):
            d.arc([o + lado*s*0.2 - s*0.17, o + ry*0.45, o + lado*s*0.2 + s*0.17, o + ry*0.95], 200 if lado < 0 else 270, 270 if lado < 0 else 340,
                  fill=ROSA_OSC, width=g)
        rz = st.get("rabo", 0.0)
        pts = [(o + math.cos(a + rz)*s*(0.02 + 0.012*a), o + ry*0.15 + math.sin(a + rz)*s*(0.02 + 0.012*a)) for a in np.linspace(0, 4*math.pi, 30)]
        d.line(pts, fill=T, width=g + 8, joint="curve"); d.line(pts, fill=ROSA_OSC, width=g, joint="curve")
        for lado in (-1, 1):
            d.ellipse([o + lado*s*0.3 - s*0.06, o - s*0.02, o + lado*s*0.3 + s*0.06, o + s*0.03], fill=ROSA_OSC)
        sx = st.get("aplasta", 1.0)
        if abs(sx - 1) > 0.005:
            capa = capa.resize((int(L*sx), int(L/sx)), Image.BICUBIC)
        if st.get("rot"):
            capa = capa.rotate(st["rot"], resample=Image.BICUBIC, expand=True)
        img.paste(capa, (int(cx - capa.width/2), int(cy - capa.height/2)), capa)
        return
    d.chord([o - rx*0.8, o - ry*0.1, o + rx*0.8, o + ry*0.95], 20, 160, fill=ROSA_CLA)
    d.rounded_rectangle([o - s*0.1, o - ry*0.9, o + s*0.1, o - ry*0.9 + s*0.045], radius=int(s*0.02), fill=T)   # la ranura
    # la cara
    ojos = st.get("ojos", "punto"); ey = o - s*0.07
    for lado in (-1, 1):
        ex = o + lado*s*0.17
        if ojos == "feliz":
            d.arc([ex - s*0.06, ey - s*0.03, ex + s*0.06, ey + s*0.07], 200, 340, fill=T, width=g)
        elif ojos == "x":
            for sg in (-1, 1):
                d.line([(ex - s*0.045, ey - s*0.045*sg), (ex + s*0.045, ey + s*0.045*sg)], fill=T, width=g)
        elif ojos == "corazon":
            r = s*0.05
            d.ellipse([ex - r, ey - r*0.8, ex, ey + r*0.2], fill=(230, 50, 80)); d.ellipse([ex, ey - r*0.8, ex + r, ey + r*0.2], fill=(230, 50, 80))
            d.polygon([(ex - r*0.97, ey - r*0.15), (ex + r*0.97, ey - r*0.15), (ex, ey + r*1.05)], fill=(230, 50, 80))
        elif ojos == "dolar":
            d.text((ex, ey), "$", font=fuente(s*0.16), fill=(40, 150, 70), anchor="mm", stroke_width=max(3, g//2), stroke_fill=T)
        elif ojos == "grandes":
            d.ellipse([ex - s*0.06, ey - s*0.07, ex + s*0.06, ey + s*0.07], fill=(255, 255, 255), outline=T, width=g)
            d.ellipse([ex - s*0.025, ey - s*0.02, ex + s*0.025, ey + s*0.03], fill=T)
        else:
            d.ellipse([ex - s*0.032, ey - s*0.04, ex + s*0.032, ey + s*0.04], fill=T)
    for lado in (-1, 1):
        d.ellipse([o + lado*s*0.3 - s*0.06, o + s*0.02, o + lado*s*0.3 + s*0.06, o + s*0.07], fill=(244, 120, 150))
    trazo(d, ovalo(o, o + s*0.06, s*0.12, s*0.08, sem + 3, tb, 28), ROSA_OSC, g)    # el morro
    for lado in (-1, 1):
        d.ellipse([o + lado*s*0.045 - s*0.018, o + s*0.045, o + lado*s*0.045 + s*0.018, o + s*0.08], fill=T)
    boca = st.get("boca", "sonrisa"); by = o + s*0.19
    if boca == "sonrisa":
        d.arc([o - s*0.07, by - s*0.05, o + s*0.07, by + s*0.03], 20, 160, fill=T, width=g)
    elif boca == "abierta":
        d.chord([o - s*0.08, by - s*0.03, o + s*0.08, by + s*0.08], 0, 180, fill=(110, 40, 50), outline=T, width=g)
    elif boca == "o":
        d.ellipse([o - s*0.03, by - s*0.03, o + s*0.03, by + s*0.05], fill=(110, 40, 50), outline=T, width=g)
    elif boca == "triste":
        d.arc([o - s*0.06, by, o + s*0.06, by + s*0.07], 200, 340, fill=T, width=g)
    else:
        d.line([(o - s*0.05, by + s*0.01), (o + s*0.05, by + s*0.01)], fill=T, width=g)
    # lo que tiene en las patitas
    coge = st.get("coge")
    if coge:
        hx, hy = o + rx*0.62, o + s*0.12
        if coge == "cafe":
            vaso(d, hx + s*0.08, hy - s*0.1, s*0.32, t)
        elif coge == "cartera":                    # abierta, delante de la barriga
            hx, hy = o + s*0.12, o + s*0.3
            cartera(d, hx, hy, s*0.36)
        elif coge == "donut":
            donut(d, hx + s*0.06, hy - s*0.02, s*0.2, st.get("mordido", 0))
        trazo(d, ovalo(hx, hy, s*0.07, s*0.055, sem + 5, tb, 20), ROSA, g)
    sx = st.get("aplasta", 1.0)
    if abs(sx - 1) > 0.005:
        capa = capa.resize((int(L*sx), int(L/sx)), Image.BICUBIC)
    if st.get("rot"):
        capa = capa.rotate(st["rot"], resample=Image.BICUBIC, expand=True)
    img.paste(capa, (int(cx - capa.width/2), int(cy - capa.height/2 + (L/sx - L)*0.0)), capa)

def vaso(d, x, y, s, t):
    g = max(5, int(s*0.06))
    d.polygon([(x - s*0.3, y - s*0.35), (x + s*0.3, y - s*0.35), (x + s*0.22, y + s*0.45), (x - s*0.22, y + s*0.45)], fill=(250, 248, 240), outline=T)
    d.line([(x - s*0.3, y - s*0.35), (x - s*0.22, y + s*0.45), (x + s*0.22, y + s*0.45), (x + s*0.3, y - s*0.35)], fill=T, width=g)
    d.rectangle([x - s*0.27, y - s*0.05, x + s*0.27, y + s*0.18], fill=(150, 100, 70))
    d.rounded_rectangle([x - s*0.36, y - s*0.5, x + s*0.36, y - s*0.33], radius=int(s*0.06), fill=(120, 80, 60), outline=T, width=g)
    for k in (-1, 1):                                  # el humito
        pts = [(x + k*s*0.12 + math.sin(t*6 + j*0.8 + k)*s*0.06, y - s*0.6 - j*s*0.1) for j in range(5)]
        d.line(pts, fill=(255, 255, 255), width=g, joint="curve")

def donut(d, x, y, r, mordido=0):
    g = max(5, int(r*0.1))
    d.ellipse([x - r, y - r, x + r, y + r], fill=(222, 170, 100), outline=T, width=g)
    d.ellipse([x - r*0.85, y - r*0.85, x + r*0.85, y + r*0.75], fill=(246, 130, 180))
    rnd = random.Random(4)
    for _ in range(9):
        a = rnd.uniform(0, 6.28); rr = rnd.uniform(r*0.45, r*0.75)
        px, py = x + math.cos(a)*rr, y + math.sin(a)*rr
        d.line([(px, py), (px + r*0.1, py + r*0.05)], fill=rnd.choice(((255, 255, 255), (90, 200, 240), (255, 220, 60))), width=g)
    d.ellipse([x - r*0.3, y - r*0.3, x + r*0.3, y + r*0.3], fill=(0, 0, 0, 0), outline=T, width=g)
    if mordido:
        for k in range(int(mordido*3)):                 # los bocados
            bx = x + r*0.85 - k*r*0.25; by = y - r*0.55
            d.ellipse([bx - r*0.22, by - r*0.22, bx + r*0.22, by + r*0.22], fill=(0, 0, 0, 0))

def cartera(d, x, y, s):
    """La cartera abierta, esperando."""
    g = max(5, int(s*0.05))
    d.rounded_rectangle([x - s*0.5, y - s*0.15, x + s*0.5, y + s*0.45], radius=int(s*0.1), fill=(120, 76, 50), outline=T, width=g)
    d.polygon([(x - s*0.5, y - s*0.15), (x + s*0.5, y - s*0.15), (x + s*0.42, y - s*0.55), (x - s*0.42, y - s*0.55)], fill=(150, 98, 64), outline=T)
    d.line([(x - s*0.5, y - s*0.15), (x - s*0.42, y - s*0.55), (x + s*0.42, y - s*0.55), (x + s*0.5, y - s*0.15)], fill=T, width=g)
    d.rectangle([x - s*0.4, y - s*0.13, x + s*0.4, y - s*0.05], fill=(40, 26, 20))
    d.ellipse([x + s*0.3, y + s*0.08, x + s*0.42, y + s*0.2], fill=(232, 196, 90), outline=T, width=3)

def billete(d, x, y, s, ang):
    """Un billete verde volando, dando vueltas (se 'voltea' y se estrecha al girar)."""
    esc = abs(math.cos(ang*0.7))*0.7 + 0.3
    ca, sa = math.cos(ang), math.sin(ang)
    rot = lambda px, py: (x + (px*ca - py*sa)*s*0.5, y + (px*sa + py*ca)*s*0.5*esc)
    pts = [(-1, -0.45), (1, -0.45), (1, 0.45), (-1, 0.45)]
    d.polygon([rot(*q) for q in pts], fill=(120, 196, 120))
    d.line([rot(*q) for q in pts + [pts[0]]], fill=T, width=5)
    d.line([rot(*q) for q in [(-0.8, -0.3), (0.8, -0.3), (0.8, 0.3), (-0.8, 0.3), (-0.8, -0.3)]], fill=(60, 130, 60), width=3)
    cx_, cy_ = rot(0, 0)
    d.ellipse([cx_ - s*0.13, cy_ - s*0.13*esc, cx_ + s*0.13, cy_ + s*0.13*esc], fill=(200, 236, 190), outline=(60, 130, 60), width=3)
    if esc > 0.6:
        d.text((cx_, cy_), "$", font=fuente(s*0.17), fill=(40, 110, 40), anchor="mm")

def cartera_llena(img, x, y, s, n):
    """TU cartera, abierta y abajo: se va llenando con los billetes que llegan (n)."""
    d = ImageDraw.Draw(img)
    for k in range(min(n, 30)):                    # el fajo que asoma, cada vez mas alto
        rnd = random.Random(k)
        bx = x + rnd.uniform(-s*0.32, s*0.32); by = y - s*0.12 - k*s*0.012
        billete(d, bx, by, s*0.38, rnd.uniform(-0.35, 0.35))
    g = max(6, int(s*0.025))
    d.rounded_rectangle([x - s*0.5, y - s*0.12, x + s*0.5, y + s*0.38], radius=int(s*0.08), fill=(120, 76, 50), outline=T, width=g)
    d.line([(x - s*0.45, y - s*0.05), (x + s*0.45, y - s*0.05)], fill=(90, 56, 36), width=g)
    for k in range(-6, 7):                         # el pespunte
        d.line([(x + k*s*0.07, y + s*0.32), (x + k*s*0.07 + s*0.03, y + s*0.32)], fill=(200, 160, 110), width=4)
    d.ellipse([x + s*0.36, y + s*0.08, x + s*0.46, y + s*0.18], fill=(232, 196, 90), outline=T, width=4)

def billetes_volando(lt, n=24, semilla=21):
    """Billetes que vuelan en remolino por toda la pantalla (como si soplara el viento)."""
    rnd = random.Random(semilla); out = []
    for k in range(n):
        x0, y0 = rnd.uniform(0, W + 400), rnd.uniform(0, H + 400)
        vx, vy = rnd.choice((-1, 1))*rnd.uniform(250, 600), rnd.uniform(-450, 350)
        x = (x0 + vx*lt + 90*math.sin(lt*2.5 + k)) % (W + 400) - 200
        y = (y0 + vy*lt + 70*math.cos(lt*3.1 + k*1.3)) % (H + 400) - 200
        out.append((x, y, rnd.uniform(170, 250), lt*rnd.uniform(2.5, 5)*rnd.choice((-1, 1)) + k))
    return out

def moneda(d, x, y, r, giro):
    w = max(0.15, abs(math.cos(giro)))
    d.ellipse([x - r*w, y - r, x + r*w, y + r], fill=(252, 206, 60), outline=T, width=max(4, int(r*0.12)))
    if w > 0.5:
        d.text((x, y + 2), "$", font=fuente(r*1.2*w), fill=(200, 140, 20), anchor="mm")

def caja(d, x, y, s, ang):
    pts = [(-1, -0.7), (1, -0.7), (1, 0.7), (-1, 0.7)]
    ca, sa = math.cos(ang), math.sin(ang)
    rot = lambda px, py: (x + (px*ca - py*sa)*s*0.5, y + (px*sa + py*ca)*s*0.5)
    d.polygon([rot(*p) for p in pts], fill=(200, 150, 96), outline=T)
    d.line([rot(*p) for p in pts + [pts[0]]], fill=T, width=max(4, int(s*0.05)))
    d.line([rot(0, -0.7), rot(0, 0.7)], fill=(240, 220, 160), width=max(6, int(s*0.12)))

def polilla(d, x, y, s, t):
    al = abs(math.sin(t*28))
    for lado in (-1, 1):
        d.polygon([(x, y), (x + lado*s*(0.3 + 0.5*al), y - s*0.45), (x + lado*s*0.75, y + s*0.05)], fill=(170, 160, 150), outline=T)
        d.line([(x, y), (x + lado*s*(0.3 + 0.5*al), y - s*0.45), (x + lado*s*0.75, y + s*0.05), (x, y)], fill=T, width=5)
    d.ellipse([x - s*0.12, y - s*0.15, x + s*0.12, y + s*0.35], fill=(130, 120, 110), outline=T, width=5)
    for lado in (-1, 1):
        d.line([(x, y - s*0.12), (x + lado*s*0.2, y - s*0.4)], fill=T, width=4)

# ---------------------------------------------------------------- texto que sale palabra a palabra, al ritmo
def frase(d, palabras, lt, y, px=110, color=T, borde=(255, 255, 255)):
    """palabras: [(t0, 'word'), ...]; cada palabra 'salta' al aparecer y la linea no se mueve."""
    f = fuente(px)
    anchos = [d.textlength(w_ + " ", font=f) for _, w_ in palabras]
    x = W/2 - (sum(anchos) - d.textlength(" ", font=f))/2
    for (t0, w_), a in zip(palabras, anchos):
        if lt >= t0:
            k = suave((lt - t0)/0.12)
            tam = px*(1.35 - 0.35*k)
            d.text((x + d.textlength(w_, font=f)/2, y), w_, font=fuente(tam), fill=color, anchor="mm",
                   stroke_width=max(4, int(tam*0.09)), stroke_fill=borde)
        x += a

def menea(img, t, cx=None, cy=None):
    """Se da la vuelta y menea el culo al ritmo (un meneo a cada lado por golpe)."""
    f = math.sin(2*math.pi*t/BEAT)
    cerdito(img, (cx or CX) + f*55, (cy or CY), S, dict(espalda=True, rot=f*18, aplasta=bote(t), rabo=t*14), t)

def ajusta(d, palabras, px):
    """El tamaño de letra mas grande (hasta px) con el que la linea cabe en pantalla."""
    while px > 40 and d.textlength(" ".join(w_ for _, w_ in palabras), font=fuente(px)) > W - 120:
        px -= 6
    return px

def Mu_sudor(d, x, y, t):
    for k in range(3):
        f = (t*1.5 + k/3) % 1.0
        xx = x + k*26; yy = y + f*50
        d.polygon([(xx, yy - 16), (xx + 9, yy + 3), (xx - 9, yy + 3)], fill=(150, 200, 240))
        d.ellipse([xx - 9, yy - 4, xx + 9, yy + 13], fill=(150, 200, 240), outline=T, width=2)

def bote(t):
    k = (t % BEAT)/BEAT
    return 1 + 0.07*math.exp(-k*7)

def vuela_moneda(d, t0, lt, origen, lado=1):
    if lt < t0: return
    u = lt - t0
    if u > 1.2: return
    x = origen[0] + lado*u*520; y = origen[1] - 700*u + 900*u*u
    moneda(d, x, y, 46, u*14)

# ---------------------------------------------------------------- las escenas
FONDOS = [(170, 226, 206), (255, 226, 140), (206, 180, 246), (40, 36, 52), (236, 170, 214)]
CX, CY, S = W/2, 1120, 700

def escena(t):
    if t < 2.0:                                   # 1. just one coffee
        lt = t; img = Image.new("RGB", (W, H), FONDOS[0]); d = ImageDraw.Draw(img)
        frase(d, [(0.0, "just"), (0.25, "one")], lt, 360, px=130)
        frase(d, [(0.5, "coffee")], lt, 530, px=190, color=(150, 90, 50))
        if lt < 0.9:
            cerdito(img, CX, CY, S, dict(ojos="feliz", boca="sonrisa", coge="cafe", aplasta=bote(t)), t)
        else:
            menea(img, t)
        vuela_moneda(ImageDraw.Draw(img), 1.0, lt, (CX, CY - S*0.4), 1)
    elif t < 4.0:                                 # 2. just one snack
        lt = t - 2.0; img = Image.new("RGB", (W, H), FONDOS[1]); d = ImageDraw.Draw(img)
        frase(d, [(0.0, "just"), (0.25, "one")], lt, 360, px=130)
        frase(d, [(0.5, "snack")], lt, 530, px=190, color=(230, 90, 150))
        if lt < 0.9:
            cerdito(img, CX, CY, S, dict(ojos="feliz", boca="abierta" if (lt % 0.5) < 0.25 else "sonrisa", coge="donut",
                                         mordido=min(1.0, lt/1.5), aplasta=bote(t)), t)
        else:
            menea(img, t)
        vuela_moneda(ImageDraw.Draw(img), 1.0, lt, (CX, CY - S*0.4), -1)
    elif t < 6.0:                                 # 3. just one tiny order (llueven paquetes)
        lt = t - 4.0; img = Image.new("RGB", (W, H), FONDOS[2]); d = ImageDraw.Draw(img)
        rnd = random.Random(9)
        for k in range(14):
            x0 = rnd.uniform(60, W - 60); v = rnd.uniform(700, 1100); f0 = rnd.uniform(-1.5, 0.5)
            y = (f0 + lt)*v - 150
            if -200 < y < H + 200:
                caja(d, x0, y, rnd.uniform(110, 170), rnd.uniform(-0.5, 0.5) + lt*rnd.uniform(-2, 2))
        frase(d, [(0.0, "just"), (0.25, "one")], lt, 360, px=130)
        frase(d, [(0.5, "tiny"), (0.75, "order")], lt, 530, px=150, color=(120, 70, 200))
        if lt < 0.75:
            cerdito(img, CX, CY, S, dict(ojos="corazon", boca="abierta", aplasta=bote(t)), t)
        else:
            menea(img, t)
        d = ImageDraw.Draw(img)
        for k, t0 in enumerate((1.0, 1.25, 1.5)):
            vuela_moneda(d, t0, lt, (CX, CY - S*0.4), 1 if k % 2 == 0 else -1)
    elif t < 8.0:                                 # 4. my savings: boca abajo... una polilla
        lt = t - 6.0; img = Image.new("RGB", (W, H), FONDOS[3]); d = ImageDraw.Draw(img)
        frase(d, [(0.0, "my"), (0.25, "savings:")], lt, 420, px=150, color=(255, 255, 255), borde=T)
        sacude = math.sin(t*40)*30 if 0.3 < lt < 1.0 else 0
        cerdito(img, CX + sacude, CY - 60, S, dict(ojos="grandes", boca="o", rot=180 + (math.sin(t*40)*12 if 0.3 < lt < 1.0 else 0)), t)
        d = ImageDraw.Draw(img)
        if lt > 1.0:
            u = lt - 1.0
            polilla(d, CX + math.sin(u*9)*140, CY - 60 + S*0.4 - u*700, 170, t)
        if 0.3 < lt < 1.0:
            for lado in (-1, 1):
                d.line([(CX + lado*380, CY - 200), (CX + lado*440, CY - 120)], fill=(255, 255, 255), width=10)
                d.line([(CX + lado*400, CY + 40), (CX + lado*470, CY + 60)], fill=(255, 255, 255), width=10)
    elif t >= 11.0:                               # 6. la cancion: los cerditos se vacian en TU cartera
        lt = t - 11.0; img = Image.new("RGB", (W, H), (150, 226, 150)); d = ImageDraw.Draw(img)
        if lt > 4.0:                              # "come on piggy": vuelan billetes por todas partes
            for item in billetes_volando(lt - 4.0, n=14, semilla=5):
                billete(d, *item)
        s_, y_ = 480, 860; wx, wy = W/2, 1400
        llegados = 0; chorro = []
        for i, x in enumerate((W/2,)):
            t0 = 2.0; t1 = 6.4                    # boca abajo con el primer "send", a sacudirse, y vacia
            vuelta = suave((lt - t0)/0.3) - suave((lt - t1)/0.3)
            sac = math.sin(t*40)*(22 if lt > 4.0 else 12) if t0 + 0.3 < lt < t1 else 0
            vacio = lt > t1 + 0.15
            st = dict(ojos="x" if vacio else ("grandes" if lt < t0 + 0.1 else "punto"), boca="triste" if vacio else "o",
                      rot=180*vuelta + sac, aplasta=1.25 if vacio else 1.0)
            cerdito(img, x + sac, y_ + (40 if vacio else 0), s_, st, t)
            if lt < 2.0:
                Mu_sudor(ImageDraw.Draw(img), x - 250, y_ - 260, t)
            j = 0
            while t0 + 0.3 + j*0.06 < t1:           # el chorro de billetes, de la ranura a la cartera
                u = (lt - (t0 + 0.3 + j*0.06))/0.5
                if 0 <= u < 1:
                    xs, ys = x, y_ + s_*0.4
                    chorro.append((xs + (wx - xs)*u + math.sin(u*9 + j)*(60 + 30*(j % 3)), ys + (wy - 90 - ys)*u*u, 130, u*8 + j))
                elif u >= 1:
                    llegados += 1
                j += 1
        cartera_llena(img, wx, wy, 520, llegados)
        d = ImageDraw.Draw(img)
        for item in chorro:
            billete(d, *item)
        LINEAS = [(0.0, [(0.0, "gimme"), (0.5, "that")], [(1.0, "MONEY")], (40, 140, 60)),
                  (2.0, [(2.0, "send,"), (2.5, "send,"), (3.0, "send")], [(3.5, "it to me")], (40, 140, 60)),
                  (4.0, [(4.0, "come on"), (4.5, "piggy,")], [(5.0, "empty"), (5.5, "out")], (226, 90, 140)),
                  (6.0, [(6.0, "one more"), (6.5, "send")], [(7.0, "won't"), (7.5, "hurt")], (220, 40, 80))]
        for k, (a, arriba, abajo, col) in enumerate(LINEAS):
            if a <= lt < (LINEAS[k + 1][0] if k + 1 < len(LINEAS) else 99):
                frase(d, arriba, lt, 300, px=ajusta(d, arriba, 120))
                frase(d, abajo, lt, 460, px=ajusta(d, abajo, 170), color=col)
    else:                                         # 5. why am i broke??
        lt = t - 8.0; img = Image.new("RGB", (W, H), FONDOS[4]); d = ImageDraw.Draw(img)
        frase(d, [(0.0, "why"), (0.5, "am"), (0.75, "i")], lt, 380, px=140)
        frase(d, [(1.0, "broke??")], lt, 570, px=210, color=(220, 40, 80))
        k = suave(lt/0.25)
        if lt < 2.0:
            cerdito(img, CX, CY + 200*k, S, dict(ojos="x", boca="triste", rot=90*k, aplasta=1.0 + 0.15*k), t)
        else:                                     # arruinada, pero el culo se menea igual
            menea(img, t, cy=CY + 150)
        d = ImageDraw.Draw(img)
        if 1.2 < lt < 2.0:                        # una pelusa rodando: lo unico que le queda
            u = lt - 1.2; x = -100 + u*700
            yy = CY + 560
            d.ellipse([x - 60, yy - 60, x + 60, yy + 60], fill=(210, 200, 190), outline=T, width=6)
            for j in range(10):
                a = j/10*6.28 + u*6
                d.line([(x + math.cos(a)*50, yy + math.sin(a)*50), (x + math.cos(a)*85, yy + math.sin(a)*85)], fill=T, width=5)
    return img

# ---------------------------------------------------------------- el sonido (todo sintetizado, sin derechos)
SR = 44100
def nf(m): return 440*2**((m - 69)/12)

def audio(ruta, con_musica=True):
    n = int(DUR*SR); out = np.zeros(n + SR); rnd = np.random.default_rng(1)
    def pon(t0, x):
        s0 = int(t0*SR); out[s0:s0 + len(x)] += x[:max(0, len(out) - s0)]
    def tono(f, d, v, ca=8, onda="sin"):
        x = np.arange(int(d*SR))/SR; ph = 2*np.pi*f*x
        w = np.sin(ph) if onda == "sin" else np.sign(np.sin(ph))*0.6 + 0.4*np.sin(ph)
        return v*w*np.minimum(1, x/0.004)*np.exp(-x*ca)
    def ruido(d, v, ca):
        x = np.arange(int(d*SR))/SR; return v*rnd.standard_normal(len(x))*np.exp(-x*ca)
    if con_musica:
        acordes = [(48, (60, 64, 67)), (45, (57, 60, 64)), (41, (57, 60, 65)), (43, (55, 59, 62))]
        mel = [72, 76, 79, 76, 77, 76, 74, 72, 69, 72, 74, 72, 71, 74, 79, 74]
        for b in range(int(DUR/BEAT)):
            tb = b*BEAT
            if 6.0 <= tb < 8.0 or 8.0 <= tb < 10.0:
                continue                          # se para la musica: el drama
            x = np.arange(int(0.25*SR))/SR
            pon(tb, 0.5*np.sin(2*np.pi*np.cumsum(50 + 90*np.exp(-x*30))/SR)*np.exp(-x*12))       # bombo
            if b % 2 == 1:
                pon(tb, ruido(0.18, 0.18, 22) + tono(190, 0.18, 0.12, 20))                         # caja
            for h in (0, 0.25):
                hh = rnd.standard_normal(int(0.04*SR)); hh = hh - np.convolve(hh, np.ones(4)/4, mode="same")
                pon(tb + h, 0.06*hh*np.exp(-np.arange(len(hh))/SR*80))
            bajo, notas = acordes[(b//4) % 4]
            pon(tb, tono(nf(bajo), 0.45, 0.16, 5, "cuadrada"))
            pon(tb, tono(nf(mel[b % 16]), 0.3, 0.07, 9, "cuadrada"))
            pon(tb + 0.25, tono(nf(mel[(b*3 + 1) % 16]), 0.2, 0.05, 12, "cuadrada"))
    # efectos
    def ching(t0):
        pon(t0, tono(2637, 0.5, 0.09, 6)); pon(t0, tono(3951, 0.4, 0.05, 7)); pon(t0 + 0.07, tono(3136, 0.5, 0.07, 6))
    for t0 in (1.0, 3.0, 5.0, 5.25, 5.5):
        ching(t0)
    for t0 in (13.0, 13.5, 14.0, 15.0, 16.0, 17.0, 18.0):      # caja registradora: ¡cha-ching!
        pon(t0, ruido(0.06, 0.2, 60)); ching(t0 + 0.06)
    x = np.arange(int(0.5*SR))/SR
    pon(0.4, 0.05*rnd.standard_normal(len(x))*np.sin(np.pi*x/0.5))                             # sorbo
    for t0 in (2.2, 2.7, 3.2, 3.7):
        pon(t0, ruido(0.08, 0.15, 40))                                                          # mordiscos
    for t0 in np.arange(4.1, 6.0, 0.37):
        pon(t0, tono(90, 0.15, 0.2, 18) + ruido(0.15, 0.08, 40))                                 # cajas cayendo
    x = np.arange(int(0.35*SR))/SR
    pon(6.0, 0.15*np.sin(2*np.pi*np.cumsum(900 - 700*x/0.35)/SR)*np.exp(-x*4))                  # el disco que se para
    for t0 in np.arange(6.3, 7.0, 0.06):
        pon(t0, ruido(0.03, 0.12, 90))                                                          # sacudida: nada suena
    x = np.arange(int(1.0*SR))/SR
    pon(7.0, 0.05*rnd.standard_normal(len(x))*(0.5 + 0.5*np.sign(np.sin(2*np.pi*28*x)))*np.exp(-x*1.5))   # aleteo
    for j, m in enumerate((58, 57, 56)):                                                        # trombon triste
        pon(8.0 + j*0.45, tono(nf(m), 0.42, 0.12, 2, "cuadrada"))
    x = np.arange(int(1.2*SR))/SR
    pon(9.35, 0.12*np.sign(np.sin(2*np.pi*np.cumsum(nf(55)*(1 + 0.03*np.sin(2*np.pi*6*x)))/SR))*np.exp(-x*1.2))
    pon(8.25, tono(80, 0.3, 0.3, 10) + ruido(0.3, 0.15, 25))                                    # se cae al suelo
    if con_musica:
        out[:n] = out[:n]*0.75 + voz(n)
    mix = np.tanh(out[:n]*1.6)*0.9
    mix[-int(0.15*SR):] *= np.linspace(1, 0, int(0.15*SR))
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix*32767).astype(np.int16).tobytes())

LETRA = [  # (tiempo, duracion, palabra, tono de espeak 0-99): la voz robotica y aguda que "canta" el texto
    (0.0, 0.25, "just", 70), (0.25, 0.25, "one", 80), (0.5, 0.5, "coffee", 92),
    (2.0, 0.25, "just", 70), (2.25, 0.25, "one", 80), (2.5, 0.5, "snack", 95),
    (4.0, 0.25, "just", 70), (4.25, 0.25, "one", 80), (4.5, 0.25, "tiny", 88), (4.75, 0.5, "order", 96),
    (6.0, 0.25, "my", 40), (6.25, 0.6, "savings", 30),
    (8.0, 0.45, "why", 85), (8.5, 0.25, "am", 75), (8.75, 0.25, "I", 70), (9.0, 0.9, "broke", 50),
    (11.0, 0.5, "gimme", 70), (11.5, 0.5, "that", 75), (12.0, 0.9, "money", 90),
    (13.0, 0.45, "send", 70), (13.5, 0.45, "send", 80), (14.0, 0.45, "send", 90), (14.5, 0.5, "it to me", 85),
    (15.0, 0.5, "come on", 75), (15.5, 0.5, "piggy", 92), (16.0, 0.5, "empty", 80), (16.5, 0.45, "out", 70),
    (17.0, 0.5, "one more", 80), (17.5, 0.45, "send", 90), (18.0, 0.45, "won't", 70), (18.5, 0.9, "hurt", 45),
]

def palabra_wav(texto, tono):
    tmp = OUT + "_w.wav"
    subprocess.run(["espeak-ng", "-v", "en-us+f3", "-p", str(tono), "-s", "170", "-w", tmp, texto], check=True)
    with wave.open(tmp) as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16)/32768
    a = np.abs(x) > 0.02
    if a.any():
        i0, i1 = np.argmax(a), len(a) - np.argmax(a[::-1]); x = x[i0:i1]
    return x, sr

def voz(n):
    """La voz 'rara': espeak agudo, acelerado como una ardilla para que quepa en su golpe, con un eco corto."""
    out = np.zeros(n)
    for t0, dur, texto, tono in LETRA:
        x, sr = palabra_wav(texto, tono)
        largo = len(x)/sr
        r = min(2.2, max(1.25 if t0 < 11 else 1.1, largo/dur))   # siempre un poco acelerada (efecto ardilla); la cancion, menos
        m = int(largo/r*SR)
        y = np.interp(np.linspace(0, len(x) - 1, m), np.arange(len(x)), x)
        if texto == "broke":                         # la ultima, temblorosa
            y = y*(1 + 0.4*np.sin(2*np.pi*7*np.arange(m)/SR))
        y = y/max(1e-6, np.max(np.abs(y)))*0.55
        s0 = int(t0*SR); s1 = min(n, s0 + m); out[s0:s1] += y[:s1 - s0]
    eco = np.zeros(n); d = int(0.11*SR); eco[d:] = out[:-d]*0.3
    return out + eco

def render(nombre, wav=None):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    cmd += ["-i", wav, "-c:a", "aac", "-b:a", "192k", "-shortest"] if wav else ["-an"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium", OUT + nombre]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(DUR*FPS)):
        p.stdin.write(escena(i/FPS).tobytes())
    p.stdin.close(); p.wait()

def main():
    Path(OUT).mkdir(exist_ok=True)
    a = sys.argv[1:]
    if a and a[0] == "fotos":
        tiempos = [11.6, 12.4, 13.2, 14.2, 14.9, 15.6, 16.4, 17.3, 18.0, 18.6, 19.0, 19.4]
        ims = [escena(x).resize((270, 480)) for x in tiempos]
        hoja = Image.new("RGB", (270*6, 480*2))
        for i, im in enumerate(ims):
            hoja.paste(im, ((i % 6)*270, (i//6)*480))
        hoja.save(OUT + "hoja.jpg", quality=85); return
    if a and a[0] == "en":
        for s in a[1:]:
            escena(float(s)).resize((540, 960)).save(OUT + f"en_{float(s):04.1f}.jpg", quality=88)
        return
    audio(OUT + "just_one.wav")
    render("REEL_just_one_musica.mp4", OUT + "just_one.wav")
    render("REEL_just_one_mudo.mp4")
    print("hecho")

if __name__ == "__main__":
    main()
