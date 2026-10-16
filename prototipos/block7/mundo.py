"""BLOCK 7 — el mundo: los vecinos del edificio y sus pisos.

Comedia muda a color. Un cactus que solo quiere abrazos se muda a un edificio
de vecinos con su propio problema. Todo se dibuja con formas simples y borde
negro, como un dibujo animado clasico; la expresion esta en ojos, cejas y boca.
Lienzo vertical 1080x1920 (Shorts / TikTok / Reels).
"""
import math, random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
T = (28, 26, 32)                     # la tinta
FUENTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
BLANCO = (252, 250, 246)

VERDE, VERDE_OSC, VERDE_CLA = (112, 182, 98), (78, 140, 70), (150, 206, 128)
MACETA, MACETA_OSC = (210, 112, 72), (170, 84, 52)
GLOBO, GLOBO_OSC = (110, 186, 236), (78, 150, 206)
HUEVO = (248, 238, 216)
GATO, GATO_OSC = (150, 146, 156), (118, 114, 124)
IMAN, PLATA = (214, 58, 52), (206, 208, 214)
PALOMITA = (252, 248, 232)
LADRILLO = (176, 84, 60)


def fuente(px):
    return ImageFont.truetype(FUENTE, int(px))


def suave(x):
    x = min(1, max(0, x))
    return x*x*(3 - 2*x)


def parpadeo(t, cada=3.6, fase=0.0):
    k = (t + fase) % cada
    return max(0.0, 1 - abs(k - 0.08)/0.08) if k < 0.16 else 0.0


def recorte(im, cx, cy, zoom):
    w, h = W/zoom, H/zoom
    x0 = min(max(0, cx - w/2), W - w); y0 = min(max(0, cy - h/2), H - h)
    return im.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + w, y0 + h))


def luz(img, x, y, rad, fuerza=0.5, color=(255, 240, 210)):
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).ellipse([x - rad, y - rad, x + rad, y + rad], fill=int(255*fuerza))
    m = m.filter(ImageFilter.GaussianBlur(rad*0.45))
    return Image.composite(Image.new("RGB", img.size, color), img, m)


def oscurece(img, f, color=(10, 12, 30)):
    return Image.blend(img, Image.new("RGB", img.size, color), f)


# ---------------------------------------------------------------- la cara
def ojos(d, cx, cy, s, piel, mira=(0, 0), cansancio=0.0, parpadeo=0.0, ceja=0.0, feliz=0.0, susto=0.0,
         enfado=0.0, juntos=1.0):
    """Ojos grandes de dibujo animado. s: el tamaño de la cara.
    ceja: + triste, - sorprendida. susto: ojos enormes y pupila pequeña."""
    g = max(3, int(s*0.03))
    sep = s*0.2*juntos
    for lado in (-1, 1):
        ex = cx + lado*sep
        rx, ry = s*0.13*(1 + 0.25*susto), s*0.16*(1 + 0.3*susto)
        if feliz > 0.5:
            d.arc([ex - rx, cy - ry*0.4, ex + rx, cy + ry*1.2], 200, 340, fill=T, width=g + 1)
        else:
            d.ellipse([ex - rx, cy - ry, ex + rx, cy + ry], fill=BLANCO, outline=T, width=g)
            pr = s*0.055*(1 - 0.4*susto)
            px, py = ex + mira[0]*rx*0.45, cy + mira[1]*ry*0.45
            d.ellipse([px - pr, py - pr*1.1, px + pr, py + pr*1.1], fill=T)
            d.ellipse([px - pr*0.35 + pr*0.3, py - pr*0.7, px + pr*0.05 + pr*0.3, py - pr*0.25], fill=BLANCO)
            f = max(cansancio*0.55, parpadeo)
            if f > 0.03:
                caja = [ex - rx - 1, cy - ry - 1, ex + rx + 1, cy + ry + 1]
                yl = cy - ry + 2*ry*min(1, f)
                d.rectangle([ex - rx - 1, cy - ry - 1, ex + rx + 1, yl], fill=piel)
                d.ellipse(caja, outline=T, width=g)
                d.line([(ex - rx*0.95, yl), (ex + rx*0.95, yl)], fill=T, width=g)
        # cejas
        cy_c = cy - ry*1.35
        if enfado:
            d.line([(ex - lado*rx*1.1, cy_c - ry*0.25), (ex + lado*rx*0.9, cy_c + ry*0.35*enfado)], fill=T, width=g + 2)
        elif susto:
            yy = cy - ry*1.45
            d.arc([ex - rx*0.9, yy - ry*0.25, ex + rx*0.9, yy + ry*0.45], 205, 335, fill=T, width=g + 1)
        elif ceja:
            k = ceja
            d.line([(ex - lado*rx*0.9, cy_c - k*ry*0.35), (ex + lado*rx*1.0, cy_c + k*ry*0.35)], fill=T, width=g + 1)
        elif feliz > 0.5:
            d.arc([ex - rx, cy_c - ry*0.2, ex + rx, cy_c + ry*0.5], 200, 340, fill=T, width=g)


