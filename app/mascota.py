"""LA MASCOTA DE WHY THOUGH: la gota morada con un "?" de pelo.

Ella, viendo canales de explicar cosas: "hay muchos canales muy parecidos,
hay que distinguirnos". La Psicologia Invisible tiene su personaje y lo
reconoces de un vistazo; este es el nuestro. Y: "una escena tiene que estar
completamente en movimiento todo el rato; cuando el personaje para, sigue
otra escena: tiene que ser muy dinamico". Asi que la mascota NUNCA esta
quieta: respira estirandose y aplastandose, se balancea, parpadea, y encima
hace su accion (entrar saltando, pensar, asustarse, reirse...), dibujada a
25 fotogramas por segundo.

Una accion es una funcion del segundo t a la postura: cuanto se mueve de su
sitio, cuanto se levanta del suelo, cuanto se estira, cuanto se inclina,
los brazos (angulo y codo), la fase de las piernas y la cara.
"""
import math
import random

from PIL import Image, ImageDraw

TINTA = (30, 30, 34)
AMARILLO = (250, 200, 70)
MORADO = (180, 150, 235)
# La mascota del canal: su forma y su color. Hay dos probadas: la judia
# amarilla y la gota morada.
NOMBRE = "Mokordo"        # el nombre que le puso ella
FORMA = "gota"            # ella: "me gusta mas el morado"
COLOR = MORADO


def _oscuro(c, f=0.82):
    return tuple(int(v*f) for v in c)


def _suave(t):
    t = min(1.0, max(0.0, t))
    return t*t*(3 - 2*t)


def _medidas(h, forma):
    """(ancho, alto) del cuerpo."""
    return (h*0.24, h*0.9) if forma == "judia" else (h*0.36, h*0.78)


def _cuerpo(alto, ancho, forma="judia", n=72):
    """El cuerpo en coordenadas locales, (0, 0) = centro de abajo: la judia
    (alta) o la gota (rechoncha, mas estrecha arriba)."""
    pts = []
    ex = 2.6 if forma == "judia" else 2.2
    for i in range(n):
        a = 2*math.pi*i/n
        sx, sy = math.sin(a), -math.cos(a)
        x = math.copysign(abs(sx)**(2/ex), sx)
        y = math.copysign(abs(sy)**(2/ex), sy)
        t = (y + 1)/2
        r = ancho*(1.08 - 0.22*t) if forma == "judia" else ancho*(1.1 - 0.35*t**1.6)
        pts.append((x*r, -alto*t))
    return pts


def _transforma(p, cx, base, estira, inclina):
    x, y = p[0]/math.sqrt(estira), p[1]*estira
    a = math.radians(inclina)
    return (cx + x*math.cos(a) - y*math.sin(a), base + x*math.sin(a) + y*math.cos(a))


# Donde salen los granos (en el cuerpo, lejos de la cara), por orden.
_GRANOS = ((-0.62, 0.3), (0.58, 0.68), (-0.35, 0.82), (0.66, 0.25), (-0.7, 0.55), (0.3, 0.18),
           (0.12, 0.88), (-0.55, 0.12), (0.72, 0.48), (-0.2, 0.2), (0.45, 0.85))


