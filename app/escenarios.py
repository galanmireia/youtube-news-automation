"""LOS ESCENARIOS DE WHY THOUGH: sitios enteros donde vive Mokordo.

Ella: "que podamos hacer a Mokordo en diferentes escenarios... rellenar todas
las escenas para que no haya cosas en blanco". El ambiente de garabato_ambiente
era un folio con cuatro trazos en los bordes; esto es un sitio de verdad, como
la tienda de prueba que le gusto: pared, suelo en perspectiva, muebles y
detalles de colores planos, un poco desenfocado y apagado para que lo de
delante (Mokordo, las cosas, las palabras) se lea primero.

Se pinta UNA vez por plano (y se guarda: el mismo sitio en la misma medida es
el mismo dibujo), y garabato_ambiente.pon_detras lo pone solo donde el
fotograma es papel. El suelo esta donde pisa la gente ('pies').
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

TINTA = (70, 64, 72)

# Lo que el guion ve de cada sitio.
ESCENARIOS = {
    "bano":         "bathroom: mirror, sink, shelf with skincare bottles, towels, tiles (skincare, hygiene, teeth, shower)",
    "dormitorio":   "bedroom: bed, nightstand with alarm clock and lamp, window at night/day (sleep, waking up, insomnia)",
    "cocina":       "kitchen: fridge, counter, stove, cabinets, fruit bowl (food, cooking, eating, diets)",
    "salon":        "living room: sofa, TV, rug, plant, lamp (home, couch potato, screens, relaxing)",
    "gimnasio":     "gym: dumbbells rack, treadmill, mats, mirror, motivational poster (exercise, muscles, sweating)",
    "oficina":      "office: desk with computer, chair, window blinds, coffee, plant (work, stress, sitting all day)",
    "calle":        "city street: buildings, shop fronts, lamp post, sidewalk (going out, walking, the city)",
    "parque":       "park: trees, bench, path, bushes, sun (outdoors, walking, nature, running)",
    "supermercado": "supermarket: shelves full of colorful products, price signs, lamps (shopping, food choices, money)",
    "consulta":     "doctor's office: exam bed, eye chart, cabinet, heart poster (doctor, health check, illness)",
    "laboratorio":  "lab: benches, flasks, microscope, whiteboard with formulas (science, experiments, studies)",
    "playa":        "beach: sea, sand, umbrella, sun, waves (sun, tanning, summer, holidays)",
    "colegio":      "classroom: blackboard, desks, clock, posters (learning, school, memory, kids)",
    "fiesta":       "party / bar: colored lights, bar counter with bottles, dance floor (party, alcohol, night out)",
}


def _texto(d, xy, txt, px, color):
    from PIL import ImageFont
    try:
        f = ImageFont.truetype("DejaVuSans-Bold.ttf", int(px))
    except OSError:
        f = ImageFont.load_default()
    d.text(xy, txt, font=f, fill=color)


def _mezcla(a, b, k):
    return tuple(int(x + (y - x)*k) for x, y in zip(a, b))


def _degradado(w, h, arriba, abajo):
    a = np.linspace(0, 1, h)[:, None, None]
    c = np.array(arriba)*(1 - a) + np.array(abajo)*a
    return Image.fromarray(np.repeat(c, w, axis=1).astype(np.uint8))


def _suelo(d, w, h, pies, color, linea, tipo="baldosa"):
    """El suelo en perspectiva, de la linea de los pies hacia abajo y un poco
    por encima (la pared acaba un poco antes de donde se pisa)."""
    arriba = pies - h*0.06
    d.rectangle([0, arriba, w, h], fill=color)
    fuga = (w*0.5, arriba - h*0.6)
    if tipo in ("baldosa", "madera"):
        paso = w/14 if tipo == "baldosa" else w/9
        k = -20
        while k*paso < w*2:
            x = k*paso
            d.line([(x, h), (fuga[0] + (x - fuga[0])*0.12, arriba)], fill=linea, width=2)
            k += 1
    if tipo == "baldosa":
        for j in range(7):
            y = arriba + (h - arriba)*((j/7)**1.6)
            d.line([(0, y), (w, y)], fill=linea, width=2)
    d.line([(0, arriba), (w, arriba)], fill=_mezcla(linea, (0, 0, 0), 0.25), width=4)


def _ventana(d, x0, y0, x1, y1, cielo=(196, 226, 246), noche=False, persiana=False):
    cielo = (52, 62, 104) if noche else cielo
    d.rectangle([x0, y0, x1, y1], fill=cielo, outline=TINTA, width=5)
    if noche:
        for k in range(6):
            sx = x0 + (x1 - x0)*(0.15 + 0.13*k)
            sy = y0 + (y1 - y0)*(0.2 + 0.25*((k*7) % 3)/3)
            d.ellipse([sx - 3, sy - 3, sx + 3, sy + 3], fill=(250, 240, 180))
        r = (x1 - x0)*0.12
        d.ellipse([x1 - r*3, y0 + r, x1 - r, y0 + r*3], fill=(250, 236, 170))
    else:
        r = (x1 - x0)*0.14
        d.ellipse([x0 + r, y0 + r*0.8, x0 + r*3.2, y0 + r*2], fill=(255, 255, 255))
    if persiana:
        for k in range(1, 9):
            y = y0 + (y1 - y0)*k/9
            d.line([(x0, y), (x1, y)], fill=(230, 226, 214), width=7)
    d.line([((x0 + x1)/2, y0), ((x0 + x1)/2, y1)], fill=TINTA, width=4)
    d.line([(x0, (y0 + y1)/2), (x1, (y0 + y1)/2)], fill=TINTA, width=4)


def _planta(d, x, y, t, rnd):
    d.polygon([(x - t*0.3, y - t*0.45), (x + t*0.3, y - t*0.45), (x + t*0.22, y), (x - t*0.22, y)],
              fill=(196, 112, 76), outline=TINTA)
    for k in range(7):
        a = math.pi*(1.1 + 0.8*k/6)
        lx, ly = x + math.cos(a)*t*0.55, y - t*0.45 + math.sin(a)*t*0.9
        d.ellipse([lx - t*0.16, ly - t*0.1, lx + t*0.16, ly + t*0.1], fill=(96, 168, 96), outline=TINTA)


def _lampara_techo(d, x, w, h, color=(250, 236, 180)):
    d.line([(x, 0), (x, h*0.07)], fill=TINTA, width=3)
    d.chord([x - w*0.035, h*0.05, x + w*0.035, h*0.13], 180, 360, fill=color, outline=TINTA, width=3)


def _cuadro(d, x0, y0, x1, y1, rnd, marco=(150, 112, 80)):
    d.rectangle([x0, y0, x1, y1], fill=marco, outline=TINTA, width=3)
    m = (x1 - x0)*0.1
    d.rectangle([x0 + m, y0 + m, x1 - m, y1 - m], fill=(206, 232, 246))
    d.polygon([(x0 + m, y1 - m), ((x0 + x1)/2 - m, y0 + (y1 - y0)*0.45), ((x0 + x1)/2 + m, y1 - m)],
              fill=(120, 180, 110))
    d.ellipse([x1 - m*3, y0 + m*1.5, x1 - m*1.6, y0 + m*2.9], fill=(250, 210, 90))


def _estante_botes(d, x0, x1, y, h, rnd, colores):
    d.rectangle([x0, y, x1, y + h*0.015], fill=(170, 130, 96), outline=TINTA, width=2)
    x = x0 + (x1 - x0)*0.05
    while x < x1 - (x1 - x0)*0.08:
        bw = h*rnd.uniform(0.025, 0.04)
        bh = h*rnd.uniform(0.05, 0.09)
        c = rnd.choice(colores)
        d.rounded_rectangle([x, y - bh, x + bw, y], radius=int(bw*0.3), fill=c, outline=TINTA, width=2)
        d.rectangle([x + bw*0.25, y - bh - h*0.012, x + bw*0.75, y - bh], fill=_mezcla(c, (0, 0, 0), 0.3))
        d.rectangle([x + bw*0.15, y - bh*0.6, x + bw*0.85, y - bh*0.35], fill=(255, 255, 255))
        x += bw + h*0.012


def _pinta(nombre, w, h, pies, rnd):
    P = lambda fx, fy: (w*fx, h*fy)
    if nombre == "bano":
        img = _degradado(w, h, (214, 236, 240), (196, 222, 230))
        d = ImageDraw.Draw(img)
        # azulejos
        lado = h*0.07
        for j in range(int(pies/lado) + 1):
            for i in range(int(w/lado) + 1):
                d.rectangle([i*lado, j*lado, (i + 1)*lado, (j + 1)*lado], outline=(180, 210, 220), width=2)
        _suelo(d, w, h, pies, (220, 226, 232), (196, 204, 212))
        # espejo y lavabo a la derecha
        d.rounded_rectangle([w*0.70, h*0.10, w*0.90, h*0.45], radius=int(h*0.05), fill=(214, 236, 248),
                            outline=(200, 170, 110), width=8)
        d.line([P(0.74, 0.15), P(0.79, 0.25)], fill=(255, 255, 255), width=8)
        d.line([P(0.76, 0.15), P(0.80, 0.22)], fill=(255, 255, 255), width=4)
        d.rounded_rectangle([w*0.68, h*0.5, w*0.92, h*0.56], radius=10, fill=(250, 250, 252), outline=TINTA, width=4)
        d.rectangle([w*0.77, h*0.56, w*0.83, pies - h*0.06], fill=(240, 240, 244), outline=TINTA, width=3)
        d.line([P(0.80, 0.47), P(0.80, 0.5)], fill=(160, 166, 176), width=8)
        d.line([P(0.80, 0.47), P(0.82, 0.47)], fill=(160, 166, 176), width=8)
        # estante con botes de skincare
        _estante_botes(d, w*0.04, w*0.26, h*0.30, h, rnd,
                       [(246, 196, 210), (196, 226, 250), (250, 236, 180), (210, 240, 210), (230, 210, 250)])
        _estante_botes(d, w*0.04, w*0.26, h*0.46, h, rnd,
                       [(250, 250, 252), (246, 180, 200), (180, 220, 240), (250, 220, 170)])
        # toalla
        d.line([P(0.30, 0.2), P(0.40, 0.2)], fill=(170, 170, 180), width=8)
        d.rounded_rectangle([w*0.31, h*0.2, w*0.39, h*0.42], radius=12, fill=(250, 170, 180), outline=TINTA, width=3)
        for k in range(3):
            d.line([P(0.31, 0.36 + k*0.015), P(0.39, 0.36 + k*0.015)], fill=(255, 220, 226), width=3)
    elif nombre == "dormitorio":
        img = _degradado(w, h, (226, 216, 240), (206, 196, 226))
        d = ImageDraw.Draw(img)
        _suelo(d, w, h, pies, (196, 160, 124), (170, 134, 100), "madera")
        _ventana(d, w*0.40, h*0.08, w*0.60, h*0.40, noche=True)
        for lado in (-1, 1):
            x = w*0.5 + lado*w*0.11
            d.polygon([(x, h*0.06), (x + lado*w*0.04, h*0.06), (x + lado*w*0.03, h*0.46), (x - lado*w*0.01, h*0.46)],
                      fill=(150, 120, 200), outline=TINTA)
        # cama a la izquierda
        d.rounded_rectangle([w*0.0, h*0.42, w*0.06, pies - h*0.04], radius=10, fill=(150, 110, 80), outline=TINTA, width=4)
        d.rectangle([w*0.02, h*0.56, w*0.30, pies - h*0.08], fill=(246, 244, 250), outline=TINTA, width=4)
        d.rectangle([w*0.10, h*0.53, w*0.30, pies - h*0.08], fill=(120, 150, 220), outline=TINTA, width=4)
        d.rounded_rectangle([w*0.025, h*0.5, w*0.09, h*0.57], radius=14, fill=(255, 255, 255), outline=TINTA, width=3)
        # mesilla con despertador y lampara a la derecha
        d.rectangle([w*0.78, h*0.55, w*0.90, pies - h*0.06], fill=(170, 128, 92), outline=TINTA, width=4)
        d.line([P(0.78, 0.62), P(0.90, 0.62)], fill=TINTA, width=3)
        d.ellipse([w*0.80, h*0.49, w*0.84, h*0.55], fill=(240, 90, 80), outline=TINTA, width=3)
        d.ellipse([w*0.807, h*0.505, w*0.833, h*0.535], fill=(255, 255, 255))
        d.line([P(0.87, 0.55), P(0.87, 0.46)], fill=TINTA, width=4)
        d.polygon([P(0.845, 0.46), P(0.895, 0.46), P(0.885, 0.40), P(0.855, 0.40)], fill=(250, 226, 150), outline=TINTA)
        _cuadro(d, w*0.72, h*0.12, w*0.86, h*0.30, rnd)
    elif nombre == "cocina":
        img = _degradado(w, h, (246, 236, 214), (236, 222, 196))
        d = ImageDraw.Draw(img)
        _suelo(d, w, h, pies, (226, 214, 196), (200, 188, 170))
        # azulejos del frente
        for i in range(24):
            for j in range(3):
                d.rectangle([i*w/24, h*(0.36 + j*0.05), (i + 1)*w/24, h*(0.41 + j*0.05)], fill=(232, 244, 240),
                            outline=(200, 220, 214), width=2)
        # armarios de arriba
        for k in range(4):
            x0 = w*(0.03 + k*0.075)
            d.rectangle([x0, h*0.06, x0 + w*0.07, h*0.3], fill=(150, 196, 180), outline=TINTA, width=4)
            d.ellipse([x0 + w*0.055, h*0.2, x0 + w*0.062, h*0.215], fill=TINTA)
        # encimera y fuegos
        d.rectangle([0, h*0.51, w*0.33, pies - h*0.06], fill=(150, 196, 180), outline=TINTA, width=4)
        d.rectangle([0, h*0.5, w*0.34, h*0.53], fill=(240, 240, 236), outline=TINTA, width=3)
        for k in range(2):
            d.ellipse([w*(0.05 + k*0.09), h*0.495, w*(0.11 + k*0.09), h*0.51], fill=(60, 60, 64))
        d.ellipse([w*0.2, h*0.44, w*0.27, h*0.5], fill=(210, 80, 70), outline=TINTA, width=3)   # olla
        # nevera a la derecha
        d.rounded_rectangle([w*0.80, h*0.12, w*0.95, pies - h*0.06], radius=18, fill=(246, 248, 252), outline=TINTA, width=5)
        d.line([P(0.80, 0.36), P(0.95, 0.36)], fill=TINTA, width=4)
        d.line([P(0.82, 0.2), P(0.82, 0.3)], fill=(150, 156, 166), width=8)
        d.line([P(0.82, 0.42), P(0.82, 0.55)], fill=(150, 156, 166), width=8)
        for k, c in enumerate(((250, 200, 80), (240, 120, 140), (120, 200, 150))):
            d.ellipse([w*(0.85 + k*0.025), h*0.15, w*(0.87 + k*0.025), h*0.18], fill=c)        # imanes
        # frutero
        d.chord([w*0.66, h*0.47, w*0.76, h*0.55], 0, 180, fill=(200, 160, 110), outline=TINTA, width=3)
        for k, c in enumerate(((240, 80, 70), (250, 200, 60), (120, 190, 90))):
            d.ellipse([w*(0.675 + k*0.025), h*0.46, w*(0.7 + k*0.025), h*0.5], fill=c, outline=TINTA)
        d.rectangle([w*0.64, h*0.55, w*0.78, h*0.56], fill=(200, 170, 130))
    elif nombre == "salon":
        img = _degradado(w, h, (246, 228, 204), (236, 214, 188))
        d = ImageDraw.Draw(img)
        _suelo(d, w, h, pies, (196, 156, 116), (170, 130, 94), "madera")
        d.ellipse([w*0.25, pies - h*0.02, w*0.75, pies + h*0.12], fill=(214, 110, 100))          # alfombra
        d.ellipse([w*0.29, pies, w*0.71, pies + h*0.1], outline=(240, 200, 160), width=4)
        _ventana(d, w*0.38, h*0.08, w*0.62, h*0.38)
        # sofa a la izquierda
        d.rounded_rectangle([w*0.0, h*0.48, w*0.24, pies - h*0.03], radius=30, fill=(110, 140, 200), outline=TINTA, width=5)
        d.rounded_rectangle([w*0.02, h*0.58, w*0.23, pies - h*0.06], radius=20, fill=(130, 160, 220), outline=TINTA, width=4)
        d.rounded_rectangle([w*0.06, h*0.52, w*0.12, h*0.6], radius=14, fill=(250, 200, 90), outline=TINTA, width=3)
        # tele a la derecha
        d.rectangle([w*0.76, h*0.58, w*0.97, pies - h*0.05], fill=(150, 112, 80), outline=TINTA, width=4)
        d.rounded_rectangle([w*0.77, h*0.30, w*0.96, h*0.56], radius=10, fill=(40, 44, 54), outline=TINTA, width=5)
        d.rectangle([w*0.785, h*0.32, w*0.945, h*0.54], fill=(110, 170, 230))
        d.line([P(0.80, 0.34), P(0.84, 0.42)], fill=(200, 230, 250), width=6)
        _planta(d, w*0.70, pies - h*0.05, h*0.18, rnd)
        d.line([P(0.29, 0.44), P(0.29, pies/h - 0.06)], fill=TINTA, width=4)                      # lampara de pie
        d.polygon([P(0.26, 0.44), P(0.32, 0.44), P(0.31, 0.36), P(0.27, 0.36)], fill=(250, 226, 150), outline=TINTA)
    elif nombre == "gimnasio":
        img = _degradado(w, h, (226, 232, 238), (206, 214, 222))
        d = ImageDraw.Draw(img)
        _suelo(d, w, h, pies, (90, 96, 108), (70, 76, 88), "liso")
        for k in range(3):                                                                         # colchonetas
            d.rectangle([w*(0.3 + k*0.14), pies - h*0.05, w*(0.42 + k*0.14), pies - h*0.03], fill=(70, 160, 200),
                        outline=TINTA, width=3)
        d.rectangle([w*0.35, h*0.08, w*0.65, h*0.36], fill=(240, 244, 248), outline=(150, 156, 166), width=6)  # espejo
        d.line([P(0.38, 0.12), P(0.43, 0.22)], fill=(255, 255, 255), width=8)
        d.rectangle([w*0.4, h*0.40, w*0.6, h*0.46], fill=(240, 90, 80), outline=TINTA, width=3)   # cartel
        _texto(d, (w*0.415, h*0.412), "NO PAIN NO GAIN", h*0.032, (255, 255, 255))
        # mancuernas a la izquierda
        d.rectangle([w*0.02, h*0.42, w*0.25, h*0.45], fill=(80, 84, 96), outline=TINTA, width=3)
        d.rectangle([w*0.02, h*0.56, w*0.25, h*0.59], fill=(80, 84, 96), outline=TINTA, width=3)
        for fila in (0.42, 0.56):
            for k in range(4):
                x = w*(0.04 + k*0.055)
                d.line([(x, h*fila - h*0.03), (x + w*0.035, h*fila - h*0.03)], fill=(150, 156, 166), width=6)
                for xx in (x, x + w*0.035):
                    d.rounded_rectangle([xx - h*0.012, h*fila - h*0.055, xx + h*0.012, h*fila - h*0.005], radius=6,
                                        fill=(40, 44, 54))
        d.rectangle([w*0.03, h*0.45, w*0.04, pies - h*0.06], fill=(80, 84, 96))
        d.rectangle([w*0.23, h*0.45, w*0.24, pies - h*0.06], fill=(80, 84, 96))
        # cinta de correr a la derecha
        d.polygon([P(0.74, pies/h - 0.07), P(0.98, pies/h - 0.07), P(0.98, pies/h - 0.12), P(0.76, pies/h - 0.12)],
                  fill=(60, 64, 74), outline=TINTA)
        d.line([P(0.95, pies/h - 0.12), P(0.92, 0.36)], fill=(120, 126, 136), width=10)
        d.rounded_rectangle([w*0.86, h*0.32, w*0.96, h*0.38], radius=8, fill=(60, 64, 74), outline=TINTA, width=3)
        d.rectangle([w*0.88, h*0.335, w*0.94, h*0.365], fill=(120, 230, 160))
    elif nombre == "oficina":
        img = _degradado(w, h, (232, 236, 240), (214, 220, 228))
        d = ImageDraw.Draw(img)
        _suelo(d, w, h, pies, (150, 160, 176), (130, 140, 156), "liso")
        _ventana(d, w*0.34, h*0.06, w*0.66, h*0.40, persiana=True)
        # mesa con ordenador a la izquierda
        d.rectangle([w*0.0, h*0.55, w*0.3, h*0.58], fill=(214, 196, 170), outline=TINTA, width=4)
        d.rectangle([w*0.02, h*0.58, w*0.04, pies - h*0.06], fill=(120, 126, 136))
        d.rectangle([w*0.26, h*0.58, w*0.28, pies - h*0.06], fill=(120, 126, 136))
        d.rounded_rectangle([w*0.06, h*0.34, w*0.22, h*0.5], radius=8, fill=(50, 54, 64), outline=TINTA, width=4)
        d.rectangle([w*0.07, h*0.355, w*0.21, h*0.485], fill=(140, 200, 240))
        for k in range(4):
            d.line([P(0.085, 0.38 + k*0.025), P(0.17 - 0.02*(k % 2), 0.38 + k*0.025)], fill=(255, 255, 255), width=4)
        d.rectangle([w*0.13, h*0.5, w*0.15, h*0.55], fill=(50, 54, 64))
        d.rectangle([w*0.22, h*0.51, w*0.25, h*0.55], fill=(255, 255, 255), outline=TINTA, width=2)     # taza
        # archivador y planta a la derecha
        d.rectangle([w*0.8, h*0.42, w*0.95, pies - h*0.06], fill=(160, 170, 186), outline=TINTA, width=4)
        for k in range(3):
            y = h*0.42 + (pies - h*0.48)*(k + 0.5)/3
            d.line([(w*0.84, y), (w*0.91, y)], fill=TINTA, width=5)
        _planta(d, w*0.72, pies - h*0.05, h*0.16, rnd)
        d.ellipse([w*0.75, h*0.12, w*0.83, h*0.26], fill=(255, 255, 255), outline=TINTA, width=5)   # reloj
        d.line([P(0.79, 0.19), P(0.79, 0.145)], fill=TINTA, width=4)
        d.line([P(0.79, 0.19), P(0.81, 0.2)], fill=TINTA, width=4)
    elif nombre == "calle":
        img = _degradado(w, h, (170, 214, 246), (222, 238, 250))
        d = ImageDraw.Draw(img)
        colores = [(240, 200, 170), (200, 220, 240), (246, 226, 160), (220, 200, 230), (200, 230, 200)]
        x = -w*0.02
        k = 0
        while x < w:
            ancho = w*(0.13 + 0.04*((k*3) % 3)/2)
            alto = h*(0.45 + 0.2*((k*5) % 4)/3)
            c = colores[k % len(colores)]
            d.rectangle([x, pies - h*0.06 - alto, x + ancho, pies - h*0.06], fill=c, outline=TINTA, width=4)
            for fy in np.arange(pies - h*0.06 - alto + h*0.05, pies - h*0.2, h*0.09):
                for fx in (x + ancho*0.15, x + ancho*0.58):
                    d.rectangle([fx, fy, fx + ancho*0.27, fy + h*0.05], fill=(170, 210, 240), outline=TINTA, width=2)
            # tienda abajo con toldo
            toldo = colores[(k + 2) % len(colores)]
            d.rectangle([x + ancho*0.08, pies - h*0.2, x + ancho*0.92, pies - h*0.06], fill=(250, 250, 246),
                        outline=TINTA, width=3)
            for j in range(5):
                tx = x + ancho*0.08 + ancho*0.84*j/5
                d.polygon([(tx, pies - h*0.22), (tx + ancho*0.168, pies - h*0.22), (tx + ancho*0.168, pies - h*0.18),
                           (tx, pies - h*0.18)], fill=(230, 90, 80) if j % 2 else (255, 255, 255), outline=TINTA)
            x += ancho
            k += 1
        _suelo(d, w, h, pies, (196, 196, 204), (170, 170, 180))
        for xx in (0.2, 0.8):                                                                     # farolas
            d.line([P(xx, pies/h - 0.05), P(xx, 0.25)], fill=(60, 64, 74), width=10)
            d.ellipse([w*xx - h*0.03, h*0.21, w*xx + h*0.03, h*0.27], fill=(250, 236, 170), outline=TINTA, width=3)
    elif nombre == "parque":
        img = _degradado(w, h, (176, 220, 248), (226, 242, 250))
        d = ImageDraw.Draw(img)
        d.ellipse([w*0.82, h*0.06, w*0.92, h*0.06 + w*0.1], fill=(252, 222, 110))
        for x, y, r in ((0.15, 0.12, 0.05), (0.55, 0.08, 0.04)):
            for dx, rr in ((-0.6, 0.7), (0, 1), (0.6, 0.75)):
                d.ellipse([w*x + dx*r*w - rr*r*w, h*y - rr*r*w*0.6, w*x + dx*r*w + rr*r*w, h*y + rr*r*w*0.6],
                          fill=(255, 255, 255))
        d.polygon([(0, pies - h*0.2), (w*0.3, pies - h*0.28), (w*0.7, pies - h*0.22), (w, pies - h*0.3), (w, h), (0, h)],
                  fill=(160, 206, 120))
        _suelo(d, w, h, pies, (140, 196, 100), (120, 176, 84), "liso")
        d.polygon([(w*0.42, h), (w*0.58, h), (w*0.53, pies - h*0.06), (w*0.47, pies - h*0.06)], fill=(226, 206, 160))
        for x, alto in ((0.08, 0.5), (0.22, 0.38), (0.86, 0.48), (0.7, 0.34)):                  # arboles
            tx, base = w*x, pies - h*0.05
            d.rectangle([tx - h*0.02, base - h*alto*0.5, tx + h*0.02, base], fill=(140, 100, 66), outline=TINTA, width=3)
            for dx, dy, rr in ((-0.6, 0, 0.9), (0.6, 0, 0.9), (0, -0.5, 1.0), (0, 0.1, 1.0)):
                cx, cy, r = tx + dx*h*0.07, base - h*alto*0.62 + dy*h*0.07, h*0.09*rr
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(96, 170, 96), outline=TINTA, width=3)
        d.rectangle([w*0.28, pies - h*0.12, w*0.4, pies - h*0.1], fill=(170, 120, 80), outline=TINTA, width=3)  # banco
        d.rectangle([w*0.28, pies - h*0.17, w*0.4, pies - h*0.15], fill=(170, 120, 80), outline=TINTA, width=3)
        for xx in (0.29, 0.39):
            d.line([P(xx, pies/h - 0.1), P(xx, pies/h - 0.06)], fill=TINTA, width=5)
    elif nombre == "supermercado":
        img = _degradado(w, h, (240, 234, 222), (226, 218, 204))
        d = ImageDraw.Draw(img)
        _suelo(d, w, h, pies, (226, 222, 214), (204, 200, 192))
        colores = [(226, 92, 80), (92, 152, 214), (246, 196, 72), (120, 190, 120), (236, 140, 180), (150, 120, 210)]
        for lado in (-1, 1):
            x_ext = 0 if lado < 0 else w
            x_int = w*0.3 if lado < 0 else w*0.7
            for nivel in range(4):
                y0 = h*0.12 + nivel*h*0.13
                d.polygon([(x_ext, y0 + h*0.1), (x_int, y0 + h*0.04), (x_int, y0 + h*0.05), (x_ext, y0 + h*0.125)],
                          fill=(170, 130, 96), outline=TINTA)
                for j in range(9):
                    u0, u1 = j/9, (j + 0.8)/9
                    xa, xb = x_ext + (x_int - x_ext)*u0, x_ext + (x_int - x_ext)*u1
                    ya = y0 + h*0.1 + (h*0.04 - h*0.1)*u0
                    yb = y0 + h*0.1 + (h*0.04 - h*0.1)*u1
                    alto = h*(0.075 - 0.035*u0)*rnd.uniform(0.7, 1.0)
                    d.polygon([(xa, ya), (xb, yb), (xb, yb - alto*0.85), (xa, ya - alto)], fill=rnd.choice(colores),
                              outline=TINTA)
        d.rectangle([w*0.4, h*0.1, w*0.6, h*0.2], fill=(240, 80, 70), outline=TINTA, width=4)
        _texto(d, (w*0.425, h*0.125), "SALE -50%", h*0.05, (255, 255, 255))
        for k in range(4):
            _lampara_techo(d, w*(0.2 + 0.2*k), w, h)
    elif nombre == "consulta":
        img = _degradado(w, h, (226, 242, 240), (208, 230, 228))
        d = ImageDraw.Draw(img)
        _suelo(d, w, h, pies, (214, 226, 230), (190, 204, 210))
        # camilla a la izquierda
        d.rounded_rectangle([w*0.0, h*0.5, w*0.28, h*0.56], radius=12, fill=(120, 180, 200), outline=TINTA, width=4)
        d.rectangle([w*0.0, h*0.49, w*0.08, h*0.52], fill=(255, 255, 255), outline=TINTA, width=3)
        for xx in (0.03, 0.25):
            d.line([P(xx, 0.56), P(xx, pies/h - 0.06)], fill=(150, 156, 166), width=8)
        # tabla de ojos y cartel del corazon
        d.rectangle([w*0.40, h*0.08, w*0.52, h*0.40], fill=(255, 255, 255), outline=TINTA, width=4)
        for k, (letras, tam) in enumerate((("E", 40), ("F P", 28), ("T O Z", 20), ("L P E D", 14))):
            _texto(d, (w*0.46 - len(letras)*tam*0.3, h*(0.11 + 0.07*k)), letras, tam*1.3, TINTA)
        d.rectangle([w*0.56, h*0.1, w*0.68, h*0.3], fill=(250, 240, 240), outline=TINTA, width=4)
        cx, cy, r = w*0.62, h*0.19, h*0.045
        d.ellipse([cx - r, cy - r, cx, cy + r*0.2], fill=(230, 70, 80))
        d.ellipse([cx, cy - r, cx + r, cy + r*0.2], fill=(230, 70, 80))
        d.polygon([(cx - r*0.97, cy - r*0.1), (cx + r*0.97, cy - r*0.1), (cx, cy + r*1.2)], fill=(230, 70, 80))
        # armario de medicinas
        d.rectangle([w*0.8, h*0.12, w*0.96, h*0.4], fill=(250, 250, 252), outline=TINTA, width=4)
        d.rectangle([w*0.865, h*0.17, w*0.895, h*0.29], fill=(230, 70, 80))
        d.rectangle([w*0.83, h*0.215, w*0.93, h*0.245], fill=(230, 70, 80))
        d.rectangle([w*0.78, h*0.5, w*0.97, pies - h*0.06], fill=(200, 214, 226), outline=TINTA, width=4)
        _planta(d, w*0.72, pies - h*0.05, h*0.14, rnd)
    elif nombre == "laboratorio":
        img = _degradado(w, h, (230, 238, 246), (212, 222, 234))
        d = ImageDraw.Draw(img)
        _suelo(d, w, h, pies, (206, 214, 224), (184, 194, 206))
        d.rectangle([w*0.33, h*0.08, w*0.67, h*0.36], fill=(252, 252, 252), outline=(150, 156, 166), width=6)  # pizarra
        for k, txt in enumerate(("E = mc²", "H₂O + CO₂", "f(x) = ?")):
            _texto(d, (w*(0.36 + 0.07*k), h*(0.12 + 0.075*k)), txt, h*0.045, (60, 100, 200))
        for lado, x0, x1 in ((-1, 0.0, 0.3), (1, 0.7, 1.0)):
            d.rectangle([w*x0, h*0.52, w*x1, pies - h*0.06], fill=(220, 226, 236), outline=TINTA, width=4)
            d.rectangle([w*x0, h*0.5, w*x1, h*0.53], fill=(60, 64, 74))
        for k, c in enumerate(((120, 220, 150), (240, 140, 190), (140, 190, 250), (250, 210, 90))):
            x = w*(0.04 + k*0.065)
            d.polygon([(x - h*0.015, h*0.4), (x + h*0.015, h*0.4), (x + h*0.04, h*0.5), (x - h*0.04, h*0.5)],
                      fill=c, outline=TINTA)
            d.rectangle([x - h*0.015, h*0.36, x + h*0.015, h*0.4], fill=(240, 244, 248), outline=TINTA)
        # microscopio
        d.rectangle([w*0.8, h*0.48, w*0.9, h*0.5], fill=(60, 64, 74))
        d.line([P(0.83, 0.48), P(0.86, 0.36)], fill=(60, 64, 74), width=14)
        d.line([P(0.85, 0.38), P(0.83, 0.3)], fill=(90, 94, 104), width=18)
        for k in range(5):                                                               # estanteria de frascos
            d.ellipse([w*(0.75 + k*0.04), h*0.18, w*(0.78 + k*0.04), h*0.24], fill=(160, 220, 200), outline=TINTA)
        d.line([P(0.74, 0.24), P(0.96, 0.24)], fill=(170, 130, 96), width=8)
    elif nombre == "playa":
        img = _degradado(w, h, (150, 206, 246), (210, 236, 252))
        d = ImageDraw.Draw(img)
        d.ellipse([w*0.8, h*0.06, w*0.9, h*0.06 + w*0.1], fill=(252, 220, 100))
        mar = pies - h*0.3
        d.rectangle([0, mar, w, pies - h*0.1], fill=(80, 170, 220))
        for k in range(4):
            y = mar + (k + 0.5)*(h*0.2)/4
            for j in range(8):
                x = w*(j*0.14 + 0.03*k)
                d.arc([x, y - h*0.01, x + w*0.06, y + h*0.01], 200, 340, fill=(220, 240, 250), width=4)
        d.rectangle([0, pies - h*0.1, w, h], fill=(246, 222, 160))
        d.line([(0, pies - h*0.1), (w, pies - h*0.1)], fill=(255, 255, 255), width=8)
        # sombrilla y toalla
        d.line([P(0.84, pies/h - 0.04), P(0.8, 0.4)], fill=(150, 112, 80), width=8)
        d.chord([w*0.7, h*0.32, w*0.9, h*0.5], 180, 360, fill=(240, 90, 80), outline=TINTA, width=4)
        for k in range(3):
            d.chord([w*(0.72 + k*0.06), h*0.34, w*(0.76 + k*0.06), h*0.5], 180, 360, fill=(255, 255, 255))
        d.polygon([P(0.05, pies/h + 0.02), P(0.25, pies/h + 0.02), P(0.27, pies/h + 0.08), P(0.03, pies/h + 0.08)],
                  fill=(120, 170, 240), outline=TINTA)
        d.ellipse([w*0.6, pies, w*0.64, pies + h*0.03], fill=(240, 200, 120), outline=TINTA)       # concha
    elif nombre == "colegio":
        img = _degradado(w, h, (246, 238, 214), (236, 224, 196))
        d = ImageDraw.Draw(img)
        _suelo(d, w, h, pies, (196, 160, 124), (170, 134, 100), "madera")
        d.rectangle([w*0.28, h*0.08, w*0.72, h*0.42], fill=(64, 104, 84), outline=(150, 110, 70), width=12)
        for k in range(3):
            pts = [(w*0.32 + i*w*0.04, h*(0.15 + k*0.08) + h*0.01*math.sin(i*2 + k)) for i in range(8)]
            d.line(pts, fill=(235, 240, 235), width=4)
        _texto(d, (w*0.55, h*0.33), "2 + 2 = 4", h*0.04, (250, 250, 240))
        d.ellipse([w*0.8, h*0.08, w*0.88, h*0.22], fill=(255, 255, 255), outline=TINTA, width=5)
        for x0 in (0.02, 0.8):                                                    # pupitres
            d.rectangle([w*x0, h*0.55, w*(x0 + 0.18), h*0.58], fill=(200, 160, 110), outline=TINTA, width=3)
            for xx in (x0 + 0.01, x0 + 0.17):
                d.line([P(xx, 0.58), P(xx, pies/h - 0.06)], fill=(80, 84, 96), width=6)
            d.rectangle([w*(x0 + 0.03), h*0.52, w*(x0 + 0.09), h*0.55], fill=(240, 100, 90), outline=TINTA)
        for k, c in enumerate(((246, 196, 72), (120, 190, 240), (240, 140, 180))):          # dibujos colgados
            d.rectangle([w*(0.04 + 0.07*k), h*(0.12 + 0.03*(k % 2)), w*(0.1 + 0.07*k), h*(0.24 + 0.03*(k % 2))],
                        fill=c, outline=TINTA, width=3)
    elif nombre == "fiesta":
        img = _degradado(w, h, (52, 40, 86), (32, 26, 56))
        d = ImageDraw.Draw(img)
        _suelo(d, w, h, pies, (60, 50, 96), (90, 80, 140))
        for k, c in enumerate(((250, 90, 160), (90, 200, 250), (250, 220, 90), (140, 250, 150))):  # focos
            x = w*(0.15 + k*0.23)
            d.polygon([(x - w*0.01, 0), (x + w*0.01, 0), (x + w*0.09, pies - h*0.06), (x - w*0.07, pies - h*0.06)],
                      fill=_mezcla(c, (52, 40, 86), 0.7))
            d.ellipse([x - w*0.015, 0, x + w*0.015, h*0.04], fill=c)
        # barra con botellas a la derecha
        d.rectangle([w*0.74, h*0.5, w*1.0, pies - h*0.06], fill=(120, 70, 50), outline=(20, 16, 30), width=4)
        d.line([P(0.74, 0.5), P(1.0, 0.5)], fill=(200, 150, 90), width=10)
        d.line([P(0.74, 0.3), P(1.0, 0.3)], fill=(150, 110, 70), width=8)
        for k, c in enumerate(((120, 200, 120), (200, 120, 60), (220, 220, 240), (160, 60, 60), (90, 160, 220))):
            x = w*(0.77 + 0.045*k)
            d.rounded_rectangle([x, h*0.2, x + w*0.022, h*0.3], radius=6, fill=c, outline=(20, 16, 30), width=2)
            d.rectangle([x + w*0.007, h*0.17, x + w*0.015, h*0.2], fill=c)
        # bola de discoteca
        cx, cy, r = w*0.5, h*0.1, h*0.06
        d.line([(cx, 0), (cx, cy - r)], fill=(200, 200, 210), width=3)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(200, 204, 220), outline=(255, 255, 255), width=3)
        for k in range(-2, 3):
            d.line([(cx - r, cy + k*r*0.35), (cx + r, cy + k*r*0.35)], fill=(255, 255, 255), width=2)
            d.line([(cx + k*r*0.35, cy - r), (cx + k*r*0.35, cy + r)], fill=(255, 255, 255), width=2)
        # guirnalda de bombillas
        for k in range(20):
            x = w*k/19
            y = h*0.24 + h*0.04*math.sin(k*0.9)
            d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=((250, 220, 90), (250, 90, 160), (90, 200, 250))[k % 3])
    else:
        return None
    return img


@lru_cache(maxsize=24)
def _cache(nombre, w, h, pies):
    img = _pinta(nombre, w, h, pies, random.Random(sum(map(ord, nombre))))
    if img is None:
        return None
    # Profundidad: el sitio un poco desenfocado y apagado, para que lo de
    # delante mande. Como la tienda: se lee "esto es el fondo".
    img = img.filter(ImageFilter.GaussianBlur(max(1.5, w/900)))
    claro = Image.new("RGB", img.size, (246, 242, 236)) if nombre != "fiesta" else Image.new("RGB", img.size, (40, 32, 70))
    img = Image.blend(img, claro, 0.16)
    return np.asarray(img)


def pinta(nombre: str, tam: tuple, pies: float) -> np.ndarray | None:
    """El escenario como array (alto, ancho, 3), o None si no existe."""
    if nombre not in ESCENARIOS:
        return None
    arr = _cache(nombre, int(tam[0]), int(tam[1]), int(pies))
    return None if arr is None else arr.copy()