def boca(d, cx, cy, s, tipo="sonrisa", k=1.0):
    g = max(3, int(s*0.03))
    if tipo == "sonrisa":
        d.arc([cx - s*0.16, cy - s*0.12, cx + s*0.16, cy + s*0.08*k], 20, 160, fill=T, width=g)
    elif tipo == "abierta":          # la sonrisa grande, de contento
        d.chord([cx - s*0.17, cy - s*0.08, cx + s*0.17, cy + s*0.16], 0, 180, fill=(70, 30, 36), outline=T, width=g)
        d.chord([cx - s*0.09, cy + s*0.04, cx + s*0.09, cy + s*0.15], 0, 180, fill=(232, 96, 104))
    elif tipo == "o":
        r = s*0.06*k
        d.ellipse([cx - r, cy - r*1.2, cx + r, cy + r*1.2], fill=(70, 30, 36), outline=T, width=g)
    elif tipo == "grito":
        d.ellipse([cx - s*0.11, cy - s*0.1, cx + s*0.11, cy + s*0.16], fill=(70, 30, 36), outline=T, width=g)
        d.ellipse([cx - s*0.06, cy + s*0.04, cx + s*0.06, cy + s*0.14], fill=(232, 96, 104))
    elif tipo == "triste":
        d.arc([cx - s*0.13, cy, cx + s*0.13, cy + s*0.16], 200, 340, fill=T, width=g)
    elif tipo == "dolor":            # dientes apretados
        d.rounded_rectangle([cx - s*0.14, cy - s*0.03, cx + s*0.14, cy + s*0.07], radius=int(s*0.03), fill=BLANCO, outline=T, width=g)
        d.line([(cx - s*0.14, cy + s*0.02), (cx + s*0.14, cy + s*0.02)], fill=T, width=max(2, g - 1))
    else:                            # plana
        d.line([(cx - s*0.09, cy), (cx + s*0.09, cy)], fill=T, width=g)


def piernas(d, cx, cadera, suelo, h, fase=None, sep=0.11, color=T):
    g = max(4, int(h*0.022))
    for lado in (-1, 1):
        x0 = cx + lado*h*sep*0.5
        if fase is not None:
            f = fase + (0 if lado < 0 else math.pi)
            fx = x0 + math.sin(f)*h*0.06; lev = max(0.0, math.cos(f))*h*0.03
        else:
            fx, lev = x0 + lado*h*0.01, 0
        d.line([(x0, cadera), (fx, suelo - h*0.015 - lev)], fill=color, width=g)
        d.ellipse([fx - h*0.05 + lado*h*0.012, suelo - h*0.035 - lev, fx + h*0.05 + lado*h*0.012, suelo + h*0.008 - lev], fill=T)


def brazo_fino(d, p0, p1, p2, h, color=T, mano=BLANCO):
    d.line([p0, p1, p2], fill=color, width=max(4, int(h*0.02)), joint="curve")
    r = h*0.03
    d.ellipse([p2[0] - r, p2[1] - r, p2[0] + r, p2[1] + r], fill=mano, outline=T, width=max(2, int(h*0.008)))


def _codo(p0, ang, largo):
    return (p0[0] + math.cos(math.radians(ang))*largo, p0[1] - math.sin(math.radians(ang))*largo)


# ---------------------------------------------------------------- POKE, el cactus
POSES_POKE = {
    # (angulo hombro-codo, angulo codo-mano) por brazo, en grados (0 = hacia fuera, 90 = arriba)
    "caido":   ((-60, -95), (-60, -95)),
    "abrazo":  ((25, 60), (25, 60)),
    "saluda":  ((-60, -95), (40, 100)),
    "maleta":  ((-75, -95), (-60, -95)),
    "triste":  ((-80, -100), (-80, -100)),
    "arriba":  ((70, 95), (70, 95)),
    "bandeja": ((-45, 5), (-45, 5)),
    "pie":     ((-40, -60), (-55, -100)),
    "pecho":   ((-30, 140), (-30, 140)),
}

def _brazo_cactus(d, hombro, lado, a1, a2, h, rnd_spikes):
    g = max(3, int(h*0.012))
    largo = h*0.15
    ang1 = a1 if lado > 0 else 180 - a1
    ang2 = a2 if lado > 0 else 180 - a2
    codo = _codo(hombro, ang1, largo); mano = _codo(codo, ang2, largo*0.95)
    ancho = int(h*0.075)
    d.line([hombro, codo, mano], fill=T, width=ancho + 2*g, joint="curve")
    for p in (hombro, codo, mano):
        r = ancho/2 + g
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=T)
    d.line([hombro, codo, mano], fill=VERDE, width=ancho, joint="curve")
    for p in (codo, mano):
        r = ancho/2
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=VERDE)
    # los pinchos del brazo
    for (a, b) in ((hombro, codo), (codo, mano)):
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1
        nx, ny = -dy/L, dx/L
        for k in (0.35, 0.75):
            px, py = a[0] + dx*k, a[1] + dy*k
            for s_ in (-1, 1):
                q = (px + s_*nx*ancho*0.5, py + s_*ny*ancho*0.5)
                d.line([q, (q[0] + s_*nx*h*0.03, q[1] + s_*ny*h*0.03)], fill=T, width=max(2, g - 1))
    return mano


