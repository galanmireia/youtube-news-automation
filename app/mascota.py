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


def dibuja(img, cx, suelo, h, gesto="neutro", estira=1.0, inclina=0.0, brazos=((60, 20), (60, 20)),
           parpadeo=False, piernas=None, levanta=0.0, color=None, forma=None, pelo="?", gafas=False,
           bigote=False):
    """Pinta la mascota. Devuelve la cabeza (cx, cy, radio, lado) para los
    efectos de garabato. brazos: (angulo, codo) por lado en grados; 0 es
    horizontal hacia fuera y + hacia abajo."""
    from . import garabato
    d = ImageDraw.Draw(img)
    g = max(4, int(h*0.017))
    color = color or COLOR
    forma = forma or FORMA
    ancho, alto = _medidas(h, forma)
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
    # Los brazos DELANTE del cuerpo: detras, el que saluda o el que se
    # levanta quedaba escondido.
    manos = []
    for lado, (ang, codo) in zip((-1, 1), brazos):
        hombro = T((lado*ancho*1.0, -alto*0.42))
        a1 = math.radians(ang)
        c = (hombro[0] + lado*math.cos(a1)*h*0.15, hombro[1] + math.sin(a1)*h*0.15)
        a2 = math.radians(ang + codo)
        mano = (c[0] + lado*math.cos(a2)*h*0.13, c[1] + math.sin(a2)*h*0.13)
        d.line([hombro, c, mano], fill=TINTA, width=int(g*2.6), joint="curve")
        d.line([hombro, c, mano], fill=color, width=int(g*1.3), joint="curve")
        d.ellipse([mano[0] - g*1.7, mano[1] - g*1.7, mano[0] + g*1.7, mano[1] + g*1.7], fill=color, outline=TINTA,
                  width=max(2, g//2))
        manos.append(mano)
    top = T((0, -alto))
    if pelo == "?":       # solo Mokordo
        garabato._letrero(img, "?", (top[0] + h*0.02, top[1] - h*0.07), h*0.2, TINTA, -12 + inclina*0.5)
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
    garabato._cara_expresiva(d, centro, r, g, random.Random(1), gesto, tinta=TINTA)
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
    return {"estira": 1 + 0.05*math.sin(2*math.pi*t/1.4), "inclina": 5*math.sin(t*1.7),
            "parpadeo": (t % 3.1) < 0.12}


# MUCHO MAS MOVIMIENTO ("hay que darle mas movimiento, mucho mas"): lo que
# hace cada accion, exagerado; y encima, unos saltitos de vez en cuando.
_EXAGERA = 1.7


def _saltito(t):
    """Un botecito cada poco: se agacha, sube y cae aplastandose."""
    u = (t % 1.9)/1.9
    if u < 0.12:
        return 0.0, 1 - 0.12*math.sin(u/0.12*math.pi)
    if u < 0.42:
        v = (u - 0.12)/0.30
        return 0.09*math.sin(v*math.pi), 1.08
    if u < 0.52:
        return 0.0, 1 - 0.14*math.sin((u - 0.42)/0.10*math.pi)
    return 0.0, 1.0


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
    return {"levanta": levanta, "estira": estira, "gesto": "riendo", "brazos": ((-80, -10), (-80, -10))}


def _piensa(t, dur, lado):
    rasca = math.sin(t*12)
    br = ((40, 40), (-125 + 10*rasca, 60)) if lado > 0 else ((-125 + 10*rasca, 60), (40, 40))
    return {"dx": 0.03*math.sin(t*2), "inclina": -6*lado + 3*math.sin(t*2), "gesto": "neutro", "brazos": br,
            "puntos": True}


def _asusta(t, dur, lado):
    retro = min(1.0, t/1.2)
    return {"dx": -lado*0.25*_suave(retro), "temblor": 0.025*math.sin(t*60), "gesto": "asustado",
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
            "brazos": ((10 + 55*a, -40 + 35*b), (10 + 55*b, -40 + 35*a)),
            "inclina": 6*math.sin(t*1.6), "dx": 0.07*math.sin(t*1.1), "piernas": t*8 if math.cos(t*1.1) > 0.6 else None}


def _mareo(t, dur, lado):
    return {"gesto": "sorpresa", "inclina": 18*math.sin(t*3), "dx": 0.05*math.sin(t*3),
            "brazos": ((-30 + 30*math.sin(t*5), 60), (-30 - 30*math.sin(t*5), 60))}


def _duerme(t, dur, lado):
    return {"gesto": "bostezo" if (t % 5) < 1.2 else "contento", "estira": 1 + 0.05*math.sin(t*1.8),
            "brazos": ((85, 0), (85, 0)), "inclina": 6, "efecto": "zzz"}


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
}


def postura(accion: str, t: float, dur: float, lado: int = 1) -> dict:
    f = ACCIONES.get(accion, ACCIONES["explica"])[0]
    p = _base(t)
    propia = f(t, dur, lado)
    p["estira"] = p["estira"]*(1 + (propia.pop("estira", 1.0) - 1)*_EXAGERA)
    p["inclina"] = p["inclina"] + propia.pop("inclina", 0.0)*_EXAGERA
    p.update(propia)
    p["levanta"] = min(0.45, p.get("levanta", 0.0)*_EXAGERA)
    # Los saltitos solo cuando la accion no lo mueve ya del suelo.
    if accion not in ("entra", "salta", "corre", "duerme", "triste", "asusta") and p["levanta"] < 0.05:
        sube, aplasta = _saltito(t + 0.6)
        p["levanta"] += sube
        p["estira"] *= aplasta
    p["estira"] = min(1.3, max(0.74, p["estira"]))
    return p


def pinta(img, mascota: dict, t: float, dur: float, suelo: float):
    """La mascota del plano en el segundo t. Devuelve la cabeza o None."""
    w, h_img = img.size
    lado = -1 if mascota.get("espejo") else 1
    accion = str(mascota.get("accion") or "explica").lower()
    p = postura(accion, t, dur, lado)
    h = h_img*float(mascota.get("tam") or 0.5)
    cx = w*float(mascota.get("x", 0.5)) + (p.get("dx", 0.0) + p.get("temblor", 0.0))*h
    gesto = str(mascota.get("gesto") or p.get("gesto") or "neutro")
    brazos = p.get("brazos", ((60, 20), (60, 20)))
    if lado < 0:
        brazos = (brazos[1], brazos[0])
    cabeza, _manos = dibuja(img, cx, suelo, h, gesto=gesto, estira=p["estira"], inclina=p["inclina"]*lado,
                            brazos=brazos, parpadeo=p.get("parpadeo", False), piernas=p.get("piernas"),
                            levanta=p.get("levanta", 0.0)*h)
    d = ImageDraw.Draw(img)
    if p.get("rayas"):
        for k in range(3):
            y = suelo - h*(0.25 + k*0.18)
            x0 = cx - lado*h*0.35
            d.line([(x0, y), (x0 - lado*h*(0.25 + 0.08*k), y)], fill=(150, 146, 140), width=max(3, int(h*0.012)))
    if p.get("puntos"):
        from . import garabato
        for k in range(3):
            garabato._letrero(img, ".", (cabeza[0] + lado*(h*0.3 + k*h*0.09), cabeza[1] - h*0.25 - k*h*0.05),
                              h*0.2, TINTA, 0, garabato._escala_pop(t - 0.3 - k*0.35))
    return cabeza, p.get("efecto")


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


def personaje(img, figura: dict, t: float, dur: float, suelo: float, w: int, h_img: int):
    """Un personaje de la familia en el segundo t. Devuelve (cabeza, manos)."""
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
    # los extras se mueven algo menos de su sitio que Mokordo (que no se crucen)
    cx = w*float(figura.get("x", 0.5)) + (p.get("dx", 0.0)*0.5 + p.get("temblor", 0.0))*h
    brazos = p.get("brazos", ((60, 20), (60, 20)))
    if lado < 0:
        brazos = (brazos[1], brazos[0])
    if figura.get("lleva"):
        brazos = (brazos[0], (-20, -10))      # la mano que lleva algo, adelante
    cabeza, manos = dibuja(img, cx, suelo, h, gesto=gesto if gesto != "neutro" else p.get("gesto", "neutro"),
                           estira=p["estira"], inclina=p["inclina"]*lado, brazos=brazos,
                           parpadeo=p.get("parpadeo", False), piernas=p.get("piernas"),
                           levanta=p.get("levanta", 0.0)*h, color=rasgos["color"], forma=rasgos["forma"],
                           pelo=rasgos["pelo"], gafas=rasgos.get("gafas", False), bigote=rasgos.get("bigote", False))
    return cabeza, manos, h
