import logging
from pathlib import Path

from google import genai
from google.genai import types

from .config import GOOGLE_CLOUD_LOCATION, GOOGLE_CLOUD_PROJECT_ID

logger = logging.getLogger(__name__)

# The old vertexai.preview.vision_models.ImageGenerationModel path 404'd on
# its model-metadata lookup (publishers/google/models/imagegeneration@006
# "not found") regardless of the model name tried. The unified google-genai
# SDK skips that lookup entirely and calls the model's :predict endpoint
# directly, which is the officially supported replacement going forward.
_IMAGE_MODEL = "imagen-3.0-generate-002"

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


def generate_image(prompt: str, out_path: Path, aspect_ratio: str) -> Path | None:
    """Generates an illustrative image for scenes tied to a very specific
    place/concept that generic stock footage won't have (e.g. a particular
    town or a local event). Returns None on any failure so callers fall back
    to stock footage instead of breaking the whole video."""
    try:
        client = _get_client()
        logger.info("Generando imagen con IA para el prompt %r...", prompt)
        response = client.models.generate_images(
            model=_IMAGE_MODEL,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                safety_filter_level=types.SafetyFilterLevel.BLOCK_MEDIUM_AND_ABOVE,
                person_generation=types.PersonGeneration.ALLOW_ADULT,
                output_mime_type="image/jpeg",
            ),
        )
        if not response.generated_images:
            logger.warning("Vertex AI no devolvio ninguna imagen para el prompt %r", prompt)
            return None
        response.generated_images[0].image.save(str(out_path))
        logger.info("Imagen generada con IA para el prompt %r", prompt)
        return out_path
    except Exception:
        logger.warning("No se pudo generar la imagen con IA para el prompt %r", prompt, exc_info=True)
        return None
