import json
import logging
import threading
from datetime import date
from pathlib import Path

from google import genai
from google.genai import types

from .config import (
    AI_IMAGE_USD_PER_MILLION_OUTPUT_TOKENS,
    AI_IMAGES_DAILY_LIMIT,
    DATA_DIR,
    GOOGLE_CLOUD_LOCATION,
    GOOGLE_CLOUD_PROJECT_ID,
)

logger = logging.getLogger(__name__)

# Google retired Imagen from this project entirely and moved image generation
# into the Gemini models: asking Vertex what it actually has here returned 132
# models, none of them an Imagen, and these five. So this is no longer an
# Imagen client - these are ordinary Gemini models called through
# generate_content, asked to answer with a picture instead of with text.
#
# Names come from that live catalogue rather than from memory. Six Imagen
# names were guessed at over two days and all six 404'd; the list Vertex
# reports is the only reliable source, and /vertex prints it when nothing
# works. Flash first because it is the cheap one and this is illustration,
# not art direction; pro as a fallback; the preview build last.
# 2.5 first because it is the one that actually answers. The 3.x names are in
# the catalogue Vertex lists for this project and still 404 on generateContent,
# which is worth knowing: being listed is not the same as being callable, so
# the order here comes from what replied, not from what was advertised.
_IMAGE_MODELS = (
    "gemini-2.5-flash-image",
    "gemini-3.1-flash-image",
    "gemini-3-pro-image",
    "gemini-3.1-flash-lite-image",
    "gemini-3.1-flash-image-preview",
)

# The channel's illustration style, appended to every prompt.
#
# It lives here rather than in the script prompt on purpose: asked to describe
# the style itself, the script model phrases it differently for every scene and
# the video comes back a collage - one flat vector, one photoreal, one 3D
# render. Splitting it this way means the script decides WHAT is shown and this
# decides HOW, identically every time, across scenes and across videos.
#
# The palette is the channel's own (branding.py): charcoal #1A1715, cream
# #F0EBDC, crimson #C41E2A, so an illustration and a fact card look like they
# came from the same place.
#
# Two composition rules earn their place. No text of any kind, because these
# models render lettering as convincing gibberish and the video already puts
# real words on screen. And clear space low and top-right, where the burned
# subtitles and the source tag sit - an illustration whose subject is dead
# centre-bottom gets covered by its own captions.
_HOUSE_STYLE = (
    "editorial news illustration, flat vector shapes with subtle paper grain, "
    "limited palette of deep charcoal #1A1715, warm cream #F0EBDC and a single "
    "crimson #C41E2A accent, muted desaturated supporting tones, one clear focal "
    "subject, strong simple silhouettes, restrained serious documentary tone, "
    "not cartoonish, not whimsical, no caricature, "
    "generous empty space across the bottom fifth and the top-right corner, "
    "absolutely no text, no words, no letters, no numbers, no logos, no watermarks, "
    "no recognisable real people"
)


def _styled(prompt: str) -> str:
    return f"{prompt.strip().rstrip('.')}. {_HOUSE_STYLE}"


_working_model: str | None = None

# The day's tally lives on the persistent volume, not in memory: a deploy or a
# crash restarts the process several times a day, and a counter that resets
# with it would not be a daily limit at all.
_USAGE_FILE = Path(DATA_DIR) / "ai_image_usage.json"
_usage_lock = threading.Lock()


def _take_daily_allowance() -> tuple[bool, int]:
    """Counts one image against today's allowance.

    Returns (allowed, images used today including this one). Reserves the slot
    before the image is requested rather than after it arrives: a failed call
    that still counted is the safe way round, since the alternative is a call
    that bills but never counts."""
    with _usage_lock:
        today = date.today().isoformat()
        used = 0
        try:
            stored = json.loads(_USAGE_FILE.read_text())
            if stored.get("date") == today:
                used = int(stored.get("count", 0))
        except (OSError, ValueError, TypeError):
            # No tally yet, or an unreadable one: today starts at zero. Never
            # fail image generation over a bookkeeping file.
            used = 0
        if used >= AI_IMAGES_DAILY_LIMIT:
            return False, used
        used += 1
        try:
            _USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
            _USAGE_FILE.write_text(json.dumps({"date": today, "count": used}))
        except OSError:
            logger.warning("No se pudo guardar el contador de imagenes de IA", exc_info=True)
        return True, used


def _image_config(aspect_ratio: str):
    """The frame shape to ask for, or None if this SDK build has no say in it.
    Not worth failing a whole image over: a picture in the wrong shape still
    gets blur-fitted into the frame like every stock photo does."""
    try:
        return types.ImageConfig(aspect_ratio=aspect_ratio)
    except (AttributeError, TypeError, ValueError):
        logger.info("El SDK de genai no acepta image_config; la imagen vendra en su forma por defecto.")
        return None


