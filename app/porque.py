"""/why: LOS VIDEOS DEL CANAL EN INGLES ("Why Though").

El porque de las cosas cotidianas - "Why Can't You Tickle Yourself?" -,
contado en ingles, en videos horizontales de MINIMO DIEZ MINUTOS ("tienen
que ser minimo de 10 mins"), dibujados a rotulador en un folio en blanco
(app/garabato.py) y con la voz de Google en ingles.

Mismo camino que /largo, en dos pasos: /why escribe el guion (centimos) y
dice que dibujos pide que no existen; /montar hace la voz y el video. Lo que
cambia: el idioma, el estilo de dibujo, el ritmo (planos de 5-9 segundos,
como los canales de este tipo) y que los capitulos acaban en la descripcion
con su minuto, que es lo que hace que YouTube los muestre.
"""
import json
import re
import logging
import math
import shutil
import time
from pathlib import Path

from . import garabato, llm_usage, mascota, monigotes
from .config import CHANNEL_NAME, DATA_DIR, MUSIC_VOLUME
from .largo import (FPS, LargoError, _FPS_DIBUJO, _ffmpeg, _json_de, _pregunta, _tuberia,
                    _voz_google)

logger = logging.getLogger(__name__)

ANCHO, ALTO = 1920, 1080
# Diez minutos MINIMO. La voz de Google en ingles lee unas 150 palabras por
# minuto; con las pausas, 1.750 palabras dan once minutos y pico, y asi un
# video que la voz lea deprisa no se queda en 9:50.
_PALABRAS = 1750
_MINIMO_SEGUNDOS = 10*60
_PALABRAS_PLANO = (10, 22)
_PAUSA_PLANO = 0.25
# Lo que se le ofrece al guion: lo de monigotes que pega en este canal y lo
# que solo existe aqui (manos en la cabeza, tumbado, muerto, calor, frio).
_POSES = tuple(monigotes.POSES_VALIDAS) + garabato.POSES_EXTRA
_ACCIONES = "; ".join(f'"{k}" = {v[1]}' for k, v in mascota.ACCIONES.items())
_GESTOS = tuple(monigotes.GESTOS_VALIDOS) + garabato.GESTOS_EXTRA
_EFECTOS = ("sorpresa", "idea", "mareo", "confuso", "zzz", "enamorado", "sudor", "lagrimas", "humo",
            "caida", "salto", "temblor") + garabato.EFECTOS_EXTRA
_PAUSA_CAPITULO = 0.8
_PENDIENTE = Path(DATA_DIR) / "porque_pendiente.json"
# El ultimo guion ya montado: /remontar lo vuelve a montar sin pagar otro
# guion (si cambia el estilo, o algo sale mal en el video).
_ULTIMO = Path(DATA_DIR) / "porque_ultimo.json"


def _lista(nombres) -> str:
    return "[" + ", ".join(nombres) + "]"


