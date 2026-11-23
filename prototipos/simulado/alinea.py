"""Cuando suena cada palabra de una narracion grabada, sin modelos de voz.

Se buscan los silencios reales del audio y se emparejan (en orden) con las
pausas que marca la puntuacion del texto. Entre dos pausas emparejadas, cada
palabra se lleva un tiempo segun sus letras.
"""
import re

import numpy as np

PAUSA_FUERTE = re.compile(r"[.?!…:]$|\.\.\.$")
PAUSA_DEBIL = re.compile(r"[,;]$")


def silencios(audio, sr, minimo=0.11):
    v = int(0.01*sr)
    n = len(audio)//v
    rms = np.sqrt((audio[:n*v].reshape(n, v)**2).mean(1) + 1e-12)
    rms = np.convolve(rms, np.ones(3)/3, mode="same")
    habla = rms > max(np.percentile(rms, 95)*0.08, 1e-4)
    idx = np.where(habla)[0]
    if len(idx) == 0:
        return [], 0.0, len(audio)/sr
    ini, fin = idx[0]*0.01, (idx[-1] + 1)*0.01
    huecos, k = [], idx[0]
    while k < idx[-1]:
        if not habla[k]:
            j = k
            while j < idx[-1] and not habla[j]:
                j += 1
            if (j - k)*0.01 >= minimo:
                huecos.append((k*0.01, j*0.01))
            k = j
        else:
            k += 1
    return huecos, ini, fin


def tiempos(texto, audio, sr):
    """[(palabra, inicio, fin)] para cada palabra del texto."""
    palabras = texto.replace("…", "...").split()
    huecos, ini, fin = silencios(audio, sr)
    peso = np.array([len(p) + 1.5 for p in palabras], float)
    pausas = [k for k, p in enumerate(palabras[:-1]) if PAUSA_FUERTE.search(p) or PAUSA_DEBIL.search(p)]
    fuerza = {k: (2.0 if PAUSA_FUERTE.search(palabras[k]) else 1.0) for k in pausas}

    def esperado(k):
        return ini + (fin - ini)*peso[:k + 1].sum()/peso.sum()

    m, n = len(pausas), len(huecos)
    INF = 1e9
    coste = np.full((m + 1, n + 1), INF)
    paso = {}
    coste[0, :] = [sum(0.6*(h[1] - h[0]) for h in huecos[:j]) for j in range(n + 1)]
    for i in range(1, m + 1):
        coste[i, 0] = coste[i - 1, 0] + 0.5*fuerza[pausas[i - 1]]
        paso[(i, 0)] = (i - 1, 0, None)
        for j in range(1, n + 1):
            h = huecos[j - 1]
            centro = (h[0] + h[1])/2
            opciones = [
                (coste[i - 1, j - 1] + abs(esperado(pausas[i - 1]) - centro)*0.9
                 - 0.25*fuerza[pausas[i - 1]]*min(1, (h[1] - h[0])/0.3), (i - 1, j - 1, j - 1)),
                (coste[i - 1, j] + 0.5*fuerza[pausas[i - 1]], (i - 1, j, None)),
                (coste[i, j - 1] + 0.6*(h[1] - h[0]), (i, j - 1, None)),
            ]
            c, p = min(opciones, key=lambda o: o[0])
            coste[i, j], paso[(i, j)] = c, p
    anclas = {}
    i, j = m, n
    while i > 0:
        pi, pj, hj = paso[(i, j)]
        if hj is not None and pi == i - 1 and pj == j - 1:
            anclas[pausas[i - 1]] = huecos[hj]
        i, j = pi, pj
    out = []
    tramo_ini, w0 = ini, 0
    for k in sorted(anclas) + [len(palabras) - 1]:
        tramo_fin = anclas[k][0] if k in anclas else fin
        ws = list(range(w0, k + 1))
        pesos = peso[ws]
        t = tramo_ini
        for w, pw in zip(ws, pesos):
            d = (tramo_fin - tramo_ini)*pw/pesos.sum()
            out.append((palabras[w], t, t + d))
            t += d
        if k in anclas:
            tramo_ini = anclas[k][1]
        w0 = k + 1
    return out
