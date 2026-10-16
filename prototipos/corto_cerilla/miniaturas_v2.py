"""MINIATURAS 2. Las primeras daban un 2 % de clics: fondo gris de oficina,
cerillas pequeñas y el titulo abajo, donde YouTube pone la duracion encima
("BURNOU" + 3:26). Aqui: fondo casi negro para que el rojo y la llama salten,
personajes grandes, el texto arriba y la esquina de abajo a la derecha vacia.
Dos de BURNOUT para la prueba A/B de YouTube y una nueva de ONE MORE."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, str(Path(__file__).resolve().parent))
import corto as C
import one_more as M
import burnout as B

W, H = C.CW, C.CH


def fondo_negro(foco=(800, 450), tono=(30, 30, 34)):
    img = Image.new("RGB", (W, H), tono)
    img = C.luz(img, foco[0], foco[1], 700, 0.18, (120, 120, 130))
    return img


def vineta(img, k=0.55):
    capa = Image.new("L", (W, H), 0)
    ImageDraw.Draw(capa).ellipse([-W*0.25, -H*0.35, W*1.25, H*1.35], fill=255)
    capa = capa.filter(ImageFilter.GaussianBlur(160))
    negro = Image.new("RGB", (W, H), (0, 0, 0))
    return Image.composite(img, Image.blend(img, negro, k), capa)


def titulo(img, texto, x, y, px, color=(255, 255, 255), ancla="mm"):
    ImageDraw.Draw(img).text((x, y), texto, font=C.fuente(px), fill=color, anchor=ancla,
                             stroke_width=max(8, px//12), stroke_fill=(8, 8, 10))


def guarda(img, nombre):
    Path(M.OUT).mkdir(exist_ok=True)
    img.resize((1280, 720), Image.LANCZOS).save(M.OUT + nombre, quality=93)
    print(M.OUT + nombre)


# BURNOUT A: el antes y el despues, grandes y juntos
def burnout_a():
    img = fondo_negro((800, 520))
    h = 900
    st1 = dict(palo=1.0, llama=1.0, feliz=0.8, mira=(0.15, 0.1), pose="caido")
    st2 = dict(palo=0.34, llama=0.22, humo=True, cansancio=0.95, ceja=0.8, mira=(-0.2, 0.5), pose="caido")
    img = C.luz(img, 420, 380, 380, 0.5, (255, 180, 100))
    C.cerilla(img, 420, 1000 - 0.2*h, 1000, h, st1, 0.35)
    C.cerilla(img, 1110, 1000 - 0.2*h, 1000, h, st2, 0.35)
    img = vineta(img, 0.5)
    C.reloj_tarjeta(img, "DAY 1", 420, 830, 0, 0)
    C.reloj_tarjeta(img, "DAY 89", 1110, 830, 0, 0)
    # el titulo encima del tocon, que es donde sobra sitio
    titulo(img, "BURNOUT", 1110, 150, 150)
    return img


# BURNOUT B: primer plano del tocon, el dia 89
def burnout_b():
    img = fondo_negro((560, 420))
    h = 1500
    st = dict(palo=0.30, llama=0.20, humo=True, cansancio=0.95, ceja=0.85, mira=(0.35, 0.35), pose="caido")
    C.cerilla(img, 560, 1260 - 0.2*h, 1260, h, st, 0.35)
    img = vineta(img, 0.5)
    titulo(img, "BURNOUT", 1150, 330, 150)
    C.reloj_tarjeta(img, "DAY 89", 1150, 470, 0, 0)
    return img


# ONE MORE: un primer plano a las 3:47 con la cara iluminada por el movil
def one_more():
    img = M.oscurece(C.recorte(M.bg("dormitorio", oscuro=0.7), 1000, 300, 1.6).filter(ImageFilter.GaussianBlur(12)), 0.45)
    st = dict(llama=0.14, cansancio=0.95, mira=(0.25, 0.95), pose="movil", ceja=0.7, humo=True, sin_piernas=True,
              objeto=(880, 860))
    tmp = img.copy(); C.cerilla(tmp, 800, 1300, 2200, 1250, st, 0.35)
    img = C.luz(img, 820, 640, 420, 0.55)
    C.cerilla(img, 800, 1300, 2200, 1250, st, 0.35)
    C.movil(ImageDraw.Draw(img), 880, 860, 1250)
    img = vineta(img, 0.55)
    C.reloj_tarjeta(img, "3:47 AM", 230, 110, 0, 0)
    titulo(img, "ONE MORE", 1170, 110, 120)
    return img


if __name__ == "__main__":
    guarda(burnout_a(), "miniatura_BURNOUT_A.jpg")
    guarda(burnout_b(), "miniatura_BURNOUT_B.jpg")
    guarda(one_more(), "miniatura_ONE_MORE_2.jpg")
