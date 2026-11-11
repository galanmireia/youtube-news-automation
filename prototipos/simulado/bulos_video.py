"""LO HE SIMULADO #2: ¿Por qué un bulo llega más lejos que la verdad?

Video horizontal (1920x1080). La simulacion en bulos.py; voz gratis (Piper,
montaje.py) o la suya con --audio y --duraciones (de /narra bulos si).

    python3 bulos_video.py salida.mp4 [--escenas 0,1] [--fotos hoja.png]
                                      [--audio X.mp3 --duraciones X.json]
"""
import argparse
import json
import math
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "espana"))
import montaje as MJ  # noqa: E402
from bulos import Cascada, Red  # noqa: E402

W, H, FPS = 1920, 1080, 30
FUENTE = MJ.FUENTE
FUENTE_B = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
FONDO_A, FONDO_B = (30, 40, 84), (8, 10, 24)
GRIS, ROJO, VERDE, AZUL, AMARILLO = (96, 108, 146), (255, 72, 88), (70, 226, 170), (96, 166, 255), (255, 206, 46)
BLANCO = (246, 248, 255)
PV, PB = 0.13, 0.22                     # la verdad y el bulo (un 70% mas, como en el estudio del MIT)

# Medias de 60 lanzamientos desde personas distintas (bulos.py, red de 1.000):
MEDIA_VERDAD, MEDIA_BULO = 41, 471
DESMENTIDO = [(0, 39), (2, 108), (4, 215), (6, 329), (10, 427)]      # (horas de retraso, alcance del bulo)
DUDA = [(0, 471), (10, 271), (20, 137), (30, 93), (40, 47)]          # (% menos de reenvios, alcance)
LIMITE = [("sin límite", 471), ("10 chats", 328), ("5 chats", 12), ("1 chat", 1)]
VACUNA = [(0, 471), (10, 275), (20, 171), (30, 73), (40, 26)]        # (% de vacunados, alcance)
BARRIDO = [(6, 2), (8, 3), (10, 6), (12, 22), (14, 66), (16, 89), (18, 175), (20, 299), (22, 471), (24, 575),
           (26, 676), (28, 730), (30, 773), (32, 825), (34, 889), (36, 904), (38, 947), (40, 956)]

