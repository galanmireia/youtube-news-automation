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
import re
import zlib
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import monigotes as m

logger = logging.getLogger(__name__)
from .garabato_mas import MAS_OBJETOS, REHECHOS
from .garabato_bichos import ANIMALES
from . import garabato_ambiente
from . import garabato_mas
from . import interaccion
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
                  "phone": "movil", "brain": "cerebro", "heart": "corazon", "feather": "pluma",
                  "shield": "escudo", "escudo_placeholder": "escudo", "foam_stick": "palo_espuma",
                  "palo": "palo_espuma", "stick": "palo_espuma", "goggles": "gafas_vr",
                  "video_goggles": "gafas_vr", "gafas": "gafas_vr", "coil": "bobina",
                  "magnetic_coil": "bobina", "cigarette": "cigarrillo", "cigarro": "cigarrillo",
                  "tabaco": "cigarrillo", "beer": "cerveza", "wine": "copa", "vino": "copa",
                  "vape": "vapeador", "vaper": "vapeador", "e_cigarette": "vapeador", "coffee": "taza",
                  "cafe": "taza", "energy_drink": "lata", "bebida_energetica": "lata",
                  "lungs": "pulmones", "liver": "higado", "pack": "paquete", "cigarette_pack": "paquete",
                  "piggy_bank": "hucha", "butts": "colillas", "ashtray": "cenicero",
                  "bell": "campana", "alarm": "campana", "foam": "esponja", "foam_pad": "esponja",
                  "sponge": "esponja", "espuma": "esponja"}


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


def _letrero(img, texto, xy, px, relleno, giro, escala=1.0, escribe=1.0):
    """escribe < 1: se esta escribiendo, se ve solo esa parte (de izquierda
    a derecha, como a rotulador)."""
    if escala <= 0.05 or not texto or escribe <= 0:
        return
    # El tamaño en pasos de 2 px: asi el "pop" reutiliza piezas ya hechas.
    px = max(8, int(px*escala)//2*2)
    pieza = _pieza_letrero(texto, px, tuple(relleno), round(float(giro), 1))
    x0, y0 = int(xy[0] - pieza.width/2), int(xy[1] - pieza.height/2)
    if escribe < 1:
        pieza = pieza.crop((0, 0, max(1, int(pieza.width*escribe)), pieza.height))
    img.paste(pieza, (x0, y0), pieza)


def _que_quepa(texto: str, px: float, ancho: float) -> float:
    """El tamaño de letra para que el letrero no se salga de la pantalla."""
    f = _fuente(px)
    largo = f.getlength(texto) or 1
    return px*min(1.0, ancho/largo)


def _contando(valor: str, t: float, dura: float = 0.9) -> str:
    """El numero gigante CUENTA hasta su valor (0... 12... 35°C), con los
    mismos decimales y lo que lleve detras."""
    m_ = re.match(r"^([^\d]*)(\d+(?:[.,]\d+)?)(.*)$", valor)
    if not m_ or t >= dura:
        return valor
    antes, num, despues = m_.groups()
    if re.fullmatch(r"\d{1,3}(,\d{3})+", num):          # 1,000 = mil, no un decimal
        objetivo = int(num.replace(",", ""))
        return antes + f"{int(objetivo*(1 - (1 - max(0.0, t)/dura)**3)):,}" + despues
    sep = "," if "," in num else "."
    dec = len(num.split(sep)[1]) if sep in num else 0
    objetivo = float(num.replace(",", "."))
    u = max(0.0, t)/dura
    actual = objetivo*(1 - (1 - u)**3)
    texto = f"{actual:.{dec}f}"
    return antes + (texto.replace(".", ",") if sep == "," else texto) + despues


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
        valor = str(cifra["valor"])[:18]
        tam_valor = _que_quepa(valor, h*0.36, w*0.7)
        valor = _contando(valor, t - 0.1)
        _letrero(img, valor, (cx, cy), tam_valor, color, -2, e)
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
        # Tampoco los letreros se quedan quietos: se balancean y laten un poco
        # (en grados enteros y pasos de 2 px, para reutilizar las piezas).
        fase = len(texto) + k*1.3
        vaiven = round(3*math.sin(t*2.3 + fase))
        late = 1 + 0.04*math.sin(t*3.1 + fase)
        y += h*0.01*math.sin(t*1.9 + fase)
        # se escribe de izquierda a derecha en un momento (a rotulador)
        escribe = 1.0 if tx.get("_ya") else min(1.0, max(0.0, (t - desde)/max(0.25, 0.04*len(texto))))
        _letrero(img, texto, (x, y), px, _color(tx.get("color"), "rojo"), float(tx.get("giro") or 0) + vaiven,
                 min(1.0, 0.7 + 0.3*escribe)*late if escribe < 1 else late, escribe=escribe)
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
    for f, pedido in zip(e["figuras"], figuras):
        if pedido.get("_ya"):
            f["_ya"] = True       # ya estaba en el plano anterior: no vuelve a entrar
        if isinstance(pedido.get("hace"), dict):
            f["hace"] = pedido["hace"]     # lo que hace con algo o con alguien
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
              "humo": "enfado", "bombilla": "idea", "bulb": "idea", "lightbulb": "idea"}
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


