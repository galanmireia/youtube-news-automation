"""Efectos de sonido sintetizados, no descargados.

Misma idea que los monigotes y por las mismas razones: gratis, iguales en
todos los videos, sin licencias que revisar - y sobre todo, SIN DEPENDER DE
UN BANCO DE SONIDOS. Un fichero de Pixabay que cambia de licencia deja un
video desmonetizado meses despues; una onda calculada aqui no.

No pretenden engañar a nadie. Son efectos de dibujo animado, que es
exactamente lo que pide un video de palotes: un golpe, una campana, un
gentio de fondo. Se mezclan MUY por debajo de la voz - la voz es el video.

Como esto no lo puedo oir, cada efecto se comprueba midiendolo: duracion,
volumen y centro espectral (si el sonido es grave o agudo). Una campana que
saliera grave y sorda no la oigo, pero la veo en el numero.
"""
from __future__ import annotations

import logging
import math
import wave
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

HZ = 44100


def _ruido(n, rng, color=0.0):
    """Ruido con inclinacion espectral: 0 blanco, 1 rosa, 2 marron."""
    blanco = rng.standard_normal(n)
    if color <= 0:
        return blanco
    espectro = np.fft.rfft(blanco)
    f = np.fft.rfftfreq(n, 1/HZ)
    f[0] = f[1] if len(f) > 1 else 1.0
    return np.fft.irfft(espectro / f**(color/2), n)


def _filtra(x, bajo=None, alto=None, suave=0.35):
    """Paso banda por FFT: sin scipy, y de sobra para esto."""
    n = len(x)
    esp = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1/HZ)
    g = np.ones_like(f)
    if bajo:
        g *= 1/(1 + (bajo/np.maximum(f, 1e-6))**(2/max(suave, .05)))
    if alto:
        g *= 1/(1 + (np.maximum(f, 1e-6)/alto)**(2/max(suave, .05)))
    return np.fft.irfft(esp*g, n)


def _env(n, ataque=0.01, caida=0.3, curva=2.0):
    t = np.linspace(0, 1, n)
    subida = np.clip(t/max(ataque, 1e-4), 0, 1)
    bajada = np.exp(-t/max(caida, 1e-3)*curva)
    return subida*bajada


def _campana(seg, rng):
    n = int(seg*HZ); t = np.arange(n)/HZ
    x = np.zeros(n)
    # Parciales INARMONICOS: es lo que separa una campana de una flauta.
    for mult, peso, caida in ((1.0,1.0,.55),(2.76,.62,.38),(5.40,.40,.24),
                              (8.93,.24,.15),(13.3,.12,.09)):
        x += peso*np.sin(2*np.pi*392*mult*t)*np.exp(-t/(seg*caida))
    golpe = _filtra(_ruido(n, rng), bajo=1800)*_env(n, .001, .012, 5)
    return x*0.85 + golpe*0.5


def _gentio(seg, rng):
    n = int(seg*HZ)
    base = _filtra(_ruido(n, rng, color=1.0), bajo=260, alto=2400)
    lento = np.interp(np.arange(n), np.linspace(0, n, 40), rng.uniform(.4, 1, 40))
    voces = np.zeros(n)
    for _ in range(9):                      # gritos sueltos por encima
        d = int(rng.uniform(.15, .45)*HZ); i = int(rng.uniform(0, max(1, n-d)))
        voces[i:i+d] += (_filtra(_ruido(d, rng), bajo=420, alto=1600)
                         * _env(d, .12, .45) * rng.uniform(.5, 1.1))
    return base*lento*1.5 + voces*0.5


def _fuego(seg, rng):
    n = int(seg*HZ)
    x = _filtra(_ruido(n, rng, color=1.5), alto=1100)*1.15
    for _ in range(int(seg*9)):             # chasquidos
        i = int(rng.uniform(0, n-400))
        d = int(rng.uniform(80, 420))
        x[i:i+d] += (_filtra(_ruido(d, rng), bajo=700, alto=4200)
                     * _env(d, .002, .08, 6) * rng.uniform(.30, .85))
    return x


def _pasos(seg, rng, por_segundo=2.2):
    n = int(seg*HZ); x = np.zeros(n)
    for k in range(int(seg*por_segundo)):
        i = int((k/por_segundo + rng.uniform(-.03, .03))*HZ)
        if not 0 <= i < n-3000: continue
        d = 3000; t = np.arange(d)/HZ
        golpe = np.sin(2*np.pi*np.maximum(150*np.exp(-t*40), 40)*t)*_env(d, .001, .09, 3)*1.6
        roce = _filtra(_ruido(d, rng), bajo=600, alto=2600)*_env(d, .002, .03, 6)*0.25
        x[i:i+d] += golpe + roce
    return x


