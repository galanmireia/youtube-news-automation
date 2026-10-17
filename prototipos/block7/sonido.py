"""BLOCK 7 — el sonido comun de la serie: el tema (pizzicato saltarin) y los efectos de dibujo animado."""
import wave
import numpy as np

SR = 44100
def nota_f(m): return 440*2**((m - 69)/12)


def musica(TABLA, DUR, silencios=(), triste=None, bpm=116):
    """El tema de la serie: un pizzicato saltarin en Do mayor, con un bajo que camina.
    Se calla en los golpes de comedia (el portazo, el POOF) y vuelve despues."""
    n = int(DUR*SR); out = np.zeros(n)
    negra = 60/bpm
    melodia = [72, 76, 79, 76, 77, 74, 71, 74, 72, 76, 79, 84, 83, 79, 77, 74]
    bajos = [48, 55, 53, 55, 48, 52, 55, 43]
    def callado(tt): return any(a <= tt < b for a, b in silencios)
    k = 0; tt = 0.0
    while tt < DUR - 2.0:
        if not callado(tt):
            m = melodia[k % len(melodia)]
            s0 = int(tt*SR); L = int(0.45*SR); x = np.arange(L)/SR
            env = np.exp(-x*9)
            tono = np.sin(2*np.pi*nota_f(m)*x) + 0.35*np.sin(2*np.pi*nota_f(m)*2*x) + 0.1*np.sin(2*np.pi*nota_f(m)*3*x)
            out[s0:s0 + L] += 0.09*env*tono[:max(0, min(L, n - s0))] if s0 + L <= n else 0
            if k % 2 == 0:
                b = bajos[(k//2) % len(bajos)]
                Lb = int(0.6*SR); xb = np.arange(Lb)/SR
                if s0 + Lb <= n:
                    out[s0:s0 + Lb] += 0.12*np.exp(-xb*5)*np.sin(2*np.pi*nota_f(b)*xb)
        tt += negra/2 if (k % 4) != 3 else negra
        k += 1
    # la parte triste: unas notas lentas en menor
    for j, m in enumerate([69, 67, 64, 62, 64] if triste is not None else []):
        s0 = int((triste + 0.2 + j*0.45)*SR); L = int(1.0*SR); x = np.arange(L)/SR
        if s0 + L <= n:
            out[s0:s0 + L] += 0.07*np.exp(-x*3)*np.sin(2*np.pi*nota_f(m)*x)
    return out

# ---------------------------------------------------------------- la orquesta de la telenovela
def cuerda(f, d, vol, at=0.35, rel=0.6, voces=3, arm=8, vib=0.004):
    """Una seccion de cuerda: varias voces de diente de sierra un poco desafinadas, con vibrato."""
    x = np.arange(int(d*SR))/SR; out = np.zeros(len(x))
    for v in range(voces):
        det = 1 + (v - (voces - 1)/2)*0.004
        fase = 2*np.pi*f*det*np.cumsum(1 + vib*np.sin(2*np.pi*5.5*x + v*1.7))/SR
        for k in range(1, arm + 1):
            out += np.sin(k*fase)/k*(0.8**k)
    env = np.minimum(1, x/at)*np.clip((d - x)/rel, 0, 1)
    return vol*out*env/voces

def platillo(d, vol, sube=True):
    rnd = np.random.default_rng(11); x = rnd.standard_normal(int(d*SR))
    x = x - np.convolve(x, np.ones(6)/6, mode="same")
    tt = np.arange(len(x))/SR
    return vol*x*((tt/d)**2 if sube else np.exp(-tt*3))

ACORDES = [((57, 60, 64), 45), ((53, 57, 60), 41), ((55, 60, 64), 48), ((55, 59, 62), 43)]    # Lam  Fa  Do  Sol

def golpe(semitono=0):
    """El ¡TAN! de la telenovela: timbal, metales y cuerda a la vez."""
    d = 1.6; x = np.arange(int(d*SR))/SR
    f0 = nota_f(33 + semitono)
    out = 0.5*np.sin(2*np.pi*f0*x)*np.exp(-x*2.2) + 0.25*np.sin(2*np.pi*f0*2*x)*np.exp(-x*3)
    out += 0.35*np.random.default_rng(5).standard_normal(len(x))*np.exp(-x*18)
    for m in (45, 48, 52, 57):
        c = cuerda(nota_f(m + semitono), d, 0.11, at=0.01, rel=0.5, voces=2, arm=10)
        out += c*np.exp(-x*1.3)
    return out

def romance(d):
    """Cuerdas y arpa en La menor: el amor a primera vista."""
    out = np.zeros(int(d*SR) + 3*SR)
    t = 0.0; i = 0
    while t < d - 0.3:
        notas, bajo = ACORDES[i % 4]; dur = min(2.0, d - t)
        s0 = int(t*SR)
        for m in notas:
            c = cuerda(nota_f(m), dur + 0.4, 0.05, at=0.5, rel=0.6); out[s0:s0 + len(c)] += c
        c = cuerda(nota_f(bajo), dur + 0.4, 0.06, at=0.3, rel=0.6, arm=5); out[s0:s0 + len(c)] += c
        for j, m in enumerate(list(notas) + [notas[0] + 12, notas[1] + 12, notas[2] + 12, notas[0] + 24]):   # el arpa
            if t + j*0.25 < d:
                x = np.arange(int(1.2*SR))/SR; a0 = int((t + j*0.25)*SR)
                arpa = 0.05*(np.sin(2*np.pi*nota_f(m + 12)*x) + 0.3*np.sin(2*np.pi*nota_f(m + 12)*2*x))*np.exp(-x*3.5)
                out[a0:a0 + len(x)] += arpa
        t += 2.0; i += 1
    return out[:int(d*SR)]

def violin(d):
    """El violin triste, solo, sobre un acorde menor que no se resuelve."""
    out = np.zeros(int(d*SR) + 3*SR)
    melodia = [(76, 0.9), (74, 0.45), (72, 0.45), (71, 0.9), (72, 0.6), (69, 1.4), (64, 0.7), (69, 1.6)]
    t = 0.0
    for m, du in melodia:
        if t >= d: break
        c = cuerda(nota_f(m), du + 0.25, 0.09, at=0.08, rel=0.25, voces=1, arm=10, vib=0.007)
        s0 = int(t*SR); out[s0:s0 + len(c)] += c; t += du
    for m in (45, 57, 60, 64):
        c = cuerda(nota_f(m), d, 0.035, at=0.8, rel=0.8); out[:len(c)] += c
    return out[:int(d*SR)]

def tremolo(d):
    """Cuerdas graves en tremolo sobre un acorde disminuido: la tension, cada vez mas fuerte."""
    x = np.arange(int(d*SR))/SR; out = np.zeros(len(x))
    for m in (45, 48, 51, 54):
        out += cuerda(nota_f(m), d, 0.07, at=0.1, rel=0.2, arm=6)
    return out*(0.55 + 0.45*np.sign(np.sin(2*np.pi*13*x)))*(0.3 + 0.7*x/d)

def efectos(TABLA, DUR):
    n = int(DUR*SR); out = np.zeros(n); rnd = np.random.default_rng(3)
    def pon(t0, x):
        s0 = int(t0*SR); s1 = min(n, s0 + len(x))
        if 0 <= s0 < n: out[s0:s1] += x[:s1 - s0]
    def tono(f, d, vol, ca=8.0, at=0.004):
        x = np.arange(int(d*SR))/SR
        return vol*np.sin(2*np.pi*f*x)*np.minimum(1, x/at)*np.exp(-x*ca)
    def barrido(f0, f1, d, vol, ca=3.0):
        x = np.arange(int(d*SR))/SR; f = f0 + (f1 - f0)*x/d
        return vol*np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-x*ca)
    def ruido(d, vol, suav=10):
        return vol*np.convolve(rnd.standard_normal(int(d*SR)), np.ones(suav)/suav, mode="same")
    for a, b, fn, sfx in TABLA:
        for t0, tipo in sfx:
            T0 = a + t0
            if tipo.startswith("pasos"):
                d = float(tipo[5:]); k = 0.0
                while k < d:
                    pon(T0 + k, tono(180, 0.08, 0.10, 40) + ruido(0.08, 0.04, 8)*np.exp(-np.arange(int(0.08*SR))/SR*50)); k += 0.26
            elif tipo == "boing":
                pon(T0, barrido(300, 700, 0.35, 0.12, 4))
            elif tipo.startswith("raspa"):
                d = float(tipo[5:]); x = ruido(d, 0.06, 4); x *= 0.5 + 0.5*np.sin(np.arange(len(x))/SR*2*np.pi*6)
                pon(T0, x)
            elif tipo == "tin":
                pon(T0, tono(2093, 0.6, 0.08, 5)); pon(T0 + 0.08, tono(2637, 0.6, 0.06, 5))
            elif tipo == "puerta":
                pon(T0, barrido(500, 380, 0.6, 0.05, 2))
            elif tipo == "susto":
                pon(T0, barrido(400, 1400, 0.25, 0.1, 2))
            elif tipo == "silbido":
                pon(T0, barrido(500, 2200, 1.0, 0.09, 1.5))
            elif tipo == "bonk":
                pon(T0, tono(110, 0.3, 0.35, 12) + ruido(0.3, 0.2, 30)*np.exp(-np.arange(int(0.3*SR))/SR*20))
            elif tipo == "pito":                 # el "¡ay!" de dibujo: un pito de goma
                pon(T0, barrido(900, 1300, 0.18, 0.1, 6)); pon(T0 + 0.22, barrido(900, 1300, 0.18, 0.1, 6))
            elif tipo == "tiembla":
                x = np.arange(int(2.0*SR))/SR; pon(T0, 0.04*np.sin(2*np.pi*90*x)*(0.5 + 0.5*np.sign(np.sin(2*np.pi*12*x))))
            elif tipo.startswith("bronca"):          # la discusion del 3o, amortiguada tras la pared
                d = float(tipo[6:]); k = 0.0
                while k < d:
                    f = rnd.uniform(220, 420); pon(T0 + k, barrido(f, f*rnd.uniform(0.7, 1.3), 0.18, 0.05, 4)); k += rnd.uniform(0.15, 0.3)
            elif tipo == "pop":
                pon(T0, ruido(0.12, 0.6, 2)*np.exp(-np.arange(int(0.12*SR))/SR*40))
            elif tipo == "toc":
                pon(T0, tono(160, 0.1, 0.3, 40) + ruido(0.1, 0.25, 20)*np.exp(-np.arange(int(0.1*SR))/SR*60))
            elif tipo == "cruje":
                pon(T0, barrido(300, 200, 0.5, 0.05, 2))
            elif tipo == "portazo":
                pon(T0, tono(70, 0.5, 0.5, 9) + ruido(0.5, 0.35, 40)*np.exp(-np.arange(int(0.5*SR))/SR*14))
            elif tipo == "clack":
                pon(T0, ruido(0.05, 0.4, 3)*np.exp(-np.arange(int(0.05*SR))/SR*80) + tono(900, 0.05, 0.1, 60))
            elif tipo == "papel":
                pon(T0, ruido(0.7, 0.08, 6)*np.exp(-np.arange(int(0.7*SR))/SR*3))
            elif tipo == "suspiro":
                x = ruido(1.2, 0.1, 80); x *= np.sin(np.linspace(0, np.pi, len(x))); pon(T0, x)
            elif tipo == "poof":
                x = ruido(0.6, 0.6, 60); x *= np.exp(-np.arange(len(x))/SR*6); pon(T0, x)
            elif tipo == "tema_feliz":
                for j, m in enumerate([72, 76, 79, 84]):
                    pon(T0 + j*0.14, tono(nota_f(m), 0.5, 0.08, 5))
            elif tipo == "ding":
                pon(T0, tono(1760, 0.5, 0.12, 6)); pon(T0, tono(2640, 0.4, 0.05, 7))
            elif tipo == "hiss":
                x = ruido(1.0, 0.35, 2); x *= np.exp(-np.arange(len(x))/SR*2.5); pon(T0, x)
            elif tipo == "silbido_corto":
                pon(T0, barrido(800, 1600, 0.6, 0.08, 2))
            elif tipo == "clink":
                pon(T0, tono(3200, 0.4, 0.1, 9)); pon(T0, tono(4100, 0.3, 0.06, 10))
            elif tipo == "tap":
                pon(T0, tono(1200, 0.05, 0.08, 60))
            elif tipo == "puerta_asc":
                x = ruido(0.5, 0.06, 40); pon(T0, x)
            elif tipo == "ding_asc":
                pon(T0, tono(1318, 0.8, 0.1, 3)); pon(T0 + 0.25, tono(1046, 0.8, 0.1, 3))
            elif tipo == "silencio":
                pass
            elif tipo == "swip":
                pon(T0, barrido(300, 2400, 0.35, 0.1, 3))
            elif tipo == "tiembla_corto":
                x = np.arange(int(0.8*SR))/SR; pon(T0, 0.05*np.sin(2*np.pi*120*x)*(0.5 + 0.5*np.sign(np.sin(2*np.pi*14*x))))
            elif tipo == "pops":
                for j in range(14):
                    pon(T0 + j*0.07 + rnd.uniform(0, 0.03), ruido(0.08, 0.5, 2)*np.exp(-np.arange(int(0.08*SR))/SR*50))
            elif tipo.startswith("pedorreta"):          # el globo desinflandose
                d = float(tipo[9:]); x = np.arange(int(d*SR))/SR
                f = 90 + 40*np.sin(2*np.pi*3*x) + 30*x
                pon(T0, 0.18*np.sign(np.sin(2*np.pi*np.cumsum(f)/SR))*np.minimum(1, x/0.05)*np.minimum(1, (d - x)/0.3)*(0.6 + 0.4*np.sin(2*np.pi*11*x)))
            elif tipo == "clonk":
                pon(T0, tono(140, 0.4, 0.4, 10)); pon(T0, tono(310, 0.3, 0.15, 12))
            elif tipo.startswith("clacks"):
                d = float(tipo[6:]); k = 0.0; paso = 0.17
                while k < d:
                    pon(T0 + k, ruido(0.05, 0.4, 3)*np.exp(-np.arange(int(0.05*SR))/SR*80) + tono(900, 0.05, 0.1, 60))
                    k += paso; paso = max(0.08, paso*0.9)
            elif tipo == "cadenas":
                for j in range(8):
                    pon(T0 + j*0.05, tono(2400 + 300*(j % 3), 0.15, 0.05, 20))
            elif tipo == "rueda":
                for j in range(12):
                    pon(T0 + j*0.06, ruido(0.03, 0.2, 3)*np.exp(-np.arange(int(0.03*SR))/SR*90))
            elif tipo.startswith("sirena"):
                d = float(tipo[6:]); k = 0.0
                while k < d:
                    pon(T0 + k, tono(880, 0.25, 0.06, 1)); pon(T0 + k + 0.25, tono(660, 0.25, 0.06, 1)); k += 0.5
            elif tipo == "clang":
                pon(T0, tono(520, 0.9, 0.15, 4)); pon(T0, tono(1350, 0.7, 0.08, 5))
            elif tipo == "achoo":
                pon(T0, barrido(300, 900, 0.3, 0.08, 2)); pon(T0 + 0.35, ruido(0.4, 0.5, 6)*np.exp(-np.arange(int(0.4*SR))/SR*8))
            elif tipo == "screech":
                x = np.arange(int(1.2*SR))/SR; pon(T0, 0.07*np.sin(2*np.pi*(1800 + 400*np.sin(x*30))*x)*np.minimum(1, x/0.05)*np.exp(-x*1.2))
            elif tipo == "clang":
                pon(T0, tono(520, 0.9, 0.15, 4)); pon(T0, tono(1350, 0.7, 0.08, 5))
            elif tipo == "slam":
                pon(T0, tono(70, 0.5, 0.5, 9)); pon(T0, ruido(0.5, 0.35, 40)*np.exp(-np.arange(int(0.5*SR))/SR*14))
            elif tipo == "bostezo":
                pon(T0, barrido(220, 150, 1.0, 0.07, 1.2))
            elif tipo == "zip":
                pon(T0, barrido(400, 1800, 0.6, 0.08, 2))
            elif tipo == "splat":
                pon(T0, ruido(0.25, 0.5, 30)*np.exp(-np.arange(int(0.25*SR))/SR*14)); pon(T0, tono(90, 0.3, 0.3, 10))
            elif tipo.startswith("metralla"):
                d = float(tipo[8:]); k = 0.0
                while k < d:
                    pon(T0 + k, ruido(0.05, 0.45, 2)*np.exp(-np.arange(int(0.05*SR))/SR*60)); k += 0.07
            elif tipo.startswith("cucharas"):
                d = float(tipo[8:]); k = 0.0
                while k < d:
                    pon(T0 + k, barrido(1400, 600, 0.2, 0.05, 6)); pon(T0 + k + 0.15, tono(2800, 0.2, 0.05, 15)); k += 0.3
            elif tipo == "crash":
                pon(T0, ruido(0.6, 0.45, 3)*np.exp(-np.arange(int(0.6*SR))/SR*6))
                for j in range(6): pon(T0 + 0.05*j, tono(2000 + 500*j, 0.2, 0.04, 12))
            elif tipo.startswith("motor"):
                d = float(tipo[5:]); x = np.arange(int(d*SR))/SR; pon(T0, 0.03*np.sin(2*np.pi*70*x)*(0.6 + 0.4*np.sin(2*np.pi*2*x)))
            elif tipo.startswith("avalancha"):
                d = float(tipo[9:]); x = ruido(d, 0.4, 120); tt = np.arange(len(x))/SR
                x *= np.minimum(1, tt/0.3)*np.minimum(1, (d - tt)/0.6); pon(T0, x)
            elif tipo == "dingdong":
                pon(T0, tono(988, 0.9, 0.12, 3)); pon(T0 + 0.45, tono(784, 1.0, 0.12, 3))
            elif tipo == "popito":
                pon(T0, ruido(0.06, 0.25, 2)*np.exp(-np.arange(int(0.06*SR))/SR*60)); pon(T0, tono(1600, 0.08, 0.06, 40))
            elif tipo == "desliza":
                pon(T0, barrido(900, 250, 0.45, 0.09, 2))
            elif tipo == "ding":
                pon(T0, tono(1760, 0.5, 0.12, 6)); pon(T0, tono(2640, 0.4, 0.05, 7))
            elif tipo == "flechazo":             # el arpa del amor a primera vista
                for j, m in enumerate([72, 76, 79, 83, 84, 88, 91, 96]):
                    pon(T0 + j*0.07, tono(nota_f(m), 1.2, 0.05, 2.5))
            elif tipo.startswith("dun"):            # dun0, dun1, dun2...: cada golpe un poco mas alto
                pon(T0, golpe(int(tipo[3:] or 0)*2))
            elif tipo == "sting":                   # el arranque de la telenovela: platillo que crece y ¡TAN!
                pon(T0, platillo(1.0, 0.25)); pon(T0 + 1.0, golpe(0)); pon(T0 + 1.0, platillo(2.0, 0.18, sube=False))
            elif tipo.startswith("romance"):
                pon(T0, romance(float(tipo[7:])))
            elif tipo.startswith("violin"):
                pon(T0, violin(float(tipo[6:])))
            elif tipo.startswith("tremolo"):
                pon(T0, tremolo(float(tipo[7:])))
            elif tipo == "latido":
                for j in (0.0, 0.22):
                    pon(T0 + j, tono(60, 0.25, 0.35, 14))
            elif tipo == "caen_flores":
                pon(T0, barrido(1200, 300, 1.2, 0.05, 1)); pon(T0 + 1.1, ruido(0.2, 0.3, 20)*np.exp(-np.arange(int(0.2*SR))/SR*20))
            elif tipo == "fin":
                for j, m in enumerate([79, 76, 72]):
                    pon(T0 + 0.2 + j*0.18, tono(nota_f(m), 0.6, 0.08, 4))
    return out

def audio(ruta, TABLA, DUR, silencios=(), triste=None, zona_tema=None):
    """zona_tema=(t0, t1): donde suena el pizzicato; se normaliza solo ahi (el resto es orquesta de telenovela)."""
    mus = musica(TABLA, DUR, silencios, triste); fx = efectos(TABLA, DUR)
    ref = mus[int(zona_tema[0]*SR):int(zona_tema[1]*SR)] if zona_tema else mus
    mus = mus/max(1e-6, np.sqrt(np.mean(ref**2)))*0.08
    fx = np.tanh(fx*2.2)*0.55
    mix = np.tanh((mus + fx)*1.3)*0.92
    fo = int(1.0*SR); mix[-fo:] *= np.linspace(1, 0, fo)
    pcm = (np.clip(mix, -0.98, 0.98)*32767).astype(np.int16)
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
