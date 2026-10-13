"""Short vertical (1080x1920) de ONE MORE: los mejores momentos en ~45 s."""
import subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, str(Path(__file__).resolve().parent))
import one_more as M
import corto as C

SW, SH = 1080, 1920
# (función, desde, hasta (segundos dentro del plano), centro x del recorte cuadrado)
CORTES = [
    (M.p_cama_lunes, 0.6, 4.8, (820, 1560)),
    (M.p_lapso_lunes, 0.0, 6.0, 960),
    (M.p_cama_720, 0.0, 2.6, 950),
    (M.p_ofi_martes_1, 0.2, 5.5, (790, 1320)),
    (M.p_ofi_martes_2, 0.3, 4.3, 700),
    (M.p_reflejo, 0.5, 4.5, 800),
    (M.p_jueves_despierta, 0.6, 5.0, 950),
    (M.p_ofi_jueves_1, 0.2, 5.3, (790, 1320)),
    (M.p_ofi_jueves_2, 0.2, 4.4, 700),
]
FIN = 4.5
_inicio = {fn: a for a, b, fn, s in M.TABLA}

def cuadro(fn, lt, cxr):
    img, (cx, cy, z) = fn(lt, _inicio[fn] + lt)
    img = C.recorte(img, cx, cy, z) if z > 1.001 or abs(cx - C.CW/2) > 1 else img
    ancho = 1100
    if isinstance(cxr, tuple): cxr, ancho = cxr
    x0 = min(max(0, cxr - ancho/2), C.CW - ancho)
    return img.crop((int(x0), 0, int(x0) + ancho, 900))

def vertical(cuad, titulo=True):
    fondo = cuad.resize((SH, SH)).crop(((SH - SW)//2, 0, (SH - SW)//2 + SW, SH)).filter(ImageFilter.GaussianBlur(40))
    fondo = M.oscurece(fondo, 0.55)
    alto = int(SW*cuad.height/cuad.width)
    fondo.paste(cuad.resize((SW, alto), Image.LANCZOS), (0, (SH - alto)//2))
    if titulo:
        d = ImageDraw.Draw(fondo)
        d.text((SW/2, 330), "Why am I always so tired?", font=C.fuente(60), fill=(255, 255, 255), anchor="mm",
               stroke_width=6, stroke_fill=(10, 10, 12))
    return fondo

def final(lt):
    img = Image.new("RGB", (SW, SH), (8, 8, 10)); d = ImageDraw.Draw(img)
    a = M.suave((lt - 0.3)/0.6)
    c = int(8 + 240*a)
    d.text((SW/2, 860), "One more video", font=C.fuente(70), fill=(c, c, c), anchor="mm")
    d.text((SW/2, 950), "always costs", font=C.fuente(70), fill=(c, c, c), anchor="mm")
    d.text((SW/2, 1040), "one more morning.", font=C.fuente(70), fill=(c, c, c), anchor="mm")
    b = M.suave((lt - 1.6)/0.6); c2 = int(8 + 150*b)
    d.text((SW/2, 1250), "Full film: ONE MORE", font=C.fuente(40), fill=(c2, c2, c2), anchor="mm")
    return img

def main():
    Path(M.OUT).mkdir(exist_ok=True)
    total = sum(b - a for _, a, b, _ in CORTES) + FIN
    # sonido: los mismos trozos del audio del vídeo largo, con fundidos cortos
    with wave.open(M.OUT + "one_more_audio.wav") as w:
        sr = w.getframerate(); aud = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    trozos = []
    f = int(0.04*sr)
    for fn, a, b, _ in CORTES:
        s0, s1 = int((_inicio[fn] + a)*sr), int((_inicio[fn] + b)*sr)
        x = aud[s0:s1].copy(); x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        trozos.append(x)
    s0 = int(M.FINAL*sr); x = aud[s0:s0 + int(FIN*sr)].copy(); x[:f] *= np.linspace(0, 1, f)
    x[-int(1.0*sr):] *= np.linspace(1, 0, int(1.0*sr)); trozos.append(x)
    pcm = np.concatenate(trozos).astype(np.int16)
    with wave.open(M.OUT + "short_audio.wav", "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{SW}x{SH}", "-r", str(M.FPS),
                          "-i", "-", "-i", M.OUT + "short_audio.wav", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                          "-preset", "medium", "-c:a", "aac", "-b:a", "160k", "-shortest", M.OUT + "ONE_MORE_short.mp4"],
                         stdin=subprocess.PIPE)
    for fn, a, b, cxr in CORTES:
        n = int(round((b - a)*M.FPS))
        for i in range(n):
            p.stdin.write(vertical(cuadro(fn, a + i/M.FPS, cxr)).tobytes())
    for i in range(int(FIN*M.FPS)):
        p.stdin.write(final(i/M.FPS).tobytes())
    p.stdin.close(); p.wait()
    print(f"short: {total:.1f} s")

if __name__ == "__main__":
    if sys.argv[1:] == ["foto"]:
        vertical(cuadro(M.p_ofi_martes_1, 4.0, (790, 1320))).resize((540, 960)).save(M.OUT + "short_foto.jpg")
    else:
        main()
