"""Amadeo de Saboya con los muñecos nuevos, los fondos y las banderas de la
epoca, la voz gratis y el montaje de montaje.py.

    python3 amadeo_nuevo.py salida.mp4 [--escenas 0,1,2] [--fotos hoja.png]
"""
import argparse
import json
import math
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import fondos as F
import montaje as MJ
from munecos import REPARTO, Muneco, pinta

W, H, FPS = MJ.W, MJ.H, MJ.FPS
SUELO = int(H*F.SUELO)
P = {k: Muneco(**v) for k, v in REPARTO.items()}
_cache = {}


def fondo(nombre, **kw):
    clave = (nombre, tuple(sorted(kw.items())))
    if clave not in _cache:
        _cache[clave] = getattr(F, nombre)(**kw)
    return _cache[clave].copy()


def rotulo(img, texto):
    f = ImageFont.truetype(F.FUENTE, 44)
    d = ImageDraw.Draw(img)
    w = d.textlength(texto, font=f) + 60
    d.rounded_rectangle([W/2 - w/2, 70, W/2 + w/2, 140], radius=30, fill=(190, 22, 34), outline=(255, 255, 255), width=4)
    d.text((W/2, 105), texto, font=f, fill=(255, 255, 255), anchor="mm")


def mesa_con_corona(img, x, suelo):
    d = ImageDraw.Draw(img)
    d.rectangle([x - 150, suelo - 300, x + 150, suelo - 270], fill=(120, 76, 44), outline=F.TINTA, width=4)
    for lx in (x - 130, x + 120):
        d.rectangle([lx, suelo - 270, lx + 12, suelo], fill=(100, 62, 36), outline=F.TINTA, width=3)
    cx, top, s = x, suelo - 300, 105
    d.polygon([(cx - s, top), (cx - s*1.1, top - s*1.1), (cx - s*0.5, top - s*0.6), (cx, top - s*1.3),
               (cx + s*0.5, top - s*0.6), (cx + s*1.1, top - s*1.1), (cx + s, top)], fill=F.ORO, outline=F.TINTA)
    for k, col in ((-0.5, (40, 90, 200)), (0, (200, 30, 40)), (0.5, (40, 160, 80))):
        d.ellipse([cx + s*k - 10, top - 40, cx + s*k + 10, top - 20], fill=col)


def habla(t, rapido=11):
    return max(0.0, math.sin(t*rapido))*0.8


# Cada escena: (fondo, funcion que pinta encima). t va de 0 a dur.
def e1(t, dur):
    img = fondo("despacho")
    pinta(img, P["prim"], 540, SUELO + 60, 1000, "catalejo", "neutro", t)
    return img


def e2(t, dur):
    img = fondo("palacio")
    pinta(img, P["amadeo"], 540, SUELO + 60, 1000, "encoge", "asustado", t, efecto="sudor", gorro="corona")
    return img


def e3(t, dur):
    img = fondo("palacio")
    p = min(1.0, t/dur)
    pinta(img, P["isabel"], 480 + p*560, SUELO + 40, 820, "de_pie", "enfadado", t, anda=True)
    rotulo(img, "Madrid, 1868")
    return img


def e4(t, dur):
    img = fondo("congreso")
    pinta(img, P["prim"], 320, SUELO + 50, 820, "libro", "contento", t)
    pinta(img, P["diputado"], 780, SUELO + 50, 820, "encoge", "sorpresa", t + 1.3, desde="de_pie", llega=0.5)
    return img


def e5(t, dur):
    img = fondo("despacho")
    F.bandera(img, "francia", 520, SUELO - 60, 260, t, nombre="FRANCIA", alto_asta=2.6)
    F.bandera(img, "prusia", 800, SUELO - 60, 260, t + 0.7, nombre="PRUSIA", alto_asta=2.6)
    pinta(img, P["prim"], 290, SUELO + 60, 900, "brazos_arriba", "asustado", t, efecto="sudor")
    return img


