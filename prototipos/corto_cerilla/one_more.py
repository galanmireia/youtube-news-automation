"""ONE MORE — el primer corto del canal (unos 3 minutos, sin voz).

Lunes a viernes de una cerilla: "solo un vídeo más" cada noche, la llama
(su energía) cada día más pequeña, hasta que una noche ve su reflejo en la
pantalla apagada y deja el móvil en la cocina. El jueves despierta con la
llama encendida; el viernes, cena con sus amigos.

La llama es la energía: dormir la recarga; trasnochar la deja en nada.
  lunes noche 1.0 -> 3:47 0.2 -> martes día 0.12 (humo)
  martes noche 0.6 -> miércoles día 0.08 -> miércoles noche 0.3
  jueves (ha dormido) 0.7 -> viernes 1.0
"""
import math, random, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corto as C
from corto import T, suave, parpadeo, fuente

OUT = str(Path(__file__).resolve().parent) + "/salida/"
FPS = 25
CW, CH = C.CW, C.CH          # 1600x900 de trabajo
VW, VH = 1920, 1080          # vídeo final
PIEL = (240, 236, 226)

# ---------------------------------------------------------------- fondos
_BG = {}
def bg(nombre, oscuro=0.0, claro=0.0, espejo=False):
    k = (nombre, oscuro, claro, espejo)
    if k not in _BG:
        _BG[k] = C.gris(nombre, oscuro=oscuro, claro=claro, espejo=espejo)
    return _BG[k].copy()

def oscurece(img, f, color=(0, 0, 0)):
    return Image.blend(img, Image.new("RGB", img.size, color), f)

# ---------------------------------------------------------------- extras (en gris: el color es solo de la cerilla)
def extra(img, cx, suelo, h, tipo, st, t):
    d = ImageDraw.Draw(img)
    fase = st.get("fase")
    cad = st.get("cadera", suelo - h*0.2)
    if fase is not None:
        cad -= abs(math.sin(fase))*h*0.014
    if not st.get("sin_piernas"):
        C.piernas(d, cx, cad - h*0.02, suelo, h, fase=fase)
    g = max(3, int(h*0.01))
    if tipo == "capsula":
        piel = (226, 226, 222); a = h*0.26; top = cad - h*0.75
        d.rounded_rectangle([cx - a/2, top, cx + a/2, cad], radius=int(a/2), fill=piel, outline=T, width=g)
        ex, ey, es = cx, top + h*0.19, h*0.24
        hombros = ((cx - a*0.48, top + h*0.36), (cx + a*0.48, top + h*0.36))
    else:
        r = h*(0.16 if tipo == "gorro" else 0.18); cy = cad - h*0.52
        piel = (240, 240, 240) if tipo == "gorro" else (196, 196, 200)
        d.rounded_rectangle([cx - h*0.11, cy + r*0.8, cx + h*0.11, cad], radius=int(h*0.05), fill=(70, 70, 74), outline=T, width=g)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=piel, outline=T, width=g)
        if tipo == "gorro":
            gc = (130, 130, 134)
            d.chord([cx - r*1.02, cy - r*1.15, cx + r*1.02, cy + r*0.5], 180, 360, fill=gc, outline=T, width=g)
            d.rectangle([cx - r*1.05, cy - r*0.42, cx + r*1.05, cy - r*0.18], fill=gc, outline=T, width=g)
            d.ellipse([cx - r*0.25, cy - r*1.45, cx + r*0.25, cy - r*0.98], fill=gc, outline=T, width=g)
        ex, ey, es = cx, cy + r*0.2, r*1.3
        hombros = ((cx - h*0.11, cy + r*1.05), (cx + h*0.11, cy + r*1.05))
    pose = st.get("pose", "caido")
    C.ojos(d, ex, ey, es, piel, st.get("cansancio", 0), st.get("parpadeo", 0),
           st.get("mira", (0, 0.9) if pose == "movil" else (0, 0)), st.get("ceja", 0), st.get("dir", 0), st.get("feliz", 0))
    if tipo == "gafas":
        for lado in (-1, 1):
            gx = ex + st.get("dir", 0)*es*0.16 + lado*es*0.32
            d.ellipse([gx - es*0.24, ey - es*0.26, gx + es*0.24, ey + es*0.24], outline=T, width=g + 2)
    obj = st.get("objeto")
    if pose == "movil" and obj is None:
        obj = (cx, hombros[0][1] + h*0.07)
    mano = C.brazos(d, hombros, h, pose, obj, piel=piel, fase=fase)
    if pose == "movil":
        C.movil(d, mano[0], mano[1], h)
    if pose == "brindis":
        vaso(d, obj[0], obj[1], h)
    return mano

def vaso(d, x, y, h):
    w, hh = h*0.035, h*0.075
    d.polygon([(x - w, y - hh), (x + w, y - hh), (x + w*0.75, y + hh*0.25), (x - w*0.75, y + hh*0.25)], fill=(250, 250, 250), outline=T)
    d.line([(x - w*0.9, y - hh*0.55), (x + w*0.9, y - hh*0.55)], fill=(200, 200, 200), width=3)

def chispas(d, x, y, k, s, semilla=4):
    """Unas chispas naranjas que saltan desde (x, y); k = 0..1 del salto."""
    if not (0 < k < 1): return
    rnd = random.Random(semilla)
    for _ in range(9):
        a = rnd.uniform(-math.pi*0.95, -math.pi*0.05); v = rnd.uniform(0.6, 1.0)
        px, py = x + math.cos(a)*s*v*k, y + math.sin(a)*s*v*k + s*0.4*k*k
        rr = max(2, s*0.045*(1 - k))
        d.ellipse([px - rr, py - rr, px + rr, py + rr], fill=C.LLAMA if rnd.random() < 0.6 else C.LLAMA2)

