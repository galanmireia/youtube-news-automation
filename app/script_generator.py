import json

import anthropic

from .config import ANTHROPIC_API_KEY, CHANNEL_NAME, CHANNEL_TONE_HINT, CLAUDE_MODEL, NEWS_LANGUAGE_HINT

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

PROMPT_TEMPLATE = """Eres el guionista y analista del canal de YouTube "{channel_name}" en {language}.

REGLA PRINCIPAL, por encima de todo lo demas: el video SIEMPRE tiene que poder monetizarse en
YouTube. Esto significa: nunca "reused/repetitious content" (resumir el titular con otras
palabras sin aportar nada propio), nunca sensacionalismo en temas sensibles (ver aviso mas abajo),
y nunca contenido que viole derechos de autor.

Cada guion debe leerse como una pieza de analisis periodistico con voz editorial propia, no como
una lectura plana de la fuente.

Identidad del canal: {tone_hint}

AVISO DE SENSIBILIDAD (evalua esto ANTES de escribir): si la noticia trata sobre una muerte,
un crimen violento, una victima identificable, una tragedia o una desgracia personal real,
YouTube puede desmonetizar el video si el tono es sensacionalista o "intrigante". En ese caso,
DEJA DE LADO el angulo de "lado oculto" del canal y escribe en su lugar como un medio de noticias
serio: tono neutral, respetuoso con las victimas y sus familias, sin especular sobre la
investigacion mas alla de lo confirmado, sin dramatizar ni usar ganchos tipo clickbait. El
"analisis" en estos casos debe centrarse en contexto social o estadistico legitimo (por ejemplo,
cifras del fenomeno, respuesta institucional, precedentes similares), nunca en morbo sobre la
victima concreta. Si la noticia NO es sensible (politica, tecnologia, economia, cultura, etc.),
aplica con normalidad el tono intrigante del canal descrito arriba.

Noticia de partida (usala solo como disparador de hechos, NO la copies ni parafrasees frase a
frase):
Titular: {title}
Resumen: {summary}

Formato de este video: {format_hint}

Estructura obligatoria del guion ({duration_hint}, en este orden):
1. Gancho: una frase que enganche (intrigante si la noticia lo permite, sobria si es sensible), con una pregunta o dato relacionado (no el titular tal cual).
2. Contexto: que ha pasado antes, quien esta implicado, por que existe esta noticia ahora.
3. El hecho: los datos concretos de la noticia, explicados con tus propias palabras.
4. Analisis: en noticias normales, la parte de la historia que no suele contarse a simple vista,
   las consecuencias reales o las preguntas que deja abiertas. En noticias sensibles, contexto
   social o estadistico legitimo, tratado con seriedad. Esta es la parte que aporta valor real y
   diferencia el canal de un simple agregador de titulares.
5. Cierre: una reflexion o pregunta abierta al espectador, y llamada a suscribirse (en noticias
   sensibles, sobria y sin banalizar).

Recuerda: SIEMPRE anclado en los hechos de la noticia original. Nunca inventes conspiraciones ni
afirmes cosas que no esten respaldadas por la fuente.

Fotos reales de personas publicas: para cada escena, si esa narracion concreta habla directamente
de una persona publica real identificable por su cargo o su nombre (un ministro, un politico, un
CEO, un famoso), rellena "photo_subject" con su nombre completo tal cual aparece en Wikipedia, para
mostrar su foto real en vez de video generico. Deja "photo_subject" vacio ("") en el resto de
escenas, y SIEMPRE vacio si la persona es una victima de un crimen/tragedia o un particular sin
relevancia publica (evita mostrar la foto real de victimas o personas privadas).

Ilustracion por IA para lugares/conceptos muy especificos: si la escena trata sobre un lugar,
evento o concepto tan especifico o local que un banco de video de stock generico NUNCA tendria
metraje real de eso (ej. una ciudad pequeña o poco fotografiada, una frontera concreta, un edificio
o instalacion muy especifica, un concepto muy abstracto de la noticia), rellena "ai_image_prompt"
con una descripcion visual detallada en ingles para generar una ilustracion (no un intento de foto
realista de personas reales - para eso esta "photo_subject"). Ejemplo: para una noticia sobre Ceuta,
"ai_image_prompt": "editorial illustration of a border fence between a north african coastal city
and mainland, dramatic lighting, news graphic style". Deja "ai_image_prompt" vacio ("") si el tema
es generico y un banco de stock normal puede representarlo bien.

Palabras clave visuales ("visual_keywords", solo se usan cuando "photo_subject" Y "ai_image_prompt"
estan vacios): tienen que representar visualmente LO QUE SE DICE EN ESA FRASE CONCRETA, no un tema
generico de todo el video. Antes de escribirlas, identifica la accion, objeto o entorno mas
concreto que menciona ESA narracion en particular, y descríbelo en ingles, 2-5 palabras, de forma
que exista de verdad en un banco de video de stock (Pexels). Ejemplos: si la narracion dice "el
banco central subio los tipos de interes", mejor "central bank building exterior" que algo vago
como "finance concept"; si dice "cientos de personas protestaron en la calle", mejor "crowd protest
street march" que "social unrest". Evita conceptos abstractos que no se pueden filmar (mal:
"government pressure", "economic uncertainty", "political tension"). No incluyas nombres propios de
personas, empresas o lugares muy especificos (para eso esta "ai_image_prompt") - en su lugar
describe el TIPO de escena/objeto/entorno, pero con la maxima especificidad posible dentro de eso
(mejor "tech startup office workspace" que "office"; mejor "riot police street clash" que "police").
MUY IMPORTANTE - variedad: dos escenas del mismo guion NUNCA deben llevar las mismas palabras clave
o describir la misma imagen generica, aunque el tema de fondo sea el mismo (ej. no repitas "press
conference" en varias escenas de una noticia politica) - cada escena debe aportar una imagen
distinta, o el video se siente repetitivo y aburrido.

Requisitos de SEO para YouTube (importante, esto determina si el video se encuentra en buscador y
sugeridos):
- "title": incluye la palabra clave principal (el tema/entidad de la noticia) cerca del inicio,
  manera natural y sin relleno de palabras clave. Maximo 90 caracteres, no calcado del titular
  original, con gancho pero sin exagerar (nada de MAYUSCULAS sostenidas ni "no vas a creer...").
- "description": empieza con 1-2 frases que repitan de forma natural la palabra clave principal
  del titulo (esto es lo que se muestra en resultados de busqueda), sigue con 2-3 frases de
  contexto, y termina con 3 a 5 hashtags relevantes (formato #Palabra, sin espacios) mas una
  llamada a suscribirse a {channel_name}.
- "tags": genera entre 10 y 15 palabras clave/frases de busqueda reales que la gente usaria en
  YouTube sobre este tema, mezclando: 2-3 amplias (el tema general, ej. "inteligencia artificial"),
  4-6 especificas (nombres, lugares, entidades concretas de la noticia), y 3-5 relacionadas con el
  tipo de contenido (ej. "noticias de actualidad", "analisis noticias españa"). Sin duplicados,
  sin almohadillas aqui (van solo en la descripcion).
{shorts_seo_hint}

Devuelve EXCLUSIVAMENTE un JSON con esta forma exacta, sin texto adicional ni markdown:
{{
  "title": "titulo optimizado para SEO, ver requisitos arriba",
  "description": "descripcion con hashtags, ver requisitos arriba",
  "tags": ["tag1", "tag2", "... entre 10 y 15 tags"],
  "scenes": [
    {{
      "narration": "texto que se narrara en esta escena",
      "visual_keywords": "palabras clave en ingles para buscar video de stock",
      "photo_subject": "nombre completo de una persona publica real si aplica, si no, cadena vacia",
      "ai_image_prompt": "descripcion en ingles para ilustracion por IA si aplica, si no, cadena vacia"
    }}
  ]
}}

Genera {scene_count_hint} siguiendo la estructura de arriba (gancho, contexto, hecho, analisis,
cierre - el hecho y el analisis pueden ocupar varias escenas). {scene_length_hint} No inventes
datos que no esten en la noticia original: puedes analizar y contextualizar, pero los hechos deben
ser reales.
"""

