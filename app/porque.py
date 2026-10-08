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
import logging
import math
import shutil
import time
from pathlib import Path

from . import garabato, llm_usage, monigotes
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
_PAUSA_CAPITULO = 0.8
_PENDIENTE = Path(DATA_DIR) / "porque_pendiente.json"


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
  "figuras": 0-3 stick people: {{"quien": one of {quienes} ("persona" = adult, "persona_b" =
             adult with a bun, "nino" = kid), "x": 0.12-0.88, "pose": one of {poses},
             "pose_fin": another pose (the figure moves from one to the other - use it often),
             "gesto": one of {gestos}, "efecto": one of {efectos} or omit,
             "lleva": what they hold, one of {llevables} or omit, "espejo": true to face left}}
  "cosas":   0-5 objects: {{"que": one of {objetos}, "x": 0.05-0.95, "tam": 0.06-0.55 (height,
             fraction of the screen), "y": 0.1-0.9 = its CENTER if it floats (omit "y" and it
             stands on the floor)}}
  "textos":  0-2 BIG hand-lettered words: {{"texto": "IT'S HOT" (max 3-4 words, CAPITALS),
             "x", "y", "tam": 0.08-0.2, "color": one of {colores}, "giro": -8 to 8 degrees}}
  "flechas": 0-2 hand-drawn arrows: {{"de": [x, y], "a": [x, y], "color": ...}}
  "cifra":   a GIANT number with rays, alone on the page: {{"valor": "35°C", "pie": "short
             caption", "color": ...}} (use it for the key numbers; then no figuras/cosas)
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
About {palabras} words of narration, split into SHOTS of {pmin}-{pmax} words each (one sentence,
5-9 seconds). The drawing changes with every shot: never the same visual twice in a row.
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
    dosier = _dosier(tema)
    sistema = _INSTRUCCIONES.format(
        canal=CHANNEL_NAME, quienes=_lista(garabato.QUIENES), poses=_lista(monigotes.POSES_VALIDAS),
        gestos=_lista(monigotes.GESTOS_VALIDOS), efectos=_lista(monigotes.EFECTOS_VALIDOS),
        llevables=_lista(monigotes.LLEVABLES_EXPLICADOS), objetos=_lista(garabato.OBJETOS_VALIDOS),
        colores=_lista(garabato.COLORES), dosier=dosier or "(no dossier: use only facts you are sure of)")
    plan = _pregunta(sistema, _PIDE_INDICE.format(tema=tema, palabras=_PALABRAS, canal=CHANNEL_NAME),
                     "why-indice", 8000)
    capitulos = [c for c in plan.get("capitulos") or [] if isinstance(c, dict)]
    if not capitulos:
        raise LargoError("el indice no trae capitulos")
    indice = "\n".join(f"{i + 1}. {c.get('titulo')}: {c.get('resumen')}" for i, c in enumerate(capitulos))
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
            palabras=int(c.get("palabras") or _PALABRAS/len(capitulos)), pmin=_PALABRAS_PLANO[0],
            pmax=_PALABRAS_PLANO[1], anterior=anterior, cierre=cierre), f"why-capitulo-{i + 1}")
        planos = [p for p in cap.get("planos") or []
                  if isinstance(p, dict) and str(p.get("narracion", "")).strip()]
        if not planos:
            raise LargoError(f"el capitulo {i + 1} ha salido vacio")
        hechos.append({"titulo": c.get("titulo", ""), "planos": planos})
    plan["capitulos"] = hechos
    return plan


def revisa(guion: dict) -> tuple[str, list[str]]:
    """Que pide el guion, y que pide que NO esta dibujado."""
    from collections import Counter
    validos = {"que": set(garabato.OBJETOS_VALIDOS), "pose": set(monigotes.POSES_VALIDAS),
               "gesto": set(monigotes.GESTOS_VALIDOS), "efecto": set(monigotes.EFECTOS_VALIDOS),
               "lleva": set(monigotes.LLEVABLES_EXPLICADOS), "quien": set(garabato.QUIENES)}
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
                que = str((c or {}).get("que") or "").lower()
                if que:
                    (usados if que in validos["que"] else faltan)[que if que in validos["que"] else f"objeto {que}"] += 1
            for f in v.get("figuras") or []:
                for campo in ("quien", "pose", "pose_fin", "gesto", "efecto", "lleva"):
                    val = str((f or {}).get(campo) or "").lower()
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
        for k, p in enumerate(cap["planos"]):
            ultimo = k == len(cap["planos"]) - 1
            planos.append((str(p["narracion"]), p.get("visual") or {},
                           _PAUSA_CAPITULO if ultimo else _PAUSA_PLANO, n))

    voz = AudioSegment.empty()
    duraciones, inicios_cap = [], {}
    for i, (texto, _v, pausa, cap) in enumerate(planos):
        if parar is not None and parar():
            from .pipeline import GenerationStopped
            raise GenerationStopped("parada pedida mientras se narraba")
        inicios_cap.setdefault(cap, len(voz)/1000.0)
        audio = _voz_google(texto, carpeta / f"voz_{i:03d}.wav", ritmo_pedido=None)
        audio = audio.set_frame_rate(44100).set_channels(1) + AudioSegment.silent(
            duration=int(pausa*1000), frame_rate=44100)
        voz += audio
        duraciones.append(len(audio)/1000.0)
    total = len(voz)/1000.0
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
        fotogramas = max(1, fronteras[i + 1] - fronteras[i])
        segundos = fotogramas/FPS
        mp4 = carpeta / f"plano_{i:03d}.mp4"
        try:
            _tuberia(garabato.fotos(visual, segundos, _FPS_DIBUJO), fotogramas, mp4, zoom=False, brillo=0)
            ruidos += [(n, fronteras[i]/FPS + t0, d) for n, t0, d in garabato.sonidos_del_plano(visual, segundos)]
        except Exception:
            logger.warning("why: el plano %s ha fallado; va en blanco con su texto.", i, exc_info=True)
            _tuberia(garabato.fotos({"textos": [{"texto": "...", "x": 0.5, "y": 0.5}]}, 1, _FPS_DIBUJO),
                     fotogramas, mp4, zoom=False, brillo=0)
        trozos.append(mp4)
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


def run_montaje(on_done) -> list[int]:
    """PASO 2 (/montar): el video del guion que dejo /why."""
    from . import storage
    from .pipeline import GenerationStopped, _stop_requested, cleanup_finished_video_files
    _stop_requested.clear()
    cleanup_finished_video_files()
    guion = json.loads(_PENDIENTE.read_text())
    carpeta = Path(DATA_DIR) / f"why_{int(time.time())}"
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
    _PENDIENTE.unlink(missing_ok=True)
    descripcion = str(guion.get("descripcion") or "").strip() + "\n\n" + capitulos
    video_id = storage.create_video_record(
        source_url="", variant="long", title=str(guion.get("titulo") or guion.get("_tema"))[:100],
        description=descripcion, tags=[str(t) for t in guion.get("tags") or []][:25],
        video_path=str(video), thumbnail_path=str(miniatura), subtitle_path="")
    logger.info("Video #%s (why) generado y pendiente de aprobacion.", video_id)
    if on_done is not None:
        on_done(video_id)
    return [video_id]
