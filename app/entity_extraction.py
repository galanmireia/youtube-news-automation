import json
import logging

import anthropic

from . import llm_usage
from .config import ANTHROPIC_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

_PROMPT_TEMPLATE = """Analiza estas narraciones, una por escena, de un guion de video de noticias.
Para cada escena (identificada por su indice numerico), identifica CUALQUIER persona publica real,
lugar, institucion, organizacion o partido politico con NOMBRE PROPIO que se mencione explicitamente
en esa narracion en concreto - solo lo que ESA escena nombra, no lo que se infiere del contexto
general del guion.

Para cada entidad que encuentres, da:
- "name": el nombre tal cual deberia buscarse en Wikipedia (nombre completo, sin apodos ni articulos
  sueltos). Si el nombre es generico y existe con el mismo nombre en varios paises (ej. "Partido
  Popular" existe en España, Portugal y otros paises), añade el pais entre parentesis para
  desambiguar, ej. "Partido Popular (España)" - si no, la busqueda en Wikipedia puede devolver el
  articulo o la imagen equivocada.
- "type": "person" si es una persona, "place" si es un lugar/institucion/organizacion/partido
- "descriptor": para una persona, su cargo/titulo actual en 2-4 palabras; para un lugar, un
  descriptor corto, o cadena vacia si el nombre ya se explica solo

No incluyas victimas de crimenes/tragedias ni particulares sin relevancia publica como "person" -
si la unica persona nombrada en una escena es asi, omitela por completo de esa escena.

NO INCLUYAS NUNCA al MEDIO DE COMUNICACION que publica o difunde la noticia: BBC, El Mundo, El
Pais, El Confidencial, La Vanguardia, RTVE, Antena 3, Muy Interesante, Reuters, EFE, etc. Cuando la
narracion dice "segun El Mundo" o "informa la BBC", ese medio es solo la FUENTE de la informacion,
no algo de lo que trate la noticia. Sacar su logo o una foto suya en pantalla no ilustra nada: en
un video sobre riesgos de la inteligencia artificial acabaria apareciendo la foto de una fiesta de
aniversario de un periodico. Omitelo. La unica excepcion es que el medio sea el ASUNTO de la
noticia (por ejemplo, un juicio contra ese periodico o su cierre).

Si una escena no menciona ninguna entidad valida, su lista debe ser exactamente [].

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


# Doce escenas por llamada. El Short que si funcionaba tenia seis y gasto
# bastante menos de la mitad del tope, asi que doce deja margen de sobra
# incluso con escenas llenas de nombres.
_POR_LOTE = 12


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
    # POR LOTES, y esto es lo que fallaba en los largos. Se mandaban las 31
    # escenas de una y la respuesta topaba con el limite de salida:
    #
    #   [coste] entidades: 4659 entrada + 6000 salida
    #   extract_entities: JSON invalido, ...{"name": "Rosario Porto Ortega",
    #   "type": "person", "descriptor": "abogada, cond'
    #
    # Cortado a media palabra, asi que el JSON entero se tiraba y el video se
    # quedaba sin UNA SOLA entidad detectada - habiendo detectado bien a los
    # dos padres, que se ven en el trozo truncado. En un Short de seis escenas
    # cabia de sobra y por eso no habia salido nunca.
    #
    # Subir el tope solo mueve el problema al siguiente guion mas largo. Con
    # lotes la respuesta nunca crece: crece el numero de llamadas, que es lo
    # que si escala.
    if len(scenes) > _POR_LOTE:
        salida: dict[int, list[dict]] = {}
        for inicio in range(0, len(scenes), _POR_LOTE):
            trozo = scenes[inicio:inicio + _POR_LOTE]
            for relativo, entidades in extract_entities(trozo).items():
                salida[inicio + relativo] = entidades
        logger.info("Entidades: %s escenas en %s lotes, %s con algo.",
                    len(scenes), -(-len(scenes) // _POR_LOTE), len(salida))
        return salida

    scenes_block = "\n".join(f'{i}: "{scene["narration"]}"' for i, scene in enumerate(scenes))
    prompt = _PROMPT_TEMPLATE.format(scenes_block=scenes_block)

    try:
        message = _client.messages.create(
            model=CLAUDE_MODEL,
            # Room for the model to reason before answering as well as for the
            # answer: the news picker hit max_tokens with nothing but a
            # thinking block, and this call makes a longer reply than that one.
            max_tokens=6000,
            messages=[{"role": "user", "content": prompt}],
        )
        llm_usage.record("entidades", CLAUDE_MODEL, message)
        text_blocks = [block.text for block in message.content if block.type == "text"]
        if not text_blocks:
            logger.warning("extract_entities: la respuesta de Claude no traia ningun bloque de texto")
            return {}
        raw_text = _strip_markdown_fence(text_blocks[0])
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.warning("extract_entities: JSON invalido, respuesta cruda: %r", raw_text)
            return {}
        result = {int(index): entities for index, entities in parsed.items()}
        logger.info("extract_entities: entidades detectadas por escena: %s", result)
        return result
    except Exception:
        logger.warning("extract_entities: fallo inesperado llamando a Claude", exc_info=True)
        return {}