ESCENAS = [
    dict(n="Un mensaje. Una sola persona le da a reenviar. En unas horas lo ha recibido media ciudad. Y es mentira.",
         vista="red", casc=["bulo"], desde=0, hasta=26),
    dict(n="¿Por qué los bulos llegan tan lejos, y la verdad casi nunca les alcanza? Para averiguarlo, he construido una red de mil personas dentro del ordenador... y he soltado un bulo.",
         vista="titulo", casc=["bulo"], desde=26, hasta=26),
    dict(n="Cada punto es una persona. Cada línea, alguien con quien habla: su familia, sus amigos, el grupo del trabajo. La mayoría solo habla con gente cercana... pero de vez en cuando alguien tiene un contacto lejano, como ese primo que vive en otra ciudad.",
         vista="red", casc=[], lejanos=True),
    dict(n="Y unos pocos tienen muchísimos contactos: los vamos a llamar influencers.",
         vista="red", casc=[], influencers=True),
    dict(n="La regla es muy sencilla. Cuando a alguien le llega un mensaje, tiene una oportunidad de reenviarlo a cada uno de sus contactos. A veces lo hace... y a veces no.",
         vista="red", casc=["verdad"], desde=0, hasta=3, zoom=True),
    dict(n="Empecemos con una noticia verdadera. Interesante, pero normal. La lanza una persona cualquiera...",
         vista="red", casc=["verdad"], desde=0, hasta=4, panel="contador"),
    dict(n="...y se apaga enseguida. La reciben unas pocas personas, y ya está.",
         vista="red", casc=["verdad"], desde=4, hasta=14, panel="contador"),
    dict(n="Ahora, un bulo. En 2018, unos investigadores del MIT analizaron unas ciento veintiséis mil historias que se habían compartido en Twitter, verdaderas y falsas. Las falsas tenían un setenta por ciento más de probabilidades de ser compartidas. Sorprenden más, indignan más... y nos encanta ser los primeros en contarlo.",
         vista="mit"),
    dict(n="Así que le doy a nuestro bulo exactamente eso: un setenta por ciento más de probabilidades de ser reenviado. Lo lanza la misma persona...",
         vista="red", casc=["bulo"], desde=0, hasta=11, panel="contador"),
    dict(n="...y mira. Sigue y sigue y sigue. Al final lo reciben cientos de personas.",
         vista="red", casc=["bulo"], desde=11, hasta=30, panel="contador"),
    dict(n="Y no es casualidad. Lo he repetido lanzando el mensaje desde sesenta personas distintas: de media, la verdad llega a unas cuarenta personas. El bulo, a unas cuatrocientas setenta. Con solo un setenta por ciento más de reenvíos, llega a más de diez veces más gente.",
         vista="barras", barras="media"),
    dict(n="¿Cómo puede una diferencia tan pequeña dar un resultado tan enorme? Porque hay un punto crítico. Si cada persona, de media, se lo pasa a menos de una persona nueva, el mensaje se apaga. Si se lo pasa a más de una, explota. La verdad se quedaba justo por debajo. El bulo, justo por encima.",
         vista="grafica"),
    dict(n="Y no solo llegan más lejos: también llegan antes. El estudio del MIT encontró que a la verdad le costaba unas seis veces más tiempo llegar a mil quinientas personas.",
         vista="mit", mit2=True),
    dict(n="¿Y si el bulo lo lanza un influencer, alguien con casi cien contactos? A la izquierda, lo lanza una persona normal. A la derecha, el influencer.",
         vista="dos", casc=("bulo", "bulo_inf"), etiquetas=("Lo lanza una persona normal", "Lo lanza un influencer"), desde=0, hasta=9),
    dict(n="Llega más rápido y a más gente. De media, a casi setecientas personas de mil. Por eso un bulo compartido por la cuenta equivocada parece imparable.",
         vista="dos", casc=("bulo", "bulo_inf"), etiquetas=("Lo lanza una persona normal", "Lo lanza un influencer"), desde=9, hasta=26),
    dict(n="Entonces, ¿se puede parar? Probemos con un desmentido. Lo lanza un influencer y, para ser justos, le doy la misma fuerza que al bulo. Quien lo ve, deja de reenviar el bulo.",
         vista="red", casc=["desm_bulo", "desm"], desde=0, hasta=24, panel="desmentido"),
    dict(n="Si el desmentido sale a la vez que el bulo, este apenas llega a cuarenta personas. Con dos horas de retraso, a más de cien. Con seis horas, a más de trescientas. Y con diez, casi da igual: llega a cuatrocientas.",
         vista="barras", barras="desmentido"),
    dict(n="Un desmentido sirve... pero solo si llega pronto. Y casi nunca llega pronto.",
         vista="barras", barras="desmentido"),
    dict(n="¿Y lo que hizo WhatsApp? En 2019 limitó los reenvíos: un mensaje solo se puede reenviar a cinco chats a la vez. Y en 2020 fue más allá: los mensajes muy reenviados, a uno solo. Vamos a probarlo. A la izquierda, sin límite. A la derecha, como mucho a cinco contactos.",
         vista="dos", casc=("bulo", "bulo_lim"), etiquetas=("Sin límite", "Como mucho, 5 contactos"), desde=0, hasta=26),
    dict(n="En mi red, ese límite deja al bulo por debajo del punto crítico: pasa de cuatrocientas setenta personas a una docena. En la vida real el efecto es menor, porque un chat puede ser un grupo de doscientas personas. Aun así, WhatsApp contó que los mensajes muy reenviados bajaron un setenta por ciento.",
         vista="barras", barras="limite"),
    dict(n="Y hay otra idea, que viene de la medicina: vacunarse. Hay investigadores que han creado juegos que te enseñan los trucos de los bulos, y quien juega luego cae bastante menos. Vamos a vacunar a una parte de la red: los puntos blancos ya conocen el truco, y no reenvían el bulo.",
         vista="red", casc=["bulo_vac"], desde=0, hasta=26, panel="contador"),
    dict(n="Con un diez por ciento de vacunados, el bulo llega a doscientas setenta y cinco personas. Con un treinta por ciento, a setenta. Y con un cuarenta, a menos de treinta. No hace falta vacunar a todo el mundo: basta con que lo esté una parte para proteger también a los demás.",
         vista="barras", barras="vacuna"),
    dict(n="Pero lo más eficaz de todo depende de ti. Vamos a hacer que cada persona dude un poco antes de reenviar. Que se pare diez segundos y piense: ¿esto será verdad?",
         vista="dos", casc=("bulo", "bulo_duda"), etiquetas=("Todos reenvían sin pensar", "Todos dudan un poco"), desde=0, hasta=26),
    dict(n="Si reenviamos solo un veinte por ciento menos, el bulo pasa de llegar a cuatrocientas setenta personas a ciento cuarenta. Con un treinta por ciento menos, a menos de cien. El bulo se queda por debajo del punto crítico... y se apaga solo.",
         vista="barras", barras="duda"),
    dict(n="Así que la próxima vez que te llegue algo que te indigne o te sorprenda muchísimo, recuerda: es justo el tipo de mensaje que más se reenvía. Espera diez segundos. A lo mejor eres tú quien lo apaga.",
         vista="red", casc=["bulo_duda"], desde=0, hasta=20, panel="leccion"),
    dict(n="¿Qué simulo en el próximo vídeo? Déjamelo en los comentarios. Esto ha sido Lo he simulado.",
         vista="final", casc=["bulo"], desde=30, hasta=30),
]