def _escala_rebote(t: float) -> float:
    """Aparece con un muelle: se pasa de grande, rebota y se asienta."""
    if t <= 0:
        return 0.0
    if t > 1.2:
        return 1.0
    return max(0.0, 1 - math.exp(-7*t)*math.cos(13*t))


def _cosa_pop(img, c, pies, t):
    """Una cosa del plano, apareciendo con su golpe (crece de su centro)."""
    w, h = img.size
    escala = _escala_rebote(t)
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
    flota = c.get("y") is not None
    y = h*float(c["y"]) if flota else pies
    # Crece desde su centro, no desde el suelo: el centro se queda quieto.
    medio = y - tam*0.5
    arriba = medio - (base - tam*0.5*escala)
    if flota and escala > 0.3:
        # su sombrita en el suelo, mas pequeña cuanto mas alta flota
        lejos = max(0.0, min(1.0, (pies - y)/(h*0.6)))
        sw = tam*0.45*(1 - 0.5*lejos)*min(1.0, escala)
        ImageDraw.Draw(img).ellipse([x - sw, pies - h*0.012, x + sw, pies + h*0.012], fill=(226, 223, 216))
    # Y despues no se queda quieta: se menea (y si flota, sube y baja).
    fase = (sum(map(ord, c["que"])) % 11)*0.57 + float(c.get("x", 0.5))*5
    vivo = min(1.0, max(0.0, (t - 0.4)/0.3))
    giro = vivo*(12 if flota else 8)*math.sin(t*3.0 + fase)
    # Entra girando, como si la tiraran a la pagina.
    giro += -35*math.exp(-t*7)*math.cos(t*12)*(1 if int(fase*10) % 2 else -1)
    if flota:
        arriba += vivo*tam*0.1*math.sin(t*2.4 + fase)
    else:
        # Las del suelo dan botecitos.
        arriba -= vivo*tam*0.08*abs(math.sin(t*2.2 + fase))
    if abs(giro) < 0.3:
        img.paste(pieza, (int(x - cx), int(arriba)), pieza)
        return
    # Gira sobre su punto de apoyo (el centro de abajo).
    vx, vy = cx - pieza.width/2, base - pieza.height/2
    girada = pieza.rotate(giro, resample=Image.BILINEAR, expand=True)
    a = math.radians(giro)
    nx = girada.width/2 + vx*math.cos(a) + vy*math.sin(a)
    ny = girada.height/2 - vx*math.sin(a) + vy*math.cos(a)
    img.paste(girada, (int(x - nx), int(arriba + base - ny)), girada)


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


