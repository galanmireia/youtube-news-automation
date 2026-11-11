"""LO HE SIMULADO #1: ¿Por qué hay atascos sin ningún accidente?

Video horizontal (1920x1080) para YouTube, con la simulacion de trafico de
trafico.py, voz gratis (Piper, la de montaje.py con los acentos arreglados),
musica y efectos sintetizados y subtitulos.

    python3 atascos.py salida.mp4 [--escenas 0,1] [--fotos hoja.png]
"""
import argparse
import math
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "espana"))
import montaje as MJ  # noqa: E402  (voz, musica, efectos, subtitulos)
from trafico import LARGO_COCHE, Anillo  # noqa: E402

W, H, FPS = 1920, 1080, 30
S = 2                                    # se dibuja al doble y se reduce
FUENTE = MJ.FUENTE
TINTA = (30, 30, 36)
AZUL_ZEN = (60, 130, 240)
DT = 0.05

# ---------------------------------------------------------------- el guion

ESCENAS = [
    dict(n="Estás en la autopista. De repente, todo el mundo frena. Diez minutos a paso de tortuga... y cuando por fin sales del atasco, no hay nada. Ni un accidente, ni obras, ni un camión averiado. Nada.",
         vista="zoom", sim="atasco"),
    dict(n="¿Entonces de dónde ha salido? Para averiguarlo, he construido una carretera dentro de un ordenador. Y en este vídeo vamos a descubrir de dónde salen estos atascos, cuántos coches hacen falta para que aparezcan, por qué meter más coches hace que pasen menos... y cómo un solo conductor puede arreglarlo.",
         vista="titulo", sim="atasco"),
    dict(n="Es un circuito redondo de doscientos treinta metros. Sin entradas, sin salidas y sin semáforos. Aquí no hay ninguna excusa para un atasco.",
         vista="vacio", sim=None),
    dict(n="Cada coche lo lleva un conductor virtual con tres reglas muy sencillas.",
         vista="anillo", sim="uno"),
    dict(n="Una: si tiene sitio delante, acelera. Dos: si se acerca al de delante, frena. Y tres: de vez en cuando, frena un poquito sin motivo. Se despista, mira el móvil, se asusta. Lo normal.",
         vista="reglas", sim="uno"),
    dict(n="Empezamos con ocho coches. Y todo va perfecto. Aunque alguno frena de vez en cuando, hay tanto hueco que no pasa nada.",
         vista="anillo", sim="ocho", panel="contador"),
    dict(n="Ahora, veintidós. Repartidos a la misma distancia y todos a la misma velocidad: unos treinta kilómetros por hora.",
         vista="anillo", sim="veintidos", panel="contador"),
    dict(n="Al principio, todo bien. Pero mira lo que pasa cuando uno de ellos frena un poco. El de detrás frena un poco más. El siguiente, más todavía. Y al cabo de un rato...",
         vista="anillo", sim="veintidos", panel="contador", acelera=4.0, frena_en=1.0),
    dict(n="...hay coches completamente parados. Nadie ha chocado. Nadie se ha salido. Ha aparecido un atasco de la nada.",
         vista="anillo", sim="veintidos", panel="contador", acelera=2.0, despistes=True),
    dict(n="Y esto no pasa solo en el ordenador. En 2008, unos investigadores japoneses lo hicieron con coches de verdad: veintidós conductores en un circuito de doscientos treinta metros, con la orden de ir a velocidad constante. Al poco rato, apareció un atasco.",
         vista="anillo", sim="veintidos", panel="japon"),
    dict(n="Si dibujamos dónde está cada coche segundo a segundo, se ve algo rarísimo: las zonas rojas, donde los coches están parados, se mueven... hacia atrás.",
         vista="anillo", sim="veintidos", panel="diagrama", acelera=2.0),
    dict(n="Los coches van hacia delante, pero el atasco va hacia atrás. Por eso, en la autopista, te comes un parón que empezó minutos antes, más adelante, porque alguien frenó sin motivo... y que ya ni siquiera está allí.",
         vista="anillo", sim="veintidos", panel="diagrama", acelera=2.0, flecha=True),
    dict(n="Pero, ¿cuántos coches hacen falta para que esto pase? Vamos a probarlo. Empiezo con diez, y voy metiendo dos más cada vez. Con diez, con doce, con catorce... nada. Con dieciséis, con dieciocho, con veinte... todo sigue fluyendo. Y de repente, con veintidós coches, se rompe. Justo el número del experimento japonés.",
         vista="barrido", acelera=3.0),
    dict(n="En una gráfica se ve clarísimo. Hasta veinte coches, cero parados. A partir de ahí, cada coche que añadimos deja, más o menos, a uno más parado. Los físicos llaman a ese punto la densidad crítica.",
         vista="grafica", grafica="parados"),
    dict(n="Y ahora, lo más raro de todo. Voy a contar cuántos coches pasan por esta línea cada minuto. A la izquierda, veinte coches. A la derecha, veinticuatro.",
         vista="dos", sim=("f20", "f24"), etiquetas=("20 coches", "24 coches"), mide="flujo", acelera=2.0),
    dict(n="Con veinte, pasan más de cincuenta por minuto. Con veinticuatro... unos cuarenta. Hay más coches en la carretera, y pasan menos.",
         vista="dos", sim=("f20", "f24"), etiquetas=("20 coches", "24 coches"), mide="flujo", acelera=2.0),
    dict(n="Esta es la gráfica más importante del tráfico. Cuantos más coches, más pasan... hasta un punto. Pasado ese punto, el atasco hace que la carretera trague menos coches, justo cuando más coches quieren pasar. Por eso un atasco, una vez que empieza, cuesta tanto que se deshaga.",
         vista="grafica", grafica="flujo"),
    dict(n="¿Y por qué pasa todo esto? Porque tardamos en reaccionar. Y cuando reaccionamos, frenamos más de la cuenta. Ese poquito de más se va sumando de coche en coche, como en el juego del teléfono.",
         vista="anillo", sim="veintidos", panel="porque"),
    dict(n="Y aquí entra cómo conducimos. Mira estos dos circuitos, los dos con veinte coches, que antes iban perfectamente. A la izquierda, conductores normales. A la derecha, agresivos: reaccionan más tarde y, cuando frenan, frenan fuerte.",
         vista="dos", sim=("ag_norm", "ag_agr"), etiquetas=("20 normales", "20 agresivos"), mide="flujo", acelera=3.0),
    dict(n="Con los mismos veinte coches, los agresivos ya han formado un atasco, y pasan unos diez coches menos por minuto. Conducir agresivo no te hace llegar antes: hace que lleguemos todos más tarde.",
         vista="dos", sim=("ag_norm", "ag_agr"), etiquetas=("20 normales", "20 agresivos"), mide="flujo", acelera=3.0),
    dict(n="Prueba: si pongo conductores perfectos, que reaccionan al instante y nunca se despistan... no hay atasco. Nunca. Pero los humanos no somos así.",
         vista="anillo", sim="perfecto", panel="perfecto", frena_en=1.0),
    dict(n="La buena noticia es que no hace falta que todos conduzcamos perfecto. Mira lo que pasa si solo uno de los veintidós coches, este azul, conduce de otra forma: no se pega al de delante, deja hueco y, si ve un parón, levanta el pie pronto y suave en vez de frenar en seco.",
         vista="dos", sim=("izq", "der"), etiquetas=("22 conductores normales", "21 normales + 1 zen"), zen_en=6.0),
    dict(n="El atasco desaparece. Nadie se para. Y todos van, de media, igual de rápido que antes. Un solo coche de veintidós ha arreglado el problema de todos.",
         vista="dos", sim=("izq", "der"), etiquetas=("22 conductores normales", "21 normales + 1 zen"), acelera=2.0),
    dict(n="Y también se ha probado de verdad: en 2016, en Arizona, en un circuito con unos veinte coches, uno de ellos conducido por ordenador consiguió reducir mucho los frenazos de todos.",
         vista="dos", sim=("izq", "der"), etiquetas=("22 conductores normales", "21 normales + 1 zen"), panel="arizona"),
    dict(n="¿Y esos paneles de la autopista que bajan el límite de velocidad cuando hay mucho tráfico? Vamos a probarlo. A la izquierda, sin límite. A la derecha, con un límite más bajo para todos.",
         vista="dos", sim=("lim_no", "lim_si"), etiquetas=("Sin límite", "Límite más bajo"), acelera=2.0),
    dict(n="Funciona... a medias. Casi nadie se para, y se conduce mucho más tranquilo. Pero en este circuito tampoco se llega antes: la velocidad media también baja. Lo que se gana es que desaparecen los frenazos, y menos frenazos son menos ocasiones de darse un golpe.",
         vista="dos", sim=("lim_no", "lim_si"), etiquetas=("Sin límite", "Límite más bajo"), acelera=2.0),
    dict(n="Así que la próxima vez que estés en un atasco sin motivo, recuerda: no eres solo una víctima. Eres parte de él. Y la solución está en tu pie derecho: deja hueco, y no frenes de golpe.",
         vista="anillo", sim="der2", panel="leccion"),
    dict(n="¿Qué quieres que simule en el próximo vídeo? Déjamelo en los comentarios. Esto ha sido Lo he simulado.",
         vista="final", sim="der2"),
]

