"""Monigotes: las escenas del canal, dibujadas con codigo.

Sustituye a la ilustracion por IA en vertical, y no es un apaño barato: es
mejor en las cuatro cosas que importaban.

GRATIS E INSTANTANEO. Cuatro centimos y siete segundos por imagen pasan a
cero y medio segundo. Un Short de cinco escenas se ahorra 20 centimos, y una
animacion de 36 fotogramas que con Gemini costaria 1,44 $ aqui cuesta nada.

IGUAL EN TODOS LOS PLANOS. Era el fallo de fondo del #82: cinco ilustraciones
preciosas que no se conocian entre si, o sea cinco imagenes de stock dibujadas.
Un monigote se dibuja idéntico siempre, por construccion.

SE MUEVE DE VERDAD. Una pose es una lista de PUNTOS, asi que entre dos poses
hay infinitas intermedias. El personaje anda, levanta el brazo o se sienta -
no es un zoom sobre una foto quieta, que es lo unico que se podia hacer antes.

Y LO PUEDO VER YO. Esto es lo que mas cambia. Llevaba el dia ajustando el
aspecto a ciegas, quemandole a ella videos de 50 centimos para enterarme de
como habia quedado. Con esto genero, miro y corrijo sin gastar nada: los
primeros cuatro fallos - monigotes pequeños, sobraba cielo, las piernas
sentadas hacian un zigzag y el arbol parecia una flor - los vi yo antes de
enseñar nada.

La idea es suya, mirando un canal de 22.000 visitas dibujado con palotes:
"igual es mejor hacer imagenes mas simples como estas".
"""
from __future__ import annotations

import logging
import math
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

TINTA = (24, 22, 20)
TINTA_CLARA = (244, 238, 226)

# Sobre que fondos hay que dibujar con tinta CLARA. Lo encontre midiendo el
# movimiento: en 'noche' salia un 96% de fotogramas quietos y en 'campo' un
# 8%, con la misma animacion. No fallaba la animacion - fallaba que un
# monigote de tinta negra sobre un azul de noche no se ve. Si no lo detecta
# una resta de fotogramas, tampoco lo ve quien mira.
_FONDOS_OSCUROS = frozenset({"noche"})
ROJO = (214, 40, 40)
FONDOS = {
    "campo":  [(0.00, 0.40, (126, 196, 232)), (0.40, 1.00, (122, 193, 96))],
    "calle":  [(0.00, 0.42, (232, 214, 186)), (0.42, 1.00, (196, 176, 150))],
    "salon":  [(0.00, 0.70, (238, 222, 200)), (0.70, 1.00, (180, 150, 118))],
    "noche":  [(0.00, 0.64, (44, 56, 92)),    (0.64, 1.00, (58, 70, 58))],
    "liso":   [(0.00, 1.00, (243, 229, 213))],
}

def _jit(p, r, rnd):
    return (p[0] + rnd.uniform(-r, r), p[1] + rnd.uniform(-r, r))

def _linea(d, pts, g, rnd, color=TINTA, temblor=2.2):
    """Una polilinea con pulso, que es lo que la hace parecer dibujada."""
    finos = []
    for a, b in zip(pts, pts[1:]):
        n = max(2, int(math.dist(a, b) / 26))
        for i in range(n):
            t = i / n
            finos.append(_jit((a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t), temblor, rnd))
    finos.append(pts[-1])
    d.line(finos, fill=color, width=g, joint="curve")

def _circulo(d, c, r, g, rnd, relleno=(255,255,255), color=TINTA):
    pts = []
    for i in range(37):
        a = i/36*2*math.pi
        rr = r + rnd.uniform(-r*0.035, r*0.035)
        pts.append((c[0]+math.cos(a)*rr, c[1]+math.sin(a)*rr))
    if relleno: d.polygon(pts, fill=relleno)
    d.line(pts, fill=color, width=g, joint="curve")

# Poses: puntos en unidades de ALTURA de la figura, origen en los pies.
_POSES = {
    "de_pie":   {"cuello": (0, -.70), "cadera": (0, -.38),
                 "brazos": [[(0,-.66),(-.13,-.50),(-.17,-.33)], [(0,-.66),(.13,-.50),(.17,-.33)]],
                 "piernas":[[(0,-.38),(-.09,-.19),(-.11,0)],   [(0,-.38),(.09,-.19),(.11,0)]]},
    "sentado":  {"cuello": (0, -.46), "cadera": (0, -.09),
                 "brazos": [[(0,-.42),(-.14,-.30),(-.17,-.13)], [(0,-.42),(.15,-.31),(.21,-.15)]],
                 "piernas":[[(0,-.09),(.19,-.22),(.31,-.01)],   [(0,-.09),(.21,-.05),(.34,-.01)]]},
    "brazos_arriba": {"cuello": (0,-.70), "cadera": (0,-.38),
                 # Separados de la cabeza: pegados parecian un marco alrededor
                 # de la cara en vez de dos brazos en alto.
                 "brazos": [[(0,-.66),(-.26,-.76),(-.34,-.96)], [(0,-.66),(.26,-.76),(.34,-.96)]],
                 "piernas":[[(0,-.38),(-.10,-.19),(-.13,0)],    [(0,-.38),(.10,-.19),(.13,0)]]},
    "señala":   {"cuello": (0,-.70), "cadera": (0,-.38),
                 "brazos": [[(0,-.66),(-.12,-.52),(-.15,-.36)], [(0,-.66),(.20,-.64),(.34,-.62)]],
                 "piernas":[[(0,-.38),(-.09,-.19),(-.11,0)],    [(0,-.38),(.09,-.19),(.11,0)]]},
    # Sentado a una mesa: el tronco recto y los antebrazos hacia delante, que
    # es lo que queda ENCIMA del tablero cuando la mesa se pinta despues.
    "en_mesa":  {"cuello": (0,-.52), "cadera": (0,-.26),
                 "brazos": [[(0,-.48),(-.16,-.40),(-.26,-.34)], [(0,-.48),(.16,-.40),(.26,-.34)]],
                 "piernas":[[(0,-.26),(.16,-.26),(.20,-.02)],   [(0,-.26),(.09,-.25),(.11,-.02)]]},
    "corriendo":{"cuello": (0,-.68), "cadera": (0,-.37),
                 "brazos": [[(0,-.64),(-.20,-.56),(-.30,-.44)], [(0,-.64),(.18,-.58),(.30,-.64)]],
                 "piernas":[[(0,-.37),(-.22,-.22),(-.30,-.04)], [(0,-.37),(.16,-.18),(.30,-.10)]]},
    # La otra mitad de la zancada. Correr no es una postura, son dos que se
    # alternan: sin esto el monigote iba en plancha, deslizando.
    "corriendo_b":{"cuello": (0,-.68), "cadera": (0,-.37),
                 "brazos": [[(0,-.64),(.20,-.56),(.30,-.44)], [(0,-.64),(-.18,-.58),(-.30,-.64)]],
                 "piernas":[[(0,-.37),(.20,-.20),(.30,-.06)],  [(0,-.37),(-.18,-.20),(-.28,-.08)]]},
}

def _cara(d, c, r, g, rnd, gesto, tinta=TINTA):
    o = r*0.30
    ojo = max(3, int(r*0.10))
    for lado in (-1, 1):
        cx, cy = c[0]+lado*o, c[1]-r*0.12
        if gesto == "enfadado":
            _linea(d, [(cx-ojo*1.6, cy-ojo*1.8), (cx+ojo*1.6, cy-ojo*0.6)][::lado], g, rnd,
                   color=tinta, temblor=1)
        d.ellipse([cx-ojo, cy-ojo, cx+ojo, cy+ojo], fill=tinta)
    b = (c[0], c[1]+r*0.34)
    if gesto in ("sorpresa", "grito"):
        rr = r*(0.20 if gesto=="sorpresa" else 0.28)
        _circulo(d, b, rr, g, rnd, relleno=tinta, color=tinta)
    elif gesto == "contento":
        d.arc([b[0]-r*.34, b[1]-r*.34, b[0]+r*.34, b[1]+r*.20], 15, 165, fill=tinta, width=g)
    elif gesto == "enfadado":
        d.arc([b[0]-r*.30, b[1]-r*.06, b[0]+r*.30, b[1]+r*.42], 195, 345, fill=tinta, width=g)
    else:
        _linea(d, [(b[0]-r*.22, b[1]), (b[0]+r*.22, b[1])], g, rnd, color=tinta, temblor=1)


# ---- GORROS ----------------------------------------------------------------
# Lo que convierte a un monigote en ALGUIEN. Es todo lo que hace falta: nadie
# necesita una cara parecida para entender que ese es el cura y ese el general.

# Los que ENVUELVEN la cabeza se pintan ANTES que ella, o tapan la cara. Es
# el mismo asunto que la mesa: lo que rodea va detras, lo que se apoya encima
# va delante. La capucha de monje tapaba la cara entera.
GORROS_DETRAS = ("monje",)


def _gorro(d, cab, rc, g, rnd, cual):
    x, y = cab
    arriba = y - rc*0.88          # donde apoya, en la coronilla
    oro, rojo, azul = (214,164,40), ROJO, (58,84,150)

    if cual == "corona":
        b = rc*0.95
        _linea(d, [(x-b, arriba), (x-b*.5, arriba-rc*.62), (x, arriba-rc*.05),
                   (x+b*.5, arriba-rc*.62), (x+b, arriba)], g, rnd, color=oro)
    elif cual == "comandante":      # bicornio: el de Napoleon, se lee al vuelo
        _linea(d, [(x-rc*1.45, arriba-rc*.10), (x-rc*.30, arriba-rc*.95),
                   (x+rc*.30, arriba-rc*.95), (x+rc*1.45, arriba-rc*.10),
                   (x, arriba+rc*.16), (x-rc*1.45, arriba-rc*.10)], g, rnd, color=azul)
        d.line([(x, arriba-rc*.80), (x, arriba+rc*.10)], fill=rojo, width=g)
    elif cual == "tricornio":       # el XVIII español
        _linea(d, [(x-rc*1.35, arriba), (x, arriba-rc*.92), (x+rc*1.35, arriba),
                   (x, arriba+rc*.22), (x-rc*1.35, arriba)], g, rnd)
    elif cual == "sombrero":        # ala ancha, el del motin
        d.ellipse([x-rc*1.5, arriba-rc*.16, x+rc*1.5, arriba+rc*.16],
                  fill=(255,255,255), outline=TINTA, width=g)
        _linea(d, [(x-rc*.62, arriba), (x-rc*.56, arriba-rc*.78),
                   (x+rc*.56, arriba-rc*.78), (x+rc*.62, arriba)], g, rnd)
    elif cual == "casco":           # morrion de conquistador, con cresta
        _linea(d, [(x-rc*1.15, arriba+rc*.10), (x-rc*.80, arriba-rc*.62),
                   (x+rc*.80, arriba-rc*.62), (x+rc*1.15, arriba+rc*.10)], g, rnd)
        _linea(d, [(x-rc*.55, arriba-rc*.60), (x, arriba-rc*1.15),
                   (x+rc*.55, arriba-rc*.60)], g, rnd)
    elif cual == "mitra":           # obispo, Inquisicion
        _linea(d, [(x-rc*.78, arriba+rc*.08), (x-rc*.60, arriba-rc*.70),
                   (x, arriba-rc*1.45), (x+rc*.60, arriba-rc*.70),
                   (x+rc*.78, arriba+rc*.08), (x-rc*.78, arriba+rc*.08)], g, rnd)
        d.line([(x, arriba-rc*1.30), (x, arriba)], fill=oro, width=g)
    elif cual == "monje":           # capucha que ENVUELVE la cabeza
        pts = []
        for i in range(19):
            a = math.pi + i/18*math.pi          # media vuelta por arriba
            pts.append((x + math.cos(a)*rc*1.34,
                        y + math.sin(a)*rc*1.34 - rc*0.02))
        pts = [(x-rc*1.34, y+rc*0.78)] + pts + [(x+rc*1.34, y+rc*0.78)]
        d.polygon(pts, fill=(146, 116, 82))
        _linea(d, pts, g, rnd, color=(86, 64, 42), temblor=1.4)
    elif cual == "boina":
        _linea(d, [(x-rc*1.0, arriba+rc*.12), (x-rc*.7, arriba-rc*.55),
                   (x+rc*.7, arriba-rc*.55), (x+rc*1.0, arriba+rc*.12),
                   (x-rc*1.0, arriba+rc*.12)], g, rnd, color=rojo)
        d.line([(x+rc*.55, arriba-rc*.62), (x+rc*.75, arriba-rc*.88)], fill=rojo, width=g)
    elif cual == "marinero":        # gorro de pico
        _linea(d, [(x-rc*1.05, arriba+rc*.05), (x, arriba-rc*.75),
                   (x+rc*1.05, arriba+rc*.05)], g, rnd, color=azul)