_INSTRUCCIONES = """You write scripts for "{canal}", an English-language YouTube channel that explains
the WHY behind everyday things ("Why Can't You Tickle Yourself?", "Why Onions Make You Cry"),
drawn as simple marker doodles: stick figures on a white page, big hand-lettered words, bold
colors. Long-form videos (11-12 minutes), narrated by one calm, friendly, curious voice.

THE STORY. Open with a hook in the first 15 seconds (a surprising fact, a question, a tiny
scene everyone recognises). Then explain step by step, as if to a smart friend: simple
words, concrete examples, one idea at a time, little "wait, but why?" turns that keep people
watching. A bit of gentle humor is welcome. End with a short payoff and a question for the
comments. FACTS MUST BE TRUE: use the DOSSIER below; when science is unsure, say so. No
medical advice beyond common sense; nothing graphic. Plain, natural spoken English: the
narration is read aloud by a speech synthesizer, so write numbers the way they are said when
it matters ("ninety-five degrees"), and no symbols it can't read.

THE DRAWINGS. Every shot ("plano") has a "visual", drawn by a program from closed lists - if
it is not in the lists, it cannot be drawn. A visual has any of:
  "mascota": THE CHANNEL'S MASCOT, the star of every video: MOKORDO, a round purple drop with a
             "?" for hair. It is always moving. {{"accion": one of {acciones}, "x": 0.15-0.85,
             "espejo": true to face left, "gesto": a face from the list to override the action's,
             "efecto": optional}}. Put it in MOST shots, doing what the sentence says (it is the
             viewer's buddy living the story): it enters hopping at the start of a section, thinks,
             points at the thing being explained, jumps when there is an idea, gets scared,
             laughs... Leave it out only for giant numbers or pure diagrams. The stick people
             ("figuras") are the other characters of the story. Now and then (a few
             times per video, not every sentence) the narration can name him, as the
             viewer's buddy: "Mokordo tries to tickle himself...", "even Mokordo knows that".
  "figuras": 0-3 stick people: {{"quien": one of {quienes} ("persona" = adult, "persona_b" =
             adult with a bun, "nino" = kid, "abuelo" = old bearded man / scientist), "x": 0.12-0.88, "pose": one of {poses},
             "pose_fin": another pose ONLY if they do something (raise their arms, put their hands
             on their head): they do it once and stay - otherwise omit it,
             "gesto": one of {gestos}, "efecto": one of {efectos} or omit,
             "lleva": what they hold: any object of the "cosas" list (a feather, a phone...)
             or one of {llevables}, or omit; "espejo": true to face left}}
  "cosas":   0-5 objects: {{"que": one of {objetos}, "cuando": "two fans", "x": 0.05-0.95, "tam": 0.06-0.55 (height,
             fraction of the screen), "y": 0.1-0.9 = its CENTER if it floats (omit "y" and it
             stands at the bottom, level with the people's feet), "etiqueta": "CAMEL" = a small
             handwritten label under it, "tachado": true = crossed out with a big red X ("NOT this",
             a myth busted)}}
  "textos":  0-2 BIG hand-lettered words: {{"texto": "IT'S HOT" (max 3-4 words, CAPITALS), "cuando": ...,
             "x", "y", "tam": 0.08-0.2, "color": one of {colores}, "giro": -8 to 8 degrees}}
  "flechas": 0-2 hand-drawn arrows: {{"de": [x, y], "a": [x, y], "cuando": ..., "color": ..., "recta": true for a
             big straight arrow (pointing at something, "goes up", "goes down")}}
  "cifra":   a GIANT number with rays, alone on the page: {{"valor": "35°C", "pie": "short
             caption", "color": ...}} (use it for the key numbers; then no figuras/cosas)
  "ambiente": where the drawing happens, doodled lightly around it so the page is not bare:
             one of {ambientes} (a horse -> "campo": grass and sun; a camel -> "desierto"; a
             person in bed -> "casa"). Give one to every fresh drawing; "nada" only for words,
             numbers and diagrams.
  "sigue":   true = KEEP the previous shot's drawing and ADD this shot's new things to it
             (only the new ones appear). Build a drawing up step by step, the way Whymentary does:
             the fan... then the person sweating next to it... then the thermometer going up.
             Use it a lot: 2-4 shots in a row building one drawing, then a fresh page.
"cuando" = the exact words of THIS shot's narration at which that thing pops in. THINGS APPEAR
WHEN THE VOICE NAMES THEM: "with one fan it's hot... but with TWO fans" - the second fan pops in
on "two fans". Give every object, word and arrow its "cuando", in the order they are said, so the
page fills up while the sentence goes (start the shot with little on it).
Special: pose "manos_cabeza" = hands on the head (panic, stress); pose "tumbado" = lying on the
floor; gesto "muerto" = X eyes and tongue out (comic fainted/dead); efecto "calor" / "frio" =
heat waves / cold shivers all around the person.
THE STYLE is Whymentary's: a white page, clean simple drawings, big red handwritten words.
NEVER EMPTY: simple drawings, but every shot shows 2-4 things that SHOW what the sentence says.
If the narration names something you can draw - an animal, an object, a body part, a food - it
MUST be on the page (a camel is a "camello", not a person alone). Label things that could be
confused ("etiqueta"). A person alone on the page only for a pure reaction beat, and never two
shots in a row. If something has no drawing, use the closest one plus an "etiqueta".
ONE IDEA PER SHOT, big and in the middle. Mix: people reacting, objects explained, "THIS =
THAT" equations (cosa + "igual" + cosa), giant numbers, a big word. Keep text and objects from
overlapping the people. The same person keeps the same "quien" all video long.

===== DOSSIER =====
{dosier}
"""

_PIDE_INDICE = """Topic: «{tema}». The video must run AT LEAST 10 minutes: about {palabras} words
of narration in total.

Return ONLY this JSON:
{{
  "titulo": "YouTube title, curiosity-driven, max 60 characters, no clickbait lies (e.g. Why a Fan Can Kill You)",
  "descripcion": "YouTube description: 2-3 short paragraphs that tease the video without spoiling the answer, then: 🔔 Subscribe to {canal} for the why behind everyday things.",
  "tags": ["15-20 tags"],
  "miniatura": {{"cosas": [...], "textos": [...]}},
  "capitulos": [{{"titulo": "short chapter title", "resumen": "what it explains, with the key facts", "palabras": 250}}]
}}
"miniatura": the thumbnail, drawn in the same visual format: dead simple and readable on a
phone - two objects and an "igual" sign, or one object and 1-3 big words.
Chapters: 5 to 8; the first one is the HOOK (short); together about {palabras} words."""

_PIDE_CAPITULO = """THE VIDEO (already decided):
{indice}

Write chapter {n}: «{titulo}» - {resumen}
AT LEAST {palabras} words of narration - that is about {n_planos} SHOTS of {pmin}-{pmax} words each
(one sentence, 5-9 seconds). The video must last 10 minutes or more, so do NOT cut it short:
go deeper - examples, studies, analogies, a little scene. The drawing changes with every shot:
a fresh drawing, or "sigue" adding something new to the one on screen - never the same twice.
{anterior}
Return ONLY this JSON:
{{"planos": [{{"narracion": "...", "visual": {{...}}, "falta": ""}}]}}

"falta": ONLY if this shot needs something that is not in the lists (an object, a pose),
name it in a few words ("a toothbrush", "a mosquito"); it will be drawn before the video is
made - meanwhile use the closest thing that exists. Otherwise "".
{cierre}"""


def _dosier(tema: str) -> str:
    from . import research
    try:
        hallados = research.buscar("en", tema, 1)
        return research.build_dossier(hallados[0], lang="en")[:50000] if hallados else ""
    except Exception:
        logger.warning("why: sin dosier para %r", tema, exc_info=True)
        return ""


