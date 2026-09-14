import json

import anthropic

from .config import ANTHROPIC_API_KEY, CLAUDE_MODEL

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

_PROMPT_TEMPLATE = """Analiza estas narraciones, una por escena, de un guion de video de noticias.
Para cada escena (identificada por su indice numerico), identifica CUALQUIER persona publica real,
lugar, institucion, organizacion o partido politico con NOMBRE PROPIO que se mencione explicitamente
en esa narracion en concreto - solo lo que ESA escena nombra, no lo que se infiere del contexto
general del guion.

Para cada entidad que encuentres, da:
- "name": el nombre tal cual deberia buscarse en Wikipedia (nombre completo, sin apodos ni articulos
  sueltos)
- "type": "person" si es una persona, "place" si es un lugar/institucion/organizacion/partido
- "descriptor": para una persona, su cargo/titulo actual en 2-4 palabras; para un lugar, un
  descriptor corto, o cadena vacia si el nombre ya se explica solo

No incluyas victimas de crimenes/tragedias ni particulares sin relevancia publica como "person" -
si la unica persona nombrada en una escena es asi, omitela por completo de esa escena. Si una
escena no menciona ninguna entidad valida, su lista debe ser exactamente [].

Escenas (indice: texto de la narracion):
{scenes_block}

Devuelve EXCLUSIVAMENTE un JSON con esta forma exacta, sin texto adicional ni markdown, con una
clave por cada indice de escena de la lista de arriba en el mismo orden:
{{
  "0": [{{"name": "...", "type": "person", "descriptor": "..."}}],
  "1": [],
  "2": [{{"name": "...", "type": "place", "descriptor": "..."}}]
}}
"""


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
    return text.strip()


def extract_entities(scenes: list[dict]) -> dict[int, list[dict]]:
    """Dedicated, isolated pass over the final narration text asking Claude
    to list every named person/place/institution/party per scene. Doing
    this as its own focused call - instead of relying on photo_subject, one
    more field buried inside the much larger script-generation prompt that
    also juggles tone, SEO, scene timing, etc. - has proven far more
    reliable in practice than either the model's own inline tagging there
    or a hand-rolled regex heuristic over the narration text.

    Returns an empty dict on any failure (missing text, bad JSON, API
    error), so callers can fall back to whatever else they already use
    (the model's own photo_subject) instead of breaking generation."""
    scenes_block = "\n".join(f'{i}: "{scene["narration"]}"' for i, scene in enumerate(scenes))
    prompt = _PROMPT_TEMPLATE.format(scenes_block=scenes_block)

    try:
        message = _client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text_blocks = [block.text for block in message.content if block.type == "text"]
        if not text_blocks:
            return {}
        parsed = json.loads(_strip_markdown_fence(text_blocks[0]))
        return {int(index): entities for index, entities in parsed.items()}
    except Exception:
        return {}
