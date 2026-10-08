"""LOS ANIMALES, DE LA FAMILIA DE MOKORDO.

Ella: "¿los dibujos tambien son como Mokordo? Me gustaria que si sale un
caballo fuera gordito y tal, que esten mejor". Asi que los animales son
todos de la misma familia: cuerpo y cabeza redondos y rellenitos, patitas
cortas, una sombra en media luna por la derecha, un brillo arriba a la
izquierda, ojos grandes con su pupila y mofletes.

Misma firma que el resto de dibujos: (d, x, y, t, rnd, g), con (x, y) el
centro de abajo y t la altura. Miran a la derecha.
"""
import math

TINTA = (30, 30, 34)
BLANCO = (255, 255, 255)
ROSA = (250, 175, 185)


def _osc(c, f=0.84):
    return tuple(int(v*f) for v in c)


def _claro(c):
    return tuple(min(255, int(v*1.1 + 28)) for v in c)


def _bola(d, caja, color, g, brillo=True):
    """Un ovalo rellenito: sombra en media luna a la derecha y abajo, brillo
    arriba a la izquierda y su borde."""
    x0, y0, x1, y1 = caja
    w, h = x1 - x0, y1 - y0
    d.ellipse(caja, fill=_osc(color))
    d.ellipse([x0, y0, x1 - w*0.13, y1 - h*0.07], fill=color)
    if brillo and w > 12:
        d.ellipse([x0 + w*0.16, y0 + h*0.13, x0 + w*0.3, y0 + h*0.3], fill=_claro(color))
    d.ellipse(caja, outline=TINTA, width=g)


