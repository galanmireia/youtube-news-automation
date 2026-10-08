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
import math
import random
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import monigotes as m

_FUENTE = Path(__file__).parent / "data" / "fuentes" / "PermanentMarker.woff"
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
           stroke_width=max(3, int(t*0.04)), stroke_fill=TINTA)


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


OBJETOS = {
    "cerebro": _cerebro, "ojo": _ojo, "corazon": _corazon, "pulmones": _pulmones,
    "estomago": _estomago, "bacteria": _bacteria, "virus": _virus, "cebolla": _cebolla,
    "termometro": _termometro, "ventilador": _ventilador, "cama": _cama, "despertador": _reloj,
    "movil": _telefono, "gota": _gota, "calavera": _calavera, "taza": _taza, "pastilla": _pastilla,
    "luna": _luna, "hielo": _hielo, "planta": _planta, "hamburguesa": _hamburguesa,
    "bombilla": _bombilla, "peligro": _peligro, "bien": _bien, "mal": _mal, "igual": _igual,
    "interrogacion": _interrogacion, "calor": _calor, "frio": _frio, "billete": _dinero,
}
# Y los de monigotes que pegan en este canal.
_DE_MONIGOTES = ("sol", "nube", "fuego", "perro", "caballo", "vaso", "libro", "arbol", "casa",
                 "dinero", "pelota", "maletin", "calendario", "periodico")
OBJETOS_VALIDOS = tuple(OBJETOS) + tuple(n for n in _DE_MONIGOTES if n in m.COSAS)
# Se registran en monigotes para que montar() los pinte como cualquier cosa.
for _n, _f in OBJETOS.items():
    m.COSAS.setdefault(_n, _f)

QUIENES = ("persona", "persona_b", "nino")


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
    borde = TINTA if relleno != TINTA else None
    trazo = max(2, int(px*0.05)) if borde else 0
    caja = f.getbbox(texto, anchor="mm", stroke_width=trazo)
    w, h = caja[2] - caja[0] + 8, caja[3] - caja[1] + 8
    pieza = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(pieza).text((w/2, h/2), texto, font=f, fill=relleno, anchor="mm",
                               stroke_width=trazo, stroke_fill=borde)
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
        p = min(1.0, max(0.0, (t - 0.3 - k*0.4)/0.6))
        if p <= 0:
            continue
        a, b = (w*float(x0), h*float(y0)), (w*float(x1), h*float(y1))
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
    for k, tx in enumerate(visual.get("textos") or []):
        texto = str(tx.get("texto") or "")[:40]
        if not texto:
            continue
        px = h*min(0.3, max(0.04, float(tx.get("tam") or 0.12)))
        x, y = w*float(tx.get("x", 0.5)), h*float(tx.get("y", 0.2))
        px = _que_quepa(texto, px, min(x, w - x)*2*0.95)
        _letrero(img, texto, (x, y), px, _color(tx.get("color")), float(tx.get("giro") or 0),
                 _escala_pop(t - 0.15 - k*0.35))
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
        figuras.append(f)
    e = m.limpia({"figuras": figuras}) if figuras else {"figuras": []}
    e["interior"] = "blanco"
    # Mas abajo que en los decorados: en un folio en blanco el monigote es el
    # protagonista y ocupa media pantalla.
    e["suelo"] = 0.76
    e["hablan"], e["a_quien"] = [], []
    cosas = []
    for c in (visual.get("cosas") or [])[:5]:
        que = str((c or {}).get("que") or "").lower()
        if que not in OBJETOS_VALIDOS:
            continue
        tam = min(0.55, max(0.06, float(c.get("tam") or 0.25)))
        cosa = {"que": que, "x": min(0.95, max(0.05, float(c.get("x", 0.5)))), "tam": tam,
                "delante": bool(c.get("delante"))}
        if c.get("y") is not None:
            cosa["y"] = min(0.98, float(c["y"]) + tam/2)      # el centro -> la base
        cosas.append(cosa)
    e["cosas"] = cosas
    # Sin nadie de pie ni nada apoyado, no hay suelo: la cifra gigante o
    # "ventilador = calavera" van en el folio limpio.
    if not e["figuras"] and all("y" in c for c in cosas):
        e["interior"] = "folio"
    return e


def fotos(visual: dict, segundos: float, fps: float, tam=(1920, 1080), calma: float = 1.6):
    """Los dibujos del plano: los monigotes animados (respiran, cambian de
    postura, sus efectos) en el folio en blanco, y encima los letreros, la
    cifra y las flechas apareciendo."""
    e = _spec(visual or {})
    reloj = 0.0
    for img in m.animar(e, segundos=segundos, fps=fps, tam=tam, calma=calma):
        yield encima(img.convert("RGB"), visual or {}, reloj, segundos)
        reloj += 1/fps


def sonidos_del_plano(visual: dict, segundos: float) -> list:
    """El ¡boing! y el golpe de los efectos, y un 'pop' por letrero."""
    e = _spec(visual or {})
    salida = []
    for f in e.get("figuras", []):
        efecto = f.get("efecto")
        if efecto in m.SONIDO_DEL_EFECTO:
            nombre, dura = m.SONIDO_DEL_EFECTO[efecto]
            t0 = m.momento_del_efecto(efecto, segundos)
            if t0 < segundos:
                salida.append((nombre, t0, dura))
    return salida
