"""Short vertical de BURNOUT (~45 s)."""
import subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, str(Path(__file__).resolve().parent))
import corto as C
import one_more as M
import burnout as B

SW, SH = 1080, 1920
J = lambda nombre: next(fn for a, b, fn, s in B.TABLA if getattr(fn, "__name__", "") == nombre)
CORTES = [
    (J("p_jefe_cerca"), 0.2, 4.2, (800, 1300)),
    (J("p_frote1"), 0.0, 2.4, (800, 1300)),
    (J("p_encendido"), 0.0, 3.5, (800, 1300)),
    (B.TABLA[11][2], 0.3, 4.3, (880, 1300)),          # "Can you stay late?"
    (J("p_noche_ofi"), 0.5, 3.5, (900, 1200)),
    (J("p_papelera"), 0.3, 4.3, (820, 1200)),
    (J("p_espejo"), 0.6, 4.6, (800, 1100)),
    (J("p_jefe_viene"), 0.6, 4.8, (900, 1300)),
    (J("p_no"), 0.3, 4.8, (860, 1300)),
    (J("p_postit_cerca"), 0.2, 3.2, (800, 1100)),
]
FIN = 4.5
_I = {fn: a for a, b, fn, s in B.TABLA}

def cuadro(fn, lt, caja):
    img, (cx, cy, z) = fn(lt, _I[fn] + lt)
    img = C.recorte(img, cx, cy, z) if z > 1.001 or abs(cx - C.CW/2) > 1 else img
    cxr, ancho = caja
    x0 = min(max(0, cxr - ancho/2), C.CW - ancho)
    return img.crop((int(x0), 0, int(x0) + ancho, 900))

def vertical(cuad):
    fondo = cuad.resize((int(SH*cuad.width/cuad.height), SH)).filter(ImageFilter.GaussianBlur(40))
    fondo = fondo.crop(((fondo.width - SW)//2, 0, (fondo.width - SW)//2 + SW, SH))
    fondo = M.oscurece(fondo, 0.55)
    alto = int(SW*cuad.height/cuad.width)
    fondo.paste(cuad.resize((SW, alto), Image.LANCZOS), (0, (SH - alto)//2))
    d = ImageDraw.Draw(fondo)
    d.text((SW/2, 330), "Is your job burning you out?", font=C.fuente(56), fill=(255, 255, 255), anchor="mm",
           stroke_width=6, stroke_fill=(10, 10, 12))
    return fondo

def final(lt):
    img = Image.new("RGB", (SW, SH), (8, 8, 10)); d = ImageDraw.Draw(img)
    a = M.suave((lt - 0.3)/0.6); c = int(8 + 240*a)
    d.text((SW/2, 880), "You only get one stick.", font=C.fuente(64), fill=(c, c, c), anchor="mm")
    d.text((SW/2, 980), "Don't let anyone", font=C.fuente(64), fill=(c, c, c), anchor="mm")
    d.text((SW/2, 1065), "burn it for you.", font=C.fuente(64), fill=(c, c, c), anchor="mm")
    b = M.suave((lt - 1.6)/0.6); c2 = int(8 + 150*b)
    d.text((SW/2, 1260), "Full film: BURNOUT", font=C.fuente(40), fill=(c2, c2, c2), anchor="mm")
    return img

def main():
    with wave.open(B.OUT + "burnout_audio.wav") as w:
        sr = w.getframerate(); aud = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    trozos = []; f = int(0.04*sr)
    for fn, a, b, _ in CORTES:
        s0, s1 = int((_I[fn] + a)*sr), int((_I[fn] + b)*sr)
        x = aud[s0:s1].copy(); x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f); trozos.append(x)
    s0 = int(B.FINAL*sr); x = aud[s0:s0 + int(FIN*sr)].copy(); x[:f] *= np.linspace(0, 1, f)
    x[-int(1.0*sr):] *= np.linspace(1, 0, int(1.0*sr)); trozos.append(x)
    pcm = np.concatenate(trozos).astype(np.int16)
    with wave.open(B.OUT + "burnout_short_audio.wav", "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{SW}x{SH}", "-r", str(B.FPS),
                          "-i", "-", "-i", B.OUT + "burnout_short_audio.wav", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                          "-preset", "medium", "-c:a", "aac", "-b:a", "160k", "-shortest", B.OUT + "BURNOUT_short.mp4"], stdin=subprocess.PIPE)
    for fn, a, b, caja in CORTES:
        for i in range(int(round((b - a)*B.FPS))):
            p.stdin.write(vertical(cuadro(fn, a + i/B.FPS, caja)).tobytes())
    for i in range(int(FIN*B.FPS)):
        p.stdin.write(final(i/B.FPS).tobytes())
    p.stdin.close(); p.wait()
    print("short: %.1f s" % (sum(b - a for _, a, b, _ in CORTES) + FIN))

if __name__ == "__main__":
    if sys.argv[1:] == ["fotos"]:
        ims = [vertical(cuadro(fn, (a + b)/2, caja)).resize((270, 480)) for fn, a, b, caja in CORTES]
        o = Image.new("RGB", (270*5, 480*2))
        for i, im in enumerate(ims): o.paste(im, ((i % 5)*270, (i//5)*480))
        o.save(B.OUT + "bo_short_fotos.jpg")
    else:
        main()
