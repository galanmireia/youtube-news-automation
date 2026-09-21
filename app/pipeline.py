import json
import logging
import random
import shutil
import threading
import time
from pathlib import Path
from typing import Callable

from . import llm_usage, storage
from .branding import INTRO_NARRATION
from .config import (
    BURN_SUBTITLES,
    CONTENT_MODE,
    DATA_DIR,
    LONG_VIDEO_HEIGHT,
    LONG_VIDEO_WIDTH,
    MUSIC_DIR,
    MUSIC_VOLUME,
    SHORT_VIDEO_HEIGHT,
    SHORT_VIDEO_WIDTH,
)
from .entity_extraction import extract_entities
from . import research
from .news_picker import pick_best_story
from .news_source import fetch_candidate_news
from .topic_source import fetch_candidate_topics, fetch_topic_by_term
from .script_generator import generate_script, _trim_sources
from .subtitles import generate_subtitles
from .thumbnail import generate_thumbnail
from . import real_photos
from .tts import synthesize_scenes
from .voice_clone import sintetizar_escenas
from .voice_align import align_recording, reading_script
from .config import NARRATION_SOURCE
from .video_builder import build_video, burn_subtitles, mix_background_music
from .visuals import fetch_clips_for_scenes

logger = logging.getLogger(__name__)

# Set by request_stop() (the bot's /parar) and cleared at the start of every
# run. A generation is a chain of single blocking calls - an API request, an
# ffmpeg run - with nowhere inside them to check a flag, so a stop can only
# take effect between stages, not instantly.
_stop_requested = threading.Event()


class GenerationStopped(Exception):
    """Raised at a stage boundary when a stop has been requested."""


def request_stop() -> None:
    """Asks the running generation to give up at its next stage boundary."""
    _stop_requested.set()


def stop_requested() -> bool:
    """Whether the run that just finished ended because a stop was asked for.
    The flag survives until the next run clears it, so a caller can tell a
    stopped run apart from one that simply had nothing to do."""
    return _stop_requested.is_set()


# En que anda ahora mismo, para que alguien de fuera lo pueda preguntar.
#
# Existe porque ella penso que se habia muerto. Y con razon: entre el paso 5 y
# el 7 de un largo el bot se calla DIEZ MINUTOS enteros - las transiciones de
# un video de siete minutos son varias pasadas de ffmpeg de dos o tres minutos
# cada una - y desde Telegram eso es indistinguible de un cuelgue.
ESTADO: dict = {"texto": "", "desde": time.time()}


def _stage(variant: str, number: int, message: str, *args) -> None:
    """Announces a stage, and aborts the generation here if a stop was asked
    for. Every stage goes through this, so a stop is honoured at whichever
    boundary comes next rather than only between variants."""
    if _stop_requested.is_set():
        raise GenerationStopped(f"parada pedida antes de [{variant}] {number}/7")
    logger.info("[%s] %s/7 " + message, variant, number, *args)
    try:
        ESTADO["texto"] = f"[{variant}] {number}/7 " + (message % args if args else message)
        ESTADO["desde"] = time.time()
    except Exception:
        # Un fallo formateando el aviso no puede tumbar una generacion.
        ESTADO["texto"] = f"[{variant}] {number}/7"
        ESTADO["desde"] = time.time()

_VARIANT_DIMENSIONS = {
    "short": (SHORT_VIDEO_WIDTH, SHORT_VIDEO_HEIGHT),
    "long": (LONG_VIDEO_WIDTH, LONG_VIDEO_HEIGHT),
}
_VARIANT_ASPECT_RATIO = {"short": "9:16", "long": "16:9"}


_MUSIC_SUFFIXES = {".mp3", ".m4a", ".wav", ".aac", ".ogg"}


def _pick_music_track() -> Path | None:
    """One random track from the music folder, or None if there is no folder
    or nothing usable in it - music is optional, and a missing folder must
    never stop a video from being generated."""
    if not MUSIC_DIR.is_dir():
        return None
    tracks = sorted(p for p in MUSIC_DIR.iterdir() if p.suffix.lower() in _MUSIC_SUFFIXES)
    if not tracks:
        logger.info("No hay pistas de musica en %s, el video se genera sin musica de fondo.", MUSIC_DIR)
        return None
    return random.choice(tracks)