BARRIDO = list(range(10, 25, 2))


def crea_sims():
    s = {}
    s["atasco"] = Anillo(22, semilla=1).corre(110)
    s["uno"] = Anillo(1, ruido=0.0)
    s["ocho"] = Anillo(8, semilla=3)
    s["veintidos"] = Anillo(22, semilla=2, ruido=0.0)       # sin despistes hasta que lo digamos
    s["perfecto"] = Anillo(22, perfecto=True)
    s["izq"] = Anillo(22, semilla=1).corre(100)
    s["der"] = Anillo(22, semilla=1).corre(100)
    s["der2"] = Anillo(22, semilla=4, zen=0).corre(60)
    for n in BARRIDO:
        s[f"b{n}"] = Anillo(n, semilla=1).corre(100)
    s["f20"] = Anillo(20, semilla=1).corre(120)
    s["f24"] = Anillo(24, semilla=1).corre(120)
    s["ag_norm"] = Anillo(20, semilla=1).corre(10)
    s["ag_agr"] = Anillo(20, semilla=1, sensibilidad=1.4, frenazo=3.0).corre(10)
    s["lim_no"] = Anillo(22, semilla=1).corre(100)
    s["lim_si"] = Anillo(22, semilla=1, vmax=8.0).corre(100)
    return s