def _ojitos(d, cx, cy, r, g, mira=0.3):
    """Los ojos de la familia de Mokordo: blanco grande, pupila y brillito."""
    for k, dx in enumerate((-0.55, 0.55)):
        ex = cx + dx*r
        ro = r*0.42
        d.ellipse([ex - ro, cy - ro*1.15, ex + ro, cy + ro*1.15], fill=BLANCO, outline=TINTA, width=max(2, g//2))
        rp = ro*0.58
        px = ex + mira*ro*0.4
        d.ellipse([px - rp, cy - rp, px + rp, cy + rp], fill=TINTA)
        d.ellipse([px - rp*0.15, cy - rp*0.75, px + rp*0.4, cy - rp*0.25], fill=BLANCO)


def _moflete(d, cx, cy, r):
    d.ellipse([cx - r, cy - r*0.6, cx + r, cy + r*0.6], fill=ROSA)


def _pata(d, x, y, ancho, alto, color, g):
    d.rounded_rectangle([x - ancho/2, y - alto, x + ancho/2, y], radius=int(ancho/2), fill=color,
                        outline=TINTA, width=g)


def _cuadrupedo(d, x, y, t, g, color, cabeza=0.27, cuello=0.0, largo=0.9, alto_c=0.5, patas=0.2,
                cola=None, orejas=None, hocico=None, extra=None, color_patas=None, detras=None):
    """El cuerpo comun: patitas, cuerpo ovalado, cola, cabeza redonda,
    orejas, hocico, ojitos y mofletes. Devuelve el centro y radio de la
    cabeza por si el animal quiere añadir algo."""
    cp = color_patas or color
    by = y - patas*t - alto_c*t*0.4
    bx = x - t*0.08
    # patas de detras (mas oscuras) y de delante
    for k, (dx, f) in enumerate(((-0.3, 0.82), (0.22, 0.82), (-0.18, 1.0), (0.34, 1.0))):
        _pata(d, bx + t*dx*largo, y, t*0.12, t*(patas + alto_c*0.2), _osc(cp, f) if f < 1 else cp, g)
    if cola:
        cola(d, bx - t*largo*0.48, by - t*alto_c*0.1, t, g)
    if detras:
        detras(d, bx, by, t, g)
    _bola(d, [bx - t*largo/2, by - t*alto_c/2, bx + t*largo/2, by + t*alto_c/2], color, g)
    if extra:
        extra(d, bx, by, t, g)
    hx = bx + t*largo*0.42
    hy = by - t*alto_c*0.45 - t*cuello
    if cuello:
        # el cuello: un trazo gordo del color, con su borde, de la cabeza al cuerpo
        a, b = (hx - t*0.04, hy + t*0.06), (bx + t*largo*0.28, by - t*alto_c*0.15)
        d.line([a, b], fill=TINTA, width=int(t*0.2 + 2*g))
        d.line([a, b], fill=color, width=int(t*0.2))
    r = t*cabeza
    if orejas:
        orejas(d, hx, hy, r, t, g, color)
    _bola(d, [hx - r, hy - r, hx + r, hy + r], color, g)
    if hocico:
        hocico(d, hx, hy, r, t, g, color)
    _ojitos(d, hx + r*0.1, hy - r*0.15, r*0.5, g)
    _moflete(d, hx + r*0.62, hy + r*0.25, r*0.17)
    _moflete(d, hx - r*0.45, hy + r*0.25, r*0.17)
    return hx, hy, r


# ---- piezas --------------------------------------------------------------

def _orejas_pico(d, hx, hy, r, t, g, color, alto=0.65):
    for dx in (-0.5, 0.45):
        d.polygon([(hx + r*(dx - 0.3), hy - r*0.6), (hx + r*dx, hy - r*(0.6 + alto)), (hx + r*(dx + 0.3), hy - r*0.6)],
                  fill=color, outline=TINTA)
        d.polygon([(hx + r*(dx - 0.14), hy - r*0.68), (hx + r*dx, hy - r*(0.55 + alto*0.7)), (hx + r*(dx + 0.14), hy - r*0.68)],
                  fill=ROSA)


def _orejas_redondas(d, hx, hy, r, t, g, color, tam=0.38):
    for dx in (-0.6, 0.55):
        _bola(d, [hx + r*dx - r*tam, hy - r*0.85 - r*tam, hx + r*dx + r*tam, hy - r*0.85 + r*tam], color, g, False)
        d.ellipse([hx + r*dx - r*tam*0.5, hy - r*0.85 - r*tam*0.5, hx + r*dx + r*tam*0.5, hy - r*0.85 + r*tam*0.5], fill=ROSA)


def _orejas_caidas(d, hx, hy, r, t, g, color):
    for dx in (-0.85, 0.7):
        d.ellipse([hx + r*dx - r*0.25, hy - r*0.7, hx + r*dx + r*0.25, hy + r*0.25], fill=_osc(color, 0.7),
                  outline=TINTA, width=g)


def _hocico_largo(d, hx, hy, r, t, g, color):
    _bola(d, [hx + r*0.2, hy - r*0.05, hx + r*1.25, hy + r*0.75], _claro(color), g, False)
    for dx in (0.85, 1.05):
        d.ellipse([hx + r*dx - r*0.06, hy + r*0.3, hx + r*dx + r*0.06, hy + r*0.42], fill=TINTA)
    d.arc([hx + r*0.55, hy + r*0.35, hx + r*1.0, hy + r*0.65], 20, 160, fill=TINTA, width=max(2, g//2))


def _hocico_perro(d, hx, hy, r, t, g, color):
    _bola(d, [hx + r*0.35, hy + r*0.05, hx + r*1.15, hy + r*0.7], _claro(color), g, False)
    d.ellipse([hx + r*0.85, hy + r*0.1, hx + r*1.12, hy + r*0.32], fill=TINTA)
    d.arc([hx + r*0.5, hy + r*0.3, hx + r*0.95, hy + r*0.62], 20, 160, fill=TINTA, width=max(2, g//2))


def _hocico_gato(d, hx, hy, r, t, g, color):
    d.polygon([(hx + r*0.32, hy + r*0.22), (hx + r*0.52, hy + r*0.22), (hx + r*0.42, hy + r*0.34)], fill=ROSA, outline=TINTA)
    for k in (-1, 1):
        d.line([(hx + r*0.65, hy + r*0.32), (hx + r*1.35, hy + r*0.32 + k*r*0.18)], fill=TINTA, width=max(2, g//3))
        d.line([(hx + r*0.2, hy + r*0.32), (hx - r*0.5, hy + r*0.32 + k*r*0.18)], fill=TINTA, width=max(2, g//3))


def _hocico_cerdo(d, hx, hy, r, t, g, color):
    d.ellipse([hx + r*0.55, hy, hx + r*1.15, hy + r*0.5], fill=_osc(color, 0.9), outline=TINTA, width=g)
    for dx in (0.75, 0.95):
        d.ellipse([hx + r*dx - r*0.05, hy + r*0.17, hx + r*dx + r*0.05, hy + r*0.33], fill=TINTA)


def _hocico_vaca(d, hx, hy, r, t, g, color):
    _bola(d, [hx + r*0.1, hy + r*0.15, hx + r*1.2, hy + r*0.85], (250, 190, 200), g, False)
    for dx in (0.55, 0.85):
        d.ellipse([hx + r*dx - r*0.06, hy + r*0.38, hx + r*dx + r*0.06, hy + r*0.52], fill=TINTA)


def _cola_pincel(color):
    def cola(d, x, y, t, g):
        d.line([(x, y), (x - t*0.12, y + t*0.15)], fill=TINTA, width=int(g*2.4))
        d.line([(x, y), (x - t*0.12, y + t*0.15)], fill=color, width=int(g*1.2))
        d.ellipse([x - t*0.2, y + t*0.1, x - t*0.06, y + t*0.28], fill=_osc(color, 0.6), outline=TINTA, width=max(2, g//2))
    return cola


def _cola_crin(color):
    def cola(d, x, y, t, g):
        pts = [(x, y), (x - t*0.14, y + t*0.05), (x - t*0.2, y + t*0.25), (x - t*0.1, y + t*0.18), (x - t*0.04, y + t*0.08)]
        d.polygon(pts, fill=color, outline=TINTA)
    return cola


def _cola_rizo(d, x, y, t, g):
    d.arc([x - t*0.16, y - t*0.08, x, y + t*0.08], 30, 330, fill=TINTA, width=g)


def _cola_larga(color):
    def cola(d, x, y, t, g):
        pts = [(x - k*t*0.05, y - t*0.12*math.sin(k*0.6)) for k in range(8)]
        d.line(pts, fill=TINTA, width=int(g*2.4), joint="curve")
        d.line(pts, fill=color, width=int(g*1.2), joint="curve")
    return cola


# ---- los animales ----------------------------------------------------------

def caballo(d, x, y, t, rnd, g, tinta=TINTA):
    c, crin = (190, 125, 75), (110, 65, 40)

    def orejas(d, hx, hy, r, t, g, color):
        _orejas_pico(d, hx, hy, r, t, g, color, alto=0.55)
        for k in range(5):
            cx, cy = hx - r*(0.9 - k*0.15), hy - r*(0.55 + 0.1*math.sin(k)) + k*r*0.05
            d.ellipse([cx - r*0.22, cy - r*0.22, cx + r*0.22, cy + r*0.22], fill=crin, outline=TINTA, width=max(2, g//2))
    hx, hy, r = _cuadrupedo(d, x, y, t, g, c, cabeza=0.24, cuello=0.18, largo=0.88, alto_c=0.42, patas=0.24,
                            cola=_cola_crin(crin), orejas=orejas, hocico=_hocico_largo)


def perro(d, x, y, t, rnd, g, tinta=TINTA):
    c = (225, 175, 110)
    _cuadrupedo(d, x, y, t, g, c, cabeza=0.27, largo=0.78, alto_c=0.45, patas=0.17, cola=_cola_larga(c),
                orejas=_orejas_caidas, hocico=_hocico_perro)


def gato(d, x, y, t, rnd, g, tinta=TINTA):
    c = (245, 165, 80)
    _cuadrupedo(d, x, y, t, g, c, cabeza=0.29, largo=0.72, alto_c=0.42, patas=0.15, cola=_cola_larga(c),
                orejas=_orejas_pico, hocico=_hocico_gato)


def vaca(d, x, y, t, rnd, g, tinta=TINTA):
    c = (250, 250, 248)

    def manchas(d, bx, by, t, g):
        for dx, dy, r in ((-0.22, -0.05, 0.1), (0.08, 0.06, 0.08), (0.2, -0.1, 0.06)):
            d.ellipse([bx + t*dx - t*r, by + t*dy - t*r*0.8, bx + t*dx + t*r, by + t*dy + t*r*0.8], fill=TINTA)

    def orejas(d, hx, hy, r, t, g, color):
        for dx in (-0.55, 0.5):
            d.polygon([(hx + r*dx, hy - r*0.7), (hx + r*(dx + 0.12*(1 if dx > 0 else -1)), hy - r*1.2),
                       (hx + r*(dx + 0.22), hy - r*0.75)], fill=(240, 225, 180), outline=TINTA)
        _orejas_caidas(d, hx, hy, r, t, g, color)
    _cuadrupedo(d, x, y, t, g, c, cabeza=0.26, largo=0.95, alto_c=0.48, patas=0.2, cola=_cola_pincel(c),
                orejas=orejas, hocico=_hocico_vaca, extra=manchas, color_patas=c)


def toro(d, x, y, t, rnd, g, tinta=TINTA):
    c = (70, 60, 60)

    def cuernos(d, hx, hy, r, t, g, color):
        for lado in (-1, 1):
            d.polygon([(hx + lado*r*0.4, hy - r*0.7), (hx + lado*r*1.1, hy - r*1.15), (hx + lado*r*0.6, hy - r*0.55)],
                      fill=(240, 230, 200), outline=TINTA)
    _cuadrupedo(d, x, y, t, g, c, cabeza=0.26, largo=0.95, alto_c=0.5, patas=0.2, cola=_cola_pincel(c),
                orejas=cuernos, hocico=_hocico_vaca)


def cerdo(d, x, y, t, rnd, g, tinta=TINTA):
    c = (250, 175, 190)
    _cuadrupedo(d, x, y, t, g, c, cabeza=0.27, largo=0.85, alto_c=0.5, patas=0.13, cola=_cola_rizo,
                orejas=lambda d, hx, hy, r, t, g, color: _orejas_pico(d, hx, hy, r, t, g, color, alto=0.4),
                hocico=_hocico_cerdo)


def oveja(d, x, y, t, rnd, g, tinta=TINTA):
    lana, cara = (250, 250, 252), (90, 85, 95)
    by = y - t*0.42
    for dx in (-0.25, 0.25):
        _pata(d, x + t*dx, y, t*0.1, t*0.25, cara, g)
    piezas = [(x - t*0.3, by, t*0.2), (x - t*0.05, by - t*0.12, t*0.24), (x + t*0.22, by - t*0.02, t*0.2),
              (x - t*0.05, by + t*0.08, t*0.22), (x - t*0.38, by + t*0.06, t*0.15)]
    for cx, cy, r in piezas:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=lana, outline=TINTA, width=g)
    for cx, cy, r in piezas:
        d.ellipse([cx - r + g, cy - r + g, cx + r - g, cy + r - g], fill=lana)
    hx, hy, r = x + t*0.38, by - t*0.12, t*0.2
    _bola(d, [hx - r, hy - r*1.1, hx + r, hy + r*1.1], cara, g)
    d.ellipse([hx - r*0.6, hy - r*1.35, hx + r*0.3, hy - r*0.65], fill=lana, outline=TINTA, width=max(2, g//2))
    _ojitos(d, hx + r*0.1, hy - r*0.1, r*0.55, g)
    _moflete(d, hx + r*0.55, hy + r*0.4, r*0.18)


def leon(d, x, y, t, rnd, g, tinta=TINTA):
    c, melena = (245, 185, 80), (200, 110, 50)

    def orejas(d, hx, hy, r, t, g, color):
        pts = [(hx + r*(1.55 if k % 2 else 1.25)*math.cos(a), hy + r*(1.55 if k % 2 else 1.25)*math.sin(a))
               for k, a in enumerate([i*math.pi/9 for i in range(18)])]
        d.polygon(pts, fill=melena, outline=TINTA)
        _orejas_redondas(d, hx, hy, r, t, g, color, tam=0.3)
    _cuadrupedo(d, x, y, t, g, c, cabeza=0.25, largo=0.82, alto_c=0.44, patas=0.18, cola=_cola_pincel(c),
                orejas=orejas, hocico=_hocico_gato)


def elefante(d, x, y, t, rnd, g, tinta=TINTA):
    c = (170, 175, 195)

    def trompa(d, hx, hy, r, t, g, color):
        pts = [(hx + r*0.6, hy + r*0.2), (hx + r*1.05, hy + r*0.7), (hx + r*1.0, hy + r*1.3), (hx + r*1.2, hy + r*1.45)]
        d.line(pts, fill=TINTA, width=int(r*0.42 + g*2), joint="curve")
        d.line(pts, fill=color, width=int(r*0.42), joint="curve")

    def orejas(d, hx, hy, r, t, g, color):
        _bola(d, [hx - r*1.3, hy - r*0.8, hx - r*0.1, hy + r*0.8], _claro(color), g, False)
        d.ellipse([hx - r*1.1, hy - r*0.55, hx - r*0.3, hy + r*0.55], fill=ROSA)
    _cuadrupedo(d, x, y, t, g, c, cabeza=0.3, largo=0.95, alto_c=0.55, patas=0.18, cola=_cola_pincel(c),
                orejas=orejas, hocico=trompa)


def camello(d, x, y, t, rnd, g, tinta=TINTA):
    c = (220, 175, 110)

    def jorobas(d, bx, by, t, g):
        for dx in (-0.18, 0.12):
            _bola(d, [bx + t*dx - t*0.15, by - t*0.36, bx + t*dx + t*0.15, by - t*0.02], c, g)
    _cuadrupedo(d, x, y, t, g, c, cabeza=0.2, cuello=0.22, largo=0.85, alto_c=0.38, patas=0.3,
                cola=_cola_pincel(c), detras=jorobas,
                orejas=lambda d, hx, hy, r, t, g, color: _orejas_redondas(d, hx, hy, r, t, g, color, tam=0.22),
                hocico=_hocico_largo)


def conejo(d, x, y, t, rnd, g, tinta=TINTA):
    c = (240, 238, 245)
    by = y - t*0.3
    _bola(d, [x - t*0.33, by - t*0.3, x + t*0.25, by + t*0.28], c, g)
    d.ellipse([x - t*0.44, by - t*0.02, x - t*0.24, by + t*0.18], fill=BLANCO, outline=TINTA, width=g)
    for dx in (-0.15, 0.12):
        _pata(d, x + t*dx, y, t*0.14, t*0.08, c, g)
    hx, hy, r = x + t*0.15, by - t*0.38, t*0.22
    for dx in (-0.35, 0.25):
        _bola(d, [hx + r*dx - r*0.25, hy - r*2.5, hx + r*dx + r*0.25, hy - r*0.6], c, g, False)
        d.ellipse([hx + r*dx - r*0.12, hy - r*2.2, hx + r*dx + r*0.12, hy - r*0.9], fill=ROSA)
    _bola(d, [hx - r, hy - r, hx + r, hy + r], c, g)
    _ojitos(d, hx + r*0.1, hy - r*0.15, r*0.5, g)
    d.ellipse([hx + r*0.3, hy + r*0.2, hx + r*0.5, hy + r*0.35], fill=ROSA)
    _moflete(d, hx + r*0.65, hy + r*0.35, r*0.17)


def rata(d, x, y, t, rnd, g, tinta=TINTA):
    c = (175, 175, 185)
    _cuadrupedo(d, x, y, t, g, c, cabeza=0.24, largo=0.78, alto_c=0.38, patas=0.08, cola=_cola_larga((240, 170, 180)),
                orejas=lambda d, hx, hy, r, t, g, color: _orejas_redondas(d, hx, hy, r, t, g, color, tam=0.45),
                hocico=_hocico_gato)


def pajaro(d, x, y, t, rnd, g, tinta=TINTA):
    c = (90, 165, 235)
    cy, r = y - t*0.46, t*0.36
    for dx in (-0.08, 0.08):
        d.line([(x + t*dx, cy + r*0.9), (x + t*dx, y)], fill=(240, 150, 50), width=max(3, g))
    d.polygon([(x - r*0.85, cy), (x - r*1.45, cy - r*0.35), (x - r*1.35, cy + r*0.25)], fill=_osc(c), outline=TINTA)
    _bola(d, [x - r, cy - r, x + r, cy + r], c, g)
    d.ellipse([x - r*0.75, cy + r*0.05, x - r*0.05, cy + r*0.5], fill=_osc(c, 0.88), outline=TINTA, width=max(2, g//2))
    d.polygon([(x + r*0.85, cy - r*0.15), (x + r*1.35, cy + r*0.02), (x + r*0.85, cy + r*0.2)], fill=(250, 180, 60), outline=TINTA)
    _ojitos(d, x + r*0.3, cy - r*0.3, r*0.38, g)
    _moflete(d, x + r*0.55, cy + r*0.15, r*0.14)


def pez(d, x, y, t, rnd, g, tinta=TINTA):
    c = (250, 150, 60)
    cy = y - t*0.4
    d.polygon([(x - t*0.3, cy), (x - t*0.62, cy - t*0.28), (x - t*0.58, cy + t*0.28)], fill=_osc(c), outline=TINTA)
    d.polygon([(x - t*0.05, cy - t*0.3), (x + t*0.08, cy - t*0.48), (x + t*0.2, cy - t*0.28)], fill=_osc(c), outline=TINTA)
    _bola(d, [x - t*0.42, cy - t*0.32, x + t*0.48, cy + t*0.32], c, g)
    _ojitos(d, x + t*0.22, cy - t*0.08, t*0.12, g)
    d.arc([x + t*0.25, cy + t*0.02, x + t*0.4, cy + t*0.14], 20, 160, fill=TINTA, width=max(2, g//2))
    _moflete(d, x + t*0.18, cy + t*0.1, t*0.04)


def gallina(d, x, y, t, rnd, g, tinta=TINTA):
    c = (252, 250, 245)
    cy = y - t*0.42
    for dx in (-0.08, 0.08):
        d.line([(x + t*dx, cy + t*0.25), (x + t*dx, y)], fill=(240, 150, 50), width=max(3, g))
    d.polygon([(x - t*0.3, cy - t*0.05), (x - t*0.48, cy - t*0.3), (x - t*0.22, cy - t*0.2)], fill=c, outline=TINTA)
    _bola(d, [x - t*0.36, cy - t*0.3, x + t*0.3, cy + t*0.3], c, g)
    hx, hy, r = x + t*0.2, cy - t*0.32, t*0.17
    for k in range(3):
        d.ellipse([hx - r*0.5 + k*r*0.35, hy - r*1.35, hx - r*0.1 + k*r*0.35, hy - r*0.85], fill=(230, 60, 60), outline=TINTA)
    _bola(d, [hx - r, hy - r, hx + r, hy + r], c, g)
    d.polygon([(hx + r*0.85, hy - r*0.1), (hx + r*1.35, hy + r*0.08), (hx + r*0.85, hy + r*0.25)], fill=(250, 180, 60), outline=TINTA)
    _ojitos(d, hx + r*0.1, hy - r*0.15, r*0.5, g)
    _moflete(d, hx + r*0.55, hy + r*0.3, r*0.17)


def rana(d, x, y, t, rnd, g, tinta=TINTA):
    c = (120, 205, 100)
    for dx in (-0.3, 0.3):
        _bola(d, [x + t*dx - t*0.18, y - t*0.12, x + t*dx + t*0.18, y], c, g, False)
    _bola(d, [x - t*0.42, y - t*0.65, x + t*0.42, y - t*0.05], c, g)
    for dx in (-0.2, 0.2):
        _bola(d, [x + t*dx - t*0.14, y - t*0.8, x + t*dx + t*0.14, y - t*0.52], c, g, False)
    _ojitos(d, x, y - t*0.66, t*0.36, g, mira=0.0)
    d.arc([x - t*0.22, y - t*0.5, x + t*0.22, y - t*0.25], 20, 160, fill=TINTA, width=g)
    _moflete(d, x - t*0.27, y - t*0.38, t*0.05)
    _moflete(d, x + t*0.27, y - t*0.38, t*0.05)


ANIMALES = {
    "caballo": caballo, "perro": perro, "gato": gato, "vaca": vaca, "toro": toro, "cerdo": cerdo,
    "oveja": oveja, "leon": leon, "elefante": elefante, "camello": camello, "conejo": conejo, "rata": rata,
    "pajaro": pajaro, "pez": pez, "gallina": gallina, "rana": rana,
}
