"""Montaje propio de un Short de España Contada, sin el bot y sin pagar voz.

Coge un guion hecho a mano (app/guiones_espana/<nombre>.json), dibuja cada
escena con los monigotes del canal y lo monta con:
  - voz neuronal GRATIS y local (Piper, voz es_ES "davefx", licencia CC0),
  - subtitulos grandes a trozos, con la palabra que suena en amarillo,
  - las cifras de pantalla cayendo como un sello, con su golpe,
  - camara que se mueve en cada plano y cortes con zoom y "whoosh",
  - musica de fondo sintetizada que baja cuando habla la voz,
  - cierre corto con el nombre del canal (y nada que corte el video a mitad).

    python3 montaje.py amadeo salida.mp4 [--voz DIR_VOZ] [--escenas 0,1,2]

La voz: el .onnx y el .onnx.json de Piper (se bajan de los releases de
GitHub de k2-fsa/sherpa-onnx, "vits-piper-es_ES-davefx-medium").
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
# config.py exige estas variables al importar; aqui no se llama a nada de fuera.
for k, v in (("ANTHROPIC_API_KEY", "x"), ("PEXELS_API_KEY", "x"), ("TELEGRAM_BOT_TOKEN", "x"),
             ("TELEGRAM_CHAT_ID", "1")):
    os.environ.setdefault(k, v)
from app import monigotes as M  # noqa: E402

W, H, FPS = 1080, 1920, 30
FPS_DIBUJO = 15
SR = 22050
FUENTE = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
AMARILLO, BLANCO, NEGRO, ROJO = (255, 214, 0), (255, 255, 255), (0, 0, 0), (196, 30, 40)
HUECO = 0.30           # silencio tras cada escena
TRANSICION = 0.20      # segundos de zoom al entrar en cada plano


# ---------------------------------------------------------------- la voz

def para_la_voz(texto: str) -> str:
    """Lo que se lee: sin comillas de bocadillo y con los numerales dichos."""
    t = texto.replace("«", "").replace("»", "")
    t = re.sub(r"\b(Isabel) II\b", r"\1 segunda", t)
    t = re.sub(r"\b([A-ZÁÉÍÓÚ][a-záéíóú]+) II\b", r"\1 segundo", t)
    t = re.sub(r"\b([A-ZÁÉÍÓÚ][a-záéíóú]+) III\b", r"\1 tercero", t)
    return t


_VOCES = {}


def fonemas(texto: str, voz_piper) -> list[list[str]]:
    """Los fonemas de cada frase, arreglados para el castellano. espeak marca
    un ACENTO SECUNDARIO (ˌ) en la primera silaba de muchas palabras, y la
    voz, que viene de una inglesa, lo pronuncia: decia Á-madeo, Í-sabel,
    ÉM-pezó, como con una tilde de mas. En castellano no existe: fuera. Y
    los diptongos a la inglesa (eɪ, eʊ) y la e abierta, a la española."""
    out = []
    for frase in voz_piper.phonemize(texto):
        palabras = []
        for w_ in "".join(frase).split(" "):
            # "sesenta y ocho" llega pegado (sesˌɛntaiʲˈotʃo): ahi el secundario
            # SI es acento de verdad, el de "sesenta"
            if re.search(r"ˌ[^ˈ]*ai[ʲ]?[^ˈ]*ˈ", w_):
                w_ = w_.replace("ˌ", "ˈ", 1)
            w_ = w_.replace("ˌ", "") if "ˈ" in w_ else w_.replace("ˌ", "ˈ")
            palabras.append(w_)
        s = " ".join(palabras)
        s = s.replace("eɪ", "ei").replace("eʊ", "eu").replace("ɛ", "e")
        out.append(list(s))
    return out


def voz(texto: str, dir_voz: Path, escala: float) -> np.ndarray:
    from piper import PiperVoice, SynthesisConfig
    modelo = next(dir_voz.glob("*.onnx"))
    if modelo not in _VOCES:
        _VOCES[modelo] = PiperVoice.load(str(modelo))
    v = _VOCES[modelo]
    cfg = SynthesisConfig(length_scale=escala, noise_scale=0.5, noise_w_scale=0.6)
    trozos = []
    for f in fonemas(texto, v):
        a = v.phoneme_ids_to_audio(v.phonemes_to_ids(f), cfg)
        a = np.asarray(a, np.float32).reshape(-1)
        if a.dtype != np.float32 or np.abs(a).max() > 1.5:
            a = a/32768.0
        trozos += [a, np.zeros(int(0.15*SR), np.float32)]
    a = np.concatenate(trozos)
    # fuera el silencio de los bordes, que es lo que hacia el ritmo lento
    vivo = np.where(np.abs(a) > 0.01)[0]
    if len(vivo):
        a = a[max(0, vivo[0] - 600):vivo[-1] + 1500]
    return a/max(1e-6, np.abs(a).max())*0.92


# ---------------------------------------------------------------- sonido

def _env(n, a=0.005, r=0.2):
    t = np.arange(n)/SR
    return np.minimum(1, t/a)*np.exp(-t/r)


def pulso(f, dur, vol=1.0, r=0.35):
    """Una nota pulsada (pizzicato): fundamental y dos armonicos que se apagan."""
    n = int(dur*SR)
    t = np.arange(n)/SR
    s = (np.sin(2*np.pi*f*t) + 0.4*np.sin(4*np.pi*f*t)*np.exp(-t*6) + 0.15*np.sin(6*np.pi*f*t)*np.exp(-t*9))
    return (s*_env(n, 0.004, r)*vol).astype(np.float32)


def musica(seg: float, bpm=104) -> np.ndarray:
    """Pizzicato alegre en bucle: Do - Sol - Lam - Fa, bajo y arpegio."""
    out = np.zeros(int(seg*SR) + SR, np.float32)
    negra = 60/bpm
    acordes = [(261.6, 329.6, 392.0), (196.0, 246.9, 293.7), (220.0, 261.6, 329.6), (174.6, 220.0, 261.6)]
    k = 0
    t = 0.0
    while t < seg:
        ac = acordes[(k//4) % 4]
        i = int(t*SR)
        if k % 4 == 0:
            b = pulso(ac[0]/2, 1.2, 0.9, 0.5)
            out[i:i + len(b)] += b[:len(out) - i]
        nota = ac[(0, 1, 2, 1)[k % 4]]*(2 if k % 8 >= 4 else 1)
        p = pulso(nota, 0.6, 0.55, 0.18)
        out[i:i + len(p)] += p[:len(out) - i]
        k += 1
        t += negra/2
    return out[:int(seg*SR)]


def whoosh(dur=0.28):
    n = int(dur*SR)
    rnd = np.random.default_rng(3)
    ruido = rnd.standard_normal(n).astype(np.float32)
    # filtro paso bajo que se abre y se cierra: el barrido del aire
    t = np.linspace(0, 1, n)
    corte = 0.02 + 0.25*np.sin(np.pi*t)
    y = np.zeros(n, np.float32)
    acc = 0.0
    for i in range(n):
        acc += corte[i]*(ruido[i] - acc)
        y[i] = acc
    return y/np.abs(y).max()*np.sin(np.pi*t)*0.35


def golpe(dur=0.45):
    """El sello: un bombo grave con un chasquido encima."""
    n = int(dur*SR)
    t = np.arange(n)/SR
    f = 50 + 120*np.exp(-t*25)
    s = np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*7)
    s[:200] += np.random.default_rng(1).standard_normal(200)*np.linspace(0.6, 0, 200)
    return (s*0.8).astype(np.float32)


def boing(dur=0.5):
    n = int(dur*SR)
    t = np.arange(n)/SR
    f = 220*(1 + 0.35*np.sin(2*np.pi*11*t)*np.exp(-t*4))*np.exp(-t*0.6)
    return (np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*4)*0.45).astype(np.float32)


def dron(dur):
    """Fondo grave y quieto para el momento serio."""
    n = int(dur*SR)
    t = np.arange(n)/SR
    s = np.sin(2*np.pi*55*t) + 0.5*np.sin(2*np.pi*82.4*t)
    fade = np.minimum(1, np.minimum(t/0.8, (dur - t)/0.8))
    return (s*fade*0.10).astype(np.float32)


def suma(pista, sonido, en):
    i = int(en*SR)
    if i >= len(pista):
        return
    trozo = sonido[:len(pista) - i]
    pista[i:i + len(trozo)] += trozo


# ---------------------------------------------------------------- textos

def fuente(t):
    return ImageFont.truetype(FUENTE, int(t))


def trozos(texto: str):
    """Subtitulos de 1 a 3 palabras, cortando en la puntuacion."""
    palabras = para_la_voz(texto).replace("...", "…").split()
    grupos, actual = [], []
    for p in palabras:
        actual.append(p)
        if len(actual) == 3 or re.search(r"[.,:;!?…]$", p):
            grupos.append(actual)
            actual = []
    if actual:
        grupos.append(actual)
    return grupos


def tiempos_de_palabras(grupos, dur):
    """Sin marcas de tiempo de la voz: cada palabra se lleva un tiempo segun
    sus letras, y la puntuacion una pausa."""
    pesos = []
    for g in grupos:
        for p in g:
            pesos.append(len(p) + 2 + (4 if re.search(r"[.,:;!?…]$", p) else 0))
    total = sum(pesos)
    t, out, k = 0.0, [], 0
    for g in grupos:
        fila = []
        for p in g:
            d = dur*pesos[k]/total
            fila.append((p, t, t + d))
            t += d
            k += 1
        out.append(fila)
    return out


def pinta_subtitulo(img, fila, ahora):
    """El trozo que toca, grande y centrado; la palabra que suena, en amarillo."""
    d = ImageDraw.Draw(img)
    ini = fila[0][1]
    pop = min(1.0, (ahora - ini)/0.09)
    escala = 0.85 + 0.15*pop
    f = fuente(96*escala)
    textos = [p for p, _, _ in fila]
    esp = d.textlength(" ", font=f)
    anchos = [d.textlength(p, font=f) for p in textos]
    total = sum(anchos) + esp*(len(textos) - 1)
    if total > W*0.9:
        f = fuente(96*escala*W*0.9/total)
        anchos = [d.textlength(p, font=f) for p in textos]
        esp = d.textlength(" ", font=f)
        total = sum(anchos) + esp*(len(textos) - 1)
    x = (W - total)/2
    y = H*0.665
    for (p, a, b), w_ in zip(fila, anchos):
        color = AMARILLO if a <= ahora < b or (ahora >= b and (p, a, b) == fila[-1]) else BLANCO
        d.text((x, y), p, font=f, fill=color, stroke_width=11, stroke_fill=NEGRO, anchor="lm")
        x += w_ + esp


def pinta_sello(img, texto, t):
    """La cifra que cae como un sello: grande, roja, torcida, y se queda."""
    if t < 0:
        return
    s = 1.0 + 0.9*max(0.0, 1 - t/0.14)**2
    d0 = ImageDraw.Draw(Image.new("L", (1, 1)))
    # que quepa: el sello entero, con su borde y torcido, en el 86% del ancho
    base = min(118.0, 118.0*(W*0.80)/max(1.0, d0.textlength(texto, font=fuente(118)) + 60))
    s *= base/118
    f = fuente(118*s)
    tw = d0.textlength(texto, font=f)
    pad = 30*s
    capa = Image.new("RGBA", (int(tw + pad*2), int(118*s*1.45)), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    d.rounded_rectangle([0, 0, capa.width - 1, capa.height - 1], radius=int(18*s), fill=ROJO + (255,),
                        outline=BLANCO + (255,), width=max(4, int(8*s)))
    d.text((capa.width/2, capa.height/2), texto, font=f, fill=BLANCO, anchor="mm")
    capa = capa.rotate(3, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(capa, (int(W/2 - capa.width/2), int(H*0.17 - capa.height/2)))


# ---------------------------------------------------------------- camara

def camara(img, p, sentido, entra):
    """Empuje lento de la camara en todo el plano; al entrar, un zoom rapido
    que frena (el corte con 'whoosh')."""
    z = 1.0 + 0.06*(p if sentido > 0 else 1 - p)
    z += 0.22*(1 - entra)**3
    cw, ch = W/z, H/z
    dx = (W - cw)*(0.5 + 0.25*sentido*(p - 0.5))
    dy = (H - ch)*0.45
    return img.crop((int(dx), int(dy), int(dx + cw), int(dy + ch))).resize((W, H), Image.BILINEAR)


def cierre(ultimo: Image.Image, t, dur):
    p = min(1.0, t/0.35)
    img = Image.blend(ultimo.convert("RGB"), Image.new("RGB", (W, H), (18, 16, 20)), 0.82*p).convert("RGBA")
    d = ImageDraw.Draw(img)
    s = 0.8 + 0.2*min(1.0, t/0.2)
    d.text((W/2, H*0.42), "ESPAÑA", font=fuente(150*s), fill=BLANCO, anchor="mm")
    d.text((W/2, H*0.50), "CONTADA", font=fuente(150*s), fill=AMARILLO, anchor="mm")
    if t > 0.35:
        d.text((W/2, H*0.60), "Historia de España · 2º Bachillerato", font=fuente(52), fill=BLANCO, anchor="mm")
        d.text((W/2, H*0.66), "Sígueme para la siguiente", font=fuente(52), fill=(200, 200, 200), anchor="mm")
    return img


# ---------------------------------------------------------------- montaje

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("nombre")
    ap.add_argument("salida")
    ap.add_argument("--voz", default=str(Path(__file__).parent / "voz" / "vits-piper-es_ES-davefx-medium"))
    ap.add_argument("--rapidez", type=float, default=0.88, help="length-scale de Piper: menos es mas rapido")
    ap.add_argument("--escenas", default="")
    args = ap.parse_args()

    guion = json.loads((RAIZ / "app" / "guiones_espana" / f"{args.nombre}.json").read_text())
    escenas = guion["scenes"]
    cuales = [int(i) for i in args.escenas.split(",")] if args.escenas else list(range(len(escenas)))

    # 1. la voz de cada escena, y de ahi lo que dura
    voces = []
    for i in cuales:
        a = voz(para_la_voz(escenas[i]["narration"]), Path(args.voz), args.rapidez)
        voces.append(a)
        print(f"voz {i + 1}: {len(a)/SR:.1f}s", flush=True)
    durs = [len(a)/SR + HUECO for a in voces]
    CIERRE = 2.0
    total = sum(durs) + CIERRE
    starts = np.cumsum([0] + durs[:-1])

    # 2. el sonido: voz, musica que se aparta, golpes y cortes
    pista_voz = np.zeros(int(total*SR) + SR, np.float32)
    for s, a in zip(starts, voces):
        suma(pista_voz, a, s + 0.05)
    musi = musica(total + 1)[:len(pista_voz)]
    # se aparta cuando habla: envolvente de la voz, suavizada
    env = np.abs(pista_voz)
    k = int(0.25*SR)
    env = np.convolve(env, np.ones(k)/k, mode="same")
    vol = 0.16 - 0.10*np.clip(env*12, 0, 1)
    serio = [n for n, i in enumerate(cuales) if "atentado" in escenas[i]["narration"]]
    for n in serio:                                     # el momento serio, sin musica
        a, b = int(starts[n]*SR), int((starts[n] + durs[n])*SR)
        rampa = int(0.4*SR)
        vol[max(0, a - rampa):a] *= np.linspace(1, 0, min(rampa, a))
        vol[a:b] = 0
        vol[b:b + rampa] *= np.linspace(0, 1, len(vol[b:b + rampa]))
    pista = pista_voz + musi*vol
    for n, s in enumerate(starts):
        if n:
            suma(pista, whoosh(), s - 0.12)
        if escenas[cuales[n]].get("on_screen_highlight"):
            suma(pista, golpe(), s + 0.12)
        if "¡Menudo" in escenas[cuales[n]]["narration"]:
            suma(pista, boing(), s + durs[n] - HUECO - 0.55)
    for n in serio:
        suma(pista, dron(durs[n]), starts[n])
    suma(pista, golpe(), sum(durs))
    pista = np.tanh(pista*1.2)*0.9
    wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    with wave.open(wav, "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR)
        f.writeframes((pista[:int(total*SR)]*32767).astype(np.int16).tobytes())

    # 3. la imagen
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium",
                           "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
                           "-movflags", "+faststart", args.salida], stdin=subprocess.PIPE)
    ultimo = None
    for n, i in enumerate(cuales):
        e = escenas[i]
        dur = durs[n]
        habla = len(voces[n])/SR
        filas = tiempos_de_palabras(trozos(e["narration"]), habla)
        dibujos = M.animar(M.limpia(e["escena"]), segundos=dur, fps=FPS_DIBUJO, tam=(W, H),
                           una_vez=True, una_vez_desde=0.4)
        sentido = 1 if n % 2 == 0 else -1
        dibujo = None
        nfr = int(round(dur*FPS))
        for fr in range(nfr):
            t = fr/FPS
            if fr % (FPS//FPS_DIBUJO) == 0:
                try:
                    dibujo = next(dibujos)
                except StopIteration:
                    pass
                if not isinstance(dibujo, Image.Image):
                    dibujo = Image.fromarray(dibujo)
            img = camara(dibujo.convert("RGB"), t/dur, sentido, min(1.0, t/TRANSICION)).convert("RGBA")
            ultimo = img.copy()            # el cierre, sobre el plano limpio
            if e.get("on_screen_highlight"):
                pinta_sello(img, e["on_screen_highlight"], t - 0.10)
            hab = t - 0.05
            fila = next((f for f in filas if f[0][1] <= hab < f[-1][2]), None)
            if fila is None and hab >= 0 and filas and hab < habla + 0.25:
                fila = filas[-1]
            if fila:
                pinta_subtitulo(img, fila, hab)
            ff.stdin.write(img.convert("RGB").tobytes())
        print(f"escena {i + 1}: {dur:.1f}s", flush=True)
    for fr in range(int(CIERRE*FPS)):
        ff.stdin.write(cierre(ultimo, fr/FPS, CIERRE).convert("RGB").tobytes())
    ff.stdin.close()
    ff.wait()
    os.unlink(wav)
    print(f"hecho: {args.salida} ({total:.1f}s)")


if __name__ == "__main__":
    main()
