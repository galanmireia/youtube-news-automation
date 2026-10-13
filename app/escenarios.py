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
    "restaurante":  "fast food restaurant: counter, menu board with burgers, tables, neon sign (junk food, eating out)",
    "piscina":      "swimming pool: blue water, tiles, ladder, lifebuoy, sun (swimming, summer, chlorine)",
    "montana":      "snowy mountain: peaks, pine trees, snow on the ground (cold, hiking, altitude, winter)",
    "carretera":    "road with cars and traffic lights, city in the distance (driving, commuting, pollution)",
    "avion":        "inside a plane: rows of seats, round windows with clouds (flying, jet lag, travel)",
    "hospital":     "hospital room: bed with an IV drip, heart monitor, curtain (being ill, surgery, recovery)",
    "autoservicio": "drive-thru: the order window, a menu board, the speaker post and a car waiting (fast food, ordering, lazy)",
    "cine":         "cinema in the dark: glowing screen, red curtains, rows of red seats, popcorn (movies, snacks, screens)",
    "farmacia":     "pharmacy: green cross sign, shelves of medicine boxes, counter (medicine, pills, remedies)",
    "cocina_noche": "kitchen at midnight: dark, moon in the window, the open fridge glowing (midnight snacks, cravings)",
    "vestuario":    "gym locker room: lockers, bench, mirror, towels, a bathroom scale (weighing in, before/after)",
    "metro":        "inside a subway car: seats, poles, line map, dark tunnel windows (commuting, crowds, travel)",
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
    elif nombre == "restaurante":
        img = _degradado(w, h, (250, 236, 210), (240, 222, 190))
        d = ImageDraw.Draw(img)
        _suelo(d, w, h, pies, (226, 90, 80), (200, 70, 64))
        for i in range(0, 20, 2):                                  # suelo a cuadros
            for j in range(4):
                y0 = pies - h*0.06 + (h - pies + h*0.06)*j/4
                d.rectangle([w*i/20 + (w/20 if j % 2 else 0), y0, w*(i + 1)/20 + (w/20 if j % 2 else 0),
                             y0 + (h - pies + h*0.06)/4], fill=(250, 246, 236))
        d.rectangle([w*0.32, h*0.06, w*0.68, h*0.3], fill=(40, 44, 54), outline=TINTA, width=6)   # menu
        for k, (txt, c) in enumerate((("BURGER  $5", (250, 210, 80)), ("FRIES  $2", (250, 250, 250)),
                                      ("SODA  $1", (120, 200, 250)))):
            _texto(d, (w*0.36, h*(0.09 + 0.07*k)), txt, h*0.045, c)
        d.rectangle([w*0.0, h*0.48, w*0.38, pies - h*0.06], fill=(226, 70, 64), outline=TINTA, width=5)  # mostrador
        d.rectangle([w*0.0, h*0.46, w*0.4, h*0.49], fill=(250, 210, 80), outline=TINTA, width=3)
        d.rounded_rectangle([w*0.06, h*0.36, w*0.14, h*0.46], radius=8, fill=(60, 64, 74), outline=TINTA, width=3)
        for x0 in (0.72, 0.86):                                   # mesas
            d.ellipse([w*x0, h*0.52, w*(x0 + 0.12), h*0.56], fill=(250, 210, 80), outline=TINTA, width=3)
            d.line([P(x0 + 0.06, 0.56), P(x0 + 0.06, pies/h - 0.06)], fill=TINTA, width=8)
        _texto(d, (w*0.74, h*0.12), "OPEN 24H", h*0.06, (250, 90, 150))
    elif nombre == "piscina":
        img = _degradado(w, h, (160, 214, 248), (214, 238, 252))
        d = ImageDraw.Draw(img)
        d.ellipse([w*0.84, h*0.06, w*0.93, h*0.06 + w*0.09], fill=(252, 220, 100))
        d.rectangle([0, h*0.32, w, pies - h*0.06], fill=(240, 244, 248))                             # pared
        for i in range(30):
            d.line([(i*w/30, h*0.32), (i*w/30, pies - h*0.06)], fill=(214, 224, 232), width=2)
        d.rectangle([0, pies - h*0.06, w, h], fill=(90, 190, 230))                                   # agua
        for k in range(5):
            y = pies + k*(h - pies)/5
            for j in range(9):
                x = w*(j*0.12 + 0.04*k)
                d.arc([x, y - h*0.01, x + w*0.07, y + h*0.015], 200, 340, fill=(200, 240, 252), width=4)
        d.line([(0, pies - h*0.06), (w, pies - h*0.06)], fill=(255, 255, 255), width=10)
        for xx in (0.08, 0.12):                                                                       # escalera
            d.arc([w*xx - w*0.03, h*0.5, w*xx + w*0.01, h*0.62], 180, 360, fill=(170, 176, 188), width=8)
            d.line([P(xx + 0.01, 0.56), P(xx + 0.01, pies/h + 0.04)], fill=(170, 176, 188), width=8)
        cx, cy, r = w*0.85, h*0.47, h*0.07                                                           # salvavidas
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(240, 80, 70), outline=TINTA, width=4)
        d.ellipse([cx - r*0.5, cy - r*0.5, cx + r*0.5, cy + r*0.5], fill=(240, 244, 248), outline=TINTA, width=3)
        for a in range(4):
            aa = a*math.pi/2 + math.pi/4
            d.line([(cx + math.cos(aa)*r*0.55, cy + math.sin(aa)*r*0.55), (cx + math.cos(aa)*r*0.95, cy + math.sin(aa)*r*0.95)],
                   fill=(255, 255, 255), width=12)
    elif nombre == "montana":
        img = _degradado(w, h, (176, 210, 240), (226, 238, 248))
        d = ImageDraw.Draw(img)
        for x0, x1, top, c in ((-0.1, 0.5, 0.12, (150, 160, 190)), (0.3, 0.95, 0.06, (130, 140, 176)),
                               (0.65, 1.2, 0.18, (150, 160, 190))):
            pico = (w*(x0 + x1)/2, h*top)
            d.polygon([(w*x0, pies - h*0.1), pico, (w*x1, pies - h*0.1)], fill=c, outline=TINTA)
            d.polygon([(pico[0] - w*(x1 - x0)*0.12, pico[1] + h*0.12), pico, (pico[0] + w*(x1 - x0)*0.12, pico[1] + h*0.12),
                       (pico[0] + w*(x1 - x0)*0.04, pico[1] + h*0.09), (pico[0], pico[1] + h*0.13),
                       (pico[0] - w*(x1 - x0)*0.05, pico[1] + h*0.09)], fill=(255, 255, 255))
        _suelo(d, w, h, pies, (246, 248, 252), (220, 228, 238), "liso")
        for x, alto in ((0.05, 0.3), (0.14, 0.22), (0.86, 0.32), (0.95, 0.24)):                        # pinos
            tx, base = w*x, pies - h*0.04
            d.rectangle([tx - h*0.012, base - h*0.05, tx + h*0.012, base], fill=(120, 86, 60))
            for k in range(3):
                yb = base - h*0.04 - k*h*alto*0.25
                d.polygon([(tx - h*alto*0.3*(1 - k*0.25), yb), (tx, yb - h*alto*0.4), (tx + h*alto*0.3*(1 - k*0.25), yb)],
                          fill=(70, 140, 100), outline=TINTA)
                d.line([(tx - h*alto*0.2*(1 - k*0.25), yb - h*0.01), (tx + h*alto*0.2*(1 - k*0.25), yb - h*0.01)],
                       fill=(255, 255, 255), width=5)
        for k in range(40):                                                                             # copos
            x, y = rnd.uniform(0, w), rnd.uniform(0, pies)
            d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(255, 255, 255))
    elif nombre == "carretera":
        img = _degradado(w, h, (176, 214, 246), (226, 240, 250))
        d = ImageDraw.Draw(img)
        for k in range(9):                                                                             # ciudad lejos
            x = w*k/9
            alto = h*(0.12 + 0.1*((k*5) % 3))
            d.rectangle([x, pies - h*0.25 - alto, x + w/10, pies - h*0.25], fill=(196, 206, 222), outline=(170, 180, 196))
        d.rectangle([0, pies - h*0.25, w, pies - h*0.06], fill=(120, 190, 100))
        d.rectangle([0, pies - h*0.06, w, h], fill=(90, 94, 104))
        for k in range(8):
            d.rectangle([w*(k/8 + 0.02), pies + h*0.06, w*(k/8 + 0.08), pies + h*0.075], fill=(250, 240, 200))
        for x, c in ((0.1, (226, 70, 64)), (0.82, (90, 150, 230))):                                     # coches
            cx, cy = w*x, pies - h*0.1
            d.rounded_rectangle([cx - w*0.07, cy - h*0.06, cx + w*0.07, cy + h*0.02], radius=14, fill=c, outline=TINTA, width=4)
            d.polygon([(cx - w*0.04, cy - h*0.06), (cx - w*0.025, cy - h*0.11), (cx + w*0.03, cy - h*0.11),
                       (cx + w*0.045, cy - h*0.06)], fill=(190, 220, 245), outline=TINTA)
            for dx in (-0.045, 0.045):
                d.ellipse([cx + w*dx - h*0.025, cy, cx + w*dx + h*0.025, cy + h*0.05], fill=(40, 40, 46))
        d.rectangle([w*0.66, h*0.3, w*0.68, pies - h*0.1], fill=(60, 64, 74))                           # semaforo
        d.rounded_rectangle([w*0.645, h*0.18, w*0.695, h*0.32], radius=8, fill=(40, 44, 54), outline=TINTA, width=3)
        for k, c in enumerate(((240, 70, 60), (250, 200, 60), (90, 200, 110))):
            d.ellipse([w*0.66, h*(0.19 + 0.043*k), w*0.68, h*(0.19 + 0.043*k) + w*0.02], fill=c)
    elif nombre == "avion":
        img = _degradado(w, h, (236, 238, 244), (220, 224, 234))
        d = ImageDraw.Draw(img)
        _suelo(d, w, h, pies, (120, 130, 160), (100, 110, 140), "liso")
        d.chord([-w*0.1, -h*0.3, w*1.1, h*0.4], 0, 180, fill=(246, 246, 250), outline=(200, 204, 214), width=4)
        for k in range(6):                                                                            # ventanillas
            x = w*(0.08 + 0.16*k)
            d.rounded_rectangle([x, h*0.18, x + w*0.06, h*0.33], radius=30, fill=(170, 214, 246), outline=(150, 156, 170), width=6)
            d.ellipse([x + w*0.01, h*0.24, x + w*0.05, h*0.28], fill=(255, 255, 255))
        for lado, xs in ((-1, (0.0, 0.12, 0.24)), (1, (0.68, 0.8, 0.92))):                            # asientos
            for x in xs:
                d.rounded_rectangle([w*x, h*0.4, w*(x + 0.09), pies - h*0.06], radius=16, fill=(70, 90, 160), outline=TINTA, width=4)
                d.rounded_rectangle([w*x + 6, h*0.4, w*(x + 0.09) - 6, h*0.46], radius=10, fill=(250, 250, 252))
    elif nombre == "hospital":
        img = _degradado(w, h, (228, 240, 246), (210, 228, 236))
        d = ImageDraw.Draw(img)
        _suelo(d, w, h, pies, (206, 220, 226), (186, 200, 208))
        d.rectangle([w*0.0, h*0.48, w*0.3, h*0.58], fill=(250, 250, 252), outline=TINTA, width=4)          # cama
        d.rectangle([w*0.02, h*0.42, w*0.04, pies - h*0.06], fill=(170, 176, 188))
        d.rectangle([w*0.0, h*0.56, w*0.3, h*0.6], fill=(120, 180, 210), outline=TINTA, width=3)
        for xx in (0.03, 0.27):
            d.line([P(xx, 0.6), P(xx, pies/h - 0.06)], fill=(170, 176, 188), width=8)
        d.line([P(0.34, 0.12), P(0.34, pies/h - 0.06)], fill=(170, 176, 188), width=6)                    # gotero
        d.rounded_rectangle([w*0.32, h*0.13, w*0.36, h*0.24], radius=10, fill=(220, 240, 250), outline=TINTA, width=3)
        d.line([P(0.34, 0.24), P(0.3, 0.5)], fill=(150, 200, 230), width=3)
        d.rounded_rectangle([w*0.78, h*0.14, w*0.95, h*0.32], radius=10, fill=(40, 44, 54), outline=TINTA, width=5)  # monitor
        pts, x = [], w*0.79
        for k in range(14):
            pico = (k % 5 == 2)
            pts.append((x + k*w*0.011, h*(0.23 - (0.06 if pico else 0) + (0.03 if k % 5 == 3 else 0))))
        d.line(pts, fill=(110, 240, 140), width=4)
        d.line([P(0.86, 0.32), P(0.86, pies/h - 0.06)], fill=(170, 176, 188), width=8)
        for k in range(6):                                                                             # cortina
            x = w*(0.55 + 0.03*k)
            d.line([(x, h*0.05), (x + w*0.01, h*0.44)], fill=(160, 200, 220), width=18)
        d.line([P(0.53, 0.05), P(0.75, 0.05)], fill=(150, 156, 166), width=6)
    elif nombre == "autoservicio":
        # EL AUTOSERVICIO (drive-thru): la ventanilla, el panel del menu y el
        # altavoz, con el coche esperando.
        img = _degradado(w, h, (250, 200, 150), (252, 226, 190))
        d = ImageDraw.Draw(img)
        d.ellipse([w*0.06, h*0.05, w*0.06 + h*0.12, h*0.17], fill=(252, 236, 140))
        d.rectangle([w*0.38, h*0.12, w*1.0, pies - h*0.06], fill=(226, 70, 64), outline=TINTA, width=5)   # edificio
        d.rectangle([w*0.38, h*0.12, w*1.0, h*0.2], fill=(250, 210, 80), outline=TINTA, width=4)
        _texto(d, (w*0.58, h*0.13), "DRIVE-THRU", h*0.055, (226, 70, 64))
        d.rounded_rectangle([w*0.46, h*0.27, w*0.62, h*0.47], radius=10, fill=(190, 222, 245), outline=TINTA, width=5)
        d.line([P(0.54, 0.27), P(0.54, 0.47)], fill=TINTA, width=4)                                      # ventanilla
        d.rectangle([w*0.44, h*0.47, w*0.64, h*0.5], fill=(200, 204, 214), outline=TINTA, width=3)
        d.rectangle([w*0.74, h*0.24, w*0.95, h*0.5], fill=(40, 44, 54), outline=TINTA, width=6)        # panel menu
        for k, (txt, c) in enumerate((("MEGA MEAL", (250, 210, 80)), ("XL FRIES", (250, 250, 250)),
                                      ("SHAKE", (250, 150, 200)))):
            _texto(d, (w*0.76, h*(0.27 + 0.07*k)), txt, h*0.04, c)
        d.line([P(0.845, 0.5), P(0.845, pies/h - 0.06)], fill=(90, 94, 104), width=12)
        d.rounded_rectangle([w*0.68, h*0.52, w*0.72, h*0.6], radius=8, fill=(60, 64, 74), outline=TINTA, width=3)  # altavoz
        for k in range(3):
            d.line([P(0.685, 0.54 + k*0.02), P(0.715, 0.54 + k*0.02)], fill=(140, 146, 156), width=3)
        d.line([P(0.70, 0.6), P(0.70, pies/h - 0.06)], fill=(90, 94, 104), width=8)
        d.rectangle([0, pies - h*0.06, w, h], fill=(110, 114, 124))                                       # carril
        for k in range(6):
            d.polygon([(w*(0.1 + k*0.17), pies + h*0.06), (w*(0.05 + k*0.17), pies + h*0.04),
                       (w*(0.05 + k*0.17), pies + h*0.08)], fill=(250, 240, 200))
        cx, cy = w*0.14, pies - h*0.1                                                                     # el coche
        d.rounded_rectangle([cx - w*0.12, cy - h*0.07, cx + w*0.12, cy + h*0.03], radius=18, fill=(90, 150, 230),
                            outline=TINTA, width=4)
        d.polygon([(cx - w*0.07, cy - h*0.07), (cx - w*0.045, cy - h*0.14), (cx + w*0.05, cy - h*0.14),
                   (cx + w*0.08, cy - h*0.07)], fill=(190, 220, 245), outline=TINTA)
        for dx in (-0.075, 0.075):
            d.ellipse([cx + w*dx - h*0.03, cy - h*0.005, cx + w*dx + h*0.03, cy + h*0.055], fill=(40, 40, 46))
    elif nombre == "cine":
        # EL CINE: a oscuras, la pantalla que brilla y las butacas rojas
        img = _degradado(w, h, (34, 30, 52), (52, 40, 66))
        d = ImageDraw.Draw(img)
        d.rectangle([w*0.18, h*0.06, w*0.82, h*0.4], fill=(170, 200, 236), outline=(20, 16, 30), width=6)   # pantalla
        d.polygon([(w*0.3, h*0.34), (w*0.42, h*0.18), (w*0.5, h*0.28), (w*0.6, h*0.14), (w*0.74, h*0.34)],
                  fill=(120, 160, 210))
        for lado in (0.0, 0.84):                                                                          # telon
            for k in range(4):
                x = w*(lado + 0.04*k)
                d.rectangle([x, 0, x + w*0.04, h*0.46], fill=((150, 30, 40), (180, 40, 50))[k % 2])
        d.rectangle([0, 0, w, h*0.04], fill=(150, 30, 40))
        _suelo(d, w, h, pies, (60, 40, 60), (44, 30, 46), "liso")
        for fila, (y, esc) in enumerate(((0.5, 0.8), (0.6, 1.0))):                                         # butacas
            n = 9 - fila
            for k in range(n):
                x = w*(k + 0.5)/n
                a, b = h*0.05*esc, h*0.09*esc
                d.rounded_rectangle([x - a, h*y, x + a, h*y + b], radius=14, fill=(190, 40, 50), outline=(20, 16, 30),
                                    width=3)
        cx, base = w*0.9, pies - h*0.04                                                                    # palomitas
        d.polygon([(cx - h*0.05, base - h*0.14), (cx + h*0.05, base - h*0.14), (cx + h*0.035, base),
                   (cx - h*0.035, base)], fill=(250, 250, 250), outline=(20, 16, 30))
        for k in range(3):
            d.line([(cx - h*0.03 + k*h*0.03, base - h*0.14), (cx - h*0.022 + k*h*0.022, base)], fill=(226, 60, 60), width=6)
        for k in range(7):
            x = cx - h*0.045 + k*h*0.015
            d.ellipse([x - h*0.018, base - h*0.18 - (k % 2)*h*0.015, x + h*0.018, base - h*0.145], fill=(252, 236, 170))
    elif nombre == "farmacia":
        # LA FARMACIA: la cruz verde, estanterias de cajitas y el mostrador
        img = _degradado(w, h, (236, 246, 240), (222, 238, 230))
        d = ImageDraw.Draw(img)
        _suelo(d, w, h, pies, (226, 232, 230), (206, 214, 212))
        cx, cy, a = w*0.5, h*0.15, h*0.05                                                                 # la cruz
        for x0, y0, x1, y1 in ((cx - a, cy - a*3, cx + a, cy + a*3), (cx - a*3, cy - a, cx + a*3, cy + a)):
            d.rectangle([x0, y0, x1, y1], fill=(60, 190, 110), outline=TINTA, width=4)
        for x0 in (0.02, 0.72):                                                                           # estanterias
            d.rectangle([w*x0, h*0.12, w*(x0 + 0.26), pies - h*0.06], fill=(250, 250, 248), outline=TINTA, width=4)
            for k in range(4):
                y = h*(0.24 + 0.11*k)
                d.line([(w*x0, y), (w*(x0 + 0.26), y)], fill=TINTA, width=4)
                x = w*x0 + 8
                while x < w*(x0 + 0.25) - 30:
                    ancho = rnd.uniform(w*0.018, w*0.03)
                    alto = rnd.uniform(h*0.04, h*0.07)
                    d.rectangle([x, y - alto, x + ancho, y - 2], outline=TINTA, width=2,
                                fill=rnd.choice(((250, 250, 252), (200, 230, 250), (250, 210, 210), (220, 246, 220),
                                                 (252, 236, 180))))
                    x += ancho + 6
        d.rectangle([w*0.36, h*0.5, w*0.64, pies - h*0.06], fill=(250, 250, 248), outline=TINTA, width=5)  # mostrador
        d.rectangle([w*0.34, h*0.48, w*0.66, h*0.51], fill=(60, 190, 110), outline=TINTA, width=3)
    elif nombre == "cocina_noche":
        # LA COCINA A MEDIANOCHE: a oscuras, la luna en la ventana y la nevera
        # abierta que lo ilumina todo (los atracones de las 3 de la mañana)
        img = _degradado(w, h, (40, 44, 76), (56, 58, 92))
        d = ImageDraw.Draw(img)
        _suelo(d, w, h, pies, (64, 66, 96), (50, 52, 80))
        d.rectangle([w*0.08, h*0.1, w*0.28, h*0.36], fill=(24, 28, 60), outline=(20, 16, 30), width=6)      # ventana
        d.ellipse([w*0.18, h*0.13, w*0.18 + h*0.08, h*0.21], fill=(250, 246, 210))
        d.ellipse([w*0.19, h*0.12, w*0.19 + h*0.08, h*0.2], fill=(24, 28, 60))
        for k in range(5):
            x, y = w*(0.1 + 0.035*k), h*(0.16 + 0.04*(k % 3))
            d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(250, 250, 230))
        d.rectangle([w*0.0, h*0.5, w*0.42, pies - h*0.06], fill=(80, 76, 110), outline=(20, 16, 30), width=4)  # encimera
        d.rectangle([w*0.0, h*0.48, w*0.44, h*0.51], fill=(110, 106, 140))
        # la luz de la nevera: un cono amarillo en el suelo
        d.polygon([(w*0.7, h*0.18), (w*0.45, pies + h*0.2), (w*1.0, pies + h*0.2), (w*0.92, h*0.18)],
                  fill=(196, 180, 120))
        d.rectangle([w*0.7, h*0.12, w*0.92, pies - h*0.06], fill=(250, 246, 220), outline=(20, 16, 30), width=5)
        for k in range(3):                                                                                 # baldas
            y = h*(0.24 + 0.12*k)
            d.line([(w*0.71, y), (w*0.91, y)], fill=(200, 200, 196), width=5)
        d.rounded_rectangle([w*0.73, h*0.17, w*0.79, h*0.24], radius=6, fill=(250, 210, 80), outline=TINTA, width=2)
        d.rounded_rectangle([w*0.82, h*0.16, w*0.86, h*0.24], radius=6, fill=(230, 240, 250), outline=TINTA, width=2)
        d.ellipse([w*0.74, h*0.3, w*0.84, h*0.36], fill=(240, 150, 80), outline=TINTA, width=2)
        d.polygon([(w*0.92, h*0.12), (w*0.99, h*0.08), (w*0.99, pies - h*0.02), (w*0.92, pies - h*0.06)],
                  fill=(230, 226, 210), outline=(20, 16, 30))                                                # puerta
    elif nombre == "vestuario":
        # EL VESTUARIO DEL GIMNASIO: taquillas, el banco y la bascula
        img = _degradado(w, h, (222, 230, 238), (206, 216, 228))
        d = ImageDraw.Draw(img)
        _suelo(d, w, h, pies, (200, 210, 220), (180, 190, 204))
        for k in range(7):                                                                                  # taquillas
            x = w*(0.02 + 0.095*k)
            if 0.36 < x/w < 0.62:
                continue
            c = ((90, 140, 210), (80, 128, 196))[k % 2]
            d.rectangle([x, h*0.1, x + w*0.09, pies - h*0.1], fill=c, outline=TINTA, width=4)
            for j in range(3):
                d.line([(x + w*0.02, h*(0.15 + 0.025*j)), (x + w*0.07, h*(0.15 + 0.025*j))], fill=(40, 60, 100), width=3)
            d.rectangle([x + w*0.065, h*0.36, x + w*0.075, h*0.42], fill=(220, 224, 232), outline=TINTA, width=2)
        d.rectangle([w*0.08, h*0.6, w*0.34, h*0.63], fill=(190, 140, 90), outline=TINTA, width=3)            # banco
        for xx in (0.1, 0.32):
            d.line([P(xx, 0.63), P(xx, pies/h - 0.06)], fill=TINTA, width=6)
        d.rounded_rectangle([w*0.4, h*0.12, w*0.58, h*0.36], radius=12, fill=(214, 236, 248), outline=(170, 176, 188),
                            width=8)                                                                         # espejo
        d.line([P(0.43, 0.16), P(0.47, 0.24)], fill=(255, 255, 255), width=6)
        bx, by = w*0.86, pies - h*0.05                                                                       # bascula
        d.rounded_rectangle([bx - w*0.06, by - h*0.04, bx + w*0.06, by], radius=10, fill=(240, 242, 246), outline=TINTA,
                            width=4)
        d.rectangle([bx - w*0.025, by - h*0.035, bx + w*0.025, by - h*0.015], fill=(60, 64, 74))
        # (sin cartel: con letras se metia debajo de los marcadores y del titulo)
        for k in range(2):                                                                                   # toallas
            x = w*(0.72 + 0.1*k)
            d.line([(x - w*0.04, h*0.36), (x + w*0.04, h*0.36)], fill=(170, 176, 188), width=8)
            d.rounded_rectangle([x - w*0.035, h*0.36, x + w*0.035, h*0.52], radius=10,
                                fill=((250, 170, 180), (250, 220, 120))[k], outline=TINTA, width=3)
    elif nombre == "metro":
        # DENTRO DEL METRO: asientos, barras, el plano de lineas y la ventana
        # oscura del tunel
        img = _degradado(w, h, (226, 230, 236), (210, 216, 226))
        d = ImageDraw.Draw(img)
        _suelo(d, w, h, pies, (150, 156, 170), (130, 136, 150), "liso")
        for k in range(3):                                                                                  # ventanas
            x = w*(0.06 + 0.32*k)
            d.rounded_rectangle([x, h*0.12, x + w*0.24, h*0.34], radius=24, fill=(40, 44, 60), outline=(150, 156, 170),
                                width=8)
            for j in range(3):
                d.line([(x + w*(0.03 + 0.07*j), h*0.2), (x + w*(0.06 + 0.07*j), h*0.2)], fill=(250, 220, 140), width=5)
        d.rectangle([w*0.0, h*0.48, w*1.0, h*0.56], fill=(90, 150, 220), outline=TINTA, width=4)             # asientos
        d.rectangle([w*0.0, h*0.38, w*1.0, h*0.48], fill=(70, 128, 200), outline=TINTA, width=4)
        for x in (0.25, 0.75):                                                                               # barras
            d.line([P(x, 0.0), P(x, pies/h - 0.06)], fill=(196, 200, 210), width=12)
        d.line([P(0.0, 0.06), P(1.0, 0.06)], fill=(196, 200, 210), width=10)
        d.rectangle([w*0.38, h*0.36, w*0.62, h*0.37], fill=(196, 200, 210))
        d.rectangle([w*0.4, h*0.02, w*0.6, h*0.1], fill=(250, 250, 248), outline=TINTA, width=3)            # plano
        for k, c in enumerate(((226, 70, 64), (60, 190, 110), (250, 200, 60))):
            y = h*(0.04 + 0.02*k)
            d.line([(w*0.42, y), (w*0.58, y)], fill=c, width=5)
            for j in range(5):
                x = w*(0.43 + 0.035*j)
                d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(255, 255, 255), outline=c, width=2)
    else:
        return None
    return img


# Los de noche: se apagan hacia oscuro, no hacia blanco.
_OSCUROS = ("fiesta", "cine", "cocina_noche")


@lru_cache(maxsize=24)
def _cache(nombre, w, h, pies):
    img = _pinta(nombre, w, h, pies, random.Random(sum(map(ord, nombre))))
    if img is None:
        return None
    # Profundidad: el sitio un poco desenfocado y apagado, para que lo de
    # delante mande. Como la tienda: se lee "esto es el fondo".
    img = img.filter(ImageFilter.GaussianBlur(max(1.5, w/900)))
    claro = Image.new("RGB", img.size, (246, 242, 236)) if nombre not in _OSCUROS else Image.new("RGB", img.size, (40, 32, 70))
    img = Image.blend(img, claro, 0.16)
    return np.asarray(img)


def pinta(nombre: str, tam: tuple, pies: float) -> np.ndarray | None:
    """El escenario como array (alto, ancho, 3), o None si no existe."""
    if nombre not in ESCENARIOS:
        return None
    arr = _cache(nombre, int(tam[0]), int(tam[1]), int(pies))
    return None if arr is None else arr.copy()
