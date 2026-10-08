"""EL CANAL EN INGLES: "el porque de las cosas", dibujado a rotulador.

Ella, viendo Whymentary: monigotes de palotes en un folio en blanco, trazo
negro gordo, pocos colores muy vivos, UNA idea por plano con el objeto
grande en medio, y palabras y numeros enormes escritos a mano ("IT'S HOT",
"35°C"). "Me gusta" a la opcion A: hacerlo con nuestro motor, no con
imagenes de IA - gratis, con estilo propio y, sobre todo, que se MUEVE.

Esto pone encima de los monigotes de siempre (animar() con el decorado
"blanco" y el reparto persona / persona_b / nino) lo que es de este canal:
los objetos de ciencia cotidiana, los letreros de rotulador, las cifras con
rayos y las flechas, todo apareciendo con un golpe.

Un plano ("visual") es:
  {"figuras": [{"quien": "persona", "x": .3, "pose": "de_pie", "pose_fin": "brazos_arriba",
                "gesto": "asustado", "efecto": "sudor", "espejo": false, "lleva": "vaso"}],
   "cosas":   [{"que": "cerebro", "x": .7, "y": .45, "tam": .30}],
   "textos":  [{"texto": "IT'S HOT", "x": .3, "y": .2, "tam": .14, "color": "negro", "giro": 4}],
   "flechas": [{"de": [.4, .5], "a": [.6, .5], "color": "rojo"}],
   "cifra":   {"valor": "35°C", "pie": "the wet-bulb limit", "color": "rojo"}}
x, y y tam en fracciones de la pantalla; "y" de una cosa es su CENTRO (sin
"y", apoyada en el suelo).
"""
import logging
import math
import random
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import monigotes as m

logger = logging.getLogger(__name__)
from .garabato_mas import MAS_OBJETOS, REHECHOS
from .garabato_bichos import ANIMALES
from . import garabato_ambiente
from . import mascota as _mascota

# La letra de Whymentary: rotulador redondo, trazo parejo (Architects
# Daughter, SIL Open Font License; la licencia va al lado).
_FUENTE = Path(__file__).parent / "data" / "fuentes" / "ArchitectsDaughter.woff"
TINTA = (22, 22, 22)
COLORES = {
    "negro": TINTA, "rojo": (226, 38, 38), "naranja": (242, 140, 28), "amarillo": (250, 206, 20),
    "azul": (38, 128, 228), "verde": (52, 170, 72), "rosa": (240, 120, 160), "morado": (140, 80, 200),
    "gris": (130, 130, 130), "blanco": (255, 255, 255),
}
_POP = 0.28          # lo que tarda un letrero en aparecer de golpe


@lru_cache(maxsize=64)
def _fuente(px: int):
    try:
        return ImageFont.truetype(str(_FUENTE), max(8, int(px)))
    except OSError:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", max(8, int(px)))


def _color(nombre, defecto="negro"):
    return COLORES.get(str(nombre or defecto).lower(), COLORES[defecto])


# ---------------------------------------------------------------------------
# Los objetos. Todos con la misma firma que las COSAS de monigotes:
#   (d, x, y, t, rnd, g, tinta) con (x, y) el centro de abajo y t la altura.
# Trazo gordo, relleno plano, colores vivos.
# ---------------------------------------------------------------------------

def _contorno(d, pts, relleno, g, rnd):
    d.polygon(pts, fill=relleno)
    m._linea(d, list(pts) + [pts[0]], g, rnd, color=TINTA, temblor=1.0)


def _ovalo(d, caja, relleno, g):
    d.ellipse(caja, fill=relleno, outline=TINTA, width=g)