def e6(t, dur):
    img = fondo("palacio")
    F.bandera(img, "italia", 110, SUELO, 240, t, nombre="ITALIA", alto_asta=3.0)
    pinta(img, P["amadeo"], 600, SUELO + 60, 1000, "brazos_arriba", "contento", t, gorro="corona")
    return img


def e7(t, dur):
    img = fondo("puerto")
    pinta(img, P["amadeo"], 540, SUELO + 80, 900, "triste", "triste", t, llega=1.0)
    rotulo(img, "Cartagena, 30 de diciembre de 1870")
    return img


def e8(t, dur):
    img = fondo("calle")
    pinta(img, P["dama"], 640, SUELO + 50, 760, "jarras", "enfadado", t)
    pinta(img, P["dama_negro"], 900, SUELO + 50, 760, "jarras", "enfadado", t + 0.8)
    pinta(img, P["amadeo"], 260, SUELO + 60, 820, "encoge", "sorpresa", t, efecto="confuso", gorro="corona")
    return img


def e9(t, dur):
    img = fondo("palacio")
    pinta(img, P["carlista"], 210, SUELO + 60, 680, "señala", "enfadado", t, habla=habla(t))
    pinta(img, P["diputado"], 870, SUELO + 60, 680, "señala_izq", "enfadado", t + 0.5, habla=habla(t + 0.4))
    pinta(img, P["amadeo"], 540, SUELO + 90, 860, "encoge", "asustado", t, efecto="mareo", gorro="corona")
    return img


def e10(t, dur):
    img = fondo("despacho")
    mesa_con_corona(img, 790, SUELO + 40)
    pinta(img, P["amadeo"], 360, SUELO + 60, 960, "señala", "enfadado", t)
    return img


def e11(t, dur):
    img = fondo("congreso")
    pinta(img, P["diputado"], 660, SUELO + 50, 700, "brazos_arriba", "enfadado", t, habla=habla(t))
    pinta(img, P["diputado2"], 900, SUELO + 50, 700, "señala_izq", "enfadado", t + 0.3, habla=habla(t + 0.3, 13))
    pinta(img, P["amadeo"], 260, SUELO + 70, 860, "señala", "enfadado", t)
    return img


def e12(t, dur):
    img = fondo("congreso", tipo_bandera="republica")
    pinta(img, P["diputado"], 330, SUELO + 50, 820, "brazos_arriba", "contento", t, habla=habla(t, 8))
    pinta(img, P["diputado2"], 560, SUELO + 50, 760, "brazos_arriba", "contento", t + 0.6)
    F.bandera(img, "republica", 760, SUELO + 40, 290, t)
    return img


def e13(t, dur):
    img = fondo("puerto")
    p = min(1.0, t/dur)
    pinta(img, P["amadeo"], 540 + p*260, SUELO + 60 - p*60, 900 - p*200, "de_pie", "contento", t, anda=True)
    return img