def poke(img, cx, suelo, h, st, t):
    """El cactus. h: alto total (de los pies a la flor). st: pose, fase, mira, feliz, susto,
    ceja, boca, plumas (0..1: cubierto de plumas), inclina, salta."""
    d = ImageDraw.Draw(img)
    g = max(3, int(h*0.012))
    fase = st.get("fase")
    bote = abs(math.sin(fase))*h*0.02 if fase is not None else 0
    suelo_p = suelo - st.get("salta", 0.0)
    pie_h = h*0.08
    mac_y1 = suelo_p - pie_h - bote; mac_y0 = mac_y1 - h*0.22
    piernas(d, cx, mac_y1 - 4, suelo_p, h, fase=fase)
    # el cuerpo
    bw, bh = h*0.36, h*0.6
    inc = st.get("inclina", 0.0)*h
    bx = cx + inc*0.5
    by1 = mac_y0 + h*0.04; by0 = by1 - bh
    rnd = random.Random(7)
    # los brazos (de cactus)
    pose = POSES_POKE.get(st.get("pose", "caido"), POSES_POKE["caido"])
    manos = []
    for lado, (a1, a2) in zip((-1, 1), pose):
        if st.get("onda") and lado == 1 and st.get("pose") == "saluda":
            a2 += math.sin(t*12)*25
        if st.get("pose") == "abrazo" and st.get("abraza_k") is not None:
            a1 = a1 + (1 - st["abraza_k"])*-60; a2 = a2 + (1 - st["abraza_k"])*-120
        hombro = (bx + lado*bw*0.36, by0 + bh*0.56)
        manos.append(_brazo_cactus(d, hombro, lado, a1, a2, h, rnd))
    d.rounded_rectangle([bx - bw/2, by0, bx + bw/2, by1], radius=int(bw/2), fill=VERDE, outline=T, width=g)
    d.rounded_rectangle([bx - bw*0.16, by0 + bh*0.06, bx + bw*0.16, by1 - bh*0.02], radius=int(bw*0.16), fill=VERDE_CLA)
    for k in (-0.3, 0.3):
        d.line([(bx + bw*k, by0 + bh*0.12), (bx + bw*k, by1 - bh*0.04)], fill=VERDE_OSC, width=max(2, g - 1))
    # los pinchos del contorno
    rnd = random.Random(7)
    for i in range(22):
        a = i/22*2*math.pi
        ex_, ey_ = math.cos(a), math.sin(a)
        if ey_ > 0.75: continue
        r_x, r_y = bw/2, bh/2
        px = bx + ex_*r_x*(1 if abs(ey_) < 0.55 else 0.95)
        py = (by0 + by1)/2 + ey_*r_y*0.92
        if abs(ey_) > 0.6:
            py = (by0 + bw/2) - (1 - abs(ex_))*0 if ey_ < 0 else py
        d.line([(px, py), (px + ex_*h*0.032, py + ey_*h*0.022)], fill=T, width=max(2, g - 1))
    for i in range(9):                   # pinchitos por delante
        px = bx + rnd.uniform(-bw*0.33, bw*0.33); py = rnd.uniform(by0 + bh*0.45, by1 - bh*0.08)
        d.line([(px - h*0.008, py - h*0.008), (px, py), (px + h*0.008, py - h*0.008)], fill=VERDE_OSC, width=max(2, g - 1))
    # la flor de la cabeza
    fx, fy = bx + bw*0.18, by0 + h*0.01
    for k in range(5):
        a = k/5*2*math.pi + 0.3
        px, py = fx + math.cos(a)*h*0.035, fy + math.sin(a)*h*0.035
        d.ellipse([px - h*0.03, py - h*0.03, px + h*0.03, py + h*0.03], fill=(244, 120, 160), outline=T, width=max(2, g - 1))
    d.ellipse([fx - h*0.022, fy - h*0.022, fx + h*0.022, fy + h*0.022], fill=(255, 214, 90), outline=T, width=max(2, g - 1))
    if st.get("plumas"):           # el abrigo de plumas: encima del cuerpo, debajo de la cara
        plumas(img, bx, (by0 + by1)/2 + bh*0.05, bw*1.3, bh*0.95, st["plumas"], semilla=3)
        d = ImageDraw.Draw(img)
    # la cara
    s = bw*1.05
    ey = by0 + bh*0.27
    ojos(d, bx + st.get("dir", 0)*bw*0.1, ey, s, VERDE, st.get("mira", (0, 0)), st.get("cansancio", 0), st.get("parpadeo", 0),
         st.get("ceja", 0), st.get("feliz", 0), st.get("susto", 0), st.get("enfado", 0))
    boca(d, bx + st.get("dir", 0)*bw*0.1, ey + s*0.27, s, st.get("boca", "sonrisa"), st.get("boca_k", 1.0))
    # la maceta (delante del cuerpo)
    tw, bw2 = h*0.44, h*0.34
    d.polygon([(cx - tw/2, mac_y0 + h*0.05), (cx + tw/2, mac_y0 + h*0.05), (cx + bw2/2, mac_y1), (cx - bw2/2, mac_y1)],
              fill=MACETA, outline=T)
    d.line([(cx - tw/2, mac_y0 + h*0.05), (cx - bw2/2, mac_y1), (cx + bw2/2, mac_y1), (cx + tw/2, mac_y0 + h*0.05)], fill=T, width=g)
    d.rounded_rectangle([cx - tw/2 - h*0.02, mac_y0, cx + tw/2 + h*0.02, mac_y0 + h*0.065], radius=int(h*0.015),
                        fill=MACETA_OSC, outline=T, width=g)
    return {"cara": (bx, ey), "manos": manos, "top": by0, "cuerpo": (bx - bw/2, by0, bx + bw/2, by1), "s": s}


def plumas(img, cx, cy, ancho, alto, k, semilla=1):
    """Cubierto de plumas: un abrigo esponjoso de bolas blancas, como una oveja."""
    d = ImageDraw.Draw(img)
    rnd = random.Random(semilla)
    bolas = [(cx + rnd.uniform(-ancho/2, ancho/2), cy + rnd.uniform(-alto/2, alto/2), rnd.uniform(0.09, 0.14)*ancho*2)
             for _ in range(int(46*k))]
    for x, y, r in bolas:
        d.ellipse([x - r - 4, y - r - 4, x + r + 4, y + r + 4], fill=(160, 158, 170))
    for x, y, r in bolas:
        d.ellipse([x - r, y - r, x + r, y + r], fill=(250, 250, 248))
        d.arc([x - r*0.7, y - r*0.7, x + r*0.5, y + r*0.5], 200, 290, fill=(224, 224, 230), width=3)