def escribe_guion(tema: str, parar=None) -> dict:
    sistema = _sistema(tema)
    plan = _pregunta(sistema, _PIDE_INDICE.format(tema=tema, palabras=_PALABRAS, canal=CHANNEL_NAME),
                     "why-indice", 8000)
    capitulos = [c for c in plan.get("capitulos") or [] if isinstance(c, dict)]
    if not capitulos:
        raise LargoError("el indice no trae capitulos")
    indice = "\n".join(f"{i + 1}. {c.get('titulo')}: {c.get('resumen')}" for i, c in enumerate(capitulos))
    # Lo que se pide a cada capitulo, escalado para que entre todos sumen las
    # palabras de diez minutos aunque el indice se quede corto.
    pedidas = [max(80, int(c.get("palabras") or 0)) for c in capitulos]
    escala = _PALABRAS/max(1, sum(pedidas))
    pedidas = [round(p*max(1.0, escala)) for p in pedidas]
    hechos = []
    for i, c in enumerate(capitulos):
        if parar is not None and parar():
            from .pipeline import GenerationStopped
            raise GenerationStopped("parada pedida mientras se escribia el guion en ingles")
        anterior = ""
        if hechos:
            ultimo = " ".join(p.get("narracion", "") for p in hechos[-1]["planos"][-2:])
            anterior = f"\nThe previous chapter ended like this (carry on, don't repeat): «{ultimo[-500:]}»\n"
        cierre = ("\nThis is the LAST chapter: end with the payoff and one question for the comments."
                  if i == len(capitulos) - 1 else "")
        cap = _pregunta(sistema, _PIDE_CAPITULO.format(
            indice=indice, n=i + 1, titulo=c.get("titulo", ""), resumen=c.get("resumen", ""),
            palabras=pedidas[i], n_planos=max(4, round(pedidas[i]/16)), pmin=_PALABRAS_PLANO[0],
            pmax=_PALABRAS_PLANO[1], anterior=anterior, cierre=cierre), f"why-capitulo-{i + 1}")
        planos = [p for p in cap.get("planos") or []
                  if isinstance(p, dict) and str(p.get("narracion", "")).strip()]
        if not planos:
            raise LargoError(f"el capitulo {i + 1} ha salido vacio")
        hechos.append({"titulo": c.get("titulo", ""), "planos": planos, "_pedidas": pedidas[i],
                       "resumen": c.get("resumen", "")})
    plan["capitulos"] = hechos
    alarga(plan, sistema, indice)
    return plan


def _palabras(planos) -> int:
    return sum(len(str(p.get("narracion", "")).split()) for p in planos)


_PIDE_MAS = """THE VIDEO (already decided):
{indice}

Chapter {n} «{titulo}» came out SHORT: {tiene} words, and it needs {pide}. The video has to last
at least 10 minutes. Here is how it currently ends: «{final}»

Write its CONTINUATION: about {faltan} more words in about {n_planos} new shots ({pmin}-{pmax}
words each), that go deeper - a study, an example, an analogy, a tiny scene - WITHOUT repeating
what is already said, and flowing on from that ending. Same format:
{{"planos": [{{"narracion": "...", "visual": {{...}}, "falta": ""}}]}}"""


def alarga(guion: dict, sistema: str, indice: str) -> list[str]:
    """DIEZ MINUTOS O MAS. El primero ("Why can't you tickle yourself") salio
    de 1.031 palabras, 6,9 minutos, porque cada capitulo se quedo corto. Cada
    capitulo que no llega al 85% de lo que se le pidio se alarga una vez con
    planos nuevos al final."""
    hecho = []
    for n, cap in enumerate(guion.get("capitulos") or [], start=1):
        pide = int(cap.get("_pedidas") or _PALABRAS/max(1, len(guion["capitulos"])))
        tiene = _palabras(cap["planos"])
        if tiene >= pide*0.85:
            continue
        faltan = pide - tiene
        final = " ".join(p.get("narracion", "") for p in cap["planos"][-2:])[-400:]
        mas = _pregunta(sistema, _PIDE_MAS.format(
            indice=indice, n=n, titulo=cap.get("titulo", ""), tiene=tiene, pide=pide, final=final,
            faltan=faltan, n_planos=max(2, round(faltan/16)), pmin=_PALABRAS_PLANO[0],
            pmax=_PALABRAS_PLANO[1]), f"why-alarga-{n}")
        nuevos = [p for p in mas.get("planos") or []
                  if isinstance(p, dict) and str(p.get("narracion", "")).strip()]
        cap["planos"] += nuevos
        hecho.append(f"cap. {n}: {tiene} -> {_palabras(cap['planos'])} palabras")
    if hecho:
        logger.info("why: capitulos alargados: %s", "; ".join(hecho))
    return hecho


def _sistema(tema: str) -> str:
    dosier = _dosier(tema)
    return _INSTRUCCIONES.format(
        canal=CHANNEL_NAME, acciones=_ACCIONES, quienes=_lista(garabato.QUIENES), poses=_lista(_POSES),
        gestos=_lista(_GESTOS), efectos=_lista(_EFECTOS),
        llevables=_lista(monigotes.LLEVABLES_EXPLICADOS), objetos=_lista(garabato.OBJETOS_VALIDOS),
        colores=_lista(garabato.COLORES), ambientes=_lista(garabato.garabato_ambiente.AMBIENTES),
        dosier=dosier or "(no dossier: use only facts you are sure of)")