def _desgaste(img, d, T, centro, r, g, h, ancho, alto, dg):
    """Lo que la droga le va dejando en la cara y en el cuerpo."""
    fino = max(2, int(g*0.6))
    ojera = tuple(int(v) for v in (95 - 20*dg, 70 - 20*dg, 105 - 10*dg))
    for lado in (-1, 1):
        ex, ey = centro[0] + lado*r*0.33, centro[1] - r*0.12
        if dg > 0.1:       # las ojeras, cada vez mas marcadas
            ancha = max(2, int(g*(0.4 + 1.0*dg)))
            d.arc([ex - r*0.24, ey - r*0.1, ex + r*0.24, ey + r*0.32], 15, 165, fill=ojera, width=ancha)
            if dg > 0.55:
                d.arc([ex - r*0.26, ey, ex + r*0.26, ey + r*0.44], 25, 155, fill=ojera, width=max(2, ancha//2))
        if dg > 0.5:       # los ojos rojos: venitas
            for k in (-1, 1):
                d.line([(ex + lado*r*0.2, ey + k*r*0.04), (ex + lado*r*0.3, ey + k*r*0.09)], fill=(215, 50, 50),
                       width=max(1, fino//2 + 1))
        if dg > 0.35:      # las mejillas hundidas
            mx, my = centro[0] + lado*r*0.72, centro[1] + r*0.25
            d.arc([mx - r*0.14, my - r*0.25, mx + r*0.14, my + r*0.25], 90 + lado*70 - 45, 90 + lado*70 + 45,
                  fill=_oscuro((150, 140, 150), 0.8), width=fino)
    for lx, ly in _GRANOS[:int(round(dg*len(_GRANOS)))]:
        gx, gy = T((lx*ancho, -ly*alto))
        rg = h*0.016
        d.ellipse([gx - rg, gy - rg, gx + rg, gy + rg], fill=(225, 80, 80), outline=(160, 40, 40), width=1)
        d.ellipse([gx - rg*0.35, gy - rg*0.55, gx + rg*0.15, gy - rg*0.05], fill=(255, 210, 200))
    if dg > 0.7:           # el sudor frio
        sx, sy = centro[0] - r*1.05, centro[1] - r*0.55
        gota = [(sx, sy - r*0.28), (sx + r*0.13, sy), (sx, sy + r*0.12), (sx - r*0.13, sy)]
        d.polygon(gota, fill=(150, 205, 245), outline=TINTA)


BRAZOS = {}      # el ultimo dibujado: lado -> (codo, mano), para orientar lo que lleva


def pie_levantado(cx, pie_y, h, forma, lado):
    """Donde queda el pie que levanta hacia delante (para hacerse cosquillas)."""
    ancho, _alto = _medidas(h, forma)
    return (cx + lado*(ancho*1.25 + h*0.1), pie_y - h*0.16)


def _hasta(hombro, punto, lado, h):
    """El brazo (angulo, codo) para que la mano llegue a `punto` (o lo mas
    cerca que pueda): dos tramos, el codo hacia abajo."""
    l1, l2 = h*0.15, h*0.13
    dx, dy = (punto[0] - hombro[0])*lado, punto[1] - hombro[1]
    d = min(max(math.hypot(dx, dy), (l1 + l2)*0.3), (l1 + l2)*0.985)
    fi = math.atan2(dy, dx)
    codo = math.pi - math.acos(max(-1.0, min(1.0, (l1*l1 + l2*l2 - d*d)/(2*l1*l2))))
    alfa = math.acos(max(-1.0, min(1.0, (l1*l1 + d*d - l2*l2)/(2*l1*d))))
    return math.degrees(fi + alfa), -math.degrees(codo)


def dibuja(img, cx, suelo, h, gesto="neutro", estira=1.0, inclina=0.0, brazos=((60, 20), (60, 20)),
           parpadeo=False, piernas=None, levanta=0.0, color=None, forma=None, pelo="?", gafas=False,
           bigote=False, alcanza=None, pie_arriba=None, desgaste=0.0, mira=None, habla=None, pelo_giro=0.0):
    """Pinta la mascota. Devuelve la cabeza (cx, cy, radio, lado) para los
    efectos de garabato. brazos: (angulo, codo) por lado en grados; 0 es
    horizontal hacia fuera y + hacia abajo.
    alcanza: {lado: (x, y)} = esa mano va a ese punto (hacer cosquillas,
    tocar, coger...); pie_arriba: el lado del pie que levanta.
    desgaste: 0-1, lo que se le va quedando el cuerpo (los videos de "y si
    Mokordo tomara..."): mas delgado y palido, ojeras, granos, mejillas
    hundidas, ojos rojos, sudor, el "?" mustio."""
    from . import garabato
    d = ImageDraw.Draw(img)
    g = max(4, int(h*0.017))
    color = color or COLOR
    forma = forma or FORMA
    ancho, alto = _medidas(h, forma)
    dg = min(1.0, max(0.0, float(desgaste or 0.0)))
    if dg:
        ancho *= 1 - 0.4*dg
        alto *= 1 + 0.04*dg
        color = tuple(int(c + (gris - c)*0.6*dg) for c, gris in zip(color, (168, 166, 150)))
    pie_y = suelo - levanta
    base = pie_y - h*0.07
    T = lambda p: _transforma(p, cx, base, estira, inclina)
    pts = [T(p) for p in _cuerpo(alto, ancho, forma)]
    k = max(0.3, 1 - levanta/(h*0.8))
    d.ellipse([cx - ancho*1.1*k, suelo - h*0.02*k, cx + ancho*1.1*k, suelo + h*0.02*k], fill=(222, 218, 210))
    for lado in (-1, 1):
        paso = math.sin(piernas + (0 if lado < 0 else math.pi))*h*0.05 if piernas is not None else 0.0
        arriba = T((lado*ancho*0.42, 0))
        pie = (cx + lado*ancho*0.42 + paso, pie_y - max(0.0, -paso)*0.6)
        if pie_arriba == lado:
            continue          # el pie levantado va delante del cuerpo: luego
        d.line([arriba, pie], fill=TINTA, width=int(g*2.6))
        d.line([arriba, pie], fill=color, width=int(g*1.3))
        d.ellipse([pie[0] - h*0.05 + lado*h*0.015, pie[1] - h*0.03, pie[0] + h*0.05 + lado*h*0.015, pie[1] + h*0.012],
                  fill=_oscuro(color, 0.7), outline=TINTA, width=g)
    # el cuerpo, con su sombra y su brillo dentro del contorno
    # Solo en la caja del cuerpo, no a pantalla entera: con varios
    # personajes a 25 por segundo, cada lienzo de 1920x1080 se notaba.
    x0, y0 = int(min(p[0] for p in pts)) - 2, int(min(p[1] for p in pts)) - 2
    x1, y1 = int(max(p[0] for p in pts)) + 3, int(max(p[1] for p in pts)) + 3
    loc = [(px - x0, py - y0) for px, py in pts]
    capa = Image.new("RGB", (max(1, x1 - x0), max(1, y1 - y0)), color)
    dc = ImageDraw.Draw(capa)
    for (a, b), relleno in ((((ancho*0.25, 0), (ancho*1.9, -alto*1.05)), _oscuro(color, 0.88)),
                            (((-ancho*0.62, -alto*0.88), (-ancho*0.42, -alto*0.66)),
                             tuple(min(255, int(v*1.1 + 25)) for v in color))):
        p0, p1 = T(a), T(b)
        dc.ellipse([min(p0[0], p1[0]) - x0, min(p0[1], p1[1]) - y0, max(p0[0], p1[0]) - x0, max(p0[1], p1[1]) - y0],
                   fill=relleno)
    mascara = Image.new("L", capa.size, 0)
    ImageDraw.Draw(mascara).polygon(loc, fill=255)
    img.paste(capa, (x0, y0), mascara)
    d = ImageDraw.Draw(img)
    d.line(pts + [pts[0]], fill=TINTA, width=g, joint="curve")
    if pie_arriba in (-1, 1):
        # La pierna levantada hacia delante, por encima del cuerpo, con la
        # planta a la vista (para hacerse cosquillas en el pie).
        lado = pie_arriba
        arriba = T((lado*ancho*0.55, -alto*0.12))
        pie = pie_levantado(cx, pie_y, h, forma, lado)
        d.line([arriba, pie], fill=TINTA, width=int(g*2.6))
        d.line([arriba, pie], fill=color, width=int(g*1.3))
        d.ellipse([pie[0] - h*0.035, pie[1] - h*0.055, pie[0] + h*0.035, pie[1] + h*0.055],
                  fill=_oscuro(color, 0.7), outline=TINTA, width=g)
    # Los brazos DELANTE del cuerpo: detras, el que saluda o el que se
    # levanta quedaba escondido.
    manos = []
    BRAZOS.clear()
    for lado, (ang, codo) in zip((-1, 1), brazos):
        hombro = T((lado*ancho*1.0, -alto*0.42))
        if alcanza and alcanza.get(lado):
            ang, codo = _hasta(hombro, alcanza[lado], lado, h)
        a1 = math.radians(ang)
        c = (hombro[0] + lado*math.cos(a1)*h*0.15, hombro[1] + math.sin(a1)*h*0.15)
        a2 = math.radians(ang + codo)
        mano = (c[0] + lado*math.cos(a2)*h*0.13, c[1] + math.sin(a2)*h*0.13)
        BRAZOS[lado] = (c, mano)
        d.line([hombro, c, mano], fill=TINTA, width=int(g*2.6), joint="curve")
        d.line([hombro, c, mano], fill=color, width=int(g*1.3), joint="curve")
        d.ellipse([mano[0] - g*1.7, mano[1] - g*1.7, mano[0] + g*1.7, mano[1] + g*1.7], fill=color, outline=TINTA,
                  width=max(2, g//2))
        manos.append(mano)
    top = T((0, -alto))
    if pelo == "?":       # solo Mokordo
        garabato._letrero(img, "?", (top[0] + h*(0.02 + 0.06*dg), top[1] - h*(0.07 - 0.03*dg)), h*0.2*(1 - 0.2*dg),
                          TINTA, -12 - 55*dg + inclina*0.5 + pelo_giro)
    elif pelo == "moño":
        rr = h*0.07
        d.ellipse([top[0] - rr, top[1] - rr*1.7, top[0] + rr, top[1] + rr*0.3], fill=_oscuro(color, 0.75),
                  outline=TINTA, width=g)
    elif pelo == "brote":
        d.line([top, (top[0] + h*0.01, top[1] - h*0.07)], fill=TINTA, width=g)
        for lado in (-1, 1):
            d.ellipse([top[0] + h*0.01 + (lado - 1)*h*0.035, top[1] - h*0.1, top[0] + h*0.01 + (lado + 1)*h*0.035,
                       top[1] - h*0.06], fill=(110, 190, 90), outline=TINTA, width=max(2, g//2))
    centro = T((h*0.02, -alto*(0.7 if forma == "judia" else 0.58)))
    r = h*0.17
    garabato._cara_expresiva(d, centro, r, g, random.Random(1), gesto, tinta=TINTA, mira=mira, habla=habla)
    if dg:
        _desgaste(img, d, T, centro, r, g, h, ancho, alto, dg)
    if gafas:
        for lado in (-1, 1):
            ex, ey = centro[0] + lado*r*0.33, centro[1] - r*0.12
            d.ellipse([ex - r*0.26, ey - r*0.28, ex + r*0.26, ey + r*0.26], outline=TINTA, width=max(2, g//2))
        d.line([(centro[0] - r*0.07, centro[1] - r*0.14), (centro[0] + r*0.07, centro[1] - r*0.14)], fill=TINTA,
               width=max(2, g//2))
    if bigote:
        for lado in (-1, 1):
            d.chord([centro[0] + (lado - 1)*r*0.22, centro[1] + r*0.12, centro[0] + (lado + 1)*r*0.22,
                     centro[1] + r*0.4], 180, 360, fill=(245, 245, 245), outline=TINTA, width=max(2, g//2))
    if parpadeo and gesto not in ("contento", "riendo", "bostezo"):
        for lado in (-1, 1):
            ex, ey = centro[0] + lado*r*0.33, centro[1] - r*0.12
            d.ellipse([ex - r*0.19, ey - r*0.22, ex + r*0.19, ey + r*0.2], fill=color)
            d.line([(ex - r*0.15, ey), (ex + r*0.15, ey)], fill=TINTA, width=max(3, g))
    return (centro[0], centro[1], r*1.25, 1), manos


# ---------------------------------------------------------------------------
# Las acciones. Cada una: t (segundos desde que empieza el plano), dur (lo que
# dura el plano), lado (1 mira a la derecha, -1 a la izquierda) -> postura.
# ---------------------------------------------------------------------------

def _base(t):
    """Lo que hace siempre, encima de cualquier accion: respirar, balancearse
    y parpadear. Para que nunca este quieta."""
    return {"estira": 1 + 0.04*math.sin(2*math.pi*t/1.4), "inclina": 5*math.sin(t*1.7),
            "parpadeo": (t % 3.1) < 0.12}


# MUCHO MAS MOVIMIENTO ("hay que darle mas movimiento, mucho mas"): lo que
# hace cada accion, exagerado, para que se note cual es.
_EXAGERA = 2.4


def _entra(t, dur, lado):
    llega = 1.4
    s = min(1.0, t/llega)
    fase = t*7.5
    fin = 1 - s**3
    p = {"dx": -lado*0.9*(1 - _suave(s)), "levanta": abs(math.sin(fase))*0.28*fin, "gesto": "contento",
         "brazos": ((-40 + 30*math.sin(fase), 50), (-40 - 30*math.sin(fase), 50)), "inclina": 8*math.sin(fase)*fin}
    contacto = 1 - abs(math.sin(fase))
    p["estira"] = 1 + 0.18*(1 - contacto)*fin - 0.2*max(0.0, contacto - 0.85)/0.15*fin
    if t > llega:
        u = t - llega
        p.update(estira=1 + 0.15*math.sin(u*14)*math.exp(-u*4), gesto="sorpresa", levanta=0, inclina=0,
                 brazos=((70, -20), (-60, -60)))
    return p


def _salta(t, dur, lado):
    ciclo = t % 0.8
    u = ciclo/0.8
    levanta = max(0.0, math.sin(min(math.pi, u*math.pi*1.4)))*0.32
    estira = 1.18 if 0.05 < u < 0.65 else 0.82
    polvo = max(0.0, 1 - (u - 0.68)/0.25) if u > 0.68 and t > 0.7 else 0.0
    return {"levanta": levanta, "estira": estira, "gesto": "riendo", "brazos": ((-80, -10), (-80, -10)),
            "polvo": polvo}


def _piensa(t, dur, lado):
    rasca = math.sin(t*12)
    br = ((40, 40), (-125 + 10*rasca, 60)) if lado > 0 else ((-125 + 10*rasca, 60), (40, 40))
    return {"dx": 0.03*math.sin(t*2), "inclina": -6*lado + 3*math.sin(t*2), "gesto": "pensativo", "brazos": br,
            "puntos": True}


def _asusta(t, dur, lado):
    retro = min(1.0, t/1.2)
    return {"dx": -lado*0.25*_suave(retro), "temblor": 0.025*math.sin(t*60), "gesto": "asustado", "sudor": True,
            "brazos": ((-110, 70), (-110, 70)), "inclina": -8*lado, "piernas": t*14 if t < 1.2 else None,
            "estira": 0.95}


def _rie(t, dur, lado):
    va = math.sin(t*10)
    return {"dx": 0.03*math.sin(t*18), "levanta": abs(math.sin(t*9))*0.07, "estira": 1 + 0.08*math.sin(t*18),
            "inclina": 10*math.sin(t*9), "gesto": "riendo", "brazos": ((-20 + 25*va, 90), (-20 - 25*va, 90))}


def _senala(t, dur, lado):
    golpe = math.sin(t*5)
    estirado = (-15 + 6*golpe, 5)
    br = ((55, 25), estirado) if lado > 0 else (estirado, (55, 25))
    return {"gesto": "contento", "brazos": br, "levanta": max(0.0, math.sin(t*5))*0.03, "inclina": 5*lado}


def _anda(t, dur, lado):
    s = min(1.0, t/max(1.0, dur))
    return {"dx": lado*(-0.35 + 0.7*s), "piernas": t*10, "levanta": abs(math.sin(t*10))*0.02,
            "brazos": ((50 + 25*math.sin(t*10), 20), (50 - 25*math.sin(t*10), 20)), "gesto": "contento",
            "inclina": 4*lado}


def _corre(t, dur, lado):
    s = min(1.0, t/max(1.0, dur*0.8))
    return {"dx": lado*(-0.8 + 1.4*s), "piernas": t*22, "levanta": abs(math.sin(t*22))*0.05,
            "brazos": ((10 + 50*math.sin(t*22), -40), (10 - 50*math.sin(t*22), -40)), "gesto": "grito",
            "inclina": 14*lado, "rayas": True}


def _encoge(t, dur, lado):
    u = (math.sin(t*4) + 1)/2
    return {"gesto": "neutro", "brazos": ((10 - 30*u, -70), (10 - 30*u, -70)), "estira": 0.96 + 0.04*u,
            "inclina": 6*math.sin(t*2)}


def _triste(t, dur, lado):
    return {"gesto": "triste", "estira": 0.9 + 0.02*math.sin(t*2), "inclina": 4*math.sin(t*1.2),
            "brazos": ((80, 5), (80, 5)), "dx": 0.01*math.sin(t*1.2)}


def _baila(t, dur, lado):
    v = math.sin(t*6)
    return {"dx": 0.06*v, "inclina": 14*v, "levanta": abs(math.cos(t*6))*0.06, "gesto": "riendo",
            "brazos": ((-70 + 50*v, 30), (-70 - 50*v, 30)), "piernas": t*12}


def _saluda(t, dur, lado):
    ola = math.sin(t*9)
    br = ((70, 10), (-100 + 20*ola, -30)) if lado > 0 else ((-100 + 20*ola, -30), (70, 10))
    return {"gesto": "contento", "brazos": br, "levanta": max(0.0, math.sin(t*4))*0.02}


def _explica(t, dur, lado):
    """La de por defecto: habla con las manos, que no se quede quieta."""
    a = math.sin(t*3.2)
    b = math.sin(t*3.2 + 1.7)
    return {"gesto": "contento" if int(t/1.6) % 2 else "neutro",
            "brazos": ((0 + 75*a, -45 + 50*b), (0 + 75*b, -45 + 50*a)),
            "inclina": 8*math.sin(t*1.6), "dx": 0.12*math.sin(t*1.1), "piernas": t*8 if math.cos(t*1.1) > 0.6 else None}


def _mareo(t, dur, lado):
    return {"gesto": "mareado", "inclina": 18*math.sin(t*3), "dx": 0.05*math.sin(t*3),
            "brazos": ((-30 + 30*math.sin(t*5), 60), (-30 - 30*math.sin(t*5), 60))}


def _duerme(t, dur, lado):
    return {"gesto": "bostezo" if (t % 5) < 1.2 else "contento", "estira": 1 + 0.05*math.sin(t*1.8),
            "brazos": ((85, 0), (85, 0)), "inclina": 6, "efecto": "zzz"}


def _tose(t, dur, lado):
    """Tose: cada poco un golpe de tos que le dobla (y le salen nubecitas)."""
    u = (t % 1.1)/1.1
    golpe = math.exp(-((u - 0.15)/0.07)**2) + 0.7*math.exp(-((u - 0.4)/0.07)**2)
    return {"gesto": "grito" if golpe > 0.4 else "triste", "estira": 1 - 0.14*golpe, "inclina": 16*golpe*lado,
            "brazos": ((70 - 120*golpe, 60), (70, 10)), "tos": golpe}


def _borracho(t, dur, lado):
    """Borracho: se tambalea, da traspies y le da hipo."""
    v = math.sin(t*1.7)
    return {"gesto": "contento" if int(t/2.2) % 2 else "sorpresa", "dx": 0.12*v, "inclina": 18*math.sin(t*1.3),
            "piernas": t*5 if abs(v) > 0.6 else None, "brazos": ((-30 + 40*v, 50), (-30 - 40*v, 50)),
            "hipo": (t % 1.7) < 0.5, "rojo": True}


ACCIONES = {
    "entra": (_entra, "enters hopping from the side and stops, surprised (first shot of a section)"),
    "explica": (_explica, "talks with its hands (the default)"),
    "piensa": (_piensa, "scratches its head, thinking"),
    "senala": (_senala, "points at something on the page (put the thing on the side it faces)"),
    "salta": (_salta, "jumps for joy: an idea, a discovery, good news"),
    "rie": (_rie, "laughs, bouncing"),
    "asusta": (_asusta, "gets scared: shakes and backs away"),
    "anda": (_anda, "walks across the page"),
    "corre": (_corre, "runs across, in a hurry or fleeing"),
    "encoge": (_encoge, "shrugs: who knows?"),
    "triste": (_triste, "sad, slumped"),
    "baila": (_baila, "dances, celebrating"),
    "saluda": (_saluda, "waves hello or goodbye"),
    "mareo": (_mareo, "dizzy, confused, wobbling"),
    "duerme": (_duerme, "sleeps, snoring (zzz)"),
    "tose": (_tose, "coughs hard, bent over (smoke, sick)"),
    "borracho": (_borracho, "drunk: staggers, sways, hiccups (alcohol videos only)"),
}


def postura(accion: str, t: float, dur: float, lado: int = 1) -> dict:
    f = ACCIONES.get(accion, ACCIONES["explica"])[0]
    p = _base(t)
    propia = f(t, dur, lado)
    p["estira"] = p["estira"]*(1 + (propia.pop("estira", 1.0) - 1)*_EXAGERA)
    p["inclina"] = p["inclina"] + propia.pop("inclina", 0.0)*_EXAGERA
    p.update(propia)
    p["levanta"] = min(0.32, p.get("levanta", 0.0)*_EXAGERA)    # que no se salga por arriba
    # (Los saltitos de relleno, fuera: "sale el monigote botando todo el
    # rato y no se diferencia una escena de otra". Cada accion se mueve a su
    # manera y ya esta.)
    p["estira"] = min(1.4, max(0.66, p["estira"]))
    p["inclina"] = min(35.0, max(-35.0, p["inclina"]))
    return p


# ---------------------------------------------------------------------------
# LAS ENTRADAS ("que los personajes aparezcan de las paredes rebotando, que
# sea curioso visualmente"): al empezar una escena nueva cada personaje
# llega a su manera, y luego ya hace su accion.
#   pared:  sale disparado del borde, se pasa de largo y vuelve rebotando
#   cae:    cae desde arriba y bota como una pelota hasta quedarse
#   muelle: sale del suelo aplastado y se estira como un muelle
# ---------------------------------------------------------------------------
ENTRADAS = ("pared", "cae", "muelle")
DURA_ENTRADA = 1.5


def tipo_entrada(semilla: int) -> str:
    return ENTRADAS[semilla % len(ENTRADAS)]


def _botes(t, alto, caida=0.42, rebote=0.42):
    """Una pelota que cae desde `alto` y bota: (altura, golpe), donde golpe
    es lo fuerte que acaba de tocar el suelo (para aplastarla)."""
    g = 2*alto/caida**2
    if t < caida:
        return alto - g*t*t/2, 0.0
    t -= caida
    v = g*caida
    golpe = 1.0
    for _ in range(5):
        v *= rebote
        vuelo = 2*v/g
        if t < vuelo:
            return v*t - g*t*t/2, golpe*math.exp(-t*16)
        t -= vuelo
        golpe *= rebote
    return 0.0, 0.0


def entrada(p: dict, tipo: str, t: float, x: float, w: int, h: float, suelo: float) -> dict:
    """La postura p, retocada por la entrada en su segundo t (desde que
    empieza a entrar). dx y levanta van en altos del personaje."""
    if t >= DURA_ENTRADA:
        return p
    t = max(0.0, t)
    p = dict(p)
    if tipo == "pared":
        izquierda = x < 0.5
        lejos = ((x*w) if izquierda else ((1 - x)*w))/h + 0.7
        signo = -1 if izquierda else 1
        d = signo*lejos*math.exp(-4.2*t)*math.cos(8.5*t)
        salto = abs(math.sin(t*11))
        apaga = math.exp(-2.2*t)
        p["dx"] = p.get("dx", 0.0)*(1 - apaga) + d
        p["levanta"] = salto*0.4*apaga
        p["estira"] = p["estira"]*(1 + 0.25*apaga*(salto - 0.5)) - 0.3*apaga*(1 - salto)**6
        p["inclina"] = p["inclina"] + signo*28*math.exp(-3*t)*math.sin(8.5*t + 1.2)
        if t < 0.6:
            p["piernas"] = t*24
    elif tipo == "cae":
        alto = suelo/h + 0.3
        sube, golpe = _botes(t, alto)
        cayendo = t < 0.42
        p["levanta"] = sube + p.get("levanta", 0.0)*min(1.0, t/DURA_ENTRADA)
        p["estira"] = p["estira"]*(1.25 if cayendo else 1.0) - 0.42*golpe
        p["inclina"] = p["inclina"] + 10*math.exp(-3*t)*math.sin(t*14)
        p["brazos"] = ((-120, 60), (-120, 60)) if cayendo else p.get("brazos")
        p["gesto"] = "sorpresa" if t < 0.7 else p.get("gesto")
        p["polvo"] = max(p.get("polvo", 0.0), min(1.0, golpe*1.5))
    else:  # muelle
        crece = 1 - math.exp(-5.5*t)*math.cos(13*t)
        p["estira"] = max(0.55, p["estira"]*crece)
        p["inclina"] = p["inclina"] + 18*math.exp(-3.5*t)*math.sin(t*19)
        p["levanta"] = p.get("levanta", 0.0) + max(0.0, math.sin(min(math.pi, (t - 0.25)*5)))*0.25*(t > 0.25)
        p["brazos"] = ((-100, -60), (-100, -60)) if 0.25 < t < 0.8 else p.get("brazos")
    if not p.get("brazos"):
        p.pop("brazos", None)
    return p


def _cansado(gesto, dg):
    """Muy desgastado ya no sonrie por defecto."""
    if dg > 0.6 and gesto in ("contento", "riendo", "neutro"):
        return "triste"
    if dg > 0.3 and gesto in ("contento", "riendo"):
        return "neutro"
    return gesto


def estado_mascota(mascota: dict, t: float, dur: float, suelo: float, w: int, h_img: int) -> dict:
    """Como esta Mokordo en el segundo t (sin pintarlo todavia: antes se le
    puede retocar, para que haga algo con otro)."""
    lado = -1 if mascota.get("espejo") else 1
    accion = str(mascota.get("accion") or "explica").lower()
    if accion == "entra" and mascota.get("_ya"):
        accion = "explica"          # ya estaba: no vuelve a entrar
    p = postura(accion, t, dur, lado)
    h = h_img*float(mascota.get("tam") or 0.5)
    if not mascota.get("_ya") and accion != "entra":
        p = entrada(p, mascota.get("_entrada") or tipo_entrada(int(float(mascota.get("x", 0.5))*10)), t,
                    float(mascota.get("x", 0.5)), w, h, suelo)
    dg = min(1.0, max(0.0, float(mascota.get("desgaste") or 0.0)))
    temblor = 0.0
    if dg:
        # Sin fuerzas: se mueve menos, encorvado y temblando.
        p["levanta"] = p.get("levanta", 0.0)*(1 - 0.6*dg)
        p["inclina"] = p["inclina"]*(1 - 0.5*dg) + 7*dg*lado
        p["estira"] = 1 + (p["estira"] - 1)*(1 - 0.5*dg) - 0.06*dg
        temblor = math.sin(t*47)*0.009*dg
    return {"quien": "mokordo", "fig": mascota, "p": p, "h": h, "lado": lado, "suelo": suelo, "desgaste": dg,
            "cx": w*float(mascota.get("x", 0.5)) + (p.get("dx", 0.0) + p.get("temblor", 0.0) + temblor)*h,
            "gesto": str(mascota.get("gesto") or _cansado(p.get("gesto") or "neutro", dg)), "color": COLOR,
            "forma": FORMA,
            "pelo": "?", "brazo_lleva": bool(mascota.get("lleva")), "t": t}


def _muelle_pelo(e):
    """El "?" va con retraso, como un muelle: se queda atras cuando el cuerpo
    se inclina o salta y luego se pasa de largo."""
    p, t = e["p"], e["t"]
    return -0.6*p["inclina"]*e["lado"] + 14*p.get("levanta", 0.0)*math.sin(t*9) + 4*math.sin(t*3.3)


def pinta_estado(img, e: dict):
    """Pinta un personaje (Mokordo o de la familia) como dice su estado.
    Devuelve (cabeza, manos)."""
    p, lado, h = e["p"], e["lado"], e["h"]
    brazos = p.get("brazos", ((60, 20), (60, 20)))
    if lado < 0:
        brazos = (brazos[1], brazos[0])
    if e.get("brazo_lleva"):
        brazos = (brazos[0], (-20, -10))      # la mano que lleva algo, adelante
    cabeza, manos = dibuja(img, e["cx"], e["suelo"], h, gesto=e["gesto"], estira=p["estira"],
                           inclina=p["inclina"]*lado, brazos=brazos, parpadeo=p.get("parpadeo", False),
                           piernas=p.get("piernas"), levanta=p.get("levanta", 0.0)*h, color=e["color"],
                           forma=e["forma"], pelo=e.get("pelo"), gafas=e.get("gafas", False),
                           bigote=e.get("bigote", False), alcanza=e.get("alcanza"), pie_arriba=e.get("pie_arriba"),
                           desgaste=e.get("desgaste", 0.0), mira=e.get("mira"), habla=e.get("habla"),
                           pelo_giro=_muelle_pelo(e))
    # Los efectos de la accion (las rayas de correr, la tos, el hipo...).
    d = ImageDraw.Draw(img)
    if p.get("rayas"):
        for k in range(3):
            y = e["suelo"] - h*(0.25 + k*0.18)
            x0 = e["cx"] - lado*h*0.35
            d.line([(x0, y), (x0 - lado*h*(0.25 + 0.08*k), y)], fill=(150, 146, 140),
                   width=max(3, int(h*0.012)))
    if p.get("polvo", 0) > 0.05:
        # el polvo de aterrizar: nubecitas que salen a los lados de los pies
        k_ = 1 - p["polvo"]
        for lado_ in (-1, 1):
            for j in range(3):
                rr_ = h*(0.025 + 0.03*k_)*(1 - j*0.2)
                px_ = e["cx"] + lado_*h*(0.22 + 0.25*k_ + j*0.07)
                py_ = e["suelo"] - h*(0.02 + 0.05*k_ + j*0.015)
                d.ellipse([px_ - rr_, py_ - rr_, px_ + rr_, py_ + rr_], fill=(232, 228, 220), outline=(200, 196, 188))
    if p.get("sudor"):
        # gotas de sudor que salen volando de la cabeza
        for j in range(2):
            u_ = (e["t"]*1.6 + j*0.5) % 1.0
            gx = cabeza[0] + (-1 if j else 1)*h*(0.2 + 0.15*u_)
            gy = cabeza[1] - h*(0.22 - 0.25*u_*u_)
            rg = h*0.025
            d.polygon([(gx, gy - rg*1.8), (gx + rg, gy), (gx, gy + rg), (gx - rg, gy)], fill=(150, 205, 245),
                      outline=TINTA)
    if p.get("tos", 0) > 0.3:
        boca = (cabeza[0] + lado*h*0.08, cabeza[1] + h*0.07)
        for k in range(3):
            rk = h*(0.02 + 0.015*k)*p["tos"]
            bx, by = boca[0] + lado*h*(0.1 + 0.07*k), boca[1] - h*0.02*k
            d.ellipse([bx - rk, by - rk, bx + rk, by + rk], fill=(225, 225, 230), outline=(150, 150, 160))
    if p.get("rojo"):
        # los mofletes colorados del que ha bebido
        for k in (-1, 1):
            mx, my = cabeza[0] + k*h*0.12, cabeza[1] + h*0.03
            d.ellipse([mx - h*0.04, my - h*0.022, mx + h*0.04, my + h*0.022], fill=(240, 110, 120))
    if p.get("hipo"):
        from . import garabato
        garabato._letrero(img, "hic!", (cabeza[0] + lado*h*0.32, cabeza[1] - h*0.28), h*0.12, TINTA, -10*lado,
                          garabato._escala_pop((e["t"] % 1.7)))
    if p.get("puntos"):
        from . import garabato
        for k in range(3):
            garabato._letrero(img, ".", (cabeza[0] + lado*(h*0.3 + k*h*0.09), cabeza[1] - h*0.25 - k*h*0.05),
                              h*0.2, TINTA, 0, garabato._escala_pop(e["t"] - 0.3 - k*0.35))
    return cabeza, manos


def pinta(img, mascota: dict, t: float, dur: float, suelo: float):
    """La mascota del plano en el segundo t. Devuelve la cabeza y su efecto."""
    e = estado_mascota(mascota, t, dur, suelo, *img.size)
    cabeza, _manos = pinta_estado(img, e)
    return cabeza, e["p"].get("efecto")


# ---------------------------------------------------------------------------
# LA FAMILIA DE MOKORDO: el resto de personajes de las historias ("ya no
# solo Mokordo: los otros personajes que se parezcan a el, mas gordos,
# delgados... pero no metas los otros", los de palotes). El guion los sigue
# pidiendo como "figuras" (quien, pose, gesto...); aqui se pintan asi.
# ---------------------------------------------------------------------------
FAMILIA = {
    "persona":   {"color": (120, 175, 240), "forma": "gota", "tam": 0.46, "pelo": None},
    "persona_b": {"color": (245, 150, 185), "forma": "gota", "tam": 0.44, "pelo": "moño"},
    "nino":      {"color": (130, 205, 115), "forma": "gota", "tam": 0.32, "pelo": "brote"},
    "abuelo":    {"color": (200, 195, 210), "forma": "judia", "tam": 0.52, "pelo": None, "gafas": True,
                  "bigote": True},
}
# La postura que pide el guion -> la accion de la familia.
_POSE_A_ACCION = {
    "de_pie": "explica", "sentado": "explica", "brazos_arriba": "salta", "señala": "senala",
    "corriendo": "corre", "andando": "anda", "cayendose": "mareo", "manos_cabeza": "asusta",
    "mirando": "piensa", "bailando": "baila", "aplaudiendo": "rie", "en_cama": "duerme",
    "tumbado": "duerme", "cantando": "baila", "de_rodillas": "triste", "rezando": "piensa",
    "peleando": "baila", "empujando": "anda", "cargando": "anda", "dando": "senala",
}
_GESTO_A_ACCION = {"riendo": "rie", "asustado": "asusta", "triste": "triste", "grito": "asusta",
                   "bostezo": "duerme"}


def semilla_entrada(figura: dict) -> int:
    return sum(map(ord, str(figura.get("quien", "")))) + int(float(figura.get("x", 0.5))*10)


def estado_personaje(figura: dict, t: float, dur: float, suelo: float, w: int, h_img: int) -> dict:
    """Como esta un personaje de la familia en el segundo t, sin pintarlo."""
    quien = figura.get("quien") if figura.get("quien") in FAMILIA else "persona"
    rasgos = FAMILIA[quien]
    pose = str(figura.get("pose_fin") or figura.get("pose") or "de_pie")
    gesto = str(figura.get("gesto") or "neutro")
    accion = _POSE_A_ACCION.get(pose, "explica")
    if accion == "explica" and gesto in _GESTO_A_ACCION:
        accion = _GESTO_A_ACCION[gesto]
    lado = -1 if figura.get("espejo") else 1
    p = postura(accion, t + (sum(map(ord, quien)) % 7)*0.37, dur, lado)
    h = h_img*rasgos["tam"]
    if not figura.get("_ya"):
        p = entrada(p, figura.get("_entrada") or tipo_entrada(semilla_entrada(figura)),
                    t - float(figura.get("_retraso", 0.0)), float(figura.get("x", 0.5)), w, h, suelo)
    # los extras se mueven algo menos de su sitio que Mokordo (que no se crucen)
    return {"quien": quien, "fig": figura, "p": p, "h": h, "lado": lado, "suelo": suelo,
            "cx": w*float(figura.get("x", 0.5)) + (p.get("dx", 0.0)*0.5 + p.get("temblor", 0.0))*h,
            "gesto": gesto if gesto != "neutro" else p.get("gesto", "neutro"), "color": rasgos["color"],
            "forma": rasgos["forma"], "pelo": rasgos["pelo"], "gafas": rasgos.get("gafas", False),
            "bigote": rasgos.get("bigote", False), "brazo_lleva": bool(figura.get("lleva")), "t": t}


def personaje(img, figura: dict, t: float, dur: float, suelo: float, w: int, h_img: int):
    """Un personaje de la familia en el segundo t. Devuelve (cabeza, manos, alto)."""
    e = estado_personaje(figura, t, dur, suelo, w, h_img)
    cabeza, manos = pinta_estado(img, e)
    return cabeza, manos, e["h"]