def pluma_suelta(d, x, y, r, ang):
    d.ellipse([x - r, y - r*0.42, x + r, y + r*0.42], fill=(250, 250, 248), outline=(180, 178, 188), width=2)
    d.line([(x - r*0.9*math.cos(ang), y - r*0.3*math.sin(ang)), (x + r*0.9*math.cos(ang), y + r*0.3*math.sin(ang))], fill=(200, 198, 206), width=2)


# ---------------------------------------------------------------- BUBBLE, el globo
def bubble(img, cx, cy, h, st, t):
    """El globo. (cx, cy): el centro del globo. Atado a un ladrillo (st['ladrillo']: (x, y) o None)."""
    d = ImageDraw.Draw(img)
    g = max(3, int(h*0.012))
    rx, ry = h*0.3, h*0.36
    tiembla = st.get("tiembla", 0.0)
    cx += math.sin(t*60)*tiembla*h*0.012
    cy += math.sin(t*1.8)*h*0.01
    nudo = (cx, cy + ry)
    lad = st.get("ladrillo")
    if lad:
        d.line([nudo, ((nudo[0] + lad[0])/2 + math.sin(t*2)*10, (nudo[1] + lad[1])/2), lad], fill=(90, 90, 96), width=3, joint="curve")
        lx, ly = lad
        d.rectangle([lx - h*0.15, ly - h*0.1, lx + h*0.15, ly], fill=LADRILLO, outline=T, width=g)
        d.line([(lx - h*0.15, ly - h*0.05), (lx + h*0.15, ly - h*0.05)], fill=(140, 64, 46), width=3)
        d.line([(lx, ly - h*0.1), (lx, ly - h*0.05)], fill=(140, 64, 46), width=3)
    elif st.get("cuerda", True):
        d.line([nudo, (nudo[0] + math.sin(t*3)*20, nudo[1] + h*0.3)], fill=(90, 90, 96), width=3)
    # los brazos (finos)
    pose = st.get("pose", "caido")
    for lado in (-1, 1):
        hb = (cx + lado*rx*0.95, cy + ry*0.15)
        if pose == "arriba" or (pose == "susto"):
            c = (hb[0] + lado*h*0.1, hb[1] - h*0.08); m = (hb[0] + lado*h*0.14, hb[1] - h*0.2)
        elif pose == "cuerda" and lado == 1:
            c = (hb[0] + h*0.06, hb[1] + h*0.08); m = (cx + h*0.03, nudo[1] + h*0.05)
        else:
            c = (hb[0] + lado*h*0.08, hb[1] + h*0.08); m = (hb[0] + lado*h*0.1, hb[1] + h*0.18)
        brazo_fino(d, hb, c, m, h)
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=GLOBO, outline=T, width=g)
    d.chord([cx - rx + g, cy - ry + g, cx + rx - g, cy + ry - g], 20, 160, fill=GLOBO_OSC)
    d.ellipse([cx - rx*0.62, cy - ry*0.72, cx - rx*0.32, cy - ry*0.35], fill=(214, 238, 252))
    d.polygon([(nudo[0] - h*0.035, nudo[1] + h*0.035), (nudo[0] + h*0.035, nudo[1] + h*0.035), (nudo[0], nudo[1] - h*0.01)],
              fill=GLOBO_OSC, outline=T)
    s = rx*1.7
    ojos(d, cx + st.get("dir", 0)*rx*0.15, cy - ry*0.12, s, GLOBO, st.get("mira", (0, 0)), 0, st.get("parpadeo", 0),
         st.get("ceja", 0), st.get("feliz", 0), st.get("susto", 0))
    boca(d, cx + st.get("dir", 0)*rx*0.15, cy + ry*0.28, s, st.get("boca", "sonrisa"))
    if st.get("rubor"):
        for lado in (-1, 1):
            ex = cx + lado*rx*0.55
            d.ellipse([ex - rx*0.18, cy + ry*0.12, ex + rx*0.18, cy + ry*0.26], fill=(244, 130, 160))
    return {"cara": (cx, cy), "nudo": nudo}