# ---------------------------------------------------------------- el móvil en grande
def movil_grande(img, cx, cy, alto, modo, lt, datos=None, pulgar=None, fondo_pantalla=None, contacto="Cloud"):
    d = ImageDraw.Draw(img)
    w = alto*0.5
    x0, y0, x1, y1 = cx - w/2, cy - alto/2, cx + w/2, cy + alto/2
    # brazos y manos que lo sujetan
    for lado, (mx, my) in ((-1, (x0 + 6, cy + alto*0.18)), (1, (x1 - 6, cy + alto*0.12))):
        if lado == 1 and pulgar: continue
        d.line([(mx, my), (mx + lado*alto*0.2, CH + 40)], fill=T, width=int(alto*0.03))
    d.rounded_rectangle([x0 - 4, y0 - 4, x1 + 4, y1 + 4], radius=int(alto*0.075), outline=(90, 90, 96), width=3)
    d.rounded_rectangle([x0, y0, x1, y1], radius=int(alto*0.07), fill=(16, 16, 20), outline=T, width=5)
    sx0, sy0, sx1, sy1 = x0 + alto*0.025, y0 + alto*0.03, x1 - alto*0.025, y1 - alto*0.03
    pant = Image.new("RGB", (int(sx1 - sx0), int(sy1 - sy0)), (26, 26, 30))
    p = ImageDraw.Draw(pant); W, H = pant.size
    if modo == "feed":
        desp = lt*30 + sum(H*0.42*suave((lt - ts)/0.35) for ts in (datos or []))
        alto_c = H*0.42
        i0 = int(desp//alto_c) - 1
        for i in range(i0, i0 + 4):
            y = i*alto_c - desp + H*0.04
            tono = 60 + (i*37) % 70
            p.rounded_rectangle([W*0.06, y, W*0.94, y + alto_c*0.66], radius=14, fill=(tono, tono, tono + 4))
            tx, ty = W/2, y + alto_c*0.33
            p.polygon([(tx - 22, ty - 28), (tx - 22, ty + 28), (tx + 30, ty)], fill=(235, 235, 235))
            p.rounded_rectangle([W*0.06, y + alto_c*0.72, W*0.8, y + alto_c*0.78], radius=6, fill=(90, 90, 96))
            p.rounded_rectangle([W*0.06, y + alto_c*0.83, W*0.55, y + alto_c*0.88], radius=6, fill=(70, 70, 76))
    elif modo == "alarma":
        hora, pospuesta = datos
        pulso = 0.5 + 0.5*math.sin(lt*12) if not pospuesta else 0
        pant = Image.new("RGB", pant.size, tuple(int(26 + 40*pulso) for _ in range(3))); p = ImageDraw.Draw(pant)
        p.text((W/2, H*0.28), hora, font=fuente(W*0.3), fill=(250, 250, 250), anchor="mm")
        p.text((W/2, H*0.42), "Alarm" if not pospuesta else "Snoozed · 20 min", font=fuente(W*0.075), fill=(170, 170, 176), anchor="mm")
        if not pospuesta:
            p.rounded_rectangle([W*0.12, H*0.62, W*0.88, H*0.76], radius=40, fill=(235, 235, 235))
            p.text((W/2, H*0.69), "SNOOZE", font=fuente(W*0.1), fill=(20, 20, 24), anchor="mm")
            p.text((W/2, H*0.86), "stop", font=fuente(W*0.07), fill=(140, 140, 146), anchor="mm")
    elif modo == "chat":
        pant = Image.new("RGB", pant.size, (238, 238, 236)); p = ImageDraw.Draw(pant)
        p.rectangle([0, 0, W, H*0.12], fill=(214, 214, 212))
        p.ellipse([W*0.06, H*0.03, W*0.06 + H*0.065, H*0.095], fill=(190, 192, 198), outline=T, width=2)
        p.text((W*0.06 + H*0.085, H*0.062), contacto, font=fuente(W*0.075), fill=(20, 20, 24), anchor="lm")
        y = H*0.17; f = fuente(W*0.068)
        for lado, texto, t0, escribe in datos:
            if lt < t0: continue
            if lado == 0:     # una linea de estado pequeña a la derecha: "Seen"
                p.text((W*0.93, y - H*0.012), texto, font=fuente(W*0.05), fill=(130, 130, 136), anchor="rm")
                y += H*0.04
                continue
            tw = p.textlength(texto, font=f) + W*0.1
            bx0 = W*0.05 if lado < 0 else W*0.95 - tw
            col, tc = ((205, 205, 203), (20, 20, 24)) if lado < 0 else ((52, 52, 58), (250, 250, 250))
            p.rounded_rectangle([bx0, y, bx0 + tw, y + H*0.075], radius=22, fill=col)
            p.text((bx0 + W*0.05, y + H*0.0375), texto, font=f, fill=tc, anchor="lm")
            y += H*0.1
        # la caja de escribir abajo, con lo que está tecleando
        p.rectangle([0, H*0.86, W, H], fill=(224, 224, 222))
        tecleo = ""
        for lado, texto, t0, escribe in datos:
            if escribe and t0 - escribe <= lt < t0:
                n = int(len(texto)*(lt - (t0 - escribe))/escribe) + 1
                tecleo = texto[:n]
        p.rounded_rectangle([W*0.05, H*0.885, W*0.95, H*0.965], radius=24, fill=(250, 250, 250), outline=(180, 180, 180))
        p.text((W*0.09, H*0.925), tecleo or "Message", font=fuente(W*0.06), fill=(30, 30, 34) if tecleo else (160, 160, 164), anchor="lm")
    elif modo == "negro":
        pant = Image.new("RGB", pant.size, (10, 10, 12)); p = ImageDraw.Draw(pant)
        if fondo_pantalla: fondo_pantalla(pant)
        p.line([(W*0.15, H*0.08), (W*0.45, H*0.02)], fill=(40, 40, 44), width=6)     # un brillo del cristal
    m = Image.new("L", pant.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, W - 1, H - 1], radius=int(alto*0.05), fill=255)
    img.paste(pant, (int(sx0), int(sy0)), m)
    d = ImageDraw.Draw(img)
    for mx, my, lado in ((x0 + 6, cy + alto*0.18, -1), (x1 - 6, cy + alto*0.12, 1)):
        r = alto*0.06
        if lado == 1 and pulgar:       # la mano derecha sube a tocar la pantalla
            mx, my = pulgar
            d.line([(mx, my), (mx + alto*0.2, CH + 40)], fill=T, width=int(alto*0.03))
        d.ellipse([mx - r, my - r, mx + r, my + r], fill=PIEL, outline=T, width=4)
    return (sx0, sy0, sx1, sy1)

# ---------------------------------------------------------------- tarjetas
def tarjeta(lt, dur, texto, px=74, sub=None):
    img = Image.new("RGB", (CW, CH), (8, 8, 10)); d = ImageDraw.Draw(img)
    a = suave(lt/0.5)*suave((dur - lt)/0.4)
    c = int(8 + 240*a)
    d.text((CW/2, CH/2), texto, font=fuente(px), fill=(c, c, c), anchor="mm")
    if sub:
        c2 = int(8 + 140*a)
        d.text((CW/2, CH/2 + px), sub, font=fuente(px*0.4), fill=(c2, c2, c2), anchor="mm")
    return img, (CW/2, CH/2, 1.0)

def negro(lt, t=0):
    return Image.new("RGB", (CW, CH), (0, 0, 0)), (CW/2, CH/2, 1.0)

