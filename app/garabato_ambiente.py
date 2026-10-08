"""EL AMBIENTE DEL FOLIO en Why Though: un fondo dibujado suave detras de lo
que pasa.

Ella: "sale una pantalla blanca y un camello... ponle una hierbita o yo que
se, algo asi, pintar un poco mas el lienzo". Asi que cada dibujo puede ir en
un sitio - el campo, el desierto, la playa, la ciudad, la casa... - pintado
con trazo fino y colores claros, en los bordes y en el suelo, para que lo
importante siga siendo lo de delante. Y debajo de cada monigote y de cada
cosa apoyada, su sombrita.

El fondo se pinta UNA vez por plano y se pone solo donde el fotograma es
papel (252, 252, 250): las cabezas y los rellenos blancos son (255, 255,
255), asi que nada del fondo se cuela por dentro de los dibujos.
"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw

from . import monigotes as m

PAPEL = (252, 252, 250)
TRAZO = (150, 150, 150)

AMBIENTES = ("campo", "desierto", "playa", "ciudad", "casa", "cocina", "laboratorio", "colegio",
             "hospital", "noche", "espacio", "cielo", "nada")

# El sitio que pega cuando el guion no dice ninguno.
_POR_COSAS = (
    ("desierto", {"camello", "serpiente", "calor"}),
    ("playa", {"pez", "tiburon", "ola", "pulpo"}),
    ("espacio", {"cohete", "tierra", "estrella", "atomo", "luna"}),
    ("campo", {"caballo", "vaca", "oveja", "cerdo", "gallina", "conejo", "perro", "gato", "tortuga",
               "rana", "leon", "elefante", "abeja", "mosquito", "pajaro", "arbol", "planta", "toro"}),
    ("laboratorio", {"microscopio", "adn", "celula", "bacteria", "virus", "neurona", "jeringa",
                     "escaner", "cerebro"}),
    ("cocina", {"nevera", "microondas", "pizza", "huevo", "hamburguesa", "taza", "queso", "sal",
                "cebolla", "tarta", "pan", "chocolate", "palomitas"}),
    ("casa", {"cama", "sofa", "tele", "almohada", "lavadora", "inodoro", "ducha", "ventilador",
              "despertador", "ordenador", "lampara"}),
)


def elige(visual: dict, cosas: list) -> str:
    pedido = str(visual.get("ambiente") or "").lower()
    if pedido in AMBIENTES:
        return pedido
    if visual.get("cifra") or not (visual.get("figuras") or cosas):
        return "nada"
    nombres = {c.get("que") for c in cosas}
    for ambiente, cuales in _POR_COSAS:
        if nombres & cuales:
            return ambiente
    return "nada"


def _linea(d, pts, g, rnd, color=TRAZO):
    m._linea(d, pts, g, rnd, color=color, temblor=0.6)


def _sol(d, w, h, g, rnd, x=0.88, y=0.15, r=0.06, color=(250, 215, 90)):
    cx, cy, rr = w*x, h*y, h*r
    d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=color, outline=(225, 175, 60), width=g)
    for k in range(10):
        a = k*math.pi/5
        _linea(d, [(cx + math.cos(a)*rr*1.3, cy + math.sin(a)*rr*1.3),
                   (cx + math.cos(a)*rr*1.65, cy + math.sin(a)*rr*1.65)], g, rnd, color=(235, 190, 70))


def _nube(d, w, h, g, x, y, r):
    piezas = [(w*x - h*r*0.9, h*y + h*r*0.15, h*r*0.7), (w*x, h*y - h*r*0.1, h*r),
              (w*x + h*r*0.95, h*y + h*r*0.15, h*r*0.75)]
    for cx, cy, rr in piezas:
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(255, 255, 255), outline=(200, 205, 215), width=g)
    for cx, cy, rr in piezas:
        d.ellipse([cx - rr + g, cy - rr + g, cx + rr - g, cy + rr - g], fill=(255, 255, 255))


def _matas(d, w, h, pies, g, rnd, n=9, color=(120, 185, 95)):
    for k in range(n):
        x = w*(0.04 + 0.92*k/(n - 1)) + rnd.uniform(-w*0.03, w*0.03)
        y = pies + rnd.uniform(-h*0.01, h*0.06)
        for a in (-0.5, 0, 0.45):
            _linea(d, [(x, y), (x + math.sin(a)*h*0.03, y - math.cos(a)*h*0.035)], g, rnd, color=color)


def _pajaros(d, w, h, g, rnd, sitios):
    for x, y in sitios:
        cx, cy, a = w*x, h*y, h*0.016
        _linea(d, [(cx - a, cy - a*0.5), (cx, cy), (cx + a, cy - a*0.5)], g, rnd, color=(130, 130, 140))


def _estrellas(d, w, h, g, rnd, n=14, color=(240, 200, 70)):
    for _ in range(n):
        x, y = rnd.uniform(0.03, 0.97)*w, rnd.uniform(0.04, 0.4)*h
        if 0.3*w < x < 0.7*w and y > 0.15*h:
            continue
        r = rnd.uniform(0.006, 0.012)*h
        d.line([(x - r, y), (x + r, y)], fill=color, width=g)
        d.line([(x, y - r), (x, y + r)], fill=color, width=g)


def _ventana(d, w, h, g, rnd, x0, y0, x1, y1, cielo=(215, 235, 250)):
    d.rectangle([w*x0, h*y0, w*x1, h*y1], fill=cielo, outline=TRAZO, width=g)
    d.line([(w*(x0 + x1)/2, h*y0), (w*(x0 + x1)/2, h*y1)], fill=TRAZO, width=g)
    d.line([(w*x0, h*(y0 + y1)/2), (w*x1, h*(y0 + y1)/2)], fill=TRAZO, width=g)


def _suelo_de(d, w, h, pies, color, linea=TRAZO, g=2, rnd=None):
    d.rectangle([0, pies - h*0.02, w, h], fill=color)
    if rnd is not None:
        _linea(d, [(0, pies - h*0.02), (w, pies - h*0.02)], g, rnd, color=linea)


def _pinta(d, ambiente, w, h, pies, g, rnd):
    if ambiente == "campo":
        colina = [(0, pies - h*0.12)] + [(w*i/20, pies - h*0.12 - h*0.03*math.sin(i*0.7)) for i in range(21)] + \
            [(w, h), (0, h)]
        d.polygon(colina, fill=(228, 242, 214))
        _linea(d, colina[1:22], g, rnd, color=(160, 205, 140))
        _matas(d, w, h, pies, g, rnd)
        for x in (0.07, 0.31, 0.66, 0.93):
            fx, fy = w*x, pies + h*0.07
            for k in range(5):
                a = k*2*math.pi/5
                d.ellipse([fx + math.cos(a)*h*0.01 - h*0.007, fy + math.sin(a)*h*0.01 - h*0.007,
                           fx + math.cos(a)*h*0.01 + h*0.007, fy + math.sin(a)*h*0.01 + h*0.007],
                          fill=(250, 190, 210))
            d.ellipse([fx - h*0.006, fy - h*0.006, fx + h*0.006, fy + h*0.006], fill=(250, 210, 80))
        _sol(d, w, h, g, rnd)
        _nube(d, w, h, g, 0.13, 0.13, 0.05)
        _pajaros(d, w, h, g, rnd, ((0.62, 0.1), (0.67, 0.13)))
    elif ambiente == "desierto":
        duna = [(0, pies - h*0.08)] + [(w*i/20, pies - h*0.08 - h*0.05*math.sin(i*0.45 + 1)) for i in range(21)] + \
            [(w, h), (0, h)]
        d.polygon(duna, fill=(247, 232, 190))
        _linea(d, duna[1:22], g, rnd, color=(220, 190, 130))
        cx, cy = w*0.05, pies + h*0.02
        verde = (140, 190, 110)
        d.rounded_rectangle([cx - h*0.022, cy - h*0.2, cx + h*0.022, cy], radius=int(h*0.02), fill=verde,
                            outline=(100, 150, 80), width=g)
        d.rounded_rectangle([cx + h*0.02, cy - h*0.13, cx + h*0.05, cy - h*0.11], radius=int(h*0.01), fill=verde)
        d.rounded_rectangle([cx + h*0.035, cy - h*0.17, cx + h*0.06, cy - h*0.11], radius=int(h*0.012), fill=verde,
                            outline=(100, 150, 80), width=g)
        _sol(d, w, h, g, rnd, r=0.075, color=(252, 200, 80))
        for k in range(3):
            y = h*(0.32 + k*0.04)
            pts = [(w*0.8 + i*w*0.012, y + h*0.006*math.sin(i)) for i in range(9)]
            _linea(d, pts, g, rnd, color=(240, 170, 110))
    elif ambiente == "playa":
        mar_alto, mar_bajo = pies - h*0.2, pies - h*0.05
        d.rectangle([0, mar_alto, w, mar_bajo], fill=(205, 230, 248))
        for k in range(3):
            y = mar_alto + (k + 0.5)*(mar_bajo - mar_alto)/3
            for j in range(6):
                x = w*(0.05 + j*0.18) + k*w*0.05
                d.arc([x, y - h*0.012, x + w*0.05, y + h*0.012], 200, 340, fill=(140, 190, 230), width=g)
        d.rectangle([0, mar_bajo, w, h], fill=(248, 236, 200))
        _linea(d, [(0, mar_bajo), (w, mar_bajo)], g, rnd, color=(215, 195, 140))
        _sol(d, w, h, g, rnd)
        _pajaros(d, w, h, g, rnd, ((0.2, 0.15), (0.25, 0.18), (0.72, 0.12)))
    elif ambiente == "ciudad":
        rng = random.Random(4)
        x = 0.0
        while x < w:
            ancho = rng.uniform(0.07, 0.12)*w
            alto = rng.uniform(0.18, 0.4)*h
            if 0.32*w < x + ancho/2 < 0.68*w:
                alto *= 0.6
            d.rectangle([x, pies - alto, x + ancho, pies], fill=(236, 237, 242), outline=(190, 192, 200), width=g)
            for yy in np.arange(pies - alto + h*0.03, pies - h*0.03, h*0.05):
                for xx in np.arange(x + ancho*0.18, x + ancho*0.8, ancho*0.3):
                    d.rectangle([xx, yy, xx + ancho*0.12, yy + h*0.02], fill=(250, 235, 170))
            x += ancho + w*0.01
        _suelo_de(d, w, h, pies + h*0.02, (232, 232, 235), g=g, rnd=rnd)
        _nube(d, w, h, g, 0.82, 0.1, 0.045)
    elif ambiente in ("casa", "cocina", "colegio", "hospital", "laboratorio"):
        suelo = {"casa": (240, 226, 206), "cocina": (232, 236, 240), "colegio": (238, 228, 210),
                 "hospital": (226, 238, 244), "laboratorio": (230, 236, 242)}[ambiente]
        _suelo_de(d, w, h, pies + h*0.02, suelo, g=g, rnd=rnd)
        if ambiente == "casa":
            _ventana(d, w, h, g, rnd, 0.05, 0.1, 0.19, 0.32)
            for lado, x in ((-1, 0.045), (1, 0.195)):
                d.polygon([(w*x, h*0.08), (w*(x + lado*0.03), h*0.08), (w*(x + lado*0.015), h*0.36), (w*x, h*0.36)],
                          fill=(240, 180, 170))
            d.rectangle([w*0.83, h*0.12, w*0.94, h*0.26], fill=(250, 245, 230), outline=(190, 150, 110), width=g*2)
            d.polygon([(w*0.85, h*0.24), (w*0.88, h*0.17), (w*0.91, h*0.24)], fill=(170, 210, 150))
        elif ambiente == "cocina":
            for i in range(14):
                for j in range(2):
                    x0, y0 = i*w/14, h*(0.3 + j*0.06)
                    d.rectangle([x0, y0, x0 + w/14, y0 + h*0.06], outline=(205, 220, 232), width=max(1, g//2))
            d.rectangle([w*0.86, pies - h*0.22, w, pies + h*0.02], fill=(225, 210, 190), outline=TRAZO, width=g)
            d.ellipse([w*0.89, pies - h*0.3, w*0.96, pies - h*0.22], fill=(190, 195, 205), outline=TRAZO, width=g)
        elif ambiente == "colegio":
            d.rectangle([w*0.03, h*0.08, w*0.27, h*0.33], fill=(70, 110, 90), outline=(150, 110, 70), width=g*3)
            for k in range(3):
                pts = [(w*0.06 + i*w*0.02, h*(0.14 + k*0.06) + h*0.008*math.sin(i*2)) for i in range(8)]
                _linea(d, pts, g, rnd, color=(235, 240, 235))
        elif ambiente == "hospital":
            _ventana(d, w, h, g, rnd, 0.05, 0.1, 0.19, 0.3)
            cx, cy, a = w*0.89, h*0.17, h*0.05
            d.rectangle([cx - a*0.35, cy - a, cx + a*0.35, cy + a], fill=(235, 80, 80))
            d.rectangle([cx - a, cy - a*0.35, cx + a, cy + a*0.35], fill=(235, 80, 80))
        else:
            d.line([(w*0.78, h*0.27), (w*0.98, h*0.27)], fill=(170, 140, 110), width=g*2)
            for k, color in enumerate(((150, 210, 160), (240, 170, 200), (160, 200, 240))):
                x = w*(0.81 + k*0.06)
                d.polygon([(x - h*0.012, h*0.17), (x + h*0.012, h*0.17), (x + h*0.03, h*0.265), (x - h*0.03, h*0.265)],
                          fill=color, outline=TRAZO)
    elif ambiente == "noche":
        _estrellas(d, w, h, g, rnd)
        cx, cy, r = w*0.88, h*0.15, h*0.06
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(250, 225, 120))
        d.ellipse([cx - r*0.4, cy - r*1.1, cx + r*1.3, cy + r*0.6], fill=PAPEL)
    elif ambiente == "espacio":
        _estrellas(d, w, h, g, rnd, n=26, color=(180, 180, 220))
        cx, cy, r = w*0.1, h*0.18, h*0.05
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(240, 190, 140), outline=TRAZO, width=g)
        d.arc([cx - r*1.8, cy - r*0.45, cx + r*1.8, cy + r*0.45], 160, 380, fill=(200, 160, 120), width=g*2)
        cx, cy, r = w*0.9, h*0.3, h*0.03
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(170, 200, 240), outline=TRAZO, width=g)
    elif ambiente == "cielo":
        for x, y, r in ((0.12, 0.15, 0.05), (0.85, 0.1, 0.06), (0.65, 0.3, 0.035), (0.25, 0.4, 0.03)):
            _nube(d, w, h, g, x, y, r)
        _pajaros(d, w, h, g, rnd, ((0.45, 0.12), (0.5, 0.15), (0.78, 0.36)))


def fondo(ambiente: str, tam: tuple, pies: float, apoyados: list) -> np.ndarray:
    """El fondo del plano como array: el ambiente y la sombra de cada cosa
    apoyada [(x, ancho)] en fracciones de pantalla."""
    w, h = tam
    img = Image.new("RGB", tam, PAPEL)
    d = ImageDraw.Draw(img)
    g = max(2, int(w*0.0022))
    _pinta(d, ambiente, w, h, pies, g, random.Random(sum(map(ord, ambiente))))
    for x, ancho in apoyados:
        cx, rx = w*x, w*ancho/2
        d.ellipse([cx - rx, pies - h*0.012, cx + rx, pies + h*0.016], fill=(226, 226, 224))
    return np.asarray(img)


def pon_detras(img: Image.Image, fondo_arr: np.ndarray) -> Image.Image:
    """El fondo solo donde el fotograma es papel."""
    arr = np.asarray(img)
    papel = (arr[..., 0] == PAPEL[0]) & (arr[..., 1] == PAPEL[1]) & (arr[..., 2] == PAPEL[2])
    return Image.fromarray(np.where(papel[..., None], fondo_arr, arr))