def run_alarga() -> str:
    """/alargar: alarga el guion que esta esperando, sin reescribirlo."""
    guion = json.loads(_PENDIENTE.read_text())
    indice = "\n".join(f"{i + 1}. {c.get('titulo')}: {c.get('resumen', '')}"
                        for i, c in enumerate(guion["capitulos"]))
    total = sum(_palabras(c["planos"]) for c in guion["capitulos"])
    if total < _PALABRAS*0.95:
        # El guion viejo no traia lo que se pidio por capitulo: se reparte.
        for c in guion["capitulos"]:
            c["_pedidas"] = max(int(c.get("_pedidas") or 0),
                                round(_PALABRAS*_palabras(c["planos"])/max(1, total)))
    alarga(guion, _sistema(guion.get("_tema", "")), indice)
    _PENDIENTE.write_text(json.dumps(guion, ensure_ascii=False, indent=1))
    texto, _ = revisa(guion)
    coste = llm_usage.report_and_reset()
    if coste:
        logger.info("[why] %s", coste)
    return texto


def revisa(guion: dict) -> tuple[str, list[str]]:
    """Que pide el guion, y que pide que NO esta dibujado."""
    from collections import Counter
    # Lo que garabato traduce solo tambien vale: "gesto confuso", "pose
    # asustado", "lleva pluma".
    validos = {"que": set(garabato.OBJETOS_VALIDOS),
               "pose": set(_POSES) | set(garabato._POSE_ES_GESTO),
               "gesto": set(_GESTOS) | set(garabato._GESTO_ES_EFECTO),
               "efecto": set(monigotes.EFECTOS_VALIDOS) | set(_EFECTOS),
               "lleva": set(monigotes.LLEVABLES_EXPLICADOS) | set(garabato.OBJETOS_VALIDOS),
               "quien": set(garabato.QUIENES)}
    faltan, pedidos, usados = Counter(), [], Counter()
    planos = 0
    palabras = 0
    for n, cap in enumerate(guion.get("capitulos") or [], start=1):
        for k, p in enumerate(cap.get("planos") or [], start=1):
            planos += 1
            palabras += len(str(p.get("narracion", "")).split())
            if p.get("falta"):
                pedidos.append(f"cap. {n}, plano {k}: {p['falta']}")
            v = p.get("visual") or {}
            for c in v.get("cosas") or []:
                que = garabato.nombre_objeto((c or {}).get("que"))
                if que:
                    (usados if que in validos["que"] else faltan)[que if que in validos["que"] else f"objeto {que}"] += 1
            for f in v.get("figuras") or []:
                for campo in ("quien", "pose", "pose_fin", "gesto", "efecto", "lleva"):
                    val = str((f or {}).get(campo) or "").lower()
                    if campo == "lleva":
                        val = garabato.nombre_objeto(val)
                    clave = "pose" if campo == "pose_fin" else campo
                    if val and val not in validos[clave]:
                        faltan[f"{clave} {val}"] += 1
    lineas = [f"«{guion.get('titulo')}»", ""]
    for n, cap in enumerate(guion.get("capitulos") or [], start=1):
        lineas.append(f"{n}. {cap.get('titulo')} ({len(cap.get('planos') or [])} planos)")
    minutos = palabras/150
    lineas += ["", f"{planos} planos, {palabras} palabras (unos {minutos:.1f} minutos)",
               "Objetos: " + ", ".join(f"{u} {c}" for u, c in usados.most_common(15))]
    if minutos < 10.3:
        lineas.append(f"⚠️ Puede quedarse corto: {minutos:.1f} minutos calculados (minimo 10).")
    lista = [f"{x} (x{c})" for x, c in faltan.most_common()] + pedidos
    lineas += ["", "⚠️ PIDE COSAS QUE NO ESTAN DIBUJADAS:"] + [f"- {x}" for x in lista] if lista \
        else ["", "✅ Todo lo que pide esta dibujado."]
    return "\n".join(lineas), lista


def run_guion(tema: str) -> str:
    """PASO 1 de /why: el guion, guardado, y lo que pide dibujar."""
    from .pipeline import _stop_requested
    _stop_requested.clear()
    logger.info("[why] Escribiendo el guion de %r...", tema)
    guion = escribe_guion(tema, parar=_stop_requested.is_set)
    guion["_tema"] = tema
    _PENDIENTE.write_text(json.dumps(guion, ensure_ascii=False, indent=1))
    texto, _ = revisa(guion)
    logger.info("[why] Guion guardado. %s", texto.replace("\n", " | "))
    for i, cap in enumerate(guion["capitulos"], start=1):
        for k, p in enumerate(cap["planos"], start=1):
            logger.info("[why] %s.%s %s", i, k, json.dumps(p.get("visual"), ensure_ascii=False)[:400])
    coste = llm_usage.report_and_reset()
    if coste:
        logger.info("[why] %s", coste)
    return texto


def hay_pendiente() -> bool:
    return _PENDIENTE.exists()


def recupera_ultimo() -> str | None:
    """/remontar: el ultimo guion montado vuelve a quedar esperando. Devuelve
    su titulo, o None si no hay ninguno."""
    if not _ULTIMO.exists():
        return None
    guion = json.loads(_ULTIMO.read_text())
    _PENDIENTE.write_text(json.dumps(guion, ensure_ascii=False, indent=1))
    return str(guion.get("titulo") or guion.get("_tema") or "")


_CARETA = 2.8     # segundos que se ve el titulo
# Ninguna escena se queda mas de esto en pantalla, la haya escrito Claude
# larga o no ("¿esta garantizado que haya una escena cada 10 segundos?"):
# la que se pasa se parte en trozos y cada trozo es otro dibujo.
_MAX_PLANO = 10.0
_FPS_MASCOTA = 25  # la mascota se pinta a 25: se mueve mucho
_DESLIZA = 0.28    # lo que tarda cada plano en entrar de lado, con su "whoosh"
_POSES_DE_RELEVO = ("señala", "brazos_arriba", "mirando", "de_pie")