# ---------------------------------------------------------------- escenas de la cama
def cama_ancha(lt, t, st, hora=None, clave="noche", texto=None, sacude=False, luz=0.45, apaga=None):
    img = C.cuarto(clave)
    if clave == "manana":
        img = C.luz(img, 800, 150, 500, 0.3, (255, 255, 250))
    k, ox, oy = 0.95, 60, 150
    if st.get("pose") == "movil" and luz:
        img = C.con_luz(img, k, ox, oy, luz)
    cab, mano = C.cama(img, k, ox, oy, st, t)
    if hora:
        suena = sacude and (lt % 0.5) < 0.3
        C.reloj_tarjeta(img, hora, 1020, 230, 1.0 if suena else 0.0, t)
        if suena:
            d = ImageDraw.Draw(img)
            for lado in (-1, 1):
                for kk in range(3):
                    x = 1020 + lado*(175 + kk*22)
                    d.line([(x, 200 - kk*8), (x + lado*10, 260 + kk*8)], fill=T, width=5)
    if texto:
        txt, t0 = texto
        C.dice(img, txt, cab[0] + 60, cab[1] - 70, t0, lt)
    if apaga is not None and lt > apaga:        # apaga la luz: solo queda el brillo de su llama
        k2 = suave((lt - apaga)/0.4)
        oscuro = oscurece(img, 0.86*k2)
        m = Image.new("L", img.size, 0)
        ImageDraw.Draw(m).ellipse([cab[0] - 170, cab[1] - 150, cab[0] + 170, cab[1] + 190], fill=255)
        m = m.filter(ImageFilter.GaussianBlur(70))
        img = Image.composite(img, oscuro, m.point(lambda v: int(v*(0.55 + 0.45*(1 - k2)))))
    return img, (560 + lt*12, 430, 1.25 + 0.025*lt)

def cama_cerca(lt, t, st, hora=None, destellos=(), luz=0.4):
    img = C.recorte(bg("dormitorio", oscuro=0.7), 1000, 250, 2.2)
    k, ox, oy = 2.3, -100, -380
    if st.get("pose") == "movil" and luz:
        img = C.con_luz(img, k, ox, oy, luz)
    C.cama(img, k, ox, oy, st, t)
    if hora:
        C.reloj_tarjeta(img, hora, 1320, 140, 0, t)
    for t0 in destellos:
        if 0 <= lt - t0 < 0.12:
            img = oscurece(img, 0.5)
    return img, (800, 450, 1.0 + 0.012*lt)

def lapso(lt, t, horas):
    """horas: [(t0, "1:10 AM", llama, cansancio)]: pasan las horas y la llama baja."""
    hora, ll, cc = horas[0][1:]
    for t0, hh, l2, c2 in horas:
        if lt >= t0: hora, ll, cc = hh, l2, c2
    st = dict(llama=ll, cansancio=cc, parpadeo=parpadeo(lt, 2.4, 1.0), mira=(0.3, 0.9), pose="movil", ceja=0.4*cc, inclina=-0.03*cc)
    return cama_cerca(lt, t, st, hora, destellos=[h[0] for h in horas[1:]])

# ---------------------------------------------------------------- los planos
def p_cama_lunes(lt, t):
    st = dict(llama=1.0, cansancio=0.1, parpadeo=parpadeo(lt), mira=(0.3, 0.9), pose="movil")
    return cama_ancha(lt, t, st, "11:58 PM", texto=("Just one more video.", 1.3))

def p_feed(lt, t):
    img = oscurece(C.recorte(bg("dormitorio", oscuro=0.7), 1000, 250, 2.2).filter(ImageFilter.GaussianBlur(8)), 0.3)
    img = C.luz(img, 800, 450, 420, 0.35)
    swipes = (0.8, 1.9, 3.0)
    pulgar = None
    for ts in swipes:
        k = (lt - ts + 0.15)/0.5
        if 0 <= k <= 1:
            pulgar = (860, 640 - 260*suave(k))
    movil_grande(img, 800, 470, 780, "feed", lt, swipes, pulgar)
    return img, (800, 460, 1.0 + 0.02*lt)

def p_lapso_lunes(lt, t):
    return lapso(lt, t, [(0.0, "12:40 AM", 0.8, 0.25), (1.5, "1:30 AM", 0.6, 0.4), (3.0, "2:15 AM", 0.4, 0.6), (4.5, "3:47 AM", 0.2, 0.85)])

def p_alarma(lt, t, tap=2.4):
    img = oscurece(C.recorte(bg("dormitorio", claro=0.1), 1000, 250, 2.2).filter(ImageFilter.GaussianBlur(8)), 0.35)
    pos = lt > tap
    pulgar = None
    k = (lt - (tap - 0.6))/0.6
    if 0 <= k <= 1.4:
        pulgar = (800 + 60*(1 - suave(k)), 470 + 780*0.19 + 200*(1 - suave(min(1, k))))
    movil_grande(img, 800, 470, 780, "alarma", lt, ("7:00", pos), pulgar)
    if pos and lt - tap < 0.1:
        img = oscurece(img, 0.25, (255, 255, 255))
    return img, (800, 460, 1.0)

def p_cama_720(lt, t):
    st = dict(llama=0.12, humo=True, cansancio=0.95, mira=(0, 0.6), ceja=0.8, inclina=-0.06)
    img, cam = cama_ancha(lt, t, st, "7:20 AM", clave="manana", sacude=True)
    return img, (560, 430, 1.3)

def p_bano(lt, t):
    # La cámara es el espejo: le vemos la cara, y detrás de él, la pared del baño.
    img = C.recorte(bg("bano", claro=0.05), 430, 360, 1.5)
    k = (lt - 2.4)/0.9
    st = dict(llama=0.12 + (0.25*math.sin(math.pi*min(1, max(0, k))) if 0 < k < 1 else 0), humo=k > 0.8 or k < 0,
              cansancio=0.9 - 0.5*math.sin(math.pi*min(1, max(0, (lt - 2.2)/1.2))), mira=(0, 0), ceja=0.7,
              inclina=-0.03 - 0.05*suave((lt - 3.6)/0.8), pose="caido", sin_piernas=True, parpadeo=parpadeo(lt, 4.1, 1.2))
    cab, _ = C.cerilla(img, 800, 930, 1800, 1000, st, t)
    d = ImageDraw.Draw(img)
    chispas(d, cab[0], cab[1] + 30, (lt - 2.4)/0.7, 160)
    # el lavabo, delante, en primer plano abajo
    d.rounded_rectangle([420, 830, 1180, 960], radius=30, fill=(236, 236, 238), outline=T, width=5)
    return img, (800, 450, 1.0 + 0.015*lt)