def _first_image_bytes(response) -> bytes | None:
    """Digs the picture out of a Gemini reply. These models answer with the
    same parts structure as any other Gemini call - the image arrives as
    inline data among them, possibly alongside text, which is ignored."""
    for candidate in getattr(response, "candidates", None) or []:
        content = getattr(candidate, "content", None)
        for part in (getattr(content, "parts", None) or []):
            inline = getattr(part, "inline_data", None)
            data = getattr(inline, "data", None)
            if data:
                return data
    return None


def _request_image(client, model: str, prompt: str, aspect_ratio: str) -> bytes | None:
    """Asks one model for one picture. TEXT is left in the accepted reply
    types alongside IMAGE because some of these models refuse an image-only
    request, and an unwanted text part costs nothing to ignore."""
    config_kwargs = {"response_modalities": ["TEXT", "IMAGE"]}
    image_config = _image_config(aspect_ratio)
    if image_config is not None:
        config_kwargs["image_config"] = image_config
    response = client.models.generate_content(
        model=model, contents=prompt, config=types.GenerateContentConfig(**config_kwargs)
    )
    coste = _describe_cost(model, response)
    if coste:
        logger.info("%s", coste)
    return _first_image_bytes(response), coste


def _describe_cost(model: str, response) -> str:
    """What this one call consumed, and what that costs at the configured rate.

    These models are billed by token like any other Gemini call and the reply
    carries its own count, so the price of a single image can be worked out
    immediately instead of waiting hours for Cloud billing - and per image,
    which a monthly bill never tells you. The rate is stated in the text
    because it is a default rather than a verified figure: a number with its
    assumption attached can be corrected, a bare number cannot."""
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return ""
    salida = getattr(usage, "candidates_token_count", None)
    entrada = getattr(usage, "prompt_token_count", None)
    partes = [f"{model}: {entrada if entrada is not None else '?'} tokens de entrada, "
              f"{salida if salida is not None else '?'} de salida"]
    if isinstance(salida, int) and salida > 0:
        usd = salida / 1_000_000 * AI_IMAGE_USD_PER_MILLION_OUTPUT_TOKENS
        partes.append(
            f"= {usd:.4f} $ por imagen a {AI_IMAGE_USD_PER_MILLION_OUTPUT_TOKENS:g} $/millon "
            f"(tarifa SIN verificar, ajustable con AI_IMAGE_USD_PER_MILLION_OUTPUT_TOKENS). "
            f"Un dia entero al tope de {AI_IMAGES_DAILY_LIMIT} serian {usd * AI_IMAGES_DAILY_LIMIT:.2f} $"
        )
    return " ".join(partes)


def _save_jpeg(data: bytes, out_path: Path) -> Path:
    """Writes the picture as a real JPEG whatever Gemini sent back, since the
    rest of the pipeline names these files .jpg and ffmpeg is happier when the
    name and the contents agree."""
    from io import BytesIO

    from PIL import Image

    with Image.open(BytesIO(data)) as image:
        image.convert("RGB").save(out_path, "JPEG", quality=92)
    return out_path


def _is_missing_model(error: Exception) -> bool:
    detail = str(error)
    return "404" in detail or "NOT_FOUND" in detail


def _models_to_try() -> tuple[str, ...]:
    """The known-good model first, if one has answered already this run."""
    if _working_model is None:
        return _IMAGE_MODELS
    return (_working_model,) + tuple(m for m in _IMAGE_MODELS if m != _working_model)

# The SDK defaults to no HTTP timeout at all, so a request that never gets a
# response blocks its thread for good. That is not theoretical: it hung a
# whole generation - the pipeline thread stopped mid-scene with no error and
# no CPU use, and because that thread holds the "one generation at a time"
# lock, every later /generar just answered "ya hay una generacion en curso"
# until the container was restarted. Expressed in milliseconds, as the SDK
# expects.
_HTTP_TIMEOUT_MS = 120_000

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        kwargs = {"vertexai": True, "project": GOOGLE_CLOUD_PROJECT_ID, "location": GOOGLE_CLOUD_LOCATION}
        try:
            kwargs["http_options"] = types.HttpOptions(timeout=_HTTP_TIMEOUT_MS)
        except Exception:
            # An SDK version that spells the option differently shouldn't cost
            # us image generation entirely - but say so, because it means the
            # hang this guards against is possible again.
            logger.warning("El SDK de genai no acepta http_options.timeout: las llamadas iran sin limite de tiempo", exc_info=True)
        _client = genai.Client(**kwargs)
    return _client