def barrido_medido():
    """Para las graficas: parados y coches por minuto segun cuantos coches hay
    (media de tres simulaciones de tres minutos cada una)."""
    filas = []
    for n in range(10, 33, 2):
        par, flu = [], []
        for sem in (1, 2, 3):
            a = Anillo(n, semilla=sem).corre(120)
            paradas, pasan, prev = [], 0, a.x.copy()
            for k in range(int(180/DT)):
                a.paso(DT)
                pasan += int(((prev < a.L/2) & (a.x >= a.L/2)).sum())
                prev = a.x.copy()
                if k % 20 == 0:
                    paradas.append(int((a.v < 1).sum()))
            par.append(np.mean(paradas))
            flu.append(pasan/3.0)
        filas.append((n, float(np.mean(par)), float(np.mean(flu))))
    return filas


class Cuenta:
    """Coches que cruzan la linea (a mitad de vuelta) en el ultimo minuto."""

    def __init__(self, sim):
        self.sim, self.cruces, self.prev = sim, [], sim.x.copy()

    def paso(self, dt):
        self.sim.paso(dt)
        L = self.sim.L
        n = int(((self.prev < L/2) & (self.sim.x >= L/2)).sum())
        self.cruces += [self.sim.t]*n
        self.prev = self.sim.x.copy()

    def por_minuto(self):
        t = self.sim.t
        self.cruces = [c for c in self.cruces if t - c <= 60]
        return len(self.cruces)


# ---------------------------------------------------------------- dibujo

def color_velocidad(v, vmax=10.0):
    """Verde si va bien, amarillo si va lento, rojo si esta parado."""
    k = max(0.0, min(1.0, v/vmax))
    if k > 0.5:
        a = (k - 0.5)*2
        return (int(250*(1 - a) + 70*a), int(200*(1 - a) + 200*a), int(40*(1 - a) + 90*a))
    a = k*2
    return (int(230*(1 - a) + 250*a), int(50*(1 - a) + 200*a), int(50*(1 - a) + 40*a))


def fondo_cesped(w, h):
    img = Image.new("RGB", (w, h), (120, 186, 96))
    d = ImageDraw.Draw(img)
    rnd = np.random.default_rng(5)
    for _ in range(int(w*h/2500)):
        x, y = rnd.uniform(0, w), rnd.uniform(0, h)
        d.line([(x, y), (x + rnd.uniform(-4, 4)*S, y - 10*S)], fill=(100, 168, 80), width=2*S)
    return img