# ---------------------------------------------------------------- EL GATO PORTERO
def gato(img, cx, base, h, st, t):
    """Sentado detras del mostrador: solo se le ve de cintura para arriba. base: la linea del mostrador."""
    d = ImageDraw.Draw(img)
    g = max(3, int(h*0.012))
    # la cola, que asoma y se mueve
    cola = [(cx + h*0.25, base), (cx + h*0.42, base - h*0.1 + math.sin(t*2.2)*h*0.04), (cx + h*0.38, base - h*0.32 + math.sin(t*2.2 + 1)*h*0.05)]
    d.line(cola, fill=T, width=int(h*0.06) + 2*g, joint="curve"); d.line(cola, fill=GATO, width=int(h*0.06), joint="curve")
    hy = base - h*0.62; r = h*0.24
    eriz = st.get("erizado", 0.0)
    if eriz > 0:                      # el pelo de punta: una estrella de pinchos detras de todo
        pts = []
        n = 26
        for i in range(n*2):
            a = i/(n*2)*2*math.pi
            rr = (h*0.42 if i % 2 == 0 else h*0.3)*(0.7 + 0.5*eriz)
            pts.append((cx + math.cos(a)*rr*1.05, base - h*0.38 + math.sin(a)*rr*1.15))
        d.polygon(pts, fill=GATO_OSC, outline=T)
        d.line(pts + [pts[0]], fill=T, width=g)
    d.rounded_rectangle([cx - h*0.26, base - h*0.45, cx + h*0.26, base + h*0.1], radius=int(h*0.2), fill=GATO, outline=T, width=g)
    d.ellipse([cx - h*0.13, base - h*0.38, cx + h*0.13, base - h*0.02], fill=(214, 210, 218))
    for lado in (-1, 1):
        d.polygon([(cx + lado*r*0.95, hy - r*0.3), (cx + lado*r*0.75, hy - r*1.25), (cx + lado*r*0.2, hy - r*0.85)], fill=GATO, outline=T)
        d.polygon([(cx + lado*r*0.82, hy - r*0.45), (cx + lado*r*0.72, hy - r*1.0), (cx + lado*r*0.38, hy - r*0.8)], fill=(232, 170, 180))
    d.ellipse([cx - r*1.05, hy - r, cx + r*1.05, hy + r*0.9], fill=GATO, outline=T, width=g)
    # la gorra de portero
    d.chord([cx - r*0.8, hy - r*1.2, cx + r*0.8, hy - r*0.2], 180, 360, fill=(52, 64, 110), outline=T, width=g)
    d.rounded_rectangle([cx - r*0.95, hy - r*0.78, cx + r*0.95, hy - r*0.6], radius=6, fill=(40, 48, 86), outline=T, width=g)
    d.ellipse([cx - r*0.12, hy - r*1.02, cx + r*0.12, hy - r*0.82], fill=(230, 196, 90), outline=T, width=2)
    s = r*1.9
    ojos(d, cx + st.get("dir", 0)*r*0.1, hy - r*0.05, s, GATO, st.get("mira", (0, 0)), st.get("cansancio", 0.75), st.get("parpadeo", 0),
         st.get("ceja", 0.0), st.get("feliz", 0), st.get("susto", 0), juntos=1.1)
    nx, ny = cx, hy + r*0.3
    d.polygon([(nx - r*0.1, ny - r*0.06), (nx + r*0.1, ny - r*0.06), (nx, ny + r*0.06)], fill=(220, 120, 140), outline=T)
    if st.get("sonrie"):
        d.arc([nx - r*0.22, ny, nx, ny + r*0.2], 0, 180, fill=T, width=g); d.arc([nx, ny, nx + r*0.22, ny + r*0.2], 0, 180, fill=T, width=g)
    else:
        d.line([(nx - r*0.16, ny + r*0.16), (nx + r*0.16, ny + r*0.16)], fill=T, width=g)
    for lado in (-1, 1):
        for k in (-1, 1):
            d.line([(nx + lado*r*0.3, ny + r*0.05 + k*r*0.05), (nx + lado*r*0.85, ny + k*r*0.12)], fill=T, width=2)
    return {"cara": (cx, hy), "pata": (cx + h*0.2, base - h*0.1)}


# ---------------------------------------------------------------- DON HUEVO
def huevo_cara(img, cx, cy, h, st, t):
    """Don Huevo asomando: el huevo con gafas, bigote blanco y gorro de dormir."""
    d = ImageDraw.Draw(img)
    g = max(3, int(h*0.012))
    rx, ry = h*0.32, h*0.42
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=HUEVO, outline=T, width=g)
    d.chord([cx - rx + g, cy - ry + g, cx + rx - g, cy + ry - g], 30, 150, fill=(230, 218, 192))
    s = rx*1.8
    ey = cy - ry*0.1
    ojos(d, cx + st.get("dir", 0)*rx*0.15, ey, s, HUEVO, st.get("mira", (0, 0)), st.get("cansancio", 0.2), st.get("parpadeo", 0),
         st.get("ceja", 0.3), 0, st.get("susto", 0))
    for lado in (-1, 1):                         # las gafas
        ex = cx + st.get("dir", 0)*rx*0.15 + lado*s*0.2
        rr = s*0.17*(1 + 0.25*st.get("susto", 0))
        d.ellipse([ex - rr, ey - rr, ex + rr, ey + rr], outline=T, width=g)
    d.line([(cx - s*0.04, ey), (cx + s*0.04, ey)], fill=T, width=g)
    by = cy + ry*0.28                           # el bigote
    for lado in (-1, 1):
        d.chord([cx + lado*rx*0.02 - rx*0.32 + (lado > 0)*rx*0.3, by - ry*0.08, cx + lado*rx*0.02 + (lado > 0)*rx*0.3 + rx*0.02, by + ry*0.12],
                0, 180, fill=(246, 246, 246), outline=T, width=max(2, g - 1))
    if st.get("boca"):
        boca(d, cx, by + ry*0.18, s*0.9, st["boca"])
    if st.get("burbujas"):         # el plastico de burbujas, por si acaso
        d.chord([cx - rx + g, cy - ry*0.1, cx + rx - g, cy + ry - g], 0, 180, fill=(214, 232, 240))
        for i in range(-4, 5):
            for j in range(0, 4):
                bx_, by_ = cx + i*rx*0.2 + (j % 2)*rx*0.1, cy + ry*0.5 + j*ry*0.12
                if ((bx_ - cx)/rx)**2 + ((by_ - cy)/ry)**2 < 0.85:
                    d.ellipse([bx_ - rx*0.07, by_ - rx*0.07, bx_ + rx*0.07, by_ + rx*0.07], outline=(150, 186, 206), width=2)
    sube = st.get("casco_salta", 0.0)
    if st.get("casco"):            # el casco de obra amarillo
        yy = cy - ry*0.7 - sube*ry*0.8
        d.chord([cx - rx*0.85, yy - ry*0.55, cx + rx*0.85, yy + ry*0.35], 180, 360, fill=(250, 200, 50), outline=T, width=g)
        d.rounded_rectangle([cx - rx*1.0, yy - ry*0.1, cx + rx*1.0, yy + ry*0.04], radius=6, fill=(230, 180, 40), outline=T, width=g)
        d.line([(cx, yy - ry*0.5), (cx, yy - ry*0.1)], fill=(220, 170, 30), width=g + 2)
    else:
        d.polygon([(cx - rx*0.7, cy - ry*0.75), (cx + rx*0.75, cy - ry*0.78), (cx + rx*1.2, cy - ry*1.25)], fill=(110, 130, 196), outline=T)
        d.ellipse([cx + rx*1.1, cy - ry*1.36, cx + rx*1.34, cy - ry*1.12], fill=BLANCO, outline=T, width=2)
    return {"cara": (cx, cy)}