def _list_publisher_models() -> tuple[int, list[str]]:
    """Asks Vertex what publisher models it will list here, returning how many
    came back in total and which of those are image models.

    The total matters as much as the image names. The previous version passed
    filter=model_garden, a guess: a filter Vertex does not understand returns
    an empty list, which is indistinguishable from "this project has no image
    models" - and that is exactly what it looked like. Nothing is filtered
    server-side now, so zero models listed means the query itself is wrong,
    while many models listed and no image ones among them is a real answer."""
    import google.auth
    import google.auth.transport.requests
    import requests

    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    url = (
        f"https://{GOOGLE_CLOUD_LOCATION}-aiplatform.googleapis.com/v1beta1/"
        f"publishers/google/models"
    )
    todos: list[str] = []
    page_token = None
    for _ in range(5):  # enough pages for any plausible catalogue
        params = {"pageSize": 200}
        if page_token:
            params["pageToken"] = page_token
        response = requests.get(
            url, headers={"Authorization": f"Bearer {creds.token}"}, params=params, timeout=30
        )
        response.raise_for_status()
        payload = response.json()
        todos.extend(m.get("name", "").rsplit("/", 1)[-1] for m in payload.get("publisherModels", []))
        page_token = payload.get("nextPageToken")
        if not page_token:
            break
    # Deliberately broad. Looking only for "imagen"/"imagegeneration" answered
    # the question we already knew the answer to: Vertex listed 132 models in
    # us-central1 and reported "none of image", because anything named
    # differently - a Gemini model with image output, say - was filtered out
    # before anyone could see it. Match "image" anywhere instead.
    imagen = sorted({n for n in todos if "image" in n.lower()})
    return len(todos), imagen


def _catalogue_sample(limit: int = 25) -> list[str]:
    """A slice of the publisher models Vertex does list here, for when none of
    them is an image model and the question becomes what this project has."""
    import google.auth
    import google.auth.transport.requests
    import requests

    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    response = requests.get(
        f"https://{GOOGLE_CLOUD_LOCATION}-aiplatform.googleapis.com/v1beta1/publishers/google/models",
        headers={"Authorization": f"Bearer {creds.token}"},
        params={"pageSize": 200},
        timeout=30,
    )
    response.raise_for_status()
    nombres = [m.get("name", "").rsplit("/", 1)[-1] for m in response.json().get("publisherModels", [])]
    return sorted(nombres)[:limit]


def preview(prompt: str, out_path: Path, aspect_ratio: str = "9:16") -> tuple[Path | None, str]:
    """One illustration from a prompt of your choosing, with the house style on
    it, so the look can be judged before committing to a whole generation.

    Seeing whether the style works otherwise costs a full video - six images
    plus every script, voice and render call around them - when one image
    answers the question."""
    allowed, _ = _take_daily_allowance()
    if not allowed:
        return None, f"Limite diario de {AI_IMAGES_DAILY_LIMIT} imagenes alcanzado."
    data = None
    coste = ""
    try:
        client = _get_client()
        for model in _models_to_try():
            try:
                data, coste = _request_image(client, model, _styled(prompt), aspect_ratio)
                globals()["_working_model"] = model
                break
            except Exception as exc:
                if not _is_missing_model(exc):
                    raise
    except Exception as exc:
        return None, f"Error: {str(exc)[:300]}"
    if not data:
        return None, "El modelo no devolvio ninguna imagen."
    try:
        _save_jpeg(data, out_path)
    except Exception as exc:
        return None, f"La imagen llego pero no se pudo guardar: {str(exc)[:200]}"
    return out_path, coste