ESCENAS = [e1, e2, e3, e4, e5, e6, e7, e8, e9, e10, e11, e12, e13]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("salida")
    ap.add_argument("--escenas", default="")
    ap.add_argument("--fotos", default="")
    ap.add_argument("--rapidez", type=float, default=0.88)
    args = ap.parse_args()
    guion = json.loads((MJ.RAIZ / "app" / "guiones_espana" / "amadeo.json").read_text())
    escenas = guion["scenes"]
    assert len(escenas) == len(ESCENAS), "el guion y las escenas dibujadas no cuadran"
    cuales = [int(i) for i in args.escenas.split(",")] if args.escenas else list(range(len(escenas)))

    if args.fotos:                     # una hoja con un fotograma de cada escena, para revisar
        fotos = [ESCENAS[i](1.2, 2.5).convert("RGB").resize((270, 480)) for i in cuales]
        hoja = Image.new("RGB", (270*min(7, len(fotos)), 480*((len(fotos) + 6)//7)), "white")
        for k, f in enumerate(fotos):
            hoja.paste(f, ((k % 7)*270, (k//7)*480))
        hoja.save(args.fotos)
        return

    dir_voz = Path(__file__).parent / "voz" / "vits-piper-es_ES-davefx-medium"
    voces = [MJ.voz(MJ.para_la_voz(escenas[i]["narration"]), dir_voz, args.rapidez) for i in cuales]
    durs = [len(a)/MJ.SR + MJ.HUECO for a in voces]
    CIERRE = 2.0
    total = sum(durs) + CIERRE
    starts = np.cumsum([0] + durs[:-1])

    pista_voz = np.zeros(int(total*MJ.SR) + MJ.SR, np.float32)
    for s, a in zip(starts, voces):
        MJ.suma(pista_voz, a, s + 0.05)
    musi = MJ.musica(total + 1)[:len(pista_voz)]
    env = np.convolve(np.abs(pista_voz), np.ones(int(0.25*MJ.SR))/int(0.25*MJ.SR), mode="same")
    vol = 0.16 - 0.10*np.clip(env*12, 0, 1)
    serio = [n for n, i in enumerate(cuales) if "atentado" in escenas[i]["narration"]]
    for n in serio:
        a, b = int(starts[n]*MJ.SR), int((starts[n] + durs[n])*MJ.SR)
        r = int(0.4*MJ.SR)
        vol[max(0, a - r):a] *= np.linspace(1, 0, min(r, a))
        vol[a:b] = 0
        vol[b:b + r] *= np.linspace(0, 1, len(vol[b:b + r]))
    pista = pista_voz + musi*vol
    for n, s in enumerate(starts):
        if n:
            MJ.suma(pista, MJ.whoosh(), s - 0.12)
        if escenas[cuales[n]].get("on_screen_highlight"):
            MJ.suma(pista, MJ.golpe(), s + 0.12)
        if "¡Menudo" in escenas[cuales[n]]["narration"]:
            MJ.suma(pista, MJ.boing(), s + durs[n] - MJ.HUECO - 0.55)
    for n in serio:
        MJ.suma(pista, MJ.dron(durs[n]), starts[n])
    MJ.suma(pista, MJ.golpe(), sum(durs))
    pista = np.tanh(pista*1.2)*0.9
    wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    with wave.open(wav, "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(MJ.SR)
        f.writeframes((pista[:int(total*MJ.SR)]*32767).astype(np.int16).tobytes())

    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                           args.salida], stdin=subprocess.PIPE)
    ultimo = None
    for n, i in enumerate(cuales):
        e = escenas[i]
        dur = durs[n]
        hablado = len(voces[n])/MJ.SR
        filas = MJ.tiempos_de_palabras(MJ.trozos(e["narration"]), hablado)
        sentido = 1 if n % 2 == 0 else -1
        dibujo = None
        for fr in range(int(round(dur*FPS))):
            t = fr/FPS
            if fr % 2 == 0:            # el dibujo a 15 fps, la camara a 30
                dibujo = ESCENAS[i](t, dur).convert("RGB")
            img = MJ.camara(dibujo, t/dur, sentido, min(1.0, t/MJ.TRANSICION)).convert("RGBA")
            ultimo = img.copy()
            if e.get("on_screen_highlight"):
                MJ.pinta_sello(img, e["on_screen_highlight"], t - 0.10)
            hab = t - 0.05
            fila = next((f_ for f_ in filas if f_[0][1] <= hab < f_[-1][2]), None)
            if fila is None and hab >= 0 and filas and hab < hablado + 0.25:
                fila = filas[-1]
            if fila:
                MJ.pinta_subtitulo(img, fila, hab)
            ff.stdin.write(img.convert("RGB").tobytes())
        print(f"escena {i + 1}: {dur:.1f}s", flush=True)
    for fr in range(int(CIERRE*FPS)):
        ff.stdin.write(MJ.cierre(ultimo, fr/FPS, CIERRE).convert("RGB").tobytes())
    ff.stdin.close()
    ff.wait()
    print(f"hecho: {args.salida} ({total:.1f}s)")


if __name__ == "__main__":
    main()
