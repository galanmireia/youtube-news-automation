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

# What a character costs, by model. This is the difference between "9,000
# credits is a video and a half" and "9,000 credits is most of one", so it is
# not a detail: the fast models bill at half rate, and on an account with a
# fixed monthly allowance that doubles the reach for a quality difference
# nobody has listened to yet.
#
# Rates as published; the account's own figures are what /cuenta reports, and
# if these ever disagree with the invoice, the invoice is right.
_CREDITOS_POR_CARACTER = {
    "eleven_multilingual_v2": 1.0,
    "eleven_turbo_v2_5": 0.5,
    "eleven_flash_v2_5": 0.5,
}


def creditos_estimados(texto: str, model: str | None = None) -> float:
    """Roughly what speaking this will cost, before spending it."""
    return len(texto) * _CREDITOS_POR_CARACTER.get(model or _MODEL, 1.0)


def cuenta() -> dict:
    """The subscription's own numbers: credits, voice slots, what is allowed.

    Asked rather than inferred from the plan's name. Which tier allows the
    professional clone, how many voice slots there are and how many credits
    are really left are all decisions this account has already made, and
    guessing them wrong sends somebody off to record thirty minutes of audio
    for a feature they cannot use."""
    response = requests.get(f"{_BASE}/user/subscription", headers=_headers(), timeout=60)
    if response.status_code >= 400:
        if response.status_code == 401:
            # A restricted key is the likely cause here rather than a bad key:
            # this endpoint needs the user permission, which a key created for
            # voices and speech alone does not carry.
            raise CloneError(
                "La clave no tiene permiso para leer la cuenta, asi que no puedo "
                "ver los creditos desde aqui. Miralos en elevenlabs.io o dame una "
                "clave con permiso de lectura de usuario."
            )
        raise CloneError(_explica(response))
    try:
        return response.json()
    except ValueError:
        raise CloneError("Respuesta inesperada al leer la cuenta.")


def resumen_cuenta(datos: dict) -> str:
    """The subscription, phrased as what it lets the channel do.

    Credits are reported as minutes of narration as well as as a number,
    because "9,000 credits" does not say whether that is one video or twenty -
    and at the channel's measured reading pace it is not even one long one."""
    usados = datos.get("character_count")
    tope = datos.get("character_limit")
    lineas = [f"Plan: {datos.get('tier') or '?'}"]
    if isinstance(usados, int) and isinstance(tope, int):
        quedan = max(tope - usados, 0)
        lineas.append(f"Creditos: {quedan:,} libres de {tope:,}".replace(",", "."))
        # Credits are billed per CHARACTER, so the useful conversion is
        # characters to minutes of finished narration, and the pace that
        # matters is the model's, not hers: 90 words a minute is what she
        # reads at, but the clone speaks at around 150, so using her pace
        # would overstate what a credit buys by two thirds.
        #
        # 5.5 characters per Spanish word, measured on the channel's own
        # scripts. A long video is fifteen minutes, which is where the market
        # study put the cliff.
        _CHARS_POR_MINUTO = 150 * 5.5
        minutos = quedan / _CHARS_POR_MINUTO
        lineas.append(
            f"Eso da para unos {minutos:.0f} min de narracion sintetizada "
            f"({minutos / 15:.0f} videos de 15 min), o el doble con los modelos "
            f"rapidos, que cuestan la mitad por caracter."
        )
    reinicio = datos.get("next_character_count_reset_unix")
    if reinicio:
        import datetime
        fecha = datetime.datetime.fromtimestamp(reinicio).strftime("%d/%m")
        lineas.append(f"Se renuevan el {fecha}.")
    huecos = datos.get("voice_limit")
    if huecos is not None:
        lineas.append(f"Huecos de voz: {huecos}.")
    pvc = datos.get("can_use_professional_voice_cloning")
    limite_pvc = datos.get("professional_voice_limit")
    if pvc is True or (limite_pvc or 0) > 0:
        lineas.append(
            f"Clonacion PROFESIONAL: disponible"
            + (f" ({limite_pvc} {'voz' if limite_pvc == 1 else 'voces'})."
               if limite_pvc else ".")
            + " Necesita unos 30 min de audio tuyo y suena mucho mejor que la instantanea."
        )
    elif pvc is False:
        lineas.append("Clonacion profesional: NO en este plan (solo la instantanea).")
    return "\n".join(lineas)