def check_access() -> tuple[bool, str]:
    """Asks Vertex AI for one small image and reports what happened.

    Whether the permissions are in place is otherwise invisible until a scene
    happens to need an illustration, which can be many videos away - and the
    error, when it does come, is buried in a traceback in the deploy logs.
    Returns (works, explanation in Spanish) so the answer can be read
    anywhere."""
    global _working_model
    allowed, used = _take_daily_allowance()
    if not allowed:
        return False, (
            f"No lo pruebo: ya se ha llegado al limite de {AI_IMAGES_DAILY_LIMIT} imagenes de hoy. "
            "La prueba genera una imagen de verdad y se cobra como cualquier otra."
        )
    intentados = []
    try:
        client = _get_client()
        last_error: Exception | None = None
        for model in _models_to_try():
            try:
                data, coste = _request_image(client, model, "a simple blue circle on a white background", "1:1")
            except Exception as exc:
                intentados.append(model)
                last_error = exc
                if _is_missing_model(exc):
                    continue
                raise
            if not data:
                return False, f"El modelo {model} respondio sin imagen."
            _working_model = model
            resumen = f"Funciona. Modelo en uso: {model} ({len(data) / 1024:.0f} KB)."
            return True, (resumen + "\n" + coste) if coste else (
                resumen + "\nGoogle no ha devuelto el consumo de esta llamada, asi que no puedo "
                "decirte lo que ha costado."
            )
        raise last_error  # type: ignore[misc]
    except Exception as exc:
        detail = str(exc)
        if "PERMISSION_DENIED" in detail or "403" in detail:
            if "has not been used" in detail or "is disabled" in detail:
                return False, (
                    "La Vertex AI API esta DESACTIVADA en el proyecto. Activala en "
                    "console.cloud.google.com/apis/library/aiplatform.googleapis.com"
                )
            return False, (
                "Falta el permiso. Da el rol 'Vertex AI User' a la cuenta "
                "tts-service@lucky-album-508608-t0.iam.gserviceaccount.com en "
                "console.cloud.google.com/iam-admin/iam"
            )
        if "billing" in detail.lower():
            return False, "Google pide activar la facturacion del proyecto para usar Imagen."
        if _is_missing_model(exc):
            # Report what Google actually said rather than a theory about why.
            # The previous wording asserted the account was still on a free
            # trial; that was a guess dressed as a finding, and it sent us
            # looking in the wrong place.
            contexto = f"Proyecto {GOOGLE_CLOUD_PROJECT_ID}, region {GOOGLE_CLOUD_LOCATION}."
            try:
                total, imagen = _list_publisher_models()
            except Exception as list_exc:
                logger.warning("No se pudo listar los modelos disponibles", exc_info=True)
                return False, (
                    f"Los {len(intentados)} modelos probados dan 404 y ademas no se puede "
                    f"listar el catalogo. {contexto}\nAl listar: {str(list_exc)[:200]}"
                    f"\nError de Google al pedir la imagen: {detail[:400]}"
                )
            if imagen:
                return False, (
                    f"Ninguno de los {len(intentados)} probados existe aqui, pero tu proyecto SI "
                    "ve estos: " + ", ".join(imagen[:12]) + ". Dimelo y lo cambio."
                )
            if total == 0:
                return False, (
                    f"Vertex no lista NINGUN modelo, ni de imagen ni de nada ({contexto}) - "
                    "asi que el problema no es Imagen en concreto, es el acceso al catalogo "
                    f"entero.\nError de Google al pedir la imagen: {detail[:400]}"
                )
            # No image model under any spelling: show what the catalogue does
            # hold, so the next step comes from the real list instead of from
            # another guess at a model name.
            try:
                muestra = ", ".join(_catalogue_sample())
            except Exception:
                muestra = "(no se pudo releer el catalogo)"
            return False, (
                f"Vertex lista {total} modelos aqui y ninguno lleva 'image' en el nombre; los "
                f"{len(intentados)} probados dan 404. {contexto}\n"
                f"Muestra del catalogo: {muestra}\n"
                f"Error de Google: {detail[:300]}"
            )
        logger.warning("check_access: error inesperado", exc_info=True)
        return False, f"Error inesperado: {detail[:300]}"


def generate_image(prompt: str, out_path: Path, aspect_ratio: str) -> Path | None:
    """Generates an illustrative image for scenes tied to a very specific
    place/concept that generic stock footage won't have (e.g. a particular
    town or a local event). Returns None on any failure so callers fall back
    to stock footage instead of breaking the whole video."""
    allowed, used = _take_daily_allowance()
    if not allowed:
        logger.warning(
            "Limite diario de imagenes por IA alcanzado (%s). Se usa material de archivo en su lugar.",
            AI_IMAGES_DAILY_LIMIT,
        )
        return None
    try:
        global _working_model
        client = _get_client()
        logger.info(
            "Generando imagen con IA para el prompt %r... (%s/%s hoy)",
            prompt,
            used,
            AI_IMAGES_DAILY_LIMIT,
        )
        data = None
        for model in _models_to_try():
            try:
                data, _ = _request_image(client, model, _styled(prompt), aspect_ratio)
                _working_model = model
                break
            except Exception as exc:
                # A retired or unavailable model is worth stepping past; any
                # other failure is about this request and retrying the same
                # call under a different name would only repeat it.
                if not _is_missing_model(exc):
                    raise
                logger.info("Modelo %s no disponible, probando el siguiente.", model)
        if not data:
            logger.warning("Vertex no devolvio ninguna imagen para el prompt %r", prompt)
            return None
        _save_jpeg(data, out_path)
        logger.info("Imagen generada con IA (%s) para el prompt %r", _working_model, prompt)
        return out_path
    except Exception:
        logger.warning("No se pudo generar la imagen con IA para el prompt %r", prompt, exc_info=True)
        return None