def figura(d, x, suelo, alto, rnd, pose="de_pie", gesto="neutro", gorro=None, espejo=False,
           pose_mezclada=None, tinta=TINTA, relleno=(255, 255, 255), rasgos=None):
    p = pose_mezclada or _POSES[pose]
    s = -1 if espejo else 1
    # El ancho separa los brazos y las piernas del eje: la abuela es redonda y
    # el mandamas seco, y eso se ve de lejos. Antes solo engordaba el trazo.
    ancho = (rasgos or {}).get("ancho", 1.0)
    P = lambda t: (x + t[0]*alto*s*ancho, suelo + t[1]*alto)
    rasgos = rasgos or {}
    g = max(5, int(alto*0.022*(0.6 + 0.4*rasgos.get("ancho", 1.0))))
    rc = alto*0.145*rasgos.get("cabeza", 1.0)
    cuello = P(p["cuello"]); cadera = P(p["cadera"])
    _linea(d, [cuello, cadera], g, rnd, color=tinta)
    for m in p["brazos"] + p["piernas"]:
        _linea(d, [P(t) for t in m], g, rnd, color=tinta)
    cab = (cuello[0], cuello[1]-rc*0.95)
    if gorro in GORROS_DETRAS:
        _gorro(d, cab, rc, g, rnd, gorro)
    # El pelo va DETRAS de la cabeza, como la capucha: es lo que asoma por
    # los lados. Y por debajo del gorro, que es del papel de hoy.
    if rasgos.get("pelo", "nada") != "nada":
        _pelo(d, cab, rc, g, rnd, rasgos["pelo"], tinta=tinta)
    _circulo(d, cab, rc, g, rnd, relleno=relleno, color=tinta)
    _cara(d, cab, rc, g, rnd, gesto, tinta=tinta)
    # Y estos DELANTE de la cara, que es donde estan.
    if rasgos.get("barba"):
        _barba(d, cab, rc, g, rnd, tinta=tinta, relleno=relleno)
    if rasgos.get("parche"):
        _parche(d, cab, rc, g, rnd, tinta=tinta)
    if gorro and gorro not in GORROS_DETRAS:
        _gorro(d, cab, rc, g, rnd, gorro)
    return cab

def tachado(d, caja, rnd, g):
    x0,y0,x1,y1 = caja
    _linea(d, [(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)], g, rnd)
    _linea(d, [(x0,y0),(x1,y1)], int(g*1.7), rnd, color=ROJO, temblor=3)
    _linea(d, [(x1,y0),(x0,y1)], int(g*1.7), rnd, color=ROJO, temblor=3)

def arbol(d, x, suelo, alto, rnd):
    g = max(5, int(alto*0.05))
    _linea(d, [(x, suelo), (x, suelo-alto*0.70)], g, rnd, color=(112,78,48))
    c = (x, suelo-alto*0.92); r = alto*0.46
    for _ in range(9):
        cx = c[0] + rnd.uniform(-r*.55, r*.55); cy = c[1] + rnd.uniform(-r*.42, r*.42)
        rr = r * rnd.uniform(.34, .62)
        pts = [(cx+math.cos(i/17*2*math.pi)*rr*rnd.uniform(.82,1.18),
                cy+math.sin(i/17*2*math.pi)*rr*.8*rnd.uniform(.82,1.18)) for i in range(18)]
        pts.append(pts[0])
        d.line(pts, fill=(58,138,58), width=max(3,int(g*0.55)), joint="curve")

def escena(spec, w=1080, h=1920, semilla=0):
    rnd = random.Random(semilla)
    img = Image.new("RGB", (w, h), (255,255,255)); d = ImageDraw.Draw(img)
    for y0, y1, col in FONDOS[spec.get("fondo","liso")]:
        d.rectangle([0, int(h*y0), w, int(h*y1)], fill=col)
    suelo = int(h*spec.get("suelo", 0.66))
    g_base = max(4, int(w*0.006))
    _sembrar(d, w, h, suelo, spec.get("fondo", "liso"), random.Random(semilla + 77), g_base)
    if spec.get("arbol"): arbol(d, w*spec["arbol"], suelo, h*0.16, rnd)
    g = max(5, int(h*0.006))
    for t in spec.get("tachados", []):
        lado = w*t.get("tam", 0.17)
        cx, cy = w*t["x"], h*t["y"]
        tachado(d, (cx-lado/2, cy-lado/2, cx+lado/2, cy+lado/2), rnd, g)
    def _pinta_cosas(delante):
        for c in spec.get("cosas", []):
            f = COSAS.get(c.get("que"))
            if f is None or bool(c.get("delante")) != delante:
                continue
            tam = h*float(c.get("tam", 0.14))
            # y por defecto: apoyada en el suelo. El sol y las nubes van donde
            # se les diga, que es arriba.
            py = h*float(c["y"]) if c.get("y") is not None else suelo
            f(d, w*float(c.get("x", 0.5)), py, tam, rnd,
              max(4, int(w*0.006)), TINTA_CLARA if oscuro else TINTA)

    oscuro = spec.get("fondo") in _FONDOS_OSCUROS
    tinta = TINTA_CLARA if oscuro else TINTA
    relleno = (38, 44, 66) if oscuro else (255, 255, 255)
    _pinta_cosas(delante=False)
    for f in spec.get("figuras", []):
        alto_f = h*f.get("alto", 0.30)
        figura(d, w*f["x"], suelo + alto_f*_RESPIRACION*f.get("_bocanada", 0.0),
               alto_f, rnd,
               f.get("pose","de_pie"), f.get("gesto","neutro"),
               f.get("gorro"), f.get("espejo", False), f.get("pose_mezclada"),
               tinta=tinta, relleno=relleno, rasgos=REPARTO.get(f.get("quien") or ""))
    _pinta_cosas(delante=True)
    return img


def sombrero(d, c, ancho, rnd, g):
    """Sombrero de ala ancha: el objeto por el que ardio Madrid."""
    a = ancho
    d.ellipse([c[0]-a/2, c[1]-a*.10, c[0]+a/2, c[1]+a*.10], fill=(255,255,255), outline=TINTA, width=g)
    _linea(d, [(c[0]-a*.22, c[1]), (c[0]-a*.20, c[1]-a*.34),
               (c[0]+a*.20, c[1]-a*.34), (c[0]+a*.22, c[1])], g, rnd)

def capa(d, c, alto, rnd, g):
    a = alto
    _linea(d, [(c[0]-a*.28, c[1]-a*.46), (c[0]+a*.28, c[1]-a*.46),
               (c[0]+a*.42, c[1]+a*.46), (c[0]-a*.42, c[1]+a*.46),
               (c[0]-a*.28, c[1]-a*.46)], g, rnd)

def bocadillo(d, texto, c, ancho, rnd, apunta_a, fuente):
    alto = ancho*0.46
    x0, y0, x1, y1 = c[0]-ancho/2, c[1]-alto/2, c[0]+ancho/2, c[1]+alto/2
    g = max(5, int(ancho*0.012))
    d.rounded_rectangle([x0,y0,x1,y1], radius=int(alto*0.32), fill=(255,255,255), outline=TINTA, width=g)
    rabo = [(c[0]-ancho*.10, y1-g), (apunta_a[0], apunta_a[1]), (c[0]+ancho*.10, y1-g)]
    d.polygon(rabo, fill=(255,255,255)); _linea(d, rabo, g, rnd, temblor=1.2)
    d.rounded_rectangle([x0+g,y0+g,x1-g,y1-g], radius=int(alto*0.30), fill=(255,255,255))
    caja = d.textbbox((0,0), texto, font=fuente)
    d.text((c[0]-(caja[2]-caja[0])/2, c[1]-(caja[3]-caja[1])/2-caja[1]), texto, font=fuente, fill=TINTA)


# ---- MOVIMIENTO ------------------------------------------------------------
# Esto es lo que el dibujo por IA no podia hacer de ninguna manera: una pose es
# una lista de PUNTOS, asi que entre dos poses hay infinitas intermedias. Se
# interpolan y el monigote se mueve de verdad, no es un zoom sobre una foto
# quieta.

def _mezcla(a, b, t):
    """Una pose intermedia entre dos, con t de 0 a 1."""
    suave = t*t*(3 - 2*t)          # arranca y frena, no a tiron
    lerp = lambda p, q: (p[0]+(q[0]-p[0])*suave, p[1]+(q[1]-p[1])*suave)
    return {
        "cuello": lerp(a["cuello"], b["cuello"]),
        "cadera": lerp(a["cadera"], b["cadera"]),
        "brazos": [[lerp(p, q) for p, q in zip(ma, mb)]
                   for ma, mb in zip(a["brazos"], b["brazos"])],
        "piernas": [[lerp(p, q) for p, q in zip(ma, mb)]
                    for ma, mb in zip(a["piernas"], b["piernas"])],
    }


def _decorado(paso, semilla):
    """El sitio donde pasa la escena, elegido por NOMBRE.

    Esto faltaba y era grave: animar() llamaba siempre a interior(), que es el
    monasterio, para cualquier interior. O sea que la taberna estaba
    construida, probada y enseñada... y no se dibujaba nunca. El guion podia
    pedir "taberna" y salia un refectorio.
    """
    if paso.get("interior"):
        return montar(paso, _ANCHO_BASE, _ALTO_BASE, semilla=semilla)
    return escena(paso, semilla=semilla)


def _fuente(alto_img):
    from PIL import ImageFont
    import glob
    for patron in ("/usr/share/fonts/**/DejaVuSans-Bold.ttf",
                   "/usr/share/fonts/**/*Bold*.ttf"):
        for f in glob.glob(patron, recursive=True):
            try:
                return ImageFont.truetype(f, max(22, int(alto_img*0.030)))
            except Exception:
                continue
    return ImageFont.load_default()


