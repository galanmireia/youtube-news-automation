import json

import anthropic

from .config import ANTHROPIC_API_KEY, CLAUDE_MODEL, NEWS_LANGUAGE_HINT

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

PROMPT_TEMPLATE = """Eres guionista de un canal de YouTube de noticias en {language}.
A partir de esta noticia, genera un guion para un video corto (60-90 segundos).

Titular: {title}
Resumen: {summary}

Devuelve EXCLUSIVAMENTE un JSON con esta forma exacta, sin texto adicional ni markdown:
{{
  "title": "titulo llamativo para YouTube, menos de 90 caracteres",
  "description": "descripcion de 2-3 frases para YouTube, incluye contexto y una llamada a suscribirse",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "scenes": [
    {{"narration": "texto que se narrara en esta escena", "visual_keywords": "palabras clave en ingles para buscar video de stock"}}
  ]
}}

Genera entre 5 y 8 escenas. Cada narracion debe ser una o dos frases cortas, faciles de narrar en voz alta.
No inventes datos que no esten en la noticia original.
"""


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
    return text.strip()


def generate_script(news_item: dict) -> dict:
    message = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": PROMPT_TEMPLATE.format(
                    language=NEWS_LANGUAGE_HINT,
                    title=news_item["title"],
                    summary=news_item["summary"],
                ),
            }
        ],
    )
    raw_text = _strip_markdown_fence(message.content[0].text)
    script = json.loads(raw_text)

    required_keys = {"title", "description", "tags", "scenes"}
    if not required_keys.issubset(script):
        raise ValueError(f"Respuesta de Claude incompleta, faltan claves: {required_keys - script.keys()}")

    return script