# LA VOZ GUARDADA: cada frase narrada se guarda por su texto, y al remontar
# (o si se repite una frase) no se vuelve a pagar a Google ("si uso el mismo
# guion, ¿cuanto cuesta?": solo la revision, unos centimos).
_VOCES = Path(DATA_DIR) / "voces_why"
_VOCES_MAX_MB = 400


def _voz_guardada(texto: str, destino: Path):
    import hashlib
    from pydub import AudioSegment
    from .config import TTS_LANGUAGE_CODE, TTS_VOICE_NAME
    clave = hashlib.sha1(f"{TTS_LANGUAGE_CODE}|{TTS_VOICE_NAME}|{texto}".encode("utf-8")).hexdigest()
    guardada = _VOCES / f"{clave}.wav"
    if guardada.exists():
        try:
            audio = AudioSegment.from_wav(guardada)
            guardada.touch()
            return audio
        except Exception:
            logger.warning("why: voz guardada ilegible; se vuelve a pedir.", exc_info=True)
    audio = _voz_google(texto, destino, ritmo_pedido=None)
    try:
        _VOCES.mkdir(parents=True, exist_ok=True)
        audio.export(guardada, format="wav")
    except Exception:
        logger.warning("why: no se ha podido guardar la voz.", exc_info=True)
    return audio


def _poda_voces() -> None:
    """Que las voces guardadas no llenen el disco: fuera las mas viejas."""
    try:
        ficheros = sorted(_VOCES.glob("*.wav"), key=lambda f: f.stat().st_mtime)
        total = sum(f.stat().st_size for f in ficheros)
        while ficheros and total > _VOCES_MAX_MB*1024*1024:
            f = ficheros.pop(0)
            total -= f.stat().st_size
            f.unlink(missing_ok=True)
    except Exception:
        logger.warning("why: no se han podido podar las voces guardadas.", exc_info=True)