# ---------------------------------------------------------------- simulaciones

def prepara():
    red = Red(alto=0.5)
    normales = [i for i in range(red.n) if i not in red.influencers]
    inf = red.influencers[0]
    # el caso de demostracion: la misma persona lanza la verdad (que se apaga
    # pronto) y el bulo (que explota). Se busca uno asi, sin trampas en la
    # simulacion: los dos con las mismas reglas.
    origen, sem = None, None
    for o in normales:
        if red.grado[o] < 7:
            continue
        for s in range(6):
            v = Cascada(red, o, PV, semilla=s).corre().alcance()
            b = Cascada(red, o, PB, semilla=s).corre().alcance()
            if 4 <= v <= 14 and 600 <= b <= 760:
                origen, sem = o, s
                break
        if origen is not None:
            break
    c = {}
    c["verdad"] = Cascada(red, origen, PV, semilla=sem).corre(80)
    c["bulo"] = Cascada(red, origen, PB, semilla=sem).corre(80)
    c["bulo_inf"] = Cascada(red, inf, PB, semilla=0).corre(80)
    c["bulo_duda"] = Cascada(red, origen, PB*0.7, semilla=sem).corre(80)
    # casos parecidos a la media (sin elegir los que mas convienen):
    # con limite de 5 se queda en torno a una docena; con un 30% vacunado, en torno a 70
    for s in range(200):
        c["bulo_lim"] = Cascada(red, origen, PB, semilla=s, limite=5).corre(80)
        if 8 <= c["bulo_lim"].alcance() <= 20:
            break
    vac = set(int(x) for x in np.random.default_rng(9).choice(red.n, 300, replace=False)) - {origen}
    for s in range(200):
        c["bulo_vac"] = Cascada(red, origen, PB, semilla=s, vacunados=vac).corre(80)
        if 50 <= c["bulo_vac"].alcance() <= 100:
            break
    # desmentido con 2 horas de retraso
    D = 2
    corr = Cascada(red, inf, PB, semilla=1000 + sem)
    corr.cuando[:] = -1
    corr.cuando[inf] = D
    corr.frente = []
    bulo = Cascada(red, origen, PB, semilla=sem,
                   inmunes=lambda i, ronda: 0 <= corr.cuando[i] <= ronda)
    for ronda in range(80):
        if ronda == D:
            corr.frente = [inf]
            corr.ronda = D
        if ronda >= D and corr.frente:
            corr.paso()
        if bulo.frente:
            bulo.paso()
    c["desm"], c["desm_bulo"] = corr, bulo
    print(f"demo: origen {origen} (grado {red.grado[origen]}), verdad {c['verdad'].alcance()}, "
          f"bulo {c['bulo'].alcance()}, influencer {c['bulo_inf'].alcance()}, dudando {c['bulo_duda'].alcance()}, "
          f"desmentido: bulo {c['desm_bulo'].alcance()}, limite {c['bulo_lim'].alcance()}, vacunados {c['bulo_vac'].alcance()}", flush=True)
    return red, c, origen, inf