EXTRAS_CALLE = [("capsula", 1650, -165, 0.0, 470, 790), ("gorro", 2100, -150, 1.3, 450, 785)]
def calle(lt, t, clave, cer, extras=EXTRAS_CALLE, sol=False):
    img = bg("calle", claro=0.05) if clave == "dia" else bg("calle", oscuro=0.5)
    if clave == "tarde":
        for x in (320, 1280):
            img = C.luz(img, x, 215, 160, 0.55, (250, 250, 235))
    if sol:
        img = C.luz(img, 1300, -80, 420, 0.45, (255, 255, 250))
    for tipo, x0, v, f0, h, suelo in extras:       # la gente de la calle, mirando el móvil
        extra(img, x0 + v*lt, suelo, h, tipo, dict(fase=lt*7 + f0, pose="movil", dir=-0.6, cansancio=0.2), t)
    x = cer["x0"] + cer["v"]*lt
    st = dict(cer["st"], fase=lt*cer.get("paso", 7.5))
    cab, mano = C.cerilla(img, x, 830 - 0.2*520, 830, 520, st, t)
    if st.get("pose") == "movil":
        C.movil(ImageDraw.Draw(img), mano[0], mano[1], 520)
    return img, (min(max(x, 700), 900), 470, 1.12)

def p_calle_manana(lt, t):
    return calle(lt, t, "dia", dict(x0=150, v=190, st=dict(llama=0.12, humo=True, cansancio=0.8, pose="movil", mira=(0.3, 0.9), dir=0.6)))

ASIENTO, H_METRO = 700, 600
def metro(lt, t, gente=True, cartel=False, st=None, sacude=0.0):
    img = bg("metro", claro=0.0)
    d = ImageDraw.Draw(img)
    suelo = ASIENTO + 0.15*H_METRO
    d.rectangle([150, ASIENTO - 8, 1450, ASIENTO + 22], fill=(150, 150, 154), outline=T, width=4)     # el asiento
    d.rectangle([170, ASIENTO + 22, 1430, suelo - 6], fill=(112, 112, 116), outline=T, width=4)      # el frontal
    if cartel:
        d.rectangle([650, 25, 950, 95], fill=(20, 20, 24))
        d.text((800, 60), "LAST STOP", font=fuente(40), fill=(250, 250, 250), anchor="mm")
    if gente:
        extra(img, 420, suelo, H_METRO*0.95, "capsula", dict(cadera=ASIENTO, pose="movil"), t)
        extra(img, 1190, suelo, H_METRO*0.95, "gafas", dict(cadera=ASIENTO, pose="movil"), t)
    cab, mano = C.cerilla(img, 800, ASIENTO, suelo, H_METRO, st, t)
    if st.get("pose") == "movil":
        C.movil(ImageDraw.Draw(img), mano[0], mano[1], H_METRO)
    dx = math.sin(t*23)*3 + sacude*math.sin(t*60)*14
    return img, (800 + dx, 450, 1.08)

def p_metro_duerme(lt, t, desde=0.0):
    lt2 = lt + desde
    k = suave((lt2 - 1.0)/2.5)
    st = dict(llama=0.12, humo=True, cansancio=0.6 + 0.4*k, ceja=0.6, inclina=-0.13*k, pose="movil",
              objeto=(805, ASIENTO - H_METRO*0.34 + 95*k), mira=(0.3, 0.9))
    return metro(lt2, t, st=st)

def p_metro_final(lt, t):
    desp = suave((lt - 0.3)/0.15)
    st = dict(llama=0.12 + 0.05*desp, humo=True, cansancio=1.0 - 0.95*desp, ceja=0.0, sorpresa=desp, inclina=-0.13*(1 - desp),
              pose="caido", dir=(-1 if 1.1 < lt < 2.0 else (1 if 2.0 <= lt < 2.9 else 0)))
    return metro(lt, t, gente=False, cartel=True, st=st, sacude=max(0, 1 - lt/0.6))

def oficina_hombro(lt, t, st_c, linea_nube, linea_cer):
    img = bg("oficina", claro=0.05)
    C.silla(img, 1040, 470, 760, 300)
    cab, _ = C.cerilla(img, 1040, 800, 900, 700, st_c, t)
    C.mesa(img, 760, 1320, 720, px=1040)
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    C.nube(capa, 250, 2000, 2000, dict(espalda=True), t)
    capa = C.desenfoca(capa, 12)
    img.paste(capa, (0, 0), capa)
    C.dice(img, linea_nube[0], 420, 140, linea_nube[1], lt, 46)
    C.dice(img, linea_cer[0], cab[0], cab[1] - 30, linea_cer[1], lt, 42)
    return img, (900, 470, 1.0 + 0.01*lt)

def oficina_contra(lt, t, st_n, linea, cer_llama=0.0, cer_humo=True):
    img = bg("oficina", claro=0.05, espejo=True)
    cab = C.nube(img, 640, 790, 560, st_n, t)
    d = ImageDraw.Draw(img)
    if st_n.get("pose") == "brindis":
        vaso(d, 640 + 560*0.2, 790 - 560*0.72 - 560*0.11*0.2, 560)
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    C.cerilla(capa, 1380, 1500, 2400, 1500, dict(espalda=True, humo=cer_humo, llama=cer_llama), t)
    capa = C.desenfoca(capa, 12)
    img.paste(capa, (0, 0), capa)
    C.dice(img, linea[0], cab[0] + 30, cab[1] - 20, linea[1], lt, 44)
    return img, (760, 450, 1.0 + 0.012*lt)

def p_ofi_martes_1(lt, t):
    st = dict(llama=0.12, humo=True, cansancio=0.85, parpadeo=parpadeo(lt, 3.1, 0.5), mira=(-0.5 if lt < 2.4 else -0.8, 0.3),
              pose="mesa", objeto=(0, 700), ceja=0.7, inclina=-0.05, sin_piernas=True)
    return oficina_hombro(lt, t, st, ("Rough night?", 0.5), ("Just one more video...", 2.6))

def p_ofi_martes_2(lt, t):
    st = dict(cansancio=0.15 + 0.35*suave((lt - 1.8)/0.4), parpadeo=parpadeo(lt, 2.9, 1.8), mira=(0.7, 0.1), ceja=0.15, pose="taza")
    return oficina_contra(lt, t, st, ("You said that yesterday.", 0.6), 0.12)

