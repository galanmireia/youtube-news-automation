"""La red de los bulos: 1.000 personas conectadas y algo que se reenvia.

La red: cada persona tiene un sitio en el plano y se conecta con sus
vecinos mas cercanos (familia, amigos, el grupo del trabajo) y, de vez en
cuando, con alguien lejano (el primo de Argentina): es una red de "mundo
pequeño" (Watts y Strogatz, 1998). Unas pocas personas tienen muchisimos
contactos: los "influencers".

La propagacion: modelo de cascada independiente (Kempe, Kleinberg y Tardos,
2003). Quien recibe el mensaje tiene UNA oportunidad de reenviarlo a cada uno
de sus contactos, y lo hace con probabilidad p. Si un contacto ya lo tenia,
no pasa nada. El bulo se reenvia un 70% mas que la verdad: es lo que midio
el estudio del MIT (Vosoughi, Roy y Aral, Science 2018).
"""
import math

import numpy as np


class Red:
    def __init__(self, n=1000, vecinos=6, lejanos=0.06, influencers=4, contactos_influencer=90,
                 ancho=1.0, alto=0.56, semilla=1):
        rnd = np.random.default_rng(semilla)
        self.n = n
        # sitios repartidos sin amontonarse (muestreo por rejilla con temblor)
        cols = int(math.sqrt(n*ancho/alto)) + 1
        filas = n//cols + 1
        pts = []
        for f in range(filas):
            for c in range(cols):
                pts.append(((c + 0.5 + rnd.uniform(-0.38, 0.38))/cols*ancho,
                            (f + 0.5 + rnd.uniform(-0.38, 0.38))/filas*alto))
        rnd.shuffle(pts)
        self.pos = np.array(pts[:n])
        enlaces = set()
        d = np.hypot(*(self.pos[:, None, :] - self.pos[None, :, :]).transpose(2, 0, 1))
        for i in range(n):
            for j in np.argsort(d[i])[1:vecinos + 1]:
                enlaces.add((min(i, j), max(i, j)))
            if rnd.random() < lejanos*vecinos:      # un contacto lejano
                j = int(rnd.integers(n))
                if j != i:
                    enlaces.add((min(i, j), max(i, j)))
        self.influencers = [int(i) for i in rnd.choice(n, influencers, replace=False)]
        for i in self.influencers:
            for j in rnd.choice(n, contactos_influencer, replace=False):
                if j != i:
                    enlaces.add((min(i, int(j)), max(i, int(j))))
        self.enlaces = sorted(enlaces)
        self.vecinos = [[] for _ in range(n)]
        for a, b in self.enlaces:
            self.vecinos[a].append(b)
            self.vecinos[b].append(a)
        self.grado = np.array([len(v) for v in self.vecinos])


class Cascada:
    """Un mensaje que se reenvia por la red, por rondas (cada ronda, una
    'hora'). Guarda quien lo tiene, cuando le llego y de quien (para pintar
    el reenvio como un pulso por el enlace)."""

    def __init__(self, red, origen, p, semilla=1, inmunes=None, limite=None, vacunados=None):
        self.red, self.p = red, p
        self.rnd = np.random.default_rng(semilla)
        self.cuando = np.full(red.n, -1)            # ronda en la que lo recibio (-1: no lo tiene)
        self.de_quien = np.full(red.n, -1)
        self.cuando[origen] = 0
        self.ronda = 0
        self.frente = [origen]
        self.inmunes = inmunes                      # los que ya vieron el desmentido: no lo reenvian
        self.limite = limite                        # como mucho a cuantos contactos se reenvia (el limite de WhatsApp)
        self.vacunados = vacunados or set()         # los que ya conocen el truco: nunca lo reenvian

    def paso(self):
        nuevos = []
        for i in self.frente:
            if self.inmunes is not None and self.inmunes(i, self.ronda):
                continue
            if i in self.vacunados:
                continue
            vecinos = list(self.red.vecinos[i])
            if self.limite is not None:
                self.rnd.shuffle(vecinos)
                vecinos = vecinos[:self.limite]
            for j in vecinos:
                if self.cuando[j] < 0 and self.rnd.random() < self.p:
                    self.cuando[j] = self.ronda + 1
                    self.de_quien[j] = i
                    nuevos.append(j)
        self.ronda += 1
        self.frente = nuevos
        return len(nuevos)

    def corre(self, rondas=60):
        for _ in range(rondas):
            if not self.frente:
                break
            self.paso()
        return self

    def alcance(self):
        return int((self.cuando >= 0).sum())
