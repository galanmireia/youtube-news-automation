import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, str(Path(__file__).resolve().parent))
import corto as C
import one_more as M
import burnout as B

W, H = C.CW, C.CH
def mitad(palo, llama, humo, texto, cans):
    img = M.oscurece(B.bg_ofi().filter(ImageFilter.GaussianBlur(6)), 0.35)
    img = img.crop((400, 0, 1200, H))
    st = dict(palo=palo, llama=llama, humo=humo, cansancio=cans, ceja=0.7*cans, pose="caido", mira=(0, 0.2 + 0.6*cans))
    tmp = img.copy(); cab, _ = C.cerilla(tmp, 400, 700 - 0.2*640, 700, 640, st, 0.35)
    if llama > 0.3:
        img = C.luz(img, cab[0], cab[1] + 40, 300, 0.35, (255, 180, 100))
    C.cerilla(img, 400, 700 - 0.2*640, 700, 640, st, 0.35)
    C.reloj_tarjeta(img, texto, 160 if texto == "DAY 1" else 640, 75, 0, 0)
    return img

out = Image.new("RGB", (W, H))
out.paste(mitad(1.0, 1.0, False, "DAY 1", 0.0), (0, 0))
out.paste(mitad(0.42, 0.18, True, "DAY 89", 0.9), (800, 0))
d = ImageDraw.Draw(out)
d.line([(800, 0), (800, H)], fill=(245, 245, 245), width=10)
d.text((W/2, 805), "BURNOUT", font=C.fuente(150), fill=(255, 255, 255), anchor="mm", stroke_width=12, stroke_fill=(10, 10, 12))
Path(M.OUT).mkdir(exist_ok=True)
out.resize((1280, 720), Image.LANCZOS).save(M.OUT + "miniatura_BURNOUT.jpg", quality=92)