def p_ofi_duerme(lt, t, nube_viene=True, desde=0.0):
    lt2 = lt + desde
    img = bg("oficina", claro=0.05)
    k = suave(lt2/3.0)
    despierta = nube_viene and lt2 > 4.8
    j = suave((lt2 - 4.8)/0.15) if despierta else 0
    st = dict(llama=0.12 if not despierta else 0.18, humo=True, cansancio=(0.6 + 0.4*k)*(1 - j), ceja=0.6*(1 - j), sorpresa=j,
              inclina=-0.15*k*(1 - j), pose="mesa", objeto=(0, 720), sin_piernas=True, dir=j*0.8, mira=(0.6*j, 0.3))
    if nube_viene and lt2 > 2.3:
        xn = 1750 - 480*suave((lt2 - 2.3)/1.4)
        andando = lt2 < 3.7
        C.nube(img, xn, 830, 560, dict(fase=lt2*7 if andando else None, pose="taza", dir=-0.8, mira=(-0.7, 0.2),
                                       parpadeo=parpadeo(lt2, 3.3)), t)
    C.silla(img, 760, 470, 760, 300)
    cab, _ = C.cerilla(img, 760, 800, 900, 700, st, t)
    C.mesa(img, 480, 1040, 720, px=760)
    if nube_viene:
        C.dice(img, "Hey. Meeting. Now.", 1270, 300, 3.9, lt2, 44)
    return img, (900 if nube_viene else 760, 470, 1.05 + 0.01*lt)

def p_calle_tarde(lt, t, desde=0.0):
    return calle(lt + desde, t, "tarde", dict(x0=200, v=150, paso=5.5,
                 st=dict(llama=0.1, humo=True, cansancio=0.85, ceja=0.7, inclina=-0.06, pose="anda", dir=0.5, mira=(0.3, 0.8))),
                 extras=[("gafas", 1700, -140, 0.4, 460, 790)])

def fondo_chat():
    return oscurece(C.recorte(bg("salon", oscuro=0.55), 800, 400, 1.8).filter(ImageFilter.GaussianBlur(9)), 0.2)

def p_chat_1(lt, t):
    img = fondo_chat()
    img = C.luz(img, 800, 450, 420, 0.35)
    datos = [(-1, "Dinner Friday?", 0.5, 0), (1, "Too tired. Next time.", 3.5, 1.5), (-1, "ok.", 4.7, 0)]
    pulgar = (820 + 40*math.sin(lt*14), 790) if 2.0 <= lt < 3.5 else None
    movil_grande(img, 800, 470, 780, "chat", lt, datos, pulgar)
    return img, (800, 460, 1.0 + 0.015*lt)

def p_cocina(lt, t):
    img = bg("cocina_noche")
    img = C.luz(img, 1300, 420, 330, 0.25, (240, 240, 250))
    st = dict(llama=0.1, humo=True, cansancio=0.75, mira=(0.3, 0.9), pose="movil", ceja=0.5, parpadeo=parpadeo(lt, 3.5))
    tmp = img.copy(); cab, mano = C.cerilla(tmp, 1020, 860 - 0.2*560, 860, 560, st, t)
    img = C.luz(img, mano[0], mano[1] - 70, 170, 0.35)
    cab, mano = C.cerilla(img, 1020, 860 - 0.2*560, 860, 560, st, t)
    C.movil(ImageDraw.Draw(img), mano[0], mano[1], 560)
    return img, (1000, 470, 1.12 + 0.015*lt)

def p_cama_martes(lt, t):
    st = dict(llama=0.6, cansancio=0.45, ceja=0.3, parpadeo=parpadeo(lt), mira=(0.3, 0.9), pose="movil")
    return cama_ancha(lt, t, st, "11:58 PM", texto=("Just one more video.", 1.1))

def p_lapso_martes(lt, t):
    return lapso(lt, t, [(0.0, "1:10 AM", 0.45, 0.55), (1.3, "2:40 AM", 0.25, 0.75), (2.6, "4:05 AM", 0.1, 0.9)])

def p_mont_alarma(lt, t):
    return p_alarma(lt, t, tap=1.1)

def p_mont_metro(lt, t):
    return p_metro_duerme(lt, t, desde=2.2)

def p_mont_ofi(lt, t):
    return p_ofi_duerme(lt, t, nube_viene=False, desde=1.2)

def p_mont_calle(lt, t):
    return p_calle_tarde(lt, t, desde=1.0)

def p_cama_miercoles(lt, t):
    apagado = lt > 3.6
    st = dict(llama=0.3, cansancio=0.6, ceja=0.5, parpadeo=parpadeo(lt), mira=(0.3, 0.9), pose="movil")
    img, cam = cama_ancha(lt, t, st, "11:58 PM", texto=("Just one...", 1.2), luz=0.0 if apagado else 0.45)
    return img, cam

def reflejo(pant):
    """En la pantalla negra se ve su cara: la llama casi apagada."""
    W, H = pant.size
    capa = Image.new("RGB", pant.size, (10, 10, 12))
    st = dict(llama=0.3, cansancio=0.55, mira=(0, 0), ceja=0.5, pose="caido", sin_piernas=True)
    C.cerilla(capa, W/2, H*1.25, H*2, H*1.5, st, 0.7)
    capa = capa.filter(ImageFilter.GaussianBlur(1.5))
    pant.paste(Image.blend(pant, capa, 0.32))

def p_reflejo(lt, t):
    img = oscurece(C.recorte(bg("dormitorio", oscuro=0.75), 1000, 250, 2.2).filter(ImageFilter.GaussianBlur(9)), 0.4)
    movil_grande(img, 800, 470, 780, "negro", lt, fondo_pantalla=reflejo)
    return img, (800, 420, 1.0 + 0.06*lt)

def p_se_da_cuenta(lt, t):
    k = suave((lt - 0.8)/1.2)
    st = dict(llama=0.3 + 0.05*math.sin(t*9), cansancio=0.6 - 0.45*k, ceja=0.5*(1 - k), sorpresa=0.6*k, mira=(0.3, 0.9 - 0.9*k), pose="movil",
              parpadeo=parpadeo(lt, 9, 2.8))
    return cama_cerca(lt, t, st, luz=0.0)

