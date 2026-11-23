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


def cierre(img, C, tl, tipo, lineas):
    """El cartel final: o te manda al video completo, o te cita mañana."""
    from estilo import AZUL, ROJO, VERDE, agente, ease, titular, tx  # noqa: F401
    velo = Image.new("RGBA", (W, H), OSCURO + (int(252*ease(tl/0.35)),))
    img.paste(velo, (0, 0), velo)
    k = tl/0.35
    if C.cruza(C.ini[-1] + 0.05):
        C.son("whoosh", 0.7)
    if tipo == "video":
        titular(img, [[(l, AMARILLO if i == 0 else BLANCO)] for i, l in enumerate(lineas)], 330, 104, k=k)
        agente(img, 540, 1060, 120, "guiño", C.t, "señala")
        d = ImageDraw.Draw(img, "RGBA")
        pulso = 1 + 0.06*np.sin(tl*7)
        f = F(64*pulso)
        s = "VÍDEO COMPLETO"
        w = d.textlength(s, font=f)
        y = 1240
        d.rounded_rectangle([W/2 - w/2 - 40, y - 52, W/2 + w/2 + 40, y + 52], radius=52, fill=AMARILLO + (255,))
        d.text((W/2, y), s, font=f, fill=OSCURO + (255,), anchor="mm")
        for j in range(3):          # flechas hacia abajo, donde YouTube pone el enlace al video
            yy = y + 76 + j*40 + (tl*50 % 40)
            a = int(255*max(0.0, 1 - j*0.3))
            d.polygon([(W/2 - 34, yy), (W/2 + 34, yy), (W/2, yy + 30)], fill=AMARILLO + (a,))
    elif tipo == "manana":
        titular(img, [[("MAÑANA", AMARILLO)]], 300, 130, k=k)
        titular(img, [[(l, BLANCO)] for l in lineas], 480, 92, k=(tl - 0.2)/0.35)
        agente(img, 540, 1150, 130, "guiño", C.t, "arriba")
    else:
        titular(img, [[("¿Qué simulo", BLANCO)], [("después?", AMARILLO)]], 330, 120, k=k)
        agente(img, 540, 1050, 130, "pensando", C.t, "cadera")
        titular(img, [[("Déjamelo en", BLANCO)], [("los comentarios", BLANCO)]], 1250, 72, k=(tl - 0.4)/0.35)
    return img


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
    ap.add_argument("--cierres", default="", help="mp3 de /narra cierres")
    ap.add_argument("--cierres-json", default="", help="duraciones de /narra cierres")
    ap.add_argument("--cierre", type=int, default=-1, help="que frase de los cierres va al final")
    ap.add_argument("--cierre-tipo", default="manana", choices=("video", "manana", "comentarios"))
    ap.add_argument("--cierre-texto", default="", help="lineas del cartel final, separadas por |")
    args = ap.parse_args()
    mod = importlib.import_module(args.short)

    info = json.loads(Path(args.duraciones).read_text())
    crudo = subprocess.run(["ffmpeg", "-v", "error", "-i", args.audio, "-f", "f32le", "-ac", "1", "-ar", str(SN.SR), "-"],
                           capture_output=True, check=True).stdout
    narr = np.frombuffer(crudo, np.float32).copy()
    narr /= max(1e-6, np.abs(narr).max())/0.9
    durs = list(info["duraciones"])
    textos = list(info["textos"])
    n_orig = len(durs)
    if args.cierre >= 0:
        # la frase final que abre la puerta (al video largo o al Short de mañana)
        ci = json.loads(Path(args.cierres_json).read_text())
        crudo_c = subprocess.run(["ffmpeg", "-v", "error", "-i", args.cierres, "-f", "f32le", "-ac", "1", "-ar",
                                  str(SN.SR), "-"], capture_output=True, check=True).stdout
        cn = np.frombuffer(crudo_c, np.float32).copy()
        cn /= max(1e-6, np.abs(cn).max())/0.9
        a0 = sum(ci["duraciones"][:args.cierre])
        dc = ci["duraciones"][args.cierre]
        clip = cn[int(a0*SN.SR):int((a0 + dc)*SN.SR)]
        hueco = 0.25
        narr = np.concatenate([narr[:int(sum(durs)*SN.SR)], np.zeros(int(hueco*SN.SR), np.float32), clip])
        durs[-1] += hueco
        durs.append(dc)
        textos.append(ci["textos"][args.cierre])
    info["textos"] = textos
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
        if args.cierre >= 0 and t >= inicios[n_orig]:
            # debajo, la ultima imagen del Short, apagada; encima, el cartel
            C.t = inicios[n_orig] - 0.05
            n_ev = len(C.eventos)
            img = mod.dibuja(img, C) or img
            del C.eventos[n_ev:]           # la imagen congelada no suena
            C.t = t
            img = cierre(img, C, t - inicios[n_orig], args.cierre_tipo, args.cierre_texto.split("|"))
        else:
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