# The fixed bumper a long video opens on. Shared because a job paused to be
# narrated by hand has to prepend exactly the same scene the ordinary path
# would, or every timing after it is off by one scene.
_INTRO_SCENE = {
    "narration": INTRO_NARRATION,
    "visual_keywords": "",
    "photo_subject": "",
    "photo_subject_role": "",
    "ai_image_prompt": "",
    "on_screen_highlight": "",
    "is_intro": True,
}


def _con_creditos(descripcion: str, urls: list[str]) -> str:
    """The description, with the image credits the licences require.

    Appended here rather than asked of the script model, for the same reason
    the facts are: a credit is a record of what was actually used, and the
    model writing the description does not know which photographs the visual
    stage ended up finding."""
    if not urls:
        return descripcion
    try:
        lineas = real_photos.creditos_de(urls)
    except Exception:
        logger.exception("No se han podido montar los creditos de imagen.")
        return descripcion
    if not lineas:
        return descripcion
    bloque = "\n".join(f"· {linea}" for linea in lineas)
    return (
        f"{descripcion.rstrip()}\n\n"
        "―――\n"
        "IMÁGENES\n"
        f"{bloque}\n\n"
        "Textos de consulta: Wikipedia, bajo licencia CC BY-SA."
    )


def _generate_variant(
    news_item: dict,
    variant: str,
    work_dir: Path,
    script: dict | None = None,
    is_sensitive: bool | None = None,
    recording_path: Path | None = None,
) -> int:
    """Builds one video. With `script` given the writing stages are skipped -
    that is how a job paused to be narrated by hand picks up where it left
    off - and with `recording_path` given the timing comes from that recording
    instead of from the synthesiser."""
    width, height = _VARIANT_DIMENSIONS[variant]
    variant_dir = work_dir / variant
    variant_dir.mkdir(parents=True, exist_ok=True)

    # Each stage announces itself before it starts, not after. When a step
    # froze with no error, the log simply stopped mid-run and there was no way
    # to tell from it which call was stuck - the stage had to be inferred from
    # whichever incidental line happened to be logged last.
    ya_escrito = script is not None
    if not ya_escrito:
        _stage(variant, 1, "Escribiendo el guion...")
        script = generate_script(news_item, variant=variant)
    # Long videos open with a fixed bumper line over a branded title card, so
    # the channel has a consistent opening. Shorts don't: the first seconds
    # of a Short decide whether the viewer keeps watching or swipes, and a
    # logo card spends them on something that tells the viewer nothing. They
    # start on the hook instead.
    # La careta va DETRAS DEL GANCHO, no delante. Los primeros cinco segundos
    # deciden si el espectador se queda, y gastarlos en el nombre del canal es
    # gastarlos en algo que todavia no le importa. Primero la frase que engancha,
    # luego la careta, luego el video. En los Shorts sigue sin haber ninguna.
    posicion_careta = 1
    indices = (posicion_careta, 0)
    has_intro = bool(script["scenes"]) and any(
        i < len(script["scenes"]) and bool(script["scenes"][i].get("is_intro"))
        for i in indices
    )
    if not ya_escrito and variant == "long" and script["scenes"]:
        has_intro = True
        escenas = list(script["scenes"])
        escenas.insert(min(posicion_careta, len(escenas)), dict(_INTRO_SCENE))
        script["scenes"] = escenas
    # Default to treating the story as sensitive if the field is somehow
    # missing/unparseable - that only disables the extra narration-based
    # real-photo lookup below, never anything the model explicitly asked for.
    if is_sensitive is None:
        raw_sensitive = script.get("is_sensitive", True)
        is_sensitive = (raw_sensitive.strip().lower() != "false"
                        if isinstance(raw_sensitive, str) else bool(raw_sensitive))

    # A dedicated, isolated pass asking specifically "what named entities
    # appear in this text" is far more reliable than the model tagging
    # photo_subject correctly as one more field inside the much larger
    # script-generation prompt.
    #
    # Esto se saltaba en los casos sensibles, para que el sistema no fuera a
    # buscar por su cuenta la cara de una victima. El resultado fue el video
    # de Asunta sin una sola persona: en un caso de sucesos TODOS los nombres
    # son de gente sensible, asi que el guardia no filtraba, apagaba. Se
    # quita. Lo que decide si una cara se puede enseñar es la licencia de la
    # foto, no si el sistema o el guion pidio el nombre.
    if not ya_escrito:
        _stage(variant, 2, "Extrayendo entidades del guion...")
        entities_by_scene = extract_entities(script["scenes"])
        for i, scene in enumerate(script["scenes"]):
            scene["detected_entities"] = entities_by_scene.get(i, [])

    marcas_narracion: list = []
    retratos_usados: list = []
    if recording_path is not None:
        _stage(variant, 3, "Alineando tu grabacion con el guion (%s escenas)...", len(script["scenes"]))
        narration_path, scene_durations = align_recording(script["scenes"], Path(recording_path))
    elif NARRATION_SOURCE == "clon":
        _stage(variant, 3, "Narrando con tu voz clonada (%s escenas)...", len(script["scenes"]))
        # The per-character timings come back too: a slide uses them to put
        # each of its reveals where the narration actually says it.
        narration_path, scene_durations = sintetizar_escenas(
            script["scenes"], variant_dir / "audio", marcas=marcas_narracion
        )
    else:
        _stage(variant, 3, "Generando la narracion con TTS (%s escenas)...", len(script["scenes"]))
        narration_path, scene_durations = synthesize_scenes(script["scenes"], variant_dir / "audio")

    _stage(variant, 4, "Buscando imagenes y videos para las escenas...")
    urls_de_fotos: list[str] = []
    clip_entries = fetch_clips_for_scenes(
        script["scenes"],
        variant_dir / "clips",
        _VARIANT_ASPECT_RATIO[variant],
        scene_durations,
        is_sensitive=is_sensitive,
        creditos=urls_de_fotos,
        marcas=marcas_narracion,
        # El articulo del caso, como ultimo recurso para las caras. La gente
        # de un suceso casi nunca tiene articulo propio - Asunta Basterra,
        # Rosario Porto, Alfonso Basterra no lo tienen - pero sus fotos estan
        # dentro del articulo del caso. Sin esto, un video de sucesos se queda
        # sin una sola cara, que es justo lo que no puede pasar.
        caso=news_item.get("title", ""),
        # Las caras que acaben en el video, para que la miniatura salga de una
        # de ellas y no de un fotograma cualquiera.
        retratos=retratos_usados,
    )

    _stage(variant, 5, "Montando el video con ffmpeg...")
    final_video_path = build_video(
        clip_entries,
        scene_durations,
        narration_path,
        variant_dir,
        variant_dir / "final_video.mp4",
        width,
        height,
        # No "FUENTE: X" burned into the corner any more. It looked like a
        # watermark and it was not attribution: Wikimedia licences ask for the
        # author and the licence of each image by name, which a single word
        # naming the website never gave. The credit now goes where video
        # credits belong - the description - with what the licence asks for.
        source_name="",
        # Cual es la careta ahora se busca, porque ya no es siempre la primera.
        intro_duration=next(
            (scene_durations[i] for i, e in enumerate(script["scenes"])
             if e.get("is_intro") and i < len(scene_durations)),
            0.0,
        ) if has_intro else 0.0,
    )

    # Two subtitle tracks off one transcription: a sentence-level SRT still
    # uploaded to YouTube as a toggleable caption track, plus a short-chunk
    # version burned into the picture (most of the Shorts feed is watched
    # muted, so on-screen text is what carries the narration).
    _stage(variant, 6, "Transcribiendo para los subtitulos...")
    srt_path, burn_ass_path = generate_subtitles(
        narration_path,
        variant_dir / "subtitles.srt",
        variant_dir / "subtitles_burn.ass",
        width,
        height,
        # The narration is this exact text spoken aloud, so the transcription
        # is only needed for its timings - the wording is already known, and
        # trusting the transcription for it burns misheard names into the
        # picture.
        script_text=" ".join(scene.get("narration", "") for scene in script["scenes"]),
    )

    # The thumbnail is grabbed from the video, so take it before burning in
    # subtitles - otherwise a random half-sentence ends up across the
    # thumbnail.
    _stage(variant, 7, "Miniatura, subtitulos incrustados y musica...")
    thumbnail_path = generate_thumbnail(
        final_video_path, script["title"], variant_dir / "thumbnail.jpg", width, height,
        retratos=retratos_usados,
    )

    if BURN_SUBTITLES:
        final_video_path = burn_subtitles(final_video_path, burn_ass_path, variant_dir / "final_subtitled.mp4")

    music_path = _pick_music_track()
    if music_path is not None:
        final_video_path = mix_background_music(
            final_video_path, music_path, variant_dir / "final_with_music.mp4", MUSIC_VOLUME
        )

    # Everything else in this directory was scaffolding for the build: the
    # downloaded stock clips and photos, the per-scene audio, the rendered
    # scene segments and every ffmpeg intermediate. Together they dwarf the
    # three files that are actually needed from here on, and they were being
    # kept until the video was uploaded or rejected - so a few videos waiting
    # for approval filled the volume and the next build died with "No space
    # left on device".
    _discard_build_files(variant_dir, keep={final_video_path, thumbnail_path, srt_path})

    video_id = storage.create_video_record(
        source_url=news_item["link"],
        variant=variant,
        title=script["title"],
        description=_con_creditos(script["description"], urls_de_fotos),
        tags=script["tags"],
        video_path=str(final_video_path),
        thumbnail_path=str(thumbnail_path),
        subtitle_path=str(srt_path),
    )
    logger.info("Video #%s (%s) generado y pendiente de aprobacion.", video_id, variant)
    return video_id