COLOR = {"verdad": VERDE, "bulo": ROJO, "bulo_inf": ROJO, "bulo_duda": ROJO, "desm_bulo": ROJO, "desm": AZUL,
         "bulo_lim": ROJO, "bulo_vac": ROJO}
VACUNADO = (236, 240, 250)


# ---------------------------------------------------------------- dibujo

def fondo():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt((xx - W/2)**2 + (yy - H/2)**2)/(W*0.62)
    k = np.clip(d, 0, 1)[..., None]
    img = np.array(FONDO_A, np.float32)*(1 - k) + np.array(FONDO_B, np.float32)*k
    return Image.fromarray(img.astype(np.uint8)).convert("RGBA")


class Lienzo:
    """Donde se pinta la red: caja en pantalla y radio de los puntos."""

    def __init__(self, red, x0, y0, w, r):
        self.red, self.x0, self.y0, self.w, self.r = red, x0, y0, w, r
        self.xy = np.column_stack([x0 + red.pos[:, 0]*w, y0 + red.pos[:, 1]*w])

    def estatico(self, base, lejanos=False, hubs=False):
        """Los enlaces (tenues) en una capa aparte, dibujada al doble."""
        S = 2
        capa = Image.new("RGBA", (W*S, H*S), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        for a, b in self.red.enlaces:
            (x1, y1), (x2, y2) = self.xy[a], self.xy[b]
            largo = math.hypot(x2 - x1, y2 - y1)
            lejos = largo > self.w*0.12
            de_hub = a in self.red.influencers or b in self.red.influencers
            marcar = (lejanos and lejos and not de_hub) or (hubs and de_hub)
            if lejanos and de_hub:
                continue
            col = ((255, 206, 46, 160) if hubs else (255, 206, 46, 95)) if marcar else (120, 140, 200, 40 if lejos else 70)
            d.line([(x1*S, y1*S), (x2*S, y2*S)], fill=col, width=(3 if marcar else 2)*S//2)
        return Image.alpha_composite(base, capa.resize((W, H), Image.LANCZOS))

    def nodos(self, img, colores, brillos, grandes=()):
        capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d, dh = ImageDraw.Draw(capa), ImageDraw.Draw(halo)
        for i, (x, y) in enumerate(self.xy):
            col = colores[i]
            r = self.r*(1.8 if i in grandes else 1.0)
            if brillos[i] > 0:
                rr = r*(1 + 1.2*brillos[i])
                dh.ellipse([x - rr*3, y - rr*3, x + rr*3, y + rr*3], fill=col + (int(220*min(1, brillos[i] + 0.4)),))
            d.ellipse([x - r, y - r, x + r, y + r], fill=col + (255,))
            if i in grandes:
                d.ellipse([x - r - 4, y - r - 4, x + r + 4, y + r + 4], outline=AMARILLO + (255,), width=3)
        img = Image.alpha_composite(img, halo.filter(ImageFilter.GaussianBlur(self.r*2.2)))
        return Image.alpha_composite(img, capa)

    def pulsos(self, img, casc, t, col):
        """El mensaje viajando por el enlace en la ronda en curso."""
        ronda, frac = int(t), t - int(t)
        d = ImageDraw.Draw(img)
        for j in np.where(casc.cuando == ronda + 1)[0]:
            i = casc.de_quien[j]
            if i < 0:
                continue
            (x1, y1), (x2, y2) = self.xy[i], self.xy[j]
            x, y = x1 + (x2 - x1)*frac, y1 + (y2 - y1)*frac
            d.line([(x1, y1), (x, y)], fill=col + (180,), width=2)
            d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(255, 255, 255, 255))
        return img


def estado(red, cascs, t):
    """Color y brillo de cada persona en la ronda t (float)."""
    colores = [GRIS]*red.n
    brillos = np.zeros(red.n)
    for clave in cascs:
        for j in CASC[clave].vacunados:
            colores[j] = VACUNADO
    for clave in cascs:
        c = CASC[clave]
        col = COLOR[clave]
        for j in np.where((c.cuando >= 0) & (c.cuando <= t))[0]:
            # el desmentido manda sobre el bulo: quien lo vio, azul
            if colores[j] in (AZUL, VACUNADO):
                continue
            colores[j] = col
            brillos[j] = max(0.0, 1 - (t - c.cuando[j])/1.5)
    return colores, brillos


def texto(d, xy, s, tam, col=BLANCO, anchor="mm", fuente=FUENTE, borde=0):
    d.text(xy, s, font=ImageFont.truetype(fuente, int(tam)), fill=col, anchor=anchor,
           stroke_width=borde, stroke_fill=(8, 10, 24) if borde else None)


def caja(d, x, y, w, h):
    d.rounded_rectangle([x, y, x + w, y + h], radius=24, fill=(14, 18, 40, 235), outline=(70, 86, 140), width=3)


def contador(d, x, y, n, total=1000, col=ROJO, hora=None):
    texto(d, (x, y), f"{n}", 92, col)
    texto(d, (x, y + 70), f"de {total} lo han recibido", 34, (200, 210, 240), fuente=FUENTE_B)
    if hora is not None:
        texto(d, (x, y + 118), f"hora {hora}", 30, (150, 160, 200), fuente=FUENTE_B)


def barras(img, tipo, t, dur):
    d = ImageDraw.Draw(img)
    if tipo == "media":
        titulo, datos, unidad = "Alcance medio (60 lanzamientos)", [("La verdad", MEDIA_VERDAD, VERDE), ("El bulo", MEDIA_BULO, ROJO)], ""
    elif tipo == "desmentido":
        titulo = "¿A cuánta gente llega el bulo, según cuándo sale el desmentido?"
        datos = [(f"{h} h" if h else "a la vez", v, AZUL if h <= 2 else ROJO) for h, v in DESMENTIDO] + [("sin desmentido", MEDIA_BULO, ROJO)]
    elif tipo == "limite":
        titulo = "¿A cuánta gente llega el bulo, con un límite de reenvíos?"
        datos = [(et, v, ROJO if v > 200 else (AMARILLO if v > 100 else VERDE)) for et, v in LIMITE]
    elif tipo == "vacuna":
        titulo = "¿A cuánta gente llega el bulo, si una parte está «vacunada»?"
        datos = [("nadie" if p == 0 else f"{p}% vacunados", v, ROJO if v > 200 else (AMARILLO if v > 100 else VERDE)) for p, v in VACUNA]
    else:
        titulo = "¿A cuánta gente llega el bulo, si dudamos antes de reenviar?"
        datos = [("sin dudar" if p == 0 else f"{p}% menos", v, ROJO if v > 200 else (VERDE if v < 100 else AMARILLO)) for p, v in DUDA]
    texto(d, (W/2, 110), titulo, 50)
    n = len(datos)
    ancho = min(260, 1500/n - 40)
    x0 = W/2 - (n*(ancho + 40) - 40)/2
    base, alto_max = 900, 620
    p = min(1.0, t/(dur*0.5))
    for k, (et, v, col) in enumerate(datos):
        x = x0 + k*(ancho + 40)
        q = min(1.0, max(0.0, p*n - k*0.6))
        alto = v/1000*alto_max*q
        d.rounded_rectangle([x, base - max(4, alto), x + ancho, base], radius=12, fill=col)
        if q > 0.5:
            texto(d, (x + ancho/2, base - alto - 40), f"{v}", 52, col)
        texto(d, (x + ancho/2, base + 45), et, 34 if n > 3 else 44, (210, 220, 245), fuente=FUENTE_B)
    texto(d, (W/2, 1010), "personas de 1.000", 30, (150, 160, 200), fuente=FUENTE_B)
    return img


def grafica(img, t, dur):
    d = ImageDraw.Draw(img)
    texto(d, (W/2, 100), "¿A cuánta gente llega, según lo que se reenvía?", 52)
    x0, y0, ww, hh = 230, 900, 1480, 680
    d.line([(x0, y0), (x0 + ww, y0)], fill=(150, 160, 200), width=4)
    d.line([(x0, y0), (x0, y0 - hh)], fill=(150, 160, 200), width=4)
    p = min(1.0, t/(dur*0.5))
    vis = max(2, int(p*len(BARRIDO)))
    pts = [(x0 + (pr - 6)/34*ww, y0 - v/1000*hh) for pr, v in BARRIDO[:vis]]
    d.line(pts, fill=AMARILLO, width=8, joint="curve")
    for pr in (6, 10, 14, 18, 22, 26, 30, 34, 38):
        texto(d, (x0 + (pr - 6)/34*ww, y0 + 40), f"{pr}%", 28, (180, 190, 220), fuente=FUENTE_B)
    texto(d, (W/2, y0 + 92), "probabilidad de reenviar a cada contacto", 32, (150, 160, 200), fuente=FUENTE_B)
    if p >= 1:
        for pr, nombre, col in ((13, "LA VERDAD", VERDE), (22, "EL BULO", ROJO)):
            x = x0 + (pr - 6)/34*ww
            v = np.interp(pr, [b[0] for b in BARRIDO], [b[1] for b in BARRIDO])
            y = y0 - v/1000*hh
            d.ellipse([x - 16, y - 16, x + 16, y + 16], fill=col, outline=BLANCO, width=3)
            texto(d, (x, y - 60), nombre, 40, col, borde=6)
        xc = x0 + (14 - 6)/34*ww
        d.line([(xc, y0), (xc, y0 - hh)], fill=(255, 255, 255, 120), width=3)
        texto(d, (xc + 14, y0 - hh + 20), "PUNTO CRÍTICO", 34, BLANCO, anchor="lm")
    return img


def mit(img, t, segundo=False):
    d = ImageDraw.Draw(img)
    caja(d, 360, 190, 1200, 640)
    texto(d, (W/2, 270), "ESTUDIO REAL · MIT, 2018", 46, AMARILLO)
    texto(d, (W/2, 330), "Vosoughi, Roy y Aral · revista Science", 30, (170, 180, 215), fuente=FUENTE_B)
    if not segundo:
        lineas = [("~126.000 historias en Twitter", BLANCO), ("verdaderas y falsas", (190, 200, 230)),
                  ("Las falsas:", BLANCO), ("+70% de probabilidad", ROJO), ("de ser compartidas", ROJO)]
    else:
        lineas = [("La verdad tardaba", BLANCO), ("unas 6 VECES más", ROJO), ("en llegar a 1.500 personas", BLANCO)]
    for k, (s, col) in enumerate(lineas):
        if t > 0.6 + k*0.9:
            texto(d, (W/2, 430 + k*80), s, 56 if col == ROJO else 46, col)
    return img


# ---------------------------------------------------------------- montaje

def main():
    global CASC
    ap = argparse.ArgumentParser()
    ap.add_argument("salida")
    ap.add_argument("--escenas", default="")
    ap.add_argument("--fotos", default="")
    ap.add_argument("--audio", default="")
    ap.add_argument("--duraciones", default="")
    args = ap.parse_args()
    cuales = [int(i) for i in args.escenas.split(",")] if args.escenas else list(range(len(ESCENAS)))

    red, CASC, origen, inf = prepara()
    base = fondo()
    grande = Lienzo(red, 80, 150, 1760, 7)
    izq = Lienzo(red, 40, 300, 900, 4.5)
    der = Lienzo(red, 980, 300, 900, 4.5)
    estaticos = {"grande": grande.estatico(base), "lejanos": grande.estatico(base, lejanos=True),
                 "hubs": grande.estatico(base, hubs=True),
                 "dos": der.estatico(izq.estatico(base))}

    def frame(e, t, dur):
        vista = e["vista"]
        # rondas ("horas") de simulacion: de 'desde' a 'hasta' a lo largo de la frase
        tr = e.get("desde", 0) + (e.get("hasta", e.get("desde", 0)) - e.get("desde", 0))*min(1.0, t/max(0.1, dur*0.9))
        if vista in ("red", "titulo", "final"):
            img = estaticos["lejanos" if e.get("lejanos") else ("hubs" if e.get("influencers") else "grande")].copy()
            cascs = e.get("casc", [])
            colores, brillos = estado(red, cascs, tr)
            for k in cascs:
                img = grande.pulsos(img, CASC[k], tr, COLOR[k])
            grandes = red.influencers if e.get("influencers") else (origen,) if cascs else ()
            img = grande.nodos(img, colores, brillos, grandes=grandes)
            d = ImageDraw.Draw(img)
            if e.get("panel") == "contador" and cascs:
                c = CASC[cascs[0]]
                n = int(((c.cuando >= 0) & (c.cuando <= tr)).sum())
                caja(d, 1500, 60, 380, 230)
                contador(d, 1690, 130, n, col=COLOR[cascs[0]], hora=int(tr))
            if e.get("panel") == "desmentido":
                nb = int(((CASC["desm_bulo"].cuando >= 0) & (CASC["desm_bulo"].cuando <= tr)).sum())
                nd = int(((CASC["desm"].cuando >= 0) & (CASC["desm"].cuando <= tr)).sum())
                caja(d, 1440, 60, 440, 260)
                texto(d, (1660, 120), f"Bulo: {nb}", 56, ROJO)
                texto(d, (1660, 195), f"Desmentido: {nd}", 50, AZUL)
                texto(d, (1660, 270), "el desmentido sale 2 h después", 26, (170, 180, 215), fuente=FUENTE_B)
            if e.get("panel") == "leccion":
                caja(d, 560, 380, 800, 260)
                texto(d, (W/2, 470), "Espera 10 segundos.", 70, AMARILLO)
                texto(d, (W/2, 560), "A lo mejor eres tú quien lo apaga.", 44)
            if vista == "titulo" or vista == "final":
                velo = Image.new("RGBA", (W, H), (8, 10, 24, int(185*min(1.0, t/0.4))))
                img = Image.alpha_composite(img, velo)
                d = ImageDraw.Draw(img)
                f = ImageFont.truetype(FUENTE, 120)
                w1, w2 = d.textlength("LO HE ", font=f), d.textlength("SIMULADO", font=f)
                x0 = W/2 - (w1 + w2)/2
                d.text((x0, H/2 - 70), "LO HE ", font=f, fill=BLANCO, anchor="lm")
                d.text((x0 + w1, H/2 - 70), "SIMULADO", font=f, fill=AMARILLO, anchor="lm")
                sub = "¿Por qué un bulo llega más lejos que la verdad?" if vista == "titulo" else "¿Qué simulo en el próximo vídeo?"
                texto(d, (W/2, H/2 + 60), sub, 52)
            if e.get("influencers"):
                texto(d, (W/2, 90), "INFLUENCERS: casi 100 contactos", 50, AMARILLO, borde=6)
            if e.get("lejanos"):
                texto(d, (W/2, 90), "Contactos lejanos", 50, AMARILLO, borde=6)
            if e.get("zoom"):                     # acercarse al que lo lanza
                x, y = grande.xy[origen]
                z = 1 + 1.6*min(1.0, t/1.2)
                cw, ch = W/z, H/z
                x0 = min(max(x - cw/2, 0), W - cw)
                y0 = min(max(y - ch/2, 0), H - ch)
                img = img.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.BILINEAR)
            return img.convert("RGB")
        if vista == "dos":
            img = estaticos["dos"].copy()
            for lienzo, clave, et in ((izq, e["casc"][0], e["etiquetas"][0]), (der, e["casc"][1], e["etiquetas"][1])):
                c = CASC[clave]
                colores, brillos = estado(red, [clave], tr)
                img = lienzo.pulsos(img, c, tr, COLOR[clave])
                grandes = (inf,) if clave == "bulo_inf" else (origen,)
                img = lienzo.nodos(img, colores, brillos, grandes=grandes)
                d = ImageDraw.Draw(img)
                cx = lienzo.x0 + lienzo.w/2
                texto(d, (cx, 230), et, 40, AMARILLO if clave != "bulo" else BLANCO)
                n = int(((c.cuando >= 0) & (c.cuando <= tr)).sum())
                texto(d, (cx, 860), f"{n}", 84, ROJO)
                texto(d, (cx, 925), "lo han recibido", 32, (200, 210, 240), fuente=FUENTE_B)
            texto(d, (W/2, 1000), f"hora {int(tr)}", 30, (150, 160, 200), fuente=FUENTE_B)
            return img.convert("RGB")
        img = base.copy()
        if vista == "barras":
            img = barras(img, e["barras"], t, dur)
        elif vista == "grafica":
            img = grafica(img, t, dur)
        elif vista == "mit":
            img = mit(img, t, e.get("mit2", False))
        return img.convert("RGB")

    if args.fotos:
        fotos = [frame(ESCENAS[i], 3.0, 6.0).resize((480, 270)) for i in cuales]
        hoja = Image.new("RGB", (480*4, 270*((len(fotos) + 3)//4)), "white")
        for k, f in enumerate(fotos):
            hoja.paste(f, ((k % 4)*480, (k//4)*270))
        hoja.save(args.fotos)
        return

    # la voz
    if args.audio:
        info = json.loads(Path(args.duraciones).read_text())
        assert len(info["duraciones"]) == len(ESCENAS), "la narracion no tiene las mismas escenas que el guion"
        crudo = subprocess.run(["ffmpeg", "-v", "error", "-i", args.audio, "-f", "f32le", "-ac", "1", "-ar",
                                str(MJ.SR), "-"], capture_output=True, check=True).stdout
        narr = np.frombuffer(crudo, np.float32).copy()
        narr /= max(1e-6, np.abs(narr).max())/0.92
        todas = list(info["duraciones"])
        durs = [todas[i] for i in cuales]
        hablados = list(durs)
        inicios = np.cumsum([0] + todas[:-1])
        trozos = [narr[int(inicios[i]*MJ.SR):int((inicios[i] + todas[i])*MJ.SR)] for i in cuales]
        desfase = 0.0
    else:
        dir_voz = Path(__file__).resolve().parents[1] / "espana" / "voz" / "vits-piper-es_ES-davefx-medium"
        trozos = [MJ.voz(MJ.para_la_voz(ESCENAS[i]["n"]), dir_voz, 0.9) for i in cuales]
        durs = [len(a)/MJ.SR + 0.35 for a in trozos]
        hablados = [len(a)/MJ.SR for a in trozos]
        desfase = 0.05
    total = sum(durs) + 1.0
    starts = np.cumsum([0] + durs[:-1])
    print(f"duracion: {total/60:.1f} min", flush=True)
    pista_voz = np.zeros(int(total*MJ.SR) + MJ.SR, np.float32)
    for s, a in zip(starts, trozos):
        MJ.suma(pista_voz, a, s + desfase)
    musi = MJ.musica(total + 1, bpm=88)[:len(pista_voz)]
    env = np.convolve(np.abs(pista_voz), np.ones(int(0.25*MJ.SR))/int(0.25*MJ.SR), mode="same")
    pista = pista_voz + musi*(0.11 - 0.07*np.clip(env*12, 0, 1))
    for n_, s in enumerate(starts):
        if n_:
            MJ.suma(pista, MJ.whoosh()*0.5, s - 0.12)
    pista = np.tanh(pista*1.2)*0.9
    wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    with wave.open(wav, "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(MJ.SR)
        f.writeframes((pista[:int(total*MJ.SR)]*32767).astype(np.int16).tobytes())

    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                           args.salida], stdin=subprocess.PIPE)
    fsub = ImageFont.truetype(FUENTE, 48)
    img = None
    for n_, i in enumerate(cuales):
        e = ESCENAS[i]
        dur = durs[n_]
        filas = MJ.tiempos_de_palabras(MJ.trozos(e["n"]), hablados[n_])
        for fr in range(int(round(dur*FPS))):
            t = fr/FPS
            img = frame(e, t, dur)
            hab = t - desfase
            fila = next((f_ for f_ in filas if f_[0][1] <= hab < f_[-1][2]), None)
            if fila is None and hab >= 0 and filas and hab < hablados[n_] + 0.25:
                fila = filas[-1]
            if fila:
                ImageDraw.Draw(img).text((W/2, H - 50), " ".join(p for p, _, _ in fila), font=fsub,
                                         fill=(255, 255, 255), anchor="mm", stroke_width=8, stroke_fill=(0, 0, 0))
            ff.stdin.write(img.tobytes())
        print(f"escena {i + 1}/{len(ESCENAS)}: {dur:.1f}s", flush=True)
    for _ in range(FPS):
        ff.stdin.write(img.tobytes())
    ff.stdin.close()
    ff.wait()
    print(f"hecho: {args.salida}")


CASC = {}

if __name__ == "__main__":
    main()
