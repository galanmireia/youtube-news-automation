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
import base64
import io
import json
import logging
from pathlib import Path

import requests
from pydub import AudioSegment

from .config import DATA_DIR, ELEVENLABS_API_KEY
from .spanish import MIN_TASA_ACENTOS, tasa_de_acentos

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

# Decided by listening, not by caution: eleven_v3 phrases better than the
# other two on this voice, and multilingual_v2 was only ever the default
# because it was the safe guess before anybody had heard anything.
_MODEL = "eleven_v3"

# Chosen by ear, over two sweeps, and these are the numbers she picked: on
# eleven_v3 the most CONTAINED of the four won.
#
# That is the opposite of what I predicted twice. The reasoning was that
# stability flattens delivery and this voice needed loosening - which held on
# multilingual_v2, where she picked the loosest preset. It does not hold on
# v3, because v3 already phrases expressively on its own: pushing style on top
# of it made it worse, not better. What a slider does depends on the model it
# is attached to, and no amount of reading the documentation was going to say
# which way round it fell here.
#
# It also happens to be the safer end for a long narration. A clone at ninety
# percent looseness wanders over fifteen minutes; at sixty-five it has much
# less room to.
AJUSTES_PARECIDO = {
    "stability": 0.35,
    "similarity_boost": 0.9,
    "style": 0.4,
    "use_speaker_boost": True,
}

# Presets for the second question, which the model comparison could not
# answer: the voice that came closest to hers was also the flattest of the
# three, so the model that wins on timbre is not the one that wins on
# phrasing. Timbre and phrasing have separate controls, so the fix is to keep
# the model that sounds like her and move the sliders, not to trade one fault
# for the other.
#
# What each slider does, as published and as far as it can be trusted:
# stability flattens delivery towards a monotone as it rises (the name is
# backwards for this purpose); style exaggerates the delivery of the original
# samples and is documented to cost stability and, on a clone, some
# similarity; similarity_boost pushes towards the samples and can drag any
# artefacts in them along with it.
#
# None of that is measured on THIS voice, which is the point of sending four
# versions instead of arguing about it.
AJUSTES_PRESETS: dict[str, dict] = {
    # Named for where it sits in the sweep, not for what it was. It used to be
    # called "igual-que-antes", which is also an ordinary Spanish phrase
    # meaning "the same as before" - so asking for the preset she had already
    # chosen, in the words anyone would use, silently selected the flat
    # starting point she had rejected. It set the wrong voice and said so
    # clearly enough that she caught it, which is the only reason this is a
    # rename and not a video.
    "punto-de-partida": {
        "stability": 0.35, "similarity_boost": 0.9, "style": 0.4,
        "use_speaker_boost": True,
    },
    "mas-suelto": {
        "stability": 0.20, "similarity_boost": 0.9, "style": 0.6,
        "use_speaker_boost": True,
    },
    "muy-suelto": {
        "stability": 0.10, "similarity_boost": 0.85, "style": 0.75,
        "use_speaker_boost": True,
    },
    # The control: maximum similarity and no style exaggeration at all. If
    # this one is both the closest AND acceptably phrased, the style slider
    # was working against us and the answer is simpler than it looked.
    "parecido-al-maximo": {
        "stability": 0.30, "similarity_boost": 1.0, "style": 0.0,
        "use_speaker_boost": True,
    },
}

# A second, finer sweep, aimed at the corner the first one left empty.
#
# The coarse sweep was built on a guess - that expressiveness was pulling the
# clone away from her samples - and the guess was wrong: on eleven_v3 the
# LOOSEST, most expressive preset was the one she picked, so style is working
# for this voice, not against it. What that preset does not have is her
# timbre at full strength: it sits at 85% similarity, and 100% with the style
# left high is a combination nobody has heard.
#
# So these hold the delivery she chose and move only the similarity, plus one
# that pushes both further. The first entry is her pick, unchanged and
# deliberately re-sent: judging audio against a memory of yesterday's audio is
# not a comparison, and the control costs one more file.
AJUSTES_FINOS: dict[str, dict] = {
    "el-que-elegiste": {  # el control: exactamente lo que ya eligio
        "stability": 0.10, "similarity_boost": 0.85, "style": 0.75,
        "use_speaker_boost": True,
    },
    "mismo-tono-mas-parecido": {
        "stability": 0.10, "similarity_boost": 0.95, "style": 0.75,
        "use_speaker_boost": True,
    },
    "mismo-tono-parecido-total": {
        "stability": 0.10, "similarity_boost": 1.0, "style": 0.75,
        "use_speaker_boost": True,
    },
    "al-limite": {
        "stability": 0.05, "similarity_boost": 1.0, "style": 0.9,
        "use_speaker_boost": True,
    },
}