class Pista:
    """Un anillo dibujado: centro, radio y metros por pixel."""

    def __init__(self, cx, cy, r, L=230.0):
        self.cx, self.cy, self.r, self.L = cx*S, cy*S, r*S, L
        self.ancho = 0.2*r*S

    def punto(self, x_m, desfase=0.0):
        ang = -math.pi/2 + 2*math.pi*x_m/self.L
        return (self.cx + (self.r + desfase)*math.cos(ang), self.cy + (self.r + desfase)*math.sin(ang)), ang

    def carretera(self, img):
        d = ImageDraw.Draw(img)
        cx, cy, r, a = self.cx, self.cy, self.r, self.ancho
        d.ellipse([cx - r - a*0.62, cy - r - a*0.62, cx + r + a*0.62, cy + r + a*0.62], fill=(236, 236, 230))
        d.ellipse([cx - r - a*0.55, cy - r - a*0.55, cx + r + a*0.55, cy + r + a*0.55], fill=(70, 72, 78))
        d.ellipse([cx - r + a*0.55, cy - r + a*0.55, cx + r - a*0.55, cy + r - a*0.55], fill=(236, 236, 230))
        d.ellipse([cx - r + a*0.62, cy - r + a*0.62, cx + r - a*0.62, cy + r - a*0.62], fill=(120, 186, 96))
        for k in range(60):                       # la linea discontinua
            a0 = 2*math.pi*k/60
            p1 = (cx + r*math.cos(a0), cy + r*math.sin(a0))
            p2 = (cx + r*math.cos(a0 + 0.05), cy + r*math.sin(a0 + 0.05))
            d.line([p1, p2], fill=(240, 220, 120), width=3*S)
        rnd = np.random.default_rng(int(r))      # arbolitos dentro
        for _ in range(9):
            ang, rr = rnd.uniform(0, 2*math.pi), rnd.uniform(0.15, 0.65)*r
            x, y = cx + rr*math.cos(ang), cy + rr*math.sin(ang)
            t = rnd.uniform(26, 40)*S*(r/(380*S))
            d.ellipse([x - t*0.3, y - t*0.3 + t*0.8, x + t*0.3, y + t*0.3 + t*0.8], fill=(90, 70, 50))
            d.ellipse([x - t, y - t, x + t, y + t], fill=(70, 150, 70), outline=(40, 100, 40), width=2*S)

    def coches(self, img, sim, destellos=(), t=0.0):
        d = ImageDraw.Draw(img)
        escala = 2*math.pi*self.r/self.L         # pixeles por metro
        largo, ancho = LARGO_COCHE*escala*0.95, self.ancho*0.5
        for i in range(sim.n):
            (x, y), ang = self.punto(sim.x[i])
            dirx, diry = -math.sin(ang), math.cos(ang)      # tangente: hacia donde va
            nx, ny = math.cos(ang), math.sin(ang)
            def pt(a_, b_):
                return (x + dirx*a_ + nx*b_, y + diry*a_ + ny*b_)
            zen = sim.zen is not None and i == sim.zen
            col = AZUL_ZEN if zen else color_velocidad(sim.v[i])
            cuerpo = [pt(-largo/2, -ancho/2), pt(largo/2 - ancho*0.25, -ancho/2), pt(largo/2, -ancho*0.3),
                      pt(largo/2, ancho*0.3), pt(largo/2 - ancho*0.25, ancho/2), pt(-largo/2, ancho/2)]
            d.polygon(cuerpo, fill=col, outline=TINTA, width=2*S)
            d.polygon([pt(largo*0.12, -ancho*0.38), pt(largo*0.3, -ancho*0.34), pt(largo*0.3, ancho*0.34),
                       pt(largo*0.12, ancho*0.38)], fill=(190, 220, 245), outline=TINTA)
            d.polygon([pt(-largo*0.34, -ancho*0.36), pt(-largo*0.22, -ancho*0.38), pt(-largo*0.22, ancho*0.38),
                       pt(-largo*0.34, ancho*0.36)], fill=(160, 190, 215))
            frenando = sim.t < sim.freno_hasta[i] or (i < len(sim.v) and sim.v[i] < 1.0)
            for lado in (-1, 1):                  # pilotos de freno
                px, py = pt(-largo/2, lado*ancho*0.32)
                rr = ancho*0.12*(1.6 if frenando else 1)
                d.ellipse([px - rr, py - rr, px + rr, py + rr], fill=(255, 40, 40) if frenando else (140, 30, 30))
            if zen:                               # aura del coche zen
                d.ellipse([x - largo*0.85, y - largo*0.85, x + largo*0.85, y + largo*0.85], outline=AZUL_ZEN, width=3*S)
        for (tf, i) in destellos:                # el "!" del frenazo sin motivo
            if 0 <= t - tf < 1.2 and i < sim.n:
                (x, y), _ = self.punto(sim.x[i], desfase=-self.ancho*1.1)
                f = ImageFont.truetype(FUENTE, int(34*S))
                d.ellipse([x - 26*S, y - 26*S, x + 26*S, y + 26*S], fill=(255, 220, 60), outline=TINTA, width=3*S)
                d.text((x, y), "!", font=f, fill=TINTA, anchor="mm")


def caja(d, x, y, w, h, titulo=None):
    d.rounded_rectangle([x, y, x + w, y + h], radius=24*S, fill=(255, 255, 255), outline=TINTA, width=4*S)
    if titulo:
        d.text((x + w/2, y + 48*S), titulo, font=ImageFont.truetype(FUENTE, 40*S), fill=TINTA, anchor="mm")


def texto(d, xy, s, tam, col=TINTA, anchor="lm", borde=0):
    d.text((xy[0]*S, xy[1]*S), s, font=ImageFont.truetype(FUENTE, int(tam*S)), fill=col, anchor=anchor,
           stroke_width=borde*S, stroke_fill=(255, 255, 255) if borde else None)


class Diagrama:
    """Tiempo hacia abajo, posicion en el anillo de izquierda a derecha."""

    def __init__(self, w=620, h=560):
        self.w, self.h = w, h
        self.img = Image.new("RGB", (w, h), (250, 250, 248))
        self.fila = 0

    def anota(self, sim):
        y = self.fila % self.h
        if self.fila >= self.h:                  # desplaza hacia arriba
            self.img = self.img.crop((0, 1, self.w, self.h))
            nueva = Image.new("RGB", (self.w, self.h), (250, 250, 248))
            nueva.paste(self.img, (0, 0))
            self.img = nueva
            y = self.h - 1
        d = ImageDraw.Draw(self.img)
        for i in range(sim.n):
            x = sim.x[i]/sim.L*self.w
            r = 3 if sim.v[i] > 4 else 6          # los parados, mas gordos: la mancha roja del atasco
            d.ellipse([x - r, y - 1, x + r, y + 1], fill=color_velocidad(sim.v[i]))
        self.fila += 1


# ---------------------------------------------------------------- escena a escena

