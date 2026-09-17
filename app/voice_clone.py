"""Cloning the channel's voice, so it does not have to be recorded every time.

Reading seventeen minutes by hand works - it was measured, and the alignment
matched an ordinary take at 86% - but it costs the channel's owner about eight
hours a month, and that is the cost most likely to end the project before the
numbers do.

A clone is not the same thing as the reading, and the difference is worth
naming before any of this is used: what makes a real voice work is that
somebody who cares about the subject is talking. A clone returns the timbre
and not the interest. It is a middle option, and whether it is good enough is
a question only listening can answer - which is what this module exists to
make cheap.

The API is reached from the server, never from a developer machine: the key
lives in the environment and the audio it produces comes back through the same
chat the scripts go out on.
"""
import logging
from pathlib import Path

import requests

from .config import ELEVENLABS_API_KEY

logger = logging.getLogger(__name__)

_BASE = "https://api.elevenlabs.io/v1"

# The model is the variable, not a setting. The first clone came back sounding
# nothing like her and, separately, phrasing badly - and those are two
# different faults: timbre comes from the samples, intonation comes from the
# model. Multilingual v2 is the conservative choice and also the flattest one.
#
# So candidates, most expressive first, and which of them the account can
# actually use is ASKED rather than assumed - these names change, and a made-up
# model id fails as "the clone is broken" instead of as "that model is not on
# your plan". English-only models are not here on purpose: a clone judged on
# one of those gets rejected for the model's Spanish accent, not its own
# quality.
_MODELOS_CANDIDATOS = ("eleven_v3", "eleven_multilingual_v2", "eleven_turbo_v2_5")
_MODEL = "eleven_multilingual_v2"

# Tuned for the complaint, not left at the defaults (stability 0.5,
# similarity 0.75). Similarity high because "it does not sound like me" is
# the first thing to fix, and stability LOW because stability is misnamed:
# it flattens delivery towards a monotone, which is exactly the second
# complaint. Low stability with an imperfect clone wanders more - that is the
# trade, and it is the right way round when the flat version has already been
# rejected.
AJUSTES_PARECIDO = {
    "stability": 0.35,
    "similarity_boost": 0.9,
    "style": 0.4,
    "use_speaker_boost": True,
}

# Long enough to judge, short enough to cost almost nothing. Chosen to break
# what usually breaks: long spoken figures, an awkward proper noun, and a real
# question, which is where a synthetic voice goes flat.
FRASE_DE_PRUEBA = (
    "El veinte de octubre de mil novecientos ochenta y dos, el río Júcar pasó por encima "
    "de la presa de Tous y la partió en dos. ¿Por qué reventó, si sus tres compuertas "
    "estaban cerradas?"
)


class CloneError(RuntimeError):
    """Something went wrong at ElevenLabs, phrased for the chat."""


def _headers() -> dict:
    if not ELEVENLABS_API_KEY:
        raise CloneError(
            "No hay ELEVENLABS_API_KEY configurada. Ponla en las variables de Railway."
        )
    return {"xi-api-key": ELEVENLABS_API_KEY}


def _explica(response: requests.Response) -> str:
    """The API's own complaint, in a form worth reading in a chat.

    The status code alone is useless here - 401 means the key is wrong, and
    403 usually means the key is real but was restricted away from this
    endpoint when it was created, which is a different thing to fix."""
    try:
        detalle = response.json().get("detail")
        if isinstance(detalle, dict):
            detalle = detalle.get("message") or detalle.get("status") or detalle
    except ValueError:
        detalle = response.text[:200]
    if response.status_code == 401:
        return f"ElevenLabs rechaza la clave (401). {detalle}"
    if response.status_code == 403:
        return (
            f"ElevenLabs acepta la clave pero no este permiso (403). Revisa que al crearla "
            f"le dieras acceso a Voces (escritura) y a Texto a voz. {detalle}"
        )
    if response.status_code == 429:
        return f"Te has quedado sin credito o has tocado el limite de la clave (429). {detalle}"
    return f"ElevenLabs ha respondido {response.status_code}. {detalle}"


