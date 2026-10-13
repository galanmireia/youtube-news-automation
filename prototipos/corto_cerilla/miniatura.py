import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, str(Path(__file__).resolve().parent))
import one_more as M
import corto as C

W, H = C.CW, C.CH
def mitad(llama, cans, hora, humo):
    img = M.oscurece(C.recorte(M.bg("dormitorio", oscuro=0.7), 1000, 300, 1.6).filter(ImageFilter.GaussianBlur(10)), 0.25)
    img = img.crop((400, 0, 1200, H))
    st = dict(llama=llama, cansancio=cans, mira=(0.3, 0.9), pose="movil", ceja=0.6*cans, humo=humo, sin_piernas=True,
              objeto=(415, 830))
    tmp = img.copy(); C.cerilla(tmp, 400, 1180, 2000, 1050, st, 0.35)
    img = C.luz(img, 410, 700, 300, 0.45)
    C.cerilla(img, 400, 1180, 2000, 1050, st, 0.35)
    C.movil(ImageDraw.Draw(img), 415, 830, 1050)
    C.reloj_tarjeta(img, hora, 400, 245, 0, 0)
    return img

Path(M.OUT).mkdir(exist_ok=True)
out = Image.new("RGB", (W, H))
out.paste(mitad(1.0, 0.05, "11:58 PM", False), (0, 0))
out.paste(mitad(0.12, 0.92, "3:47 AM", True), (800, 0))
d = ImageDraw.Draw(out)
d.line([(800, 0), (800, H)], fill=(245, 245, 245), width=10)
d.text((W/2, 105), "ONE MORE", font=C.fuente(140), fill=(255, 255, 255), anchor="mm", stroke_width=12, stroke_fill=(10, 10, 12))
out.resize((1280, 720), Image.LANCZOS).save(M.OUT + "miniatura_ONE_MORE.jpg", quality=92)