def _cerebro(d, x, y, t, rnd, g, tinta=TINTA):
    cy, r = y - t*0.5, t*0.5
    _ovalo(d, [x - r*1.2, cy - r*0.85, x + r*1.2, cy + r*0.85], (246, 160, 180), g)
    d.line([(x, cy - r*0.8), (x, cy + r*0.6)], fill=TINTA, width=max(2, g//2))
    rr = random.Random(4)
    for _ in range(9):
        cx, cyy = x + rr.uniform(-r*0.95, r*0.95), cy + rr.uniform(-r*0.55, r*0.55)
        d.arc([cx - r*0.22, cyy - r*0.14, cx + r*0.22, cyy + r*0.14], rr.choice((0, 180)),
              rr.choice((150, 330)), fill=TINTA, width=max(2, g//2))


def _ojo(d, x, y, t, rnd, g, tinta=TINTA):
    cy, r = y - t*0.5, t*0.5
    pts = [(x - r*1.4, cy)] + [(x + r*1.4*math.cos(a), cy - r*0.8*math.sin(a))
                               for a in [i*math.pi/16 for i in range(17)]][::-1] + \
          [(x + r*1.4*math.cos(a), cy + r*0.8*math.sin(a)) for a in [i*math.pi/16 for i in range(17)]]
    d.polygon(pts, fill=(255, 255, 255))
    m._linea(d, pts, g, rnd, temblor=0.6)
    _ovalo(d, [x - r*0.55, cy - r*0.55, x + r*0.55, cy + r*0.55], (60, 140, 220), g)
    d.ellipse([x - r*0.25, cy - r*0.25, x + r*0.25, cy + r*0.25], fill=TINTA)
    d.ellipse([x - r*0.05, cy - r*0.35, x + r*0.15, cy - r*0.15], fill=(255, 255, 255))


def _corazon(d, x, y, t, rnd, g, tinta=TINTA):
    pts = []
    for i in range(40):
        a = i/40*2*math.pi
        px = 16*math.sin(a)**3
        py = 13*math.cos(a) - 5*math.cos(2*a) - 2*math.cos(3*a) - math.cos(4*a)
        pts.append((x + px*t/34, y - t*0.55 - py*t/34))
    _contorno(d, pts, (226, 38, 38), g, rnd)


def _pulmones(d, x, y, t, rnd, g, tinta=TINTA):
    top = y - t
    d.line([(x, top), (x, top + t*0.35)], fill=TINTA, width=g)
    for lado in (-1, 1):
        cx = x + lado*t*0.24
        _ovalo(d, [cx - t*0.2, top + t*0.25, cx + t*0.2, y], (240, 130, 150), g)
        d.line([(x, top + t*0.33), (cx, top + t*0.45)], fill=TINTA, width=max(2, g//2))


def _estomago(d, x, y, t, rnd, g, tinta=TINTA):
    pts = []
    for i in range(30):
        a = i/30*2*math.pi
        px = math.cos(a)*(1 + 0.25*math.sin(a))
        py = math.sin(a)*0.7
        pts.append((x + px*t*0.42 + t*0.05*math.sin(3*a), y - t*0.45 + py*t*0.5))
    _contorno(d, pts, (244, 150, 160), g, rnd)


def _bacteria(d, x, y, t, rnd, g, tinta=TINTA):
    cy = y - t*0.5
    d.rounded_rectangle([x - t*0.45, cy - t*0.22, x + t*0.45, cy + t*0.22], radius=int(t*0.22),
                        fill=(110, 200, 90), outline=TINTA, width=g)
    for k in (-0.2, 0.05, 0.25):
        d.ellipse([x + t*k - t*0.04, cy - t*0.05, x + t*k + t*0.04, cy + t*0.03], fill=(60, 140, 50))
    for lado in (-1, 1):
        pts = [(x + lado*(t*0.45 + i*t*0.05), cy + t*0.06*math.sin(i*1.4)) for i in range(7)]
        m._linea(d, pts, max(2, g//2), rnd, temblor=0.6)
    m._linea(d, [(x - t*0.12, cy - t*0.02), (x - t*0.08, cy - t*0.06)], max(2, g//2), rnd)   # ojitos
    d.ellipse([x - t*0.15, cy - t*0.1, x - t*0.09, cy - t*0.04], fill=TINTA)
    d.ellipse([x + t*0.09, cy - t*0.1, x + t*0.15, cy - t*0.04], fill=TINTA)


def _virus(d, x, y, t, rnd, g, tinta=TINTA):
    cy, r = y - t*0.5, t*0.32
    for k in range(10):
        a = k*math.pi/5
        ex, ey = x + math.cos(a)*r*1.45, cy + math.sin(a)*r*1.45
        d.line([(x + math.cos(a)*r, cy + math.sin(a)*r), (ex, ey)], fill=TINTA, width=max(2, g//2))
        d.ellipse([ex - r*0.16, ey - r*0.16, ex + r*0.16, ey + r*0.16], fill=(230, 80, 80),
                  outline=TINTA, width=max(2, g//3))
    _ovalo(d, [x - r, cy - r, x + r, cy + r], (150, 210, 90), g)
    d.ellipse([x - r*0.45, cy - r*0.3, x - r*0.15, cy], fill=TINTA)
    d.ellipse([x + r*0.15, cy - r*0.3, x + r*0.45, cy], fill=TINTA)
    d.arc([x - r*0.4, cy + r*0.05, x + r*0.4, cy + r*0.55], 200, 340, fill=TINTA, width=max(2, g//2))


def _cebolla(d, x, y, t, rnd, g, tinta=TINTA):
    cy, r = y - t*0.42, t*0.42
    pts = [(x + r*math.cos(a)*(1 if math.sin(a) > 0 else 1 - 0.35*(-math.sin(a))**3),
            cy + r*math.sin(a)) for a in [i*math.pi/20 for i in range(40)]]
    pts = [(px, py - (r*0.45*(1 - abs(px - x)/r)**2 if py < cy else 0)) for px, py in pts]
    _contorno(d, pts, (196, 120, 190), g, rnd)
    for k in (-0.4, 0, 0.4):
        d.arc([x - r*0.9 + abs(k)*r, cy - r*0.8, x + r*0.9 - abs(k)*r, cy + r*0.95], 300, 60 if k else 420,
              fill=(150, 80, 140), width=max(2, g//2))
    d.line([(x, cy - r*1.2), (x, cy - r*1.55)], fill=(80, 160, 60), width=g)


def _termometro(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*0.16
    d.rounded_rectangle([x - w/2, y - t, x + w/2, y - t*0.18], radius=int(w/2), fill=(255, 255, 255),
                        outline=TINTA, width=g)
    _ovalo(d, [x - w, y - t*0.3, x + w, y], (226, 38, 38), g)
    d.rectangle([x - w*0.22, y - t*0.8, x + w*0.22, y - t*0.22], fill=(226, 38, 38))
    for k in range(5):
        yy = y - t*0.35 - k*t*0.12
        d.line([(x + w/2, yy), (x + w/2 + w*0.5, yy)], fill=TINTA, width=max(2, g//2))


def _ventilador(d, x, y, t, rnd, g, tinta=TINTA):
    cy, r = y - t*0.62, t*0.36
    d.line([(x, cy), (x, y - t*0.06)], fill=TINTA, width=g)
    d.ellipse([x - t*0.22, y - t*0.08, x + t*0.22, y + t*0.02], fill=(70, 130, 200), outline=TINTA, width=g)
    for k in range(3):
        a = k*2*math.pi/3 + 0.3
        bx, by = x + math.cos(a)*r*0.6, cy + math.sin(a)*r*0.6
        d.ellipse([bx - r*0.38, by - r*0.24, bx + r*0.38, by + r*0.24], fill=(90, 160, 230),
                  outline=TINTA, width=max(2, g//2))
    d.ellipse([x - r, cy - r, x + r, cy + r], outline=TINTA, width=g)
    for k in range(8):
        a = k*math.pi/4
        d.line([(x, cy), (x + math.cos(a)*r, cy + math.sin(a)*r)], fill=(120, 120, 120), width=max(1, g//4))
    d.ellipse([x - r*0.12, cy - r*0.12, x + r*0.12, cy + r*0.12], fill=TINTA)


def _cama(d, x, y, t, rnd, g, tinta=TINTA):
    a = t*1.9
    d.rectangle([x - a/2, y - t*0.45, x + a/2, y - t*0.15], fill=(90, 140, 220), outline=TINTA, width=g)
    d.rectangle([x - a/2 - g, y - t*0.9, x - a/2 + t*0.08, y], fill=(150, 100, 60), outline=TINTA, width=g)
    d.rectangle([x + a/2 - t*0.08, y - t*0.6, x + a/2 + g, y], fill=(150, 100, 60), outline=TINTA, width=g)
    d.ellipse([x - a/2 + t*0.12, y - t*0.62, x - a/2 + t*0.55, y - t*0.42], fill=(255, 255, 255),
              outline=TINTA, width=max(2, g//2))


def _reloj(d, x, y, t, rnd, g, tinta=TINTA):
    cy, r = y - t*0.48, t*0.4
    for lado in (-1, 1):
        d.ellipse([x + lado*r*0.75 - r*0.3, cy - r*1.2, x + lado*r*0.75 + r*0.3, cy - r*0.7],
                  fill=(226, 38, 38), outline=TINTA, width=max(2, g//2))
        d.line([(x + lado*r*0.6, cy + r*0.8), (x + lado*r*0.85, y)], fill=TINTA, width=g)
    _ovalo(d, [x - r, cy - r, x + r, cy + r], (255, 255, 255), g)
    d.line([(x, cy), (x, cy - r*0.65)], fill=TINTA, width=g)
    d.line([(x, cy), (x + r*0.45, cy + r*0.2)], fill=TINTA, width=g)


def _telefono(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*0.5
    d.rounded_rectangle([x - w/2, y - t, x + w/2, y], radius=int(w*0.15), fill=(40, 40, 46),
                        outline=TINTA, width=g)
    d.rounded_rectangle([x - w/2 + g*1.5, y - t + g*2.5, x + w/2 - g*1.5, y - g*3], radius=int(w*0.06),
                        fill=(120, 200, 250))


def _gota(d, x, y, t, rnd, g, tinta=TINTA):
    cy, r = y - t*0.32, t*0.32
    pts = [(x, y - t)] + [(x + r*math.cos(a), cy + r*math.sin(a)) for a in
                          [-math.pi/6 + i*(4*math.pi/3)/24 for i in range(25)]]
    _contorno(d, pts, (60, 150, 235), g, rnd)
    d.arc([x - r*0.55, cy - r*0.5, x - r*0.05, cy + r*0.5], 120, 220, fill=(255, 255, 255), width=max(2, g//2))


def _calavera(d, x, y, t, rnd, g, tinta=TINTA):
    cy, r = y - t*0.6, t*0.4
    _ovalo(d, [x - r, cy - r, x + r, cy + r*0.8], (240, 240, 236), g)
    d.rectangle([x - r*0.5, cy + r*0.6, x + r*0.5, y], fill=(240, 240, 236), outline=TINTA, width=g)
    for lado in (-1, 1):
        d.ellipse([x + lado*r*0.42 - r*0.25, cy - r*0.1, x + lado*r*0.42 + r*0.25, cy + r*0.4], fill=TINTA)
    d.polygon([(x, cy + r*0.45), (x - r*0.12, cy + r*0.65), (x + r*0.12, cy + r*0.65)], fill=TINTA)
    for k in (-0.25, 0, 0.25):
        d.line([(x + r*k, cy + r*0.8), (x + r*k, y - r*0.05)], fill=TINTA, width=max(2, g//2))


def _taza(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*0.7
    d.arc([x + w*0.3, y - t*0.65, x + w*0.85, y - t*0.2], 270, 90, fill=TINTA, width=g)
    _contorno(d, [(x - w/2, y - t*0.75), (x + w/2, y - t*0.75), (x + w*0.4, y), (x - w*0.4, y)],
              (255, 255, 255), g, rnd)
    d.ellipse([x - w/2, y - t*0.82, x + w/2, y - t*0.68], fill=(110, 70, 40), outline=TINTA, width=max(2, g//2))
    for k in (-0.15, 0.12):
        pts = [(x + w*k + t*0.04*math.sin(i), y - t*0.9 - i*t*0.05) for i in range(6)]
        m._linea(d, pts, max(2, g//2), rnd, color=(150, 150, 150))


def _pastilla(d, x, y, t, rnd, g, tinta=TINTA):
    cy = y - t*0.3
    d.rounded_rectangle([x - t*0.5, cy - t*0.2, x, cy + t*0.2], radius=int(t*0.2), fill=(226, 38, 38),
                        outline=TINTA, width=g)
    d.rounded_rectangle([x - t*0.02, cy - t*0.2, x + t*0.5, cy + t*0.2], radius=int(t*0.2),
                        fill=(255, 255, 255), outline=TINTA, width=g)


def _luna(d, x, y, t, rnd, g, tinta=TINTA):
    cy, r = y - t*0.5, t*0.45
    _ovalo(d, [x - r, cy - r, x + r, cy + r], (250, 220, 90), g)
    d.ellipse([x - r*0.35, cy - r*1.05, x + r*1.25, cy + r*0.75], fill=(252, 252, 250))


def _hielo(d, x, y, t, rnd, g, tinta=TINTA):
    a = t*0.8
    _contorno(d, [(x - a/2, y - a), (x + a/2, y - a), (x + a/2, y), (x - a/2, y)], (190, 230, 250), g, rnd)
    _contorno(d, [(x - a/2, y - a), (x - a/4, y - a*1.2), (x + a*0.75, y - a*1.2), (x + a/2, y - a)],
              (220, 245, 255), g, rnd)
    m._linea(d, [(x - a*0.3, y - a*0.75), (x - a*0.1, y - a*0.55)], max(2, g//2), rnd, color=(255, 255, 255))


def _planta(d, x, y, t, rnd, g, tinta=TINTA):
    _contorno(d, [(x - t*0.25, y - t*0.35), (x + t*0.25, y - t*0.35), (x + t*0.18, y), (x - t*0.18, y)],
              (200, 110, 70), g, rnd)
    m._linea(d, [(x, y - t*0.35), (x, y - t*0.85)], g, rnd, color=(60, 140, 60))
    for lado, h in ((-1, 0.6), (1, 0.75), (-1, 0.9)):
        cx = x + lado*t*0.16
        d.ellipse([cx - t*0.16, y - t*h - t*0.08, cx + t*0.16, y - t*h + t*0.08], fill=(90, 190, 80),
                  outline=TINTA, width=max(2, g//2))


def _hamburguesa(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*1.2
    d.chord([x - w/2, y - t, x + w/2, y - t*0.3], 180, 360, fill=(230, 160, 70), outline=TINTA, width=g)
    d.rectangle([x - w/2, y - t*0.62, x + w/2, y - t*0.5], fill=(90, 190, 80), outline=TINTA, width=max(2, g//2))
    d.rounded_rectangle([x - w/2, y - t*0.5, x + w/2, y - t*0.3], radius=int(t*0.08), fill=(120, 70, 40),
                        outline=TINTA, width=g)
    d.rounded_rectangle([x - w/2, y - t*0.3, x + w/2, y], radius=int(t*0.1), fill=(230, 160, 70),
                        outline=TINTA, width=g)


def _bombilla(d, x, y, t, rnd, g, tinta=TINTA):
    cy, r = y - t*0.62, t*0.36
    _ovalo(d, [x - r, cy - r, x + r, cy + r], (255, 230, 80), g)
    d.rectangle([x - r*0.45, cy + r*0.8, x + r*0.45, y], fill=(170, 170, 170), outline=TINTA, width=g)
    for k in range(7):
        a = -math.pi + k*math.pi/6
        d.line([(x + math.cos(a)*r*1.25, cy + math.sin(a)*r*1.25), (x + math.cos(a)*r*1.6, cy + math.sin(a)*r*1.6)],
               fill=(250, 200, 20), width=g)


def _peligro(d, x, y, t, rnd, g, tinta=TINTA):
    _contorno(d, [(x, y - t), (x + t*0.58, y), (x - t*0.58, y)], (250, 206, 20), g, rnd)
    d.line([(x, y - t*0.68), (x, y - t*0.3)], fill=TINTA, width=int(g*1.6))
    d.ellipse([x - g, y - t*0.2 - g, x + g, y - t*0.2 + g], fill=TINTA)


def _bien(d, x, y, t, rnd, g, tinta=TINTA):
    m._linea(d, [(x - t*0.45, y - t*0.5), (x - t*0.1, y - t*0.1), (x + t*0.5, y - t*0.95)],
             int(g*2.2), rnd, color=(52, 170, 72), temblor=0.8)


def _mal(d, x, y, t, rnd, g, tinta=TINTA):
    for a, b in (((-0.4, 0.9), (0.4, 0.1)), ((0.4, 0.9), (-0.4, 0.1))):
        m._linea(d, [(x + t*a[0], y - t*a[1]), (x + t*b[0], y - t*b[1])], int(g*2.2), rnd,
                 color=(226, 38, 38), temblor=0.8)


def _igual(d, x, y, t, rnd, g, tinta=TINTA):
    for yy in (0.62, 0.38):
        d.rounded_rectangle([x - t*0.45, y - t*yy - t*0.08, x + t*0.45, y - t*yy + t*0.08],
                            radius=int(t*0.05), fill=(226, 38, 38), outline=TINTA, width=max(2, g//2))


def _interrogacion(d, x, y, t, rnd, g, tinta=TINTA):
    d.text((x, y - t*0.5), "?", font=_fuente(t), fill=(242, 140, 28), anchor="mm",
           stroke_width=max(2, int(t*0.03)), stroke_fill=(242, 140, 28))


def _calor(d, x, y, t, rnd, g, tinta=TINTA):
    """Las rayas de calor que suben, rojas y naranjas."""
    for k in range(5):
        px = x - t*0.4 + k*t*0.2
        color = (226, 38, 38) if k % 2 else (242, 140, 28)
        pts = [(px + t*0.04*math.sin(i*0.9 + k), y - i*t*0.1) for i in range(10)]
        m._linea(d, pts, max(3, int(g*0.8)), rnd, color=color, temblor=0.5)


def _frio(d, x, y, t, rnd, g, tinta=TINTA):
    """Un copo de nieve azul."""
    cy, r = y - t*0.5, t*0.45
    for k in range(3):
        a = k*math.pi/3
        m._linea(d, [(x - math.cos(a)*r, cy - math.sin(a)*r), (x + math.cos(a)*r, cy + math.sin(a)*r)],
                 g, rnd, color=(60, 150, 235), temblor=0.5)


def _dinero(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*1.4
    d.rounded_rectangle([x - w/2, y - t*0.6, x + w/2, y], radius=int(t*0.06), fill=(120, 200, 110),
                        outline=TINTA, width=g)
    d.text((x, y - t*0.3), "$", font=_fuente(t*0.5), fill=(40, 110, 40), anchor="mm")


def _pluma(d, x, y, t, rnd, g, tinta=TINTA):
    """La pluma de hacer cosquillas: curva, con sus barbas."""
    base, punta = (x - t*0.15, y), (x + t*0.2, y - t)
    pts = []
    for i in range(21):
        s = i/20
        cx = base[0] + (punta[0] - base[0])*s + t*0.12*math.sin(s*math.pi)
        cy = base[1] + (punta[1] - base[1])*s
        pts.append((cx, cy))
    for i in range(3, 20):
        cx, cy = pts[i]
        ancho = t*0.16*math.sin((i - 3)/17*math.pi)
        for lado in (-1, 1):
            d.line([(cx, cy), (cx + lado*ancho, cy - ancho*0.5)], fill=(120, 190, 240), width=max(3, g//2))
    m._linea(d, pts, max(3, g//2), rnd, color=TINTA, temblor=0.4)


def _bicho(d, x, y, t, rnd, g, tinta=TINTA):
    """Un bicho que trepa: cuerpo, cabeza, seis patas y antenas."""
    cy, r = y - t*0.4, t*0.28
    for k in (-1, 0, 1):
        for lado in (-1, 1):
            d.line([(x + k*r*0.6, cy), (x + k*r*0.8 + lado*0, cy + lado*r*1.1)], fill=TINTA, width=max(3, g//2))
    _ovalo(d, [x - r*1.1, cy - r*0.7, x + r*0.7, cy + r*0.7], (90, 70, 60), g)
    _ovalo(d, [x + r*0.5, cy - r*0.5, x + r*1.3, cy + r*0.5], (90, 70, 60), g)
    for lado in (-1, 1):
        d.line([(x + r*1.1, cy - r*0.3*lado), (x + r*1.6, cy - r*0.9*lado)], fill=TINTA, width=max(2, g//3))
    d.ellipse([x + r*0.9, cy - r*0.25, x + r*1.1, cy - r*0.05], fill=(255, 255, 255))


def _rata(d, x, y, t, rnd, g, tinta=TINTA):
    """La rata de laboratorio: gris, orejas rosas, cola larga."""
    cy, r = y - t*0.35, t*0.35
    pts = [(x - r*1.3, cy), (x - r*1.9, cy - r*0.3), (x - r*2.4, cy + r*0.1)]
    m._linea(d, pts, max(3, g//2), rnd, color=(230, 150, 160))
    _ovalo(d, [x - r*1.4, cy - r*0.75, x + r*0.6, cy + r*0.75], (170, 170, 175), g)
    d.polygon([(x + r*0.4, cy - r*0.5), (x + r*1.5, cy + r*0.1), (x + r*0.4, cy + r*0.5)],
              fill=(170, 170, 175), outline=TINTA)
    _ovalo(d, [x + r*0.2, cy - r*1.0, x + r*0.7, cy - r*0.45], (240, 170, 180), max(2, g//2))
    d.ellipse([x + r*0.75, cy - r*0.2, x + r*0.9, cy - r*0.05], fill=TINTA)
    d.ellipse([x + r*1.4, cy + r*0.0, x + r*1.6, cy + r*0.2], fill=(240, 120, 140))


def _maquina_cosquillas(d, x, y, t, rnd, g, tinta=TINTA):
    """La maquina de cosquillas de los experimentos: una caja con palanca y
    un brazo que acaba en una bola de espuma."""
    d.rectangle([x - t*0.45, y - t*0.35, x + t*0.1, y], fill=(200, 200, 205), outline=TINTA, width=g)
    d.ellipse([x - t*0.3, y - t*0.25, x - t*0.15, y - t*0.1], fill=(226, 38, 38), outline=TINTA, width=max(2, g//3))
    m._linea(d, [(x - t*0.35, y - t*0.35), (x - t*0.45, y - t*0.6)], g, rnd)            # palanca
    d.ellipse([x - t*0.5, y - t*0.66, x - t*0.4, y - t*0.56], fill=TINTA)
    m._linea(d, [(x + t*0.1, y - t*0.2), (x + t*0.45, y - t*0.55)], g, rnd)              # brazo
    _ovalo(d, [x + t*0.38, y - t*0.72, x + t*0.6, y - t*0.5], (250, 210, 60), g)          # espuma


def _gafas_vr(d, x, y, t, rnd, g, tinta=TINTA):
    """Unas gafas de realidad virtual."""
    cy = y - t*0.4
    d.rounded_rectangle([x - t*0.55, cy - t*0.25, x + t*0.55, cy + t*0.25], radius=int(t*0.1),
                        fill=(50, 50, 60), outline=TINTA, width=g)
    for lado in (-1, 1):
        d.ellipse([x + lado*t*0.27 - t*0.15, cy - t*0.12, x + lado*t*0.27 + t*0.15, cy + t*0.15],
                  fill=(120, 200, 250), outline=TINTA, width=max(2, g//2))
    d.arc([x - t*0.7, cy - t*0.5, x + t*0.7, cy + t*0.3], 180, 360, fill=TINTA, width=max(3, g//2))


def _palanca(d, x, y, t, rnd, g, tinta=TINTA):
    d.rounded_rectangle([x - t*0.3, y - t*0.2, x + t*0.3, y], radius=int(t*0.05), fill=(130, 130, 140),
                        outline=TINTA, width=g)
    m._linea(d, [(x, y - t*0.2), (x + t*0.2, y - t*0.85)], int(g*1.2), rnd)
    _ovalo(d, [x + t*0.1, y - t*0.98, x + t*0.3, y - t*0.78], (226, 38, 38), g)


def _bobina(d, x, y, t, rnd, g, tinta=TINTA):
    """La bobina magnetica de estimular el cerebro: un ocho de cobre con mango."""
    cy, r = y - t*0.6, t*0.22
    for lado in (-1, 1):
        for k in range(3):
            rr = r*(1 - k*0.25)
            d.ellipse([x + lado*r - rr, cy - rr, x + lado*r + rr, cy + rr], outline=(200, 120, 50), width=g)
    d.rounded_rectangle([x - t*0.06, cy + r, x + t*0.06, y], radius=int(t*0.03), fill=(60, 60, 70),
                        outline=TINTA, width=max(2, g//2))
    for k in range(3):                               # el zumbido
        d.arc([x - r*2.6 - k*t*0.05, cy - r*1.5 - k*t*0.05, x + r*2.6 + k*t*0.05, cy + r*0.8],
              200, 340, fill=(140, 80, 200), width=max(2, g//3))


def _mano(d, x, y, t, rnd, g, tinta=TINTA, relleno=(255, 224, 196)):
    """Una mano abierta: palma y cinco dedos."""
    cy = y - t*0.35
    _ovalo(d, [x - t*0.22, cy - t*0.2, x + t*0.22, cy + t*0.3], relleno, g)
    for k, (dx, largo) in enumerate(((-0.18, 0.32), (-0.07, 0.42), (0.05, 0.44), (0.16, 0.38))):
        d.rounded_rectangle([x + t*dx - t*0.05, cy - t*0.2 - t*largo, x + t*dx + t*0.05, cy - t*0.12],
                            radius=int(t*0.05), fill=relleno, outline=TINTA, width=max(2, g//2))
    d.rounded_rectangle([x - t*0.38, cy - t*0.05, x - t*0.12, cy + t*0.07], radius=int(t*0.05),
                        fill=relleno, outline=TINTA, width=max(2, g//2))


def _marioneta(d, x, y, t, rnd, g, tinta=TINTA):
    """La mano que se mueve sola: colgada de hilos atados a la punta de cada
    dedo, con su cruceta arriba y rayitas de movimiento."""
    tm = t*0.72
    _mano(d, x, y, tm, rnd, g)
    cy = y - tm*0.35
    puntas = [(x + tm*dx, cy - tm*0.2 - tm*largo) for dx, largo in
              ((-0.18, 0.32), (-0.07, 0.42), (0.05, 0.44), (0.16, 0.38))] + [(x - tm*0.38, cy)]
    arriba = y - t
    d.line([(x - t*0.32, arriba), (x + t*0.32, arriba)], fill=(150, 100, 60), width=int(g*1.4))
    d.line([(x, arriba - t*0.06), (x, arriba + t*0.06)], fill=(150, 100, 60), width=int(g*1.4))
    for k, (px, py) in enumerate(sorted(puntas)):     # el pulgar, al hilo de la izquierda
        ax = x - t*0.3 + k*t*0.15
        d.line([(ax, arriba), (px, py)], fill=(110, 110, 110), width=max(2, g//4))
    for lado in (-1, 1):                              # se mueve
        for k in range(2):
            cx = x + lado*(tm*0.5 + k*t*0.08)
            d.arc([cx - t*0.05, cy - t*0.25, cx + t*0.05, cy + t*0.05], 300 if lado > 0 else 120,
                  60 if lado > 0 else 240, fill=TINTA, width=max(2, g//2))


def _mano_robot(d, x, y, t, rnd, g, tinta=TINTA):
    _mano(d, x, y, t, rnd, g, relleno=(180, 185, 195))
    for k in (-0.1, 0.06):
        d.ellipse([x + t*k - t*0.03, y - t*0.32, x + t*k + t*0.03, y - t*0.26], fill=TINTA)


def _yinyang(d, x, y, t, rnd, g, tinta=TINTA):
    """Yo y el otro: el circulo partido en dos, blanco y negro."""
    cy, r = y - t*0.5, t*0.45
    d.ellipse([x - r, cy - r, x + r, cy + r], fill=(255, 255, 255))
    d.pieslice([x - r, cy - r, x + r, cy + r], 90, 270, fill=TINTA)
    d.ellipse([x - r/2, cy - r, x + r/2, cy], fill=(255, 255, 255))
    d.ellipse([x - r/2, cy, x + r/2, cy + r], fill=TINTA)
    d.ellipse([x - r*0.12, cy - r*0.62, x + r*0.12, cy - r*0.38], fill=TINTA)
    d.ellipse([x - r*0.12, cy + r*0.38, x + r*0.12, cy + r*0.62], fill=(255, 255, 255))
    d.ellipse([x - r, cy - r, x + r, cy + r], outline=TINTA, width=g)


def _suaviza(pts, vueltas=3):
    """Esquinas redondeadas (Chaikin): de poligono a dibujo."""
    for _ in range(vueltas):
        nuevos = []
        for a, b in zip(pts, pts[1:] + pts[:1]):
            nuevos += [(a[0]*0.75 + b[0]*0.25, a[1]*0.75 + b[1]*0.25),
                       (a[0]*0.25 + b[0]*0.75, a[1]*0.25 + b[1]*0.75)]
        pts = nuevos
    return pts


def _pie(d, x, y, t, rnd, g, tinta=TINTA):
    """La planta del pie con sus cinco deditos: el pie de las cosquillas de
    toda la vida ("mejora el dibujo del pie"; el de perfil parecia una bota)."""
    piel, almohadilla = (255, 222, 196), (250, 196, 182)
    contorno = [(0.02, 0), (0.15, -0.07), (0.18, -0.28), (0.2, -0.5), (0.23, -0.66), (0.21, -0.77),
                (0.1, -0.82), (-0.08, -0.84), (-0.2, -0.79), (-0.23, -0.66), (-0.17, -0.52),
                (-0.09, -0.4), (-0.09, -0.24), (-0.14, -0.09), (-0.06, 0.0)]
    pts = _suaviza([(x + t*a, y + t*b) for a, b in contorno])
    dedos = [(-0.13, -0.92, 0.075, 0.095), (-0.01, -0.95, 0.055, 0.07), (0.075, -0.93, 0.048, 0.06),
             (0.145, -0.89, 0.042, 0.052), (0.2, -0.83, 0.036, 0.045)]
    for cx, cy, rx, ry in dedos:
        d.ellipse([x + t*(cx - rx), y + t*(cy - ry), x + t*(cx + rx), y + t*(cy + ry)], fill=piel,
                  outline=TINTA, width=max(2, int(g*0.8)))
    d.polygon(pts, fill=piel)
    d.line(pts + [pts[0]], fill=TINTA, width=g, joint="curve")
    # las almohadillas de la planta y del talon, y un par de arruguitas
    d.ellipse([x - t*0.16, y - t*0.74, x + t*0.18, y - t*0.58], fill=almohadilla)
    d.ellipse([x - t*0.1, y - t*0.2, x + t*0.12, y - t*0.04], fill=almohadilla)
    for k in (0, 1):
        yy = y - t*(0.42 - k*0.06)
        d.arc([x - t*0.02, yy - t*0.03, x + t*0.12, yy + t*0.03], 200, 340, fill=(225, 165, 150),
              width=max(2, g//2))


def _mono(d, x, y, t, rnd, g, tinta=TINTA):
    """Un mono (chimpance): cuerpo marron, cara clara, orejas grandes."""
    marron, cara = (130, 90, 60), (236, 200, 160)
    cy = y - t*0.62
    _ovalo(d, [x - t*0.22, y - t*0.45, x + t*0.22, y], marron, g)                 # cuerpo
    for lado in (-1, 1):
        _ovalo(d, [x + lado*t*0.25 - t*0.07, cy - t*0.08, x + lado*t*0.25 + t*0.07, cy + t*0.08], cara, max(2, g//2))
        m._linea(d, [(x + lado*t*0.18, y - t*0.35), (x + lado*t*0.35, y - t*0.1)], g, rnd, color=marron)
    _ovalo(d, [x - t*0.2, cy - t*0.2, x + t*0.2, cy + t*0.18], marron, g)          # cabeza
    _ovalo(d, [x - t*0.14, cy - t*0.08, x + t*0.14, cy + t*0.16], cara, max(2, g//2))
    for lado in (-1, 1):
        d.ellipse([x + lado*t*0.06 - t*0.02, cy - t*0.04, x + lado*t*0.06 + t*0.02, cy], fill=TINTA)
    d.arc([x - t*0.06, cy + t*0.02, x + t*0.06, cy + t*0.1], 20, 160, fill=TINTA, width=max(2, g//3))


def _escaner(d, x, y, t, rnd, g, tinta=TINTA):
    """El escaner del cerebro (resonancia): el anillo grande con su camilla."""
    cy, r = y - t*0.55, t*0.45
    _ovalo(d, [x - r, cy - r, x + r, cy + r], (230, 232, 238), g)
    _ovalo(d, [x - r*0.5, cy - r*0.5, x + r*0.5, cy + r*0.5], (60, 70, 90), g)
    d.rectangle([x - t*0.9, cy + r*0.2, x + t*0.1, cy + r*0.35], fill=(120, 170, 220), outline=TINTA, width=max(2, g//2))
    d.rectangle([x - t*0.85, cy + r*0.35, x - t*0.75, y], fill=(150, 150, 160), outline=TINTA, width=max(2, g//2))
    d.ellipse([x + r*0.55, cy - r*0.75, x + r*0.75, cy - r*0.55], fill=(52, 170, 72))


def _joystick(d, x, y, t, rnd, g, tinta=TINTA):
    d.rounded_rectangle([x - t*0.35, y - t*0.25, x + t*0.35, y], radius=int(t*0.08), fill=(60, 60, 70),
                        outline=TINTA, width=g)
    m._linea(d, [(x, y - t*0.25), (x - t*0.08, y - t*0.75)], int(g*1.2), rnd)
    _ovalo(d, [x - t*0.2, y - t*0.95, x + t*0.04, y - t*0.7], (226, 38, 38), g)
    d.ellipse([x + t*0.12, y - t*0.17, x + t*0.24, y - t*0.07], fill=(250, 206, 20), outline=TINTA)

OBJETOS = {
    "cerebro": _cerebro, "ojo": _ojo, "corazon": _corazon, "pulmones": _pulmones,
    "estomago": _estomago, "bacteria": _bacteria, "virus": _virus, "cebolla": _cebolla,
    "termometro": _termometro, "ventilador": _ventilador, "cama": _cama, "despertador": _reloj,
    "movil": _telefono, "gota": _gota, "calavera": _calavera, "taza": _taza, "pastilla": _pastilla,
    "luna": _luna, "hielo": _hielo, "planta": _planta, "hamburguesa": _hamburguesa,
    "bombilla": _bombilla, "peligro": _peligro, "bien": _bien, "mal": _mal, "igual": _igual,
    "interrogacion": _interrogacion, "calor": _calor, "frio": _frio, "billete": _dinero,
    "pluma": _pluma, "bicho": _bicho, "rata": _rata, "maquina_cosquillas": _maquina_cosquillas,
    "gafas_vr": _gafas_vr, "palanca": _palanca, "bobina": _bobina, "mano": _mano,
    "marioneta": _marioneta, "mano_robot": _mano_robot, "yinyang": _yinyang, "pie": _pie,
    "mono": _mono, "escaner": _escaner, "joystick": _joystick,
}
# La biblioteca grande, mismo estilo y a color (garabato_mas.py), y los
# rehechos, que ganan a los de antes.
for _n, _f in MAS_OBJETOS.items():
    OBJETOS.setdefault(_n, _f)
for _n, _f in REHECHOS.items():
    if _n in OBJETOS:
        OBJETOS[_n] = _f
# Y los animales, de la familia de Mokordo (gorditos, con sus ojazos).
for _n, _f in ANIMALES.items():
    if _n in OBJETOS:
        OBJETOS[_n] = _f
# Lo que el guion pide con otro nombre: "igualdad", "signo_igual"...
_ALIAS_OBJETOS = {"gear": "engranaje", "rueda_dentada": "engranaje", "engranajes": "engranaje",
                  "horse": "caballo", "camel": "camello", "elephant": "elefante", "pig": "cerdo",
                  "chicken": "gallina", "hen": "gallina", "lion": "leon", "rabbit": "conejo",
                  "turtle": "tortuga", "frog": "rana", "sheep": "oveja", "cat": "gato", "fish": "pez",
                  "bird": "pajaro", "bee": "abeja", "spider": "arana", "snake": "serpiente", "cow": "vaca",
                  "shark": "tiburon", "monkey": "mono", "rat": "rata", "mouse": "rata",
                  "igualdad": "igual", "signo_igual": "igual", "equals": "igual", "equal": "igual",
                  "equal_sign": "igual", "igual_que": "igual", "perro_pata": "perro", "dog": "perro",
                  "pregunta": "interrogacion", "question": "interrogacion", "telefono": "movil",
                  "phone": "movil", "brain": "cerebro", "heart": "corazon", "feather": "pluma"}


def nombre_objeto(que) -> str:
    que = str(que or "").strip().lower()
    return _ALIAS_OBJETOS.get(que, que)


# Lo que el guion pide como POSTURA y es una cara: "pose asustado".
_POSE_ES_GESTO = {"asustado": "asustado", "riendo": "riendo", "sorprendido": "sorpresa",
                  "contento": "contento", "triste": "triste", "enfadado": "enfadado",
                  "gritando": "grito", "bostezando": "bostezo"}
# Lo que el guion pide como cara y en realidad es un efecto (o al reves).
_GESTO_ES_EFECTO = {"confuso": "confuso", "mareado": "mareo", "llorando": "lagrimas",
                    "dormido": "zzz", "sudando": "sudor", "enamorado": "enamorado"}
# Y los de monigotes que pegan en este canal.
_DE_MONIGOTES = ("sol", "nube", "fuego", "perro", "caballo", "vaso", "libro", "arbol", "casa",
                 "dinero", "pelota", "maletin", "calendario", "periodico", "espada", "carta",
                 "barco", "toro", "cofre", "antorcha")
OBJETOS_VALIDOS = tuple(OBJETOS) + tuple(n for n in _DE_MONIGOTES if n in m.COSAS)
OBJETOS_TODOS = {**{n: m.COSAS[n] for n in _DE_MONIGOTES if n in m.COSAS}, **OBJETOS, **REHECHOS, **ANIMALES}
# Se registran en monigotes para que montar() los pinte como cualquier cosa.
for _n, _f in OBJETOS.items():
    m.COSAS.setdefault(_n, _f)
    # En la mano, grandes: en un folio en blanco es lo que hay que ver.
    m._TAM_LLEVADO.setdefault(_n, 0.38)

QUIENES = ("persona", "persona_b", "nino", "abuelo")
# La cabeza grande de los monigotes de Whymentary.
# Un poco mas bajitos, para que con la cabeza grande quepan las ondas de
# calor, los letreros y lo que tengan encima.
for _q in QUIENES:
    m.REPARTO[_q]["cabeza"] = 1.65
    m.REPARTO[_q]["alto"] = round(m.REPARTO[_q]["alto"]*0.85, 3)

# LO QUE SOLO EXISTE EN WHY THOUGH, visto en Whymentary: las manos en la
# cabeza del que se agobia, el muerto tumbado (ojos en X, lengua fuera) y las
# ondas de calor o de frio alrededor. Se añaden despues de las listas de
# monigotes a proposito: el guion de España Contada no los ofrece.
m._POSES["manos_cabeza"] = {
    "cuello": (0, -.70), "cadera": (0, -.38),
    "brazos": [[(0, -.66), (-.36, -.78), (-.25, -.96)], [(0, -.66), (.36, -.78), (.25, -.96)]],
    "piernas": [[(0, -.38), (-.10, -.19), (-.14, 0)], [(0, -.38), (.10, -.19), (.14, 0)]]}
POSES_EXTRA = ("manos_cabeza", "tumbado")
GESTOS_EXTRA = ("muerto",)
EFECTOS_EXTRA = ("calor", "frio")


# ---------------------------------------------------------------------------
# Lo que va encima: letreros, cifras y flechas, que aparecen de golpe.
# ---------------------------------------------------------------------------

def _escala_pop(t: float) -> float:
    """Aparece de golpe: de nada a un poco mas grande y se asienta."""
    if t <= 0:
        return 0.0
    if t >= _POP:
        return 1.0
    p = t/_POP
    return 1.15*math.sin(p*math.pi/2) if p < 0.7 else 1.15 - 0.15*(p - 0.7)/0.3


@lru_cache(maxsize=256)
def _pieza_letrero(texto, px, relleno, giro):
    """El letrero dibujado UNA vez, en un recorte de su tamaño: dibujarlo a
    pantalla completa en cada fotograma triplicaba lo que tarda el montaje."""
    f = _fuente(px)
    # Sin borde negro, como en Whymentary: la letra de su color y un poco
    # engordada con su mismo color, que el trazo de la fuente es fino.
    trazo = max(1, int(px*0.02))
    caja = f.getbbox(texto, anchor="mm", stroke_width=trazo)
    w, h = caja[2] - caja[0] + 8, caja[3] - caja[1] + 8
    pieza = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(pieza).text((w/2, h/2), texto, font=f, fill=relleno, anchor="mm",
                               stroke_width=trazo, stroke_fill=relleno)
    if giro:
        pieza = pieza.rotate(giro, expand=True, resample=Image.BICUBIC)
    return pieza


def _letrero(img, texto, xy, px, relleno, giro, escala=1.0):
    if escala <= 0.05 or not texto:
        return
    # El tamaño en pasos de 2 px: asi el "pop" reutiliza piezas ya hechas.
    px = max(8, int(px*escala)//2*2)
    pieza = _pieza_letrero(texto, px, tuple(relleno), round(float(giro), 1))
    img.paste(pieza, (int(xy[0] - pieza.width/2), int(xy[1] - pieza.height/2)), pieza)


def _que_quepa(texto: str, px: float, ancho: float) -> float:
    """El tamaño de letra para que el letrero no se salga de la pantalla."""
    f = _fuente(px)
    largo = f.getlength(texto) or 1
    return px*min(1.0, ancho/largo)


def encima(img: Image.Image, visual: dict, t: float, segundos: float) -> Image.Image:
    """Letreros, cifra y flechas del plano en el segundo t."""
    w, h = img.size
    d = ImageDraw.Draw(img)
    rnd = random.Random(int(t*12.5)//3)
    cifra = visual.get("cifra") if isinstance(visual.get("cifra"), dict) else None
    if cifra and cifra.get("valor"):
        color = _color(cifra.get("color"), "rojo")
        e = _escala_pop(t - 0.1)
        cx, cy = w*0.5, h*0.43
        if e > 0:
            n = 26
            giro = t*0.08
            for k in range(n):
                a = giro + 2*math.pi*k/n
                r0, r1 = h*0.33, h*(0.40 + 0.04*(k % 2))
                m._linea(d, [(cx + math.cos(a)*r0*e, cy + math.sin(a)*r0*e),
                             (cx + math.cos(a)*r1*e, cy + math.sin(a)*r1*e)], max(4, int(h*0.007)), rnd,
                         color=color, temblor=1.4)
        valor = str(cifra["valor"])[:10]
        _letrero(img, valor, (cx, cy), _que_quepa(valor, h*0.36, w*0.7), color, -2, e)
        pie = str(cifra.get("pie") or "")[:70]
        if pie:
            _letrero(img, pie, (w*0.5, h*0.85), _que_quepa(pie, h*0.075, w*0.86), TINTA, 0,
                     _escala_pop(t - 0.5))
    for k, f in enumerate(visual.get("flechas") or []):
        try:
            (x0, y0), (x1, y1) = f["de"], f["a"]
        except (KeyError, TypeError, ValueError):
            continue
        desde = float(f["_t"]) if f.get("_t") is not None else 0.3 + k*0.4
        p = 1.0 if f.get("_ya") else min(1.0, max(0.0, (t - desde)/0.6))
        if p <= 0:
            continue
        a, b = (w*float(x0), h*float(y0)), (w*float(x1), h*float(y1))
        if f.get("recta"):
            # La flecha gorda y recta de Whymentary, que se estira hasta su sitio.
            color = _color(f.get("color"), "rojo")
            an = math.atan2(b[1] - a[1], b[0] - a[0])
            tam = h*0.075
            fin = (a[0] + (b[0] - a[0])*p, a[1] + (b[1] - a[1])*p)
            cuello = (fin[0] - math.cos(an)*tam*0.8, fin[1] - math.sin(an)*tam*0.8)
            m._linea(d, [a, cuello], max(10, int(h*0.022)), rnd, color=color, temblor=0.6)
            d.polygon([(fin[0], fin[1]),
                       (cuello[0] + math.cos(an + math.pi/2)*tam*0.6, cuello[1] + math.sin(an + math.pi/2)*tam*0.6),
                       (cuello[0] + math.cos(an - math.pi/2)*tam*0.6, cuello[1] + math.sin(an - math.pi/2)*tam*0.6)],
                      fill=color)
            continue
        mx, my = (a[0] + b[0])/2, (a[1] + b[1])/2 - h*0.08
        pts = [((1-s)**2*a[0] + 2*(1-s)*s*mx + s*s*b[0], (1-s)**2*a[1] + 2*(1-s)*s*my + s*s*b[1])
               for s in [i/24*p for i in range(25)]]
        color = _color(f.get("color"), "rojo")
        m._linea(d, pts, max(6, int(h*0.011)), rnd, color=color, temblor=0.8)
        if p >= 1:
            (px, py), (qx, qy) = pts[-2], pts[-1]
            an = math.atan2(qy - py, qx - px)
            tam = h*0.05
            d.polygon([(qx + math.cos(an)*tam*0.6, qy + math.sin(an)*tam*0.6),
                       (qx + math.cos(an + 2.5)*tam, qy + math.sin(an + 2.5)*tam),
                       (qx + math.cos(an - 2.5)*tam, qy + math.sin(an - 2.5)*tam)], fill=color)
    nuevos = 0
    for tx in visual.get("textos") or []:
        texto = str(tx.get("texto") or "")[:40]
        if not texto:
            continue
        k = -9 if tx.get("_ya") else nuevos
        nuevos += 0 if tx.get("_ya") else 1
        px = h*min(0.3, max(0.04, float(tx.get("tam") or 0.12)))
        x, y = w*float(tx.get("x", 0.5)), h*float(tx.get("y", 0.2))
        px = _que_quepa(texto, px, min(x, w - x)*2*0.95)
        desde = float(tx["_t"]) if tx.get("_t") is not None and not tx.get("_ya") else 0.15 + k*0.35
        _letrero(img, texto, (x, y), px, _color(tx.get("color"), "rojo"), float(tx.get("giro") or 0),
                 _escala_pop(t - desde))
    return img


# ---------------------------------------------------------------------------
# El plano entero, dibujo a dibujo.
# ---------------------------------------------------------------------------

def _spec(visual: dict) -> dict:
    """De lo que pide el guion a lo que entiende animar()."""
    figuras = []
    for f in (visual.get("figuras") or [])[:3]:
        if not isinstance(f, dict):
            continue
        f = dict(f)
        f["quien"] = f.get("quien") if f.get("quien") in QUIENES else "persona"
        gesto = str(f.get("gesto") or "").lower()
        if gesto in _GESTO_ES_EFECTO:
            f["gesto"] = "sorpresa" if gesto == "confuso" else "neutro"
            f.setdefault("efecto", _GESTO_ES_EFECTO[gesto])
        for campo in ("pose", "pose_fin"):
            pose = str(f.get(campo) or "").lower()
            if pose in _POSE_ES_GESTO:
                f[campo] = "de_pie" if campo == "pose" else None
                f["gesto"] = _POSE_ES_GESTO[pose]
        figuras.append(f)
    # Cualquier objeto de este canal se puede llevar en la mano (la pluma de
    # hacer cosquillas): limpia() solo deja los de España Contada.
    en_mano = [nombre_objeto(f.get("lleva")) for f in figuras]
    pedidos = [{c: str(f.get(c) or "").lower() for c in ("pose", "pose_fin", "gesto", "efecto")}
               for f in figuras]
    e = m.limpia({"figuras": figuras}) if figuras else {"figuras": []}
    for f, pedido in zip(e["figuras"], pedidos):
        for campo in ("pose", "pose_fin"):
            if pedido[campo] == "manos_cabeza":
                f[campo] = "manos_cabeza"
        if pedido["gesto"] in GESTOS_EXTRA:
            f["gesto"] = pedido["gesto"]
        if "tumbado" in (pedido["pose"], pedido["pose_fin"]):
            # Tumbado = de pie y girado noventa grados sobre los pies.
            f["pose"], f["pose_fin"] = "de_pie", None
            f["_giro"] = -90 if f.get("espejo") else 90
            # Girado sobre los pies, la cabeza quedaba fuera de su sitio: se
            # corre medio cuerpo para que quede tumbado donde pide el guion.
            f["_dx"] = -0.5 if f.get("espejo") else 0.5
            f["_dy"] = -0.05
        if pedido["efecto"] in EFECTOS_EXTRA:
            f["_extra"] = pedido["efecto"]
    # Quietos salvo lo que pide el guion: limpia() les pone una postura
    # "compañera" para que gesticulen sin parar (en España Contada), y aqui
    # eso es el brazo moviendose todo el rato - y el sentado con mesa.
    for f, pedido in zip(e["figuras"], figuras):
        if not pedido.get("pose_fin") or pedido.get("pose_fin") == pedido.get("pose"):
            f["pose_fin"] = None
    for f, que in zip(e["figuras"], en_mano):
        if not f.get("lleva") and que in OBJETOS_VALIDOS:
            f["lleva"] = que
    # LOS EFECTOS DE ESTE CANAL: el sudor, las lagrimas o la bombilla de
    # España Contada se quitan del monigote y se pintan encima a lo garabato
    # ("tiene los mismos efectos que el otro canal"). Los que mueven al
    # monigote (se cae, salta, tiembla) se quedan.
    doodles = []
    for i, f in enumerate(e["figuras"]):
        efecto = f.get("efecto")
        if f.get("_giro"):
            continue            # tumbado: la cabeza no esta donde se calcula
        if f.get("_extra"):
            doodles.append((i, f.pop("_extra")))
        elif efecto in _GARABATOS:
            doodles.append((i, _GARABATOS[efecto]))
            f.pop("efecto", None)
    e["_doodles"] = doodles
    # SIN SUELO: en Whymentary los monigotes flotan en el folio, sin raya.
    e["interior"] = "folio"
    # Mas abajo que en los decorados: en un folio en blanco el monigote es el
    # protagonista y ocupa media pantalla.
    e["suelo"] = 0.76
    e["hablan"], e["a_quien"] = [], []
    cosas = []
    for c in (visual.get("cosas") or [])[:5]:
        que = nombre_objeto((c or {}).get("que"))
        if que not in OBJETOS_VALIDOS:
            continue
        # Que se vean: en Why Though los objetos son grandes, y mas si hay
        # pocos en el folio (el "=" y el "?" salian diminutos).
        pocas = len([x for x in visual.get("cosas") or [] if isinstance(x, dict)]) <= 2
        tam = min(0.55, max(0.3 if pocas else 0.2, float(c.get("tam") or 0.25)))
        cosa = {"que": que, "x": min(0.95, max(0.05, float(c.get("x", 0.5)))), "tam": tam,
                "delante": bool(c.get("delante")), "tachado": bool(c.get("tachado")),
                "_ya": bool(c.get("_ya")), "_t": c.get("_t"),
                "etiqueta": str(c.get("etiqueta") or "")[:24].upper()}
        if c.get("y") is not None:
            cosa["y"] = min(0.98, float(c["y"]) + tam/2)      # el centro -> la base
        cosas.append(cosa)
    # Las cosas no las pinta animar(): aparecen de golpe, una detras de otra,
    # encima del folio (ver _cosa_pop).
    e["cosas"] = []
    e["_pop"] = cosas
    e["_ambiente"] = garabato_ambiente.elige(visual, cosas)
    return e


# ---------------------------------------------------------------------------
# LA VIDA DEL DIBUJO: lo que hace que Why Though no parezca España Contada.
# La linea "hierve" (todo el folio tiembla un poquito, redibujado seis veces
# por segundo), las cosas aparecen de golpe con su "pop", los efectos son de
# garabato (rayitas de susto, espirales, zetas...) y cada plano entra
# deslizandose con un "whoosh" (eso lo hace el montaje, en ffmpeg).
# ---------------------------------------------------------------------------

_GARABATOS = {"sudor": "sudor", "lagrimas": "lagrimas", "mareo": "espiral", "confuso": "dudas",
              "idea": "idea", "zzz": "zzz", "enamorado": "corazones", "sorpresa": "alerta",
              "humo": "enfado"}
_PULSO = 0.12       # el temblor del trazo, comparado con España Contada
_GROSOR = 0.85      # y su grosor
_ACERCA = 1.32      # lo que se acerca la camara cuando solo salen monigotes
_HERVOR = 2          # fotogramas dibujados con el mismo temblor (12,5/2: seis por segundo)
_PASO_COSAS = 0.3    # entre que aparece una cosa y la siguiente


@lru_cache(maxsize=4)
def _mapas_de_hervor(ancho: int, alto: int, n: int = 3, amplitud: float = 1.1):
    """Tres desplazamientos suaves de todo el folio, como indices planos para
    np.take: alternandolos, las lineas ondulan como dibujadas a mano."""
    rng = np.random.default_rng(7)
    amp = amplitud*ancho/1920
    yy, xx = np.mgrid[0:alto, 0:ancho]
    mapas = []
    for _ in range(n):
        campos = []
        for _eje in range(2):
            ruido = (rng.random((alto//40 + 2, ancho//40 + 2))*2 - 1).astype(np.float32)
            campo = np.asarray(Image.fromarray(ruido, mode="F").resize((ancho, alto), Image.BICUBIC))
            campos.append(np.rint(campo*amp).astype(np.int32))
        sx = np.clip(xx + campos[0], 0, ancho - 1)
        sy = np.clip(yy + campos[1], 0, alto - 1)
        mapas.append((sy*ancho + sx).ravel())
    return mapas


def _hierve(img: Image.Image, n: int) -> Image.Image:
    mapas = _mapas_de_hervor(*img.size)
    plano = np.asarray(img).reshape(-1, 3)
    return Image.fromarray(np.take(plano, mapas[(n//_HERVOR) % len(mapas)], axis=0).reshape(
        img.size[1], img.size[0], 3))


class _DibujoSeguro:
    """Un ImageDraw que no peta con cajas al reves: a tamaños pequeños o con
    trazo gordo, muchas cuentas de los dibujos dejan x1 < x0, y Pillow lo
    rechaza. Se ordenan las esquinas y listo."""
    _CAJAS = ("ellipse", "rectangle", "rounded_rectangle", "chord", "arc", "pieslice")

    def __init__(self, d):
        self._d = d

    def __getattr__(self, nombre):
        f = getattr(self._d, nombre)
        if nombre not in self._CAJAS:
            return f

        def seguro(xy, *args, **kw):
            try:
                if len(xy) == 2:
                    (x0, y0), (x1, y1) = xy
                else:
                    x0, y0, x1, y1 = xy
            except (TypeError, ValueError):
                return f(xy, *args, **kw)
            x0, x1 = sorted((float(x0), float(x1)))
            y0, y1 = sorted((float(y0), float(y1)))
            if "radius" in kw:
                kw["radius"] = max(0, min(int(kw["radius"]), int((x1 - x0)/2), int((y1 - y0)/2)))
            if kw.get("width") and (x1 - x0 < 2*kw["width"] or y1 - y0 < 2*kw["width"]):
                kw["width"] = max(1, int(min(x1 - x0, y1 - y0)/2))
            return f([x0, y0, x1, y1], *args, **kw)
        return seguro


def _volumen(pieza: Image.Image) -> Image.Image:
    """LA FAMILIA DE MOKORDO para cualquier dibujo ("si, todo de familia
    Mokordo"): los rellenos de color se oscurecen hacia la derecha y abajo
    (la sombra en media luna) y se aclaran arriba a la izquierda (el brillo).
    La tinta y los blancos puros no se tocan."""
    a = np.asarray(pieza).astype(np.float32)
    h, w = a.shape[:2]
    if w < 8 or h < 8:
        return pieza
    rgb, alfa = a[..., :3], a[..., 3]
    lum = rgb.mean(axis=2)
    relleno = (alfa > 0) & (lum > 70) & (lum < 250)
    yy, xx = np.mgrid[0:h, 0:w]
    u, v = xx/(w - 1), yy/(h - 1)
    sombra = np.clip((u - 0.45)/0.55, 0, 1)**1.4*0.26 + np.clip((v - 0.55)/0.45, 0, 1)**1.6*0.12
    brillo = np.clip(1 - np.hypot((u - 0.28)/0.22, (v - 0.25)/0.2), 0, 1)**1.4*0.3
    factor = (1 - sombra)[..., None]
    nuevo = rgb*factor + (255 - rgb*factor)*brillo[..., None]
    a[..., :3] = np.where(relleno[..., None], nuevo, rgb)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


@lru_cache(maxsize=96)
def _pieza_cosa(que: str, t: int, g: int):
    """La cosa dibujada UNA vez en su recorte; el centro de abajo en (cx, base)."""
    w, h = int(t*2.8), int(t*1.7)
    pieza = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    base = int(t*1.4)
    try:
        OBJETOS_TODOS[que](_DibujoSeguro(ImageDraw.Draw(pieza)), w/2, base, t, random.Random(3), g)
    except Exception:
        # Un dibujo que falla a un tamaño raro no tumba el plano entero (el
        # 43 de las cosquillas salio en blanco por la mano): se queda sin el.
        logger.warning("why: el dibujo %r ha fallado a tamaño %s.", que, t, exc_info=True)
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0)), 0, 0
    caja = pieza.getbbox() or (0, 0, w, h)
    recorte = pieza.crop(caja)
    if que not in ANIMALES:          # los animales ya traen su sombra y su brillo
        recorte = _volumen(recorte)
    return recorte, w/2 - caja[0], base - caja[1]


def _cosa_pop(img, c, pies, t):
    """Una cosa del plano, apareciendo con su golpe (crece de su centro)."""
    w, h = img.size
    escala = _escala_pop(t)
    if escala <= 0.05:
        return
    tam = int(h*float(c.get("tam", 0.14)))
    g = max(3, int(w*0.0055))
    pieza, cx, base = _pieza_cosa(c["que"], tam, g)
    if escala != 1.0:
        pieza = pieza.resize((max(1, int(pieza.width*escala)), max(1, int(pieza.height*escala))),
                             Image.BILINEAR)
        cx, base = cx*escala, base*escala
    x = w*float(c.get("x", 0.5))
    y = h*float(c["y"]) if c.get("y") is not None else pies
    # Crece desde su centro, no desde el suelo: el centro se queda quieto.
    medio = y - tam*0.5
    arriba = medio - (base - tam*0.5*escala)
    img.paste(pieza, (int(x - cx), int(arriba)), pieza)


def _garabato_en_cabeza(img, d, tipo, cabeza, t, rnd):
    """El efecto de garabato encima de una cabeza: (cx, cy, radio, lado)."""
    cx, cy, r, lado = cabeza
    g = max(4, int(r*0.12))
    e = _escala_pop(t - 0.2)
    if e <= 0.05:
        return
    if tipo == "calor":
        _ondas(d, cabeza, t, rnd, (COLORES["naranja"], COLORES["rojo"]))
    elif tipo == "frio":
        _ondas(d, cabeza, t, rnd, (COLORES["azul"], (120, 190, 240)), frio=True)
    elif tipo == "alerta":
        sube = r*0.08*math.sin(t*9)
        for a in (-140, -112, -90, -68, -40):
            ar = math.radians(a)
            m._linea(d, [(cx + math.cos(ar)*r*1.3, cy + math.sin(ar)*r*1.3 - sube),
                         (cx + math.cos(ar)*r*(1.3 + 0.55*e), cy + math.sin(ar)*r*(1.3 + 0.55*e) - sube)],
                     g, rnd, color=TINTA, temblor=0.6)
        _letrero(img, "!", (cx + lado*r*1.75, cy - r*0.9), r*1.2, COLORES["rojo"], -12*lado, e)
    elif tipo == "enfado":
        # El nubarron gris de mal humor, con sus rayos rojos.
        oy = cy - r*1.85 + r*0.05*math.sin(t*4)
        piezas = [(cx - r*0.55, oy + r*0.1, r*0.38), (cx, oy - r*0.12, r*0.48), (cx + r*0.55, oy + r*0.1, r*0.38)]
        for px, py, rr in piezas:
            d.ellipse([px - rr*e, py - rr*e, px + rr*e, py + rr*e], fill=(110, 110, 120), outline=TINTA, width=g)
        for px, py, rr in piezas:
            if rr*e > g*1.5:
                d.ellipse([px - rr*e + g, py - rr*e + g, px + rr*e - g, py + rr*e - g], fill=(110, 110, 120))
        if int(t*3) % 2 == 0:
            for k in (-1, 1):
                px = cx + k*r*0.35
                d.line([(px, oy + r*0.4), (px - k*r*0.12, oy + r*0.7), (px + k*r*0.05, oy + r*0.72),
                        (px - k*r*0.08, oy + r*1.0)], fill=COLORES["rojo"], width=max(3, int(g*1.2)))
    elif tipo == "espiral":
        oy, giro = cy - r*1.75, t*5
        pts = [(cx + math.cos(giro + a/10)*r*0.06*a/10*e, oy + math.sin(giro + a/10)*r*0.035*a/10*e)
               for a in range(0, 130)]
        d.line(pts, fill=COLORES["morado"], width=g, joint="curve")
    elif tipo == "dudas":
        for k, (dx, fase) in enumerate(((-1.2, 0), (0.1, 0.7), (1.3, 0.35))):
            sube = ((t*0.8 + fase) % 1.0)
            _letrero(img, "?", (cx + dx*r, cy - r*(1.6 + sube*0.6)), r*(0.8 + 0.2*k),
                     COLORES["naranja"], 12*(k - 1), e*min(1.0, (1 - sube)*4))
    elif tipo == "idea":
        tam = int(r*1.4)
        pieza, pcx, base = _pieza_cosa("bombilla", tam, g)
        if e != 1.0:
            pieza = pieza.resize((max(1, int(pieza.width*e)), max(1, int(pieza.height*e))))
            pcx, base = pcx*e, base*e
        img.paste(pieza, (int(cx - pcx), int(cy - r*1.25 - base)), pieza)
    elif tipo == "zzz":
        for k in range(3):
            fase = (t*0.5 + k/3) % 1.0
            _letrero(img, "Z", (cx + lado*r*(1.0 + fase*2.4), cy - r*(1.2 + fase*2.6)), r*(0.7 + fase*0.8),
                     COLORES["azul"], -10*lado, min(1.0, (1 - fase)*3)*e)
    elif tipo == "corazones":
        for k in range(3):
            fase = (t*0.6 + k/3) % 1.0
            tam = int(r*(0.45 + 0.25*fase))
            if fase > 0.9 or tam < 4:
                continue
            pieza, pcx, base = _pieza_cosa("corazon", tam, max(2, g//2))
            px = cx + (k - 1)*r*0.9 + r*0.2*math.sin(fase*6 + k)
            img.paste(pieza, (int(px - pcx), int(cy - r*(1.2 + fase*1.5) - base)), pieza)
    elif tipo == "sudor":
        for k in (-1, 1):
            fase = (t*0.9 + (0.5 if k > 0 else 0)) % 1.0
            px = cx + k*r*(1.05 + fase*0.7)
            py = cy - r*0.6 + r*1.4*(fase - 0.35)**2
            tam = int(r*0.5)
            pieza, pcx, base = _pieza_cosa("gota", tam, max(2, g//2))
            img.paste(pieza, (int(px - pcx), int(py - base)), pieza)
            m._linea(d, [(cx + k*r*1.1, cy - r*0.95), (cx + k*r*1.35, cy - r*1.15)], max(2, g//2), rnd)
    elif tipo == "lagrimas":
        for k in (-1, 1):
            ox, oy = cx + k*r*0.32, cy - r*0.05
            pts = [(ox + k*r*1.7*s, oy - r*0.7*math.sin(s*math.pi*0.9) + r*1.6*s*s) for s in
                   [i/18 for i in range(19)]]
            fase = int(t*10) % 3
            for j in range(fase, len(pts) - 1, 3):
                d.line([pts[j], pts[j + 1]], fill=COLORES["azul"], width=max(6, int(g*2.2)))


def _tacha(d, tam_img, c, pies, t, rnd):
    """La X roja gorda encima de una cosa, trazo a trazo: "esto NO"."""
    if t <= 0:
        return
    w, h = tam_img
    tam = h*float(c.get("tam", 0.14))
    x = w*float(c.get("x", 0.5))
    medio = (h*float(c["y"]) if c.get("y") is not None else pies) - tam*0.5
    r = tam*0.6
    grosor = max(8, int(h*0.014))
    for k, (a, b) in enumerate((((-r, -r), (r, r)), ((r, -r), (-r, r)))):
        p = min(1.0, max(0.0, (t - k*0.25)/0.25))
        if p > 0:
            ini = (x + a[0], medio + a[1])
            fin = (x + a[0] + (b[0] - a[0])*p, medio + a[1] + (b[1] - a[1])*p)
            m._linea(d, [ini, fin], grosor, rnd, color=COLORES["rojo"], temblor=0.8)


def _ondas(d, cabeza, t, rnd, colores, frio=False):
    """Rayitas onduladas alrededor de todo el monigote: el calor (naranjas y
    rojas, subiendo) o el frio (azules, temblando en zigzag)."""
    cx, cy, r, _lado = cabeza
    sitios = ((-2.3, -0.6), (-1.7, 0.6), (-2.6, 1.9), (-1.6, 2.9), (-2.2, 3.9), (1.6, -0.9),
              (2.4, 0.3), (1.7, 1.6), (2.6, 2.6), (1.8, 3.6), (-0.9, -1.9), (0.3, -2.2), (1.2, -1.8))
    g = max(3, int(r*0.08))
    for k, (dx, dy) in enumerate(sitios):
        x0, y0 = cx + dx*r, cy + dy*r
        largo = r*(1.0 + 0.25*(k % 3))
        if frio:
            sacude = r*0.06*math.sin(t*30 + k)
            pts = [(x0 + sacude + (r*0.12 if i % 2 else -r*0.12), y0 + i*largo/6) for i in range(7)]
        else:
            sube = (t*r*0.6) % (r*0.5)
            pts = [(x0 + r*0.13*math.sin(i*1.3 + t*6 + k), y0 - sube + i*largo/8) for i in range(9)]
        m._linea(d, pts, g, rnd, color=colores[k % len(colores)], temblor=0.4)


# ---------------------------------------------------------------------------
# CARAS CON MAS EXPRESION ("currate mas los dibujos, que sean mas
# expresivos"): ojos con su blanco y su pupila, cejas que cuentan lo que
# siente, mofletes, lengua. Solo en Why Though: se cambia por la de
# monigotes mientras se dibuja cada fotograma.
# ---------------------------------------------------------------------------
_ROSA_MOFLETE = (250, 185, 190)
_LENGUA = (230, 100, 120)


def _ojo_abierto(d, cx, cy, r, g, tinta, mira=(0.0, 0.0), grande=1.0, pupila=1.0):
    ro = r*0.15*grande
    d.ellipse([cx - ro, cy - ro*1.15, cx + ro, cy + ro*1.15], fill=(255, 255, 255), outline=tinta,
              width=max(2, g//2))
    rp = ro*0.55*pupila
    px, py = cx + mira[0]*ro*0.35, cy + mira[1]*ro*0.35
    d.ellipse([px - rp, py - rp, px + rp, py + rp], fill=tinta)
    d.ellipse([px - rp*0.15, py - rp*0.7, px + rp*0.35, py - rp*0.25], fill=(255, 255, 255))


def _ceja(d, cx, cy, r, g, tinta, lado, inclina=0.0, alto=0.0):
    """inclina > 0: el lado de dentro baja (enfado); < 0: sube (pena)."""
    a = r*0.16
    dentro, fuera = cx - lado*a, cx + lado*a
    y = cy - r*(0.30 + alto)
    d.line([(fuera, y - inclina*r*0.04), (dentro, y + inclina*r*0.08)], fill=tinta, width=max(3, int(g*1.1)))


def _cara_expresiva(d, c, r, g, rnd, gesto, tinta=TINTA):
    o = r*0.33
    ey = c[1] - r*0.12
    b = (c[0], c[1] + r*0.38)
    if gesto == "muerto":
        return _CARA_ORIGINAL(d, c, r, g, rnd, gesto, tinta)
    for lado in (-1, 1):
        cx = c[0] + lado*o
        if gesto in ("contento", "riendo", "enamorado"):
            # Los ojos cerrados de felicidad: dos arcos hacia arriba.
            d.arc([cx - r*0.13, ey - r*0.08, cx + r*0.13, ey + r*0.14], 200, 340, fill=tinta, width=max(3, g))
            _ceja(d, cx, ey, r, g, tinta, lado, inclina=-0.4, alto=0.06)
        elif gesto in ("sorpresa", "asustado", "grito"):
            _ojo_abierto(d, cx, ey, r, g, tinta, grande=1.25, pupila=0.6)
            _ceja(d, cx, ey, r, g, tinta, lado, inclina=-0.6 if gesto == "asustado" else -0.2, alto=0.14)
        elif gesto == "enfadado":
            _ojo_abierto(d, cx, ey, r, g, tinta, mira=(0, 0.3), grande=0.9)
            _ceja(d, cx, ey, r, g, tinta, lado, inclina=1.6, alto=-0.04)
        elif gesto == "triste":
            _ojo_abierto(d, cx, ey, r, g, tinta, mira=(0, 0.8), grande=0.95)
            _ceja(d, cx, ey, r, g, tinta, lado, inclina=-1.5, alto=0.05)
        elif gesto == "asco":
            _ojo_abierto(d, cx, ey + r*0.02, r, g, tinta, mira=(-lado*0.6, 0), grande=0.75 if lado < 0 else 1.0)
            _ceja(d, cx, ey, r, g, tinta, lado, inclina=1.2 if lado < 0 else -0.8, alto=0.0 if lado < 0 else 0.1)
        elif gesto == "bostezo":
            d.line([(cx - r*0.12, ey + r*0.02), (cx + r*0.12, ey + r*0.02)], fill=tinta, width=max(3, g))
            _ceja(d, cx, ey, r, g, tinta, lado, inclina=-0.5, alto=0.04)
        else:
            _ojo_abierto(d, cx, ey, r, g, tinta, mira=(0.15, 0))
            _ceja(d, cx, ey, r, g, tinta, lado, inclina=0.0, alto=0.06)
    if gesto in ("contento", "riendo", "enamorado"):
        for lado in (-1, 1):
            mx = c[0] + lado*r*0.52
            d.ellipse([mx - r*0.13, b[1] - r*0.2, mx + r*0.13, b[1] - r*0.06], fill=_ROSA_MOFLETE)
    if gesto == "riendo":
        d.chord([b[0] - r*0.36, b[1] - r*0.16, b[0] + r*0.36, b[1] + r*0.46], 0, 180, fill=tinta)
        d.chord([b[0] - r*0.2, b[1] + r*0.14, b[0] + r*0.2, b[1] + r*0.44], 0, 180, fill=_LENGUA)
    elif gesto in ("contento", "enamorado"):
        d.arc([b[0] - r*0.32, b[1] - r*0.3, b[0] + r*0.32, b[1] + r*0.18], 20, 160, fill=tinta, width=max(3, g))
    elif gesto == "sorpresa":
        d.ellipse([b[0] - r*0.12, b[1] - r*0.08, b[0] + r*0.12, b[1] + r*0.2], fill=tinta)
    elif gesto in ("asustado", "grito"):
        d.chord([b[0] - r*0.3, b[1] - r*0.12, b[0] + r*0.3, b[1] + r*0.42], 180, 360, fill=tinta)
        d.rectangle([b[0] - r*0.3, b[1] + r*0.15, b[0] + r*0.3, b[1] + r*0.2], fill=tinta)
        d.chord([b[0] - r*0.16, b[1] + r*0.02, b[0] + r*0.16, b[1] + r*0.2], 180, 360, fill=_LENGUA)
    elif gesto == "enfadado":
        pts = [(b[0] - r*0.26 + k*r*0.104, b[1] + (r*0.04 if k % 2 else -r*0.02)) for k in range(6)]
        d.line(pts, fill=tinta, width=max(3, g))
    elif gesto == "triste":
        d.arc([b[0] - r*0.28, b[1], b[0] + r*0.28, b[1] + r*0.42], 200, 340, fill=tinta, width=max(3, g))
    elif gesto == "asco":
        pts = [(b[0] - r*0.28 + k*r*0.112, b[1] + (r*0.07 if k % 2 else -r*0.03)) for k in range(6)]
        d.line(pts, fill=tinta, width=max(3, g))
        d.chord([b[0] + r*0.02, b[1] - r*0.02, b[0] + r*0.22, b[1] + r*0.24], 0, 180, fill=_LENGUA,
                outline=tinta, width=max(2, g//2))
    elif gesto == "bostezo":
        d.ellipse([b[0] - r*0.18, b[1] - r*0.16, b[0] + r*0.18, b[1] + r*0.38], fill=tinta)
        d.ellipse([b[0] - r*0.1, b[1] + r*0.14, b[0] + r*0.1, b[1] + r*0.32], fill=_LENGUA)
    else:
        d.arc([b[0] - r*0.18, b[1] - r*0.12, b[0] + r*0.18, b[1] + r*0.1], 20, 160, fill=tinta, width=max(3, g))


_CARA_ORIGINAL = m._cara


def _vida(img, e, cabezas, t, n):
    """Lo de este canal, encima de cada fotograma de animar()."""
    w, h = img.size
    pies = min(h*e.get("suelo", 0.76) + h*0.06, h*0.86)
    d = ImageDraw.Draw(img)
    rnd = random.Random(n//_HERVOR)
    nuevas = 0
    for c in e.get("_pop", []):
        # Las que ya estaban en el plano anterior ("sigue") estan desde el
        # principio; las nuevas van apareciendo.
        # Y las que nombra la voz ("cuando"), en su segundo.
        if c.get("_ya"):
            tc = 9.0
        elif c.get("_t") is not None:
            tc = t - float(c["_t"])
        else:
            tc = t - 0.1 - nuevas*_PASO_COSAS
            nuevas += 1
        _cosa_pop(img, c, pies, tc)
        if c.get("etiqueta"):
            # La etiqueta a mano debajo ("CAMEL"): que se entienda que es.
            w_, h_ = img.size
            tam = h_*float(c.get("tam", 0.14))
            base = h_*float(c["y"]) if c.get("y") is not None else pies
            px = _que_quepa(c["etiqueta"], h_*0.055, max(w_*0.12, tam*1.6))
            _letrero(img, c["etiqueta"], (w_*float(c.get("x", 0.5)), min(h_*0.96, base + px*0.75)), px, TINTA, 0,
                     _escala_pop(tc - 0.15))
        if c.get("tachado"):
            _tacha(d, img.size, c, pies, tc - 0.45, rnd)
    for i, tipo in e.get("_doodles", []):
        if i < len(cabezas):
            _garabato_en_cabeza(img, d, tipo, cabezas[i], t, rnd)
    return img


def fotos(visual: dict, segundos: float, fps: float, tam=(1920, 1080), calma: float = 1.6,
          hervor: bool = True):
    """Los dibujos del plano: los monigotes animados (respiran, cambian de
    postura) en el folio en blanco; encima las cosas apareciendo, los efectos
    de garabato, los letreros, la cifra y las flechas; y todo hirviendo."""
    e = _spec(visual or {})
    cabezas = []
    original = m.figura

    def espia(d, x, suelo, alto, rnd, pose="de_pie", gesto="neutro", gorro=None, espejo=False,
              pose_mezclada=None, **kw):
        # Donde queda cada cabeza en ESTE fotograma, para pintarle encima.
        p = pose_mezclada or m._POSES.get(pose) or m._POSES["de_pie"]
        rasgos = kw.get("rasgos") or {}
        lado = -1 if espejo else 1
        rc = alto*0.145*rasgos.get("cabeza", 1.0)
        cuello = (x + p["cuello"][0]*alto*lado*rasgos.get("ancho", 1.0), suelo + p["cuello"][1]*alto)
        cabezas.append((cuello[0], cuello[1] - rc*0.95, rc, lado))
        return original(d, x, suelo, alto, rnd, pose, gesto, gorro, espejo, pose_mezclada, **kw)

    # El ambiente del folio (la hierba y el sol del caballo, las dunas del
    # camello) y las sombritas de lo que esta apoyado: una vez por plano.
    ancho, alto = tam
    pies = min(alto*e.get("suelo", 0.76) + alto*0.06, alto*0.86)
    apoyados = [(f["x"], f.get("alto", 0.5)*0.42*alto/ancho) for f in e.get("figuras", []) if not f.get("_giro")]
    apoyados += [(c["x"], c["tam"]*1.0*alto/ancho) for c in e.get("_pop", []) if c.get("y") is None]
    fondo = None
    if e.get("_ambiente", "nada") != "nada" or apoyados:
        fondo = garabato_ambiente.fondo(e.get("_ambiente", "nada"), tam, pies, apoyados)
    # SI SOLO SALEN ELLOS, MAS GRANDES ("que ocupen mas en pantalla"): la
    # camara se acerca a los monigotes, con los pies abajo del todo.
    camara = None
    figs = e.get("figuras", [])
    if figs and len(figs) <= 2 and not e.get("_pop") and not (visual or {}).get("cifra") \
            and not (visual or {}).get("mascota") and not any(f.get("_giro") for f in figs):
        # Cuanto acercar: que el mas alto ocupe unas tres cuartas partes de la
        # pantalla (el niño, bajito, se acerca mas); menos si lleva algo
        # encima de la cabeza (humo, zetas...).
        meta = 0.64 if e.get("_doodles") else 0.74
        z = min(2.0, max(1.0, meta/(1.08*max(f.get("alto", 0.5) for f in figs))))
        cw, ch = ancho/z, alto/z
        cx = sum(f["x"] for f in figs)/len(figs)*ancho
        x0 = min(max(0.0, cx - cw/2), ancho - cw)
        y0 = min(max(0.0, pies - alto*0.93/z), alto - ch)
        camara = (int(x0), int(y0), int(x0 + cw), int(y0 + ch))
    mascota = (visual or {}).get("mascota") if isinstance((visual or {}).get("mascota"), dict) else None
    paso_hervor = max(1, round(fps/6))
    animacion = m.animar(e, segundos=segundos, fps=fps, tam=tam, calma=calma, una_vez=True)
    n = 0
    while True:
        cabezas.clear()
        # El trazo de Whymentary: liso, sin el pulso de España Contada, y
        # algo mas fino. Solo mientras se dibuja este fotograma.
        m.figura, m.PULSO, m.GROSOR, m._cara = espia, _PULSO, _GROSOR, _cara_expresiva
        try:
            img = next(animacion).convert("RGB")
            if fondo is not None:
                img = garabato_ambiente.pon_detras(img, fondo)
            reloj = n/fps
            img = _vida(img, e, list(cabezas), reloj, n)
            if mascota:
                cabeza, efecto = _mascota.pinta(img, mascota, reloj, segundos, pies)
                efecto = mascota.get("efecto") or efecto
                if efecto in _GARABATOS or efecto in EFECTOS_EXTRA:
                    _garabato_en_cabeza(img, ImageDraw.Draw(img), _GARABATOS.get(efecto, efecto), cabeza,
                                        reloj, random.Random(n//paso_hervor))
                # La camara que respira: un acercamiento lento todo el plano,
                # para que nada parezca una foto.
                z = 1 + 0.045*min(1.0, reloj/max(0.5, segundos))
                cw, ch = ancho/z, alto/z
                img = img.crop((int((ancho - cw)/2), int((alto - ch)*0.6), int((ancho + cw)/2),
                                int((alto - ch)*0.6 + ch))).resize(tam, Image.BILINEAR)
            if camara:
                img = img.crop(camara).resize(tam, Image.BILINEAR)
            img = encima(img, visual or {}, reloj, segundos)
        except StopIteration:
            break
        finally:
            m.figura, m.PULSO, m.GROSOR, m._cara = original, 1.0, 1.0, _CARA_ORIGINAL
        yield _hierve(img, n//paso_hervor*_HERVOR) if hervor else img
        n += 1


def sonidos_del_plano(visual: dict, segundos: float) -> list:
    """Los de este canal: un 'pop' por cosa, letrero y efecto de garabato
    cuando aparecen, y el golpe si alguien se cae. Ni un 'boing': ese es de
    España Contada."""
    e = _spec(visual or {})
    salida = []
    for f in e.get("figuras", []):
        efecto = f.get("efecto")
        if efecto == "caida":
            salida.append(("golpe", m.momento_del_efecto(efecto, segundos), 0.9))
        elif efecto == "bofetada":
            salida.append(("zas", m.momento_del_efecto(efecto, segundos), 0.4))
    sin_hora = 0
    for c in e.get("_pop", []):
        if c.get("_ya"):
            continue
        if c.get("_t") is not None:
            salida.append(("pop", float(c["_t"]), 0.25))
        else:
            salida.append(("pop", 0.1 + sin_hora*_PASO_COSAS, 0.25))
            sin_hora += 1
    sin_hora = 0
    for x in (visual or {}).get("textos") or []:
        if not isinstance(x, dict) or x.get("_ya"):
            continue
        if x.get("_t") is not None:
            salida.append(("pop", float(x["_t"]), 0.25))
        else:
            salida.append(("pop", 0.15 + sin_hora*0.35, 0.25))
            sin_hora += 1
    if (visual or {}).get("cifra"):
        salida.append(("pop", 0.1, 0.25))
    for _i, _tipo in e.get("_doodles", []):
        salida.append(("pop", 0.2, 0.25))
    return [s for s in salida if s[1] < segundos]
