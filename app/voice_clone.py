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

# Multilingual, because the channel is in Spanish and the English-only models
# mangle it - a clone judged on one of those would be rejected for the model's
# accent rather than its own quality.
_MODEL = "eleven_multilingual_v2"

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


def sintetizar(voice_id: str, texto: str, out_path: Path) -> Path:
    """Speaks `texto` in the cloned voice."""
    response = requests.post(
        f"{_BASE}/text-to-speech/{voice_id}",
        headers={**_headers(), "Accept": "audio/mpeg", "Content-Type": "application/json"},
        json={"text": texto, "model_id": _MODEL},
        timeout=300,
    )
    if response.status_code >= 400:
        raise CloneError(_explica(response))
    out_path.write_bytes(response.content)
    logger.info(
        "Voz clonada: %s caracteres sintetizados, %.1f KB.", len(texto), len(response.content) / 1024
    )
    return out_path


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
