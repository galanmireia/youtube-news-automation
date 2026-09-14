import logging
from pathlib import Path

import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

from .config import GOOGLE_CLOUD_LOCATION, GOOGLE_CLOUD_PROJECT_ID

logger = logging.getLogger(__name__)

_model = None


def _get_model() -> ImageGenerationModel:
    global _model
    if _model is None:
        vertexai.init(project=GOOGLE_CLOUD_PROJECT_ID, location=GOOGLE_CLOUD_LOCATION)
        _model = ImageGenerationModel.from_pretrained("imagegeneration@006")
    return _model


def generate_image(prompt: str, out_path: Path, aspect_ratio: str) -> Path | None:
    """Generates an illustrative image for scenes tied to a very specific
    place/concept that generic stock footage won't have (e.g. a particular
    town or a local event). Returns None on any failure so callers fall back
    to stock footage instead of breaking the whole video."""
    try:
        model = _get_model()
        images = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio=aspect_ratio,
            safety_filter_level="block_some",
            person_generation="allow_adult",
        )
        images[0].save(location=str(out_path), include_generation_parameters=False)
        return out_path
    except Exception:
        logger.warning("No se pudo generar la imagen con IA para el prompt %r", prompt, exc_info=True)
        return None