def p_deja_movil(lt, t):
    # La cocina, sin la nevera: deja el móvil en la encimera y se va a dormir.
    img = oscurece(C.recorte(bg("cocina_noche"), 560, 420, 1.45), 0.1)
    img = C.luz(img, 330, 120, 260, 0.2, (220, 225, 245))         # la luna por la ventana
    if lt < 2.0:
        x = 120 + 520*suave(lt/2.0); fase = lt*7
    elif lt < 3.8:
        x = 640; fase = None
    else:
        x = 640 + 1100*((lt - 3.8)/2.2); fase = (lt - 3.8)*7
    deja = suave((lt - 2.2)/0.5)
    encima = (760, 476)            # sobre la encimera
    pecho = (x + 70, 520)
    obj = (pecho[0] + (encima[0] - pecho[0])*deja, pecho[1] + (encima[1] - pecho[1])*deja)
    con_movil = lt < 2.8
    st = dict(llama=0.3, cansancio=0.45, ceja=0.2, pose="movil" if con_movil else ("anda" if fase is not None else "caido"),
              objeto=obj, fase=fase, dir=(0.7 if fase is not None else (0.5 if lt < 3.2 else 0)), mira=(0.4, 0.8) if lt < 3.2 else (0, 0.2))
    encendido = lt < 3.3
    d = ImageDraw.Draw(img)
    if not con_movil:      # el móvil, tumbado en la encimera
        d.rounded_rectangle([encima[0] - 50, encima[1] - 6, encima[0] + 50, encima[1] + 8], radius=4, fill=(18, 18, 22), outline=T, width=3)
        if encendido:
            img = C.luz(img, encima[0], encima[1] - 30, 90, 0.35)
    cab, mano = C.cerilla(img, x, 900 - 0.2*820, 900, 820, st, t)
    if con_movil:
        C.movil(ImageDraw.Draw(img), mano[0], mano[1], 820, encendido=True)
    return img, (700, 450, 1.0)

def p_cama_duerme(lt, t):
    st = dict(llama=0.3, cansancio=0.4 + 0.6*suave((lt - 1.6)/1.4), ceja=0.0, pose="caido", mira=(0, 0.3))
    return cama_ancha(lt, t, st, None, apaga=0.9)

def p_jueves_despierta(lt, t):
    abre = suave((lt - 1.0)/0.4)
    pop = suave((lt - 1.8)/0.35)
    arriba = 2.9 < lt < 4.4
    st = dict(llama=0.15 + 0.55*pop + 0.03*math.sin(t*8), cansancio=1.0 - 0.85*abre, ceja=0.0, mira=(0, 0.2),
              pose="arriba" if arriba else "caido", feliz=1.0 if 3.2 < lt < 4.3 else 0.0, parpadeo=parpadeo(lt, 9, 4.8))
    img, cam = cama_ancha(lt, t, st, "7:00 AM", clave="manana", sacude=lt < 1.0)
    d = ImageDraw.Draw(img)
    chispas(d, 60 + 370*0.95, 150 + 410*0.95, (lt - 1.8)/0.6, 120)
    return img, (560, 430, 1.3 - 0.02*lt)

def p_calle_jueves(lt, t):
    return calle(lt, t, "dia", dict(x0=120, v=235, paso=9.0,
                 st=dict(llama=0.7, cansancio=0.1, pose="anda", dir=0.6, mira=(0.2, -0.7) if 2.4 < lt < 4.2 else (0.3, 0.1),
                         feliz=1.0 if 2.8 < lt < 4.0 else 0.0)), sol=True)

def p_ofi_jueves_1(lt, t):
    st = dict(llama=0.7, cansancio=0.1, parpadeo=parpadeo(lt, 3.1, 0.5), mira=(-0.6, 0.2), pose="mesa", objeto=(0, 700),
              sin_piernas=True, feliz=1.0 if lt > 3.9 else 0.0)
    return oficina_hombro(lt, t, st, ("Rough night?", 0.5), ("Actually... no.", 2.4))

def p_ofi_jueves_2(lt, t):
    s = suave((lt - 0.3)/0.3)
    st = dict(cansancio=0.0, sorpresa=s if lt < 2.4 else 0.0, feliz=1.0 if lt >= 2.4 else 0.0, mira=(0.7, 0.1),
              pose="brindis" if lt >= 2.4 else "taza", parpadeo=parpadeo(lt, 9, 1.9))
    return oficina_contra(lt, t, st, ("", 0), cer_llama=0.7, cer_humo=False)

def p_chat_2(lt, t):
    img = fondo_chat()
    img = C.luz(img, 800, 450, 420, 0.35)
    datos = [(-1, "Dinner Friday?", -1, 0), (1, "Too tired. Next time.", -1, 0), (-1, "ok.", -1, 0),
             (1, "Is Friday still on?", 2.4, 1.8), (-1, "YES!! 8pm", 3.6, 0)]
    pulgar = (820 + 40*math.sin(lt*14), 790) if 0.6 <= lt < 2.4 else None
    movil_grande(img, 800, 470, 780, "chat", lt, datos, pulgar)
    return img, (800, 460, 1.0 + 0.015*lt)

def p_bar(lt, t):
    img = bg("fiesta", claro=0.0)
    img = C.luz(img, 800, 330, 300, 0.22, (255, 170, 90))          # su llama ilumina a todos
    brinda = suave((lt - 2.6)/0.5)
    centro = (800, 330)
    def copa(x, y):
        return (x + (centro[0] - x)*0.35*brinda, y + (centro[1] - y)*0.35*brinda)
    extra(img, 330, 850, 520, "gorro", dict(pose="brindis", objeto=copa(440, 420), feliz=1.0, dir=0.6), t)
    extra(img, 1290, 850, 540, "capsula", dict(pose="brindis", objeto=copa(1180, 430), feliz=1.0 if lt > 2.0 else 0.0, dir=-0.6), t)
    C.nube(img, 1040, 850, 560, dict(feliz=1.0, dir=-0.5, pose="brindis", objeto=copa(930, 440), vaso=True), t)
    vaso(ImageDraw.Draw(img), *copa(930, 440), 560)
    st = dict(llama=1.0, cansancio=0.0, feliz=1.0 if lt > 1.0 else 0.0, pose="brindis", objeto=copa(700, 400), dir=0.2)
    cab, _ = C.cerilla(img, 600, 850 - 0.2*560, 850, 560, st, t)
    d = ImageDraw.Draw(img)
    vaso(d, *copa(700, 400), 560)
    if lt > 3.1:     # el brindis: un pequeño destello entre las copas
        k = suave((lt - 3.1)/0.3)*(1 - suave((lt - 3.5)/0.5))
        if k > 0:
            for a in range(8):
                ang = a*math.pi/4
                d.line([(centro[0] + math.cos(ang)*20, centro[1] + 60 + math.sin(ang)*20),
                        (centro[0] + math.cos(ang)*(20 + 40*k), centro[1] + 60 + math.sin(ang)*(20 + 40*k))], fill=(250, 250, 250), width=4)
    return img, (800, 470, 1.05 + 0.015*lt)