def _pinta_bocadillo(img, texto, apunta_x, rnd):
    """El globo, DENTRO del propio dibujo.

    Antes se pegaba con ffmpeg encima del plano ya montado. Aqui sale mejor y
    mas simple: como los fotogramas se dibujan de uno en uno y se sabe el
    segundo de cada uno, el globo se pinta solo en los que tocan. La
    sincronia es exacta por construccion, sin filtros ni ventanas.
    """
    w, h = img.size
    d = ImageDraw.Draw(img)
    f = _fuente(h)
    # Que quepa: se parte en lineas antes de dibujar nada.
    palabras, lineas, linea = texto.split(), [], ""
    for p in palabras:
        if d.textlength((linea + " " + p).strip(), font=f) > w*0.68:
            lineas.append(linea.strip()); linea = p
        else:
            linea = (linea + " " + p).strip()
    if linea:
        lineas.append(linea)
    lineas = lineas[:3]
    alto_linea = f.size*1.32
    ancho = max(w*0.30, max(d.textlength(l, font=f) for l in lineas) + w*0.10)
    alto = alto_linea*len(lineas) + h*0.022
    cx, cy = w*0.50, h*0.155
    x0, y0, x1, y1 = cx-ancho/2, cy-alto/2, cx+ancho/2, cy+alto/2
    g = max(4, int(w*0.006))
    d.rounded_rectangle([x0, y0, x1, y1], radius=int(alto*0.30),
                        fill=(255, 255, 255), outline=TINTA, width=g)
    rabo = [(cx-ancho*.09, y1-g//2), (apunta_x, y1 + h*0.075), (cx+ancho*.09, y1-g//2)]
    d.polygon(rabo, fill=(255, 255, 255))
    _linea(d, rabo, g, rnd, temblor=1.0)
    d.line([(cx-ancho*.09, y1-g//2), (cx+ancho*.09, y1-g//2)], fill=(255,255,255), width=g)
    for i, l in enumerate(lineas):
        d.text((cx - d.textlength(l, font=f)/2,
                cy - alto_linea*len(lineas)/2 + i*alto_linea), l, font=f, fill=TINTA)
    return img


# Cada cuanto se repite el movimiento. ESTE ERA EL FALLO del video #84: el
# personaje iba de una pose a otra UNA vez, estirada a lo largo de los cinco
# segundos del plano - y con suavizado al entrar y al salir, asi que se
# pasaba la mayor parte del plano casi quieto. Eso no es animacion, es una
# foto deformandose despacio. Ella lo dijo en dos palabras: "se tiene que
# mover mas".
#
# Segundo y cuarto es el ritmo de un gesto humano: levantar el brazo, bajarlo.
# En un plano de cinco segundos eso son cuatro repeticiones en vez de media.
_SEGUNDOS_POR_CICLO = 1.25

# Nadie esta nunca completamente quieto. Un personaje que no cambia de pose
# sigue respirando y balanceandose un poco, y cada uno con su propio compas -
# si van todos a la vez parecen un coro y canta muchisimo.
_RESPIRACION = 0.012      # de la altura de la figura
_SEGUNDOS_RESPIRACION = 2.3


def animar(spec, segundos=2.5, fps=15, vaiven=True, bocadillo=None):
    """Los fotogramas de una escena donde cada figura va de 'pose' a 'pose_fin'.

    El temblor de la linea cambia cada tres fotogramas y no cada uno: cada uno
    parpadea y marea, y quieto parece un PDF. Tres es el hervor de la
    animacion dibujada a mano de toda la vida.
    """
    total = max(2, int(segundos*fps))
    fotogramas = []
    for n in range(total):
        reloj = n/fps
        # El movimiento se REPITE cada ciclo en vez de estirarse por el plano.
        t = (reloj % _SEGUNDOS_POR_CICLO)/_SEGUNDOS_POR_CICLO
        if vaiven:
            t = 1 - abs(1 - 2*t)   # va y vuelve, para que el bucle no salte
        paso = dict(spec)
        paso["figuras"] = []
        for k, f in enumerate(spec.get("figuras", [])):
            g = dict(f)
            fin = f.get("pose_fin")
            # Cada figura con su propio desfase: si el movimiento de las tres
            # empieza en el mismo fotograma parecen marionetas de un hilo.
            desfase = k*0.37
            tk = (reloj/_SEGUNDOS_POR_CICLO + desfase) % 1.0
            tk = 1 - abs(1 - 2*tk) if vaiven else tk
            # Andar o correr se anima SOLO: son ciclos, no un gesto. Si el
            # guion no pide a donde va, la pierna alterna igual.
            if not fin and f.get("pose") == "corriendo":
                fin = "corriendo_b"
            if fin and fin != f.get("pose"):
                g["pose_mezclada"] = _mezcla(_POSES[f.get("pose","de_pie")], _POSES[fin], tk)
            # RESPIRACION: sube y baja un poco aunque no cambie de pose.
            g["_bocanada"] = math.sin(2*math.pi*(reloj/_SEGUNDOS_RESPIRACION + desfase))
            paso["figuras"].append(g)
        rnd = random.Random(1000 + n//3)
        img = _decorado(paso, semilla=1000 + n//3)
        if bocadillo:
            ahora = n/fps
            if bocadillo["desde"] <= ahora <= bocadillo["hasta"]:
                quien = bocadillo.get("x", 0.5)
                img = _pinta_bocadillo(img, bocadillo["texto"], img.size[0]*quien, rnd)
        fotogramas.append(img)
    return fotogramas


# ---- LO QUE EL GUION PUEDE PEDIR -------------------------------------------
# Vocabulario CERRADO a proposito. El guion elige de estas listas y de ninguna
# otra: si pide "fondo: catedral gotica al atardecer" no hay nada que dibujar,
# y una escena que no se puede dibujar es un hueco en el video. Lo que no se
# reconoce no rompe nada, se sustituye por lo mas parecido y se apunta.
FONDOS_VALIDOS = tuple(FONDOS)
POSES_VALIDAS = tuple(p for p in _POSES if p != "corriendo_b")
GESTOS_VALIDOS = ("neutro", "sorpresa", "contento", "enfadado", "grito")
GORROS_VALIDOS = ("corona", "comandante", "tricornio", "sombrero", "casco",
                  "mitra", "monje", "boina", "marinero")
OBJETOS_VALIDOS = ("sombrero", "capa")
# Se rellena abajo, con las recetas: asi no puede haber una lista de sitios
# que ofrezco al guion y otra de sitios que se saben dibujar.
INTERIORES_VALIDOS: tuple = ()

_MAX_FIGURAS = 4

# Lo minimo que tienen que separarse dos cosas en horizontal, en pantallas.
_SEPARACION = 0.13


def _una_de(valor, validas, por_defecto):
    v = (valor or "").strip().lower()
    return v if v in validas else por_defecto


def limpia(spec: dict) -> dict:
    """La escena que ha pedido el guion, dejada en algo que se sabe dibujar."""
    if not isinstance(spec, dict):
        return {"fondo": "liso", "figuras": [{"x": 0.5, "pose": "de_pie"}]}
    figuras = []
    crudas = spec.get("figuras")
    for f in (crudas if isinstance(crudas, list) else [])[:_MAX_FIGURAS]:
        if not isinstance(f, dict):
            continue
        gorro = (f.get("gorro") or "").strip().lower()
        # El personaje del reparto trae su estatura consigo: el mandamas es
        # alto y la abuela bajita SIEMPRE, en todos los videos. Si el guion
        # pide otra cosa se ignora, porque eso es justo lo que romperia que se
        # les reconozca.
        quien = (f.get("quien") or "").strip().lower()
        quien = quien if quien in REPARTO else None
        por_defecto = REPARTO[quien]["alto"] if quien else 0.34
        figuras.append({
            "quien": quien,
            "x": min(0.88, max(0.12, float(f.get("x", 0.5) or 0.5))),
            "alto": por_defecto if quien else min(
                0.46, max(0.18, float(f.get("alto", 0.34) or 0.34))),
            "pose": _una_de(f.get("pose"), POSES_VALIDAS, "de_pie"),
            "pose_fin": (_una_de(f.get("pose_fin"), POSES_VALIDAS, "")
                         if f.get("pose_fin") else None),
            "gesto": _una_de(f.get("gesto"), GESTOS_VALIDOS, "neutro"),
            "gorro": gorro if gorro in GORROS_VALIDOS else None,
            "espejo": bool(f.get("espejo")),
        })
    if not figuras:
        # Una escena sin nadie es un fondo de color. Antes que eso, alguien.
        figuras = [{"x": 0.5, "alto": 0.34, "pose": "de_pie", "pose_fin": None,
                    "gesto": "neutro", "gorro": None, "espejo": False}]
    tachados = []
    for t in (spec.get("tachados") if isinstance(spec.get("tachados"), list) else [])[:3]:
        if isinstance(t, dict):
            tachados.append({"x": min(0.9, max(0.1, float(t.get("x", 0.5) or 0.5))),
                             "y": min(0.5, max(0.12, float(t.get("y", 0.28) or 0.28))),
                             "tam": min(0.26, max(0.10, float(t.get("tam", 0.18) or 0.18)))})
    # El interior manda sobre el fondo: si el guion pide "monasterio" no hay
    # que mirar el fondo plano. Se me colaba porque limpia() se comia la clave
    # entera y el monasterio salia como campo liso.
    dentro = (spec.get("interior") or "").strip().lower()
    dentro = dentro if dentro in INTERIORES_VALIDOS else None
    # El tope se cuenta sobre las cosas BUENAS, no sobre lo que llega. Con el
    # tope arriba, un "dragon" que no se sabe dibujar ocupaba el sitio de una
    # casa que si: se pedian cinco, se colaban dos malas y se perdia la buena.
    cosas = []
    for c in (spec.get("cosas") if isinstance(spec.get("cosas"), list) else []):
        if len(cosas) >= 4:
            break
        if not isinstance(c, dict):
            continue
        que = (c.get("que") or "").strip().lower()
        if que not in COSAS or COSAS[que] is None:
            continue
        cosas.append({"que": que,
                      "x": min(0.95, max(0.05, float(c.get("x", 0.5) or 0.5))),
                      "y": (min(0.95, max(0.05, float(c["y"]))) 
                            if c.get("y") is not None else None),
                      "tam": min(0.34, max(0.05, float(c.get("tam", 0.14) or 0.14))),
                      "delante": bool(c.get("delante"))})
    # QUE NO SE PISEN. El guion elige la x de cada cosa y de cada persona sin
    # ver el resultado, asi que dos acaban en el mismo sitio: en la primera
    # prueba el perro salio DEBAJO del cañon. Aqui se separan, que es algo que
    # el dibujo puede garantizar y el guion no.
    # Se busca el hueco LIBRE mas cercano al sitio que pidio el guion. Mi
    # primer intento empujaba a un lado y a otro segun con quien chocara, y
    # rebotaba: el perro iba del cañon al soldado y vuelta, doce veces, y se
    # quedaba encima del cañon igual. Buscar en vez de empujar no puede
    # oscilar.
    ocupadas = [f["x"] for f in figuras]
    for c in cosas:
        if c["y"] is not None:          # lo del cielo no estorba a nadie
            continue
        libre = lambda px: all(abs(o - px) >= _SEPARACION for o in ocupadas)
        if not libre(c["x"]):
            sitios = [0.05 + 0.02*k for k in range(46)]
            candidato = min((p for p in sitios if libre(p)),
                            key=lambda p: abs(p - c["x"]), default=None)
            if candidato is not None:
                c["x"] = round(candidato, 3)
        ocupadas.append(c["x"])

    return {"interior": dentro, "cosas": cosas,
            "fondo": _una_de(spec.get("fondo"), FONDOS_VALIDOS, "liso"),
            "suelo": min(0.86, max(0.58, float(spec.get("suelo", 0.70 if dentro else 0.74)
                                              or 0.74))),
            "figuras": figuras, "tachados": tachados,
            "arbol": spec.get("arbol") if isinstance(spec.get("arbol"), (int, float)) else None}


_ANCHO_BASE, _ALTO_BASE = 1080, 1920

# La camara. Con las ilustraciones de IA habia al menos un zoom lento; con los
# monigotes el plano se quedo clavado del todo, y un plano clavado se nota
# aunque dentro haya movimiento. Un empuje del 7% y una deriva lateral: poco,
# pero quita la sensacion de foto.
_EMPUJE = 0.045


def _camara(img, t):
    """El recorte de este instante: entra despacio y deriva un poco."""
    w, h = img.size
    zoom = 1.0 + _EMPUJE*t
    cw, ch = w/zoom, h/zoom
    # La deriva va hacia el centro, asi que el plano se cierra sobre la accion.
    x = (w-cw)*(0.5 + 0.30*math.cos(math.pi*t))
    y = (h-ch)*0.5
    return img.crop((int(x), int(y), int(x+cw), int(y+ch)))
_FPS = 15


def render(spec: dict, out_path: Path, ancho: int, alto: int,
           segundos: float, bocadillo: dict | None = None) -> Path | None:
    """La escena, ya montada como clip de video de la duracion que se pida.

    Devuelve None si algo falla, nunca revienta: una escena sin clip cae en la
    cadena de siempre (foto real, imagen del articulo, archivo), que es lo que
    hace que un fallo aqui cueste un plano y no el video.
    """
    try:
        limpio = limpia(spec)
        segundos = max(1.0, min(12.0, float(segundos)))
        fotogramas = animar(limpio, segundos=segundos, fps=_FPS,
                            bocadillo=bocadillo)
        carpeta = Path(out_path).with_suffix("")
        carpeta.mkdir(parents=True, exist_ok=True)
        for i, img in enumerate(fotogramas):
            _camara(img, i/max(1, len(fotogramas)-1)).resize(
                (ancho, alto), Image.LANCZOS).save(carpeta / f"{i:04d}.png")
        orden = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(_FPS),
                 "-i", str(carpeta / "%04d.png"),
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                 "-r", "30", str(out_path)]
        subprocess.run(orden, check=True, capture_output=True, timeout=180)
        # Un fotograma suelto para la miniatura. La lista de 'retratos' la lee
        # thumbnail.py con PIL, y un mp4 ahi dentro es una excepcion: la
        # portada de un video de monigotes tiene que ser un monigote.
        medio = _camara(fotogramas[len(fotogramas)//2], 0.5).resize(
            (ancho, alto), Image.LANCZOS)
        medio.save(Path(out_path).with_suffix(".jpg"), quality=92)
        for f in carpeta.glob("*.png"):
            f.unlink()
        carpeta.rmdir()
        quienes = ", ".join(
            f"{f['pose']}{'->' + f['pose_fin'] if f['pose_fin'] else ''}"
            f"{'/' + f['gorro'] if f['gorro'] else ''}" for f in limpio["figuras"])
        logger.info("Monigotes: %s en %r, %.1fs (%s).", quienes,
                    limpio.get("interior") or limpio["fondo"], segundos, out_path.name)
        return Path(out_path)
    except Exception:
        logger.warning("No se ha podido dibujar la escena de monigotes.", exc_info=True)
        return None


# ---- DECORADOS -------------------------------------------------------------
# Un fondo de dos bandas de color vale para un campo o una calle, y no vale
# para un sitio: un refectorio, una taberna, un salon del trono. Lo que hace
# que parezca una habitacion y no unas pegatinas sobre un color es el ORDEN:
#
#   pared -> ventana -> velas -> bancos -> FIGURAS -> LA MESA DELANTE -> loza
#
# La mesa se pinta DESPUES de la gente. Por eso los brazos se apoyan encima y
# las piernas quedan debajo, que es lo que se ve en cualquier escena de estas
# bien hecha.

PIEDRA = (150, 144, 134)
MADERA = (150, 106, 62)
MADERA_OSCURA = (112, 78, 44)


def _pared_piedra(d, w, h, suelo, rnd):
    d.rectangle([0, 0, w, suelo], fill=PIEDRA)
    d.rectangle([0, suelo, w, h], fill=(108, 100, 92))
    g = max(3, int(w*0.0045))
    for _ in range(30):
        bw = rnd.uniform(w*.05, w*.13); bh = bw*rnd.uniform(.32, .52)
        bx = rnd.uniform(0, w-bw); by = rnd.uniform(0, suelo-bh)
        _linea(d, [(bx,by),(bx+bw,by),(bx+bw,by+bh),(bx,by+bh),(bx,by)], g, rnd,
               color=(104, 98, 90), temblor=1.8)


def _resplandor(img, c, r, color=(255, 214, 120)):
    """El halo de una vela. Va en su propia capa porque necesita transparencia."""
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dd = ImageDraw.Draw(capa)
    for k in range(7, 0, -1):
        rr = r*k/7
        dd.ellipse([c[0]-rr, c[1]-rr, c[0]+rr, c[1]+rr], fill=color + (12,))
    return Image.alpha_composite(img.convert("RGBA"), capa).convert("RGB")


def _vela(d, x, y, alto, rnd, g):
    _linea(d, [(x-alto*.16, y), (x-alto*.16, y-alto), (x+alto*.16, y-alto),
               (x+alto*.16, y), (x-alto*.16, y)], g, rnd, temblor=1.2)
    d.rectangle([x-alto*.15, y-alto*.98, x+alto*.15, y-2], fill=(248, 244, 232))
    llama = [(x, y-alto*1.44), (x+alto*.14, y-alto*1.06), (x, y-alto*.98),
             (x-alto*.14, y-alto*1.06), (x, y-alto*1.44)]
    d.polygon(llama, fill=(250, 176, 60)); _linea(d, llama, max(2, g//2), rnd, temblor=1)


def _ventana_arco(d, cx, cy, ancho, alto, rnd, g):
    izq, der = cx-ancho/2, cx+ancho/2
    arco = cy-alto/2
    d.rounded_rectangle([izq, arco, der, cy+alto/2], radius=int(ancho*0.48),
                        fill=(38, 44, 86), outline=TINTA, width=g)
    d.rectangle([izq+g, cy, der-g, cy+alto/2-g], fill=(38, 44, 86))
    d.polygon([(izq+g, cy+alto/2-g), (cx-ancho*.16, cy), (cx+ancho*.10, cy+alto*.18),
               (der-g, cy+alto*.06), (der-g, cy+alto/2-g)], fill=(62, 74, 106))
    luna = (cx-ancho*.14, arco+alto*.22); rl = ancho*.13
    d.ellipse([luna[0]-rl, luna[1]-rl, luna[0]+rl, luna[1]+rl], fill=(248, 232, 150))
    d.ellipse([luna[0]-rl*1.5, luna[1]-rl*1.25, luna[0]+rl*.55, luna[1]+rl*1.25],
              fill=(38, 44, 86))
    for _ in range(6):
        ex, ey = rnd.uniform(izq+ancho*.18, der-ancho*.12), rnd.uniform(arco+alto*.10, cy-alto*.06)
        re = ancho*rnd.uniform(.022, .040)
        d.polygon([(ex, ey-re), (ex+re*.34, ey-re*.34), (ex+re, ey), (ex+re*.34, ey+re*.34),
                   (ex, ey+re), (ex-re*.34, ey+re*.34), (ex-re, ey), (ex-re*.34, ey-re*.34)],
                  fill=(250, 226, 130))


def _banco(d, x, y, ancho, rnd, g):
    alto = ancho*0.34
    _linea(d, [(x-ancho/2, y-alto), (x+ancho/2, y-alto), (x+ancho/2, y-alto*.70),
               (x-ancho/2, y-alto*.70), (x-ancho/2, y-alto)], g, rnd, temblor=1.4)
    d.rectangle([x-ancho/2+g, y-alto+g, x+ancho/2-g, y-alto*.70-g], fill=MADERA)
    for lado in (-1, 1):
        px = x + lado*ancho*.36
        _linea(d, [(px, y-alto*.70), (px, y)], int(g*2.2), rnd, color=MADERA_OSCURA, temblor=1.2)


def _mesa(d, y, ancho_img, rnd, g):
    """La mesa, DELANTE de la gente. Ese es todo el truco."""
    x0, x1 = ancho_img*0.10, ancho_img*0.90
    grosor = ancho_img*0.030
    _linea(d, [(x0, y), (x1, y), (x1, y+grosor), (x0, y+grosor), (x0, y)], g, rnd, temblor=1.6)
    d.rectangle([x0+g, y+g, x1-g, y+grosor-g], fill=MADERA)
    for px in (x0+ancho_img*.06, ancho_img*.50, x1-ancho_img*.06):
        _linea(d, [(px, y+grosor), (px, y+grosor+ancho_img*0.22)], int(g*2.6), rnd,
               color=MADERA_OSCURA, temblor=1.2)


def _cuenco(d, x, y, ancho, rnd, g):
    """El cuenco se APOYA en el tablero: base en y, cuerpo hacia arriba.

    Lo tenia centrado en y, o sea medio cuenco flotando por encima de las
    caras y el otro medio colgando por debajo de la mesa como un pendulo."""
    boca = y - ancho*0.42
    d.chord([x-ancho/2, boca-ancho*.30, x+ancho/2, y], 0, 180,
            fill=(146, 104, 58), outline=TINTA, width=g)
    for _ in range(30):
        a = rnd.uniform(0, 6.283); rr = rnd.uniform(0, ancho*.40)
        bx = x + math.cos(a)*rr
        by = boca - ancho*.10 + math.sin(a)*rr*.22
        rb = ancho*.052
        d.ellipse([bx-rb, by-rb, bx+rb, by+rb], fill=(168, 34, 44), outline=(120,20,28))
    d.ellipse([x-ancho/2, boca-ancho*.17, x+ancho/2, boca+ancho*.17],
              fill=None, outline=TINTA, width=g)


def _jarra(d, x, y, alto, rnd, g):
    _linea(d, [(x-alto*.34, y-alto), (x+alto*.34, y-alto), (x+alto*.28, y),
               (x-alto*.28, y), (x-alto*.34, y-alto)], g, rnd, temblor=1.2)
    d.polygon([(x-alto*.32, y-alto*.94), (x+alto*.32, y-alto*.94),
               (x+alto*.26, y-g), (x-alto*.26, y-g)], fill=(198, 152, 104))
    d.arc([x+alto*.20, y-alto*.80, x+alto*.62, y-alto*.30], 290, 70, fill=TINTA, width=g)


# Los sitios que se saben montar: el guion elige por NOMBRE, no describe una
# catedral gotica al atardecer. INTERIORES_VALIDOS esta arriba, con el resto
# del vocabulario.
def interior(spec: dict, w: int, h: int, semilla: int = 0):
    """Una habitacion de verdad, montada por capas."""
    rnd = random.Random(semilla)
    sitio = spec.get("interior", "monasterio")
    suelo = int(h*spec.get("suelo", 0.70))
    img = Image.new("RGB", (w, h), PIEDRA)
    d = ImageDraw.Draw(img)
    g = max(4, int(w*0.006))

    _pared_piedra(d, w, h, suelo, rnd)
    if sitio in ("monasterio", "taberna"):
        # En vertical el quinto de arriba es del bocadillo, asi que la ventana
        # baja. En apaisado cabe arriba sin estorbar.
        vertical = h > w
        _ventana_arco(d, w*0.50, h*(0.36 if vertical else 0.23),
                      w*(0.20 if vertical else 0.155),
                      h*(0.17 if vertical else 0.30), rnd, g)

    # Velas en repisas. Se apuntan y su halo se compone al final, porque la
    # transparencia tiene que ir sobre TODO lo que ya esta pintado.
    velas = []
    for x, y in ((0.10, 0.20), (0.27, 0.16), (0.78, 0.19), (0.92, 0.26)):
        cx, cy = w*x, h*y
        _linea(d, [(cx-w*.055, cy), (cx+w*.055, cy)], int(g*1.8), rnd, color=MADERA_OSCURA)
        _vela(d, cx, cy, h*0.042, rnd, g)
        velas.append((cx, cy - h*0.030))

    linea_mesa = suelo - h*0.02
    for f in spec.get("figuras", []):
        alto_f = h*f.get("alto", 0.30)
        figura(d, w*f["x"],
               linea_mesa + h*0.075 + alto_f*_RESPIRACION*f.get("_bocanada", 0.0),
               alto_f, rnd,
               f.get("pose", "en_mesa"), f.get("gesto", "neutro"),
               f.get("gorro"), f.get("espejo", False), f.get("pose_mezclada"),
               rasgos=REPARTO.get(f.get("quien") or ""))

    _mesa(d, linea_mesa, w, rnd, g)                      # DELANTE de la gente
    _cuenco(d, w*0.50, linea_mesa, w*0.11, rnd, g)
    for x in (0.26, 0.38, 0.70):
        _jarra(d, w*x, linea_mesa + h*0.004, h*0.035, rnd, g)
    _vela(d, w*0.62, linea_mesa, h*0.035, rnd, g)
    velas.append((w*0.62, linea_mesa - h*0.025))

    for c in velas:
        img = _resplandor(img, c, h*0.075)
    return img


# ---- EL REPARTO ------------------------------------------------------------
# Idea suya, y es la que puede hacer el canal: "que sean los mismos entre
# video y video, para que el espectador los reconozca aunque esten en una
# historia diferente".
#
# La gente vuelve a un canal por la GENTE, no por el tema. Si siempre sale el
# mismo viejo del bigote, aunque hoy este en Lepanto y mañana en un motin, se
# vuelve "el canal ese del viejo". Eso no se consigue con el gorro, porque el
# gorro es el PAPEL y cambia en cada historia: hace falta algo que no cambie
# nunca - el pelo, el bigote, la estatura, la forma de la cabeza.
#
# Son cinco y estan pensados para cubrir cualquier escena de historia de
# España sin repetirse: quien manda, quien obedece, quien lo cuenta, quien lo
# sufre y quien se aprovecha.
REPARTO = {
    # El que siempre esta. Es el testigo, los ojos del espectador: se asoma,
    # se escandaliza, comenta. Sale en TODOS los videos.
    "cronista": {"alto": 0.38, "cabeza": 0.95, "ancho": 1.0,
                 "pelo": "raya", "barba": True},
    # La que no se calla. Bajita, redonda, moño.
    "abuela":   {"alto": 0.25, "cabeza": 1.12, "ancho": 1.25,
                 "pelo": "moño"},
    # El que se mete donde no le llaman.
    "chaval":   {"alto": 0.21, "cabeza": 1.05, "ancho": 0.9,
                 "pelo": "punta"},
    # El que manda, o el que cree que manda. Alto y seco.
    "mandamas": {"alto": 0.45, "cabeza": 0.90, "ancho": 0.95,
                 "pelo": "nada", "barba": True},
    # El que se lleva los palos. Ancho, con un ojo tapado.
    "soldado":  {"alto": 0.32, "cabeza": 1.0, "ancho": 1.3,
                 "pelo": "tonsura", "parche": True},
}
REPARTO_VALIDO = tuple(REPARTO)


def _pelo(d, cab, rc, g, rnd, cual, tinta=TINTA):
    """Lo que no cambia nunca, por debajo del gorro del dia."""
    x, y = cab
    if cual == "raya":                       # dos mechones que ASOMAN
        for lado in (-1, 1):
            _linea(d, [(x+lado*rc*0.70, y-rc*0.78),
                       (x+lado*rc*1.24, y-rc*0.20),
                       (x+lado*rc*1.16, y+rc*0.46)], g, rnd, color=tinta, temblor=1.8)
    elif cual == "moño":
        c = (x, y-rc*1.18)
        _circulo(d, c, rc*0.42, g, rnd, relleno=None, color=tinta)
        _linea(d, [(x-rc*.55, y-rc*.80), (x, y-rc*.96), (x+rc*.55, y-rc*.80)], g, rnd,
               color=tinta, temblor=1.4)
    elif cual == "punta":
        for k in (-1, 0, 1):
            _linea(d, [(x+k*rc*0.42, y-rc*0.88),
                       (x+k*rc*0.52, y-rc*1.34)], g, rnd, color=tinta, temblor=2.2)
    elif cual == "tonsura":                  # calva con corona de pelo
        for lado in (-1, 1):
            _linea(d, [(x+lado*rc*0.82, y-rc*0.52),
                       (x+lado*rc*1.22, y-rc*0.06),
                       (x+lado*rc*1.10, y+rc*0.52)], g, rnd, color=tinta, temblor=1.8)


def _barba(d, cab, rc, g, rnd, tinta=TINTA, relleno=(255, 255, 255)):
    """Una barba que CUELGA por debajo de la cabeza.

    Empece con bigote y no cabe: en una cara de monigote, del tamaño de una
    moneda en pantalla, un bigote se come la boca y se lee como un
    manchurron. Probado dos veces - primero parecian sonreir, luego parecian
    tristes. La barba va por FUERA del circulo de la cabeza, asi que no pisa
    ni los ojos ni la boca, y se reconoce a un metro del movil.
    """
    pts = []
    for i in range(15):
        a = i/14*math.pi                       # media vuelta por abajo
        pts.append((cab[0] + math.cos(math.pi - a)*rc*0.92,
                    cab[1] + math.sin(a)*rc*1.55 + rc*0.18))
    contorno = [(cab[0]-rc*0.92, cab[1]+rc*0.18)] + pts + [(cab[0]+rc*0.92, cab[1]+rc*0.18)]
    d.polygon(contorno, fill=relleno)
    _linea(d, contorno, g, rnd, color=tinta, temblor=2.0)


def _parche(d, cab, rc, g, rnd, tinta=TINTA):
    ojo = (cab[0]-rc*0.30, cab[1]-rc*0.12)
    r = rc*0.26
    d.ellipse([ojo[0]-r, ojo[1]-r, ojo[0]+r, ojo[1]+r], fill=tinta)
    _linea(d, [(cab[0]-rc*.95, cab[1]-rc*.42), (cab[0]+rc*.85, cab[1]-rc*.02)],
           max(2, g//2), rnd, color=tinta, temblor=1.2)


# ---- LAS COSAS -------------------------------------------------------------
# "Si habla de perro dibuja un perro". Es lo que le faltaba a la escena para
# contar algo: los monigotes ponen quien, el fondo pone donde, y esto pone DE
# QUE se esta hablando. Un plano con un barco ardiendo dice mas que tres
# monigotes gesticulando en un campo vacio.
#
# Todas se dibujan apoyadas en su base, como se apoya una cosa en el suelo, y
# con el mismo pulso tembloroso que el resto: si una sale con linea limpia
# canta que es de otro sitio.

def _perro(d, x, y, t, rnd, g, tinta=TINTA):
    """De perfil, con hocico. El primero salia como un bicho: la cabeza era un
    circulo suelto con una raya saliendo."""
    lomo = [(x-t*.46, y-t*.34), (x-t*.10, y-t*.40), (x+t*.28, y-t*.36)]
    _linea(d, lomo, g, rnd, color=tinta)
    _linea(d, [(x-t*.46, y-t*.34), (x-t*.40, y-t*.14), (x+t*.24, y-t*.14),
               (x+t*.28, y-t*.36)], g, rnd, color=tinta)
    for px in (-.38, -.20, .06, .22):
        _linea(d, [(x+t*px, y-t*.15), (x+t*px+t*.02, y)], g, rnd, color=tinta)
    _linea(d, [(x+t*.28, y-t*.36), (x+t*.44, y-t*.58)], g, rnd, color=tinta)
    cab = (x+t*.52, y-t*.66)
    _circulo(d, cab, t*.15, g, rnd, relleno=(255, 255, 255), color=tinta)
    hocico = [(cab[0]+t*.06, cab[1]-t*.02), (cab[0]+t*.30, cab[1]+t*.02),
              (cab[0]+t*.30, cab[1]+t*.12), (cab[0]+t*.04, cab[1]+t*.12)]
    d.polygon(hocico, fill=(255, 255, 255)); _linea(d, hocico, g, rnd, color=tinta)
    d.ellipse([cab[0]+t*.26, cab[1]+t*.01, cab[0]+t*.34, cab[1]+t*.09], fill=tinta)
    _linea(d, [(cab[0]-t*.08, cab[1]-t*.13), (cab[0]-t*.20, cab[1]+t*.14)], g, rnd, color=tinta)
    d.ellipse([cab[0]-t*.04, cab[1]-t*.06, cab[0]+t*.02, cab[1]], fill=tinta)
    _linea(d, [(x-t*.46, y-t*.34), (x-t*.64, y-t*.60)], g, rnd, color=tinta)


def _caballo(d, x, y, t, rnd, g, tinta=TINTA):
    """La cabeza era un bloque cuadrado flotando. Ahora es una cuña pegada al
    cuello, que es lo que hace que se lea como un caballo."""
    _linea(d, [(x-t*.50, y-t*.56), (x-t*.10, y-t*.62), (x+t*.36, y-t*.58)], g, rnd, color=tinta)
    _linea(d, [(x-t*.50, y-t*.56), (x-t*.44, y-t*.30), (x+t*.30, y-t*.30),
               (x+t*.36, y-t*.58)], g, rnd, color=tinta)
    for px in (-.42, -.24, .10, .28):
        _linea(d, [(x+t*px, y-t*.31), (x+t*px+t*.04, y)], g, rnd, color=tinta)
    cuello = [(x+t*.30, y-t*.58), (x+t*.50, y-t*1.02), (x+t*.66, y-t*1.00),
              (x+t*.50, y-t*.56)]
    d.polygon(cuello, fill=(255, 255, 255)); _linea(d, cuello, g, rnd, color=tinta)
    cabeza = [(x+t*.50, y-t*1.02), (x+t*.86, y-t*1.06), (x+t*.90, y-t*.90),
              (x+t*.62, y-t*.92), (x+t*.50, y-t*1.02)]
    d.polygon(cabeza, fill=(255, 255, 255)); _linea(d, cabeza, g, rnd, color=tinta)
    d.ellipse([x+t*.80, y-t*1.02, x+t*.86, y-t*.96], fill=tinta)
    _linea(d, [(x+t*.34, y-t*.62), (x+t*.52, y-t*1.04)], max(2, g), rnd, color=tinta, temblor=3.0)
    _linea(d, [(x-t*.50, y-t*.56), (x-t*.66, y-t*.20)], g, rnd, color=tinta, temblor=3.0)


def _barco(d, x, y, t, rnd, g, tinta=TINTA):
    casco = [(x-t*.62, y-t*.28), (x+t*.62, y-t*.28), (x+t*.42, y), (x-t*.42, y), (x-t*.62, y-t*.28)]
    _linea(d, casco, g, rnd, color=tinta)
    _linea(d, [(x, y-t*.28), (x, y-t*1.15)], g, rnd, color=tinta)              # mastil
    vela = [(x+t*.04, y-t*1.10), (x+t*.46, y-t*.62), (x+t*.04, y-t*.40)]
    d.polygon(vela, fill=(255, 255, 255)); _linea(d, vela, g, rnd, color=tinta)
    vela2 = [(x-t*.04, y-t*1.10), (x-t*.40, y-t*.66), (x-t*.04, y-t*.46)]
    d.polygon(vela2, fill=(255, 255, 255)); _linea(d, vela2, g, rnd, color=tinta)


def _casa(d, x, y, t, rnd, g, tinta=TINTA):
    """Con las paredes RELLENAS. Las dibujaba a linea suelta, asi que en una
    calle se veia el cielo a traves de las casas."""
    d.polygon([(x-t*.42, y), (x-t*.42, y-t*.60), (x+t*.42, y-t*.60), (x+t*.42, y)],
              fill=(232, 222, 202))
    d.polygon([(x-t*.52, y-t*.58), (x, y-t*1.00), (x+t*.52, y-t*.58)], fill=(168, 96, 72))
    _linea(d, [(x-t*.42, y), (x-t*.42, y-t*.60), (x+t*.42, y-t*.60), (x+t*.42, y)],
           g, rnd, color=tinta)
    _linea(d, [(x-t*.52, y-t*.58), (x, y-t*1.00), (x+t*.52, y-t*.58), (x-t*.52, y-t*.58)],
           g, rnd, color=tinta)
    d.polygon([(x-t*.12, y), (x-t*.12, y-t*.34), (x+t*.12, y-t*.34), (x+t*.12, y)],
              fill=(120, 82, 54))
    _linea(d, [(x-t*.12, y), (x-t*.12, y-t*.34), (x+t*.12, y-t*.34), (x+t*.12, y)],
           g, rnd, color=tinta)
    d.rectangle([x+t*.18, y-t*.52, x+t*.32, y-t*.38], fill=(150, 190, 214),
                outline=tinta, width=max(2, g//2))


def _iglesia(d, x, y, t, rnd, g, tinta=TINTA):
    _linea(d, [(x-t*.46, y), (x-t*.46, y-t*.66), (x+t*.46, y-t*.66), (x+t*.46, y)],
           g, rnd, color=tinta)
    _linea(d, [(x-t*.20, y-t*.64), (x-t*.20, y-t*1.14), (x+t*.20, y-t*1.14), (x+t*.20, y-t*.64)],
           g, rnd, color=tinta)
    _linea(d, [(x, y-t*1.14), (x, y-t*1.46)], g, rnd, color=tinta)
    _linea(d, [(x-t*.13, y-t*1.34), (x+t*.13, y-t*1.34)], g, rnd, color=tinta)
    d.arc([x-t*.16, y-t*.40, x+t*.16, y+t*.06], 180, 360, fill=tinta, width=g)


def _castillo(d, x, y, t, rnd, g, tinta=TINTA):
    _linea(d, [(x-t*.60, y), (x-t*.60, y-t*.72), (x+t*.60, y-t*.72), (x+t*.60, y)],
           g, rnd, color=tinta)
    almena = [(x-t*.60, y-t*.72)]
    for k in range(6):
        px = x - t*.60 + t*1.20*k/6
        almena += [(px, y-t*.92), (px+t*.10, y-t*.92), (px+t*.10, y-t*.72), (px+t*.20, y-t*.72)]
    _linea(d, almena, g, rnd, color=tinta)
    _linea(d, [(x-t*.14, y), (x-t*.14, y-t*.34), (x+t*.14, y-t*.34), (x+t*.14, y)],
           g, rnd, color=tinta)


def _espada(d, x, y, t, rnd, g, tinta=TINTA):
    """Salia identica a la cruz. Una espada tiene PUNTA, guarda corta y
    empuñadura larga - y se dibuja inclinada, que es como se sostiene."""
    hoja = [(x-t*.10, y-t*.34), (x+t*.02, y-t*.40), (x+t*.34, y-t*1.12),
            (x+t*.20, y-t*1.16), (x-t*.10, y-t*.34)]
    d.polygon(hoja, fill=(255, 255, 255)); _linea(d, hoja, g, rnd, color=tinta)
    _linea(d, [(x-t*.26, y-t*.44), (x+t*.16, y-t*.26)], max(g, int(t*.06)), rnd, color=tinta)
    _linea(d, [(x-t*.06, y-t*.32), (x-t*.18, y-t*.04)], max(g, int(t*.07)), rnd, color=tinta)
    _circulo(d, (x-t*.19, y-t*.02), t*.07, g, rnd, relleno=None, color=tinta)


def _canion(d, x, y, t, rnd, g, tinta=TINTA):
    """No se entendia nada. Un cañon es un TUBO que se estrecha, sobre dos
    ruedas, y apuntando claramente a un lado."""
    tubo = [(x-t*.34, y-t*.56), (x+t*.62, y-t*.46), (x+t*.62, y-t*.28),
            (x-t*.34, y-t*.16), (x-t*.34, y-t*.56)]
    d.polygon(tubo, fill=(255, 255, 255)); _linea(d, tubo, g, rnd, color=tinta)
    _linea(d, [(x+t*.62, y-t*.46), (x+t*.70, y-t*.48), (x+t*.70, y-t*.26),
               (x+t*.62, y-t*.28)], g, rnd, color=tinta)
    _linea(d, [(x-t*.36, y-t*.44), (x-t*.10, y-t*.06)], g, rnd, color=tinta)
    for cx, r in ((-.26, .22), (.14, .16)):
        _circulo(d, (x+t*cx, y-t*r), t*r, g, rnd, relleno=(255, 255, 255), color=tinta)


def _fuego(d, x, y, t, rnd, g, tinta=TINTA):
    for k, (ancho, alto, col) in enumerate(((.42, .90, (232, 120, 30)),
                                            (.26, .62, (248, 186, 60)))):
        llama = [(x-t*ancho, y)]
        for i in range(7):
            f = i/6
            llama.append((x - t*ancho + 2*t*ancho*f,
                          y - t*alto*(0.4 + 0.6*math.sin(math.pi*f)) + rnd.uniform(-t*.06, t*.06)))
        llama.append((x+t*ancho, y))
        d.polygon(llama, fill=col)
        _linea(d, llama, max(2, g//2), rnd, color=tinta, temblor=2.4)


def _dinero(d, x, y, t, rnd, g, tinta=TINTA):
    for i, (dx, dy, r) in enumerate(((-.22, -.10, .18), (.16, -.09, .16), (-.02, -.30, .17))):
        c = (x+t*dx, y+t*dy)
        _circulo(d, c, t*r, g, rnd, relleno=(236, 196, 88), color=tinta)


def _libro(d, x, y, t, rnd, g, tinta=TINTA):
    """Salia una pajarita: tenia las paginas al reves. Un libro abierto son
    dos hojas que se hunden en el centro y suben por fuera."""
    izq = [(x-t*.02, y-t*.10), (x-t*.44, y-t*.22), (x-t*.44, y-t*.56),
           (x-t*.02, y-t*.44)]
    der = [(x+t*.02, y-t*.10), (x+t*.44, y-t*.22), (x+t*.44, y-t*.56),
           (x+t*.02, y-t*.44)]
    for hoja in (izq, der):
        d.polygon(hoja, fill=(255, 255, 255)); _linea(d, hoja + [hoja[0]], g, rnd, color=tinta)
    _linea(d, [(x, y-t*.44), (x, y-t*.10)], g, rnd, color=tinta)
    for k in (1, 2):
        _linea(d, [(x-t*.36, y-t*.50+t*.08*k), (x-t*.08, y-t*.40+t*.08*k)],
               max(2, g//2), rnd, color=tinta)
        _linea(d, [(x+t*.08, y-t*.40+t*.08*k), (x+t*.36, y-t*.50+t*.08*k)],
               max(2, g//2), rnd, color=tinta)


def _bandera(d, x, y, t, rnd, g, tinta=TINTA):
    _linea(d, [(x, y), (x, y-t*1.10)], g, rnd, color=tinta)
    paño = [(x, y-t*1.06), (x+t*.56, y-t*.92), (x+t*.50, y-t*.62), (x, y-t*.66)]
    d.polygon(paño, fill=(200, 60, 50)); _linea(d, paño, g, rnd, color=tinta)


def _cruz(d, x, y, t, rnd, g, tinta=TINTA):
    _linea(d, [(x, y), (x, y-t*.90)], max(g, int(t*.08)), rnd, color=tinta)
    _linea(d, [(x-t*.28, y-t*.62), (x+t*.28, y-t*.62)], max(g, int(t*.08)), rnd, color=tinta)


def _olla(d, x, y, t, rnd, g, tinta=TINTA):
    """Era un cuenco con una raya encima. Una olla tiene ASAS y tapa."""
    cuerpo = [(x-t*.32, y-t*.46), (x+t*.32, y-t*.46), (x+t*.26, y), (x-t*.26, y)]
    d.polygon(cuerpo, fill=(146, 142, 136)); _linea(d, cuerpo + [cuerpo[0]], g, rnd, color=tinta)
    for lado in (-1, 1):
        d.arc([x+lado*t*.30-t*.12, y-t*.46, x+lado*t*.30+t*.12, y-t*.22],
              0, 360, fill=tinta, width=g)
    _linea(d, [(x-t*.38, y-t*.48), (x+t*.38, y-t*.48)], g, rnd, color=tinta)
    _circulo(d, (x, y-t*.56), t*.07, g, rnd, relleno=(255, 255, 255), color=tinta)


def _montaña(d, x, y, t, rnd, g, tinta=TINTA):
    _linea(d, [(x-t*.80, y), (x-t*.24, y-t*.86), (x+t*.06, y-t*.46),
               (x+t*.34, y-t*.72), (x+t*.86, y)], g, rnd, color=tinta)


def _nube(d, x, y, t, rnd, g, tinta=TINTA):
    for dx, r in ((-.28, .22), (0, .30), (.28, .22)):
        _circulo(d, (x+t*dx, y), t*r, g, rnd, relleno=(255, 255, 255), color=tinta)


def _sol(d, x, y, t, rnd, g, tinta=TINTA):
    _circulo(d, (x, y), t*.30, g, rnd, relleno=(250, 214, 90), color=tinta)
    for k in range(8):
        a = k/8*2*math.pi
        _linea(d, [(x+math.cos(a)*t*.40, y+math.sin(a)*t*.40),
                   (x+math.cos(a)*t*.58, y+math.sin(a)*t*.58)], g, rnd, color=tinta)


COSAS = {
    "perro": _perro, "caballo": _caballo, "barco": _barco, "casa": _casa,
    "iglesia": _iglesia, "castillo": _castillo, "espada": _espada,
    "canion": _canion, "fuego": _fuego, "dinero": _dinero, "libro": _libro,
    "bandera": _bandera, "cruz": _cruz, "olla": _olla, "montaña": _montaña,
    "nube": _nube, "sol": _sol,
    # El arbol ya existia pero con otra firma, y por estar aqui a None se
    # caia en silencio: el prompt lo ofrecia y limpia() lo tiraba.
    "arbol": lambda d, x, y, t, rnd, g, tinta=TINTA: arbol(d, x, y, t*1.6, rnd),
}
COSAS_VALIDAS = tuple(COSAS)


# ---- DECORADOS CON FONDO -----------------------------------------------------
# Ella, enseñandome una taberna dibujada con palotes igual que los mios pero
# con entramado de madera, chimenea de ladrillo, mapas en las mesas y el
# puerto por la ventana: "las escenas siempre son las mismas, igual no
# necesitan mas movimiento si no mejorar la imagen, el fondo".
#
# Tiene razon y cambia la prioridad. En esa imagen no se mueve NADA y te
# quedas mirandola, porque hay cosas que ver. Lo mio eran dos bandas de color
# planas, asi que todas las escenas se parecian aunque los monigotes hicieran
# cosas distintas.
#
# Lo que da profundidad es tener CAPAS: algo al fondo que se ve por un hueco
# (el mar por la ventana), la habitacion en medio, y algo delante que corta el
# plano (una viga, una mesa). Eso es lo que separa un decorado de un fondo.

MADERA_CLARA = (186, 146, 96)
LADRILLO = (166, 86, 68)
PIEDRA_CLARA = (196, 190, 180)


def _tablas(d, w, y0, y1, rnd, g, n=9):
    """Suelo de tablas con fuga: las juntas se juntan hacia el fondo."""
    d.rectangle([0, y0, w, y1], fill=MADERA)
    fuga = (w*0.5, y0 - (y1-y0)*1.2)
    for k in range(n+1):
        px = w*k/n
        _linea(d, [(px, y1), (fuga[0] + (px-fuga[0])*0.22, y0)], max(2, g//2), rnd,
               color=MADERA_OSCURA, temblor=1.2)
    for k in range(1, 4):                      # juntas transversales
        yy = y1 - (y1-y0)*(k/4)**1.7
        _linea(d, [(0, yy), (w, yy)], max(2, g//2), rnd, color=MADERA_OSCURA, temblor=1.4)


def _entramado(d, w, y0, y1, rnd, g, postes=4):
    """Pared de entramado: yeso entre vigas de madera."""
    d.rectangle([0, y0, w, y1], fill=(226, 214, 192))
    grueso = w*0.035
    for k in range(postes+1):
        px = w*k/postes - grueso/2
        d.rectangle([px, y0, px+grueso, y1], fill=MADERA_CLARA)
        _linea(d, [(px, y0), (px, y1)], max(2, g//2), rnd, color=MADERA_OSCURA, temblor=1.4)
        _linea(d, [(px+grueso, y0), (px+grueso, y1)], max(2, g//2), rnd,
               color=MADERA_OSCURA, temblor=1.4)
    for yy in (y0 + (y1-y0)*0.06, y1 - (y1-y0)*0.06):
        d.rectangle([0, yy-grueso/2, w, yy+grueso/2], fill=MADERA_CLARA)
        _linea(d, [(0, yy-grueso/2), (w, yy-grueso/2)], max(2, g//2), rnd,
               color=MADERA_OSCURA, temblor=1.4)
        _linea(d, [(0, yy+grueso/2), (w, yy+grueso/2)], max(2, g//2), rnd,
               color=MADERA_OSCURA, temblor=1.4)


def _chimenea(d, x, y_suelo, ancho, alto, rnd, g, encendida=True):
    x0, x1 = x-ancho/2, x+ancho/2
    y0 = y_suelo - alto
    d.rectangle([x0, y0, x1, y_suelo], fill=LADRILLO)
    fila_h = alto/9
    for f in range(9):                         # ladrillos a matajunta
        yy = y0 + f*fila_h
        _linea(d, [(x0, yy), (x1, yy)], max(2, g//2), rnd, color=(126, 62, 48), temblor=1.0)
        desfase = (ancho/4) if f % 2 else 0
        px = x0 + desfase
        while px < x1:
            _linea(d, [(px, yy), (px, yy+fila_h)], max(2, g//2), rnd,
                   color=(126, 62, 48), temblor=1.0)
            px += ancho/2
    _linea(d, [(x0, y0), (x1, y0), (x1, y_suelo)], g, rnd, color=TINTA)
    _linea(d, [(x0, y0), (x0, y_suelo)], g, rnd, color=TINTA)
    hueco = [(x-ancho*.28, y_suelo), (x-ancho*.28, y_suelo-alto*.30),
             (x, y_suelo-alto*.42), (x+ancho*.28, y_suelo-alto*.30),
             (x+ancho*.28, y_suelo)]
    d.polygon(hueco, fill=(42, 36, 32)); _linea(d, hueco, g, rnd, color=TINTA)
    if encendida:
        _fuego(d, x, y_suelo-alto*.02, ancho*.34, rnd, max(2, g//2), TINTA)
        for lado in (-1, 1):                   # leños
            _linea(d, [(x+lado*ancho*.20, y_suelo-alto*.02),
                       (x-lado*ancho*.06, y_suelo-alto*.06)], g, rnd, color=MADERA_OSCURA)


def _ventana_al_mar(d, x, y, ancho, alto, rnd, g, barcos=2):
    """Un hueco con OTRO mundo detras: es lo que da fondo a la escena."""
    x0, y0, x1, y1 = x-ancho/2, y-alto/2, x+ancho/2, y+alto/2
    d.rectangle([x0, y0, x1, y1], fill=(146, 198, 232))
    d.rectangle([x0, y0+alto*0.52, x1, y1], fill=(92, 140, 186))
    for k in range(barcos):
        bx = x0 + ancho*(0.22 + 0.42*k)
        _barco(d, bx, y0+alto*(0.62+0.06*k), ancho*0.26, rnd, max(2, g//2), TINTA)
    _linea(d, [(x0, y1-alto*0.36), (x1, y1-alto*0.30)], max(2, g//2), rnd,
           color=(120, 92, 62), temblor=1.4)     # el muelle
    _linea(d, [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], int(g*1.6), rnd, color=TINTA)
    _linea(d, [(x, y0), (x, y1)], g, rnd, color=TINTA)


def _adoquines(d, x0, y0, x1, y1, rnd, g):
    """Con FUGA hacia el fondo. En filas rectas parecia una pared de ladrillo
    puesta de pie, no una calle."""
    d.rectangle([x0, y0, x1, y1], fill=PIEDRA_CLARA)
    ancho_total = x1 - x0
    centro = (x0 + x1)/2
    fila, yy = 0, y0
    while yy < y1:
        f = (yy - y0)/max(1.0, y1 - y0)         # 0 al fondo, 1 delante
        alto = (y1-y0)*(0.035 + 0.075*f)
        # Cerca todo es mas ancho y esta mas abierto: eso es la fuga.
        ancho = ancho_total*(0.06 + 0.10*f)
        px = centro - ancho_total*(0.55 + 0.1*f) + (ancho/2 if fila % 2 else 0)
        while px < x1 + ancho:
            _linea(d, [(px, yy), (px+ancho*.92, yy+alto*.08),
                       (px+ancho*.88, yy+alto), (px-ancho*.04, yy+alto*.92), (px, yy)],
                   max(2, g//2), rnd, color=(150, 144, 136), temblor=1.4)
            px += ancho
        yy += alto; fila += 1


def _mesa_con_cosas(d, x, y, ancho, rnd, g, papeles=2, jarras=2, alto=None):
    alto = alto if alto else ancho*0.30
    tablero = [(x-ancho/2, y-alto), (x+ancho/2, y-alto),
               (x+ancho*0.42, y-alto*0.72), (x-ancho*0.42, y-alto*0.72)]
    d.polygon(tablero, fill=MADERA_CLARA); _linea(d, tablero+[tablero[0]], g, rnd, color=TINTA)
    for lado in (-1, 1):
        px = x + lado*ancho*0.36
        _linea(d, [(px, y-alto*0.74), (px, y)], int(g*1.8), rnd, color=MADERA_OSCURA)
    for k in range(papeles):
        px = x - ancho*0.22 + ancho*0.34*k
        hoja = [(px-ancho*.13, y-alto*1.02), (px+ancho*.13, y-alto*1.04),
                (px+ancho*.15, y-alto*.88), (px-ancho*.15, y-alto*.86)]
        d.polygon(hoja, fill=(248, 242, 226)); _linea(d, hoja+[hoja[0]], max(2, g//2), rnd, color=TINTA)
        for j in range(2):
            _linea(d, [(px-ancho*.09, y-alto*(.98-.05*j)), (px+ancho*.09, y-alto*(.99-.05*j))],
                   max(2, g//3), rnd, color=(150, 140, 126), temblor=1.6)
    for k in range(jarras):
        px = x + ancho*(0.30 - 0.52*k)
        _jarra(d, px, y-alto*0.92, ancho*0.075, rnd, max(2, g//2))


def _taburete(d, x, y, t, rnd, g):
    d.ellipse([x-t*.30, y-t*.62, x+t*.30, y-t*.44], fill=MADERA_CLARA, outline=TINTA, width=g)
    for px in (-.22, 0, .22):
        _linea(d, [(x+t*px, y-t*.52), (x+t*px*1.5, y)], int(g*1.4), rnd, color=MADERA_OSCURA)


def _cartel(d, x, y, ancho, texto, rnd, g):
    """El cartel colgado. Lo de la imagen que me paso: es lo que le pone
    NOMBRE al sitio sin que la voz tenga que decirlo."""
    lineas = texto.upper().split("\n")[:3]
    alto = ancho*(0.30 + 0.18*len(lineas))
    x0, y0, x1, y1 = x-ancho/2, y, x+ancho/2, y+alto
    _linea(d, [(x-ancho*.42, y), (x-ancho*.42, y-ancho*.22)], g, rnd, color=TINTA)
    _linea(d, [(x+ancho*.42, y), (x+ancho*.42, y-ancho*.22)], g, rnd, color=TINTA)
    _linea(d, [(x-ancho*.55, y-ancho*.22), (x+ancho*.55, y-ancho*.22)], int(g*1.4), rnd, color=TINTA)
    d.rectangle([x0, y0, x1, y1], fill=MADERA_CLARA)
    _linea(d, [(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)], int(g*1.5), rnd, color=TINTA)
    # La letra se MIDE y se encoge hasta que cabe. Sin esto "LA TABERNA DEL
    # PUERTO" se salia del tablero por los dos lados: elegia el tamaño por la
    # altura del cartel y no miraba lo ancho que era el texto.
    px = int(alto/(len(lineas)+0.6))
    for _ in range(14):
        f = _fuente_cartel(px)
        if max(d.textlength(l, font=f) for l in lineas) <= ancho*0.84 or px <= 12:
            break
        px = int(px*0.88)
    salto = alto*0.80/len(lineas)
    arriba = y0 + (alto - salto*len(lineas))/2
    for i, l in enumerate(lineas):
        d.text((x - d.textlength(l, font=f)/2, arriba + i*salto), l, font=f, fill=(74, 52, 34))


def _fuente_cartel(px):
    from PIL import ImageFont
    import glob
    for patron in ("/usr/share/fonts/**/DejaVuSerif-Bold.ttf",
                   "/usr/share/fonts/**/DejaVuSans-Bold.ttf"):
        for f in glob.glob(patron, recursive=True):
            try:
                return ImageFont.truetype(f, max(12, px))
            except Exception:
                continue
    return ImageFont.load_default()


def taberna(spec: dict, w: int, h: int, semilla: int = 0):
    """Una taberna de puerto, montada por capas de profundidad.

      1. la pared del fondo, con su entramado
      2. un hueco al mar y una chimenea encendida - el "otro mundo"
      3. mesas del fondo, mas pequeñas, con su gente
      4. el suelo de tablas
      5. LAS FIGURAS
      6. la mesa de delante con mapas y jarras, POR DELANTE de la gente
      7. una viga cruzando arriba, que es lo que mete al espectador dentro
    """
    rnd = random.Random(semilla)
    vertical = h > w
    suelo = int(h*spec.get("suelo", 0.70))
    img = Image.new("RGB", (w, h), (226, 214, 192))
    d = ImageDraw.Draw(img)
    g = max(4, int(w*0.006))

    _entramado(d, w, 0, suelo, rnd, g, postes=3 if vertical else 5)
    _ventana_al_mar(d, w*0.26, h*(0.30 if vertical else 0.32),
                    w*0.34, h*(0.16 if vertical else 0.26), rnd, g)
    _chimenea(d, w*0.78, suelo, w*0.30, h*(0.30 if vertical else 0.46), rnd, g)
    _tablas(d, w, suelo, h, rnd, g, n=7 if vertical else 11)

    # Gente del fondo, pequeña: llena el sitio sin robar el plano.
    for x, alto in ((0.42, 0.10), (0.56, 0.095)):
        figura(d, w*x, suelo + h*0.02, h*alto, rnd, "en_mesa", "neutro")
    _mesa_con_cosas(d, w*0.49, suelo + h*0.03, w*0.24, rnd, max(2, g//2),
                    papeles=1, jarras=1, alto=h*0.035)

    velas = []
    for f in spec.get("figuras", []):
        alto_f = h*f.get("alto", 0.30)
        figura(d, w*f["x"], suelo + h*0.27 + alto_f*_RESPIRACION*f.get("_bocanada", 0.0),
               alto_f, rnd, f.get("pose", "en_mesa"), f.get("gesto", "neutro"),
               f.get("gorro"), f.get("espejo", False), f.get("pose_mezclada"),
               rasgos=REPARTO.get(f.get("quien") or ""))

    _mesa_con_cosas(d, w*0.46, suelo + h*0.34, w*0.92, rnd, g, papeles=2, jarras=2,
                    alto=h*0.075)
    _taburete(d, w*0.90, suelo + h*0.36, h*0.09, rnd, g)
    # Un banco cruzando abajo: cierra el plano y quita el metro de suelo
    # vacio que quedaba. Es lo que en la referencia hace la barandilla.
    _banco(d, w*0.42, h*1.02, w*0.62, rnd, g)

    # La viga de delante: el marco que mete al espectador DENTRO del sitio.
    d.rectangle([0, 0, w, h*0.055], fill=MADERA_CLARA)
    _linea(d, [(0, h*0.055), (w, h*0.055)], int(g*1.6), rnd, color=MADERA_OSCURA)
    for px in (0.12, 0.88):
        d.rectangle([w*px-w*0.022, 0, w*px+w*0.022, h*0.30], fill=MADERA_CLARA)
        _linea(d, [(w*px-w*0.022, 0), (w*px-w*0.022, h*0.30)], g, rnd, color=MADERA_OSCURA)
        _linea(d, [(w*px+w*0.022, 0), (w*px+w*0.022, h*0.30)], g, rnd, color=MADERA_OSCURA)

    # La pared de la izquierda salia pelada. Dos cosas colgadas y ya hay algo
    # que mirar mientras habla la voz.
    # Colgadas de la pared, y solo lo que se cuelga de verdad: el libro
    # flotaba a media pared como un fantasma.
    for px, py, que, tam in ((0.13, 0.52, "espada", 0.10), (0.15, 0.72, "olla", 0.05)):
        COSAS[que](d, w*px, h*py, h*tam, rnd, max(2, g//2), TINTA)
    _linea(d, [(w*0.09, h*0.73), (w*0.21, h*0.73)], int(g*1.4), rnd, color=MADERA_OSCURA)
    _vela(d, w*0.36, suelo - h*0.01, h*0.035, rnd, max(2, g//2))

    letrero = spec.get("cartel")
    if letrero:
        _cartel(d, w*0.50, h*0.10, w*0.42, str(letrero)[:40], rnd, g)

    img = _resplandor(img, (w*0.78, suelo - h*0.10), h*0.16)
    return img


# ---- EL SUELO CON COSAS ------------------------------------------------------
# Del video que me paso: dos monigotes en una savana, y el suelo NO es una
# banda verde - tiene matas de hierba, piedras sueltas y arboles de distintos
# tamaños repartidos. Eso es lo que hace que el plano aguante veinte segundos
# de voz encima. Y es barato: son bucles.
#
# Va sembrado con semilla fija por escena, asi que los matojos no bailan de un
# fotograma a otro - que es justo lo que pasaria sembrandolos al azar en cada
# uno, y marearia.

def _mata(d, x, y, t, rnd, g, color=(72, 132, 52)):
    for k in (-1, 0, 1):
        _linea(d, [(x + k*t*0.18, y),
                   (x + k*t*0.34, y - t*rnd.uniform(0.55, 1.0))], g, rnd,
               color=color, temblor=1.6)


def _piedra(d, x, y, t, rnd, g, color=(150, 142, 132)):
    pts = []
    for i in range(9):
        a = i/8*math.pi
        pts.append((x - math.cos(a)*t*rnd.uniform(.8, 1.1),
                    y - math.sin(a)*t*rnd.uniform(.45, .7)))
    pts += [(x + t, y), (x - t, y)]
    d.polygon(pts, fill=color)
    _linea(d, pts + [pts[0]], max(2, g//2), rnd, color=TINTA, temblor=1.2)


_SIEMBRA = {
    "campo": {"matas": 34, "piedras": 9, "arboles": 3, "verde": (72, 132, 52)},
    "calle": {"matas": 5,  "piedras": 16, "arboles": 1, "verde": (120, 112, 96)},
    "noche": {"matas": 20, "piedras": 7, "arboles": 2, "verde": (44, 62, 44)},
    "liso":  {"matas": 0,  "piedras": 0, "arboles": 0, "verde": (72, 132, 52)},
    "salon": {"matas": 0,  "piedras": 0, "arboles": 0, "verde": (72, 132, 52)},
}


def _sembrar(d, w, h, suelo, fondo, rnd, g):
    """Lo que llena el suelo. Las cosas de detras, mas pequeñas y mas palidas:
    es lo unico que hace falta para que haya profundidad."""
    plan = _SIEMBRA.get(fondo)
    if not plan:
        return
    # Un par de nubes: el cielo se quedaba como un rectangulo azul enorme y
    # vacio, que es la mitad de arriba del plano en vertical.
    if plan["arboles"] and fondo != "noche":
        for _ in range(2):
            _nube(d, w*rnd.uniform(0.08, 0.92), suelo*rnd.uniform(0.18, 0.55),
                  h*rnd.uniform(0.035, 0.055), rnd, max(3, g//2))
    hondo = h - suelo
    # Los arboles van EN EL HORIZONTE, no repartidos por el prado: sembrados
    # hacia delante salian entre las piernas de la gente, y ademas pequeños,
    # con lo que parecian arbustos en un palo. En la referencia estan todos en
    # la linea del fondo y son grandes.
    for _ in range(plan["arboles"]):
        arbol(d, w*rnd.uniform(0.02, 0.98), suelo + hondo*rnd.uniform(0.0, 0.05),
              h*rnd.uniform(0.13, 0.19), rnd)
    for _ in range(plan["matas"]):
        f = rnd.uniform(0, 1)
        _mata(d, w*rnd.uniform(0.01, 0.99), suelo + hondo*f,
              h*(0.016 + 0.038*f), rnd, max(3, int(g*(0.5 + 0.7*f))),
              color=plan["verde"])
    for _ in range(plan["piedras"]):
        f = rnd.uniform(0.1, 1)
        _piedra(d, w*rnd.uniform(0.03, 0.97), suelo + hondo*f,
                h*(0.006 + 0.022*f), rnd, max(2, int(g*(0.4 + 0.6*f))))


# ---- MOTOR DE DECORADOS ------------------------------------------------------
# "¿Has hecho mas escenarios o solo esa? Tiene que tener muchas mas". Tiene
# razon, y el problema no era la idea: era que monte el monasterio y la
# taberna como funciones a medida, asi que cada sitio nuevo costaba media hora
# y siempre habria dos.
#
# Aqui un decorado es una RECETA: paredes, suelo, lo que hay al fondo, los
# muebles y lo que cuelga. Añadir un sitio son tres lineas, y todos heredan
# gratis lo que ya funciona - el orden por capas, el resplandor de las velas,
# la gente delante y los muebles de primer termino por encima.

def _pared(d, w, y0, y1, clase, rnd, g):
    if clase == "entramado":
        _entramado(d, w, y0, y1, rnd, g)
    elif clase == "piedra":
        _pared_piedra(d, w, y1, y1, rnd)
        d.rectangle([0, y0, w, y1], fill=PIEDRA)
        rr = random.Random(7)
        for _ in range(30):
            bw = rr.uniform(w*.05, w*.13); bh = bw*rr.uniform(.32, .52)
            bx = rr.uniform(0, w-bw); by = rr.uniform(y0, y1-bh)
            _linea(d, [(bx,by),(bx+bw,by),(bx+bw,by+bh),(bx,by+bh),(bx,by)], max(2, g//2),
                   rnd, color=(104, 98, 90), temblor=1.6)
    elif clase == "encalada":
        d.rectangle([0, y0, w, y1], fill=(238, 232, 220))
        for _ in range(7):                      # grietas
            x = rnd.uniform(0, w); y = rnd.uniform(y0, y1)
            _linea(d, [(x, y), (x+rnd.uniform(-w*.04, w*.04), y+rnd.uniform(0, (y1-y0)*.2))],
                   max(2, g//3), rnd, color=(206, 198, 184), temblor=3.0)
    elif clase == "ladrillo":
        d.rectangle([0, y0, w, y1], fill=LADRILLO)
        fila = (y1-y0)/12
        for f in range(12):
            yy = y0 + f*fila
            _linea(d, [(0, yy), (w, yy)], max(2, g//2), rnd, color=(126, 62, 48), temblor=1.0)
            px = (w/8) if f % 2 else 0
            while px < w:
                _linea(d, [(px, yy), (px, yy+fila)], max(2, g//2), rnd,
                       color=(126, 62, 48), temblor=1.0)
                px += w/4
    else:                                        # "cielo"
        d.rectangle([0, y0, w, y1], fill=(146, 198, 232))


def _piso(d, w, h, suelo, clase, rnd, g):
    if clase == "tablas":
        _tablas(d, w, suelo, h, rnd, g)
    elif clase == "adoquines":
        _adoquines(d, 0, suelo, w, h, rnd, g)
    elif clase == "losas":
        d.rectangle([0, suelo, w, h], fill=(176, 170, 160))
        paso = (h-suelo)/5
        for k in range(6):
            yy = suelo + k*paso
            _linea(d, [(0, yy), (w, yy)], max(2, g//2), rnd, color=(140, 134, 124), temblor=1.4)
        for k in range(5):
            _linea(d, [(w*k/4, suelo), (w*(k/4-0.25)+w*0.5, h)], max(2, g//2), rnd,
                   color=(140, 134, 124), temblor=1.4)
    elif clase == "tierra":
        d.rectangle([0, suelo, w, h], fill=(166, 138, 104))
        for _ in range(14):
            _piedra(d, rnd.uniform(0, w), rnd.uniform(suelo, h), h*rnd.uniform(.006, .016),
                    rnd, max(2, g//2), color=(150, 126, 96))
    elif clase == "hierba":
        d.rectangle([0, suelo, w, h], fill=(122, 193, 96))
    else:
        d.rectangle([0, suelo, w, h], fill=MADERA)


def _puerta_arco(d, x, y, ancho, alto, rnd, g, fuera=(146, 198, 232)):
    """Un vano con luz detras: barato y abre el plano."""
    x0, y0, x1 = x-ancho/2, y-alto, x+ancho/2
    d.rounded_rectangle([x0, y0, x1, y], radius=int(ancho*0.48), fill=fuera)
    d.rectangle([x0, y-alto*0.4, x1, y], fill=fuera)
    _linea(d, [(x0, y), (x0, y0+ancho*0.3)], int(g*1.4), rnd, color=TINTA)
    _linea(d, [(x1, y), (x1, y0+ancho*0.3)], int(g*1.4), rnd, color=TINTA)
    d.arc([x0, y0, x1, y0+ancho], 180, 360, fill=TINTA, width=int(g*1.4))


def _estante(d, x, y, ancho, rnd, g, ollas=2):
    _linea(d, [(x-ancho/2, y), (x+ancho/2, y)], int(g*1.8), rnd, color=MADERA_OSCURA)
    for k in range(ollas):
        px = x - ancho*0.28 + ancho*0.56*k/max(1, ollas-1) if ollas > 1 else x
        _olla(d, px, y, ancho*0.22, rnd, max(2, g//2))


def _estandarte(d, x, y, ancho, alto, rnd, g, color=(170, 44, 44)):
    paño = [(x-ancho/2, y), (x+ancho/2, y), (x+ancho/2, y+alto),
            (x, y+alto*0.86), (x-ancho/2, y+alto)]
    d.polygon(paño, fill=color); _linea(d, paño+[paño[0]], g, rnd, color=TINTA)
    _linea(d, [(x-ancho*0.62, y), (x+ancho*0.62, y)], int(g*1.4), rnd, color=MADERA_OSCURA)


def _trono(d, x, y, ancho, rnd, g):
    alto = ancho*1.5
    respaldo = [(x-ancho/2, y), (x-ancho/2, y-alto), (x-ancho*0.28, y-alto*1.14),
                (x, y-alto*1.0), (x+ancho*0.28, y-alto*1.14), (x+ancho/2, y-alto),
                (x+ancho/2, y)]
    d.polygon(respaldo, fill=MADERA_CLARA); _linea(d, respaldo+[respaldo[0]], g, rnd, color=TINTA)
    d.rectangle([x-ancho*0.6, y-alto*0.36, x+ancho*0.6, y-alto*0.24], fill=(170, 44, 44))
    _linea(d, [(x-ancho*0.6, y-alto*0.36), (x+ancho*0.6, y-alto*0.36)], g, rnd, color=TINTA)


def _mastil(d, x, suelo, h, rnd, g):
    _linea(d, [(x, suelo), (x, h*0.03)], int(g*2.4), rnd, color=MADERA_OSCURA)
    _linea(d, [(x-h*0.14, h*0.16), (x+h*0.14, h*0.16)], int(g*1.6), rnd, color=MADERA_OSCURA)
    vela = [(x-h*0.13, h*0.17), (x+h*0.13, h*0.17), (x+h*0.09, h*0.40), (x-h*0.09, h*0.40)]
    d.polygon(vela, fill=(248, 244, 232)); _linea(d, vela+[vela[0]], g, rnd, color=TINTA)
    for lado in (-1, 1):
        _linea(d, [(x, h*0.05), (x+lado*h*0.22, suelo)], max(2, g//2), rnd, color=TINTA)


# Cada sitio es una receta. Añadir uno son tres lineas y hereda gratis el
# orden por capas, el resplandor de las velas y la gente delante.
#
#   pared / piso  : de que estan hechos
#   fondo         : lo que hay pegado a la pared (chimenea, ventana, puerta...)
#   muebles       : lo que hay en el suelo, DETRAS de la gente
#   delante       : lo que tapa a la gente por abajo (la mesa, una barandilla)
#   cuelga        : lo colgado de la pared
#   velas         : donde hay lumbre, para el resplandor
_DECORADOS = {
    "taberna":      {"pared": "entramado", "piso": "tablas",
                     "fondo": [("ventana_mar", .26, .34, .34), ("chimenea", .78, 1.0, .30)],
                     "muebles": [("mesa_fondo", .49, .03, .24), ("taburete", .90, .10, .09)],
                     "delante": [("mesa", .46, .34, .92)],
                     "cuelga": [("espada", .13, .40, .10)], "velas": [(.78, -.10)]},
    "monasterio":   {"pared": "piedra", "piso": "losas",
                     "fondo": [("ventana_arco", .50, .36, .20)],
                     "muebles": [("estante", .18, .06, .22)],
                     "delante": [("mesa", .50, .30, .94)],
                     "cuelga": [("cruz", .84, .38, .09)], "velas": [(.12, -.30), (.88, -.30)]},
    "salon_trono":  {"pared": "piedra", "piso": "losas",
                     "fondo": [("trono", .50, 1.0, .22), ("estandarte", .16, .22, .13),
                               ("estandarte", .84, .22, .13)],
                     "muebles": [], "delante": [],
                     "cuelga": [("espada", .26, .34, .11), ("espada", .74, .34, .11)],
                     "velas": [(.08, -.34), (.92, -.34)]},
    "cocina":       {"pared": "encalada", "piso": "losas",
                     "fondo": [("chimenea", .74, 1.0, .34), ("ventana_arco", .22, .34, .16)],
                     "muebles": [("estante", .30, .30, .30)],
                     "delante": [("mesa", .44, .32, .90)],
                     "cuelga": [("olla", .50, .30, .06)], "velas": [(.74, -.12)]},
    "iglesia":      {"pared": "piedra", "piso": "losas",
                     "fondo": [("ventana_arco", .28, .30, .17), ("ventana_arco", .72, .30, .17),
                               ("cruz_grande", .50, .58, .22)],
                     "muebles": [("banco_fondo", .50, .30, .56)],
                     "delante": [("banco_fondo", .50, .46, .96)],
                     "cuelga": [], "velas": [(.20, -.26), (.80, -.26), (.50, -.10)]},
    "calle":        {"pared": "cielo", "piso": "adoquines",
                     "fondo": [("casas", .5, 1.0, 1.0)],
                     "muebles": [], "delante": [], "cuelga": [], "velas": []},
    "mercado":      {"pared": "cielo", "piso": "adoquines",
                     "fondo": [("casas", .5, 1.0, 1.0), ("puesto", .20, 1.0, .28),
                               ("puesto", .80, 1.0, .28)],
                     "muebles": [("olla_suelo", .50, .06, .07)],
                     "delante": [("mesa", .50, .34, .84)], "cuelga": [], "velas": []},
    "cubierta":     {"pared": "cielo_mar", "piso": "tablas",
                     "fondo": [("mastil", .50, 1.0, 1.0)],
                     "muebles": [("olla_suelo", .84, .08, .06)],
                     "delante": [("barandilla", .5, .30, 1.0)], "cuelga": [], "velas": []},
    "mina":         {"pared": "roca", "piso": "tierra",
                     "fondo": [("puntales", .5, 1.0, 1.0)],
                     "muebles": [], "delante": [], "cuelga": [], "velas": [(.30, -.30), (.70, -.24)]},
}
DECORADOS_VALIDOS = tuple(_DECORADOS)


def _pieza_fondo(d, w, h, suelo, que, x, y, tam, rnd, g):
    X, Y, T = w*x, h*y, w*tam
    if que == "ventana_mar":      _ventana_al_mar(d, X, h*y, T, h*tam*0.55, rnd, g)
    elif que == "ventana_arco":   _ventana_arco(d, X, h*y, T, h*tam*0.95, rnd, g)
    elif que == "chimenea":       _chimenea(d, X, suelo, T, h*tam, rnd, g)
    elif que == "trono":          _trono(d, X, suelo, T, rnd, g)
    elif que == "estandarte":     _estandarte(d, X, h*y, T, h*tam*1.9, rnd, g)
    elif que == "cruz_grande":    _cruz(d, X, h*y, h*tam, rnd, int(g*1.6), TINTA)
    elif que == "mastil":         _mastil(d, X, suelo, h, rnd, g)
    elif que == "casas":
        for k in range(5):
            px = w*(0.08 + 0.21*k)
            _casa(d, px, suelo + h*0.005, h*rnd.uniform(0.17, 0.25), rnd, g, TINTA)
    elif que == "puesto":
        toldo = [(X-T*.6, suelo-h*.20), (X+T*.6, suelo-h*.20),
                 (X+T*.5, suelo-h*.13), (X-T*.5, suelo-h*.13)]
        d.polygon(toldo, fill=(198, 88, 76)); _linea(d, toldo+[toldo[0]], g, rnd, color=TINTA)
        for lado in (-1, 1):
            _linea(d, [(X+lado*T*.5, suelo-h*.14), (X+lado*T*.5, suelo)], g, rnd, color=MADERA_OSCURA)
        _mesa_con_cosas(d, X, suelo, T*1.1, rnd, max(2, g//2), papeles=1, jarras=1, alto=h*0.045)
    elif que == "puntales":
        for k in range(3):
            px = w*(0.16 + 0.34*k)
            _linea(d, [(px, suelo), (px, h*0.10)], int(g*2.6), rnd, color=MADERA_OSCURA)
        _linea(d, [(0, h*0.10), (w, h*0.10)], int(g*2.6), rnd, color=MADERA_OSCURA)


def _pieza_mueble(d, w, h, suelo, que, x, y, tam, rnd, g):
    X, Y, T = w*x, suelo + h*y, w*tam
    if que == "mesa_fondo":
        _mesa_con_cosas(d, X, Y, T, rnd, max(2, g//2), papeles=1, jarras=1, alto=h*0.035)
    elif que == "taburete":   _taburete(d, X, Y, h*tam, rnd, g)
    elif que == "estante":    _estante(d, X, h*y, T, rnd, g)
    elif que == "banco_fondo":_banco(d, X, Y, T, rnd, g)
    elif que == "olla_suelo": _olla(d, X, Y, h*tam, rnd, g)
    elif que == "mesa":       _mesa_con_cosas(d, X, Y, T, rnd, g, alto=h*0.075)
    elif que == "barandilla":
        _linea(d, [(0, Y), (w, Y)], int(g*2.6), rnd, color=MADERA_OSCURA)
        for k in range(7):
            px = w*(0.07 + 0.145*k)
            _linea(d, [(px, Y), (px, h)], int(g*1.8), rnd, color=MADERA_OSCURA)


def montar(spec: dict, w: int, h: int, semilla: int = 0):
    """Un decorado cualquiera, montado desde su receta y por capas.

    El orden es el mismo para todos, y es lo que hace que un sitio nuevo
    cueste tres lineas de receta en vez de media hora de funcion a medida:

      pared -> lo del fondo -> suelo -> muebles -> GENTE -> muebles de
      delante -> lo colgado -> marco -> resplandores
    """
    receta = _DECORADOS.get(spec.get("interior"))
    if receta is None:
        return escena(spec, w, h, semilla)
    rnd = random.Random(semilla)
    suelo = int(h*spec.get("suelo", 0.66))
    img = Image.new("RGB", (w, h), (226, 214, 192))
    d = ImageDraw.Draw(img)
    g = max(4, int(w*0.006))

    clase = receta["pared"]
    if clase == "cielo_mar":
        _pared(d, w, 0, suelo, "cielo", rnd, g)
        d.rectangle([0, suelo - h*0.06, w, suelo], fill=(92, 140, 186))
    elif clase == "roca":
        _pared(d, w, 0, suelo, "piedra", rnd, g)
        d.rectangle([0, 0, w, suelo], fill=(96, 86, 76))
    else:
        _pared(d, w, 0, suelo, clase, rnd, g)

    for que, x, y, tam in receta["fondo"]:
        _pieza_fondo(d, w, h, suelo, que, x, y, tam, rnd, g)
    # Lo colgado de la pared, DETRAS de todo lo demas: es pared. Lo tenia al
    # final, despues incluso de los muebles de delante, y las espadas del
    # salon del trono salian clavadas en la cabeza de los monigotes.
    for que, x, y, tam in receta["cuelga"]:
        f = COSAS.get(que)
        if f:
            f(d, w*x, h*y, h*tam, rnd, max(2, g//2), TINTA)
    _piso(d, w, h, suelo, receta["piso"], rnd, g)
    for que, x, y, tam in receta["muebles"]:
        _pieza_mueble(d, w, h, suelo, que, x, y, tam, rnd, g)

    # DONDE PISA LA GENTE. Tenia un +0.24 fijo, puesto para la taberna: ahi
    # hay una mesa por delante que les tapa medio cuerpo, asi que hundirlos es
    # lo correcto. En un salon del trono NO hay mesa, y ese mismo +0.24 les
    # dejaba los pies al 90% de la pantalla - mas el 4,5% que recorta la
    # camara -, o sea con las piernas cortadas por el borde y un agujero
    # vacio enorme entre la pared y ellos.
    #
    # Asi que depende del decorado, no de un numero suelto: si hay algo
    # delante, se hunden para que lo tape; si no, pisan cerca de la linea del
    # suelo, que es donde pisa la gente.
    # Y con TOPE: pase lo que pase, los pies no bajan del 86% de la pantalla.
    # Un decorado con mesa mas un personaje alto mas el recorte de camara se
    # comian las piernas por el borde de abajo, y eso no puede depender de que
    # los numeros del decorado esten bien elegidos.
    hunde = h*(0.24 if receta["delante"] else 0.06)
    pies = min(suelo + hunde, h*0.86)
    for f in spec.get("figuras", []):
        alto_f = h*f.get("alto", 0.30)
        figura(d, w*f["x"], pies + alto_f*_RESPIRACION*f.get("_bocanada", 0.0),
               alto_f, rnd, f.get("pose", "de_pie"), f.get("gesto", "neutro"),
               f.get("gorro"), f.get("espejo", False), f.get("pose_mezclada"),
               rasgos=REPARTO.get(f.get("quien") or ""))

    for que, x, y, tam in receta["delante"]:
        _pieza_mueble(d, w, h, suelo, que, x, y, tam, rnd, g)

    if spec.get("cartel"):
        _cartel(d, w*0.50, h*0.09, w*0.44, str(spec["cartel"])[:40], rnd, g)
    for vx, vy in receta["velas"]:
        _vela(d, w*vx, suelo + h*vy, h*0.035, rnd, max(2, g//2))
        img = _resplandor(img, (w*vx, suelo + h*vy - h*0.03), h*0.10)
    return img


# La lista que ve el guion ES la de las recetas, no una copia a mano.
INTERIORES_VALIDOS = DECORADOS_VALIDOS
