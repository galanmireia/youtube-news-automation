"""Times the video to a recording of the channel's own voice.

The pipeline has always got its timing for free: it synthesised each scene
separately, so it knew exactly how long each one lasted. A human reads the
whole script in one take, which is the right way to read it - the pauses and
the emphasis only work if the sentences run into one another - and that take
arrives as one audio file with no markers in it.

So the boundaries are recovered instead of known. The recording is
transcribed with per-word timestamps and matched against the script that was
read; the instant the last word of a scene was spoken is where that scene
ends.

Only the boundaries are wanted here, not a corrected transcript, so this does
its own matching rather than borrowing the subtitles' word-replacement pass.
That pass refuses below sixty per cent agreement, which is right when the
voice is a synthesiser reading the exact script and far too strict for a
person, who stumbles, repeats a line and swaps a word for a better one
without the take being bad.

What must not happen is a quiet failure. Handed the wrong file, this would
put every cut in the wrong place and produce a video that looks broken for no
visible reason, so below a floor of agreement it refuses and says why.
"""
import difflib
import logging
import re
import unicodedata
from pathlib import Path

from .subtitles import _get_model

logger = logging.getLogger(__name__)

# Below this the recording is not this script: wrong file, wrong take, or
# somebody improvising. Well under what a synthesiser scores, because a person
# genuinely does deviate; well over what a different recording could reach by
# chance on Spanish function words alone.
_MIN_MATCH = 0.45

# A scene still has to last long enough for its images to be seen, however the
# reading came out.
_MIN_SCENE_SECONDS = 0.8


class AlignmentFailed(RuntimeError):
    """The recording could not be matched to the script."""


def _norm(word: str) -> str:
    folded = unicodedata.normalize("NFKD", word.lower())
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", folded)


def _spoken_times(oidas: list, escritas: list[str]) -> tuple[list[float], float]:
    """For each written word, the moment it was spoken.

    Matching is done on normalised words, so accents, capitals and punctuation
    never break it. Where the reader deviated there is no exact counterpart,
    and the time is interpolated across the gap between the words either side
    that did match - which is all a scene boundary needs.
    """
    oidas_norm = [_norm(getattr(w, "word", "")) for w in oidas]
    escritas_norm = [_norm(w) for w in escritas]
    matcher = difflib.SequenceMatcher(None, oidas_norm, escritas_norm, autojunk=False)
    ratio = matcher.ratio()
    if ratio < _MIN_MATCH:
        raise AlignmentFailed(
            f"La grabacion coincide con el guion solo al {ratio * 100:.0f}%. "
            "Comprueba que es el audio de este video y que esta leido entero."
        )

    tiempos: list[float | None] = [None] * len(escritas)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            continue
        for offset in range(i2 - i1):
            tiempos[j1 + offset] = float(oidas[i1 + offset].end)

    # Fill the gaps the reader left, and the edges, so every written word has a
    # time even where nothing matched.
    primero = next((t for t in tiempos if t is not None), 0.0)
    ultimo_oido = float(oidas[-1].end)
    anterior = 0.0
    for i, t in enumerate(tiempos):
        if t is not None:
            anterior = t
            continue
        siguiente = next((x for x in tiempos[i + 1:] if x is not None), ultimo_oido)
        restantes = 1 + sum(1 for x in tiempos[i:] if x is None)
        tiempos[i] = anterior + (siguiente - anterior) / restantes
        anterior = tiempos[i]

    if tiempos and tiempos[0] is None:
        tiempos[0] = primero
    logger.info("Voz propia: la grabacion encaja con el guion al %.0f%%.", ratio * 100)
    return [float(t) for t in tiempos], ratio