def _normal(texto: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9']+", " ", str(texto).lower()).split())


def _al_nombrarlo(visual: dict, texto: str, hablado: float) -> dict:
    """"cuando": cada cosa sale en el segundo en que la voz la nombra ("y
    cuando pongo DOS ventiladores..." - ¡pa!, el segundo ventilador). La voz
    de Google lee a ritmo parejo, asi que el sitio de esas palabras en la
    frase dice cuando suenan."""
    frase = _normal(texto)
    if not frase or not hablado:
        return visual
    v = dict(visual)
    for campo in ("cosas", "textos", "flechas"):
        salida = []
        for x in visual.get(campo) or []:
            if isinstance(x, dict) and x.get("cuando") and not x.get("_ya"):
                aguja = _normal(x["cuando"])
                k = frase.find(aguja) if aguja else -1
                if k < 0 and aguja:
                    # Si no esta tal cual, la palabra mas larga de las pedidas.
                    larga = max(aguja.split(), key=len)
                    k = frase.find(larga) if len(larga) > 3 else -1
                if k >= 0:
                    x = dict(x, _t=round(max(0.1, k/len(frase)*hablado), 2))
            salida.append(x)
        v[campo] = salida
    # NUNCA EL FOLIO EN BLANCO ESPERANDO ("se queda la pantalla en blanco y
    # tienes que esperar a ver que sale"): si al empezar no hay nadie ni nada,
    # lo primero que se nombra esta desde el principio.
    hay_algo = bool(v.get("figuras") or v.get("cifra")) or any(
        isinstance(x, dict) and (x.get("_ya") or x.get("_t") is None)
        for campo in ("cosas", "textos", "flechas") for x in v.get(campo) or [])
    if not hay_algo:
        con_hora = [(x["_t"], campo, n) for campo in ("cosas", "textos", "flechas")
                    for n, x in enumerate(v.get(campo) or []) if isinstance(x, dict)]
        if con_hora:
            _t, campo, n = min(con_hora)
            v[campo] = list(v[campo])
            v[campo][n] = dict(v[campo][n], _t=0.1)
    return v


def _desde(visual: dict, segundo: float) -> dict:
    """El trozo de un plano partido que empieza en `segundo`: lo que tenia que
    salir antes ya esta; lo que sale despues, a su hora dentro del trozo."""
    if segundo <= 0:
        return visual
    v = dict(visual)
    for campo in ("cosas", "textos", "flechas"):
        salida = []
        for x in visual.get(campo) or []:
            if isinstance(x, dict) and x.get("_t") is not None:
                t = float(x["_t"]) - segundo
                x = dict(x, _t=t) if t > 0.05 else dict(x, _ya=True)
            elif isinstance(x, dict):
                x = dict(x, _ya=True)
            salida.append(x)
        v[campo] = salida
    return v


def _acumula(anterior: dict | None, visual: dict) -> dict:
    """"sigue": el dibujo de antes se queda y se le añade lo nuevo, como en
    Whymentary (el ventilador... el monigote sudando... el termometro). Lo
    que ya estaba se marca "_ya" para que no vuelva a aparecer de golpe."""
    if not anterior or not visual.get("sigue"):
        return visual
    v = {"sigue": True, "figuras": visual.get("figuras") or anterior.get("figuras") or [],
         "ambiente": visual.get("ambiente") or anterior.get("ambiente")}
    if visual.get("mascota") or anterior.get("mascota"):
        v["mascota"] = visual.get("mascota") or dict(anterior["mascota"], accion="explica")
    for campo, tope in (("cosas", 5), ("textos", 3), ("flechas", 3)):
        viejos = [dict(x, _ya=True) for x in anterior.get(campo) or [] if isinstance(x, dict)]
        nuevos = [x for x in visual.get(campo) or [] if isinstance(x, dict)]
        v[campo] = (viejos + nuevos)[-tope:]
    if visual.get("cifra"):
        v["cifra"] = visual["cifra"]
    return v


def _variante(visual: dict, k: int) -> dict:
    """El mismo plano dibujado de otra manera, para el trozo k (1, 2...) de un
    plano demasiado largo: todo en espejo (lo de la izquierda pasa a la
    derecha), cada monigote en otra postura, y los letreros fuera a partir del
    segundo relevo; o, si hay una cosa de la que se habla, ella sola y enorme
    (el inserto), para que el folio cambie de verdad."""
    v = json.loads(json.dumps(visual))
    cosas = [c for c in v.get("cosas") or [] if isinstance(c, dict)]
    llevan = [f["lleva"] for f in v.get("figuras") or [] if isinstance(f, dict) and f.get("lleva")]
    if k % 2 == 0 and (cosas or llevan):
        # El inserto: la cosa de la que se habla, sola y enorme en el folio.
        que = cosas[0].get("que") if cosas else llevan[0]
        return {"cosas": [{"que": que, "x": 0.5, "y": 0.52, "tam": 0.5}],
                "textos": [t for t in v.get("textos") or [] if isinstance(t, dict)][:1]}
    espejo = k % 2 == 1
    for f in v.get("figuras") or []:
        if espejo:
            f["x"] = 1 - float(f.get("x", 0.5))
            f["espejo"] = not f.get("espejo")
        f["pose"] = _POSES_DE_RELEVO[(k + len(str(f.get("quien", "")))) % len(_POSES_DE_RELEVO)]
        f.pop("pose_fin", None)
    for c in v.get("cosas") or []:
        if espejo:
            c["x"] = 1 - float(c.get("x", 0.5))
        c["tam"] = min(0.55, float(c.get("tam") or 0.25)*(1.25 if k % 2 else 0.85))
    for t in v.get("textos") or []:
        if espejo:
            t["x"] = 1 - float(t.get("x", 0.5))
    for fl in v.get("flechas") or []:
        for punta in ("de", "a"):
            if espejo and isinstance(fl.get(punta), list) and fl[punta]:
                fl[punta] = [1 - float(fl[punta][0])] + list(fl[punta][1:])
    if isinstance(v.get("mascota"), dict):
        ma = v["mascota"]
        if espejo:
            ma["x"] = 1 - float(ma.get("x", 0.5))
            ma["espejo"] = not ma.get("espejo")
        ma["accion"] = ("explica", "senala", "encoge", "piensa")[k % 4]
    if k >= 2:
        v.pop("textos", None)
    return v


def _trozos_del_plano(visual: dict, fotogramas: int) -> list:
    """[(visual, fotogramas)]: el plano entero, o partido en trozos iguales
    de menos de _MAX_PLANO si se pasa. La careta del titulo no se parte."""
    n = 1 if visual.get("_careta") else math.ceil(fotogramas/(_MAX_PLANO*FPS))
    if n <= 1:
        return [(visual, fotogramas)]
    cortes = [round(fotogramas*j/n) for j in range(n + 1)]
    return [(visual if j == 0 else _variante(visual, j), cortes[j + 1] - cortes[j]) for j in range(n)]


def _cartel_titulo(titulo: str) -> dict:
    """El titulo en grande, en una o dos lineas, y WHY THOUGH debajo."""
    palabras = titulo.upper().split()
    if len(" ".join(palabras)) > 22 and len(palabras) > 1:
        corte = max(1, len(palabras)//2)
        lineas = [" ".join(palabras[:corte]), " ".join(palabras[corte:])]
    else:
        lineas = [" ".join(palabras)]
    textos = [{"texto": l, "x": 0.5, "y": 0.36 + k*0.18 - (0.09 if len(lineas) == 1 else 0),
               "tam": 0.16, "color": "rojo", "giro": -2} for k, l in enumerate(lineas)]
    textos.append({"texto": CHANNEL_NAME.upper(), "x": 0.5, "y": 0.8, "tam": 0.07, "color": "negro"})
    return {"textos": textos, "_careta": True}


def _minuto(segundos: float) -> str:
    s = int(segundos)
    return f"{s//60}:{s % 60:02d}"


def monta(guion: dict, carpeta: Path, parar=None) -> tuple[Path, Path, str]:
    """Voz, dibujos y video. Devuelve el video, la miniatura y los capitulos
    con su minuto para la descripcion."""
    from pydub import AudioSegment
    from . import sonidos
    carpeta.mkdir(parents=True, exist_ok=True)
    planos = []     # (texto, visual, pausa, capitulo)
    for n, cap in enumerate(guion["capitulos"]):
        anterior = None
        for k, p in enumerate(cap["planos"]):
            ultimo = k == len(cap["planos"]) - 1
            anterior = _acumula(anterior, p.get("visual") or {})
            planos.append((str(p["narracion"]), anterior,
                           _PAUSA_CAPITULO if ultimo else _PAUSA_PLANO, n))
        if n == 0 and len(guion["capitulos"]) > 1:
            # EL TITULO, DETRAS DEL GANCHO, como la careta de España Contada:
            # "¿has puesto la intro?". Tres segundos en silencio (solo la
            # campana): el titulo a rotulador y el nombre del canal debajo.
            planos.append(("", _cartel_titulo(guion.get("titulo") or ""), _CARETA, n))

    voz = AudioSegment.empty()
    duraciones, inicios_cap = [], {}
    for i, (texto, _v, pausa, cap) in enumerate(planos):
        if parar is not None and parar():
            from .pipeline import GenerationStopped
            raise GenerationStopped("parada pedida mientras se narraba")
        inicios_cap.setdefault(cap, len(voz)/1000.0)
        if texto:
            audio = _voz_guardada(texto, carpeta / f"voz_{i:03d}.wav")
        else:
            audio = AudioSegment.silent(duration=0, frame_rate=44100)
        audio = audio.set_frame_rate(44100).set_channels(1)
        hablado = len(audio)/1000.0
        planos[i] = (texto, _al_nombrarlo(_v, texto, hablado), pausa, cap)
        audio = audio + AudioSegment.silent(duration=int(pausa*1000), frame_rate=44100)
        voz += audio
        duraciones.append(len(audio)/1000.0)
    total = len(voz)/1000.0
    _poda_voces()
    logger.info("why: narracion de %.1f minutos (%s planos).", total/60, len(planos))
    if total < _MINIMO_SEGUNDOS:
        logger.warning("why: la narracion dura %.1f minutos, menos de los 10 que hacen falta.", total/60)
    narracion = carpeta / "narracion.m4a"
    voz.export(narracion, format="ipod", bitrate="128k")

    fronteras, t = [0], 0.0
    for d in duraciones:
        t += d
        fronteras.append(round(t*FPS))
    trozos, ruidos = [], []
    for i, (_texto, visual, _p, _c) in enumerate(planos):
        if parar is not None and parar():
            from .pipeline import GenerationStopped
            raise GenerationStopped("parada pedida mientras se dibujaba")
        inicio = fronteras[i]
        for j, (dibujo, fotogramas) in enumerate(_trozos_del_plano(visual, max(1, fronteras[i + 1] - fronteras[i]))):
            segundos = fotogramas/FPS
            dibujo = _desde(dibujo, (inicio - fronteras[i])/FPS)
            mp4 = carpeta / f"plano_{i:03d}_{j}.mp4"
            try:
                # Lo que "sigue" no entra deslizandose: es el mismo dibujo creciendo.
                entra = j > 0 or not visual.get("sigue")
                fps_plano = _FPS_MASCOTA if dibujo.get("mascota") else _FPS_DIBUJO
                _tuberia(garabato.fotos(dibujo, segundos, fps_plano), fotogramas, mp4, zoom=False, brillo=0,
                         desliza=_DESLIZA if entra else 0, fps_entrada=fps_plano)
                if entra:
                    ruidos.append(("whoosh", max(0.0, inicio/FPS - 0.12), 0.4))
                ruidos += [(n, inicio/FPS + t0, d) for n, t0, d in garabato.sonidos_del_plano(dibujo, segundos)]
                if visual.get("_careta"):
                    ruidos.append(("campana", inicio/FPS + 0.1, 1.8))
            except Exception:
                logger.warning("why: el plano %s ha fallado; va en blanco con su texto.", i, exc_info=True)
                _tuberia(garabato.fotos({"textos": [{"texto": "...", "x": 0.5, "y": 0.5}]}, 1, _FPS_DIBUJO),
                         fotogramas, mp4, zoom=False, brillo=0)
            trozos.append(mp4)
            inicio += fotogramas
        if i % 25 == 0:
            logger.info("why: %s de %s planos montados.", i + 1, len(planos))

    lista = carpeta / "planos.txt"
    lista.write_text("\n".join(f"file '{p.resolve()}'" for p in trozos))
    mudo = carpeta / "mudo.mp4"
    _ffmpeg(["-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(mudo)], "union")
    con_voz = carpeta / "con_voz.mp4"
    _ffmpeg(["-i", str(mudo), "-i", str(narracion), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
             "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(con_voz)], "voz")
    final = con_voz
    if ruidos:
        try:
            from .video_builder import mezclar_efectos
            pista = sonidos.pista(ruidos, total, carpeta / "efectos.wav", volumen=0.14)
            if pista is not None:
                final = mezclar_efectos(con_voz, pista, carpeta / "con_efectos.mp4")
        except Exception:
            logger.warning("why: sin efectos de sonido.", exc_info=True)
    try:
        from .pipeline import _pick_music_track
        from .video_builder import mix_background_music
        musica = _pick_music_track()
        if musica is not None:
            final = mix_background_music(final, musica, carpeta / "final.mp4", MUSIC_VOLUME*0.7)
    except Exception:
        logger.warning("why: sin musica de fondo.", exc_info=True)

    # La miniatura: la que pidio el guion, dibujada igual que un plano.
    jpg = carpeta / "miniatura.jpg"
    mini = guion.get("miniatura") if isinstance(guion.get("miniatura"), dict) else {"textos": [
        {"texto": str(guion.get("titulo", ""))[:24].upper(), "x": 0.5, "y": 0.5, "tam": 0.14}]}
    ultima = None
    for img in garabato.fotos(mini, 1.2, _FPS_DIBUJO):
        ultima = img
    ultima.resize((1280, 720)).save(jpg, quality=92)

    # Los capitulos, con su minuto: el primero tiene que empezar en 0:00 o
    # YouTube no los muestra.
    marcas = []
    for n, cap in enumerate(guion["capitulos"]):
        segundo = 0.0 if n == 0 else inicios_cap.get(n, 0.0)
        marcas.append(f"{_minuto(segundo)} {cap['titulo']}")

    for p in list(carpeta.glob("plano_*")) + list(carpeta.glob("voz_*")):
        p.unlink(missing_ok=True)
    for p in (mudo, narracion, con_voz, carpeta / "con_efectos.mp4", carpeta / "efectos.wav"):
        if p != final:
            p.unlink(missing_ok=True)
    return final, jpg, "\n".join(marcas)


_PIDE_RETOQUE = """Redo ONLY the "visual" of these shots - the narration stays exactly the same.
Some asked for drawings that did not exist when the script was written ("falta"): many exist NOW
(check the lists above). Others are TOO EMPTY (a lonely person, a single thing): make them show
what the sentence says - 2-4 things, everything the narration names that can be drawn, with
"etiqueta" labels and "cuando" timings. Keep "sigue" as it was:
{planos}

Return ONLY: {{"planos": [{{"i": <same number>, "visual": {{...}}}}]}}"""


def _pobre(visual: dict) -> bool:
    """Un plano que no cuenta nada: una persona sola o una cosa suelta, sin
    nada mas ("es simple, pero igual no habria que hacerlo tan simple")."""
    if visual.get("sigue") or visual.get("cifra") or visual.get("_careta"):
        return False
    cuenta = sum(len([x for x in visual.get(c) or [] if isinstance(x, dict)])
                 for c in ("figuras", "cosas", "textos", "flechas")) + (1 if visual.get("mascota") else 0)
    return cuenta <= 1


def retoca(guion: dict) -> int:
    """Antes de montar: los planos que pidieron un dibujo que faltaba se
    vuelven a pedir, ahora que ya esta dibujado (la pluma, la rata...). Una
    sola llamada pequeña; si falla, se monta con lo que habia."""
    todos = [p for cap in guion.get("capitulos") or [] for p in cap.get("planos") or []]
    pendientes = [(i, p) for i, p in enumerate(todos)
                  if str(p.get("falta") or "").strip() or _pobre(p.get("visual") or {})]
    if not pendientes:
        return 0
    lista = "\n".join(json.dumps({"i": i, "narracion": p.get("narracion"), "falta": p.get("falta"),
                                   "visual": p.get("visual")}, ensure_ascii=False)
                       for i, p in pendientes)
    sistema = _INSTRUCCIONES.format(
        canal=CHANNEL_NAME, acciones=_ACCIONES, quienes=_lista(garabato.QUIENES), poses=_lista(_POSES),
        gestos=_lista(_GESTOS), efectos=_lista(_EFECTOS),
        llevables=_lista(monigotes.LLEVABLES_EXPLICADOS), objetos=_lista(garabato.OBJETOS_VALIDOS),
        colores=_lista(garabato.COLORES), ambientes=_lista(garabato.garabato_ambiente.AMBIENTES),
        dosier="(not needed for this task)")
    try:
        nuevos = _pregunta(sistema, _PIDE_RETOQUE.format(planos=lista), "why-retoque", 16000)
    except Exception:
        logger.warning("why: no se han podido redibujar los planos que pedian algo.", exc_info=True)
        return 0
    hechos = 0
    for n in nuevos.get("planos") or []:
        try:
            i = int(n.get("i"))
        except (TypeError, ValueError):
            continue
        if 0 <= i < len(todos) and isinstance(n.get("visual"), dict):
            todos[i]["visual"] = n["visual"]
            todos[i]["falta"] = ""
            hechos += 1
    logger.info("why: %s de %s planos redibujados (lo que faltaba o estaban vacios).", hechos, len(pendientes))
    return hechos


def run_montaje(on_done) -> list[int]:
    """PASO 2 (/montar): el video del guion que dejo /why."""
    from . import storage
    from .pipeline import GenerationStopped, _stop_requested, cleanup_finished_video_files
    _stop_requested.clear()
    cleanup_finished_video_files()
    guion = json.loads(_PENDIENTE.read_text())
    carpeta = Path(DATA_DIR) / f"why_{int(time.time())}"
    if retoca(guion):
        _PENDIENTE.write_text(json.dumps(guion, ensure_ascii=False, indent=1))
    try:
        logger.info("[why] Voz y dibujos de %r...", guion.get("_tema"))
        video, miniatura, capitulos = monta(guion, carpeta, parar=_stop_requested.is_set)
    except GenerationStopped as exc:
        logger.info("Video en ingles detenido: %s", exc)
        shutil.rmtree(carpeta, ignore_errors=True)
        return []
    except Exception:
        shutil.rmtree(carpeta, ignore_errors=True)
        raise
    _PENDIENTE.replace(_ULTIMO)
    descripcion = str(guion.get("descripcion") or "").strip() + "\n\n" + capitulos
    video_id = storage.create_video_record(
        source_url="", variant="long", title=str(guion.get("titulo") or guion.get("_tema"))[:100],
        description=descripcion, tags=[str(t) for t in guion.get("tags") or []][:25],
        video_path=str(video), thumbnail_path=str(miniatura), subtitle_path="")
    logger.info("Video #%s (why) generado y pendiente de aprobacion.", video_id)
    if on_done is not None:
        on_done(video_id)
    return [video_id]