def _espada(seg, rng):
    n = int(seg*HZ); t = np.arange(n)/HZ
    x = _filtra(_ruido(n, rng), bajo=2600)*_env(n, .001, .10, 5)
    for hz, p in ((3100,.5),(4700,.34),(6900,.22)):
        x += p*np.sin(2*np.pi*hz*t)*np.exp(-t*7)
    return x


def _tormenta(seg, rng):
    n = int(seg*HZ)
    x = _filtra(_ruido(n, rng, color=2.0), alto=220)
    return x*_env(n, .03, .55, 1.6)*2.2


def _mar(seg, rng):
    n = int(seg*HZ)
    x = _filtra(_ruido(n, rng, color=1.2), bajo=120, alto=1500)
    olas = np.interp(np.arange(n), np.linspace(0, n, 8), rng.uniform(.25, 1, 8))
    return x*olas*1.4


def _monedas(seg, rng):
    n = int(seg*HZ); x = np.zeros(n)
    for _ in range(int(seg*7)):
        i = int(rng.uniform(0, max(1, n-6000))); d = 6000
        t = np.arange(d)/HZ; hz = rng.uniform(2200, 4200)
        x[i:i+d] += (np.sin(2*np.pi*hz*t) + .6*np.sin(2*np.pi*hz*2.31*t))*_env(d, .001, .06, 5)
    return x


def _puerta(seg, rng):
    n = int(seg*HZ); t = np.arange(n)/HZ
    chirrido = np.sin(2*np.pi*(260 + 110*np.sin(2*np.pi*3.5*t))*t)*_env(n, .08, .35, 1.5)*.28
    golpe = np.sin(2*np.pi*np.maximum(90*np.exp(-t*25), 38)*t)*_env(n, .001, .18, 2.2)
    return chirrido + golpe*2.4


def _caballo(seg, rng):
    return _pasos(seg, rng, por_segundo=3.6)


EFECTOS = {
    "campana": _campana, "gentio": _gentio, "fuego": _fuego, "pasos": _pasos,
    "espada": _espada, "tormenta": _tormenta, "mar": _mar, "monedas": _monedas,
    "puerta": _puerta, "caballo": _caballo,
}
EFECTOS_VALIDOS = tuple(EFECTOS)


def _normaliza(x, pico=0.9):
    m = float(np.max(np.abs(x))) if len(x) else 0.0
    return x*(pico/m) if m > 1e-9 else x


def efecto(nombre: str, segundos: float, semilla: int = 0) -> np.ndarray:
    """La onda de un efecto, normalizada. Nombre desconocido -> silencio."""
    f = EFECTOS.get((nombre or "").strip().lower())
    if f is None:
        return np.zeros(int(max(0.1, segundos)*HZ))
    rng = np.random.default_rng(semilla)
    x = f(max(0.15, min(20.0, float(segundos))), rng)
    # Un poco de aire al principio y al final: un efecto que entra de golpe
    # suena a corte, no a sonido.
    n = len(x)
    borde = min(int(0.05*HZ), n//4)
    if borde > 1:
        x[:borde] *= np.linspace(0, 1, borde)
        x[-borde:] *= np.linspace(1, 0, borde)
    return _normaliza(x)


def pista(trozos: list[tuple[str, float, float]], total: float,
          out_path: Path, volumen: float = 0.16) -> Path | None:
    """Una sola pista con cada efecto en su sitio.

    trozos: (nombre, cuando_empieza, cuanto_dura), en segundos.

    Se monta una pista unica en vez de un fichero por escena porque asi el
    video solo lleva UNA mezcla mas: la voz manda y el efecto va debajo.
    """
    try:
        n = int(max(0.5, total)*HZ)
        mezcla = np.zeros(n)
        puestos = []
        for i, (nombre, desde, dura) in enumerate(trozos):
            onda = efecto(nombre, dura, semilla=i*97 + 13)
            ini = int(max(0.0, desde)*HZ)
            fin = min(n, ini + len(onda))
            if fin <= ini:
                continue
            mezcla[ini:fin] += onda[:fin-ini]
            puestos.append(f"{nombre}@{desde:.1f}s")
        if not puestos:
            return None
        mezcla = _normaliza(mezcla, pico=1.0)*volumen
        datos = np.clip(mezcla, -1, 1)
        with wave.open(str(out_path), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(HZ)
            w.writeframes((datos*32767).astype("<i2").tobytes())
        logger.info("Sonido: %s en %.1fs.", ", ".join(puestos), total)
        return Path(out_path)
    except Exception:
        logger.warning("No se ha podido montar la pista de sonido.", exc_info=True)
        return None
