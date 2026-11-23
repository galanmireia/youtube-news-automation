"""Sonido para los videos de Lo he simulado (44,1 kHz): musica propia y efectos sintetizados."""
import numpy as np

SR = 44100


def _t(dur):
    return np.arange(int(dur*SR))/SR


def nota(f, dur, ataque=0.01, caida=0.3, armonicos=(1.0, 0.35, 0.12)):
    t = _t(dur)
    s = sum(a*np.sin(2*np.pi*f*(k + 1)*t)*np.exp(-t*k*3) for k, a in enumerate(armonicos))
    return (s*np.minimum(1, t/ataque)*np.exp(-t/caida)).astype(np.float32)


def pad(fs, dur, vol=1.0):
    t = _t(dur)
    s = np.zeros_like(t)
    for f in fs:
        for d in (-0.6, 0.0, 0.7):
            s += np.sin(2*np.pi*(f + d)*t + d)
        s += 0.25*np.sin(2*np.pi*f*2*t)
    env = np.minimum(1, t/0.6)*np.minimum(1, (dur - t)/0.8).clip(0, 1)
    return (s/len(fs)/3*env*vol).astype(np.float32)


def musica(seg, bpm=104, alegre=True):
    """Bajo, pad y arpegio en corcheas. alegre: Do-Sol-Lam-Fa; si no, Lam-Fa-Do-Sol."""
    out = np.zeros(int(seg*SR) + SR*4, np.float32)
    negra = 60/bpm
    compas = 4*negra
    acordes = ([(261.6, 329.6, 392.0), (196.0, 246.9, 293.7), (220.0, 261.6, 329.6), (174.6, 220.0, 261.6)] if alegre else
               [(220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (261.6, 329.6, 392.0), (196.0, 246.9, 293.7)])
    t, k = 0.0, 0
    while t < seg:
        ac = acordes[k % 4]
        i = int(t*SR)
        p = pad(ac, compas + 0.8, 0.16)
        out[i:i + len(p)] += p[:len(out) - i]
        b = nota(ac[0]/2, compas, 0.02, 1.0, (1.0, 0.2))*0.4
        out[i:i + len(b)] += b[:len(out) - i]
        for c in range(8):
            f = ac[(0, 1, 2, 1, 2, 0, 1, 2)[c]]*2
            n = nota(f, 0.5, 0.003, 0.14)*(0.17 if c % 2 == 0 else 0.11)
            j = i + int(c*negra/2*SR)
            out[j:j + len(n)] += n[:len(out) - j]
        t += compas
        k += 1
    return out[:int(seg*SR)]


def tic(rnd, vol=1.0):
    f = rnd.uniform(1500, 2600)
    t = _t(0.035)
    return (np.sin(2*np.pi*f*t)*np.exp(-t*140)*vol).astype(np.float32)


def ding(f=1046.5, vol=1.0):
    t = _t(0.9)
    s = np.sin(2*np.pi*f*t) + 0.5*np.sin(2*np.pi*f*1.5*t)*np.exp(-t*4) + 0.25*np.sin(2*np.pi*f*2*t)*np.exp(-t*6)
    return (s*np.exp(-t*4.5)*0.35*vol).astype(np.float32)


def pop(vol=1.0):
    t = _t(0.09)
    f = 900*np.exp(-t*30) + 250
    return (np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*45)*0.5*vol).astype(np.float32)


def golpe(vol=1.0):
    t = _t(0.6)
    f = 48 + 120*np.exp(-t*25)
    s = np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*6)
    s[:400] += np.random.default_rng(1).standard_normal(400)*np.linspace(0.6, 0, 400)
    return (s*0.85*vol).astype(np.float32)


def whoosh(dur=0.32, vol=1.0):
    n = int(dur*SR)
    ruido = np.random.default_rng(3).standard_normal(n)
    t = np.linspace(0, 1, n)
    corte = 0.01 + 0.12*np.sin(np.pi*t)
    y = np.zeros(n)
    acc = 0.0
    for i in range(n):
        acc += corte[i]*(ruido[i] - acc)
        y[i] = acc
    return (y/np.abs(y).max()*np.sin(np.pi*t)*0.3*vol).astype(np.float32)


def suma(pista, s, en):
    i = int(en*SR)
    if i < 0 or i >= len(pista):
        return
    trozo = s[:len(pista) - i]
    pista[i:i + len(trozo)] += trozo