# ---------------------------------------------------------------- POP y MAG (en su piso del 3o)
def pop(img, cx, suelo, h, st, t):
    """La palomita: una nube de bolitas blancas con trocitos amarillos. Si explota, salen palomitas."""
    d = ImageDraw.Draw(img)
    g = max(2, int(h*0.014))
    cy = suelo - h*0.55
    piernas(d, cx, cy + h*0.25, suelo, h)
    ex = st.get("explota", 0.0)
    rnd = random.Random(5)
    for i, (dx, dy, r) in enumerate(((-0.16, 0.05, 0.2), (0.16, 0.06, 0.2), (0, -0.14, 0.22), (-0.12, -0.12, 0.16), (0.13, -0.11, 0.16), (0, 0.12, 0.2))):
        k = 1 + ex*0.6
        x, y = cx + dx*h*k, cy + dy*h*k
        d.ellipse([x - r*h, y - r*h, x + r*h, y + r*h], fill=PALOMITA, outline=T, width=g)
        d.ellipse([x - r*h*0.4, y + r*h*0.2, x + r*h*0.1, y + r*h*0.6], fill=(246, 214, 120))
    for lado in (-1, 1):
        hb = (cx + lado*h*0.3, cy + h*0.05)
        if st.get("brazos_arriba"):
            brazo_fino(d, hb, (hb[0] + lado*h*0.1, hb[1] - h*0.12), (hb[0] + lado*h*0.12, hb[1] - h*0.26), h)
        else:
            brazo_fino(d, hb, (hb[0] + lado*h*0.08, hb[1] + h*0.1), (hb[0] + lado*h*0.1, hb[1] + h*0.2), h)
    s = h*0.5
    ojos(d, cx, cy - h*0.06, s, PALOMITA, st.get("mira", (0, 0)), 0, 0, st.get("ceja", 0), st.get("feliz", 0), st.get("susto", 0), st.get("enfado", 0))
    boca(d, cx, cy + h*0.1, s, st.get("boca", "grito"))
    if st.get("pajarita"):          # la pajarita roja de las citas (con su clip metalico)
        px, py = cx + st.get("pajarita_dx", 0.0), cy + h*0.3
        torcida = st.get("torcida", 0.0)
        for lado in (-1, 1):
            d.polygon([(px, py), (px + lado*h*0.13, py - h*0.07 + lado*torcida*h*0.05), (px + lado*h*0.13, py + h*0.07 + lado*torcida*h*0.05)],
                      fill=(210, 40, 50), outline=T)
        d.ellipse([px - h*0.035, py - h*0.035, px + h*0.035, py + h*0.035], fill=(200, 200, 210), outline=T, width=2)
    if ex > 0:
        for i in range(10):
            a = i/10*2*math.pi + 0.3
            r = h*(0.4 + 0.5*ex)
            x, y = cx + math.cos(a)*r, cy + math.sin(a)*r*0.8
            rr = h*0.06
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=PALOMITA, outline=T, width=max(2, g - 1))
        d.text((cx, cy - h*0.75 - ex*h*0.2), "POP!", font=fuente(h*0.28), fill=(255, 210, 60), anchor="mm", stroke_width=max(3, int(h*0.025)), stroke_fill=T)


def mag(img, cx, suelo, h, st, t):
    """El iman: una herradura roja con las puntas plateadas, patas y brazos."""
    d = ImageDraw.Draw(img)
    g = max(2, int(h*0.014))
    top = suelo - h*0.95
    w = h*0.5; grosor = h*0.17
    piernas(d, cx, suelo - h*0.2, suelo, h, sep=0.3)
    caja = [cx - w/2, top, cx + w/2, top + w]
    d.pieslice(caja, 180, 360, fill=IMAN, outline=T, width=g)
    d.rectangle([cx - w/2, top + w/2, cx + w/2, suelo - h*0.2], fill=IMAN, outline=T, width=g)
    d.pieslice([cx - w/2 + grosor, top + grosor, cx + w/2 - grosor, top + w - grosor], 180, 360, fill=st.get("fondo", (236, 226, 210)))
    d.rectangle([cx - w/2 + grosor, top + w/2 - 1, cx + w/2 - grosor, suelo - h*0.2 + 2], fill=st.get("fondo", (236, 226, 210)))
    for lado in (-1, 1):
        x0 = cx + lado*(w/2 - grosor/2)
        d.rectangle([x0 - grosor/2, suelo - h*0.32, x0 + grosor/2, suelo - h*0.2], fill=PLATA, outline=T, width=g)
    # lo que se le ha pegado
    if st.get("tenedor"):
        x0 = cx + w/2 - grosor/2
        d.line([(x0 + h*0.02, suelo - h*0.3), (x0 + h*0.2, suelo - h*0.55)], fill=(200, 200, 206), width=max(4, int(h*0.03)))
        for k in range(3):
            d.line([(x0 + h*0.2 + k*h*0.02, suelo - h*0.55), (x0 + h*0.25 + k*h*0.02, suelo - h*0.66)], fill=(200, 200, 206), width=3)
    for lado in (-1, 1):
        hb = (cx + lado*w/2, top + w*0.45)
        if st.get("brazos_arriba"):
            brazo_fino(d, hb, (hb[0] + lado*h*0.1, hb[1] - h*0.1), (hb[0] + lado*h*0.12, hb[1] - h*0.24), h)
        else:
            brazo_fino(d, hb, (hb[0] + lado*h*0.08, hb[1] + h*0.08), (hb[0] + lado*h*0.1, hb[1] + h*0.18), h)
    s = h*0.42
    ojos(d, cx, top + w*0.2, s, IMAN, st.get("mira", (0, 0)), 0, 0, 0, 0, st.get("susto", 0), st.get("enfado", 0), juntos=0.95)