# Written to be read aloud badly: a long spoken figure, an awkward proper
# noun, a question, a subordinate clause and a colon - the places a synthetic
# voice puts the stress in the wrong spot. Longer than the cloning test phrase
# because phrasing is what is being judged here, and phrasing needs somewhere
# to go wrong.
#
# ACCENTED, which the first version of this was not. It scored zero on
# spanish.tasa_de_acentos and said "anos" out loud - the exact failure this
# project already had a rule about for generated narration, walked into by
# hand in a phrase whose whole job is to be pronounced.
FRASE_DE_ENTONACION = (
    "El dos de noviembre de mil novecientos ochenta y ocho, Robert Tappan Morris tenía "
    "veintitrés años y estudiaba en Cornell. ¿Qué hizo exactamente? Escribió noventa y nueve "
    "líneas de código que se copiaban solas de un ordenador a otro, y en cuestión de horas "
    "había tumbado el diez por ciento de internet. No quería romper nada: quería contar "
    "cuántas máquinas había."
)

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
    # Warned here rather than trusted upstream, because this is the last point
    # before the characters are paid for and spoken. Any text reaches this
    # function - a generated script, a hand-written test phrase, something
    # typed into a Telegram command - and the voice reads the spelling, so
    # unaccented Spanish comes out as different words, not as sloppy ones.
    acentuadas, palabras, tasa = tasa_de_acentos(texto)
    if palabras and tasa < MIN_TASA_ACENTOS:
        logger.warning(
            "El texto a sintetizar va practicamente sin acentos (%s de %s palabras, %.1f%%). "
            "La voz lee la ortografia tal cual, asi que una palabra sin tilde o sin ene suena "
            "como OTRA palabra, no como una version descuidada de la suya. Texto: %.80s",
            acentuadas, palabras, tasa * 100, texto,
        )

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
    # The SETTINGS go in the log, not just the model. Without them two
    # different sweeps of four takes each look identical afterwards - same
    # model, same character count - and I read one as the other and told her
    # the log said something it could not say. A log that cannot tell two runs
    # apart is not evidence about which one happened.
    ajustes_usados = cuerpo["voice_settings"]
    logger.info(
        "Voz clonada con %s (estabilidad %.2f, parecido %.2f, estilo %.2f): "
        "%s caracteres, %.1f KB.",
        cuerpo["model_id"], ajustes_usados.get("stability", -1),
        ajustes_usados.get("similarity_boost", -1), ajustes_usados.get("style", -1),
        len(texto), len(response.content) / 1024,
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
# Read off the account's own pricing table rather than assumed. v3 is listed
# at the same price as multilingual v2 - $0.10 per thousand characters - and
# Flash and Turbo at half that. Worth checking rather than guessing: the
# spend was running 1,460 credits over what these rates predicted, and the
# obvious explanation was that v3 billed at nearly twice the rate, which
# would have doubled every long video's cost and halved how many the plan
# could carry. It does not. The gap was spending outside this bot.
#
# The table is quoted for the Free tier; the absolute prices differ by plan,
# but what these numbers are used for is the RATIO between models, which does
# not.
_CREDITOS_POR_CARACTER = {
    "eleven_v3": 1.0,
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


# ---------------------------------------------------------------------------
# Which voice, which model, which settings - kept where every caller can read
# it.
#
# The choice is made by listening, in Telegram, and then used by the pipeline
# when it builds a video, which are two different processes on two different
# days. Holding it in one file next to the audio is what lets the second one
# honour a decision the first one made.

_ESTADO = "voz_clonada.json"


def estado_voz() -> dict:
    """The cloned voice on the account, and what was decided about it."""
    fichero = Path(DATA_DIR) / _ESTADO
    if fichero.exists():
        try:
            return json.loads(fichero.read_text())
        except ValueError:
            logger.warning("El estado de la voz esta corrupto; se ignora.")
    # Migration from the version that stored a bare voice id. The number of
    # samples is unknown and 1 is right: that version could only use one.
    viejo = Path(DATA_DIR) / "voz_clonada.txt"
    if viejo.exists():
        return {"voice_id": viejo.read_text().strip(), "muestras": 1}
    return {}


def guardar_estado_voz(**cambios) -> dict:
    """Updates the stored decision without losing the parts not being changed.

    A merge rather than a write, because the voice id is set when the voice is
    rebuilt and the model and settings are set later, when somebody has
    listened - and a plain write from either side would erase the other."""
    estado = {**estado_voz(), **cambios}
    (Path(DATA_DIR) / _ESTADO).write_text(json.dumps(estado))
    viejo = Path(DATA_DIR) / "voz_clonada.txt"
    if viejo.exists():
        viejo.unlink()
    return estado


def ajustes_elegidos() -> tuple[str | None, str, dict]:
    """(voice id, model, settings) as last chosen, with defaults where not.

    Defaults matter here: a video must not fail to build because nobody has
    run the comparison yet. Without a choice it falls back to the conservative
    model and the settings the first clone used."""
    estado = estado_voz()
    modelo = estado.get("model") or _MODEL
    preset = estado.get("preset")
    ajustes = AJUSTES_PRESETS.get(preset) or AJUSTES_FINOS.get(preset) or AJUSTES_PARECIDO
    return estado.get("voice_id"), modelo, dict(ajustes)


# ---------------------------------------------------------------------------
# Narrating a whole script in the cloned voice.
#
# Same contract as tts.synthesize_scenes - (audio file, one duration per
# scene) - so the pipeline can swap one for the other without knowing which
# it got.

# Bigger chunks than the Google path uses, and for the opposite reason: there
# the limit is the API's, here it is drift. A clone at low stability wanders
# over a long request, and short requests break the prosody at every seam.
# Fifteen hundred characters is roughly a minute of speech.
_MAX_CHUNK_CHARS = 1500


def _trozos(scenes: list[dict]) -> list[list[dict]]:
    grupos: list[list[dict]] = []
    actual: list[dict] = []
    largo = 0
    for scene in scenes:
        texto = len(scene.get("narration", ""))
        if actual and largo + texto > _MAX_CHUNK_CHARS:
            grupos.append(actual)
            actual, largo = [], 0
        actual.append(scene)
        largo += texto
    if actual:
        grupos.append(actual)
    return grupos


def _hablar_con_marcas(
    voice_id: str, texto: str, model: str, ajustes: dict, antes: str, despues: str
) -> tuple[bytes, list[float] | None]:
    """One chunk of narration, with per-character timings when they are given.

    The timings are what make this cheap. The Google path synthesises every
    scene twice - once alone to measure it and once in its group to sound
    continuous - which here would mean paying for every character twice. This
    endpoint returns the audio AND where each character falls inside it, so
    the scene boundaries come out exact for the price of one take.

    `antes` and `despues` are the surrounding narration. They are not spoken
    and not billed; they tell the model what it is in the middle of, so the
    seams between chunks do not land on a sentence that starts from nothing."""
    cuerpo = {
        "text": texto,
        "model_id": model,
        "voice_settings": ajustes,
    }
    if antes:
        cuerpo["previous_text"] = antes[-500:]
    if despues:
        cuerpo["next_text"] = despues[:500]

    response = requests.post(
        f"{_BASE}/text-to-speech/{voice_id}/with-timestamps",
        headers={**_headers(), "Content-Type": "application/json"},
        json=cuerpo,
        timeout=300,
    )
    if response.status_code >= 400:
        # Not every model serves timestamps. Falling back to plain synthesis
        # loses the exact boundaries, not the narration - so it is a warning
        # and a cruder split, not a failed video.
        logger.warning(
            "Sin marcas de tiempo (%s); se reparte la duracion por longitud.",
            _explica(response),
        )
        return _hablar_sin_marcas(voice_id, texto, model, ajustes, antes, despues), None

    try:
        datos = response.json()
        audio = base64.b64decode(datos["audio_base64"])
        alineacion = datos.get("alignment") or {}
        caracteres = alineacion.get("characters") or []
        finales = alineacion.get("character_end_times_seconds") or []
    except (ValueError, KeyError, TypeError):
        raise CloneError("Respuesta inesperada al sintetizar con marcas de tiempo.")

    # The alignment is only usable if it lines up with the text that was sent.
    # If the model normalised the text on the way in, the indices mean
    # something else and using them would cut the scenes in the wrong places.
    if len(caracteres) != len(texto) or len(finales) != len(texto):
        logger.warning(
            "Las marcas no cuadran con el texto (%s marcas para %s caracteres); "
            "se reparte por longitud.", len(finales), len(texto),
        )
        return audio, None
    return audio, list(finales)


def _hablar_sin_marcas(
    voice_id: str, texto: str, model: str, ajustes: dict, antes: str, despues: str
) -> bytes:
    cuerpo = {"text": texto, "model_id": model, "voice_settings": ajustes}
    if antes:
        cuerpo["previous_text"] = antes[-500:]
    if despues:
        cuerpo["next_text"] = despues[:500]
    response = requests.post(
        f"{_BASE}/text-to-speech/{voice_id}",
        headers={**_headers(), "Accept": "audio/mpeg", "Content-Type": "application/json"},
        json=cuerpo,
        timeout=300,
    )
    if response.status_code >= 400:
        raise CloneError(_explica(response))
    return response.content


def sintetizar_escenas(scenes: list[dict], out_dir: Path) -> tuple[Path, list[float]]:
    """The whole script in the cloned voice, and how long each scene runs.

    Interchangeable with tts.synthesize_scenes: same arguments, same return,
    so the pipeline picks one and the rest of the build does not care."""
    voice_id, modelo, ajustes = ajustes_elegidos()
    if not voice_id:
        raise CloneError(
            "No hay ninguna voz clonada todavia. Manda /clon antes de generar con ella."
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    narraciones = [s.get("narration", "") for s in scenes]
    grupos = _trozos(scenes)
    completo = AudioSegment.empty()
    pausa = AudioSegment.silent(duration=250)
    duraciones: list[float] = []
    caracteres_totales = 0

    hablado = 0
    for indice, grupo in enumerate(grupos):
        texto = " ".join(s.get("narration", "") for s in grupo)
        antes = " ".join(narraciones[max(0, hablado - 3):hablado])
        despues = " ".join(narraciones[hablado + len(grupo):hablado + len(grupo) + 3])
        audio_bytes, finales = _hablar_con_marcas(
            voice_id, texto, modelo, ajustes, antes, despues
        )
        caracteres_totales += len(texto)
        trozo = AudioSegment.from_file(io.BytesIO(audio_bytes))
        real = len(trozo) / 1000.0

        if finales:
            # Exact: each scene ends where its last character was spoken.
            duraciones += _por_marcas(grupo, finales, real)
        else:
            # Crude but safe: split the take in proportion to how much text
            # each scene contributed. Wrong on a scene that happens to be
            # spoken faster than its neighbours, and never wrong by enough to
            # desynchronise the video, because the parts still sum to the take.
            duraciones += _por_longitud(grupo, real)

        completo += trozo
        if indice < len(grupos) - 1:
            completo += pausa
            duraciones[-1] += len(pausa) / 1000.0
        hablado += len(grupo)

    destino = out_dir / "narracion.mp3"
    completo.export(destino, format="mp3")
    logger.info(
        "Narracion clonada: %s escenas en %s tomas, %.1fs, %s caracteres "
        "(~%.0f creditos con %s).",
        len(scenes), len(grupos), len(completo) / 1000.0, caracteres_totales,
        creditos_estimados("x" * caracteres_totales, modelo), modelo,
    )
    return destino, duraciones


def _por_marcas(grupo: list[dict], finales: list[float], real: float) -> list[float]:
    """Scene durations read off the character timings."""
    duraciones = []
    anterior = 0.0
    posicion = 0
    for numero, scene in enumerate(grupo):
        posicion += len(scene.get("narration", ""))
        # The last scene of the take owns the tail, so the parts always sum to
        # the audio: a rounding gap here would drift the video out of sync.
        if numero == len(grupo) - 1:
            fin = real
        else:
            fin = min(finales[min(posicion, len(finales)) - 1], real)
            posicion += 1  # el espacio que une las escenas
        duraciones.append(max(fin - anterior, 0.05))
        anterior = fin
    return duraciones


def _por_longitud(grupo: list[dict], real: float) -> list[float]:
    largos = [max(len(s.get("narration", "")), 1) for s in grupo]
    total = sum(largos)
    duraciones = [real * largo / total for largo in largos]
    # Same rule as above: give the remainder to the last scene rather than
    # letting rounding lose it.
    duraciones[-1] = real - sum(duraciones[:-1])
    return duraciones
