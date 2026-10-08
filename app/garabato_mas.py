"""MAS DIBUJOS para Why Though, todos con el mismo estilo que los de garabato:
trazo negro gordo, relleno plano y colores vivos.

Ella: "ten preparados todos los dibujos con el mismo estilo y usa colores".
Asi el guion casi nunca pide algo que no tenemos: el cuerpo y la salud, la
casa, la comida, la naturaleza y el espacio, los transportes, los animales
y los iconos de explicar cosas (graficos, lupa, candado...).

Misma firma que las COSAS de monigotes: (d, x, y, t, rnd, g, tinta), con
(x, y) el centro de abajo y t la altura.
"""
import math

from . import monigotes as m

TINTA = (22, 22, 22)
ROJO, NARANJA, AMARILLO = (226, 38, 38), (242, 140, 28), (250, 206, 20)
AZUL, CELESTE, VERDE = (38, 128, 228), (150, 210, 250), (52, 170, 72)
VERDE_CLARO, ROSA, MORADO = (140, 210, 90), (240, 120, 160), (140, 80, 200)
CARNE, MARRON, CHOCOLATE = (255, 214, 180), (160, 105, 60), (110, 65, 35)
GRIS, GRIS_OSCURO, BLANCO = (180, 180, 185), (90, 90, 100), (255, 255, 255)
CREMA, DORADO = (250, 240, 210), (240, 185, 40)


def _cont(d, pts, relleno, g, rnd):
    d.polygon(pts, fill=relleno)
    m._linea(d, list(pts) + [pts[0]], g, rnd, color=TINTA, temblor=1.0)


def _ov(d, caja, relleno, g):
    d.ellipse(caja, fill=relleno, outline=TINTA, width=g)


def _circ(d, cx, cy, r, relleno, g):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=relleno, outline=TINTA, width=g)


def _caja(d, caja, relleno, g, radio=0):
    if radio:
        d.rounded_rectangle(caja, radius=max(1, int(radio)), fill=relleno, outline=TINTA, width=g)
    else:
        d.rectangle(caja, fill=relleno, outline=TINTA, width=g)


def _raya(d, pts, g, rnd, color=TINTA):
    m._linea(d, pts, g, rnd, color=color, temblor=0.8)


def _arco(cx, cy, rx, ry, a0, a1, n=30):
    """Puntos de una elipse de a0 a a1 (grados; 90 = abajo, que la y baja)."""
    return [(cx + rx*math.cos(math.radians(a0 + (a1 - a0)*i/n)),
             cy + ry*math.sin(math.radians(a0 + (a1 - a0)*i/n))) for i in range(n + 1)]


def _ojo(d, cx, cy, r):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=TINTA)
    d.ellipse([cx - r*0.15, cy - r*0.75, cx + r*0.45, cy - r*0.15], fill=BLANCO)


