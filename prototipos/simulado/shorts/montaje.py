"""Montador comun de los Shorts verticales de Lo he simulado.

Cada Short es un modulo con una funcion dibuja(img, C) que pinta el fotograma
del instante C.t. Aqui va lo comun: la voz (su mp3 de /narra y las
duraciones), saber cuando suena cada palabra (pausas reales del audio), los
subtitulos grandes de 1-3 palabras, la musica, los efectos y el render.

    python3 montaje.py cumple salida.mp4 --audio X.mp3 --duraciones X.json [--fotos hoja.png]
"""
import argparse
import importlib
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sonido as SN  # noqa: E402
from alinea import tiempos as alinear  # noqa: E402
from estilo import AMARILLO, BLANCO, FPS, H, OSCURO, W, F, fondo, marca, sale  # noqa: E402


def norm(p):
    p = unicodedata.normalize("NFD", p.lower())
    p = "".join(c for c in p if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w]", "", p)


class Ctx:
    """Lo que sabe cada fotograma: tiempo total, escena, palabras y eventos de sonido."""

    def __init__(self, palabras, inicios, durs):
        self.pal = palabras          # por escena: [(palabra, ini_abs, fin_abs)]
        self.ini = inicios
        self.durs = durs
        self.t = 0.0
        self.eventos = []

    @property
    def esc(self):
        for k in range(len(self.ini) - 1, -1, -1):
            if self.t >= self.ini[k]:
                return k
        return 0

    @property
    def tl(self):
        """Tiempo dentro de la escena actual."""
        return self.t - self.ini[self.esc]

    def en(self, escena, palabra, n=1, exacta=False):
        """Segundo (absoluto) en que empieza esa palabra en esa escena."""
        q = norm(palabra)
        vistos = 0
        for p, a, _ in self.pal[escena]:
            w = norm(p)
            if (w == q) if exacta else w.startswith(q):
                vistos += 1
                if vistos == n:
                    return a
        print(f"  ! escena {escena}: no encuentro «{palabra}»", flush=True)
        return self.ini[escena] + self.durs[escena]/2

    def cruza(self, te):
        return self.t <= te < self.t + 1/FPS

    def son(self, tipo, vol=1.0, en=None):
        self.eventos.append((self.t if en is None else en, tipo, vol))


def trozos_sub(palabras):
    """Subtitulos de 1 a 3 palabras, cortando en la puntuacion."""
    out, cur = [], []
    for p in palabras:
        cur.append(p)
        if len(cur) == 3 or re.search(r"[.,:;!?…]$", p[0]) or sum(len(x[0]) for x in cur) > 16:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def subtitulo(img, grupos, t, y=1470):
    fila = None
    for k, g in enumerate(grupos):
        fin = grupos[k + 1][0][1] if k + 1 < len(grupos) else g[-1][2] + 0.4
        if g[0][1] - 0.05 <= t < fin:
            fila = g
            break
    if not fila:
        return
    d = ImageDraw.Draw(img, "RGBA")
    k = sale((t - fila[0][1] + 0.05)/0.12)
    f = F(84*(0.85 + 0.15*k))
    textos = [p.upper().strip("…") for p, _, _ in fila]
    anchos = [d.textlength(s + " ", font=f) for s in textos]
    total = sum(anchos) - d.textlength(" ", font=f)
    if total > W - 80:
        f = F(84*(W - 80)/total)
        anchos = [d.textlength(s + " ", font=f) for s in textos]
        total = sum(anchos) - d.textlength(" ", font=f)
    x = W/2 - total/2
    for (p, a, b), s, w in zip(fila, textos, anchos):
        col = AMARILLO if a <= t < b + 0.08 else BLANCO
        d.text((x + 5, y + 7), s, font=f, fill=(0, 0, 0, 150), anchor="lm", stroke_width=12, stroke_fill=(0, 0, 0, 150))
        d.text((x, y), s, font=f, fill=col + (255,), anchor="lm", stroke_width=12, stroke_fill=OSCURO + (255,))
        x += w