def crear_voz(nombre: str, muestras: list[Path]) -> str:
    """Registers a cloned voice from one or more reference recordings.

    Returns the voice id. Cloning consumes a voice SLOT on the account rather
    than credits, and slots are limited by plan - so a failure here is usually
    "no room for another voice", not "no money", and says so."""
    ficheros = []
    abiertos = []
    try:
        for muestra in muestras:
            fh = open(muestra, "rb")
            abiertos.append(fh)
            ficheros.append(("files", (muestra.name, fh, "audio/mpeg")))
        response = requests.post(
            f"{_BASE}/voices/add",
            headers=_headers(),
            data={"name": nombre, "description": "Voz del canal, clonada de una grabacion propia."},
            files=ficheros,
            timeout=180,
        )
    finally:
        for fh in abiertos:
            fh.close()

    if response.status_code >= 400:
        raise CloneError(_explica(response))
    try:
        voice_id = response.json()["voice_id"]
    except (ValueError, KeyError):
        raise CloneError(f"Respuesta inesperada al crear la voz: {response.text[:200]}")
    logger.info("Voz clonada creada en ElevenLabs: %s (%s muestras).", voice_id, len(muestras))
    return voice_id


def sintetizar(
    voice_id: str,
    texto: str,
    out_path: Path,
    model: str | None = None,
    ajustes: dict | None = None,
) -> Path:
    """Speaks `texto` in the cloned voice."""
    cuerpo = {
        "text": texto,
        "model_id": model or _MODEL,
        "voice_settings": AJUSTES_PARECIDO if ajustes is None else ajustes,
    }
    response = requests.post(
        f"{_BASE}/text-to-speech/{voice_id}",
        headers={**_headers(), "Accept": "audio/mpeg", "Content-Type": "application/json"},
        json=cuerpo,
        timeout=300,
    )
    if response.status_code >= 400:
        raise CloneError(_explica(response))
    out_path.write_bytes(response.content)
    logger.info(
        "Voz clonada con %s: %s caracteres, %.1f KB.",
        cuerpo["model_id"], len(texto), len(response.content) / 1024,
    )
    return out_path


def modelos_para_probar() -> list[str]:
    """The candidate models this account can actually use, best first.

    Asked, not assumed. If the account cannot list its models - an older key
    without the permission - the candidates are returned unfiltered and each
    one reports its own failure, which is more useful than refusing to try."""
    try:
        response = requests.get(f"{_BASE}/models", headers=_headers(), timeout=60)
    except requests.RequestException as exc:
        logger.warning("No se ha podido listar los modelos (%s); se prueban todos.", exc)
        return list(_MODELOS_CANDIDATOS)
    if response.status_code >= 400:
        logger.warning("No se ha podido listar los modelos: %s", _explica(response))
        return list(_MODELOS_CANDIDATOS)
    try:
        disponibles = {m.get("model_id") for m in response.json()}
    except ValueError:
        return list(_MODELOS_CANDIDATOS)
    elegidos = [m for m in _MODELOS_CANDIDATOS if m in disponibles]
    logger.info(
        "Modelos de ElevenLabs disponibles: %s. Se prueban: %s.",
        len(disponibles), ", ".join(elegidos) or "ninguno de los candidatos",
    )
    return elegidos or list(_MODELOS_CANDIDATOS)


def borrar_voz(voice_id: str) -> None:
    """Frees the voice slot. Rebuilding without this leaks one slot per try."""
    response = requests.delete(f"{_BASE}/voices/{voice_id}", headers=_headers(), timeout=60)
    if response.status_code >= 400:
        # Not fatal: the rebuild matters more than the tidy-up, and a leaked
        # slot is visible in the account rather than silent.
        logger.warning("No se ha podido borrar la voz %s: %s", voice_id, _explica(response))
        return
    logger.info("Voz %s borrada; el hueco queda libre.", voice_id)


def voces() -> list[dict]:
    """The voices already on the account, with the cloned ones first."""
    response = requests.get(f"{_BASE}/voices", headers=_headers(), timeout=60)
    if response.status_code >= 400:
        raise CloneError(_explica(response))
    try:
        todas = response.json().get("voices", [])
    except ValueError:
        raise CloneError("Respuesta inesperada al listar las voces.")
    return sorted(todas, key=lambda v: v.get("category") != "cloned")
