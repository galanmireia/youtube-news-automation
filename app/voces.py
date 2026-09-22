"""Cada personaje con su voz, sacada de la de ella.

Idea suya: "me gustaria que cada personaje tuviera siempre su propia voz, mas
aguda mas fuerte, y luego la voz de la narracion".

Habia dos caminos. Uno era cinco voces distintas de ElevenLabs: voces de
verdad, pero cinco IDs que configurar, creditos por cada frase y depender de
que existan en su cuenta. El otro es este: coger SU voz y cambiarle el tono
solo en el trozo donde habla cada personaje.

Gana el segundo por lo mismo que ganaron los monigotes y los sonidos: no
cuesta nada, es instantaneo, sale igual siempre - y sobre todo, la sincronia
es exacta POR CONSTRUCCION, porque el instante en que se dice cada frase ya
se calcula para poner el bocadillo. Es el mismo numero.

Y ademas queda mejor de lo que parece: un monigote con la voz de ella
acelerada es exactamente el registro de un dibujo animado.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Tono y fuerza de cada uno. El tono es un multiplicador: 1.30 es un tercio
# mas agudo, 0.85 es mas grave. La fuerza, en decibelios.
#
# Ella pidio "mas aguda, mas fuerte", y eso vale para los que interrumpen -
# Perico y Remedios -, pero no para todos: si los cinco hablan agudo no se
# distinguen, que es justo lo que queriamos evitar. Don Severo manda, y quien
# manda habla GRAVE y despacio.
VOCES = {
    "chaval":   {"tono": 1.34, "fuerza": 4.0},   # Perico, el mas agudo
    "abuela":   {"tono": 1.20, "fuerza": 3.5},   # Remedios, aguda y cortante
    "cronista": {"tono": 1.07, "fuerza": 2.0},   # Anselmo, casi la voz normal
    "soldado":  {"tono": 0.90, "fuerza": 3.0},   # Bruno, grave y rota
    "mandamas": {"tono": 0.80, "fuerza": 2.5},   # Don Severo, el mas grave
}
VOCES_VALIDAS = tuple(VOCES)
_HZ = 44100


def _filtro(tono: float, fuerza: float) -> str:
    """Sube o baja el tono SIN cambiar la duracion.

    asetrate reproduce mas rapido - eso sube el tono y acorta -, y atempo
    devuelve la duracion original. Si solo se acelerara, el trozo duraria
    menos y todo lo que viene detras se descolocaria: los subtitulos, el
    bocadillo y el video entero.

    atempo solo admite de 0.5 a 2.0, asi que se encadena si hace falta.
    """
    pasos, resto = [], 1.0/tono
    while resto < 0.5:
        pasos.append("atempo=0.5"); resto /= 0.5
    while resto > 2.0:
        pasos.append("atempo=2.0"); resto /= 2.0
    pasos.append(f"atempo={resto:.6f}")
    # Y el limitador al final, que no es adorno: subir 4 dB una narracion que
    # ya viene alta la saca de rango - medido, +4 dB sobre un pico de 0.9 da
    # 1.43 -, y eso no suena mas fuerte, suena roto. Con el limitador el trozo
    # sube todo lo que puede subir y los picos se quedan dentro.
    return (f"asetrate={int(_HZ*tono)},aresample={_HZ},"
            + ",".join(pasos)
            + f",volume={fuerza:.1f}dB,alimiter=limit=0.95:level=disabled")


def _corta(entrada: Path, salida: Path, desde: float, hasta: float | None,
           filtro: str | None = None) -> bool:
    orden = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(entrada),
             "-ss", f"{desde:.3f}"]
    if hasta is not None:
        orden += ["-to", f"{hasta:.3f}"]
    if filtro:
        orden += ["-af", filtro]
    orden += ["-ar", str(_HZ), "-ac", "1", str(salida)]
    try:
        subprocess.run(orden, check=True, capture_output=True, timeout=120)
        return salida.exists() and salida.stat().st_size > 0
    except Exception:
        logger.warning("No he podido cortar el audio en %.2f-%s.", desde, hasta, exc_info=True)
        return False


def poner_voces(narracion: Path, trozos: list[tuple[str, float, float]],
                out_path: Path) -> Path | None:
    """La narracion con la voz cambiada en cada frase de personaje.

    trozos: (quien, desde, hasta) en segundos ABSOLUTOS del video.

    Si algo falla se devuelve None y se sigue con la narracion de siempre: una
    voz sin gracia es mucho menos malo que un video sin voz.
    """
    trozos = sorted((t for t in trozos if t[0] in VOCES and t[2] > t[1]),
                    key=lambda t: t[1])
    if not trozos:
        return None
    try:
        tmp = Path(out_path).parent / "voces"
        tmp.mkdir(parents=True, exist_ok=True)
        partes, reloj, n = [], 0.0, 0
        for quien, desde, hasta in trozos:
            if desde < reloj:                 # se solapan: se salta
                continue
            if desde > reloj + 0.01:
                p = tmp / f"{n:03d}_normal.wav"; n += 1
                if _corta(narracion, p, reloj, desde):
                    partes.append(p)
            v = VOCES[quien]
            p = tmp / f"{n:03d}_{quien}.wav"; n += 1
            if _corta(narracion, p, desde, hasta, _filtro(v["tono"], v["fuerza"])):
                partes.append(p)
            reloj = hasta
        p = tmp / f"{n:03d}_final.wav"
        if _corta(narracion, p, reloj, None):
            partes.append(p)
        if len(partes) < 2:
            return None
        lista = tmp / "lista.txt"
        lista.write_text("".join(f"file '{x.name}'\n" for x in partes), encoding="utf-8")
        # Se vuelve a codificar, no se copia: los trozos son WAV y el destino
        # es el mp3 que ya espera el resto del montaje, y "copiar" PCM dentro
        # de un mp3 no es copiar, es no salir.
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat",
                        "-safe", "0", "-i", str(lista),
                        "-ar", str(_HZ), "-ac", "1", "-b:a", "192k", str(out_path)],
                       check=True, capture_output=True, timeout=180)
        logger.info("Voces: %s.", ", ".join(
            f"{q} {VOCES[q]['tono']:.2f}x en {d:.1f}s" for q, d, _ in trozos))
        return Path(out_path)
    except Exception:
        logger.warning("No he podido poner las voces de los personajes.", exc_info=True)
        return None


def _quienes_hablan(escena: dict, cuantas: int) -> list[str]:
    """El personaje de cada frase de la escena, en orden.

    La primera es de quien dice el guion ("habla_x"); la respuesta es del
    OTRO. Es la misma regla que usa el bocadillo para decidir a quien apunta
    el rabo, y tiene que serlo: si la voz dijera un personaje y el globo
    apuntara a otro, el video se contradiria a si mismo en pantalla.
    """
    figuras = [f for f in (escena.get("figuras") or []) if isinstance(f, dict)]
    if not figuras:
        return []
    x = escena.get("habla_x")
    orden = figuras
    if isinstance(x, (int, float)):
        orden = sorted(figuras, key=lambda f: abs(float(f.get("x", 0.5) or 0.5) - float(x)))
    primero = (orden[0].get("quien") or "").strip().lower()
    # El que contesta es el que esta mas lejos, igual que en el bocadillo.
    if len(orden) > 1:
        ref = float(orden[0].get("x", 0.5) or 0.5)
        lejos = max(figuras, key=lambda f: abs(float(f.get("x", 0.5) or 0.5) - ref))
        segundo = (lejos.get("quien") or "").strip().lower()
    else:
        segundo = primero
    return [primero if k % 2 == 0 else segundo for k in range(cuantas)]


def _quien_habla(escena: dict) -> str:
    """El personaje que dice la frase de esta escena.

    El guion no guarda el nombre del que habla, guarda DONDE esta: `habla_x`,
    que es lo que necesita el rabo del bocadillo para apuntarle. Asi que el
    nombre se saca de la figura que esta en esa x - la misma que va a tener el
    globo encima. Si no se dice quien, habla el primero.
    """
    figuras = [f for f in (escena.get("figuras") or []) if isinstance(f, dict)]
    if not figuras:
        return ""
    x = escena.get("habla_x")
    if isinstance(x, (int, float)):
        figuras = sorted(figuras, key=lambda f: abs(float(f.get("x", 0.5) or 0.5) - float(x)))
    return (figuras[0].get("quien") or "").strip().lower()


def trozos_de(scenes: list[dict], duraciones: list[float],
              marcas: list | None) -> list[tuple[str, float, float]]:
    """Cuando habla cada personaje, en segundos del audio entero.

    No se calcula nada nuevo: la ventana es LA MISMA que usa el bocadillo -
    misma cita, misma funcion, mismas marcas -, solo que corrida por el
    principio de la escena para pasarla a tiempo del video completo. Por eso
    la voz y el globo no pueden descuadrarse entre si: si uno acierta, acierta
    el otro, y si uno falla no sale ninguno de los dos.
    """
    from . import bocadillos

    trozos, reloj = [], 0.0
    for i, scene in enumerate(scenes):
        dura = duraciones[i] if i < len(duraciones) else 0.0
        escena = scene.get("escena")
        citas = bocadillos.citas_de(scene.get("narration", ""))
        marca = marcas[i] if marcas and i < len(marcas) else None
        if citas and marca and isinstance(escena, dict):
            quienes = _quienes_hablan(escena, len(citas))
            cursor = 0
            for k, frase in enumerate(citas):
                ventana = bocadillos.cuando_se_dice(marca[0], marca[1], frase, cursor)
                if not ventana:
                    continue
                cursor = bocadillos.donde_se_dice(marca[0], frase, cursor) + len(frase)
                quien = quienes[k] if k < len(quienes) else ""
                if quien in VOCES:
                    trozos.append((quien, reloj + ventana[0],
                                   min(reloj + ventana[1], reloj + dura)))
                else:
                    logger.info("Escena %s: la frase %s la dice alguien que no es del "
                                "reparto (%r); se queda con la voz de la narracion.",
                                i, k + 1, quien)
        reloj += dura
    return trozos


# QUE NO SE SEPAREN LAS DOS LISTAS.
#
# Esto ya ha costado dos fallos: la taberna que se dibujaba y no se usaba, y
# el arbol que estaba en el guion y no existia al dibujarlo. Las dos veces
# habia una lista escrita a mano al lado de otra, y una de las dos se quedo
# atras sin que nada avisara. Asi que aqui se comprueba solo.
#
# Los dos casos no pesan igual, y por eso no se tratan igual:
#  - una voz de alguien que no esta en el reparto es una errata y no tiene
#    ningun lado bueno, asi que revienta aqui, al arrancar, y se ve.
#  - un personaje nuevo sin voz solo significa que habla con la voz de la
#    narracion, que es lo de antes. Eso avisa, pero no tira el bot abajo por
#    algo que no rompe ningun video.
def _cuadra_con_el_reparto() -> None:
    from .monigotes import REPARTO
    sobran = set(VOCES) - set(REPARTO)
    if sobran:
        raise RuntimeError(
            f"voces.py da voz a alguien que no existe en el reparto: {sorted(sobran)}")
    faltan = set(REPARTO) - set(VOCES)
    if faltan:
        logger.warning("Estos personajes no tienen voz propia y hablaran con la de la "
                       "narracion: %s.", ", ".join(sorted(faltan)))


_cuadra_con_el_reparto()
