"""Logo (800x800) y banner (2560x1440) de LO HE SIMULADO.

La idea visual del canal, que vale para cualquier tema (trafico, contagios,
bulos, dinero, decisiones): muchos AGENTES -puntos de luz- que siguen reglas
y estan conectados; en un sitio algo se propaga (rojo) y uno es distinto
(azul). Fondo azul noche de laboratorio, amarillo para el nombre.
"""
import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FUENTE = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FUENTE_B = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
AMARILLO = (255, 206, 46)
BLANCO = (246, 248, 255)
VERDE, NARANJA, ROJO, AZUL = (70, 226, 170), (255, 160, 60), (255, 72, 88), (96, 166, 255)


def degradado_radial(w, h, centro, interior, exterior, radio):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt((xx - centro[0])**2 + (yy - centro[1])**2)/radio
    k = np.clip(d, 0, 1)[..., None]
    img = np.array(interior, np.float32)*(1 - k) + np.array(exterior, np.float32)*k
    return Image.fromarray(img.astype(np.uint8))


def rejilla(img, paso, color, r):
    d = ImageDraw.Draw(img)
    for y in range(paso//2, img.height, paso):
        for x in range(paso//2, img.width, paso):
            d.ellipse([x - r, y - r, x + r, y + r], fill=color)


def color_contagio(k):
    """De verde (normal) a rojo (le ha llegado lo que se propaga)."""
    if k < 0.5:
        a = k*2
        return tuple(int(VERDE[i]*(1 - a) + NARANJA[i]*a) for i in range(3))
    a = (k - 0.5)*2
    return tuple(int(NARANJA[i]*(1 - a) + ROJO[i]*a) for i in range(3))


def red_de_agentes(w, h, pts, focos, zen, r, grosor_linea, enlace, semilla=3):
    """Dibuja la red: lineas entre vecinos cercanos y los agentes encima,
    con halo. 'focos': puntos desde los que se propaga el rojo."""
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    brillo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d, db = ImageDraw.Draw(capa), ImageDraw.Draw(brillo)
    def contagio(p):
        return max([max(0.0, 1 - math.dist(p, f)/rf) for f, rf in focos] + [0.0])
    cols = [AZUL if i == zen else color_contagio(contagio(p)) for i, p in enumerate(pts)]
    pts_np = np.array(pts)
    for i, p in enumerate(pts):
        dist = np.hypot(*(pts_np - p).T)
        for j in np.argsort(dist)[1:4]:
            if j > i and dist[j] < enlace:
                c = tuple((np.array(cols[i]) + np.array(cols[j]))//2)
                d.line([tuple(p), tuple(pts[j])], fill=c + (110,), width=grosor_linea)
    for (x, y), c in zip(pts, cols):
        rr = r*(1.35 if c == AZUL else 1.0)
        db.ellipse([x - rr*2.6, y - rr*2.6, x + rr*2.6, y + rr*2.6], fill=c + (255,))
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=c + (255,))
        d.ellipse([x - rr*0.35 - rr*0.2, y - rr*0.35 - rr*0.2, x - rr*0.35 + rr*0.2, y - rr*0.35 + rr*0.2],
                  fill=(255, 255, 255, 200))
    return capa, brillo


def con_brillo(base, capa, brillo, cuanto):
    halo = brillo.filter(ImageFilter.GaussianBlur(cuanto))
    halo.putalpha(halo.getchannel("A").point(lambda v: int(v*0.55)))
    out = Image.alpha_composite(base.convert("RGBA"), halo)
    return Image.alpha_composite(out, capa)


def logo(salida):
    S = 4
    W = 800*S
    base = degradado_radial(W, W, (W*0.5, W*0.45), (36, 48, 98), (9, 12, 28), W*0.72)
    rejilla(base, 40*S, (26, 34, 68), 2*S)
    # agentes en un anillo irregular alrededor del nombre (dentro del circulo de YouTube)
    rnd = np.random.default_rng(11)
    pts = []
    for k in range(34):
        a = 2*math.pi*k/34 + rnd.uniform(-0.05, 0.05)
        rr = W*(0.335 + rnd.uniform(-0.035, 0.035))
        pts.append((W/2 + rr*math.cos(a), W/2 + rr*math.sin(a)))
    focos = [((W/2 + W*0.3, W/2 - W*0.17), W*0.2)]
    zen = 21
    capa, brillo = red_de_agentes(W, W, pts, focos, zen, 15*S, 4*S, W*0.12)
    img = con_brillo(base, capa, brillo, 12*S)
    d = ImageDraw.Draw(img)
    d.text((W/2, W/2 - 50*S), "LO HE", font=ImageFont.truetype(FUENTE, 76*S), fill=BLANCO, anchor="mm")
    d.text((W/2, W/2 + 36*S), "SIMULADO", font=ImageFont.truetype(FUENTE, 84*S), fill=AMARILLO, anchor="mm")
    img.convert("RGB").resize((800, 800), Image.LANCZOS).save(salida)


def banner(salida):
    S = 2
    W, H = 2560*S, 1440*S
    base = degradado_radial(W, H, (W*0.5, H*0.5), (32, 42, 88), (8, 10, 24), W*0.62)
    rejilla(base, 48*S, (22, 30, 60), 2*S)
    # una nube de agentes por todo el banner, con dos focos que se propagan
    rnd = np.random.default_rng(5)
    pts = []
    while len(pts) < 230:
        p = (rnd.uniform(0, W), rnd.uniform(0, H))
        if all(math.dist(p, q) > 95*S for q in pts):
            pts.append(p)
    focos = [((W*0.16, H*0.32), W*0.13), ((W*0.86, H*0.72), W*0.11)]
    zen = int(np.argmin([math.dist(p, (W*0.8, H*0.22)) for p in pts]))
    capa, brillo = red_de_agentes(W, H, pts, focos, zen, 11*S, 3*S, 190*S)
    img = con_brillo(base, capa, brillo, 9*S)
    # zona segura (1546x423 en el centro): velo oscuro para que se lea
    velo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(velo).rounded_rectangle([W/2 - 860*S, H/2 - 255*S, W/2 + 860*S, H/2 + 255*S], radius=70*S,
                                           fill=(8, 10, 24, 225))
    img = Image.alpha_composite(img, velo.filter(ImageFilter.GaussianBlur(34*S)))
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FUENTE, 150*S)
    t1, t2 = "LO HE ", "SIMULADO"
    w1, w2 = d.textlength(t1, font=f), d.textlength(t2, font=f)
    x0 = W/2 - (w1 + w2)/2
    d.text((x0, H/2 - 62*S), t1, font=f, fill=BLANCO, anchor="lm")
    d.text((x0 + w1, H/2 - 62*S), t2, font=f, fill=AMARILLO, anchor="lm")
    d.text((W/2, H/2 + 60*S), "Preguntas de la vida real, respondidas con simulaciones",
           font=ImageFont.truetype(FUENTE_B, 50*S), fill=(205, 214, 242), anchor="mm")
    temas = ("tráfico", "decisiones", "contagios", "dinero", "bulos")
    fp = ImageFont.truetype(FUENTE_B, 36*S)
    anchos = [d.textlength(tm, font=fp) + 64*S for tm in temas]
    x = W/2 - (sum(anchos) + 24*S*(len(temas) - 1))/2
    for tm, aw in zip(temas, anchos):
        d.rounded_rectangle([x, H/2 + 120*S, x + aw, H/2 + 188*S], radius=34*S, outline=AMARILLO, width=3*S)
        d.text((x + aw/2, H/2 + 154*S), tm, font=fp, fill=(255, 232, 160), anchor="mm")
        x += aw + 24*S
    img.convert("RGB").resize((2560, 1440), Image.LANCZOS).save(salida)


if __name__ == "__main__":
    logo(sys.argv[1])
    banner(sys.argv[2])