# ---------------------------------------------------------------- decorados
PAREDES = {"porteria": (150, 196, 186), "p1": (246, 214, 170), "p2": (200, 186, 226), "p3": (246, 196, 186),
           "p4": (176, 214, 236), "atico": (226, 220, 168), "escalera": (230, 222, 206)}

def suelo_madera(d, y0, y1, color=(196, 150, 104)):
    d.rectangle([0, y0, W, y1], fill=color)
    for k in range(0, W, 120):
        d.line([(k, y0), (k - 40, y1)], fill=(170, 126, 86), width=3)
    d.line([(0, y0), (W, y0)], fill=T, width=5)

def puerta(d, x, suelo, numero=None, abre=0.0, color=(132, 96, 70), alto=640, ancho=330):
    x0, y0 = x - ancho/2, suelo - alto
    d.rectangle([x0 - 18, y0 - 18, x0 + ancho + 18, suelo], fill=(240, 236, 228), outline=T, width=5)
    if abre > 0:
        d.rectangle([x0, y0, x0 + ancho, suelo], fill=(40, 34, 40))
    a = ancho*(1 - 0.8*abre)
    d.rectangle([x0, y0, x0 + a, suelo], fill=color, outline=T, width=6)
    if a > ancho*0.5:
        for k in range(2):
            d.rounded_rectangle([x0 + a*0.14, y0 + 60 + k*290, x0 + a*0.86, y0 + 250 + k*290], radius=10, outline=(104, 74, 54), width=5)
        d.ellipse([x0 + a*0.8 - 18, suelo - alto*0.47 - 18, x0 + a*0.8 + 18, suelo - alto*0.47 + 18], fill=(232, 196, 90), outline=T, width=4)
    if numero:
        d.rounded_rectangle([x - 50, y0 - 120, x + 50, y0 - 40], radius=10, fill=(250, 246, 236), outline=T, width=4)
        d.text((x, y0 - 80), numero, font=fuente(52), fill=T, anchor="mm")

def ventana(d, x0, y0, x1, y1, noche=False, cielo=(186, 222, 246)):
    d.rectangle([x0, y0, x1, y1], fill=(36, 40, 70) if noche else cielo, outline=T, width=6)
    if not noche:
        d.ellipse([x0 + (x1 - x0)*0.15, y0 + (y1 - y0)*0.2, x0 + (x1 - x0)*0.45, y0 + (y1 - y0)*0.36], fill=(250, 250, 250))
    else:
        d.ellipse([x1 - (x1 - x0)*0.35, y0 + (y1 - y0)*0.15, x1 - (x1 - x0)*0.15, y0 + (y1 - y0)*0.35], fill=(250, 240, 200))
    d.line([((x0 + x1)/2, y0), ((x0 + x1)/2, y1)], fill=T, width=5)
    d.line([(x0, (y0 + y1)/2), (x1, (y0 + y1)/2)], fill=T, width=5)
    d.rectangle([x0 - 14, y1, x1 + 14, y1 + 18], fill=(240, 236, 228), outline=T, width=4)

def cuadro(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=(250, 246, 236), outline=T, width=5)
    d.polygon([(x0 + 15, y1 - 15), ((x0 + x1)/2, y0 + 30), (x1 - 15, y1 - 15)], fill=(150, 196, 140))
    d.ellipse([x1 - 60, y0 + 20, x1 - 25, y0 + 55], fill=(250, 210, 90))

def planta(d, x, suelo, s=1.0):
    d.polygon([(x - 50*s, suelo - 110*s), (x + 50*s, suelo - 110*s), (x + 38*s, suelo), (x - 38*s, suelo)], fill=(220, 220, 214), outline=T)
    for a in (-60, -25, 0, 25, 60):
        r = math.radians(90 + a)
        d.ellipse([x + math.cos(r)*70*s - 30*s, suelo - 110*s - math.sin(r)*90*s - 20*s, x + math.cos(r)*70*s + 30*s,
                   suelo - 110*s - math.sin(r)*90*s + 20*s], fill=(96, 160, 90), outline=T, width=3)

def texto(d, x, y, s, px, color=BLANCO, borde=T, ancla="mm"):
    d.text((x, y), s, font=fuente(px), fill=color, anchor=ancla, stroke_width=max(3, int(px*0.1)), stroke_fill=borde)

def bocadillo_simbolo(d, x, y, simbolo, px=90, color=(255, 220, 70)):
    """Los signos de los dibujos: !, ?, ♥, ..."""
    texto(d, x, y, simbolo, px, color)

def lineas_velocidad(d, x, y0, y1, n=6, color=(255, 255, 255)):
    for k in range(n):
        xx = x + (k - n/2)*28
        d.line([(xx, y0 + k*15), (xx, y1 - k*10)], fill=color, width=6)


