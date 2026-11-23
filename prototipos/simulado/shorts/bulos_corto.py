"""Short de los bulos: el gancho y el resultado del video largo (con su voz),
en vertical, y un final que manda al video completo.

El trozo horizontal se saca de bulos_v3.py (--segmentos 0,1 --sin-subtitulos)
y aqui se coloca en el centro de la pantalla vertical, con la pregunta arriba.
Variable de entorno CLIP: la ruta de ese trozo.
"""
import os
import subprocess

import numpy as np
from PIL import Image

from estilo import AMARILLO, BLANCO, ROJO, W, titular

ALEGRE = False
CLIP = os.environ.get("CLIP", "")
AW, AH, Y0 = 1080, 608, 640


class Lector:
    def __init__(self, ruta):
        self.ruta, self.p, self.sig = ruta, None, None

    def _abre(self, n):
        if self.p:
            self.p.kill()
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{n/30:.4f}", "-i", self.ruta, "-vf", f"scale={AW}:{AH}",
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.sig = n

    def frame(self, t):
        n = int(round(t*30))
        if self.p is None or n != self.sig:
            self._abre(n)
        b = self.p.stdout.read(AW*AH*3)
        self.sig += 1
        if len(b) < AW*AH*3:
            return self.ultimo
        self.ultimo = Image.frombuffer("RGB", (AW, AH), b)
        return self.ultimo


LEC = None


def prepara(C):
    global LEC
    LEC = Lector(CLIP)


def dibuja(img, C):
    t = C.t
    fr = LEC.frame(min(t, sum(C.durs[:2]) - 0.05))
    img.paste(fr, (0, Y0))
    if C.cruza(C.en(0, "reenviar")):
        C.son("pop", 1.0)
    if C.cruza(C.en(0, "mentira")):
        C.son("golpe", 0.9)
    if C.cruza(C.en(1, "diez")):
        C.son("golpe", 0.7)
    titular(img, [[("¿Por qué un bulo", BLANCO)], [("llega ", BLANCO), ("11 VECES", ROJO)], [("más lejos", AMARILLO)],
                  [("que la verdad?", BLANCO)]], 170, 96)
    return img
