"""Portadas de los Shorts: el primer fotograma (pregunta + escena) y el Agente en
grande abajo, con la cara que pide cada tema.

    python3 portadas.py carpeta   (lee PORTADA_<nombre>.png y las rehace)
"""
import sys
from pathlib import Path

from PIL import Image

from estilo import agente

CARAS = {"frenazo": ("susto", "abajo"), "dinero": ("pensando", "cadera"), "cumple": ("susto", "abajo"),
         "puertas": ("pensando", "señala"), "cola": ("triste", "abajo")}

if __name__ == "__main__":
    d = Path(sys.argv[1])
    for n, (cara, brazos) in CARAS.items():
        img = Image.open(d/f"PORTADA_{n}.png").convert("RGB")
        agente(img, 540, 1480, 165, cara, 1.0, brazos)
        img.save(d/f"PORTADA_{n}.png")