def p_final(lt, t, dur):
    img = Image.new("RGB", (CW, CH), (8, 8, 10)); d = ImageDraw.Draw(img)
    for t0, txt, y, px, col in ((0.5, "One more video", 380, 66, 250), (1.6, "always costs one more morning.", 470, 66, 250)):
        a = suave((lt - t0)/0.7)*suave((dur - lt)/0.8)
        c = int(8 + (col - 8)*a)
        d.text((CW/2, y), txt, font=fuente(px), fill=(c, c, c), anchor="mm")
    a = suave((lt - 3.4)/0.8)*suave((dur - lt)/0.8)
    if a > 0:
        c = int(8 + 150*a)
        d.text((CW/2 + 22, 690), "STILL BURNING", font=fuente(34), fill=(c, c, c), anchor="mm")
        x = CW/2 - 175
        d.rounded_rectangle([x - 5, 670, x + 5, 720], radius=4, fill=tuple(int(8 + (v - 8)*a) for v in (225, 218, 200)))
        d.ellipse([x - 12, 652, x + 12, 678], fill=tuple(int(8 + (v - 8)*a) for v in C.ROJO))
        if a > 0.6:
            C.llama(d, x, 655, 30*a, t)
    return img, (CW/2, CH/2, 1.0)

# ---------------------------------------------------------------- el montaje
# (función, duración, sonidos [(segundo dentro del plano, tipo)])
GUION = [
    (lambda lt, t: tarjeta(lt, 2.5, "MONDAY"), 2.5, []),
    (p_cama_lunes, 5.0, []),
    (p_feed, 4.0, [(0.8, "swish"), (1.9, "swish"), (3.0, "swish")]),
    (p_lapso_lunes, 6.0, [(1.5, "tic"), (3.0, "tic"), (4.5, "tic")]),
    (negro, 0.8, []),
    (lambda lt, t: tarjeta(lt, 2.6, "ONE MORE", 96), 2.6, []),
    (p_alarma, 3.5, [(0.0, "alarma2.4"), (2.4, "tap")]),
    (p_cama_720, 3.0, [(0.0, "alarma3.0")]),
    (p_bano, 5.0, [(2.4, "chispa")]),
    (p_calle_manana, 6.5, []),
    (p_metro_duerme, 4.2, [(0.0, "tren4.2")]),
    (p_metro_final, 3.6, [(0.0, "freno")]),
    (p_ofi_martes_1, 5.5, []),
    (p_ofi_martes_2, 4.5, []),
    (p_ofi_duerme, 6.5, [(4.8, "golpe")]),
    (lambda lt, t: p_calle_tarde(lt, t), 5.0, []),
    (p_chat_1, 6.0, [(0.5, "ding"), (3.5, "envia"), (4.7, "ding")]),
    (p_cocina, 4.5, []),
    (p_cama_martes, 4.5, []),
    (p_lapso_martes, 4.0, [(1.3, "tic"), (2.6, "tic")]),
    (lambda lt, t: tarjeta(lt, 2.0, "WEDNESDAY"), 2.0, []),
    (p_mont_alarma, 1.8, [(0.0, "alarma1.1"), (1.1, "tap")]),
    (p_mont_metro, 2.0, [(0.0, "tren2.0")]),
    (p_mont_ofi, 2.2, []),
    (p_mont_calle, 2.0, []),
    (p_cama_miercoles, 5.0, [(3.6, "click")]),
    (p_reflejo, 5.0, []),
    (p_se_da_cuenta, 3.6, []),
    (p_deja_movil, 6.0, [(2.6, "tap"), (3.3, "click")]),
    (p_cama_duerme, 4.0, [(0.9, "click")]),
    (negro, 1.5, []),
    (lambda lt, t: tarjeta(lt, 2.0, "THURSDAY"), 2.0, []),
    (p_jueves_despierta, 5.0, [(0.0, "alarma1.0"), (1.8, "chispa")]),
    (p_calle_jueves, 6.0, []),
    (p_ofi_jueves_1, 5.5, []),
    (p_ofi_jueves_2, 4.5, []),
    (p_chat_2, 5.0, [(2.4, "envia"), (3.6, "ding")]),
    (lambda lt, t: tarjeta(lt, 2.0, "FRIDAY"), 2.0, []),
    (p_bar, 6.0, [(3.1, "clink")]),
    (lambda lt, t: p_final(lt, t, 8.0), 8.0, []),
    (negro, 2.0, []),
]

def tiempos():
    t = 0.0; out = []
    for fn, dur, sfx in GUION:
        out.append((t, t + dur, fn, sfx)); t += dur
    return out, t

TABLA, DUR = tiempos()
# La música cambia de humor: gris hasta que deja el móvil, esperanza desde el jueves.
_INICIO = {fn: a for a, b, fn, s in TABLA}
CAMBIO = _INICIO[p_deja_movil]
JUEVES = _INICIO[p_jueves_despierta]
FINAL = DUR - 10.0

def fotograma(t):
    for a, b, fn, _ in TABLA:
        if a <= t < b:
            img, (cx, cy, z) = fn(t - a, t)
            break
    else:
        img, (cx, cy, z) = negro(0)
    img = C.recorte(img, cx, cy, z) if z > 1.001 or abs(cx - CW/2) > 1 else img
    img = img.resize((VW, VH), Image.LANCZOS)
    if t < 0.5:
        img = oscurece(img, 1 - t/0.5)
    return vineta(img)

_VIN = None
def vineta(img):
    global _VIN
    if _VIN is None:
        m = Image.new("L", (VW, VH), 0)
        ImageDraw.Draw(m).ellipse([-VW*0.15, -VH*0.2, VW*1.15, VH*1.2], fill=255)
        _VIN = m.filter(ImageFilter.GaussianBlur(150))
    return Image.composite(img, oscurece(img, 0.4), _VIN)

# ---------------------------------------------------------------- sonido
SR = 44100
def nota(m): return 440*2**((m - 69)/12)