_VARIANT_CONFIG = {
    "short": {
        "format_hint": (
            "YouTube Short vertical (9:16). Debe ser autoconclusivo, directo al grano, pensado "
            "para verse en el feed de Shorts sin contexto previo."
        ),
        "duration_hint": "45-60 segundos",
        "scene_count_hint": "entre 5 y 7 escenas",
        "scene_length_hint": "Cada narracion debe ser una frase corta y directa, ritmo rapido.",
        "shorts_seo_hint": (
            '- Incluye "#Shorts" como uno de los hashtags al final de la descripcion (obligatorio '
            "para que YouTube lo clasifique bien como Short)."
        ),
    },
    "long": {
        "format_hint": "Video horizontal (16:9) extendido para YouTube, no es un Short.",
        "duration_hint": "3 a 5 minutos",
        "scene_count_hint": "entre 16 y 24 escenas",
        "scene_length_hint": (
            "Cada narracion puede tener hasta 2-3 frases; profundiza mas que en un Short: añade "
            "ejemplos concretos, cifras adicionales, comparaciones, cronologia mas detallada y "
            "matices en el analisis."
        ),
        "shorts_seo_hint": "",
    },
}


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
    return text.strip()


_MAX_TOKENS = {"short": 4000, "long": 10000}
_MAX_ATTEMPTS = 3


def generate_script(news_item: dict, variant: str = "long") -> dict:
    if variant not in _VARIANT_CONFIG:
        raise ValueError(f"variant desconocida: {variant!r}")
    variant_config = _VARIANT_CONFIG[variant]

    prompt = PROMPT_TEMPLATE.format(
        channel_name=CHANNEL_NAME,
        tone_hint=CHANNEL_TONE_HINT,
        language=NEWS_LANGUAGE_HINT,
        title=news_item["title"],
        summary=news_item["summary"],
        **variant_config,
    )

    last_error: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        message = _client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=_MAX_TOKENS[variant],
            messages=[{"role": "user", "content": prompt}],
        )
        text_blocks = [block.text for block in message.content if block.type == "text"]
        if not text_blocks:
            last_error = ValueError("Claude no devolvio ningun bloque de texto en la respuesta")
            continue

        raw_text = _strip_markdown_fence(text_blocks[0])
        try:
            script = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            # The response occasionally gets cut off mid-JSON (long thinking
            # + long output competing for the same token budget). Retrying
            # is cheap and usually succeeds on the next try.
            last_error = exc
            continue

        required_keys = {"title", "description", "tags", "scenes"}
        if not required_keys.issubset(script):
            last_error = ValueError(f"Respuesta de Claude incompleta, faltan claves: {required_keys - script.keys()}")
            continue

        return script

    raise RuntimeError(f"generate_script fallo tras {_MAX_ATTEMPTS} intentos: {last_error}") from last_error