def mezcla(total, narr, eventos, alegre=True):
    pista = np.zeros(int((total + 0.5)*SN.SR), np.float32)
    voz = np.zeros_like(pista)
    voz[:min(len(narr), len(voz))] = narr[:len(voz)]
    musi = SN.musica(total + 0.5, alegre=alegre)[:len(pista)]
    musi = np.pad(musi, (0, len(pista) - len(musi)))
    env = np.convolve(np.abs(voz), np.ones(int(0.25*SN.SR))/int(0.25*SN.SR), mode="same")
    duck = 0.20 - 0.12*np.clip(env*10, 0, 1)
    tt = np.arange(len(pista))/SN.SR
    duck *= np.clip((total + 0.3 - tt)/0.8, 0, 1)
    efectos = np.zeros_like(pista)
    rnd = np.random.default_rng(7)
    for t, tipo, vol in eventos:
        s = {"tic": lambda: SN.tic(rnd, 0.06*vol), "ding": lambda: SN.ding(rnd.choice([1046.5, 1174.7, 1318.5]), 0.55*vol),
             "pop": lambda: SN.pop(0.6*vol), "golpe": lambda: SN.golpe(0.7*vol), "whoosh": lambda: SN.whoosh(vol=0.8*vol)}.get(tipo)
        if s:
            SN.suma(efectos, s(), t)
    return np.tanh((voz + musi*duck + efectos)*1.1)*0.92


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("short")
    ap.add_argument("salida")
    ap.add_argument("--audio", required=True)
    ap.add_argument("--duraciones", required=True)
    ap.add_argument("--fotos", default="")
    ap.add_argument("--cola", type=float, default=0.6)
    ap.add_argument("--portada", default="", help="guarda un fotograma sin subtitulos (la portada del Short)")
    ap.add_argument("--en", type=float, default=1.6, help="segundo del fotograma de la portada")
    args = ap.parse_args()
    mod = importlib.import_module(args.short)

    info = json.loads(Path(args.duraciones).read_text())
    crudo = subprocess.run(["ffmpeg", "-v", "error", "-i", args.audio, "-f", "f32le", "-ac", "1", "-ar", str(SN.SR), "-"],
                           capture_output=True, check=True).stdout
    narr = np.frombuffer(crudo, np.float32).copy()
    narr /= max(1e-6, np.abs(narr).max())/0.9
    durs = list(info["duraciones"])
    inicios = list(np.cumsum([0] + durs[:-1]))
    palabras = []
    for k, (s, dv) in enumerate(zip(inicios, durs)):
        trozo = narr[int(s*SN.SR):int((s + dv)*SN.SR)]
        palabras.append([(p, a + s, b + s) for p, a, b in alinear(info["textos"][k], trozo, SN.SR)])
    total = sum(durs) + args.cola
    C = Ctx(palabras, inicios, durs)
    if hasattr(mod, "prepara"):
        mod.prepara(C)
    grupos = trozos_sub([p for esc in palabras for p in esc])

    def frame(t):
        C.t = t
        img = fondo()
        img = mod.dibuja(img, C) or img
        subtitulo(img, grupos, t)
        marca(img)
        return img

    if args.portada:
        C.t = args.en
        mod.agente = lambda *a, **k: None      # en la portada el Agente va solo en grande (portadas.py)
        img = mod.dibuja(fondo(), C) or fondo()
        marca(img)
        img.save(args.portada)
        return

    if args.fotos:
        ts = [inicios[k] + durs[k]*f for k in range(len(durs)) for f in (0.15, 0.75)]
        fotos = [frame(t).resize((270, 480), Image.LANCZOS) for t in ts]
        cols = 6
        hoja = Image.new("RGB", (270*cols, 480*((len(fotos) + cols - 1)//cols)), "white")
        for k, f in enumerate(fotos):
            hoja.paste(f, ((k % cols)*270, (k//cols)*480))
        hoja.save(args.fotos)
        return

    tmp = Path(tempfile.mkdtemp(prefix="short_"))
    video = tmp/"video.mp4"
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                           "-pix_fmt", "yuv420p", str(video)], stdin=subprocess.PIPE)
    for fr in range(int(round(total*FPS))):
        ff.stdin.write(frame(fr/FPS).tobytes())
    ff.stdin.close()
    ff.wait()
    pista = mezcla(total, narr, C.eventos, getattr(mod, "ALEGRE", True))
    wav = tmp/"pista.wav"
    with wave.open(str(wav), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SN.SR)
        f.writeframes((np.clip(pista, -1, 1)*32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-i", str(wav), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", args.salida], check=True)
    print(f"hecho: {args.salida} ({total:.1f} s)", flush=True)


if __name__ == "__main__":
    main()
