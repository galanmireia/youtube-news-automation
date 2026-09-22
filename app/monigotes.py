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
    if spec.get("arbol"): arbol(d, w*spec["arbol"], suelo, h*0.16, rnd)
    g = max(5, int(h*0.006))
    for t in spec.get("tachados", []):
        lado = w*t.get("tam", 0.17)
        cx, cy = w*t["x"], h*t["y"]
        tachado(d, (cx-lado/2, cy-lado/2, cx+lado/2, cy+lado/2), rnd, g)
    oscuro = spec.get("fondo") in _FONDOS_OSCUROS
    tinta = TINTA_CLARA if oscuro else TINTA
    relleno = (38, 44, 66) if oscuro else (255, 255, 255)
    for f in spec.get("figuras", []):
        alto_f = h*f.get("alto", 0.30)
        figura(d, w*f["x"], suelo + alto_f*_RESPIRACION*f.get("_bocanada", 0.0),
               alto_f, rnd,
               f.get("pose","de_pie"), f.get("gesto","neutro"),
               f.get("gorro"), f.get("espejo", False), f.get("pose_mezclada"),
               tinta=tinta, relleno=relleno, rasgos=REPARTO.get(f.get("quien") or ""))
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
        img = (interior(paso, _ANCHO_BASE, _ALTO_BASE, semilla=1000 + n//3)
               if paso.get("interior") else escena(paso, semilla=1000 + n//3))
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
INTERIORES_VALIDOS = ("monasterio", "taberna", "salon_trono")

_MAX_FIGURAS = 4


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
    return {"interior": dentro,
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
_EMPUJE = 0.07


def _camara(img, t):
    """El recorte de este instante: entra despacio y deriva un poco."""
    w, h = img.size
    zoom = 1.0 + _EMPUJE*t
    cw, ch = w/zoom, h/zoom
    # La deriva va hacia el centro, asi que el plano se cierra sobre la accion.
    x = (w-cw)*(0.5 + 0.35*math.cos(math.pi*t))
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
               (x+alto*.26, y-g), (x-alto*.26, y-g)], fill=(92, 88, 82))
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
