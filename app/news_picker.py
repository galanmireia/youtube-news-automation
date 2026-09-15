import json
import logging
import re

import anthropic

from .config import ANTHROPIC_API_KEY, CHANNEL_TONE_HINT, CLAUDE_MODEL

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Choosing is one cheap call, and the failures seen are transient (an empty
# reply, malformed JSON). Retrying costs seconds; not retrying costs the run.
_MAX_ATTEMPTS = 3

_PROMPT_TEMPLATE = """Eres el editor de un canal de noticias en video corto (formato Short vertical, unos 60
segundos). Tienes que elegir CUAL de estas noticias merece la pena convertir en video hoy.

Identidad del canal: {tone_hint}

Elige pensando en un espectador que se encuentra el video en su feed sin buscarlo y decide en dos
segundos si sigue viendo o pasa. Prioriza, por este orden:
1. Que haya PERSONAS concretas y algo en juego, no solo instituciones y tramites.
2. Que se entienda sin saber nada previo del tema. Si hace falta explicar tres antecedentes antes de
   llegar al asunto, no funciona en 60 segundos.
3. Que afecte a mucha gente, o que sorprenda, o que tenga consecuencias reales que el espectador
   pueda notar en su vida.

Penaliza fuerte las noticias PURAMENTE de procedimiento: un tramite administrativo, una votacion de
comision, un recurso judicial sobre un plazo, unas declaraciones de un politico respondiendo a otro
politico. Aunque sean importantes, en 60 segundos no hay forma de que le importen a nadie que no
siga ya el tema.

No penalices una noticia por ser dura o triste: sucesos, investigaciones, juicios, condenas,
desapariciones, corrupcion y fallos institucionales SE CUBREN, solo que con tono sobrio y sin
especular. Ese es el terreno donde mejor funciona el canal. Lo que se valora aqui es el interes
para el espectador, no el morbo.

PERO HAY NOTICIAS QUE NO SE PUEDEN CONVERTIR EN VIDEO, por muy interesantes que parezcan, porque
YouTube no las monetiza casi nunca y el canal vive de monetizar. NO ELIJAS NUNCA una noticia cuyo
asunto central sea:
1. La muerte, el maltrato o el abuso de un MENOR de edad.
2. Un suicidio o una autolesion.
3. Violencia sexual, sobre todo con victimas identificables.
4. El detalle de COMO murio o fue herida una persona concreta (heridas, sufrimiento, la escena).
5. La desgracia recien ocurrida de un particular sin relevancia publica, cuando la noticia se
   reduce a que esa persona ha muerto y no hay nada mas que contar todavia.
Estas no son "noticias duras que hay que tratar con cuidado": son noticias que este canal no hace.
Si la unica candidata potente es de este tipo, elige otra aunque sea menos llamativa.

Ojo con la diferencia, porque es sutil: "un juicio por un crimen" SI se cubre; "como murio la
victima de ese crimen" NO. "Una red de abusos destapada por una investigacion" SI; "el relato de lo
que sufrio una victima concreta" NO. Lo que decide no es el tema, es si el video acabaria girando
sobre el dano a una persona concreta.

Noticias candidatas:
{candidates_block}

Devuelve EXCLUSIVAMENTE un JSON con esta forma exacta, sin texto adicional ni markdown:
{{
  "index": 0,
  "reason": "en una frase, por que esta y no las otras"
}}
donde "index" es el numero de la noticia elegida de la lista de arriba.

MUY IMPORTANTE sobre el formato: dentro de "reason" NO uses comillas dobles (") ni saltos de
linea. Muchos titulares llevan comillas dobles, y si las copias dentro del valor rompes el JSON.
Si necesitas citar algo, usa comillas simples.
"""


# Last-ditch way to recover the decision from a reply whose JSON is broken.
# The prose in "reason" is what breaks it (an unescaped quote copied out of a
# headline), and that prose is decoration - the index is the actual answer, so
# losing the whole choice over a stray quote and falling back to "take the
# first story" gives up the entire point of asking.
_INDEX_RE = re.compile(r'"index"\s*:\s*(\d+)')


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
    return text.strip()


def pick_best_story(candidates: list[dict]) -> dict | None:
    """Chooses which of the fetched headlines to actually make a video about,
    or None when it cannot choose safely.

    The pipeline used to take whichever story happened to come first in the
    feed, with no judgement about whether anyone would care - so a procedural
    court filing got the same treatment as a story with a person in it."""
    if len(candidates) <= 1:
        return candidates[0] if candidates else None

    candidates_block = "\n".join(
        f"{i}. {c['title']}\n   {c.get('summary', '')[:300]}" for i, c in enumerate(candidates)
    )
    prompt = _PROMPT_TEMPLATE.format(tone_hint=CHANNEL_TONE_HINT, candidates_block=candidates_block)

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return _pick_once(prompt, candidates)
        except Exception:
            logger.warning("pick_best_story: intento %s/%s fallido", attempt, _MAX_ATTEMPTS, exc_info=True)

    # Taking the first headline on failure is no longer the harmless default
    # it was. This prompt also decides which stories the channel must not make
    # at all, so choosing blindly can hand back precisely the story it was
    # asked to rule out - it just did, returning a story about a dead child
    # that the rules exclude. Making nothing this run is the cheaper mistake:
    # the schedule comes round again.
    logger.error(
        "pick_best_story: no se pudo elegir tras %s intentos; no se genera nada en esta pasada, "
        "porque coger la primera a ciegas se saltaria los filtros de monetizacion.",
        _MAX_ATTEMPTS,
    )
    return None


def _pick_once(prompt: str, candidates: list[dict]) -> dict:
    """One attempt. Raises rather than falling back, so the caller can retry."""
    message = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    text_blocks = [block.text for block in message.content if block.type == "text"]
    if not text_blocks:
        # Says why, rather than just that it happened: an empty reply looks the
        # same whether the model stopped early, hit the token ceiling, or
        # returned only non-text blocks, and those need different fixes.
        raise ValueError(
            f"respuesta sin texto (stop_reason={getattr(message, 'stop_reason', '?')}, "
            f"bloques={[b.type for b in message.content]})"
        )

    raw = _strip_markdown_fence(text_blocks[0])
    try:
        parsed = json.loads(raw)
        index = int(parsed["index"])
        reason = parsed.get("reason", "")
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        # The prose in "reason" is what breaks the JSON, usually an unescaped
        # quote copied from a headline. The index is the actual answer, so it
        # is worth recovering on its own.
        match = _INDEX_RE.search(raw)
        if match is None:
            raise
        index = int(match.group(1))
        reason = "(JSON mal formado, se recupero solo el indice)"
        logger.warning("pick_best_story: JSON invalido, indice %s recuperado del texto", index)

    if not 0 <= index < len(candidates):
        raise ValueError(f"indice {index} fuera de rango (hay {len(candidates)} candidatas)")

    logger.info(
        "pick_best_story: elegida %r de %s candidatas. Motivo: %s",
        candidates[index]["title"],
        len(candidates),
        reason,
    )
    return candidates[index]
