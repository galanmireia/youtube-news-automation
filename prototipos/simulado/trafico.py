"""La carretera simulada: coches en un circuito circular, sin entradas, sin
salidas, sin obras y sin accidentes.

Cada conductor sigue el modelo de "velocidad optima" (Bando y otros, 1995),
el que se usa para explicar el experimento japones de 2008 en el que 22
coches en un circuito de 230 metros acabaron atascados sin motivo:
  - quiere ir a la velocidad que le parece segura para el hueco que tiene
    delante (mas hueco, mas rapido), y se acerca a ella poco a poco
    (tarda en reaccionar);
  - de vez en cuando frena un poco sin motivo (se despista, mira el movil,
    se asusta).
Con pocos coches no pasa nada. Con muchos, ese frenazo pequeño se agranda de
coche en coche y aparece una ola de atasco que viaja HACIA ATRAS.

El coche "zen" (opcional) es el que no se pega: mantiene hueco y va a la
velocidad media del que tiene delante, sin acelerones. Se traga la ola.
"""
import math

import numpy as np

LARGO_COCHE = 4.5


class Anillo:
    def __init__(self, n, longitud=230.0, vmax=12.0, sc=4.0, w=3.0, sensibilidad=2.0,
                 ruido=0.04, frenazo=1.8, zen=None, semilla=1, perfecto=False):
        self.n, self.L = n, longitud
        self.vmax, self.sc, self.w, self.a = vmax, sc, w, sensibilidad
        self.ruido, self.frenazo = ruido, frenazo
        self.zen = zen
        self.perfecto = perfecto
        self.rnd = np.random.default_rng(semilla)
        self.x = np.arange(n)*longitud/n            # posicion a lo largo del anillo
        self.x += self.rnd.uniform(-0.3, 0.3, n)
        self.v = np.full(n, self.v_optima(longitud/n - LARGO_COCHE))
        self.freno_hasta = np.zeros(n)              # hasta cuando dura su frenazo sin motivo
        self.t = 0.0
        self.media_zen = float(self.v[0])
        self.frenazos = []                          # (t, coche) para pintar el destello

    def v_optima(self, hueco):
        k = math.tanh(self.sc/self.w)
        return self.vmax*(np.tanh((hueco - self.sc)/self.w) + k)/(1 + k)

    def huecos(self):
        delante = np.roll(self.x, -1)
        return (delante - self.x) % self.L - LARGO_COCHE

    def paso(self, dt):
        h = self.huecos()
        objetivo = self.v_optima(h)
        acel = self.a*(objetivo - self.v)
        if self.perfecto:                          # el conductor perfecto: reacciona al instante y no se despista
            acel = 3.0*(objetivo - self.v)
        else:
            nuevos = self.rnd.random(self.n) < self.ruido*dt
            for i in np.where(nuevos)[0]:
                if self.t >= self.freno_hasta[i]:
                    self.freno_hasta[i] = self.t + 0.8
                    self.frenazos.append((self.t, int(i)))
            acel = np.where(self.t < self.freno_hasta, np.minimum(acel, -self.frenazo), acel)
        if self.zen is not None:
            # el coche zen: no persigue al de delante. Va a un ritmo tranquilo
            # (un poco por debajo del que tendria todo el mundo si fuesen
            # repartidos) y, si ve que se le echa encima un parón, levanta el
            # pie PRONTO y despacio, en vez de frenar en seco al llegar. Cuando
            # llega, el parón ya se ha deshecho.
            i = self.zen
            v_eq = float(self.v_optima(self.L/self.n - LARGO_COCHE))
            quiere = min(0.85*v_eq, max(0.0, (h[i] - 2.0)/1.6))
            acel[i] = float(np.clip(0.6*(quiere - self.v[i]), -3.0, 0.5))
        self.v = np.clip(self.v + acel*dt, 0, self.vmax)
        # nadie se choca: si se queda sin hueco, se para
        h = self.huecos()
        self.v = np.where(h < 0.8, 0.0, self.v)
        self.x = (self.x + self.v*dt) % self.L
        self.t += dt

    def corre(self, segundos, dt=0.05):
        for _ in range(int(segundos/dt)):
            self.paso(dt)
        return self