def _brillo(d, cx, cy, r, g):
    d.arc([cx - r, cy - r, cx + r, cy + r], 200, 250, fill=BLANCO, width=max(2, g//2))


def _nube_rellena(d, piezas, relleno, g):
    """Varios circulos que se tocan: primero todos con borde, luego todos
    rellenos un poco mas pequenos, para que solo quede el borde de fuera."""
    for cx, cy, r in piezas:
        _circ(d, cx, cy, r, relleno, g)
    for cx, cy, r in piezas:
        d.ellipse([cx - r + g, cy - r + g, cx + r - g, cy + r - g], fill=relleno)


# ---- El cuerpo y la salud -------------------------------------------------

def _diente(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*0.75
    pts = [(x - w*0.5, y - t*0.72), (x - w*0.47, y - t*0.93), (x - w*0.25, y - t), (x, y - t*0.92),
           (x + w*0.25, y - t), (x + w*0.47, y - t*0.93), (x + w*0.5, y - t*0.72),
           (x + w*0.4, y - t*0.42), (x + w*0.34, y - t*0.05), (x + w*0.2, y), (x + w*0.1, y - t*0.3),
           (x, y - t*0.36), (x - w*0.1, y - t*0.3), (x - w*0.2, y), (x - w*0.34, y - t*0.05),
           (x - w*0.4, y - t*0.42)]
    _cont(d, pts, BLANCO, g, rnd)
    d.arc([x - w*0.4, y - t*0.95, x - w*0.05, y - t*0.55], 190, 260, fill=CELESTE, width=max(2, g//2))


def _hueso(d, x, y, t, rnd, g, tinta=TINTA):
    cy, l, r = y - t*0.3, t*0.62, t*0.15
    for sx in (-1, 1):
        for sy in (-1, 1):
            _circ(d, x + sx*l, cy + sy*r*0.85, r, CREMA, g)
    d.rectangle([x - l, cy - r*0.75, x + l, cy + r*0.75], fill=CREMA)
    for sy in (-1, 1):
        _raya(d, [(x - l + r*0.3, cy + sy*r*0.75), (x + l - r*0.3, cy + sy*r*0.75)], g, rnd)


def _nariz(d, x, y, t, rnd, g, tinta=TINTA):
    _cont(d, [(x - t*0.1, y - t), (x + t*0.1, y - t), (x + t*0.24, y - t*0.35), (x - t*0.24, y - t*0.35)],
          CARNE, g, rnd)
    for lado in (-1, 1):
        _ov(d, [x + lado*t*0.3 - t*0.15, y - t*0.38, x + lado*t*0.3 + t*0.15, y - t*0.04], CARNE, g)
    _ov(d, [x - t*0.22, y - t*0.48, x + t*0.22, y - t*0.06], CARNE, g)
    for lado in (-1, 1):
        d.ellipse([x + lado*t*0.2 - t*0.06, y - t*0.14, x + lado*t*0.2 + t*0.06, y - t*0.06], fill=TINTA)


def _oreja(d, x, y, t, rnd, g, tinta=TINTA):
    cy = y - t*0.55
    pts = _arco(x, cy, t*0.32, t*0.45, -200, 20, 32) + [(x + t*0.05, y - t*0.05), (x - t*0.12, y)]
    _cont(d, pts, CARNE, g, rnd)
    d.arc([x - t*0.18, cy - t*0.3, x + t*0.2, cy + t*0.2], 190, 40, fill=(210, 140, 120), width=g)
    d.arc([x - t*0.06, cy - t*0.1, x + t*0.1, cy + t*0.12], 150, 360, fill=(210, 140, 120),
          width=max(2, g//2))


def _lengua(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*0.9
    lengua = [(x - w*0.28, y - t*0.62), (x - w*0.28, y - t*0.42)] + \
        _arco(x, y - t*0.42, w*0.28, t*0.4, 180, 0, 24)[1:] + [(x + w*0.28, y - t*0.62)]
    _cont(d, lengua, ROSA, g, rnd)
    _raya(d, [(x, y - t*0.55), (x, y - t*0.25)], max(2, g//2), rnd, color=(200, 70, 110))
    _ov(d, [x - w/2, y - t, x + w/2, y - t*0.55], ROJO, g)
    d.ellipse([x - w*0.36, y - t*0.86, x + w*0.36, y - t*0.66], fill=(90, 20, 30))


def _gota_de(color):
    def dibujo(d, x, y, t, rnd, g, tinta=TINTA):
        cy, r = y - t*0.32, t*0.32
        pts = [(x, y - t)] + _arco(x, cy, r, r, -30, 210, 24)
        _cont(d, pts, color, g, rnd)
        d.arc([x - r*0.6, cy - r*0.5, x - r*0.05, cy + r*0.5], 120, 220, fill=BLANCO, width=max(2, g//2))
    return dibujo


def _musculo(d, x, y, t, rnd, g, tinta=TINTA):
    """El brazo sacando bola."""
    P = lambda a, b: (x + t*a, y - t*b)
    brazo = [P(-0.6, 0.05), P(0.25, 0.05), P(0.42, 0.18), P(0.44, 0.7), P(0.22, 0.7), P(0.2, 0.35)] + \
        [(x + t*a, y - t*b) for a, b in ((0.1, 0.52), (-0.05, 0.62), (-0.22, 0.6), (-0.38, 0.48))] + \
        [P(-0.6, 0.42)]
    _cont(d, brazo, CARNE, g, rnd)
    _circ(d, x + t*0.33, y - t*0.82, t*0.15, CARNE, g)
    d.arc([x - t*0.25, y - t*0.55, x + t*0.05, y - t*0.3], 200, 330, fill=(210, 140, 120), width=max(2, g//2))
    for k in range(3):
        a = math.radians(-150 + k*30)
        cx, cy = x - t*0.05, y - t*0.68
        d.line([(cx + math.cos(a)*t*0.12, cy + math.sin(a)*t*0.12), (cx + math.cos(a)*t*0.22, cy + math.sin(a)*t*0.22)],
               fill=AMARILLO, width=g)


def _jeringa(d, x, y, t, rnd, g, tinta=TINTA):
    cy, h = y - t*0.3, t*0.13
    _raya(d, [(x - t*0.45, cy), (x - t*0.72, cy)], g, rnd)
    _caja(d, [x - t*0.78, cy - h*1.3, x - t*0.7, cy + h*1.3], GRIS, max(2, g//2))
    _caja(d, [x - t*0.45, cy - h, x + t*0.25, cy + h], BLANCO, g)
    d.rectangle([x - t*0.2, cy - h + g, x + t*0.25 - g, cy + h - g], fill=CELESTE)
    for k in range(4):
        xx = x - t*0.3 + k*t*0.13
        d.line([(xx, cy - h), (xx, cy - h*0.4)], fill=TINTA, width=max(2, g//3))
    _caja(d, [x + t*0.25, cy - h*0.45, x + t*0.34, cy + h*0.45], GRIS, max(2, g//2))
    d.line([(x + t*0.34, cy), (x + t*0.72, cy)], fill=GRIS_OSCURO, width=max(2, g//2))


def _tirita(d, x, y, t, rnd, g, tinta=TINTA):
    cy, w, h = y - t*0.3, t*1.2, t*0.36
    _caja(d, [x - w/2, cy - h/2, x + w/2, cy + h/2], (236, 190, 140), g, h/2)
    _caja(d, [x - w*0.17, cy - h*0.35, x + w*0.17, cy + h*0.35], (250, 225, 195), max(2, g//2), h*0.1)
    for dx in (-0.36, -0.28, 0.28, 0.36):
        for dy in (-0.15, 0.15):
            d.ellipse([x + w*dx - 3, cy + h*dy - 3, x + w*dx + 3, cy + h*dy + 3], fill=(200, 150, 100))


def _mascarilla(d, x, y, t, rnd, g, tinta=TINTA):
    cy, w, h = y - t*0.4, t*0.9, t*0.5
    for lado in (-1, 1):
        d.arc([x + lado*w*0.5 - t*0.18, cy - h*0.45, x + lado*w*0.5 + t*0.18, cy + h*0.45],
              270 if lado > 0 else 90, 90 if lado > 0 else 270, fill=GRIS_OSCURO, width=max(2, g//2))
    _cont(d, [(x - w/2, cy - h*0.38), (x, cy - h/2), (x + w/2, cy - h*0.38), (x + w/2, cy + h*0.3),
              (x, cy + h/2), (x - w/2, cy + h*0.3)], (170, 215, 240), g, rnd)
    for k in (-0.15, 0.05, 0.25):
        d.line([(x - w*0.42, cy + h*k), (x + w*0.42, cy + h*k)], fill=(110, 170, 210), width=max(2, g//2))


def _microscopio(d, x, y, t, rnd, g, tinta=TINTA):
    cuerpo = (90, 130, 200)
    _caja(d, [x - t*0.4, y - t*0.1, x + t*0.35, y], cuerpo, g, t*0.03)
    m._linea(d, [(x + t*0.18, y - t*0.1), (x + t*0.28, y - t*0.4), (x + t*0.12, y - t*0.72)],
             int(g*2.4), rnd, color=TINTA)
    m._linea(d, [(x + t*0.18, y - t*0.1), (x + t*0.28, y - t*0.4), (x + t*0.12, y - t*0.72)],
             int(g*1.2), rnd, color=cuerpo)
    _raya(d, [(x - t*0.32, y - t*0.36), (x + t*0.22, y - t*0.36)], int(g*1.3), rnd)
    a = math.radians(-65)
    dx, dy = math.cos(a), math.sin(a)
    px, py = -dy*t*0.08, dx*t*0.08
    base, punta = (x - t*0.08, y - t*0.45), (x - t*0.08 + dx*t*0.55, y - t*0.45 + dy*t*0.55)
    _cont(d, [(base[0] + px, base[1] + py), (base[0] - px, base[1] - py),
              (punta[0] - px, punta[1] - py), (punta[0] + px, punta[1] + py)], GRIS, g, rnd)
    _caja(d, [punta[0] - t*0.1, punta[1] - t*0.06, punta[0] + t*0.1, punta[1] + t*0.04], GRIS_OSCURO,
          max(2, g//2))


def _adn(d, x, y, t, rnd, g, tinta=TINTA):
    n, w = 40, t*0.24
    a = [(x + w*math.sin(i/n*3*math.pi), y - i/n*t) for i in range(n + 1)]
    b = [(x - w*math.sin(i/n*3*math.pi), y - i/n*t) for i in range(n + 1)]
    for k, i in enumerate(range(2, n, 3)):
        d.line([a[i], b[i]], fill=(AMARILLO, VERDE, NARANJA, ROSA)[k % 4], width=max(3, g))
    for hebra, color in ((a, AZUL), (b, ROJO)):
        d.line(hebra, fill=TINTA, width=int(g*2.2), joint="curve")
        d.line(hebra, fill=color, width=max(2, int(g*1.1)), joint="curve")


def _celula(d, x, y, t, rnd, g, tinta=TINTA):
    cy = y - t*0.45
    pts = [(x + t*0.62*math.cos(a)*(1 + 0.05*math.sin(3*a)), cy + t*0.44*math.sin(a)*(1 + 0.06*math.cos(4*a)))
           for a in [i*math.pi/24 for i in range(48)]]
    _cont(d, pts, (190, 235, 160), g, rnd)
    _circ(d, x - t*0.1, cy - t*0.04, t*0.17, MORADO, g)
    d.ellipse([x - t*0.16, cy - t*0.1, x - t*0.06, cy], fill=(90, 40, 140))
    for cx, cy2, rx, ry in ((0.3, -0.15, 0.1, 0.05), (0.25, 0.18, 0.12, 0.05), (-0.42, 0.1, 0.07, 0.07)):
        _ov(d, [x + t*cx - t*rx, cy + t*cy2 - t*ry, x + t*cx + t*rx, cy + t*cy2 + t*ry], NARANJA,
            max(2, g//2))


def _neurona(d, x, y, t, rnd, g, tinta=TINTA):
    cx, cy, r = x - t*0.35, y - t*0.55, t*0.17
    for k in range(5):
        a = math.radians(110 + k*35)
        p1 = (cx + math.cos(a)*r*2.2, cy + math.sin(a)*r*2.2)
        _raya(d, [(cx, cy), p1], g, rnd)
        for s in (-0.5, 0.5):
            _raya(d, [p1, (p1[0] + math.cos(a + s)*r, p1[1] + math.sin(a + s)*r)], max(2, g//2), rnd)
    ax = [(cx + r, cy), (x + t*0.1, cy + t*0.1), (x + t*0.45, cy + t*0.3)]
    m._linea(d, ax, int(g*1.4), rnd, color=TINTA)
    for k in range(3):
        d.ellipse([x - t*0.12 + k*t*0.18, cy + t*0.02 + k*t*0.08, x + t*0.0 + k*t*0.18,
                   cy + t*0.12 + k*t*0.08], fill=NARANJA, outline=TINTA, width=max(2, g//3))
    for s in (-0.6, 0, 0.6):
        _raya(d, [ax[-1], (ax[-1][0] + math.cos(0.5 + s)*r*1.1, ax[-1][1] + math.sin(0.5 + s)*r*1.1)],
              max(2, g//2), rnd)
    _circ(d, cx, cy, r, AMARILLO, g)
    d.ellipse([cx - r*0.35, cy - r*0.35, cx + r*0.35, cy + r*0.35], fill=NARANJA)


# ---- La casa --------------------------------------------------------------

def _nevera(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*0.55
    _caja(d, [x - w/2, y - t, x + w/2, y], (225, 238, 250), g, t*0.05)
    _raya(d, [(x - w/2, y - t*0.64), (x + w/2, y - t*0.64)], g, rnd)
    for y0, y1 in ((0.9, 0.74), (0.55, 0.35)):
        _caja(d, [x - w*0.38, y - t*y0, x - w*0.3, y - t*y1], GRIS, max(2, g//2))
    d.ellipse([x + w*0.1, y - t*0.85, x + w*0.24, y - t*0.77], fill=ROJO, outline=TINTA)
    d.ellipse([x + w*0.05, y - t*0.5, x + w*0.2, y - t*0.42], fill=AMARILLO, outline=TINTA)


def _microondas(d, x, y, t, rnd, g, tinta=TINTA):
    w, h = t*1.2, t*0.66
    _caja(d, [x - w/2, y - h, x + w/2, y], (220, 220, 225), g, t*0.04)
    _caja(d, [x - w*0.42, y - h*0.84, x + w*0.18, y - h*0.16], (70, 100, 120), g, t*0.03)
    d.ellipse([x - w*0.2, y - h*0.4, x - w*0.04, y - h*0.26], fill=NARANJA)
    for k in range(3):
        d.ellipse([x + w*0.27, y - h*0.8 + k*h*0.22, x + w*0.37, y - h*0.66 + k*h*0.22], fill=GRIS_OSCURO)


def _inodoro(d, x, y, t, rnd, g, tinta=TINTA):
    _caja(d, [x - t*0.26, y - t, x + t*0.26, y - t*0.62], BLANCO, g, t*0.04)
    _cont(d, [(x - t*0.36, y - t*0.58), (x + t*0.36, y - t*0.58), (x + t*0.2, y - t*0.22),
              (x + t*0.17, y), (x - t*0.17, y), (x - t*0.2, y - t*0.22)], BLANCO, g, rnd)
    _ov(d, [x - t*0.4, y - t*0.68, x + t*0.4, y - t*0.5], (210, 230, 245), g)
    _caja(d, [x + t*0.12, y - t*0.92, x + t*0.2, y - t*0.86], GRIS, max(2, g//2))


def _ducha(d, x, y, t, rnd, g, tinta=TINTA):
    m._linea(d, [(x - t*0.45, y), (x - t*0.45, y - t*0.95), (x + t*0.05, y - t*0.95), (x + t*0.05, y - t*0.82)],
             int(g*1.4), rnd, color=GRIS_OSCURO)
    _cont(d, [(x - t*0.08, y - t*0.82), (x + t*0.18, y - t*0.82), (x + t*0.3, y - t*0.68),
              (x - t*0.2, y - t*0.68)], GRIS, g, rnd)
    for k in range(5):
        px = x - t*0.15 + k*t*0.1
        for j in range(3):
            yy = y - t*0.58 + j*t*0.17 + (k % 2)*t*0.06
            d.line([(px + (k - 2)*t*0.02*j, yy), (px + (k - 2)*t*0.025*(j + 0.6), yy + t*0.08)], fill=AZUL,
                   width=max(2, g//2))


def _ordenador(d, x, y, t, rnd, g, tinta=TINTA):
    w, h = t*1.1, t*0.7
    _caja(d, [x - t*0.08, y - t*0.32, x + t*0.08, y - t*0.08], GRIS, g)
    _caja(d, [x - t*0.3, y - t*0.08, x + t*0.3, y], GRIS, g, t*0.03)
    _caja(d, [x - w/2, y - t, x + w/2, y - t*0.3], (50, 52, 60), g, t*0.04)
    _caja(d, [x - w/2 + g*2, y - t + g*2, x + w/2 - g*2, y - t*0.3 - g*2], (110, 190, 245), 0)
    for k in range(3):
        d.line([(x - w*0.38, y - t*0.86 + k*t*0.1), (x - w*0.38 + w*(0.5 - k*0.12), y - t*0.86 + k*t*0.1)],
               fill=BLANCO, width=max(2, g//2))


def _enchufe(d, x, y, t, rnd, g, tinta=TINTA):
    cy, a = y - t*0.45, t*0.45
    _caja(d, [x - a, cy - a, x + a, cy + a], BLANCO, g, t*0.12)
    _circ(d, x, cy, a*0.68, (225, 225, 230), g)
    for lado in (-1, 1):
        d.ellipse([x + lado*a*0.3 - a*0.1, cy - a*0.1, x + lado*a*0.3 + a*0.1, cy + a*0.1], fill=TINTA)


def _espejo(d, x, y, t, rnd, g, tinta=TINTA):
    _caja(d, [x - t*0.25, y - t*0.06, x + t*0.25, y], DORADO, g)
    _raya(d, [(x, y - t*0.06), (x, y - t*0.2)], int(g*1.4), rnd)
    _ov(d, [x - t*0.34, y - t, x + t*0.34, y - t*0.18], DORADO, g)
    d.ellipse([x - t*0.26, y - t*0.92, x + t*0.26, y - t*0.26], fill=(200, 235, 250), outline=TINTA,
              width=max(2, g//2))
    for k in (0, 0.1):
        d.line([(x - t*0.12 + t*k, y - t*0.75), (x + t*0.0 + t*k, y - t*0.85)], fill=BLANCO, width=g)


def _almohada(d, x, y, t, rnd, g, tinta=TINTA):
    cy, w, h = y - t*0.3, t*1.1, t*0.55
    pts = [(x - w/2, cy - h/2), (x, cy - h*0.4), (x + w/2, cy - h/2), (x + w*0.44, cy),
           (x + w/2, cy + h/2), (x, cy + h*0.4), (x - w/2, cy + h/2), (x - w*0.44, cy)]
    lisos = []
    for a, b in zip(pts, pts[1:] + pts[:1]):
        lisos += [a, ((a[0] + b[0])/2, (a[1] + b[1])/2)]
    _cont(d, lisos, (215, 210, 250), g, rnd)


def _sofa(d, x, y, t, rnd, g, tinta=TINTA):
    w, c = t*1.5, (230, 100, 80)
    _caja(d, [x - w*0.42, y - t*0.85, x + w*0.42, y - t*0.35], c, g, t*0.08)
    _caja(d, [x - w*0.42, y - t*0.45, x + w*0.42, y - t*0.15], (245, 130, 105), g, t*0.06)
    for lado in (-1, 1):
        _caja(d, [x + lado*w*0.5 - t*0.13, y - t*0.6, x + lado*w*0.5 + t*0.13, y - t*0.12], c, g, t*0.06)
        _raya(d, [(x + lado*w*0.4, y - t*0.12), (x + lado*w*0.4, y)], g, rnd)


def _tele(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*1.1
    for lado in (-1, 1):
        _raya(d, [(x, y - t*0.82), (x + lado*t*0.25, y - t)], max(2, g//2), rnd)
        _raya(d, [(x + lado*w*0.32, y - t*0.1), (x + lado*w*0.38, y)], g, rnd)
    _caja(d, [x - w/2, y - t*0.82, x + w/2, y - t*0.1], (150, 100, 60), g, t*0.06)
    _caja(d, [x - w*0.42, y - t*0.74, x + w*0.24, y - t*0.18], (110, 190, 245), g, t*0.06)
    for k in range(2):
        _circ(d, x + w*0.36, y - t*(0.62 - k*0.2), t*0.05, AMARILLO, max(2, g//2))


def _lavadora(d, x, y, t, rnd, g, tinta=TINTA):
    a = t*0.8
    _caja(d, [x - a/2, y - t, x + a/2, y], BLANCO, g, t*0.05)
    _raya(d, [(x - a/2, y - t*0.8), (x + a/2, y - t*0.8)], max(2, g//2), rnd)
    _circ(d, x + a*0.3, y - t*0.9, t*0.05, ROJO, max(2, g//2))
    _circ(d, x, y - t*0.4, a*0.32, GRIS, g)
    _circ(d, x, y - t*0.4, a*0.22, (110, 180, 240), g)
    d.arc([x - a*0.15, y - t*0.5, x + a*0.15, y - t*0.3], 200, 300, fill=BLANCO, width=max(2, g//2))


def _grifo(d, x, y, t, rnd, g, tinta=TINTA):
    _caja(d, [x - t*0.5, y - t*0.82, x + t*0.2, y - t*0.66], GRIS, g, t*0.05)
    _caja(d, [x + t*0.06, y - t*0.82, x + t*0.24, y - t*0.5], GRIS, g, t*0.05)
    _caja(d, [x - t*0.22, y - t, x - t*0.12, y - t*0.82], GRIS_OSCURO, max(2, g//2))
    _caja(d, [x - t*0.32, y - t*1.0, x - t*0.02, y - t*0.94], AZUL, max(2, g//2), t*0.03)
    _gota_de((60, 150, 235))(d, x + t*0.15, y - t*0.05, t*0.3, rnd, max(2, g//2))


def _llave(d, x, y, t, rnd, g, tinta=TINTA):
    cy = y - t*0.3
    _caja(d, [x - t*0.15, cy - t*0.07, x + t*0.6, cy + t*0.07], DORADO, g)
    _cont(d, [(x + t*0.3, cy + t*0.07), (x + t*0.4, cy + t*0.07), (x + t*0.4, cy + t*0.22),
              (x + t*0.3, cy + t*0.22)], DORADO, max(2, g//2), rnd)
    _cont(d, [(x + t*0.46, cy + t*0.07), (x + t*0.56, cy + t*0.07), (x + t*0.56, cy + t*0.17),
              (x + t*0.46, cy + t*0.17)], DORADO, max(2, g//2), rnd)
    _circ(d, x - t*0.35, cy, t*0.26, DORADO, g)
    _circ(d, x - t*0.35, cy, t*0.1, BLANCO, max(2, g//2))


# ---- La comida -------------------------------------------------------------

def _manzana(d, x, y, t, rnd, g, tinta=TINTA):
    cy, r = y - t*0.4, t*0.4
    pts = [(x + r*math.cos(a)*(1.05 - 0.1*math.sin(a)), cy + r*math.sin(a)) for a in
           [i*math.pi/24 for i in range(48)]]
    pts = [(px, py + (r*0.25*(1 - abs(px - x)/(r*0.5)) if py < cy and abs(px - x) < r*0.5 else 0))
           for px, py in pts]
    _cont(d, pts, ROJO, g, rnd)
    _raya(d, [(x, y - t*0.72), (x + t*0.05, y - t*0.95)], g, rnd, color=MARRON)
    _ov(d, [x + t*0.06, y - t*1.0, x + t*0.36, y - t*0.86], VERDE, max(2, g//2))
    _brillo(d, x - r*0.1, cy, r*0.6, g)


def _platano(d, x, y, t, rnd, g, tinta=TINTA):
    fuera = _arco(x, y - t*0.85, t*0.65, t*0.8, 20, 160, 28)
    dentro = _arco(x, y - t*1.1, t*0.55, t*0.75, 150, 30, 28)
    _cont(d, fuera + dentro, AMARILLO, g, rnd)
    for p in (fuera[0], fuera[-1]):
        d.ellipse([p[0] - t*0.05, p[1] - t*0.07, p[0] + t*0.05, p[1] + t*0.01], fill=CHOCOLATE)


def _pizza(d, x, y, t, rnd, g, tinta=TINTA):
    _cont(d, [(x - t*0.48, y - t*0.85), (x + t*0.48, y - t*0.85), (x, y)], (252, 205, 90), g, rnd)
    _caja(d, [x - t*0.55, y - t, x + t*0.55, y - t*0.8], (215, 140, 60), g, t*0.1)
    for cx, cy in ((-0.18, 0.62), (0.15, 0.6), (0, 0.35)):
        _circ(d, x + t*cx, y - t*cy, t*0.08, ROJO, max(2, g//2))
    d.ellipse([x + t*0.12, y - t*0.42, x + t*0.2, y - t*0.36], fill=VERDE)


def _huevo(d, x, y, t, rnd, g, tinta=TINTA):
    cy, rx, ry = y - t*0.45, t*0.34, t*0.45
    pts = [(x + rx*math.cos(a)*(1 - 0.22*max(0, -math.sin(a))), cy + ry*math.sin(a))
           for a in [i*math.pi/24 for i in range(48)]]
    _cont(d, pts, CREMA, g, rnd)
    _brillo(d, x - rx*0.1, cy - ry*0.1, rx*0.65, g)


def _queso(d, x, y, t, rnd, g, tinta=TINTA):
    q = (252, 210, 70)
    _cont(d, [(x - t*0.6, y - t*0.3), (x + t*0.35, y - t*0.75), (x + t*0.6, y - t*0.6), (x - t*0.35, y - t*0.15)],
          (255, 230, 120), g, rnd)
    _cont(d, [(x - t*0.6, y - t*0.3), (x - t*0.35, y - t*0.15), (x - t*0.35, y), (x - t*0.6, y - t*0.12)],
          (230, 180, 50), g, rnd)
    _cont(d, [(x - t*0.35, y - t*0.15), (x + t*0.6, y - t*0.6), (x + t*0.6, y - t*0.42), (x - t*0.35, y)],
          q, g, rnd)
    for cx, cy, r in ((-0.1, 0.2, 0.05), (0.2, 0.33, 0.06), (0.42, 0.45, 0.04)):
        d.ellipse([x + t*cx - t*r, y - t*cy - t*r*0.8, x + t*cx + t*r, y - t*cy + t*r*0.8], fill=(215, 160, 40))


def _chocolate(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*0.6
    _caja(d, [x - w/2, y - t, x + w/2, y], CHOCOLATE, g, t*0.04)
    for k in (1, 2):
        d.line([(x - w/2 + k*w/3, y - t), (x - w/2 + k*w/3, y - t*0.45)], fill=(70, 40, 20), width=max(2, g//2))
    for k in (1, 2, 3):
        d.line([(x - w/2, y - t + k*t*0.14), (x + w/2, y - t + k*t*0.14)], fill=(70, 40, 20), width=max(2, g//2))
    _cont(d, [(x - w/2 - t*0.02, y - t*0.5), (x - w*0.1, y - t*0.42), (x + w*0.2, y - t*0.52),
              (x + w/2 + t*0.02, y - t*0.45), (x + w/2 + t*0.02, y), (x - w/2 - t*0.02, y)], ROJO, g, rnd)


def _tubo(centro, anchos):
    """Un contorno alrededor de una linea central, con su grosor en cada punto."""
    izq, der = [], []
    for k, (p, a) in enumerate(zip(centro, anchos)):
        q0, q1 = centro[max(0, k - 1)], centro[min(len(centro) - 1, k + 1)]
        dx, dy = q1[0] - q0[0], q1[1] - q0[1]
        n = math.hypot(dx, dy) or 1
        izq.append((p[0] - dy/n*a, p[1] + dx/n*a))
        der.append((p[0] + dy/n*a, p[1] - dx/n*a))
    return izq + der[::-1]


def _guindilla(d, x, y, t, rnd, g, tinta=TINTA):
    centro = [(x - t*0.3 + t*0.55*s + t*0.12*math.sin(s*math.pi), y - t*0.82 + t*0.8*s**1.4)
              for s in [i/16 for i in range(17)]]
    anchos = [t*0.13*(1 - s)**0.6 + t*0.01 for s in [i/16 for i in range(17)]]
    _cont(d, _tubo(centro, anchos), ROJO, g, rnd)
    d.arc([centro[3][0] - t*0.1, centro[3][1] - t*0.05, centro[3][0] + t*0.02, centro[3][1] + t*0.1], 200, 280,
          fill=BLANCO, width=max(2, g//2))
    _ov(d, [x - t*0.44, y - t*0.92, x - t*0.18, y - t*0.76], VERDE, max(2, g//2))
    _raya(d, [(x - t*0.32, y - t*0.9), (x - t*0.4, y - t*1.0)], g, rnd, color=(40, 120, 50))


def _limon(d, x, y, t, rnd, g, tinta=TINTA):
    cy, rx, ry = y - t*0.35, t*0.5, t*0.35
    pts = [(x + rx*math.cos(a)*(1 + 0.25*math.cos(a)**8), cy + ry*math.sin(a)) for a in
           [i*math.pi/24 for i in range(48)]]
    _cont(d, pts, (250, 225, 40), g, rnd)
    _brillo(d, x - rx*0.1, cy, ry*0.75, g)


def _sal(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*0.5
    _cont(d, [(x - w*0.4, y - t*0.75), (x + w*0.4, y - t*0.75), (x + w*0.5, y), (x - w*0.5, y)],
          (235, 245, 250), g, rnd)
    d.rectangle([x - w*0.4, y - t*0.5, x + w*0.4, y - t*0.05], fill=BLANCO)
    d.chord([x - w*0.42, y - t*1.0, x + w*0.42, y - t*0.55], 180, 360, fill=GRIS, outline=TINTA, width=g)
    for k in (-0.2, 0, 0.2):
        d.ellipse([x + w*k - 3, y - t*0.87 - 3, x + w*k + 3, y - t*0.87 + 3], fill=TINTA)


def _helado(d, x, y, t, rnd, g, tinta=TINTA):
    _cont(d, [(x - t*0.24, y - t*0.55), (x + t*0.24, y - t*0.55), (x, y)], (230, 180, 110), g, rnd)
    for k in (-1, 1):
        d.line([(x - t*0.12*k, y - t*0.55), (x + t*0.08*k, y - t*0.2)], fill=(180, 120, 60), width=max(2, g//2))
    _circ(d, x, y - t*0.6, t*0.22, (250, 160, 190), g)
    _circ(d, x, y - t*0.82, t*0.18, (150, 95, 60), g)
    _circ(d, x + t*0.03, y - t*1.0, t*0.04, ROJO, max(2, g//2))


def _palomitas(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*0.6
    for k in range(9):
        cx = x - w*0.45 + (k % 5)*w*0.22 + (k // 5)*w*0.1
        cy = y - t*0.78 - (k // 5)*t*0.14
        _circ(d, cx, cy, t*0.1, CREMA, max(2, g//2))
    _cont(d, [(x - w/2, y - t*0.78), (x + w/2, y - t*0.78), (x + w*0.38, y), (x - w*0.38, y)], BLANCO, g, rnd)
    for k in (-0.25, 0.08):
        d.polygon([(x + w*k, y - t*0.78), (x + w*(k + 0.17), y - t*0.78), (x + w*(k*0.8 + 0.14), y),
                   (x + w*k*0.8, y)], fill=ROJO)
    m._linea(d, [(x - w/2, y - t*0.78), (x + w/2, y - t*0.78), (x + w*0.38, y), (x - w*0.38, y),
                 (x - w/2, y - t*0.78)], g, rnd, color=TINTA, temblor=1.0)


def _botella(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*0.38
    _cont(d, [(x - w*0.25, y - t*0.88), (x + w*0.25, y - t*0.88), (x + w*0.25, y - t*0.8),
              (x + w/2, y - t*0.62), (x + w/2, y), (x - w/2, y), (x - w/2, y - t*0.62),
              (x - w*0.25, y - t*0.8)], (190, 228, 250), g, rnd)
    _caja(d, [x - w*0.28, y - t, x + w*0.28, y - t*0.88], AZUL, g)
    _caja(d, [x - w/2, y - t*0.45, x + w/2, y - t*0.25], (60, 150, 235), max(2, g//2))


def _zanahoria(d, x, y, t, rnd, g, tinta=TINTA):
    for a in (-0.3, 0, 0.3):
        m._linea(d, [(x, y - t*0.78), (x + math.sin(a)*t*0.25, y - t*0.78 - math.cos(a)*t*0.25)],
                 int(g*1.6), rnd, color=VERDE)
    _cont(d, [(x - t*0.18, y - t*0.8), (x + t*0.18, y - t*0.8), (x + t*0.02, y), (x - t*0.02, y)],
          NARANJA, g, rnd)
    for k in (0.6, 0.4, 0.25):
        d.line([(x - t*0.12*k*1.5, y - t*k), (x - t*0.02, y - t*k)], fill=(200, 100, 20), width=max(2, g//2))


def _pan(d, x, y, t, rnd, g, tinta=TINTA):
    cy = y - t*0.3
    _ov(d, [x - t*0.7, cy - t*0.3, x + t*0.7, cy + t*0.3], (225, 165, 85), g)
    for k in (-0.35, 0, 0.35):
        d.arc([x + t*k - t*0.15, cy - t*0.25, x + t*k + t*0.15, cy + t*0.05], 200, 340, fill=(160, 100, 40),
              width=g)


def _tarta(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*1.0
    _caja(d, [x - w/2, y - t*0.32, x + w/2, y], (240, 210, 160), g)
    _caja(d, [x - w*0.4, y - t*0.62, x + w*0.4, y - t*0.32], (240, 210, 160), g)
    for y0, ww in ((0.32, 0.5), (0.62, 0.4)):
        pts = [(x - w*ww, y - t*y0 - t*0.03)] + [(x - w*ww + i*w*ww/5, y - t*y0 + (0.08 if i % 2 else 0.02)*t)
                                                 for i in range(11)] + [(x + w*ww, y - t*y0 - t*0.03)]
        d.polygon(pts, fill=(250, 160, 190))
        _raya(d, pts, max(2, g//2), rnd)
    _caja(d, [x - t*0.03, y - t*0.85, x + t*0.03, y - t*0.62], (120, 190, 240), max(2, g//2))
    _gota_de(NARANJA)(d, x, y - t*0.86, t*0.15, rnd, max(2, g//2))


def _lata(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*0.45
    _caja(d, [x - w/2, y - t*0.92, x + w/2, y - t*0.04], ROJO, g)
    _ov(d, [x - w/2, y - t, x + w/2, y - t*0.86], GRIS, g)
    _ov(d, [x - w/2, y - t*0.1, x + w/2, y], GRIS, g)
    d.rectangle([x - w/2 + g, y - t*0.9, x + w/2 - g, y - t*0.06], fill=ROJO)
    pts = [(x - w/2 + g + i*(w - 2*g)/12, y - t*0.5 + t*0.07*math.sin(i*0.6)) for i in range(13)]
    d.line(pts, fill=BLANCO, width=int(g*1.4), joint="curve")


def _caramelo(d, x, y, t, rnd, g, tinta=TINTA):
    cy, r = y - t*0.3, t*0.24
    for lado in (-1, 1):
        _cont(d, [(x + lado*r*0.8, cy), (x + lado*r*2.0, cy - r*0.8), (x + lado*r*2.0, cy + r*0.8)],
              (250, 160, 190), g, rnd)
    _circ(d, x, cy, r, (250, 120, 170), g)
    d.arc([x - r*0.6, cy - r*0.6, x + r*0.6, cy + r*0.6], 0, 300, fill=BLANCO, width=max(2, g//2))


def _sandia(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*1.3
    cy = y - w/2
    d.chord([x - w/2, cy - w/2, x + w/2, cy + w/2], 0, 180, fill=VERDE, outline=TINTA, width=g)
    d.chord([x - w*0.43, cy - w*0.43, x + w*0.43, cy + w*0.43], 0, 180, fill=(240, 80, 90))
    d.line([(x - w/2, cy), (x + w/2, cy)], fill=TINTA, width=g)
    for cx, dy in ((-0.2, 0.08), (0, 0.22), (0.2, 0.08), (-0.08, 0.34), (0.1, 0.34)):
        d.ellipse([x + w*cx - w*0.015, cy + w*dy - w*0.025, x + w*cx + w*0.015, cy + w*dy + w*0.025], fill=TINTA)


# ---- La naturaleza, el tiempo y el espacio ---------------------------------

def _rayo(d, x, y, t, rnd, g, tinta=TINTA):
    _cont(d, [(x + t*0.1, y - t), (x - t*0.3, y - t*0.42), (x - t*0.02, y - t*0.42), (x - t*0.15, y),
              (x + t*0.32, y - t*0.6), (x + t*0.04, y - t*0.6), (x + t*0.22, y - t)], AMARILLO, g, rnd)


def _lluvia(d, x, y, t, rnd, g, tinta=TINTA):
    cy = y - t*0.68
    _nube_rellena(d, [(x - t*0.3, cy + t*0.05, t*0.2), (x, cy - t*0.08, t*0.28), (x + t*0.3, cy + t*0.05, t*0.2)],
                  (200, 205, 215), g)
    for k in range(4):
        px = x - t*0.3 + k*t*0.2
        d.line([(px, y - t*0.36 + (k % 2)*t*0.1), (px - t*0.05, y - t*0.2 + (k % 2)*t*0.1)], fill=AZUL,
               width=int(g*1.2))


def _arcoiris(d, x, y, t, rnd, g, tinta=TINTA):
    r = t*0.9
    for k, color in enumerate((ROJO, NARANJA, AMARILLO, VERDE, AZUL, MORADO)):
        rr = r - k*t*0.07
        d.arc([x - rr, y - t*0.15 - rr, x + rr, y - t*0.15 + rr], 180, 360, fill=color, width=int(t*0.075))
    for lado in (-1, 1):
        cx = x + lado*r*0.82
        _nube_rellena(d, [(cx - t*0.13, y - t*0.12, t*0.12), (cx + t*0.1, y - t*0.15, t*0.15),
                          (cx + t*0.0, y - t*0.25, t*0.13)], BLANCO, g)


def _volcan(d, x, y, t, rnd, g, tinta=TINTA):
    for k, (cx, cy, r) in enumerate(((0.05, 0.92, 0.1), (-0.08, 1.02, 0.12), (0.12, 1.08, 0.09))):
        _circ(d, x + t*cx, y - t*cy, t*r, GRIS, max(2, g//2))
    _cont(d, [(x - t*0.7, y), (x - t*0.15, y - t*0.75), (x + t*0.15, y - t*0.75), (x + t*0.7, y)],
          (150, 95, 60), g, rnd)
    _cont(d, [(x - t*0.15, y - t*0.75), (x + t*0.15, y - t*0.75), (x + t*0.18, y - t*0.6), (x + t*0.06, y - t*0.5),
              (x + t*0.02, y - t*0.62), (x - t*0.08, y - t*0.42), (x - t*0.12, y - t*0.6), (x - t*0.2, y - t*0.65)],
          NARANJA, g, rnd)


def _ola(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*1.3
    cresta = [(x - w/2, y - t*0.35)] + _arco(x + t*0.05, y - t*0.55, t*0.4, t*0.38, 160, 360, 20) + \
        _arco(x + t*0.3, y - t*0.6, t*0.16, t*0.14, 0, 160, 10) + [(x + w/2, y - t*0.3)]
    _cont(d, cresta + [(x + w/2, y), (x - w/2, y)], (60, 150, 235), g, rnd)
    for k in range(3):
        d.arc([x - w*0.35 + k*t*0.25, y - t*0.25, x - w*0.2 + k*t*0.25, y - t*0.12], 180, 360, fill=BLANCO,
              width=max(2, g//2))


def _tierra(d, x, y, t, rnd, g, tinta=TINTA):
    cy, r = y - t*0.5, t*0.48
    _circ(d, x, cy, r, (60, 150, 235), g)
    for pts in (((-0.6, -0.4), (-0.2, -0.6), (0.0, -0.3), (-0.2, 0.0), (-0.1, 0.3), (-0.4, 0.4), (-0.7, 0.0)),
                ((0.2, -0.1), (0.55, -0.35), (0.7, 0.1), (0.5, 0.5), (0.25, 0.4))):
        d.polygon([(x + r*a, cy + r*b) for a, b in pts], fill=VERDE, outline=TINTA)
    d.ellipse([x - r, cy - r, x + r, cy + r], outline=TINTA, width=g)


def _estrella(d, x, y, t, rnd, g, tinta=TINTA):
    cy, r = y - t*0.5, t*0.5
    pts = [(x + (r if i % 2 == 0 else r*0.42)*math.cos(math.radians(-90 + i*36)),
            cy + (r if i % 2 == 0 else r*0.42)*math.sin(math.radians(-90 + i*36))) for i in range(10)]
    _cont(d, pts, AMARILLO, g, rnd)


def _cohete(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*0.28
    _gota_de(NARANJA)(d, x, y + t*0.02, t*0.25, rnd, max(2, g//2))
    for lado in (-1, 1):
        _cont(d, [(x + lado*w/2, y - t*0.4), (x + lado*w*1.1, y - t*0.15), (x + lado*w/2, y - t*0.2)],
              ROJO, g, rnd)
    pts = [(x - w/2, y - t*0.2), (x - w/2, y - t*0.7)] + _arco(x, y - t*0.7, w/2, t*0.3, 180, 360, 16) + \
        [(x + w/2, y - t*0.2)]
    _cont(d, pts, BLANCO, g, rnd)
    _cont(d, _arco(x, y - t*0.7, w/2, t*0.3, 180, 360, 16)[4:-4], ROJO, max(2, g//2), rnd)
    _circ(d, x, y - t*0.55, w*0.25, (110, 190, 245), max(2, g//2))


def _montana(d, x, y, t, rnd, g, tinta=TINTA):
    _cont(d, [(x - t*0.75, y), (x - t*0.3, y - t*0.6), (x + t*0.1, y)], (130, 140, 160), g, rnd)
    _cont(d, [(x - t*0.3, y), (x + t*0.2, y - t), (x + t*0.75, y)], (110, 120, 140), g, rnd)
    _cont(d, [(x + t*0.2, y - t), (x + t*0.06, y - t*0.72), (x + t*0.14, y - t*0.78), (x + t*0.22, y - t*0.7),
              (x + t*0.3, y - t*0.78), (x + t*0.35, y - t*0.73)], BLANCO, max(2, g//2), rnd)


def _copo(d, x, y, t, rnd, g, tinta=TINTA):
    cy, r = y - t*0.5, t*0.48
    for k in range(6):
        a = k*math.pi/3
        fin = (x + math.cos(a)*r, cy + math.sin(a)*r)
        m._linea(d, [(x, cy), fin], g, rnd, color=(80, 160, 230), temblor=0.4)
        mitad = (x + math.cos(a)*r*0.6, cy + math.sin(a)*r*0.6)
        for s in (-0.6, 0.6):
            d.line([mitad, (mitad[0] + math.cos(a + s)*r*0.25, mitad[1] + math.sin(a + s)*r*0.25)],
                   fill=(80, 160, 230), width=max(2, int(g*0.7)))


def _tornado(d, x, y, t, rnd, g, tinta=TINTA):
    for k in range(7):
        s = k/6
        cx = x + t*0.08*math.sin(s*4)
        rx = t*(0.1 + 0.4*s)
        cy = y - t*0.08 - s*t*0.82
        d.arc([cx - rx, cy - t*0.07, cx + rx, cy + t*0.07], 0, 360, fill=(120, 125, 140), width=int(g*1.2))


def _avion(d, x, y, t, rnd, g, tinta=TINTA):
    cy, w = y - t*0.4, t*1.5
    _cont(d, [(x - w*0.38, cy), (x - w*0.48, cy - t*0.4), (x - w*0.36, cy - t*0.4), (x - w*0.22, cy)],
          ROJO, g, rnd)
    _caja(d, [x - w*0.45, cy - t*0.12, x + w*0.48, cy + t*0.14], BLANCO, g, t*0.13)
    _cont(d, [(x - w*0.05, cy), (x + w*0.12, cy), (x - w*0.05, cy + t*0.45), (x - w*0.17, cy + t*0.45)],
          AZUL, g, rnd)
    for k in range(5):
        _circ(d, x - w*0.2 + k*w*0.1, cy - t*0.01, t*0.035, (110, 190, 245), max(2, g//3))


def _coche(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*1.5
    _cont(d, [(x - w*0.24, y - t*0.42), (x - w*0.12, y - t*0.72), (x + w*0.18, y - t*0.72), (x + w*0.3, y - t*0.42)],
          (110, 190, 245), g, rnd)
    d.line([(x + w*0.03, y - t*0.72), (x + w*0.03, y - t*0.42)], fill=TINTA, width=g)
    _caja(d, [x - w/2, y - t*0.45, x + w/2, y - t*0.12], ROJO, g, t*0.1)
    d.ellipse([x + w*0.42, y - t*0.38, x + w*0.48, y - t*0.3], fill=AMARILLO, outline=TINTA)
    for cx in (-0.28, 0.28):
        _circ(d, x + w*cx, y - t*0.13, t*0.13, (50, 50, 55), g)
        _circ(d, x + w*cx, y - t*0.13, t*0.05, GRIS, max(2, g//3))


def _bicicleta(d, x, y, t, rnd, g, tinta=TINTA):
    r = t*0.3
    a, b = (x - t*0.42, y - r), (x + t*0.42, y - r)
    for c in (a, b):
        d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], outline=TINTA, width=g)
    pedal, silla, manillar = (x - t*0.05, y - r), (x - t*0.15, y - t*0.72), (x + t*0.28, y - t*0.8)
    for p, q in ((a, pedal), (pedal, silla), (silla, a), (silla, (x + t*0.25, y - t*0.65)),
                 ((x + t*0.25, y - t*0.65), pedal), ((x + t*0.25, y - t*0.65), b), ((x + t*0.25, y - t*0.65), manillar)):
        d.line([p, q], fill=(30, 160, 150), width=int(g*1.2))
    d.line([(silla[0] - t*0.1, silla[1]), (silla[0] + t*0.08, silla[1])], fill=TINTA, width=int(g*1.6))
    d.line([manillar, (manillar[0] - t*0.1, manillar[1])], fill=TINTA, width=int(g*1.4))


# ---- Los animales -----------------------------------------------------------

def _gato(d, x, y, t, rnd, g, tinta=TINTA):
    c = (245, 160, 70)
    m._linea(d, [(x + t*0.2, y - t*0.05), (x + t*0.45, y - t*0.1), (x + t*0.5, y - t*0.4)], int(g*2.6), rnd)
    m._linea(d, [(x + t*0.2, y - t*0.05), (x + t*0.45, y - t*0.1), (x + t*0.5, y - t*0.4)], int(g*1.4), rnd,
             color=c)
    _ov(d, [x - t*0.28, y - t*0.6, x + t*0.28, y], c, g)
    cy = y - t*0.68
    for lado in (-1, 1):
        _cont(d, [(x + lado*t*0.24, cy - t*0.05), (x + lado*t*0.24, cy - t*0.32), (x + lado*t*0.05, cy - t*0.2)],
              c, g, rnd)
    _circ(d, x, cy, t*0.25, c, g)
    for lado in (-1, 1):
        _ojo(d, x + lado*t*0.09, cy - t*0.03, t*0.04)
        for k in (-1, 1):
            d.line([(x + lado*t*0.12, cy + t*0.08), (x + lado*t*0.35, cy + t*0.08 + k*t*0.05)], fill=TINTA,
                   width=max(2, g//3))
    d.polygon([(x - t*0.03, cy + t*0.05), (x + t*0.03, cy + t*0.05), (x, cy + t*0.09)], fill=ROSA)


def _pez(d, x, y, t, rnd, g, tinta=TINTA):
    cy, c = y - t*0.4, NARANJA
    _cont(d, [(x + t*0.3, cy), (x + t*0.65, cy - t*0.28), (x + t*0.6, cy), (x + t*0.65, cy + t*0.28)], c, g, rnd)
    _ov(d, [x - t*0.55, cy - t*0.32, x + t*0.4, cy + t*0.32], c, g)
    _cont(d, [(x - t*0.1, cy - t*0.3), (x + t*0.05, cy - t*0.5), (x + t*0.2, cy - t*0.28)], c, g, rnd)
    d.arc([x - t*0.1, cy - t*0.25, x + t*0.25, cy + t*0.25], 120, 240, fill=(200, 100, 20), width=max(2, g//2))
    _ojo(d, x - t*0.32, cy - t*0.06, t*0.06)


def _pajaro(d, x, y, t, rnd, g, tinta=TINTA):
    cy, r = y - t*0.48, t*0.36
    for dx in (-0.08, 0.08):
        _raya(d, [(x + t*dx, cy + r*0.9), (x + t*dx, y)], max(2, g//2), rnd, color=NARANJA)
    _cont(d, [(x - r*0.9, cy), (x - r*1.6, cy - r*0.4), (x - r*1.5, cy + r*0.2)], AZUL, g, rnd)
    _circ(d, x, cy, r, (80, 160, 235), g)
    _cont(d, [(x + r*0.9, cy - r*0.2), (x + r*1.4, cy), (x + r*0.9, cy + r*0.15)], NARANJA, g, rnd)
    d.chord([x - r*0.6, cy - r*0.1, x + r*0.3, cy + r*0.6], 0, 180, fill=AZUL, outline=TINTA, width=max(2, g//2))
    _ojo(d, x + r*0.45, cy - r*0.3, r*0.13)


def _mosquito(d, x, y, t, rnd, g, tinta=TINTA):
    cy = y - t*0.5
    for k in range(3):
        a = (x - t*0.1 + k*t*0.1, cy + t*0.05)
        _raya(d, [a, (a[0] - t*0.15 + k*t*0.12, cy + t*0.25), (a[0] - t*0.2 + k*t*0.2, y)], max(2, g//2), rnd)
    for k, a in enumerate((-110, -70)):
        _ov(d, [x - t*0.05 + k*t*0.1 - t*0.1, cy - t*0.5, x - t*0.05 + k*t*0.1 + t*0.12, cy - t*0.08],
            (220, 240, 255), max(2, g//2))
    _ov(d, [x - t*0.55, cy - t*0.07, x + t*0.05, cy + t*0.07], (120, 100, 90), g)
    _circ(d, x + t*0.13, cy - t*0.03, t*0.09, (120, 100, 90), g)
    d.line([(x + t*0.2, cy), (x + t*0.55, cy + t*0.12)], fill=TINTA, width=max(2, g//2))
    _ojo(d, x + t*0.15, cy - t*0.06, t*0.035)


def _abeja(d, x, y, t, rnd, g, tinta=TINTA):
    cy = y - t*0.45
    for dx in (-0.12, 0.08):
        _ov(d, [x + t*dx - t*0.14, cy - t*0.55, x + t*dx + t*0.14, cy - t*0.15], (220, 240, 255), max(2, g//2))
    d.polygon([(x - t*0.45, cy), (x - t*0.62, cy - t*0.04), (x - t*0.45, cy + t*0.08)], fill=TINTA)
    _ov(d, [x - t*0.5, cy - t*0.25, x + t*0.35, cy + t*0.25], AMARILLO, g)
    for k in (-0.22, 0.02):
        d.rectangle([x + t*k, cy - t*0.22, x + t*k + t*0.1, cy + t*0.22], fill=TINTA)
    d.ellipse([x - t*0.5, cy - t*0.25, x + t*0.35, cy + t*0.25], outline=TINTA, width=g)
    _ojo(d, x + t*0.2, cy - t*0.05, t*0.05)
    for lado in (-1, 1):
        _raya(d, [(x + t*0.25, cy - t*0.2), (x + t*0.3 + lado*t*0.04, cy - t*0.38)], max(2, g//2), rnd)


def _arana(d, x, y, t, rnd, g, tinta=TINTA):
    cy, r = y - t*0.35, t*0.22
    for lado in (-1, 1):
        for k in range(4):
            a = math.radians(-50 + k*30)
            codo = (x + lado*(r + t*0.22)*math.cos(a), cy + (r + t*0.22)*math.sin(a) - t*0.18)
            pie = (x + lado*(r + t*0.42)*math.cos(a*0.6), y)
            _raya(d, [(x, cy), codo, pie], g, rnd)
    _circ(d, x, cy, r, (60, 50, 70), g)
    _circ(d, x, cy - r*1.1, r*0.6, (60, 50, 70), g)
    for lado in (-1, 1):
        d.ellipse([x + lado*r*0.25 - r*0.15, cy - r*1.3, x + lado*r*0.25 + r*0.15, cy - r*1.0], fill=BLANCO)


def _serpiente(d, x, y, t, rnd, g, tinta=TINTA):
    pts = [(x - t*0.65 + i*t*0.06, y - t*0.15 - t*0.15*math.sin(i*0.55)) for i in range(18)]
    pts += [(pts[-1][0] + t*0.05, pts[-1][1] - t*0.15), (pts[-1][0] + t*0.07, pts[-1][1] - t*0.35)]
    d.line(pts, fill=TINTA, width=int(t*0.17 + 2*g), joint="curve")
    d.line(pts, fill=VERDE, width=int(t*0.17), joint="curve")
    for p in pts[2:-2:3]:
        d.ellipse([p[0] - t*0.025, p[1] - t*0.025, p[0] + t*0.025, p[1] + t*0.025], fill=AMARILLO)
    cab = pts[-1]
    d.line([(cab[0] + t*0.1, cab[1]), (cab[0] + t*0.2, cab[1] - t*0.03), (cab[0] + t*0.2, cab[1] + t*0.03)],
           fill=ROJO, width=max(2, g//2))
    _ov(d, [cab[0] - t*0.12, cab[1] - t*0.12, cab[0] + t*0.15, cab[1] + t*0.1], VERDE, g)
    _ojo(d, cab[0] + t*0.03, cab[1] - t*0.04, t*0.035)


def _vaca(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*1.2
    for px in (-0.42, -0.25, 0.22, 0.38):
        d.line([(x + w*px*0.9, y - t*0.35), (x + w*px*0.9, y)], fill=TINTA, width=int(g*2.2))
    m._linea(d, [(x - w*0.45, y - t*0.65), (x - w*0.55, y - t*0.35)], g, rnd)
    _caja(d, [x - w*0.45, y - t*0.75, x + w*0.35, y - t*0.3], BLANCO, g, t*0.15)
    for cx, cy, r in ((-0.25, 0.6, 0.1), (0.05, 0.45, 0.12), (0.2, 0.62, 0.07)):
        d.ellipse([x + w*cx - t*r, y - t*cy - t*r*0.8, x + w*cx + t*r, y - t*cy + t*r*0.8], fill=TINTA)
    _ov(d, [x + w*0.25, y - t*0.95, x + w*0.55, y - t*0.55], BLANCO, g)
    _ov(d, [x + w*0.3, y - t*0.7, x + w*0.62, y - t*0.5], (250, 180, 190), g)
    for k in (0.4, 0.5):
        d.ellipse([x + w*k, y - t*0.63, x + w*k + t*0.04, y - t*0.58], fill=TINTA)
    _cont(d, [(x + w*0.3, y - t*0.92), (x + w*0.26, y - t*1.02), (x + w*0.35, y - t*0.93)], CREMA,
          max(2, g//2), rnd)
    _ojo(d, x + w*0.42, y - t*0.8, t*0.035)


def _tiburon(d, x, y, t, rnd, g, tinta=TINTA):
    cy, w = y - t*0.35, t*1.5
    c = (130, 150, 175)
    _cont(d, [(x + w*0.3, cy), (x + w*0.5, cy - t*0.35), (x + w*0.44, cy), (x + w*0.5, cy + t*0.25)], c, g, rnd)
    _cont(d, [(x - w*0.05, cy - t*0.15), (x + w*0.05, cy - t*0.55), (x + w*0.15, cy - t*0.15)], c, g, rnd)
    cuerpo = [(x - w*0.5, cy + t*0.02)] + _arco(x - w*0.05, cy, w*0.4, t*0.2, 180, 360, 18) + \
        [(x + w*0.35, cy)] + _arco(x - w*0.05, cy, w*0.4, t*0.18, 0, 180, 18)
    _cont(d, cuerpo, c, g, rnd)
    d.chord([x - w*0.45, cy - t*0.05, x + w*0.3, cy + t*0.2], 0, 180, fill=BLANCO)
    for k in range(3):
        d.arc([x - w*0.22 + k*t*0.06, cy - t*0.08, x - w*0.15 + k*t*0.06, cy + t*0.08], 270, 90, fill=TINTA,
              width=max(2, g//2))
    _ojo(d, x - w*0.33, cy - t*0.05, t*0.04)
    d.line([(x - w*0.46, cy + t*0.08), (x - w*0.35, cy + t*0.08)], fill=TINTA, width=max(2, g//2))


# ---- Los iconos de explicar --------------------------------------------------

def _reloj_arena(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*0.5
    _cont(d, [(x - w*0.4, y - t*0.9), (x + w*0.4, y - t*0.9), (x + w*0.05, y - t*0.5), (x + w*0.4, y - t*0.1),
              (x - w*0.4, y - t*0.1), (x - w*0.05, y - t*0.5)], (220, 240, 252), g, rnd)
    d.polygon([(x - w*0.22, y - t*0.72), (x + w*0.22, y - t*0.72), (x, y - t*0.53)], fill=AMARILLO)
    d.polygon([(x - w*0.36, y - t*0.12), (x + w*0.36, y - t*0.12), (x, y - t*0.32)], fill=AMARILLO)
    d.line([(x, y - t*0.5), (x, y - t*0.3)], fill=AMARILLO, width=max(2, g//2))
    for yy in (y - t, y - t*0.1):
        _caja(d, [x - w/2, yy, x + w/2, yy + t*0.1], MARRON, g, t*0.03)


def _grafico(sube):
    def dibujo(d, x, y, t, rnd, g, tinta=TINTA):
        w = t*1.2
        alturas = (0.25, 0.42, 0.6, 0.82) if sube else (0.82, 0.6, 0.42, 0.25)
        colores = (AZUL, VERDE, AMARILLO, ROJO)
        for k, (h, c) in enumerate(zip(alturas, colores)):
            x0 = x - w*0.4 + k*w*0.22
            _caja(d, [x0, y - t*h, x0 + w*0.16, y], c, g)
        _raya(d, [(x - w*0.48, y - t), (x - w*0.48, y), (x + w*0.5, y)], g, rnd)
        p0, p1 = ((x - w*0.4, y - t*0.45), (x + w*0.4, y - t*1.0)) if sube else \
            ((x - w*0.4, y - t*1.0), (x + w*0.4, y - t*0.45))
        m._linea(d, [p0, p1], int(g*1.6), rnd, color=VERDE if sube else ROJO)
        a = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
        for s in (2.5, -2.5):
            d.line([p1, (p1[0] + math.cos(a + s)*t*0.14, p1[1] + math.sin(a + s)*t*0.14)],
                   fill=VERDE if sube else ROJO, width=int(g*1.6))
    return dibujo


def _lupa(d, x, y, t, rnd, g, tinta=TINTA):
    cx, cy, r = x - t*0.12, y - t*0.62, t*0.3
    m._linea(d, [(cx + r*0.7, cy + r*0.7), (x + t*0.4, y)], int(g*2.8), rnd)
    m._linea(d, [(cx + r*0.75, cy + r*0.75), (x + t*0.38, y - t*0.02)], int(g*1.5), rnd, color=MARRON)
    _circ(d, cx, cy, r, (200, 235, 250), int(g*1.3))
    d.arc([cx - r*0.65, cy - r*0.65, cx + r*0.65, cy + r*0.65], 190, 260, fill=BLANCO, width=g)


def _nota(d, x, y, t, rnd, g, tinta=TINTA):
    for cx in (-0.25, 0.25):
        d.ellipse([x + t*cx - t*0.18, y - t*0.28, x + t*cx + t*0.08, y - t*0.05], fill=TINTA)
        d.line([(x + t*cx + t*0.06, y - t*0.18), (x + t*cx + t*0.06, y - t*0.9 + (0.1 if cx > 0 else 0)*t)],
               fill=TINTA, width=g)
    d.polygon([(x - t*0.19, y - t*0.9), (x + t*0.31, y - t*0.8), (x + t*0.31, y - t*0.68), (x - t*0.19, y - t*0.78)],
              fill=TINTA)


def _bateria(llena):
    def dibujo(d, x, y, t, rnd, g, tinta=TINTA):
        cy, w, h = y - t*0.3, t*1.1, t*0.5
        _caja(d, [x + w/2, cy - h*0.2, x + w/2 + t*0.08, cy + h*0.2], GRIS_OSCURO, g)
        _caja(d, [x - w/2, cy - h/2, x + w/2, cy + h/2], BLANCO, g, t*0.06)
        n, c = (4, VERDE) if llena else (1, ROJO)
        for k in range(n):
            x0 = x - w/2 + g*2 + k*(w - g*4)/4
            d.rectangle([x0 + g, cy - h/2 + g*2, x0 + (w - g*4)/4 - g, cy + h/2 - g*2], fill=c)
    return dibujo


def _candado(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*0.7
    d.arc([x - w*0.32, y - t, x + w*0.32, y - t*0.35], 180, 360, fill=TINTA, width=int(t*0.12) + 2*g)
    d.arc([x - w*0.32 + g, y - t + g, x + w*0.32 - g, y - t*0.35 - g], 180, 360, fill=GRIS, width=int(t*0.12))
    _caja(d, [x - w/2, y - t*0.6, x + w/2, y], DORADO, g, t*0.06)
    d.ellipse([x - t*0.06, y - t*0.42, x + t*0.06, y - t*0.3], fill=TINTA)
    d.polygon([(x - t*0.03, y - t*0.36), (x + t*0.03, y - t*0.36), (x + t*0.05, y - t*0.15), (x - t*0.05, y - t*0.15)],
              fill=TINTA)


def _iman(d, x, y, t, rnd, g, tinta=TINTA):
    cy, r, grosor = y - t*0.62, t*0.38, t*0.2
    pts = _arco(x, cy, r, r, 180, 360, 20) + [(x + r, y - t*0.05), (x + r - grosor, y - t*0.05)] + \
        _arco(x, cy, r - grosor, r - grosor, 360, 180, 20) + [(x - r + grosor, y - t*0.05), (x - r, y - t*0.05)]
    _cont(d, pts, ROJO, g, rnd)
    for lado in (-1, 1):
        x0, x1 = sorted((x + lado*r, x + lado*(r - grosor)))
        _caja(d, [x0, y - t*0.25, x1, y - t*0.05], GRIS, g)


def _regalo(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*0.8
    for lado in (-1, 1):
        _ov(d, [x + lado*t*0.2 - t*0.16, y - t, x + lado*t*0.2 + t*0.16, y - t*0.8], AMARILLO, g)
    _caja(d, [x - w/2, y - t*0.65, x + w/2, y], ROJO, g)
    _caja(d, [x - w*0.55, y - t*0.82, x + w*0.55, y - t*0.62], (240, 70, 70), g)
    d.rectangle([x - t*0.06, y - t*0.82 + g, x + t*0.06, y - g], fill=AMARILLO)
    d.line([(x - t*0.06, y - t*0.82), (x - t*0.06, y)], fill=TINTA, width=max(2, g//2))
    d.line([(x + t*0.06, y - t*0.82), (x + t*0.06, y)], fill=TINTA, width=max(2, g//2))


def _trofeo(d, x, y, t, rnd, g, tinta=TINTA):
    for lado in (-1, 1):
        d.arc([x + lado*t*0.3 - t*0.15, y - t*0.95, x + lado*t*0.3 + t*0.15, y - t*0.6],
              270 if lado > 0 else 90, 90 if lado > 0 else 270, fill=TINTA, width=int(g*1.4))
    _cont(d, [(x - t*0.32, y - t), (x + t*0.32, y - t)] + _arco(x, y - t, t*0.32, t*0.45, 0, 180, 16)[1:-1],
          DORADO, g, rnd)
    _caja(d, [x - t*0.05, y - t*0.55, x + t*0.05, y - t*0.25], DORADO, g)
    _caja(d, [x - t*0.25, y - t*0.25, x + t*0.25, y], MARRON, g, t*0.03)
    _estrella(d, x, y - t*0.65, t*0.25, rnd, max(2, g//2))


def _dado(d, x, y, t, rnd, g, tinta=TINTA):
    a = t*0.7
    _cont(d, [(x - a/2, y - a), (x - a*0.2, y - t), (x + a*0.8, y - t), (x + a/2, y - a)], (235, 235, 240), g, rnd)
    _cont(d, [(x + a/2, y - a), (x + a*0.8, y - t), (x + a*0.8, y - t*0.3), (x + a/2, y)], (210, 210, 220), g, rnd)
    _caja(d, [x - a/2, y - a, x + a/2, y], BLANCO, g, t*0.04)
    for cx, cy in ((-0.25, -0.75), (0, -0.5), (0.25, -0.25)):
        d.ellipse([x + a*cx - a*0.08, y + a*cy - a*0.08, x + a*cx + a*0.08, y + a*cy + a*0.08], fill=ROJO)


def _altavoz(d, x, y, t, rnd, g, tinta=TINTA):
    cy = y - t*0.45
    _cont(d, [(x - t*0.5, cy - t*0.15), (x - t*0.3, cy - t*0.15), (x - t*0.05, cy - t*0.4), (x - t*0.05, cy + t*0.4),
              (x - t*0.3, cy + t*0.15), (x - t*0.5, cy + t*0.15)], GRIS_OSCURO, g, rnd)
    for k, r in enumerate((0.2, 0.35, 0.5)):
        d.arc([x - t*0.05 - t*r, cy - t*r, x - t*0.05 + t*r, cy + t*r], -45, 45, fill=AZUL, width=int(g*1.2))


def _atomo(d, x, y, t, rnd, g, tinta=TINTA):
    cy, rx, ry = y - t*0.5, t*0.5, t*0.18
    for k in range(3):
        a = k*math.pi/3
        pts = [(x + rx*math.cos(s)*math.cos(a) - ry*math.sin(s)*math.sin(a),
                cy + rx*math.cos(s)*math.sin(a) + ry*math.sin(s)*math.cos(a)) for s in
               [i*math.pi/24 for i in range(49)]]
        d.line(pts, fill=AZUL, width=g, joint="curve")
        e = pts[8 + k*12]
        _circ(d, e[0], e[1], t*0.05, AMARILLO, max(2, g//2))
    _circ(d, x, cy, t*0.1, ROJO, g)


def _diana(d, x, y, t, rnd, g, tinta=TINTA):
    cy = y - t*0.5
    for k, r in enumerate((0.48, 0.36, 0.24, 0.12)):
        _circ(d, x, cy, t*r, ROJO if k % 2 == 0 else BLANCO, g)
    m._linea(d, [(x, cy), (x + t*0.45, cy - t*0.35)], int(g*1.3), rnd, color=MARRON)
    _cont(d, [(x + t*0.4, cy - t*0.31), (x + t*0.5, cy - t*0.48), (x + t*0.55, cy - t*0.32)], AZUL,
          max(2, g//2), rnd)


def _balanza(d, x, y, t, rnd, g, tinta=TINTA):
    _caja(d, [x - t*0.25, y - t*0.06, x + t*0.25, y], DORADO, g)
    _raya(d, [(x, y - t*0.06), (x, y - t*0.85)], int(g*1.4), rnd)
    _raya(d, [(x - t*0.55, y - t*0.8), (x + t*0.55, y - t*0.8)], int(g*1.4), rnd)
    _circ(d, x, y - t*0.88, t*0.05, DORADO, max(2, g//2))
    for lado in (-1, 1):
        cx = x + lado*t*0.5
        for s in (-1, 1):
            d.line([(cx, y - t*0.8), (cx + s*t*0.17, y - t*0.42)], fill=TINTA, width=max(2, g//2))
        d.chord([cx - t*0.2, y - t*0.55, cx + t*0.2, y - t*0.3], 0, 180, fill=DORADO, outline=TINTA, width=g)


def _pesa(d, x, y, t, rnd, g, tinta=TINTA):
    cy = y - t*0.3
    _caja(d, [x - t*0.55, cy - t*0.05, x + t*0.55, cy + t*0.05], GRIS, g)
    for lado in (-1, 1):
        _caja(d, [x + lado*t*0.4 - t*0.08, cy - t*0.3, x + lado*t*0.4 + t*0.08, cy + t*0.3], GRIS_OSCURO, g, t*0.03)
        _caja(d, [x + lado*t*0.27 - t*0.06, cy - t*0.22, x + lado*t*0.27 + t*0.06, cy + t*0.22], (60, 60, 70), g,
              t*0.03)


def _robot(d, x, y, t, rnd, g, tinta=TINTA):
    c = (150, 180, 210)
    for lado in (-1, 1):
        _raya(d, [(x + lado*t*0.12, y - t*0.15), (x + lado*t*0.12, y)], int(g*1.6), rnd)
        _raya(d, [(x + lado*t*0.25, y - t*0.48), (x + lado*t*0.42, y - t*0.3)], int(g*1.6), rnd)
    _caja(d, [x - t*0.25, y - t*0.58, x + t*0.25, y - t*0.15], c, g, t*0.04)
    _circ(d, x, y - t*0.38, t*0.07, ROJO, max(2, g//2))
    _raya(d, [(x, y - t*0.9), (x, y - t*1.0)], g, rnd)
    _circ(d, x, y - t*1.0, t*0.04, AMARILLO, max(2, g//2))
    _caja(d, [x - t*0.2, y - t*0.9, x + t*0.2, y - t*0.6], c, g, t*0.05)
    for lado in (-1, 1):
        _circ(d, x + lado*t*0.08, y - t*0.78, t*0.045, (110, 220, 250), max(2, g//2))
    d.line([(x - t*0.08, y - t*0.67), (x + t*0.08, y - t*0.67)], fill=TINTA, width=max(2, g//2))


def _moneda(d, x, y, t, rnd, g, tinta=TINTA):
    cy, r = y - t*0.42, t*0.4
    _ov(d, [x - r, cy - r, x + r*0.85, cy + r], (200, 150, 30), g)
    _circ(d, x - r*0.08, cy, r*0.9, DORADO, g)
    d.ellipse([x - r*0.6, cy - r*0.52, x + r*0.44, cy + r*0.52], outline=(200, 150, 30), width=max(2, g//2))
    _brillo(d, x - r*0.08, cy, r*0.65, g)


# ---- Mas animales (ella: "habla de un camello o de un caballo y sale solo el
# monigote"). De perfil, mirando a la derecha, como el resto.

def _patas(d, x, y, xs, alto, g, color=TINTA):
    """Patas del color del animal, con su borde."""
    for px in xs:
        d.line([(x + px, y - alto), (x + px, y)], fill=TINTA, width=int(g*2.6))
        d.line([(x + px, y - alto), (x + px, y - g*0.7)], fill=color, width=max(2, int(g*1.2)))


def _camello(d, x, y, t, rnd, g, tinta=TINTA):
    c = (215, 170, 105)
    _patas(d, x, y, (-t*0.38, -t*0.24, t*0.12, t*0.26), t*0.4, g, c)
    m._linea(d, [(x - t*0.52, y - t*0.6), (x - t*0.6, y - t*0.42)], g, rnd)
    lomo = [(x - t*0.5, y - t*0.42), (x - t*0.5, y - t*0.62)] + _arco(x - t*0.26, y - t*0.62, t*0.2, t*0.24, 180, 360, 12) + \
        _arco(x + t*0.1, y - t*0.62, t*0.18, t*0.22, 180, 360, 12) + [(x + t*0.32, y - t*0.6), (x + t*0.34, y - t*0.42)]
    _cont(d, lomo, c, g, rnd)
    _cont(d, [(x + t*0.26, y - t*0.6), (x + t*0.42, y - t*0.95), (x + t*0.52, y - t*0.92), (x + t*0.38, y - t*0.55)],
          c, g, rnd)
    _ov(d, [x + t*0.38, y - t*1.02, x + t*0.66, y - t*0.88], c, g)
    _ojo(d, x + t*0.5, y - t*0.96, t*0.025)


def _elefante(d, x, y, t, rnd, g, tinta=TINTA):
    c = (165, 170, 185)
    _patas(d, x, y, (-t*0.42, -t*0.25, t*0.08, t*0.24), t*0.3, int(g*1.8), c)
    _ov(d, [x - t*0.6, y - t*0.85, x + t*0.35, y - t*0.25], c, g)
    m._linea(d, [(x + t*0.42, y - t*0.6), (x + t*0.6, y - t*0.35), (x + t*0.58, y - t*0.12)], int(g*3.2), rnd)
    m._linea(d, [(x + t*0.42, y - t*0.6), (x + t*0.6, y - t*0.35), (x + t*0.58, y - t*0.12)], int(g*1.8), rnd,
             color=c)
    _circ(d, x + t*0.36, y - t*0.72, t*0.2, c, g)
    _ov(d, [x + t*0.1, y - t*0.92, x + t*0.36, y - t*0.5], (190, 195, 210), g)
    _ojo(d, x + t*0.44, y - t*0.78, t*0.03)


def _cerdo(d, x, y, t, rnd, g, tinta=TINTA):
    c = (250, 175, 190)
    _patas(d, x, y, (-t*0.38, -t*0.22, t*0.1, t*0.26), t*0.22, int(g*1.3), c)
    d.arc([x - t*0.68, y - t*0.62, x - t*0.48, y - t*0.42], 0, 300, fill=TINTA, width=g)
    _ov(d, [x - t*0.55, y - t*0.7, x + t*0.4, y - t*0.18], c, g)
    _cont(d, [(x + t*0.22, y - t*0.66), (x + t*0.3, y - t*0.82), (x + t*0.36, y - t*0.62)], c, g, rnd)
    _ov(d, [x + t*0.34, y - t*0.5, x + t*0.5, y - t*0.32], (240, 140, 160), g)
    for k in (0.4, 0.45):
        d.ellipse([x + t*k - 3, y - t*0.43, x + t*k + 3, y - t*0.37], fill=TINTA)
    _ojo(d, x + t*0.26, y - t*0.52, t*0.03)


def _gallina(d, x, y, t, rnd, g, tinta=TINTA):
    for px in (-0.06, 0.08):
        _raya(d, [(x + t*px, y - t*0.25), (x + t*px, y)], g, rnd, color=NARANJA)
    _cont(d, [(x - t*0.3, y - t*0.48), (x - t*0.42, y - t*0.78), (x - t*0.18, y - t*0.6)], BLANCO, g, rnd)
    _ov(d, [x - t*0.34, y - t*0.68, x + t*0.28, y - t*0.24], BLANCO, g)
    d.arc([x - t*0.2, y - t*0.58, x + t*0.08, y - t*0.36], 20, 160, fill=TINTA, width=max(2, g//2))
    _circ(d, x + t*0.2, y - t*0.72, t*0.14, BLANCO, g)
    _cont(d, [(x + t*0.12, y - t*0.84), (x + t*0.16, y - t*0.95), (x + t*0.22, y - t*0.86), (x + t*0.28, y - t*0.95),
              (x + t*0.3, y - t*0.82)], ROJO, max(2, g//2), rnd)
    _cont(d, [(x + t*0.32, y - t*0.74), (x + t*0.44, y - t*0.7), (x + t*0.32, y - t*0.66)], AMARILLO, max(2, g//2), rnd)
    _ojo(d, x + t*0.24, y - t*0.75, t*0.025)


def _leon(d, x, y, t, rnd, g, tinta=TINTA):
    c = (240, 180, 70)
    _patas(d, x, y, (-t*0.4, -t*0.25, t*0.05, t*0.2), t*0.25, int(g*1.5), c)
    m._linea(d, [(x - t*0.48, y - t*0.5), (x - t*0.7, y - t*0.4), (x - t*0.72, y - t*0.55)], g, rnd)
    _ov(d, [x - t*0.52, y - t*0.62, x + t*0.25, y - t*0.22], c, g)
    pts = [(x + t*0.28 + t*(0.3 if k % 2 else 0.24)*math.cos(a), y - t*0.62 + t*(0.3 if k % 2 else 0.24)*math.sin(a))
           for k, a in enumerate([i*math.pi/10 for i in range(20)])]
    _cont(d, pts, (190, 110, 40), g, rnd)
    _circ(d, x + t*0.3, y - t*0.62, t*0.16, c, g)
    _ojo(d, x + t*0.36, y - t*0.66, t*0.025)
    d.polygon([(x + t*0.42, y - t*0.6), (x + t*0.46, y - t*0.6), (x + t*0.44, y - t*0.56)], fill=TINTA)


def _conejo(d, x, y, t, rnd, g, tinta=TINTA):
    c = (235, 235, 240)
    for dx in (-0.02, 0.1):
        _ov(d, [x + t*dx, y - t*1.0, x + t*dx + t*0.12, y - t*0.6], c, g)
    _ov(d, [x - t*0.4, y - t*0.5, x + t*0.15, y], c, g)
    _circ(d, x - t*0.42, y - t*0.22, t*0.08, BLANCO, g)
    _circ(d, x + t*0.1, y - t*0.55, t*0.17, c, g)
    _ojo(d, x + t*0.16, y - t*0.58, t*0.03)
    d.ellipse([x + t*0.24, y - t*0.53, x + t*0.28, y - t*0.49], fill=ROSA)


def _tortuga(d, x, y, t, rnd, g, tinta=TINTA):
    c = (120, 190, 90)
    _patas(d, x, y, (-t*0.35, t*0.25), t*0.15, int(g*1.8), c)
    _cont(d, [(x + t*0.38, y - t*0.12), (x + t*0.5, y - t*0.26), (x + t*0.58, y - t*0.18), (x + t*0.42, y - t*0.04)],
          c, g, rnd)
    _circ(d, x + t*0.56, y - t*0.26, t*0.11, c, g)
    _ojo(d, x + t*0.6, y - t*0.29, t*0.025)
    d.chord([x - t*0.5, y - t*0.65, x + t*0.45, y + t*0.05], 180, 360, fill=(70, 140, 70), outline=TINTA, width=g)
    for cx, cy in ((-0.24, 0.4), (0.18, 0.4), (-0.03, 0.54)):
        d.ellipse([x + t*cx - t*0.1, y - t*cy - t*0.07, x + t*cx + t*0.1, y - t*cy + t*0.07], outline=(40, 90, 40),
                  width=max(2, g//2))
    d.line([(x - t*0.5, y - t*0.3), (x + t*0.45, y - t*0.3)], fill=TINTA, width=g)


def _rana(d, x, y, t, rnd, g, tinta=TINTA):
    c = (110, 200, 90)
    for lado in (-1, 1):
        _ov(d, [x + lado*t*0.3 - t*0.18, y - t*0.12, x + lado*t*0.3 + t*0.18, y], c, g)
    _ov(d, [x - t*0.42, y - t*0.65, x + t*0.42, y - t*0.05], c, g)
    for lado in (-1, 1):
        _circ(d, x + lado*t*0.2, y - t*0.68, t*0.13, BLANCO, g)
        d.ellipse([x + lado*t*0.2 - t*0.05, y - t*0.72, x + lado*t*0.2 + t*0.05, y - t*0.62], fill=TINTA)
    d.arc([x - t*0.22, y - t*0.5, x + t*0.22, y - t*0.25], 20, 160, fill=TINTA, width=g)


def _oveja(d, x, y, t, rnd, g, tinta=TINTA):
    _patas(d, x, y, (-t*0.3, -t*0.15, t*0.1, t*0.25), t*0.3, int(g*1.2), (70, 70, 80))
    cy = y - t*0.55
    _nube_rellena(d, [(x - t*0.3, cy, t*0.2), (x - t*0.05, cy - t*0.12, t*0.22), (x + t*0.2, cy, t*0.2),
                      (x - t*0.05, cy + t*0.1, t*0.2)], (248, 248, 250), g)
    _ov(d, [x + t*0.3, y - t*0.78, x + t*0.55, y - t*0.5], (70, 70, 80), g)
    _ojo(d, x + t*0.46, y - t*0.68, t*0.03)


# ---- REHECHOS ("mejora todos los dibujos"): los que flojeaban en la hoja de
# todos, y los de España Contada que aqui desentonaban (arbol, sol, nube...).

def _arbol(d, x, y, t, rnd, g, tinta=TINTA):
    _cont(d, [(x - t*0.07, y), (x - t*0.05, y - t*0.5), (x + t*0.05, y - t*0.5), (x + t*0.08, y)], MARRON, g, rnd)
    copa = [(x - t*0.25, y - t*0.62, t*0.2), (x + t*0.22, y - t*0.6, t*0.2), (x, y - t*0.8, t*0.24),
            (x - t*0.14, y - t*0.48, t*0.17), (x + t*0.14, y - t*0.47, t*0.17)]
    _nube_rellena(d, copa, (120, 195, 95), g)
    for cx, cy in ((-0.1, 0.7), (0.15, 0.62), (0.02, 0.52)):
        d.arc([x + t*cx - t*0.06, y - t*cy - t*0.04, x + t*cx + t*0.06, y - t*cy + t*0.04], 200, 340,
              fill=(80, 150, 70), width=max(2, g//2))


def _sol(d, x, y, t, rnd, g, tinta=TINTA):
    cy, r = y - t*0.5, t*0.26
    for k in range(10):
        a = k*math.pi/5
        d.line([(x + math.cos(a)*r*1.3, cy + math.sin(a)*r*1.3), (x + math.cos(a)*r*1.8, cy + math.sin(a)*r*1.8)],
               fill=NARANJA, width=int(g*1.3))
    _circ(d, x, cy, r, AMARILLO, g)
    d.arc([x - r*0.45, cy - r*0.1, x + r*0.45, cy + r*0.55], 20, 160, fill=TINTA, width=max(2, g//2))
    for lado in (-1, 1):
        d.ellipse([x + lado*r*0.35 - r*0.07, cy - r*0.25, x + lado*r*0.35 + r*0.07, cy - r*0.1], fill=TINTA)


def _nube(d, x, y, t, rnd, g, tinta=TINTA):
    cy = y - t*0.35
    _nube_rellena(d, [(x - t*0.32, cy + t*0.06, t*0.2), (x, cy - t*0.08, t*0.28), (x + t*0.32, cy + t*0.06, t*0.2)],
                  BLANCO, g)
    d.rectangle([x - t*0.32, cy + t*0.06, x + t*0.32, cy + t*0.26 - g], fill=BLANCO)
    d.line([(x - t*0.32, cy + t*0.26), (x + t*0.32, cy + t*0.26)], fill=TINTA, width=g)


def _pelota(d, x, y, t, rnd, g, tinta=TINTA):
    cy, r = y - t*0.42, t*0.42
    _circ(d, x, cy, r, BLANCO, g)
    d.pieslice([x - r, cy - r, x + r, cy + r], 200, 340, fill=ROJO)
    d.pieslice([x - r, cy - r, x + r, cy + r], 20, 160, fill=AZUL)
    d.ellipse([x - r, cy - r, x + r, cy + r], outline=TINTA, width=g)
    _brillo(d, x - r*0.1, cy - r*0.1, r*0.7, g)


def _dinero(d, x, y, t, rnd, g, tinta=TINTA):
    cy = y - t*0.38
    _cont(d, _suave([(x - t*0.2, y - t*0.72), (x + t*0.2, y - t*0.72), (x + t*0.12, y - t*0.62),
                     (x + t*0.42, y - t*0.35), (x + t*0.38, y), (x - t*0.38, y), (x - t*0.42, y - t*0.35),
                     (x - t*0.12, y - t*0.62)]), (215, 180, 120), g, rnd)
    d.line([(x - t*0.14, y - t*0.63), (x + t*0.14, y - t*0.63)], fill=MARRON, width=int(g*1.4))
    d.text((x, cy + t*0.02), "$", fill=(60, 130, 60), anchor="mm", font=_fuente(int(t*0.42)))


def _estomago(d, x, y, t, rnd, g, tinta=TINTA):
    """El estomago de libro: una judia con su tubito (el esofago) arriba."""
    pts = _suave([(x - t*0.1, y - t*0.95), (x - t*0.02, y - t*0.95), (x - t*0.02, y - t*0.72), (x + t*0.15, y - t*0.75),
                  (x + t*0.36, y - t*0.6), (x + t*0.38, y - t*0.32), (x + t*0.18, y - t*0.12), (x - t*0.1, y - t*0.12),
                  (x - t*0.22, y - t*0.02), (x - t*0.32, y - t*0.1), (x - t*0.24, y - t*0.28), (x - t*0.04, y - t*0.36),
                  (x + t*0.12, y - t*0.48), (x - t*0.1, y - t*0.65)], 2)
    _cont(d, pts, (245, 150, 160), g, rnd)
    for k in range(3):
        d.arc([x + t*(0.0 + k*0.08), y - t*0.55, x + t*(0.18 + k*0.08), y - t*0.3], 200, 300,
              fill=(215, 100, 120), width=max(2, g//2))


def _mano(d, x, y, t, rnd, g, tinta=TINTA):
    """La mano abierta de frente, cinco dedos."""
    piel = CARNE
    for k, (dx, largo, ancho) in enumerate(((-0.24, 0.42, 0.075), (-0.1, 0.55, 0.08), (0.04, 0.6, 0.08),
                                            (0.17, 0.54, 0.075))):
        d.rounded_rectangle([x + t*dx - t*ancho, y - t*(0.4 + largo), x + t*dx + t*ancho, y - t*0.45],
                            radius=int(t*ancho), fill=piel, outline=TINTA, width=g)
    d.rounded_rectangle([x - t*0.32, y - t*0.6, x + t*0.27, y - t*0.05], radius=int(t*0.14), fill=piel,
                        outline=TINTA, width=g)
    for k, (dx, largo, ancho) in enumerate(((-0.24, 0.42, 0.075), (-0.1, 0.55, 0.08), (0.04, 0.6, 0.08),
                                            (0.17, 0.54, 0.075))):
        d.rectangle([x + t*dx - t*ancho + g, y - t*0.62, x + t*dx + t*ancho - g, y - t*0.5], fill=piel)
    pulgar = [(x + t*0.22, y - t*0.42), (x + t*0.42, y - t*0.6), (x + t*0.5, y - t*0.52), (x + t*0.3, y - t*0.25)]
    _cont(d, _suave(pulgar, 2), piel, g, rnd)
    d.arc([x - t*0.15, y - t*0.38, x + t*0.12, y - t*0.18], 200, 330, fill=(220, 160, 130), width=max(2, g//2))


def _nariz(d, x, y, t, rnd, g, tinta=TINTA):
    """La nariz de perfil, grande y redonda, de dibujo animado."""
    pts = _suave([(x - t*0.15, y - t*0.98), (x - t*0.02, y - t*0.95), (x + t*0.22, y - t*0.45), (x + t*0.36, y - t*0.3),
                  (x + t*0.34, y - t*0.12), (x + t*0.18, y - t*0.05), (x - t*0.02, y - t*0.12), (x - t*0.15, y - t*0.08),
                  (x - t*0.18, y)], 2) + [(x - t*0.3, y), (x - t*0.3, y - t*0.98)]
    _cont(d, pts, CARNE, g, rnd)
    d.ellipse([x + t*0.06, y - t*0.2, x + t*0.18, y - t*0.12], fill=(150, 90, 80))
    d.arc([x - t*0.02, y - t*0.38, x + t*0.25, y - t*0.12], 120, 250, fill=(220, 160, 130), width=max(2, g//2))


def _lengua(d, x, y, t, rnd, g, tinta=TINTA):
    """La boca abierta sacando la lengua."""
    w = t*0.8
    _ov(d, [x - w/2, y - t, x + w/2, y - t*0.45], (120, 30, 40), g)
    lengua = [(x - w*0.26, y - t*0.62)] + _arco(x, y - t*0.42, w*0.26, t*0.4, 180, 0, 24)[1:] + [(x + w*0.26, y - t*0.62)]
    lengua = [(x - w*0.26, y - t*0.62), (x - w*0.26, y - t*0.42)] + _arco(x, y - t*0.42, w*0.26, t*0.4, 180, 0, 24)[1:]
    _cont(d, lengua + [(x + w*0.26, y - t*0.62)], (240, 120, 140), g, rnd)
    d.line([(x, y - t*0.6), (x, y - t*0.25)], fill=(200, 80, 110), width=max(2, g//2))
    d.rectangle([x - w*0.3, y - t*0.98, x + w*0.3, y - t*0.9], fill=BLANCO)


def _frio(d, x, y, t, rnd, g, tinta=TINTA):
    """Frio: el termometro en lo mas bajo y un copo al lado."""
    w = t*0.16
    tx = x - t*0.18
    d.rounded_rectangle([tx - w/2, y - t, tx + w/2, y - t*0.18], radius=int(w/2), fill=BLANCO, outline=TINTA, width=g)
    _ov(d, [tx - w, y - t*0.3, tx + w, y], AZUL, g)
    d.rectangle([tx - w*0.22, y - t*0.36, tx + w*0.22, y - t*0.22], fill=AZUL)
    cx, cy, r = x + t*0.25, y - t*0.65, t*0.22
    for k in range(6):
        a = k*math.pi/3
        d.line([(cx, cy), (cx + math.cos(a)*r, cy + math.sin(a)*r)], fill=(80, 160, 230), width=g)


def _queso(d, x, y, t, rnd, g, tinta=TINTA):
    """La cuña de queso con sus agujeros."""
    q, q2 = (252, 210, 70), (255, 232, 130)
    _cont(d, [(x - t*0.55, y - t*0.38), (x + t*0.5, y - t*0.6), (x + t*0.5, y - t*0.42), (x - t*0.55, y - t*0.2)], q2,
          g, rnd)
    _cont(d, [(x - t*0.55, y - t*0.2), (x + t*0.5, y - t*0.42), (x + t*0.5, y), (x - t*0.55, y)], q, g, rnd)
    for cx, cy, r in ((-0.3, 0.12, 0.06), (0.05, 0.22, 0.07), (0.32, 0.12, 0.05), (0.2, 0.47, 0.04)):
        d.ellipse([x + t*cx - t*r, y - t*cy - t*r*0.8, x + t*cx + t*r, y - t*cy + t*r*0.8], fill=(225, 170, 40))


def _cama(d, x, y, t, rnd, g, tinta=TINTA):
    w = t*1.8
    d.rounded_rectangle([x - w/2, y - t*0.95, x - w/2 + t*0.1, y], radius=int(t*0.04), fill=MARRON, outline=TINTA,
                        width=g)
    d.rounded_rectangle([x + w/2 - t*0.1, y - t*0.6, x + w/2, y], radius=int(t*0.04), fill=MARRON, outline=TINTA,
                        width=g)
    _caja(d, [x - w/2 + t*0.08, y - t*0.42, x + w/2 - t*0.08, y - t*0.18], BLANCO, g, t*0.04)
    _ov(d, [x - w/2 + t*0.14, y - t*0.62, x - w/2 + t*0.6, y - t*0.38], BLANCO, g)
    _caja(d, [x - w/2 + t*0.5, y - t*0.5, x + w/2 - t*0.1, y - t*0.12], (110, 160, 230), g, t*0.06)
    for k in range(3):
        xx = x - w/2 + t*(0.75 + k*0.3)
        d.line([(xx, y - t*0.46), (xx, y - t*0.14)], fill=(150, 190, 240), width=max(2, g//2))


def _escaner(d, x, y, t, rnd, g, tinta=TINTA):
    """El escaner (resonancia): el aro gordo con la camilla entrando."""
    cx, cy, r = x + t*0.15, y - t*0.5, t*0.45
    _caja(d, [x - t*0.75, y - t*0.36, x + t*0.2, y - t*0.26], (190, 200, 215), g, t*0.03)
    _caja(d, [x - t*0.6, y - t*0.26, x - t*0.5, y], GRIS, g)
    _circ(d, cx, cy, r, (225, 230, 240), g)
    _circ(d, cx, cy, r*0.55, (60, 70, 90), g)
    d.arc([cx - r*0.8, cy - r*0.8, cx + r*0.8, cy + r*0.8], 200, 260, fill=(120, 200, 250), width=g)
    d.ellipse([cx + r*0.55, cy - r*0.75, cx + r*0.7, cy - r*0.6], fill=VERDE)
    _caja(d, [x - t*0.62, y - t*0.36, x + t*0.05, y - t*0.3], (190, 200, 215), max(2, g//2), t*0.02)


def _musculo(d, x, y, t, rnd, g, tinta=TINTA):
    """El brazo sacando bola, con el biceps bien redondo."""
    piel = CARNE
    brazo = _suave([(x - t*0.6, y - t*0.08), (x + t*0.22, y - t*0.08), (x + t*0.4, y - t*0.22), (x + t*0.42, y - t*0.62),
                    (x + t*0.24, y - t*0.66), (x + t*0.2, y - t*0.36), (x + t*0.05, y - t*0.5), (x - t*0.2, y - t*0.62),
                    (x - t*0.42, y - t*0.5), (x - t*0.6, y - t*0.44)], 2)
    _cont(d, brazo, piel, g, rnd)
    _circ(d, x + t*0.33, y - t*0.78, t*0.16, piel, g)
    d.arc([x - t*0.32, y - t*0.6, x + t*0.12, y - t*0.3], 200, 320, fill=(220, 160, 130), width=max(2, g//2))
    for k in range(3):
        a = math.radians(-150 + k*30)
        cx, cy = x - t*0.1, y - t*0.6
        d.line([(cx + math.cos(a)*t*0.15, cy + math.sin(a)*t*0.15), (cx + math.cos(a)*t*0.25, cy + math.sin(a)*t*0.25)],
               fill=AMARILLO, width=g)


def _microscopio(d, x, y, t, rnd, g, tinta=TINTA):
    azul = (90, 130, 200)
    _caja(d, [x - t*0.38, y - t*0.1, x + t*0.32, y], azul, g, t*0.04)
    _cont(d, _suave([(x + t*0.1, y - t*0.1), (x + t*0.26, y - t*0.1), (x + t*0.3, y - t*0.5), (x + t*0.15, y - t*0.78),
                     (x + t*0.04, y - t*0.7), (x + t*0.14, y - t*0.45)], 1), azul, g, rnd)
    _caja(d, [x - t*0.3, y - t*0.4, x + t*0.2, y - t*0.34], (60, 70, 90), g)
    a = math.radians(-70)
    dx, dy = math.cos(a), math.sin(a)
    px, py = -dy*t*0.08, dx*t*0.08
    base, punta = (x - t*0.06, y - t*0.46), (x - t*0.06 + dx*t*0.5, y - t*0.46 + dy*t*0.5)
    _cont(d, [(base[0] + px, base[1] + py), (base[0] - px, base[1] - py), (punta[0] - px, punta[1] - py),
              (punta[0] + px, punta[1] + py)], (220, 225, 235), g, rnd)
    _caja(d, [punta[0] - t*0.07, punta[1] - t*0.08, punta[0] + t*0.07, punta[1] + t*0.02], (60, 70, 90), g, t*0.02)
    _caja(d, [base[0] - t*0.05, base[1], base[0] + t*0.05, base[1] + t*0.05], (60, 70, 90), max(2, g//2))


def _suave(pts, vueltas=2):
    for _ in range(vueltas):
        nuevos = []
        for a, b in zip(pts, pts[1:] + pts[:1]):
            nuevos += [(a[0]*0.75 + b[0]*0.25, a[1]*0.75 + b[1]*0.25), (a[0]*0.25 + b[0]*0.75, a[1]*0.25 + b[1]*0.75)]
        pts = nuevos
    return pts


def _fuente(px):
    from PIL import ImageFont
    from pathlib import Path
    try:
        return ImageFont.truetype(str(Path(__file__).parent / "data" / "fuentes" / "ArchitectsDaughter.woff"), max(8, px))
    except OSError:
        return ImageFont.load_default()


MAS_OBJETOS = {
    # el cuerpo y la salud
    "diente": _diente, "hueso": _hueso, "nariz": _nariz, "oreja": _oreja, "lengua": _lengua,
    "sangre": _gota_de(ROJO), "musculo": _musculo, "jeringa": _jeringa, "tirita": _tirita,
    "mascarilla": _mascarilla, "microscopio": _microscopio, "adn": _adn, "celula": _celula,
    "neurona": _neurona,
    # la casa
    "nevera": _nevera, "microondas": _microondas, "inodoro": _inodoro, "ducha": _ducha,
    "ordenador": _ordenador, "enchufe": _enchufe, "espejo": _espejo, "almohada": _almohada,
    "sofa": _sofa, "tele": _tele, "lavadora": _lavadora, "grifo": _grifo, "llave": _llave,
    # la comida
    "manzana": _manzana, "platano": _platano, "pizza": _pizza, "huevo": _huevo, "queso": _queso,
    "chocolate": _chocolate, "guindilla": _guindilla, "limon": _limon, "sal": _sal,
    "helado": _helado, "palomitas": _palomitas, "botella": _botella, "zanahoria": _zanahoria,
    "pan": _pan, "tarta": _tarta, "lata": _lata, "caramelo": _caramelo, "sandia": _sandia,
    # la naturaleza, el tiempo y el espacio
    "rayo": _rayo, "lluvia": _lluvia, "arcoiris": _arcoiris, "volcan": _volcan, "ola": _ola,
    "tierra": _tierra, "estrella": _estrella, "cohete": _cohete, "montana": _montana,
    "copo": _copo, "tornado": _tornado,
    # los transportes
    "avion": _avion, "coche": _coche, "bicicleta": _bicicleta,
    # los animales
    "gato": _gato, "pez": _pez, "pajaro": _pajaro, "mosquito": _mosquito, "abeja": _abeja,
    "arana": _arana, "serpiente": _serpiente, "vaca": _vaca, "tiburon": _tiburon,
    "camello": _camello, "elefante": _elefante, "cerdo": _cerdo, "gallina": _gallina, "leon": _leon,
    "conejo": _conejo, "tortuga": _tortuga, "rana": _rana, "oveja": _oveja,
    # los iconos de explicar
    "reloj_arena": _reloj_arena, "grafico_sube": _grafico(True), "grafico_baja": _grafico(False),
    "lupa": _lupa, "nota_musical": _nota, "bateria": _bateria(True), "bateria_baja": _bateria(False),
    "candado": _candado, "iman": _iman, "regalo": _regalo, "trofeo": _trofeo, "dado": _dado,
    "altavoz": _altavoz, "atomo": _atomo, "diana": _diana, "balanza": _balanza, "pesa": _pesa,
    "robot": _robot, "moneda": _moneda,
}
# Los rehechos ganan a los de antes (y a los de España Contada, solo aqui).
REHECHOS = {"arbol": _arbol, "sol": _sol, "nube": _nube, "pelota": _pelota, "dinero": _dinero,
            "estomago": _estomago, "mano": _mano, "nariz": _nariz, "lengua": _lengua, "frio": _frio,
            "queso": _queso, "cama": _cama, "escaner": _escaner, "musculo": _musculo,
            "microscopio": _microscopio}
