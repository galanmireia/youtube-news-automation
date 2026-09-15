import json
import logging
import threading
from datetime import date
from pathlib import Path

from google import genai
from google.genai import types

from .config import (
    AI_IMAGES_DAILY_LIMIT,
    DATA_DIR,
    GOOGLE_CLOUD_LOCATION,
    GOOGLE_CLOUD_PROJECT_ID,
)

logger = logging.getLogger(__name__)

# The old vertexai.preview.vision_models.ImageGenerationModel path 404'd on
# its model-metadata lookup (publishers/google/models/imagegeneration@006
# "not found") regardless of the model name tried. The unified google-genai
# SDK skips that lookup entirely and calls the model's :predict endpoint
# directly, which is the officially supported replacement going forward.
# Tried in order until one answers. Google retires and renames these every few
# months, and asking for a retired one comes back as 404 "not found or your
# project does not have access to it" - which reads like a permissions problem
# and is not. Picking a single name means being wrong again the next time one
# is retired; trying a list means the first working model is found whatever
# Google has done since, and the one that works is remembered for the process.
_IMAGE_MODELS = (
    "imagen-4.0-generate-001",
    "imagen-4.0-fast-generate-001",
    "imagen-3.0-generate-002",
    "imagen-3.0-generate-001",
    "imagen-3.0-fast-generate-001",
    "imagegeneration@006",
)

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


def check_access() -> tuple[bool, str]:
    """Asks Vertex AI for one small image and reports what happened.

    Whether the permissions are in place is otherwise invisible until a scene
    happens to need an illustration, which can be many videos away - and the
    error, when it does come, is buried in a traceback in the deploy logs.
    Returns (works, explanation in Spanish) so the answer can be read
    anywhere."""
    global _working_model
    intentados = []
    try:
        client = _get_client()
        last_error: Exception | None = None
        for model in _models_to_try():
            try:
                response = client.models.generate_images(
                    model=model,
                    prompt="a simple blue circle on a white background",
                    config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="1:1"),
                )
            except Exception as exc:
                intentados.append(model)
                last_error = exc
                if _is_missing_model(exc):
                    continue
                raise
            if not response.generated_images:
                return False, f"El modelo {model} respondio sin imagen."
            _working_model = model
            return True, f"Funciona. Modelo en uso: {model}"
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
        response = None
        for model in _models_to_try():
            try:
                response = client.models.generate_images(
                    model=model,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio=aspect_ratio,
                        safety_filter_level=types.SafetyFilterLevel.BLOCK_MEDIUM_AND_ABOVE,
                        person_generation=types.PersonGeneration.ALLOW_ADULT,
                        output_mime_type="image/jpeg",
                    ),
                )
                _working_model = model
                break
            except Exception as exc:
                # A retired or unavailable model is worth stepping past; any
                # other failure is about this request and retrying the same
                # call under a different name would only repeat it.
                if not _is_missing_model(exc):
                    raise
                logger.info("Modelo %s no disponible, probando el siguiente.", model)
        if response is None or not response.generated_images:
            logger.warning("Vertex AI no devolvio ninguna imagen para el prompt %r", prompt)
            return None
        response.generated_images[0].image.save(str(out_path))
        logger.info("Imagen generada con IA para el prompt %r", prompt)
        return out_path
    except Exception:
        logger.warning("No se pudo generar la imagen con IA para el prompt %r", prompt, exc_info=True)
        return None