def _cara_expresiva(d, c, r, g, rnd, gesto, tinta=TINTA, mira=None, habla=None):
    """La cara. mira: (dx, dy) de -1 a 1, adonde miran las pupilas; habla:
    0-1, lo abierta que tiene la boca al hablar (None = no habla)."""
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
            _ojo_abierto(d, cx, ey, r, g, tinta, mira=mira or (0, 0), grande=1.25, pupila=0.6)
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
        elif gesto == "pensativo":
            # mirando arriba, a un lado, con una ceja levantada
            _ojo_abierto(d, cx, ey, r, g, tinta, mira=mira or (0.6, -0.8))
            _ceja(d, cx, ey, r, g, tinta, lado, inclina=-0.8 if lado > 0 else 0.4, alto=0.16 if lado > 0 else 0.02)
        elif gesto == "mareado":
            # ojos en espiral
            for k in range(3):
                rk = r*(0.05 + 0.04*k)
                d.arc([cx - rk, ey - rk, cx + rk, ey + rk], 90*k + (180 if lado > 0 else 0), 90*k + 270 +
                      (180 if lado > 0 else 0), fill=tinta, width=max(2, g//2))
        elif gesto == "confuso":
            _ojo_abierto(d, cx, ey, r, g, tinta, mira=mira or (0, 0), grande=1.2 if lado > 0 else 0.8)
            _ceja(d, cx, ey, r, g, tinta, lado, inclina=-0.6 if lado > 0 else 0.8, alto=0.1)
        elif gesto == "bostezo":
            d.line([(cx - r*0.12, ey + r*0.02), (cx + r*0.12, ey + r*0.02)], fill=tinta, width=max(3, g))
            _ceja(d, cx, ey, r, g, tinta, lado, inclina=-0.5, alto=0.04)
        else:
            _ojo_abierto(d, cx, ey, r, g, tinta, mira=mira or (0.15, 0))
            # al hablar, las cejas acompañan un poco
            _ceja(d, cx, ey, r, g, tinta, lado, inclina=0.0, alto=0.06 + 0.05*(habla or 0))
    if gesto in ("contento", "riendo", "enamorado"):
        for lado in (-1, 1):
            mx = c[0] + lado*r*0.52
            d.ellipse([mx - r*0.13, b[1] - r*0.2, mx + r*0.13, b[1] - r*0.06], fill=_ROSA_MOFLETE)
    if habla is not None and habla >= 0.12 and gesto not in ("riendo", "asustado", "grito", "bostezo", "mareado"):
        # HABLANDO: la boca se abre con la voz (y se ve la lengua si abre mucho)
        ancho_b, alto_b = r*(0.24 + 0.12*habla), r*(0.1 + 0.42*habla)
        sube = r*0.06 if gesto in ("contento", "enamorado") else 0
        d.chord([b[0] - ancho_b, b[1] - alto_b*0.35 - sube, b[0] + ancho_b, b[1] + alto_b - sube], 0, 180, fill=tinta)
        d.chord([b[0] - ancho_b, b[1] - alto_b*0.5 - sube, b[0] + ancho_b, b[1] + alto_b*0.1 - sube], 0, 180,
                fill=tinta)
        if habla > 0.5:
            d.chord([b[0] - ancho_b*0.55, b[1] + alto_b*0.3 - sube, b[0] + ancho_b*0.55, b[1] + alto_b*0.95 - sube],
                    180, 360, fill=_LENGUA)
        return
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
    elif gesto == "pensativo":
        # "mmm": la boca pequeña y torcida a un lado
        d.line([(b[0] + r*0.02, b[1] + r*0.04), (b[0] + r*0.22, b[1] - r*0.02)], fill=tinta, width=max(3, g))
    elif gesto in ("mareado", "confuso"):
        pts = [(b[0] - r*0.24 + k*r*0.06, b[1] + r*0.04*math.sin(k*1.6)) for k in range(9)]
        d.line(pts, fill=tinta, width=max(3, g), joint="curve")
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


# Las acciones en las que Mokordo "habla" (mueve la boca con la voz).
_HABLAN = ("explica", "senala", "piensa", "encoge", "saluda", "triste", "entra")


def _miradas(estados, apariciones, t):
    """ADONDE MIRAN: a lo que tocan o señalan, a lo que acaba de aparecer, al
    que les hace algo; y si no, un poco hacia delante. Las pupilas se van
    hacia alli."""
    recientes = [sitio for tp, sitio in apariciones if sitio and 0 <= t - tp < 2.5]
    for est in estados:
        cabeza = (est["cx"], est["suelo"] - est["h"]*0.55)
        punto = None
        if est.get("alcanza"):
            punto = list(est["alcanza"].values())[0]
        elif recientes:
            punto = recientes[-1][:2]
        else:
            otros = [o for o in estados if o is not est]
            # al que le esta haciendo algo (o al de al lado)
            for o in otros:
                if o.get("alcanza") and any(abs(px - est["cx"]) < est["h"]*0.6 for px, _py in o["alcanza"].values()):
                    punto = (o["cx"], o["suelo"] - o["h"]*0.55)
        if punto is None:
            est["mira"] = (0.35*est["lado"], 0.0)
            continue
        dx, dy = punto[0] - cabeza[0], punto[1] - cabeza[1]
        n_ = math.hypot(dx, dy) or 1.0
        est["mira"] = (dx/n_, dy/n_*0.8)


def _reacciona(estados, apariciones, t):
    """Lo que se dibuja tiene que ver con lo que se cuenta: cuando la voz
    nombra algo y aparece, Mokordo se gira hacia ello, lo señala con el brazo
    estirado y pone cara de "¡mira!" (si no esta haciendo otra cosa)."""
    recientes = [(tp, sitio) for tp, sitio in apariciones if sitio and 0 <= t - tp < 1.6]
    if not recientes:
        return
    tp, (sx, sy, _st) = max(recientes, key=lambda r: r[0])
    u = t - tp
    for est in estados:
        if est["quien"] != "mokordo" or interaccion.que_hace(est["fig"]):
            continue
        if abs(sx - est["cx"]) < est["h"]*0.3:
            continue
        est["lado"] = 1 if sx > est["cx"] else -1
        est["alcanza"] = {est["lado"]: (sx, sy)}
        est["gesto"] = "sorpresa" if u < 0.5 else "contento"
        est["p"]["levanta"] = est["p"].get("levanta", 0.0) + max(0.0, math.sin(min(1.0, u/0.35)*math.pi))*0.12
        est["p"]["inclina"] = est["p"]["inclina"]*0.3 + 8


def _pega_girada(img, pieza, ax, ay, giro, x, y):
    """Pega la pieza girada `giro` grados sobre su punto (ax, ay), que cae en (x, y)."""
    if abs(giro) < 0.5:
        img.paste(pieza, (int(x - ax), int(y - ay)), pieza)
        return
    vx, vy = ax - pieza.width/2, ay - pieza.height/2
    girada = pieza.rotate(giro, resample=Image.BILINEAR, expand=True)
    a = math.radians(giro)
    nx = girada.width/2 + vx*math.cos(a) + vy*math.sin(a)
    ny = girada.height/2 - vx*math.sin(a) + vy*math.cos(a)
    img.paste(girada, (int(x - nx), int(y - ny)), girada)


def _en_la_mano(img, est):
    """Lo que lleva mientras hace algo: la pluma por el canon apuntando a
    donde hace cosquillas, el vaso inclinado hacia la boca, la manzana..."""
    o = est["objeto"]
    lado = est["lado"]
    codo, mano = _mascota.BRAZOS.get(lado, (None, None))
    que = nombre_objeto(o.get("que"))
    if mano is None or que not in OBJETOS_TODOS:
        return
    tam = max(8, int(est["h"]*0.36*float(o.get("escala", 1.0))))
    pieza, pcx, pbase = _pieza_cosa(que, tam, max(3, int(img.width*0.0045)))
    if pieza.width < 2:
        return
    if que == "cigarrillo" and o.get("consumo") is not None:
        # el cigarro que se va gastando, cogido por el filtro
        pieza = _pieza_cigarro(tam, max(2, int(img.width*0.003)), round(float(o["consumo"]), 2),
                               round(float(o.get("ceniza", 0.0)), 1))
        _pega_girada(img, pieza, tam*0.17, pieza.height/2, float(o.get("giro", 0.0)), mano[0], mano[1])
        return
    if o.get("modo") == "punta":
        # cogida por abajo, y su punta hacia donde va (o siguiendo el brazo)
        destino = o.get("apunta") or (mano[0] + (mano[0] - codo[0]), mano[1] + (mano[1] - codo[1]))
        vx, vy = destino[0] - mano[0], destino[1] - mano[1]
        if math.hypot(vx, vy) < 1:
            vx, vy = lado, -1
        giro = math.degrees(math.atan2(-vx, -vy))
        _pega_girada(img, pieza, pcx, pbase, giro, mano[0], mano[1])
    else:
        dx, dy = o.get("desplaza", (0.0, 0.0))
        _pega_girada(img, pieza, pieza.width/2, pieza.height*0.55, float(o.get("giro", 0.0)),
                     mano[0] + dx*est["h"], mano[1] - pieza.height*0.05 + dy*est["h"])


@lru_cache(maxsize=64)
def _pieza_cigarro(t: int, g: int, consumo: float, ceniza: float):
    """El cigarro gastado en `consumo`, recortado: el filtro a la izquierda."""
    w, h = int(t*1.6), int(t*0.6)
    pieza = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    garabato_mas.cigarro(ImageDraw.Draw(pieza), t*0.55, h*0.5 + t*0.3 - t*0.08, t, g, consumo=consumo, ceniza=ceniza)
    caja = pieza.getbbox() or (0, 0, w, h)
    return pieza.crop((caja[0], 0, caja[2], h))


def _humo(img, pos, r, alfa):
    """Una bocanada de humo: gris clarito y medio transparente."""
    r = max(2, int(r))
    a = int(255*max(0.0, min(1.0, alfa)))
    if a < 8:
        return
    nube = Image.new("RGBA", (r*2 + 4, r*2 + 4), (0, 0, 0, 0))
    dn = ImageDraw.Draw(nube)
    dn.ellipse([2, 2, r*2 + 2, r*2 + 2], fill=(214, 214, 220, int(a*0.85)), outline=(150, 150, 160, a),
               width=max(1, r//10))
    img.paste(nube, (int(pos[0] - r - 2), int(pos[1] - r - 2)), nube)


def _camara_viva(img, t, dur, mueve, golpes, foco=None):
    """LA CAMARA QUE NUNCA ESTA QUIETA ("mas movimiento, mucho mas"): en cada
    plano se acerca o se aleja y se desliza hacia un lado (cada plano a su
    manera), con un vaiven de mano; y da un golpecito de zoom cada vez que
    aparece algo."""
    ancho, alto = img.size
    s = _suave_cam(min(1.0, t/max(0.5, dur)))
    z = 1.06 + 0.14*s if mueve % 2 else 1.2 - 0.14*s
    if foco:
        # plano cercano / de detalle: encima de lo que importa, y acercandose
        z = foco[2] + 0.12*s
    sacude = 0.0
    for tp in golpes:
        if 0 <= t - tp < 1.0:
            u = t - tp
            z += 0.07*math.sin(min(1.0, u/0.1)*math.pi/2)*math.exp(-u*5)
            sacude += math.exp(-u*9)*math.sin(u*55)
    lado = 1 if (mueve >> 1) % 2 else -1
    cw, ch = ancho/z, alto/z
    hx, hy = (ancho - cw)/2, (alto - ch)/2
    ox = hx*(1 + lado*(0.8*s - 0.4) + 0.18*math.sin(t*1.1 + mueve % 7)) + sacude*ancho*0.006
    oy = hy*(1.2 + 0.2*math.sin(t*1.5 + mueve % 5)) + sacude*alto*0.006
    if foco:
        ox = foco[0] - cw/2 + ancho*0.01*math.sin(t*1.1) + sacude*ancho*0.006
        oy = foco[1] - ch/2 + alto*0.01*math.sin(t*1.4) + sacude*alto*0.006
    ox = min(max(0.0, ox), ancho - cw)
    oy = min(max(0.0, oy), alto - ch)
    return img.crop((int(ox), int(oy), int(ox + cw), int(oy + ch))).resize((ancho, alto), Image.BILINEAR)


# Los fondos de color de los planos "color" y "partido" (nunca el morado de
# Mokordo).
COLORES_FONDO = ((255, 214, 92), (140, 205, 250), (160, 228, 180), (255, 178, 160), (255, 236, 200),
                 (190, 225, 255))
TRANSICIONES = ("derecha", "abajo", "zoom", "izquierda", "giro", "arriba")
_DURA_TRANSICION = 0.35


def _transicion(img, tipo, s):
    """El plano entrando (s de 0 a 1): de lado, de arriba o abajo, de un
    zoom con rebote o girando."""
    w, h = img.size
    e = 1 - (1 - s)**3
    lienzo = Image.new("RGB", (w, h), garabato_ambiente.PAPEL)
    if tipo in ("derecha", "izquierda", "arriba", "abajo"):
        dx = {"derecha": w, "izquierda": -w}.get(tipo, 0)*(1 - e)
        dy = {"abajo": h, "arriba": -h}.get(tipo, 0)*(1 - e)
        lienzo.paste(img, (int(dx), int(dy)))
        if s < 0.8:
            # la estela del barrido (como un desenfoque de movimiento)
            for k, alfa in ((1, 0.35), (2, 0.18)):
                atras = Image.new("RGB", (w, h), garabato_ambiente.PAPEL)
                atras.paste(img, (int(dx + (dx and math.copysign(w*0.06*k*(1 - e), dx))),
                                  int(dy + (dy and math.copysign(h*0.06*k*(1 - e), dy)))))
                lienzo = Image.blend(lienzo, atras, alfa*(1 - s))
        return lienzo
    if tipo == "zoom":
        k = max(0.05, 1 - math.exp(-6*s)*math.cos(9*s)*0.75)
    else:
        k = 0.55 + 0.45*e
    pieza = img.resize((max(1, int(w*k)), max(1, int(h*k))), Image.BILINEAR)
    if tipo == "giro":
        pieza = pieza.rotate(-35*(1 - e), resample=Image.BILINEAR, expand=False,
                             fillcolor=garabato_ambiente.PAPEL)
    if k >= 1:
        x0, y0 = (pieza.width - w)//2, (pieza.height - h)//2
        return pieza.crop((x0, y0, x0 + w, y0 + h))
    lienzo.paste(pieza, ((w - pieza.width)//2, (h - pieza.height)//2))
    return lienzo


def _fondo_de_encuadre(fondo, encuadre, color, tam):
    """El fondo de color (o partido en dos) debajo del ambiente."""
    w, h = tam
    base = np.zeros((h, w, 3), np.uint8)
    if encuadre == "partido":
        otro = COLORES_FONDO[(COLORES_FONDO.index(color) + 2) % len(COLORES_FONDO)]
        base[:, :w//2] = color
        base[:, w//2:] = otro
        base[:, w//2 - 4:w//2 + 4] = (30, 30, 34)
    else:
        base[:] = color
    if fondo is None:
        return base
    papel = np.all(fondo == np.array(garabato_ambiente.PAPEL, np.uint8), axis=-1)
    return np.where(papel[..., None], base, fondo)


def _suave_cam(s):
    return s*s*(3 - 2*s)


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
    apoyados = [] + [(c["x"], c["tam"]*1.0*alto/ancho) for c in e.get("_pop", []) if c.get("y") is None]
    fondo = None
    if e.get("_ambiente", "nada") != "nada" or apoyados:
        fondo = garabato_ambiente.fondo(e.get("_ambiente", "nada"), tam, pies, apoyados)
    # EL ENCUADRE del plano (para que no parezca todo lo mismo): general,
    # cerca (Mokordo de cerca), detalle (la cosa de la que se habla), color
    # (el folio entero de color) o partido (dos colores, para comparar).
    encuadre = str((visual or {}).get("_encuadre") or "general")
    if encuadre in ("color", "partido"):
        color = COLORES_FONDO[int((visual or {}).get("_color", 0)) % len(COLORES_FONDO)]
        fondo = _fondo_de_encuadre(fondo, encuadre, color, tam)
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
    # LA FAMILIA DE MOKORDO en vez de los monigotes de palotes: los pinta
    # mascota.personaje, no animar().
    familia = [dict(f, _retraso=(0.3 if mascota and not mascota.get("_ya") else 0.0) + 0.22*i)
               for i, f in enumerate(e.get("figuras", []))]
    e["figuras"] = []
    camara = None          # la familia ya trae su camara que respira
    paso_hervor = max(1, round(fps/6))
    # Donde esta cada cosa del folio, por si alguien hace algo con ella
    # (acariciar al perro, mirar el cerebro con la lupa).
    sitios = {}
    for c in e.get("_pop", []):
        t_ = alto*float(c.get("tam", 0.14))
        y_ = alto*float(c["y"]) if c.get("y") is not None else pies
        sitios[c["que"]] = (ancho*float(c.get("x", 0.5)), y_ - t_*0.5, t_)
    # Cuando aparece algo (la voz lo nombra), Mokordo lo mira y lo señala.
    apariciones, nuevas_ = [], 0
    for c in e.get("_pop", []):
        if c.get("_ya"):
            continue
        tp = float(c["_t"]) if c.get("_t") is not None else 0.1 + nuevas_*_PASO_COSAS
        if c.get("_t") is None:
            nuevas_ += 1
        apariciones.append((tp, sitios.get(c["que"])))
    habla_env = list((visual or {}).get("_habla") or [])
    mueve = zlib.crc32(repr(sorted(((k, v) for k, v in (visual or {}).items() if k != "_habla"), key=str)).encode())
    foco = None
    ma_ = (visual or {}).get("mascota") if isinstance((visual or {}).get("mascota"), dict) else None
    if encuadre == "cerca" and ma_:
        hm = alto*float(ma_.get("tam") or 0.5)
        foco = (ancho*float(ma_.get("x", 0.5)), pies - hm*0.6, 1.65)
    elif encuadre == "detalle" and apariciones and apariciones[0][1]:
        sx, sy, st = apariciones[0][1]
        foco = (sx, sy, max(1.3, min(1.9, alto*0.55/max(1.0, st))))
    golpes, nuevas = [], 0
    for c in e.get("_pop", []):
        if c.get("_ya"):
            continue
        if c.get("_t") is not None:
            golpes.append(float(c["_t"]))
        else:
            golpes.append(0.1 + nuevas*_PASO_COSAS)
            nuevas += 1
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
            doodles = dict(e.get("_doodles", []))
            # Primero como esta cada uno; luego lo que hacen entre ellos
            # (acercarse, la mano al pie, el otro riendose); luego se pintan.
            estados = []
            for i, fig in enumerate(familia):
                est = _mascota.estado_personaje(fig, reloj, segundos, pies, ancho, alto)
                est["i"] = i
                estados.append(est)
            if mascota:
                estados.append(_mascota.estado_mascota(mascota, reloj, segundos, pies, ancho, alto))
            _reacciona(estados, apariciones, reloj)
            vuelan = interaccion.planifica(estados, sitios, ancho, reloj)
            _miradas(estados, apariciones, reloj)
            if habla_env and n < len(habla_env):
                for est in estados:
                    if est["quien"] == "mokordo" and not est.get("alcanza") and not interaccion.que_hace(est["fig"]) \
                            and str(est["fig"].get("accion") or "explica") in _HABLAN:
                        est["habla"] = habla_env[n]
            # El que hace algo con otro, delante: si no, el otro le tapa la pluma.
            for est in sorted(estados, key=lambda x_: (1 if x_.get("alcanza") else 0, x_["cx"])):
                cab, manos = _mascota.pinta_estado(img, est)
                fig = est["fig"]
                if est.get("objeto"):
                    _en_la_mano(img, est)
                elif nombre_objeto(fig.get("lleva")) in OBJETOS_TODOS and manos and est.get("brazo_lleva"):
                    pieza, pcx, pbase = _pieza_cosa(nombre_objeto(fig["lleva"]), int(est["h"]*0.4), max(3, int(ancho*0.0045)))
                    mx, my = manos[1]
                    img.paste(pieza, (int(mx - pcx), int(my - pbase + est["h"]*0.15)), pieza)
                if est.get("i") is not None and est["i"] in doodles:
                    _garabato_en_cabeza(img, ImageDraw.Draw(img), doodles[est["i"]], cab, reloj,
                                        random.Random(n//paso_hervor))
                if est["quien"] == "mokordo":
                    efecto = mascota.get("efecto") or est["p"].get("efecto")
                    if efecto in _GARABATOS or efecto in EFECTOS_EXTRA:
                        _garabato_en_cabeza(img, ImageDraw.Draw(img), _GARABATOS.get(efecto, efecto), cab,
                                            reloj, random.Random(n//paso_hervor))
            for o in vuelan:
                if o["que"] == "humo":
                    _humo(img, o["pos"], o["tam"], o.get("alfa", 0.8))
                    continue
                if o["que"] == "ceniza":
                    cx_, cy_ = o["pos"]
                    ImageDraw.Draw(img).ellipse([cx_ - o["tam"], cy_ - o["tam"]*0.5, cx_ + o["tam"], cy_ + o["tam"]*0.5],
                                                fill=(150, 150, 155))
                    continue
                if nombre_objeto(o["que"]) not in OBJETOS_TODOS:
                    continue
                pieza, pcx, pbase = _pieza_cosa(nombre_objeto(o["que"]), int(o["tam"]), max(3, int(ancho*0.0045)))
                _pega_girada(img, pieza, pieza.width/2, pieza.height/2, o["giro"], o["pos"][0], o["pos"][1])
            img = _camara_viva(img, reloj, segundos, mueve, golpes, foco)
            if camara:
                img = img.crop(camara).resize(tam, Image.BILINEAR)
            img = encima(img, visual or {}, reloj, segundos)
            if (visual or {}).get("_transicion") and reloj < _DURA_TRANSICION:
                img = _transicion(img, visual["_transicion"], reloj/_DURA_TRANSICION)
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
    # Las entradas de los personajes: el whoosh del que sale de la pared y
    # el pop del que cae o sale del suelo.
    ma = (visual or {}).get("mascota") if isinstance((visual or {}).get("mascota"), dict) else None
    llegan = []
    if ma and not ma.get("_ya") and str(ma.get("accion") or "") != "entra":
        llegan.append((_mascota.tipo_entrada(int(float(ma.get("x", 0.5))*10)), 0.0))
    retraso = 0.3 if llegan else 0.0
    for i, f in enumerate(e.get("figuras", [])):
        if not f.get("_ya"):
            llegan.append((_mascota.tipo_entrada(_mascota.semilla_entrada(f)), retraso + 0.22*i))
    for tipo, t0 in llegan:
        if tipo == "pared":
            salida.append(("whoosh", t0, 0.35))
        elif tipo == "cae":
            salida.append(("puf", t0 + 0.42, 0.3))
        else:
            salida.append(("pop", t0 + 0.05, 0.25))
    # El sonido de lo que hace cada uno: la tos, el hipo, los pasos, el polvo
    # al aterrizar de un salto, el "ding" de una idea.
    quienes = ([ma] if ma else []) + [f for f in e.get("figuras", []) if isinstance(f, dict)]
    for q in quienes:
        accion = str(q.get("accion") or "").lower()
        efecto = str(q.get("efecto") or "").lower()
        if accion == "tose":
            salida += [("tos", 0.1 + k*1.1, 0.45) for k in range(int(segundos/1.1) + 1)]
        elif accion == "borracho":
            salida += [("hic", 0.05 + k*1.7, 0.2) for k in range(int(segundos/1.7) + 1)]
        elif accion == "salta":
            salida += [("puf", 0.54 + k*0.8, 0.3) for k in range(1, int(segundos/0.8) + 1)]
        elif accion in ("anda", "corre"):
            salida.append(("pasos", 0.0, max(0.5, segundos)))
        if efecto in ("idea", "bombilla", "bulb", "lightbulb"):
            salida += [("ding", 0.25, 0.7), ("chispa", 0.3, 0.5)]
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
    salida += interaccion.sonidos(visual or {}, segundos)
    for _i, _tipo in e.get("_doodles", []):
        salida.append(("pop", 0.2, 0.25))
    return [s for s in salida if s[1] < segundos]