# ---------------------------------------------------------------- CUBI, el cubito de hielo
def cubi(img, cx, suelo, h, st, t):
    d = ImageDraw.Draw(img)
    g = max(2, int(h*0.014))
    piernas(d, cx, suelo - h*0.18, suelo, h, fase=st.get("fase"))
    w = h*0.62; y1 = suelo - h*0.16; y0 = y1 - w
    d.rounded_rectangle([cx - w/2, y0, cx + w/2, y1], radius=int(w*0.16), fill=(196, 230, 246), outline=T, width=g)
    d.polygon([(cx - w*0.38, y0 + w*0.1), (cx - w*0.1, y0 + w*0.1), (cx - w*0.38, y0 + w*0.4)], fill=(236, 248, 254))
    for lado in (-1, 1):
        hb = (cx + lado*w/2, y0 + w*0.55)
        brazo_fino(d, hb, (hb[0] + lado*h*0.08, hb[1] + h*0.08), (hb[0] + lado*h*0.1, hb[1] + h*0.18), h)
    s = w*1.0
    ojos(d, cx, y0 + w*0.42, s, (196, 230, 246), st.get("mira", (0, 0)), 0, 0, 0, st.get("feliz", 0))
    boca(d, cx, y0 + w*0.68, s, st.get("boca", "abierta"))
    if st.get("gotas"):
        for k in range(3):
            yy = y1 + ((t*1.5 + k/3) % 1.0)*h*0.2
            d.ellipse([cx - w*0.3 + k*w*0.3 - 6, yy - 9, cx - w*0.3 + k*w*0.3 + 6, yy + 9], fill=(150, 200, 236))


# ---------------------------------------------------------------- recursos de comedia
def grawlix(d, x, y, s, t, texto="#@%!", color=(230, 40, 40), semilla=0):
    """El bocadillo de los insultos de tebeo: una explosion blanca con #@%!."""
    rnd = random.Random(semilla + int(t*8))
    pts = []
    n = 14
    for i in range(n*2):
        a = i/(n*2)*2*math.pi
        r = s*(1.0 if i % 2 == 0 else 0.68)*rnd.uniform(0.92, 1.08)
        pts.append((x + math.cos(a)*r*1.25, y + math.sin(a)*r*0.85))
    d.polygon(pts, fill=(252, 252, 250), outline=T)
    d.line(pts + [pts[0]], fill=T, width=max(3, int(s*0.05)))
    d.text((x, y), texto, font=fuente(s*0.62), fill=color, anchor="mm")


def rayo(d, p0, p1, t, color=(255, 214, 40)):
    """Rayos entre los ojos de dos que se odian."""
    rnd = random.Random(int(t*20))
    n = 7
    pts = [p0]
    for k in range(1, n):
        f = k/n
        pts.append((p0[0] + (p1[0] - p0[0])*f + rnd.uniform(-14, 14), p0[1] + (p1[1] - p0[1])*f + rnd.uniform(-22, 22)))
    pts.append(p1)
    d.line(pts, fill=T, width=12)
    d.line(pts, fill=color, width=6)


def vena(d, x, y, s, t):
    """La vena del enfado: cuatro arcos rojos que laten."""
    k = 1 + 0.15*math.sin(t*18)
    r = s*0.18*k
    for dx, dy, a0 in ((-1, -1, 0), (1, -1, 90), (1, 1, 180), (-1, 1, 270)):
        cx, cy = x + dx*r*0.95, y + dy*r*0.95
        d.arc([cx - r, cy - r, cx + r, cy + r], a0 + 90, a0 + 180, fill=(220, 40, 40), width=max(4, int(s*0.06)))


def alarma(d, x, y, t, encendida=True):
    on = encendida and (t*4) % 1.0 < 0.5
    d.chord([x - 50, y - 60, x + 50, y + 40], 180, 360, fill=(240, 60, 50) if on else (150, 40, 40), outline=T, width=5)
    d.rectangle([x - 60, y - 10, x + 60, y + 10], fill=(80, 80, 90), outline=T, width=4)
    if on:
        for a in (-150, -120, -90, -60, -30):
            r = math.radians(a)
            d.line([(x + math.cos(r)*70, y - 10 + math.sin(r)*70), (x + math.cos(r)*120, y - 10 + math.sin(r)*120)], fill=(255, 80, 60), width=8)


def palomita_suelta(d, x, y, r):
    for dx, dy, k in ((-0.4, 0.1, 0.62), (0.4, 0.1, 0.62), (0, -0.35, 0.66), (0, 0.3, 0.6)):
        d.ellipse([x + dx*r - k*r, y + dy*r - k*r, x + dx*r + k*r, y + dy*r + k*r], fill=PALOMITA, outline=T, width=2)
    d.ellipse([x - r*0.25, y + r*0.05, x + r*0.15, y + r*0.4], fill=(246, 214, 120))


def palomitas_pegadas(img, info, k, semilla=4):
    """Palomitas clavadas en los pinchos del cactus."""
    if k <= 0: return
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = info["cuerpo"]
    rnd = random.Random(semilla)
    for i in range(int(18*k)):
        lado = rnd.choice((-1, 1))
        x = (x0 if lado < 0 else x1) + lado*rnd.uniform(-10, 18)
        y = rnd.uniform(y0 + (y1 - y0)*0.15, y1 - 10)
        if rnd.random() < 0.35:
            x = rnd.uniform(x0 + 20, x1 - 20); y = rnd.uniform(y0 + (y1 - y0)*0.55, y1 - 20)
        palomita_suelta(d, x, y, rnd.uniform(14, 20))



def humo_enfado(d, x, y, s, t):
    """Humo saliendo de la cabeza, en bocanadas que suben."""
    for i in range(3):
        k = (t*1.6 + i/3) % 1.0
        r = s*(0.25 + 0.5*k)
        cx, cy = x + math.sin(k*5 + i)*s*0.3, y - k*s*2.2
        d.ellipse([cx - r, cy - r*0.8, cx + r, cy + r*0.8], fill=(214, 214, 220), outline=(150, 150, 160), width=3)