def frame(e, sims, t, dur, cache, diagrama):
    img = cache["cesped"].copy()
    d = ImageDraw.Draw(img)
    vista = e["vista"]
    if vista in ("anillo", "zoom", "titulo", "vacio", "reglas", "final"):
        pista = cache["pista_grande"] if vista in ("zoom", "titulo", "vacio", "final") else cache["pista"]
        img.paste(cache["carretera_grande" if pista is cache["pista_grande"] else "carretera"], (0, 0))
        d = ImageDraw.Draw(img)
        if vista == "vacio":
            p0, _ = pista.punto(0, desfase=-pista.ancho*1.4)
            texto(d, (W/2, H/2 - 40), "230 metros", 64, anchor="mm")
            texto(d, (W/2, H/2 + 40), "sin entradas · sin salidas · sin semáforos", 34, col=(60, 60, 70), anchor="mm")
        else:
            sim = sims[e["sim"]]
            pista.coches(img, sim, sim.frenazos, sim.t)
        if vista == "titulo":
            p = min(1.0, t/0.4)
            ov = Image.new("RGBA", img.size, (20, 22, 30, int(170*p)))
            img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
            d = ImageDraw.Draw(img)
            texto(d, (W/2, H/2 - 70), "LO HE SIMULADO", 120*(0.9 + 0.1*p), col=(255, 214, 0), anchor="mm")
            texto(d, (W/2, H/2 + 60), "¿Por qué hay atascos sin ningún accidente?", 50, col=(255, 255, 255), anchor="mm")
        if vista == "final":
            ov = Image.new("RGBA", img.size, (20, 22, 30, 150))
            img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
            d = ImageDraw.Draw(img)
            texto(d, (W/2, H/2 - 60), "LO HE SIMULADO", 110, col=(255, 214, 0), anchor="mm")
            texto(d, (W/2, H/2 + 50), "¿Qué simulo en el próximo vídeo?", 48, col=(255, 255, 255), anchor="mm")
            texto(d, (W/2, H/2 + 120), "Déjalo en los comentarios", 36, col=(210, 210, 210), anchor="mm")
    elif vista == "dos":
        img.paste(cache["carretera_dos"], (0, 0))
        d = ImageDraw.Draw(img)
        etiquetas = e.get("etiquetas", ("", ""))
        for clave, pista, nombre in ((e["sim"][0], cache["pista_izq"], etiquetas[0]),
                                     (e["sim"][1], cache["pista_der"], etiquetas[1])):
            sim = sims[clave]
            if e.get("mide") == "flujo":          # la linea de meta, a mitad de vuelta
                (lx, ly), ang = pista.punto(sim.L/2)
                nx, ny = math.cos(ang), math.sin(ang)
                for k in range(-3, 3):
                    a0 = pista.ancho*0.55*k/3
                    d.line([(lx + nx*a0, ly + ny*a0), (lx + nx*(a0 + pista.ancho*0.18), ly + ny*(a0 + pista.ancho*0.18))],
                           fill=(255, 255, 255) if k % 2 else (20, 20, 20), width=8*S)
            pista.coches(img, sim, sim.frenazos, sim.t)
            x0 = pista.cx/S
            arriba = e.get("panel") == "arizona"
            texto(d, (x0, 60 if arriba else 90), nombre, 40, anchor="mm", borde=6)
            parados = int((sim.v < 1).sum())
            if e.get("mide") == "flujo":
                pm = cache["cuentas"][clave].por_minuto() if clave in cache["cuentas"] else 0
                texto(d, (x0, 905), f"Pasan: {pm} por minuto", 46, anchor="mm", borde=6)
                texto(d, (x0, 962), f"Parados: {parados}", 36, col=(200, 30, 30) if parados else (40, 140, 60), anchor="mm", borde=6)
            else:
                texto(d, (x0, 120 if arriba else 905), f"Parados: {parados}", 46, col=(200, 30, 30) if parados else (40, 140, 60), anchor="mm", borde=6)
                texto(d, (x0, 170 if arriba else 960), f"Velocidad media: {sim.v.mean()*3.6:.0f} km/h", 34, anchor="mm", borde=6)
    elif vista == "barrido":
        img.paste(cache["carretera"], (0, 0))
        d = ImageDraw.Draw(img)
        k = min(len(BARRIDO) - 1, int(t/dur*len(BARRIDO)*1.05))
        n = BARRIDO[k]
        sim = sims[f"b{n}"]
        cache["pista"].coches(img, sim, sim.frenazos, sim.t)
        caja(d, 1180*S, 160*S, 700*S, 760*S, "PARADOS SEGÚN Nº DE COCHES")
        datos = {fila[0]: fila[1] for fila in cache["barrido"]}
        maximo = max(datos[m] for m in BARRIDO) or 1
        for j, m in enumerate(BARRIDO[:k + 1]):
            bx = 1230 + j*80
            alto = datos[m]/maximo*480
            col = (200, 30, 30) if datos[m] >= 0.5 else (60, 160, 80)
            d.rectangle([bx*S, (820 - max(6, alto))*S, (bx + 56)*S, 820*S], fill=col, outline=TINTA, width=2*S)
            texto(d, (bx + 28, 860), str(m), 30, anchor="mm")
        texto(d, (590, 520), f"{n}", 120, anchor="mm", col=(255, 255, 255), borde=0)
        texto(d, (590, 610), "coches", 40, anchor="mm", col=(255, 255, 255))
        parados = int((sim.v < 1).sum())
        texto(d, (590, 990), f"Parados ahora: {parados}", 44, anchor="mm", col=(200, 30, 30) if parados else (40, 140, 60), borde=6)
    elif vista == "grafica":
        img = Image.new("RGB", (W*S, H*S), (250, 248, 242))
        d = ImageDraw.Draw(img)
        datos = cache["barrido"]
        cual = e["grafica"]
        valores = [f[1] if cual == "parados" else f[2] for f in datos]
        titulo = "Coches parados según cuántos coches hay" if cual == "parados" else "Coches que pasan por minuto según cuántos coches hay"
        texto(d, (W/2, 90), titulo, 52, anchor="mm")
        x0, y0, ww, hh = 220, 900, 1500, 680
        d.line([(x0*S, y0*S), ((x0 + ww)*S, y0*S)], fill=TINTA, width=4*S)
        d.line([(x0*S, y0*S), (x0*S, (y0 - hh)*S)], fill=TINTA, width=4*S)
        vmax = max(valores)*1.15
        p = min(1.0, t/(dur*0.55))
        visibles = max(1, int(round(p*len(datos))))
        pts = []
        for j, ((n, _, _), v) in enumerate(zip(datos, valores)):
            x = x0 + 40 + j*(ww - 80)/(len(datos) - 1)
            y = y0 - v/vmax*hh
            texto(d, (x, y0 + 40), str(n), 30, anchor="mm")
            if j < visibles:
                pts.append((x*S, y*S))
        if len(pts) > 1:
            d.line(pts, fill=(60, 120, 220), width=8*S, joint="curve")
        for j, (x, y) in enumerate(pts):
            critico = datos[j][0] == 22
            r = 14*S if critico else 10*S
            d.ellipse([x - r, y - r, x + r, y + r], fill=(200, 30, 30) if critico else (60, 120, 220), outline=TINTA, width=2*S)
        texto(d, (W/2, y0 + 95), "número de coches en el circuito", 34, anchor="mm", col=(90, 90, 100))
        if visibles >= 7:
            j = [f[0] for f in datos].index(22 if cual == "parados" else 20)
            x = (x0 + 40 + j*(ww - 80)/(len(datos) - 1))
            y = y0 - valores[j]/vmax*hh
            letrero = "DENSIDAD CRÍTICA" if cual == "parados" else "EL MÁXIMO: a partir de aquí, pasan MENOS"
            texto(d, (x + 30, y - 70), letrero, 40, col=(200, 30, 30), borde=6)
    # paneles de la derecha
    panel = e.get("panel")
    if vista == "anillo" and panel:
        x, y, w_, h_ = 1230*S, 120*S, 620*S, 760*S
        sim = sims[e["sim"]]
        if panel == "contador":
            caja(d, x, y + 150*S, w_, 420*S)
            parados = int((sim.v < 1).sum())
            texto(d, (1260, 340), f"Coches: {sim.n}", 54)
            texto(d, (1260, 430), f"Velocidad media: {sim.v.mean()*3.6:.0f} km/h", 40)
            texto(d, (1260, 520), f"Parados: {parados}", 54, col=(200, 30, 30) if parados else (40, 140, 60))
            texto(d, (1260, 610), "Accidentes: 0", 40, col=(90, 90, 100))
        elif panel == "japon":
            caja(d, x, y + 120*S, w_, 520*S, "EXPERIMENTO REAL")
            for k, linea in enumerate(("Japón, 2008", "22 coches de verdad", "Circuito de 230 metros", "Orden: velocidad constante",
                                       "Resultado: atasco")):
                texto(d, (1270, 330 + k*72), linea, 40, col=(200, 30, 30) if k == 4 else TINTA)
        elif panel == "diagrama":
            caja(d, x - 20*S, 40*S, w_ + 40*S, 980*S)
            texto(d, (1540, 90), "Cada punto, un coche · el tiempo baja", 30, anchor="mm")
            img.paste(diagrama.img.resize((620*S, 840*S), Image.NEAREST), (int(x), int(150*S)))
            d = ImageDraw.Draw(img)
            texto(d, (1540, 1005), "← posición en el circuito →", 28, anchor="mm", col=(90, 90, 100))
            if e.get("flecha"):
                p = 0.5 + 0.5*math.sin(t*4)
                texto(d, (1540, 560), "← EL ATASCO VA HACIA ATRÁS", 40, col=(200, 30, 30), anchor="mm", borde=8)
        elif panel == "porque":
            caja(d, x, y + 120*S, w_, 560*S, "¿POR QUÉ PASA?")
            for k, (linea, col) in enumerate((("1. Tardamos en reaccionar", TINTA), ("2. Frenamos más de la cuenta", TINTA),
                                              ("3. El de detrás, más aún", TINTA), ("= la ola crece", (200, 30, 30)))):
                texto(d, (1270, 340 + k*90), linea, 42, col=col)
        elif panel == "perfecto":
            caja(d, x, y + 160*S, w_, 380*S, "CONDUCTORES PERFECTOS")
            texto(d, (1270, 420), "Reaccionan al instante", 40)
            texto(d, (1270, 500), "Nunca se despistan", 40)
            parados = int((sim.v < 1).sum())
            texto(d, (1270, 590), f"Parados: {parados}", 50, col=(40, 140, 60))
        elif panel == "leccion":
            caja(d, x, y + 200*S, w_, 360*S)
            texto(d, (1540, 410), "Deja hueco.", 64, anchor="mm")
            texto(d, (1540, 510), "No frenes de golpe.", 56, anchor="mm", col=AZUL_ZEN)
    if vista == "reglas":
        x, y, w_ = 1230*S, 160*S, 620*S
        reglas = (("1", "Si tiene sitio, acelera", 0.3), ("2", "Si se acerca, frena", 3.2), ("3", "A veces frena sin motivo", 6.4))
        for k, (num, txt, desde) in enumerate(reglas):
            if t >= desde:
                p = min(1.0, (t - desde)/0.25)
                yy = (200 + k*220)
                caja(d, x + (1 - p)*200*S, yy*S, w_, 170*S)
                d.ellipse([x + 30*S + (1 - p)*200*S, (yy + 35)*S, x + 130*S + (1 - p)*200*S, (yy + 135)*S], fill=(255, 214, 0), outline=TINTA, width=4*S)
                texto(d, (1230 + 80 + (1 - p)*200, yy + 85), num, 60, anchor="mm")
                texto(d, (1230 + 160 + (1 - p)*200, yy + 85), txt, 40)
    if vista == "dos" and e.get("panel") == "arizona":
        caja(d, 660*S, 820*S, 600*S, 200*S)
        texto(d, (960, 860), "EXPERIMENTO REAL · Arizona, 2016", 32, anchor="mm")
        texto(d, (960, 915), "~20 coches · 1 conducido por ordenador", 30, anchor="mm")
        texto(d, (960, 968), "Muchos menos frenazos para todos", 30, anchor="mm", col=AZUL_ZEN)
    if e.get("acelera", 1) > 1 and vista in ("anillo", "dos"):
        if vista == "dos":
            texto(d, (W/2, 520), f"CÁMARA RÁPIDA x{e['acelera']:.0f}", 30, col=(255, 255, 255), anchor="mm")
        else:
            texto(d, (60, 60), f"CÁMARA RÁPIDA x{e['acelera']:.0f}", 40, col=(255, 255, 255))
    # zoom de la primera escena: sobre el coche mas lento
    if vista == "zoom":
        sim = sims[e["sim"]]
        i = int(np.argmin(sim.v))
        (px, py), _ = cache["pista_grande"].punto(sim.x[i])
        z = 1.9 - 0.5*min(1.0, t/dur)
        cw, ch = W*S/z, H*S/z
        x0 = min(max(px - cw/2, 0), W*S - cw)
        y0 = min(max(py - ch/2, 0), H*S - ch)
        img = img.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W*S, H*S), Image.BILINEAR)
    return img.reduce(S)