def _discard_build_files(variant_dir: Path, keep: set[Path]) -> int:
    """Removes everything under a finished variant's directory except the
    files that are still needed - the video itself, its thumbnail and its
    subtitle track. Returns the megabytes freed."""
    keep_resolved = {path.resolve() for path in keep}
    freed = 0
    for path in sorted(variant_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir():
            # Only removes it if the loop above already emptied it.
            try:
                path.rmdir()
            except OSError:
                pass
            continue
        if path.resolve() in keep_resolved:
            continue
        freed += path.stat().st_size
        path.unlink(missing_ok=True)
    if freed:
        logger.info("Limpieza: %.0f MB de ficheros intermedios eliminados.", freed / 1e6)
    return freed


_interrupted_run = ""


def interrupted_run_evidence() -> str:
    """What note_interrupted_run() found at startup, or "" if nothing."""
    return _interrupted_run


def note_interrupted_run() -> str:
    """Names a generation that a restart killed mid-build, or "" if none.

    A deploy restarts the container, and a generation in flight simply
    vanishes: no video, no error, no message. Twice today a push of mine did
    exactly that, and the only symptom was the user waiting for something that
    was never coming. The leftover job directory is the evidence, so the bot
    can say so instead of leaving somebody guessing.

    Must run BEFORE sweep_orphan_build_files(), which deletes exactly the
    files this reads as evidence."""
    global _interrupted_run
    keep = {Path(path).resolve() for path in storage.all_referenced_paths()}
    for job_dir in sorted(Path(DATA_DIR).glob("job_*")):
        if not job_dir.is_dir():
            continue
        # A finished build's files are either referenced by a video record or
        # already cleaned up. Files belonging to neither mean a build stopped
        # halfway.
        huerfanos = [f for f in job_dir.rglob("*") if f.is_file() and f.resolve() not in keep]
        if huerfanos:
            _interrupted_run = job_dir.name
            return _interrupted_run
    _interrupted_run = ""
    return ""


def sweep_orphan_build_files() -> int:
    """One pass over the whole data directory removing files no video record
    points at any more.

    Builds used to leave their scaffolding behind until the video was uploaded
    or rejected, and a failed run could leave a whole job directory with no
    record at all. That filled the volume - a build died with "No space left
    on device" with 4.8GB of a 5GB disk used. New builds clean up after
    themselves now; this clears what earlier ones left. Returns megabytes
    freed."""
    keep = {Path(path).resolve() for path in storage.all_referenced_paths()}
    freed = 0
    for job_dir in Path(DATA_DIR).glob("job_*"):
        for path in sorted(job_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if path.is_dir():
                try:
                    path.rmdir()
                except OSError:
                    pass
                continue
            if path.resolve() in keep:
                continue
            freed += path.stat().st_size
            path.unlink(missing_ok=True)
        if job_dir.is_dir() and not any(job_dir.iterdir()):
            job_dir.rmdir()
    if freed:
        logger.info("Limpieza de arranque: %.0f MB de ficheros huerfanos eliminados.", freed / 1e6)
    return freed


def cleanup_finished_video_files() -> int:
    """Deletes the on-disk working files (downloaded clips, audio, ffmpeg
    intermediates, final video/thumbnail/subtitles) for videos that are
    already uploaded or rejected - nothing ever needs them again once a
    video reaches one of those states, and leaving every run's files on
    disk forever eventually fills up the volume. Returns how many variant
    directories were removed."""
    removed = 0
    for video in storage.list_finished_videos():
        video_path = video["video_path"]
        if not video_path:
            continue
        variant_dir = Path(video_path).parent
        if variant_dir.exists():
            shutil.rmtree(variant_dir, ignore_errors=True)
            removed += 1
        job_dir = variant_dir.parent
        if job_dir.exists() and not any(job_dir.iterdir()):
            job_dir.rmdir()
    return removed


_TRABAJO_VOZ = "trabajo_voz.json"


def prepare_voice_job(variant: str, forced_topic: str | None = None) -> dict | None:
    """Writes the script and stops, so it can be read aloud before anything is
    built.

    Everything up to the narration is done here - choosing the case, the
    dossier, the script, the entities - and then the job waits on disk. What
    comes back is the text to read; what resumes it is resume_voice_job with
    the recording."""
    news_item, work_dir = _choose_and_prepare(forced_topic)
    if news_item is None:
        return None

    width, height = _VARIANT_DIMENSIONS[variant]
    _stage(variant, 1, "Escribiendo el guion para narrar a mano...")
    script = generate_script(news_item, variant=variant)
    if variant == "long":
        script["scenes"] = [dict(_INTRO_SCENE)] + script["scenes"]

    raw = script.get("is_sensitive", True)
    is_sensitive = raw.strip().lower() != "false" if isinstance(raw, str) else bool(raw)
    if not is_sensitive:
        _stage(variant, 2, "Extrayendo entidades del guion...")
        entities = extract_entities(script["scenes"])
        for i, scene in enumerate(script["scenes"]):
            scene["detected_entities"] = entities.get(i, [])

    job_file = work_dir / _TRABAJO_VOZ
    job_file.write_text(json.dumps({
        "news_item": news_item, "variant": variant, "script": script,
        "is_sensitive": is_sensitive, "work_dir": str(work_dir),
    }, ensure_ascii=False))

    resumen_coste = llm_usage.report_and_reset()
    if resumen_coste:
        logger.info("[%s] %s", variant, resumen_coste)
    logger.info("Guion listo y esperando narracion: %s", job_file)

    # The intro bumper is spoken by the channel too, so it is part of what
    # gets read - leaving it out would desynchronise every scene after it.
    texto = reading_script(script["scenes"], script["title"], news_item["title"])
    limpio = " ".join((sc.get("narration") or "") for sc in script["scenes"])
    return {
        "job_file": job_file, "title": script["title"], "variant": variant,
        "narration": texto, "palabras": len(limpio.split()),
        "escenas": len(script["scenes"]), "tema": news_item["title"],
    }


def pending_voice_job() -> Path | None:
    """The newest script still waiting to be narrated, if there is one."""
    trabajos = sorted(Path(DATA_DIR).glob(f"job_*/{_TRABAJO_VOZ}"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
    return trabajos[0] if trabajos else None


def resume_voice_job(job_file: Path, recording_path: Path) -> int:
    """Finishes a paused job using the recording as its narration."""
    datos = json.loads(Path(job_file).read_text())
    work_dir = Path(datos["work_dir"])
    video_id = _generate_variant(
        datos["news_item"], datos["variant"], work_dir,
        script=datos["script"], is_sensitive=datos["is_sensitive"],
        recording_path=Path(recording_path),
    )
    storage.mark_source_processed(datos["news_item"]["link"], datos["news_item"].get("title", ""))
    Path(job_file).unlink(missing_ok=True)
    resumen_coste = llm_usage.report_and_reset()
    if resumen_coste:
        logger.info("[%s] %s", datos["variant"], resumen_coste)
    return video_id


# How many cases go in one video, and how much dossier each one gets.
#
# Five is what the titles in the niche promise most often ("4 Most...", "The 8
# Strangest..."), and it divides a ten-minute video into pieces of about two
# minutes - long enough for a story with a turn in it, short enough that a
# viewer who finds one case dull is a minute from the next.
CASOS_POR_VIDEO = 5
# How much of each case's dossier reaches the script.
#
# Nine thousand was sized when a dossier meant Wikipedia and nothing else.
# Measured on Cicada 3301 with the open-web reader working: 8,210 words of
# first-hand material on top of the article - four of the six sources
# rescued from the archive. Nine thousand characters is about 1,400 words,
# so the cut was throwing away roughly four fifths of what had just been
# fetched, including every reference, because they sit at the END of the
# dossier where the cut lands.
#
# Five cases at twenty-five thousand is 125,000 characters, about 31,000
# tokens of input - a few cents, and the story sits after the prompt-cache
# marker so it does not invalidate the cached instructions. Reading it is
# far cheaper than fetching it was.
_CHARS_POR_CASO = 25000

# Por debajo de esto no hay video, hay relleno. Dos mil caracteres son unas
# trescientas palabras: menos que la entradilla de un solo caso.
#
# Menos para un Short, y no por relajar el listón sino porque mide otra cosa:
# un largo son dos mil palabras de narracion y necesita un dosier que las
# sostenga, mientras que un Short son noventa palabras y UN hecho. Mil
# doscientos caracteres son unas ciento ochenta palabras - el doble de lo que
# se va a narrar - y con eso el guion cuenta algo que leyó, no algo que se
# invento, que es de lo que protege este guardia.
#
# Importa para la tanda diaria: con el listón del largo, media historia de
# España se descartaría por tener el articulo corto.
_MINIMO_DOSIER = 2000
_MINIMO_DOSIER_SHORT = 1200


def _recopilatorio(casos: list[dict]) -> dict:
    """Several catalogue entries as one video.

    The title here is a placeholder: the script model writes the real one, and
    the niche's own titles say how - a COUNT and a superlative, never a list of
    the cases. What this carries is the list of cases, which the dossier stage
    reads to research each one separately."""
    nombres = [c["title"] for c in casos]
    return {
        "title": f"{len(nombres)} misterios de internet",
        "casos": nombres,
        "summary": "",
        # The first case's link is what marks the batch as processed, so a
        # compilation is never rebuilt from the same opening case.
        "link": casos[0]["link"],
        "published": "",
        "source_name": "Wikipedia",
    }


def _choose_and_prepare(forced_topic: str | None) -> tuple[dict | None, Path | None]:
    """Picks the case to make, gathers its sources and opens a working
    directory for it. Shared by the ordinary run and by a job that pauses to
    be narrated, so both choose the same way."""
    _stop_requested.clear()
    cleanup_finished_video_files()

    if forced_topic:
        # An explicitly named case skips both the catalogue and the picker: the
        # caller has already decided, and the point of asking for one by name
        # is usually to remake it.
        chosen = fetch_topic_by_term(forced_topic)
        candidates = [chosen] if chosen else []
    elif CONTENT_MODE == "topics":
        # Enough cases for a compilation, not one for a documentary.
        #
        # Measured across 1,494 videos: what works in this niche is several
        # cases in one video with the count in the title - "4 Most Disturbing
        # Internet Mysteries", "The 8 Strangest Ancient Constructions" - not a
        # single story told at length. One case is asked for when the caller
        # names it, which is how a single subject still gets made on purpose.
        candidates = fetch_candidate_topics(limit=CASOS_POR_VIDEO)
    else:
        candidates = fetch_candidate_news(limit=6)
    if not candidates:
        logger.info("No hay temas nuevos que procesar.")
        return None, None

    # Which story gets made matters more than how well it is made: a
    # procedural court filing and a story with a person in it are not worth
    # the same 60 seconds, and taking whichever headline came first made that
    # choice at random.
    if forced_topic or CONTENT_MODE == "topics":
        # No picker here. The picker exists to judge which of six headlines the
        # feed happened to push is worth making, and to refuse the ones the
        # channel must not touch. The catalogue is already curated and ordered,
        # so that judgement was made when it was written - and asking the model
        # to re-make it over three nine-thousand-character articles would cost
        # more than the script itself.
        news_item = candidates[0]
        if len(candidates) > 1:
            news_item = _recopilatorio(candidates)
    else:
        news_item = pick_best_story(candidates)
        if news_item is None:
            # The picker also enforces which stories the channel must not make,
            # so there is no safe default to fall back on here.
            logger.info("No se ha podido elegir noticia con garantias; no se genera nada.")
            return None, None
    logger.info("Procesando noticia: %s", news_item["title"])

    # El dosier cuesta varias llamadas a Wikipedia, asi que se construye para
    # el tema ELEGIDO y no para los candidatos que solo habia que ojear. Si
    # falla, se sigue con el extracto corto que ya traia el candidato: un
    # video con menos material es peor, pero es mejor que ninguno.
    if CONTENT_MODE == "topics":
        # One dossier per case. A compilation gives each case a couple of
        # minutes, so it needs the shape of the story and its best two or
        # three facts - not the forty thousand characters a single-subject
        # documentary lived on.
        partes = []
        for caso in news_item.get("casos") or [news_item["title"]]:
            try:
                d = research.build_dossier(caso)
            except Exception:
                logger.exception("No se pudo montar el dosier de %r.", caso)
                continue
            if d:
                # Cut on a source boundary, never mid-sentence: the sources
                # are labelled so the script can cross them, and one that
                # stops halfway reads as a document contradicting itself
                # rather than as one that ended.
                recortado = _trim_sources(d, _CHARS_POR_CASO)
                if len(recortado) < len(d):
                    logger.info(
                        "Caso %r recortado a %s de %s caracteres para el recopilatorio.",
                        caso, len(recortado), len(d))
                partes.append(f"########## CASO: {caso} ##########\n{recortado}")
        dosier = "\n\n".join(partes)
        if len(dosier) > len(news_item.get("summary") or ""):
            news_item = {**news_item, "summary": dosier}
        logger.info("Dosier del video: %s casos, %s caracteres.", len(partes), len(dosier))

        # El guardia que faltaba, y su ausencia costo una generacion entera.
        #
        # Wikipedia devolvio vacio para los cinco casos, el dosier quedo en
        # cero caracteres, y esto siguio adelante y mando a escribir un video
        # de seis minutos SIN UNA SOLA FUENTE. Un guion sin material no sale
        # corto ni falla: sale completo y entero inventado, porque es lo unico
        # que puede hacer el modelo cuando no le das nada. Y despues se paga
        # la narracion de eso.
        #
        # Un fallo de red no puede convertirse en un video falso. Si no hay
        # material, esto para aqui, antes de gastar un credito.
        if not partes:
            raise RuntimeError(
                "No he podido montar el dosier de NINGUNO de los casos, asi que "
                "el guion se lo inventaria entero. Paro aqui sin gastar nada. "
                "Mira los logs: ahora dicen por que falla Wikipedia."
            )
        minimo = _MINIMO_DOSIER_SHORT if variant == "short" else _MINIMO_DOSIER
        if len(dosier) < minimo:
            raise RuntimeError(
                f"Solo he reunido {len(dosier):,} caracteres de material en "
                f"{len(partes)} caso(s), que no da para un video sin rellenar. "
                "Paro aqui sin gastar nada.".replace(",", ".")
            )

    work_dir = Path(DATA_DIR) / f"job_{int(time.time())}"
    work_dir.mkdir(parents=True, exist_ok=True)

    return news_item, work_dir


def run_once(
    on_variant_done: Callable[[int], None] | None = None,
    variants: tuple[str, ...] = ("short", "long"),
    forced_topic: str | None = None,
) -> list[int]:
    """Picks the next unprocessed news item and generates the requested
    variants for it (both a vertical Short and a longer horizontal video by
    default), storing each as 'pending'. Calls on_variant_done(video_id)
    right after each variant finishes, so callers can notify/send it
    immediately instead of waiting for all of them to be done. Returns the
    new videos' ids (empty if there was no fresh news)."""
    _stop_requested.clear()
    cleanup_finished_video_files()

    news_item, work_dir = _choose_and_prepare(forced_topic)
    if news_item is None:
        return []

    video_ids = []
    for variant in variants:
        try:
            video_id = _generate_variant(news_item, variant, work_dir)
            resumen_coste = llm_usage.report_and_reset()
            if resumen_coste:
                logger.info("[%s] %s", variant, resumen_coste)
            video_ids.append(video_id)
            if on_variant_done is not None:
                on_variant_done(video_id)
        except GenerationStopped as exc:
            logger.info("Generacion detenida a peticion: %s", exc)
            shutil.rmtree(work_dir / variant, ignore_errors=True)
            break
        except Exception:
            # Don't let one variant's failure wipe out the other's already-finished
            # video: only the failed variant's own directory is cleaned up.
            logger.exception("Error generando la variante '%s'", variant)
            shutil.rmtree(work_dir / variant, ignore_errors=True)

    if video_ids:
        storage.mark_source_processed(news_item["link"], news_item.get("title", ""))
    else:
        shutil.rmtree(work_dir, ignore_errors=True)

    return video_ids