def align_recording(
    scenes: list[dict], audio_path: Path, language: str = "es"
) -> tuple[Path, list[float]]:
    """Where each scene ends inside one recording of the whole script.

    Returns the recording and one duration per scene - the same pair
    tts.synthesize_scenes returns, so nothing downstream changes."""
    textos = [(s.get("narration") or "").strip() for s in scenes]
    if not any(textos):
        raise AlignmentFailed("El guion no tiene narracion que alinear.")

    model = _get_model()
    segments, _ = model.transcribe(str(audio_path), language=language, word_timestamps=True)
    oidas: list = []
    fin_audio = 0.0
    for segment in segments:
        oidas.extend(segment.words or [])
        fin_audio = max(fin_audio, float(segment.end or 0.0))
    if not oidas:
        raise AlignmentFailed("No se ha entendido ninguna palabra en la grabacion.")

    escritas: list[str] = []
    ultima_de_escena: list[int] = []
    for texto in textos:
        palabras = texto.split()
        escritas.extend(palabras)
        # An empty scene ends where the previous one did.
        ultima_de_escena.append(len(escritas) - 1 if escritas else 0)

    tiempos, _ratio = _spoken_times(oidas, escritas)

    duraciones: list[float] = []
    anterior = 0.0
    for n, indice in enumerate(ultima_de_escena):
        ultimo = tiempos[indice] if escritas else 0.0
        # The final scene runs to the end of the recording rather than to its
        # last word: the breath that closes the take belongs to the video too.
        if n == len(ultima_de_escena) - 1:
            ultimo = max(ultimo, fin_audio)
        duraciones.append(max(_MIN_SCENE_SECONDS, ultimo - anterior))
        anterior = anterior + duraciones[-1]

    logger.info(
        "Voz propia: %s escenas sobre %.1fs de grabacion (la mas corta %.1fs, la mas larga %.1fs).",
        len(duraciones), fin_audio, min(duraciones), max(duraciones),
    )
    return audio_path, duraciones


# --- El guion tal como se lee, que no es el guion tal como se alinea -------
#
# Estas marcas existen solo en el .txt que se manda a leer. El guion guardado
# conserva la narracion limpia, y es esa la que se alinea: si una marca
# acabara en el texto de referencia, ninguna palabra la diria en voz alta y
# el emparejamiento tendria un hueco en cada frase.

_PAUSA_ESCENA = "⏸"
_BEAT = "|"
_FIN_FRASE = re.compile(r"([.!?…])(\s+)(?=[¿¡A-ZÁÉÍÓÚÑ])")


def _marcar_beats(texto: str) -> str:
    """Un palo despues de cada punto: ahi se respira, no se para."""
    return _FIN_FRASE.sub(rf"\1 {_BEAT}\2", texto.strip())


def reading_script(scenes: list[dict], title: str = "", tema: str = "") -> str:
    """El guion preparado para leerlo en voz alta.

    Dos marcas y nada mas, porque esto se lee en un movil y cada simbolo de
    adorno es una cosa menos que se mira: el palo es una respiracion dentro de
    la escena, y el simbolo de pausa es el cambio de imagen.

    La pausa entre escenas no es un permiso, es lo que se quiere: el corte se
    monta dentro de ese silencio, asi que la imagen nueva entra mientras no
    hablas en vez de cortarte a media palabra."""
    textos = [(sc.get("narration") or "").strip() for sc in scenes]
    palabras = sum(len(t.split()) for t in textos)

    cabecera = [
        title or "Guion",
        f"Tema: {tema}" if tema else "",
        f"{len(textos)} escenas · {palabras} palabras · unos {palabras / 150:.0f} min de lectura",
        "",
        "COMO LEERLO",
        f"  {_BEAT}   respira, medio segundo. No bajes el tono, la frase sigue.",
        f"  {_PAUSA_ESCENA}   para de verdad, un segundo entero. Aqui cambia la imagen,",
        "      y el corte se monta dentro de tu silencio.",
        "",
        "  · Graba del tiron, sin cortar el archivo entre escenas.",
        "  · Si te equivocas, NO pares: repite la frase entera y sigue. Se apaña solo.",
        "  · Las cifras son lo que la gente recuerda: apoyate en ellas al decirlas.",
        "  · Si una frase te suena rara al decirla en alto, cambiala. Manda tu voz,",
        "    no el papel.",
        "",
        "=" * 64,
    ]

    partes = []
    for i, texto in enumerate(textos, start=1):
        if not texto:
            continue
        partes.append(
            f"\n── ESCENA {i} de {len(textos)} " + "─" * 34 + "\n\n"
            + _marcar_beats(texto) + f"  {_PAUSA_ESCENA}"
        )
    return "\n".join(l for l in cabecera if l is not None) + "\n" + "\n".join(partes) + "\n"
