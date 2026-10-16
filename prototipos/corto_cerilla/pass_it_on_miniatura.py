"""Miniaturas de PASS IT ON, con lo aprendido: fondo oscuro, caras grandes,
texto arriba y la esquina de abajo a la derecha libre (ahi va la duracion)."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent))
import corto as C
import one_more as M
import pass_it_on as P
from miniaturas_v2 import fondo_negro, vineta, titulo, guarda

W, H = C.CW, C.CH

def mini_a():
    """El hijo junta su cabeza con la del padre, que casi no tiene llama."""
    img = fondo_negro((700, 520))
    img = C.luz(img, 520, 380, 380, 0.45, P.CALIDO)
    P.cabeza_suelta(img, 880, 640, 200, P.ROJO_P, 0.22, 0.3, gafas_=True, dirx=-0.4, mira=(-0.5, 0.2),
                    cansancio=0.85, ceja=0.5)
    P.cabeza_suelta(img, 520, 610, 210, C.ROJO, 0.8, 0.35, dirx=0.5, mira=(0.6, 0.3), ceja=0.45)
    img = vineta(img, 0.5)
    titulo(img, "CALL HIM.", 1170, 150, 125)
    return img

def mini_b():
    """El padre solo, de cerca, con la llama a punto de apagarse, y el movil."""
    img = fondo_negro((560, 480))
    P.cabeza_suelta(img, 470, 540, 290, P.ROJO_P, 0.25, 0.3, gafas_=True, dirx=0.3, mira=(0.4, 0.4),
                    cansancio=0.85, ceja=0.55)
    img = vineta(img, 0.5)
    titulo(img, "12 missed calls", 1170, 330, 80, color=(255, 255, 255))
    titulo(img, "from Dad.", 1170, 440, 80, color=(230, 70, 60))
    return img

if __name__ == "__main__":
    guarda(mini_a(), "miniatura_PASS_IT_ON_A.jpg")
    guarda(mini_b(), "miniatura_PASS_IT_ON_B.jpg")
