import json

import anthropic

from .config import ANTHROPIC_API_KEY, CLAUDE_MODEL, NEWS_LANGUAGE_HINT

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

PROMPT_TEMPLATE = """Eres el guionista y analista de un canal de YouTube de noticias en {language}.
Tu trabajo NO es resumir el titular. YouTube penaliza (y puede desmonetizar) los canales que
solo leen una noticia con otras palabras sin aportar nada propio ("reused/repetitious content").
Cada guion debe leerse como una pieza de analisis periodistico con voz editorial propia, no como
una lectura plana de la fuente.

Noticia de partida (usala solo como disparador de hechos, NO la copies ni parafrasees frase a
frase):
Titular: {title}
Resumen: {summary}

Estructura obligatoria del guion (60-90 segundos, en este orden):
1. Gancho: una frase que enganche, con una pregunta o dato llamativo relacionado (no el titular tal cual).
2. Contexto: que ha pasado antes, quien esta implicado, por que existe esta noticia ahora.
3. El hecho: los datos concretos de la noticia, explicados con tus propias palabras.
4. Analisis: por que importa esto, que consecuencias tiene, como conecta con otras tendencias o
   noticias del sector. Esta es la parte que aporta valor real y diferencia el canal de un simple
   agregador.
5. Cierre: una reflexion o pregunta abierta al espectador, y llamada a suscribirse.

Devuelve EXCLUSIVAMENTE un JSON con esta forma exacta, sin texto adicional ni markdown:
{{
  "title": "titulo llamativo para YouTube, menos de 90 caracteres, no calcado del titular original",
  "description": "descripcion de 2-3 frases para YouTube con contexto y llamada a suscribirse",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "scenes": [
    {{"narration": "texto que se narrara en esta escena", "visual_keywords": "palabras clave en ingles para buscar video de stock"}}
  ]
}}

Genera entre 6 y 9 escenas siguiendo la estructura de arriba (gancho, contexto, hecho, analisis,
cierre - el hecho y el analisis pueden ocupar varias escenas). Cada narracion debe ser una o dos
frases cortas, faciles de narrar en voz alta. No inventes datos que no esten en la noticia
original: puedes analizar y contextualizar, pero los hechos deben ser reales.
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
    text_blocks = [block.text for block in message.content if block.type == "text"]
    if not text_blocks:
        raise ValueError("Claude no devolvio ningun bloque de texto en la respuesta")
    raw_text = _strip_markdown_fence(text_blocks[0])
    script = json.loads(raw_text)

    required_keys = {"title", "description", "tags", "scenes"}
    if not required_keys.issubset(script):
        raise ValueError(f"Respuesta de Claude incompleta, faltan claves: {required_keys - script.keys()}")

    return script