# ---------------------------------------------------------------- montaje

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("salida")
    ap.add_argument("--escenas", default="")
    ap.add_argument("--fotos", default="")
    ap.add_argument("--audio", default="", help="la narracion con su voz (el mp3 de /narra)")
    ap.add_argument("--duraciones", default="", help="el json de /narra con lo que dura cada escena")
    args = ap.parse_args()
    cuales = [int(i) for i in args.escenas.split(",")] if args.escenas else list(range(len(ESCENAS)))

    cache = {"cesped": fondo_cesped(W*S, H*S)}
    cache["pista"] = Pista(590, 520, 430)
    cache["pista_grande"] = Pista(960, 520, 440)
    cache["pista_izq"] = Pista(480, 520, 330)
    cache["pista_der"] = Pista(1440, 520, 330)
    for clave, pistas in (("carretera", ["pista"]), ("carretera_grande", ["pista_grande"]),
                          ("carretera_dos", ["pista_izq", "pista_der"])):
        im = cache["cesped"].copy()
        for p in pistas:
            cache[p].carretera(im)
        cache[clave] = im
    sims = crea_sims()
    diagrama = Diagrama()
    cache["cuentas"] = {k: Cuenta(sims[k]) for k in ("f20", "f24", "ag_norm", "ag_agr")}
    for c in cache["cuentas"].values():        # un minuto de rodaje para que el contador tenga datos
        for _ in range(int(60/DT)):
            c.paso(DT)
    print("midiendo el barrido...", flush=True)
    cache["barrido"] = barrido_medido()
    print(cache["barrido"], flush=True)

    if args.fotos:
        fotos = []
        for i in cuales:
            e = ESCENAS[i]
            for k in (e["sim"] if isinstance(e.get("sim"), tuple) else ([e["sim"]] if e.get("sim") else [])):
                sims[k].corre(3)
            for _ in range(80):
                if e.get("sim") == "veintidos":
                    sims["veintidos"].corre(1.0)
                    diagrama.anota(sims["veintidos"])
            fotos.append(frame(e, sims, 2.0, 5.0, cache, diagrama).resize((480, 270)))
        hoja = Image.new("RGB", (480*4, 270*((len(fotos) + 3)//4)), "white")
        for k, f in enumerate(fotos):
            hoja.paste(f, ((k % 4)*480, (k//4)*270))
        hoja.save(args.fotos)
        return

    dir_voz = Path(__file__).resolve().parents[1] / "espana" / "voz" / "vits-piper-es_ES-davefx-medium"
    if args.audio:
        # SU VOZ: la narracion entera de /narra, y lo que dura cada escena
        # medido por ElevenLabs letra a letra; el video se ajusta a ella.
        import json
        info = json.loads(Path(args.duraciones).read_text())
        assert len(info["duraciones"]) == len(ESCENAS), "la narracion no tiene las mismas escenas que el guion"
        crudo = subprocess.run(["ffmpeg", "-v", "error", "-i", args.audio, "-f", "f32le", "-ac", "1", "-ar",
                                str(MJ.SR), "-"], capture_output=True, check=True).stdout
        narracion = np.frombuffer(crudo, np.float32).copy()
        narracion /= max(1e-6, np.abs(narracion).max())/0.92
        durs_todas = list(info["duraciones"])
        durs = [durs_todas[i] for i in cuales]
        hablados = list(durs)
        total = sum(durs) + 1.0
        starts = np.cumsum([0] + durs[:-1])
        pista_voz = np.zeros(int(total*MJ.SR) + MJ.SR, np.float32)
        inicios = np.cumsum([0] + durs_todas[:-1])
        for s, i in zip(starts, cuales):
            a = narracion[int(inicios[i]*MJ.SR):int((inicios[i] + durs_todas[i])*MJ.SR)]
            MJ.suma(pista_voz, a, s)
    else:
        voces = [MJ.voz(MJ.para_la_voz(ESCENAS[i]["n"]), dir_voz, 0.9) for i in cuales]
        durs = [len(a)/MJ.SR + 0.35 for a in voces]
        hablados = [len(a)/MJ.SR for a in voces]
        total = sum(durs) + 1.0
        starts = np.cumsum([0] + durs[:-1])
        pista_voz = np.zeros(int(total*MJ.SR) + MJ.SR, np.float32)
        for s, a in zip(starts, voces):
            MJ.suma(pista_voz, a, s + 0.05)
    print(f"duracion: {total/60:.1f} min", flush=True)
    musi = MJ.musica(total + 1, bpm=92)[:len(pista_voz)]
    env = np.convolve(np.abs(pista_voz), np.ones(int(0.25*MJ.SR))/int(0.25*MJ.SR), mode="same")
    vol = 0.12 - 0.08*np.clip(env*12, 0, 1)
    pista = pista_voz + musi*vol
    for n, s in enumerate(starts):
        if n:
            MJ.suma(pista, MJ.whoosh()*0.6, s - 0.12)
        if ESCENAS[cuales[n]].get("frena_en") is not None:
            MJ.suma(pista, MJ.boing()*0.7, s + ESCENAS[cuales[n]]["frena_en"])
    pista = np.tanh(pista*1.2)*0.9
    wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    with wave.open(wav, "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(MJ.SR)
        f.writeframes((pista[:int(total*MJ.SR)]*32767).astype(np.int16).tobytes())

    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                           args.salida], stdin=subprocess.PIPE)
    fuente_sub = ImageFont.truetype(FUENTE, 50)
    for n, i in enumerate(cuales):
        e = ESCENAS[i]
        dur = durs[n]
        hablado = hablados[n]
        filas = MJ.tiempos_de_palabras(MJ.trozos(e["n"]), hablado)
        claves = e["sim"] if isinstance(e.get("sim"), tuple) else ([e["sim"]] if e.get("sim") else [])
        frenado = False
        zen_puesto = False
        acum_diag = 0.0
        for fr in range(int(round(dur*FPS))):
            t = fr/FPS
            pasos = max(1, int(round(e.get("acelera", 1.0)/FPS/DT)))
            if e.get("frena_en") is not None and not frenado and t >= e["frena_en"]:
                sim = sims[claves[0]]
                sim.freno_hasta[0] = sim.t + 1.5
                sim.frenazos.append((sim.t, 0))
                frenado = True
            if e.get("zen_en") is not None and not zen_puesto and t >= e["zen_en"]:
                sims[claves[1]].zen = 0
                zen_puesto = True
            if e.get("despistes") and fr == 0:     # a partir de aqui, los despistes de siempre
                sims["veintidos"].ruido = 0.04
            if e["vista"] == "barrido":
                n_ahora = BARRIDO[min(len(BARRIDO) - 1, int(t/dur*len(BARRIDO)*1.05))]
                claves_paso = [f"b{n_ahora}"]
            else:
                claves_paso = claves
            for k in claves_paso:
                for _ in range(pasos):
                    if k in cache["cuentas"]:
                        cache["cuentas"][k].paso(DT)
                    else:
                        sims[k].paso(DT)
            if e.get("sim") == "veintidos" or e.get("panel") == "diagrama":
                acum_diag += pasos*DT
                while acum_diag >= 0.5:
                    diagrama.anota(sims["veintidos"])
                    acum_diag -= 0.5
            img = frame(e, sims, t, dur, cache, diagrama)
            # subtitulos abajo
            hab = t - 0.05
            fila = next((f_ for f_ in filas if f_[0][1] <= hab < f_[-1][2]), None)
            if fila is None and hab >= 0 and filas and hab < hablado + 0.25:
                fila = filas[-1]
            if fila:
                dd = ImageDraw.Draw(img)
                palabras = [p for p, _, _ in fila]
                frase = " ".join(palabras)
                dd.text((W/2, H - 70), frase, font=fuente_sub, fill=(255, 255, 255), anchor="mm",
                        stroke_width=8, stroke_fill=(0, 0, 0))
            ff.stdin.write(img.tobytes())
        print(f"escena {i + 1}/{len(ESCENAS)}: {dur:.1f}s", flush=True)
    ultimo = img
    for fr in range(int(1.0*FPS)):
        ff.stdin.write(ultimo.tobytes())
    ff.stdin.close()
    ff.wait()
    print(f"hecho: {args.salida}")


if __name__ == "__main__":
    main()