def musica():
    n = int(DUR*SR); t = np.arange(n)/SR
    out = np.zeros(n)
    secciones = [
        # (inicio, fin, acordes, segundos por acorde, volumen del piano, octava del piano)
        (0, CAMBIO, [[57, 60, 64, 67], [53, 57, 60, 64], [48, 55, 59, 64], [55, 59, 62, 64]], 3.0, 0.045, 12),
        (CAMBIO, JUEVES, [[53, 57, 60, 64], [48, 55, 60, 64]], 4.0, 0.025, 12),
        (JUEVES, FINAL, [[48, 55, 60, 64], [55, 59, 62, 67], [57, 60, 64, 69], [53, 57, 60, 65]], 2.0, 0.06, 24),
        (FINAL, DUR, [[48, 55, 60, 64], [53, 57, 60, 65]], 3.0, 0.04, 12),
    ]
    for a, b, acordes, dur, vp, octava in secciones:
        i = 0; t0 = a
        while t0 < b:
            ac = acordes[i % len(acordes)]
            s0, s1 = int(t0*SR), min(n, int((min(b, t0 + dur) + 0.8)*SR))
            tt = t[s0:s1] - t0
            fin = min(b, t0 + dur) - t0
            env = np.minimum(1, tt/0.9)*np.exp(-np.maximum(0, tt - fin)*5)
            for m in ac:
                f = nota(m)
                out[s0:s1] += 0.045*env*(np.sin(2*np.pi*f*tt) + 0.25*np.sin(2*np.pi*2*f*tt + 0.4))
            out[s0:s1] += 0.06*env*np.sin(2*np.pi*nota(ac[0] - 12)*tt)
            paso = dur/4
            for k, m in enumerate([ac[0], ac[2], ac[1], ac[3]]):
                pa = t0 + k*paso
                if pa >= b: break
                a0 = int(pa*SR); a1 = min(n, a0 + int(1.8*SR))
                ta = t[a0:a1] - pa; f = nota(m + octava)
                out[a0:a1] += vp*np.exp(-ta*2.4)*(np.sin(2*np.pi*f*ta) + 0.2*np.sin(2*np.pi*3*f*ta))
            t0 += dur; i += 1
    # reverberación: una cola de ruido que se apaga (convolución por FFT)
    ir_n = int(1.8*SR)
    ir = np.random.default_rng(2).standard_normal(ir_n)*np.exp(-np.arange(ir_n)/SR*3.2)
    ir[0] = 1.0; ir /= np.sqrt(np.sum(ir**2))
    L = n + ir_n
    wet = np.fft.irfft(np.fft.rfft(out, L)*np.fft.rfft(ir, L), L)[:n]
    out = 0.65*out + 0.35*wet/np.max(np.abs(wet))*np.max(np.abs(out))
    out += 0.003*np.random.default_rng(1).standard_normal(n)
    return out

def efectos():
    n = int(DUR*SR); out = np.zeros(n); rnd = np.random.default_rng(5)
    def pon(t0, *xs):
        for x in xs:
            s0 = int(t0*SR); s1 = min(n, s0 + len(x))
            if s0 < n: out[s0:s1] += x[:s1 - s0]
    def tono(f, d, vol, ataque=0.005, caida=8.0):
        tt = np.arange(int(d*SR))/SR
        return vol*np.sin(2*np.pi*f*tt)*np.minimum(1, tt/ataque)*np.exp(-tt*caida)
    def ruido(d, vol, suav=20):
        x = rnd.standard_normal(int(d*SR))
        return vol*np.convolve(x, np.ones(suav)/suav, mode="same")
    for a, b, fn, sfx in TABLA:
        for t0, tipo in sfx:
            T0 = a + t0
            if tipo.startswith("alarma"):
                dur = float(tipo[6:])
                k = 0.0
                while k < dur:
                    tt = np.arange(int(0.12*SR))/SR
                    beep = 0.09*np.sign(np.sin(2*np.pi*1750*tt))*np.minimum(1, tt/0.005)*np.minimum(1, (0.12 - tt)/0.005)
                    pon(T0 + k, beep); pon(T0 + k + 0.18, beep)
                    k += 0.6
            elif tipo.startswith("tren"):
                dur = float(tipo[4:]); x = ruido(dur, 0.05, 200)
                x *= np.minimum(1, np.arange(len(x))/(0.3*SR))*np.minimum(1, (len(x) - np.arange(len(x)))/(0.3*SR))
                pon(T0, x)
            elif tipo == "freno":
                tt = np.arange(int(0.7*SR))/SR
                pon(T0, 0.05*np.sin(2*np.pi*(2400 - 600*tt)*tt)*np.exp(-tt*3) + ruido(0.7, 0.05, 30)*np.exp(-tt*4))
            elif tipo == "tap":
                pon(T0, ruido(0.03, 0.25, 3), tono(1200, 0.04, 0.05, 0.001, 60))
            elif tipo == "click":
                pon(T0, ruido(0.02, 0.3, 2), tono(2200, 0.03, 0.06, 0.001, 90))
            elif tipo == "swish":
                x = ruido(0.25, 0.12, 6); pon(T0, x*np.sin(np.linspace(0, np.pi, len(x))))
            elif tipo == "ding":
                pon(T0, tono(1318, 0.6, 0.08, 0.002, 5), tono(1976, 0.5, 0.04, 0.002, 6))
            elif tipo == "envia":
                tt = np.arange(int(0.18*SR))/SR
                pon(T0, 0.06*np.sin(2*np.pi*(700 + 2600*tt)*tt)*np.exp(-tt*10))
            elif tipo == "tic":
                pon(T0, tono(880, 0.25, 0.05, 0.002, 12))
            elif tipo == "chispa":
                x = ruido(0.35, 0.12, 2)*np.exp(-np.arange(int(0.35*SR))/SR*9); pon(T0, x)
            elif tipo == "golpe":
                pon(T0, tono(90, 0.25, 0.25, 0.002, 18), ruido(0.08, 0.1, 10))
            elif tipo == "clink":
                pon(T0, tono(2637, 0.9, 0.06, 0.001, 4), tono(3520, 0.7, 0.04, 0.001, 5))
    return out

def audio(ruta):
    mus = musica(); fx = efectos()
    mix = mus/np.max(np.abs(mus))*0.42 + fx
    fade = np.ones(len(mix)); fo = int(2.5*SR); mix[-fo:] *= np.linspace(1, 0, fo)
    mix = np.clip(mix, -0.98, 0.98)
    pcm = (mix*32767).astype(np.int16)
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

def main():
    Path(OUT).mkdir(exist_ok=True)
    args = sys.argv[1:]
    if args and args[0] == "fotos":
        # una foto por plano (a mitad) para revisar
        for i, (a, b, fn, _) in enumerate(TABLA):
            fotograma((a + b)/2).resize((960, 540)).save(OUT + f"rev_{i:02d}.jpg", quality=85)
        print(f"{len(TABLA)} planos, {DUR:.1f} s")
        return
    if args and args[0] == "en":
        for s in args[1:]:
            fotograma(float(s)).resize((960, 540)).save(OUT + f"en_{float(s):06.2f}.jpg", quality=85)
        return
    audio(OUT + "one_more_audio.wav")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}",
                          "-r", str(FPS), "-i", "-", "-i", OUT + "one_more_audio.wav", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                          "-crf", "19", "-preset", "medium", "-c:a", "aac", "-b:a", "192k", "-shortest",
                          OUT + "ONE_MORE.mp4"], stdin=subprocess.PIPE)
    for i in range(int(DUR*FPS)):
        p.stdin.write(fotograma(i/FPS).tobytes())
    p.stdin.close(); p.wait()
    print(f"hecho: {DUR:.1f} s")

if __name__ == "__main__":
    main()
