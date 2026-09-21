import asyncio
import time
from io import BytesIO
import logging
import re
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, MessageHandler, filters)

from . import (ai_images, archivo, demanda, efemerides, fotos_propias, news_source, oficial,
               pipeline,
               real_photos, research, storage, tendencias, topic_source, tts,
               voice_align, voice_clone)
from .voice_align import AlignmentFailed
from .config import (
    CHANNEL_NAME,
    DATA_DIR,
    PIPELINE_INTERVAL_SECONDS,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TTS_LANGUAGE_CODE,
    TTS_VOICE_NAME,
    NARRATION_SOURCE,
    WIKI_LANG,
    DEMANDA_MINIMA,
)
from .pipeline import (
    cleanup_finished_video_files,
    interrupted_run_evidence,
    request_stop,
    prepare_voice_job,
    pending_voice_job,
    resume_voice_job,
    run_once,
    stop_requested as pipeline_stop_requested,
)
from .video_builder import make_preview
from .youtube_uploader import AutorizacionCaducada, upload_captions, upload_video

logger = logging.getLogger(__name__)

_VARIANT_LABELS = {"short": "🔹 SHORT (vertical)", "long": "🔸 VIDEO LARGO (horizontal)"}

# run_once()/upload_video() are blocking (ffmpeg subprocesses, network I/O).
# Running them directly inside an async handler would freeze the whole bot -
# no button presses or commands would be processed until they finished. They
# run in this executor instead, and this lock keeps two pipeline runs from
# overlapping (e.g. the scheduled job and a manual /generar at the same time).
_pipeline_lock = asyncio.Lock()

# Telegram's own ceiling is 50MB; stay clear of it so a file that measures just
# under does not fail on multipart overhead.
_PREVIEW_THRESHOLD_BYTES = 45 * 1024 * 1024

# A whole run (both variants) normally takes around three minutes. If it goes
# far past that, something is stuck rather than slow, and waiting longer will
# not help: an external call with no time limit of its own once froze the
# worker thread indefinitely, and because the lock above was still held, every
# later /generar was answered with "ya hay una generacion en curso" until the
# container was restarted. The stuck thread can't be killed from here, but
# giving up on it releases the lock so the bot stays usable.
# A six-minute video took sixteen minutes to build, most of it ffmpeg.
# Fifteen minutes of video is fifty scenes to render and a much longer
# join, so the old ceiling would have killed the run with the script and
# the narration already paid for - the most expensive possible moment to
# give up. The watchdogs inside video_builder are what catch a genuine
# hang; this is only the outer limit.
_PIPELINE_TIMEOUT_SECONDS = 50 * 60


# Telegram corta el pie de una foto o un video en 1024 caracteres, y no lo
# recorta el: rechaza el mensaje entero con "Message caption is too long".
#
# Paso de verdad, con un video ya hecho y pagado: la descripcion en ingles
# mas el bloque de creditos de las imagenes se paso del limite, el envio
# fallo, y el plan B - mandar solo la miniatura - fallo identicamente porque
# reutilizaba el mismo pie. El video existia entero en el disco y desde
# fuera parecia que la generacion se habia parado sin mas.
_PIE_MAXIMO = 1000


def _recorta_pie(texto: str) -> str:
    """El pie, recortado por un salto de linea si hace falta."""
    if len(texto) <= _PIE_MAXIMO:
        return texto
    corte = texto.rfind("\n", 0, _PIE_MAXIMO - 20)
    if corte < _PIE_MAXIMO // 2:
        corte = _PIE_MAXIMO - 20
    return texto[:corte].rstrip() + "\n\n[...]"


async def send_for_approval(bot, video_id: int) -> None:
    record = storage.get_video(video_id)
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Aprobar y subir", callback_data=f"approve:{video_id}"),
                InlineKeyboardButton("Rechazar", callback_data=f"reject:{video_id}"),
            ]
        ]
    )
    label = _VARIANT_LABELS.get(record["variant"], record["variant"])
    caption_completo = f"{label}\n*{record['title']}*\n\n{record['description']}"
    caption = _recorta_pie(caption_completo)

    # Send something watchable, not just its thumbnail: a video approved
    # without being seen is not approved at all, and that happened - a long
    # video went to YouTube on the strength of its thumbnail alone because it
    # was over Telegram's 50MB upload limit. Anything too big is re-encoded
    # smaller first; only if even that fails does the thumbnail stand in.
    video_path = Path(record["video_path"])
    to_send = video_path
    if video_path.stat().st_size > _PREVIEW_THRESHOLD_BYTES:
        loop = asyncio.get_running_loop()
        preview = await loop.run_in_executor(
            None, make_preview, video_path, video_path.with_name("preview.mp4")
        )
        if preview is not None:
            to_send = preview
            caption += "\n\n(Vista previa comprimida; a YouTube sube la version completa)"

    try:
        with open(to_send, "rb") as video_file, open(record["thumbnail_path"], "rb") as thumb_file:
            message = await bot.send_video(
                chat_id=TELEGRAM_CHAT_ID,
                video=video_file,
                thumbnail=thumb_file,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=keyboard,
                supports_streaming=True,
                write_timeout=120,
            )
    except Exception:
        logger.warning("No se pudo enviar el video %s a Telegram, se enviara solo la miniatura", video_id, exc_info=True)
        with open(record["thumbnail_path"], "rb") as thumbnail_file:
            message = await bot.send_photo(
                chat_id=TELEGRAM_CHAT_ID,
                photo=thumbnail_file,
                caption=caption + "\n\n(Video demasiado grande para previsualizar aqui)",
                parse_mode="Markdown",
                reply_markup=keyboard,
            )

    storage.set_telegram_message(video_id, str(TELEGRAM_CHAT_ID), str(message.message_id))

    # Si el pie se recorto, la descripcion entera va aparte: es lo que se sube
    # a YouTube y hay que poder leerla antes de aprobar.
    if len(caption_completo) > len(caption):
        try:
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=f"Descripcion completa del video {video_id}:\n\n{record['description']}"[:4000],
            )
        except Exception:
            logger.warning("No se pudo enviar la descripcion completa del video %s",
                           video_id, exc_info=True)


async def handle_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    action, video_id_str = query.data.split(":")
    video_id = int(video_id_str)
    record = storage.get_video(video_id)

    if record is None or record["status"] != "pending":
        await query.edit_message_caption(caption="Este video ya fue procesado anteriormente.")
        return

    label = _VARIANT_LABELS.get(record["variant"], record["variant"])

    if action == "reject":
        storage.set_status(video_id, "rejected")
        await asyncio.get_running_loop().run_in_executor(None, cleanup_finished_video_files)
        await query.edit_message_caption(caption=f"{label}\nRechazado: {record['title']}")
        return

    await query.edit_message_caption(caption=f"{label}\nSubiendo a YouTube: {record['title']}")
    loop = asyncio.get_running_loop()
    try:
        youtube_id, publish_at = await loop.run_in_executor(
            None,
            upload_video,
            Path(record["video_path"]),
            Path(record["thumbnail_path"]),
            record["title"],
            record["description"],
            record["tags"].split(","),
        )
        storage.set_status(video_id, "uploaded", youtube_id)

        if record["subtitle_path"]:
            try:
                await loop.run_in_executor(None, upload_captions, youtube_id, Path(record["subtitle_path"]))
            except Exception:
                # Not critical: the video is already live without a captions track.
                logger.exception("Error subiendo subtitulos para el video %s", video_id)

        # Only safe to delete the working files (video/thumbnail/subtitles)
        # now that every upload that needed them has already happened.
        await loop.run_in_executor(None, cleanup_finished_video_files)

        if publish_at is None:
            estado = "Publicado"
        else:
            # Shown in Spanish local time, which is what the user reads the
            # message in - publish_at itself is UTC.
            local = publish_at.astimezone(ZoneInfo("Europe/Madrid"))
            estado = f"Subido en privado, se publica solo a las {local.strftime('%H:%M')}"
        await query.edit_message_caption(
            caption=f"{label}\n{estado}: {record['title']}\nhttps://youtu.be/{youtube_id}"
        )
    except AutorizacionCaducada:
        # Esto no es un fallo de red que se arregle reintentando, asi que no se
        # dice "revisa los logs": se dice que hay que hacer. El video queda
        # pendiente, no fallido, porque no le pasa nada - el problema es el
        # permiso, y cuando se arregle se sube con /enviar.
        logger.error("Autorizacion de YouTube caducada al subir el video %s", video_id)
        await query.edit_message_caption(
            caption=(f"{label}\nLa autorizacion de YouTube ha caducado. El video esta "
                     f"hecho y guardado: {record['title']}"))
        await context.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=("*La autorizacion de YouTube ha caducado.* No se ha perdido nada.\n\n"
                  "1. En tu ordenador: `python -m scripts.authorize_youtube`\n"
                  "2. El token nuevo, a la variable `YOUTUBE_TOKEN_JSON` de Railway.\n"
                  "3. En Google Cloud, pantalla de consentimiento: ponla *En produccion*, "
                  "o vuelve a caducar en una semana.\n\n"
                  "Despues, /enviar y lo apruebas otra vez."),
            parse_mode="Markdown")
    except Exception:
        logger.exception("Error subiendo el video %s a YouTube", video_id)
        storage.set_status(video_id, "upload_failed")
        await query.edit_message_caption(caption=f"{label}\nError al subir: {record['title']}. Revisa los logs.")


async def _run_pipeline_and_notify(
    bot, variants: tuple[str, ...] = ("short", "long"), forced_topic: str | None = None
) -> None:
    loop = asyncio.get_running_loop()

    def on_variant_done(video_id: int) -> None:
        # run_once() executes in a worker thread (see run_in_executor below),
        # so sending straight away here would call async Telegram code off
        # the event loop. Hop back onto the loop instead, and block this
        # worker thread until it's actually sent so variants stay in order.
        future = asyncio.run_coroutine_threadsafe(send_for_approval(bot, video_id), loop)
        try:
            future.result()
        except Exception:
            logger.exception("Error enviando el video %s a Telegram", video_id)

    async with _pipeline_lock:
        pulso = asyncio.create_task(_latido(bot))
        try:
            video_ids = await asyncio.wait_for(
                loop.run_in_executor(None, run_once, on_variant_done, variants, forced_topic),
                timeout=_PIPELINE_TIMEOUT_SECONDS,
            )
            if pipeline_stop_requested():
                await bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=(
                        f"Generacion parada. {len(video_ids)} video(s) terminados antes de parar "
                        "siguen pendientes de tu aprobacion."
                        if video_ids
                        else "Generacion parada. No habia ningun video terminado todavia."
                    ),
                )
            elif not video_ids:
                await bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID, text="No hay noticias nuevas que procesar ahora mismo."
                )
        except asyncio.TimeoutError:
            logger.error(
                "El pipeline lleva mas de %s minutos sin terminar; se deja de esperar y se libera el bloqueo. "
                "El ultimo mensaje del log de antes de pararse dice en que paso se quedo colgado.",
                _PIPELINE_TIMEOUT_SECONDS // 60,
            )
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=(
                    f"La generacion lleva mas de {_PIPELINE_TIMEOUT_SECONDS // 60} minutos bloqueada, "
                    "asi que la doy por perdida. Puedes volver a lanzar /generar."
                ),
            )
        except Exception:
            logger.exception("Error ejecutando el pipeline de generacion de video")
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="Error generando el video, revisa los logs.")
        finally:
            # En el finally para que se calle tambien cuando la generacion
            # revienta, que es cuando mas raro seria seguir diciendo "sigo".
            pulso.cancel()


async def pipeline_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_pipeline_and_notify(context.bot)


_GENERATE_ARG_VARIANTS = {"s": ("short",), "v": ("long",)}

# What each variant costs to narrate with the clone, in credits, at one
# credit per character.
#
# Taken from the length the prompt actually ASKS FOR, which is where the
# first version of this went wrong: it quoted eleven thousand, the figure for
# the fifteen-minute video the market study argues for. The prompt still asks
# for three to five minutes, so the real bill is a quarter of that, and the
# warning was overstating the cost of every run by four times.
#
# If the long variant is ever lengthened to fifteen minutes, this moves to
# about 10,900 with it. The two numbers have to change together.
# The long video is no longer a fixed length - it is sized to how much
# material the case has - so this is a CEILING and says so, rather than
# a figure that would be wrong for every video that came in shorter.
_CREDITOS_POR_VARIANTE = {"short": 700, "long": 7500}


async def handle_generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    if _pipeline_lock.locked():
        await update.message.reply_text("Ya hay una generacion en curso, espera a que termine.")
        return

    # "/generar s" picks the variant; anything after it names the case to make,
    # e.g. "/generar s Costa Concordia". Naming one remakes it even if it has
    # been made before, which is how two versions of the same story can be put
    # side by side after a change to the writing.
    args = list(context.args or [])
    if args and args[0].lower() in _GENERATE_ARG_VARIANTS:
        variants = _GENERATE_ARG_VARIANTS[args.pop(0).lower()]
    else:
        variants = ("short", "long")
    forced_topic = " ".join(args).strip() or None
    label = {"short": "el Short", "long": "el video largo"}.get(
        variants[0] if len(variants) == 1 else "", "el Short y el video largo"
    )
    sobre = f" sobre {forced_topic}" if forced_topic else ""
    if NARRATION_SOURCE == "clon":
        # Checked before anything is written. Without it the failure lands
        # after the script has been paid for and the images fetched, which
        # wastes the expensive half of the run to discover something knowable
        # in advance.
        voice_id, modelo, _ = voice_clone.ajustes_elegidos()
        if not voice_id:
            await update.message.reply_text(
                "Esta puesto NARRATION_SOURCE=clon pero no hay ninguna voz clonada. "
                "Manda /clon primero, o quita la variable para volver al TTS."
            )
            return
        # Costed per variant rather than with one number: a Short is five or
        # six sentences and quoting a long video's bill at it reads as though
        # every run costs the same, which is the figure somebody would budget
        # with.
        coste = " + ".join(
            f"{'el Short' if v == 'short' else 'el largo'} "
            f"{'hasta ' if v == 'long' else '~'}{_CREDITOS_POR_VARIANTE[v]:,}"
            .replace(",", ".")
            for v in variants
        )
        await update.message.reply_text(
            f"Generando {label}{sobre} con tu voz clonada (`{modelo}`).\n"
            f"Creditos estimados: {coste}. Tardara unos minutos...",
            parse_mode="Markdown",
        )
        # Same reasoning as the ordinary path below: not awaited, so the bot
        # keeps answering while the video builds.
        context.application.create_task(
            _run_pipeline_and_notify(context.bot, variants, forced_topic))
        return
    if NARRATION_SOURCE == "voz":
        await update.message.reply_text(
            f"Escribiendo el guion de {label}{sobre}. Cuando este te lo mando para que lo leas."
        )
        context.application.create_task(
            _prepare_and_send_script(context.bot, variants[0], forced_topic)
        )
        return
    await update.message.reply_text(f"Generando {label}{sobre}, tardara unos minutos...")
    # Deliberately NOT awaited. python-telegram-bot handles updates one at a
    # time by default (max_concurrent_updates=1), so awaiting the generation
    # here froze the whole bot for as long as it ran: /vertex, /reset and -
    # worse - the approve and reject buttons on a Short that had already been
    # sent all sat unprocessed in the queue until the long video finished.
    # Running it as a task lets the handler return now and the bot keep
    # answering; _pipeline_lock still stops two generations overlapping.
    context.application.create_task(_run_pipeline_and_notify(context.bot, variants, forced_topic))


_LATIDO_SEGUNDOS = 180


async def _latido(bot) -> None:
    """Señal de vida cada tres minutos mientras se genera.

    Ella penso que una generacion se habia muerto, y con razon: entre el paso
    5 y el 7 de un largo el bot se calla diez minutos - las transiciones de un
    video de siete minutos son varias pasadas de ffmpeg de dos o tres minutos
    cada una - y desde fuera eso es igual que un cuelgue.

    Va aqui y no en el pipeline a proposito: asi cubre TODAS las esperas
    largas, incluidas las que estan dentro de un paso y no entre dos, que son
    justo las que asustan.
    """
    try:
        while True:
            await asyncio.sleep(_LATIDO_SEGUNDOS)
            paso = pipeline.ESTADO.get("texto") or "trabajando"
            minutos = int((time.time() - float(pipeline.ESTADO.get("desde") or 0)) // 60)
            cuanto = f", {minutos} min en este paso" if minutos >= 2 else ""
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID,
                                   text=f"Sigo: {paso}{cuanto}.")
    except asyncio.CancelledError:
        raise
    except Exception:
        # El latido no puede tumbar una generacion por no poder avisar.
        logger.warning("El latido ha fallado; la generacion sigue.", exc_info=True)


async def _prepare_and_send_script(bot, variant: str, forced_topic: str | None) -> None:
    """Writes the script and sends it to be read aloud."""
    loop = asyncio.get_running_loop()
    async with _pipeline_lock:
        try:
            job = await loop.run_in_executor(None, prepare_voice_job, variant, forced_topic)
        except Exception:
            logger.exception("Error preparando el guion para narrar")
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID,
                                   text="Ha fallado la escritura del guion. Mira los logs.")
            return
    if job is None:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="No hay temas nuevos que procesar.")
        return

    minutos = job["palabras"] / voice_align._PALABRAS_POR_MINUTO
    # The script goes as a file rather than a message: Telegram splits a long
    # message at 4096 characters wherever it lands, and a narration cut in
    # half mid-sentence cannot be read from. reading_script already carries
    # its own heading and its legend of marks, so nothing is prepended here.
    texto = job["narration"]
    await bot.send_document(
        chat_id=TELEGRAM_CHAT_ID,
        document=BytesIO(texto.encode("utf-8")),
        filename=f"guion_{job['variant']}.txt",
        caption=(f"Guion listo: *{job['title']}*\n\n"
                 f"{job['palabras']} palabras, unos {minutos:.0f} minutos.\n"
                 "Grabalo del tiron y mandame el audio por aqui."),
        parse_mode="Markdown",
    )


def _partes_grabadas(job_file: Path) -> list[Path]:
    """The takes received so far, in the order they were sent."""
    return sorted(job_file.parent.glob("narracion_*.audio"))


def _resumen_partes(partes: list[Path]) -> str:
    total = sum(voice_align._probe_duration(p) for p in partes)
    # Integer division, not a rounded quotient: 36 seconds formatted with
    # total/60 rounds to 1 and reads back as "1 min 36 s".
    return (f"{len(partes)} parte{'s' if len(partes) != 1 else ''}, "
            f"{int(total // 60)} min {int(total % 60):02d} s")


async def handle_narration_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """An audio file arrives: one more part of whatever script is waiting.

    Nothing is built on arrival. Seventeen minutes is not read in one breath,
    so the parts pile up until /listo says the reading is finished - which
    also means a fluffed section costs that section and not the whole take."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    msg = update.message
    fichero = msg.audio or msg.voice or msg.document
    job_file = pending_voice_job()
    if job_file is None:
        # No script is waiting, so this audio is not narration. Rather than
        # rejecting it, it is kept as a reference a clone can be built from -
        # which is the other thing audio gets sent here for.
        #
        # Kept ALONGSIDE the previous ones, not over them. A clone that came
        # back wrong is answered by sending more voice, and a single fixed
        # filename turned that into replacing one sample with another: the
        # clone would look unchanged and the extra recording would have been
        # wasted without anything saying so.
        ya_tenia = len(_referencias())
        destino = Path(DATA_DIR) / f"referencia_{ya_tenia + 1:02d}.audio"
        tg_file = await context.bot.get_file(fichero.file_id)
        await tg_file.download_to_drive(custom_path=str(destino))
        muestras = _referencias()
        total = sum(voice_align._probe_duration(m) for m in muestras)
        await msg.reply_text(
            f"No hay ningun guion esperando, asi que guardo este audio "
            f"({voice_align._probe_duration(destino):.0f}s) como referencia de tu voz.\n\n"
            f"Llevas {len(muestras)} muestra{'s' if len(muestras) != 1 else ''}, "
            f"{int(total // 60)} min {int(total % 60):02d} s en total.\n\n"
            "Manda /clon y rehago la voz con todas."
        )
        return
    siguiente = len(_partes_grabadas(job_file)) + 1
    destino = job_file.parent / f"narracion_{siguiente:02d}.audio"
    tg_file = await context.bot.get_file(fichero.file_id)
    await tg_file.download_to_drive(custom_path=str(destino))

    partes = _partes_grabadas(job_file)
    await msg.reply_text(
        f"Parte {siguiente} guardada. Llevas {_resumen_partes(partes)}.\n\n"
        "Manda la siguiente cuando quieras, /rehacer si esa ultima no te ha gustado, "
        "o /listo cuando hayas terminado el guion."
    )


async def handle_redo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/rehacer - throws away the last part, to be recorded again."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    job_file = pending_voice_job()
    partes = _partes_grabadas(job_file) if job_file else []
    if not partes:
        await update.message.reply_text("No hay ninguna parte grabada que rehacer.")
        return
    partes[-1].unlink(missing_ok=True)
    quedan = _partes_grabadas(job_file)
    await update.message.reply_text(
        f"Borrada la parte {len(partes)}. "
        + (f"Quedan {_resumen_partes(quedan)}. Manda esa parte otra vez."
           if quedan else "No queda ninguna: empieza por el principio del guion.")
    )


async def handle_done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/listo - the reading is finished: join the parts and build the video."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    job_file = pending_voice_job()
    if job_file is None:
        await update.message.reply_text("No hay ningun guion esperando narracion.")
        return
    partes = _partes_grabadas(job_file)
    if not partes:
        await update.message.reply_text("No me has mandado ninguna grabacion todavia.")
        return
    if _pipeline_lock.locked():
        await update.message.reply_text("Espera, que hay algo generandose ahora mismo.")
        return

    await update.message.reply_text(
        f"{_resumen_partes(partes)}. Uniendo, alineando con el guion y montando el video..."
    )
    loop = asyncio.get_running_loop()

    async def trabajo():
        async with _pipeline_lock:
            try:
                grabacion = await loop.run_in_executor(
                    None, voice_align.join_parts, partes, job_file.parent / "narracion.m4a"
                )
                video_id = await loop.run_in_executor(
                    None, resume_voice_job, job_file, grabacion
                )
            except AlignmentFailed as exc:
                # The parts are kept: the script is still waiting, so the fix
                # is to re-send whichever part went wrong, not to record the
                # whole thing again.
                await context.bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=f"{exc}\n\nTus grabaciones siguen guardadas. Puedes /rehacer la ultima parte.",
                )
                return
            except Exception:
                logger.exception("Error montando el video con la narracion grabada")
                await context.bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID, text="Ha fallado el montaje. Mira los logs.")
                return
        await send_for_approval(context.bot, video_id)

    context.application.create_task(trabajo())


# Instant cloning does not keep improving with more audio - a couple of
# minutes is where it lands, and past that the upload is slow for nothing. The
# cap exists so that sending a whole seventeen-minute narration as reference
# does not turn /clon into a ten-minute upload, and what it leaves out is said
# out loud rather than dropped quietly.
_MAX_SEGUNDOS_MUESTRA = 300


def _referencias() -> list[Path]:
    """Every reference recording sent so far, oldest first."""
    carpeta = Path(DATA_DIR)
    antigua = carpeta / "referencia_voz.audio"
    if antigua.exists():
        # The first version of this kept one sample under a fixed name. It is
        # renamed into the numbered series rather than ignored: it is a real
        # recording, and it was the reference the first clone was made from.
        primera = carpeta / "referencia_01.audio"
        if not primera.exists():
            antigua.rename(primera)
        else:
            antigua.unlink()
    return sorted(carpeta.glob("referencia_[0-9]*.audio"))


def _muestras_para_clonar(muestras: list[Path]) -> tuple[list[Path], float]:
    """The samples the clone is built from, newest first until the cap."""
    elegidas: list[Path] = []
    total = 0.0
    for muestra in reversed(muestras):
        duracion = voice_align._probe_duration(muestra)
        if elegidas and total + duracion > _MAX_SEGUNDOS_MUESTRA:
            continue
        elegidas.append(muestra)
        total += duracion
    return sorted(elegidas), total


async def handle_clone_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/clon - rebuilds the voice from every sample and compares the models.

    The first clone came back sounding nothing like her and phrasing badly,
    which is two separate faults: timbre comes from the samples, intonation
    comes from the model. So this does both at once - the voice is rebuilt
    whenever new samples have arrived, and the test phrase comes back once per
    candidate model, because no amount of reasoning decides which one sounds
    right and listening to three takes a minute."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    muestras = _referencias()
    if not muestras:
        await update.message.reply_text(
            "Primero mandame un audio tuyo (1-2 minutos limpios es lo ideal) y lo guardo "
            "como referencia. Luego vuelve a mandar /clon."
        )
        return

    texto = " ".join(context.args).strip() or voice_clone.FRASE_DE_PRUEBA
    usadas, segundos = _muestras_para_clonar(muestras)
    estado = voice_clone.estado_voz()
    rehacer = estado.get("muestras") != len(usadas)
    aviso = (
        f"{'Rehaciendo' if rehacer else 'Usando'} la voz con "
        f"{len(usadas)} muestra{'s' if len(usadas) != 1 else ''} "
        f"({int(segundos // 60)} min {int(segundos % 60):02d} s)"
    )
    if len(usadas) < len(muestras):
        aviso += f", de las {len(muestras)} que tengo (el resto sobra para clonar)"
    await update.message.reply_text(aviso + ".\nProbando cada modelo. Tarda un rato...")

    loop = asyncio.get_running_loop()

    async def trabajo():
        try:
            voice_id = estado.get("voice_id")
            if rehacer:
                if voice_id:
                    # The slot is freed first: instant cloning spends a voice
                    # slot rather than credits, and rebuilding without this
                    # leaks one slot per attempt until the account is full.
                    await loop.run_in_executor(None, voice_clone.borrar_voz, voice_id)
                voice_id = await loop.run_in_executor(
                    None, voice_clone.crear_voz, f"{CHANNEL_NAME} (voz propia)", usadas
                )
                voice_clone.guardar_estado_voz(voice_id=voice_id, muestras=len(usadas))
            modelos = await loop.run_in_executor(None, voice_clone.modelos_para_probar)
        except voice_clone.CloneError as exc:
            await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=str(exc))
            return
        except Exception:
            logger.exception("Error clonando la voz")
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID, text="Ha fallado la clonacion. Mira los logs.")
            return

        enviados = 0
        for modelo in modelos:
            destino = Path(DATA_DIR) / f"prueba_clon_{modelo}.mp3"
            try:
                await loop.run_in_executor(
                    None, voice_clone.sintetizar, voice_id, texto, destino, modelo
                )
            except voice_clone.CloneError as exc:
                # One model refusing is not the others failing: a model can be
                # off this plan, and saying which is more useful than stopping.
                await context.bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID, text=f"{modelo}: {exc}")
                continue
            except Exception:
                logger.exception("Error sintetizando con %s", modelo)
                continue
            with open(destino, "rb") as audio:
                await context.bot.send_audio(
                    chat_id=TELEGRAM_CHAT_ID, audio=audio, title=modelo,
                    caption=f"Modelo: `{modelo}`", parse_mode="Markdown",
                )
            enviados += 1

        if not enviados:
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text="Ningun modelo ha devuelto audio. Los mensajes de arriba dicen por que.")
            return
        await context.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=(f"{enviados} version{'es' if enviados != 1 else ''} de la misma frase, "
                  "misma voz, distinto modelo.\n\n"
                  "Dime cual se acerca mas y si alguna entona bien. Si ninguna te vale, "
                  "el clon instantaneo no da para mas y hay que decidir otra cosa - "
                  "te lo explico cuando me lo digas."),
        )

    context.application.create_task(trabajo())


# Short names, because these get typed on a phone.
_ALIAS_MODELO = {
    "v2": "eleven_multilingual_v2",
    "v3": "eleven_v3",
    "turbo": "eleven_turbo_v2_5",
    "flash": "eleven_flash_v2_5",
}


async def handle_tone_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/tono [v2|v3|turbo] - same voice, same model, four different settings.

    The model comparison split the problem instead of solving it: the version
    that sounded most like her was the flattest, and the one that phrased best
    sounded least like her. Timbre and phrasing are separate sliders, so the
    question is no longer which model but whether the model that already has
    her timbre can be pushed into phrasing properly - and whether the one that
    phrases properly can be pushed into her timbre. Same experiment either
    way, run on whichever model is named."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    estado = voice_clone.estado_voz()
    voice_id = estado.get("voice_id")
    if not voice_id:
        await update.message.reply_text(
            "Todavia no hay voz clonada. Manda /clon primero."
        )
        return

    args = list(context.args)
    modelo = voice_clone._MODEL
    if args and (args[0] in _ALIAS_MODELO or args[0].startswith("eleven_")):
        modelo = _ALIAS_MODELO.get(args[0], args[0])
        args = args[1:]
    texto = " ".join(args).strip() or voice_clone.FRASE_DE_ENTONACION

    # A second word picks the finer sweep around the preset she already chose,
    # rather than the coarse one that found it.
    presets = voice_clone.AJUSTES_PRESETS
    if args and args[0] in ("fino", "afinar"):
        presets = voice_clone.AJUSTES_FINOS
        args = args[1:]
    coste = int(voice_clone.creditos_estimados(texto, modelo) * len(presets))
    await update.message.reply_text(
        f"{len(presets)} versiones con `{modelo}`, la misma voz, distintos ajustes.\n"
        f"Unos {coste} creditos en total. Tarda un rato...",
        parse_mode="Markdown",
    )

    loop = asyncio.get_running_loop()

    async def trabajo():
        enviados = 0
        for nombre, ajustes in presets.items():
            destino = Path(DATA_DIR) / f"tono_{modelo}_{nombre}.mp3"
            try:
                await loop.run_in_executor(
                    None, voice_clone.sintetizar, voice_id, texto, destino, modelo, ajustes
                )
            except voice_clone.CloneError as exc:
                await context.bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID, text=f"{nombre}: {exc}")
                continue
            except Exception:
                logger.exception("Error sintetizando el preset %s", nombre)
                continue
            with open(destino, "rb") as audio:
                await context.bot.send_audio(
                    chat_id=TELEGRAM_CHAT_ID, audio=audio, title=nombre,
                    caption=(f"*{nombre}*\n"
                             f"soltura {1 - ajustes['stability']:.0%} · "
                             f"parecido {ajustes['similarity_boost']:.0%} · "
                             f"expresividad {ajustes['style']:.0%}"),
                    parse_mode="Markdown",
                )
            enviados += 1

        if not enviados:
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text="Ningun ajuste ha devuelto audio. Los mensajes de arriba dicen por que.")
            return
        await context.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=("Dime cual entona mejor Y si alguno pierde parecido contigo. "
                  "Si el de *parecido-al-maximo* suena bien, la expresividad estaba "
                  "trabajando en contra y la respuesta es mas simple de lo que parecia.\n\n"
                  "Prueba tambien el otro modelo: /tono v2 o /tono v3."),
            parse_mode="Markdown",
        )

    context.application.create_task(trabajo())


async def handle_use_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/usar <modelo> <preset> - records which combination won the listening.

    The comparison happens in Telegram, on one day, by ear. The videos get
    built somewhere else, on another day, by the pipeline. Without somewhere
    to write the answer down, every video would go out at whatever the code's
    default happened to be and the whole afternoon of listening would decide
    nothing."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    presets = {**voice_clone.AJUSTES_PRESETS, **voice_clone.AJUSTES_FINOS}
    # No two presets may share a name across the two sweeps: they carry
    # different numbers, and picking by name would then be picking at random.
    assert len(presets) == len(voice_clone.AJUSTES_PRESETS) + len(voice_clone.AJUSTES_FINOS)
    args = [a.strip().lower() for a in context.args]
    modelo = next((_ALIAS_MODELO.get(a, a) for a in args
                   if a in _ALIAS_MODELO or a.startswith("eleven_")), None)
    preset = next((a for a in args if a in presets), None)

    if not modelo and not preset:
        voice_id, actual_modelo, actual_ajustes = voice_clone.ajustes_elegidos()
        await update.message.reply_text(
            f"Ahora mismo los videos se narrarian con `{actual_modelo}`:\n"
            f"soltura {1 - actual_ajustes['stability']:.0%} · "
            f"parecido {actual_ajustes['similarity_boost']:.0%} · "
            f"expresividad {actual_ajustes['style']:.0%}\n\n"
            "Para cambiarlo: /usar v3 muy-suelto\n"
            f"Presets: {', '.join(presets)}",
            parse_mode="Markdown",
        )
        return

    cambios = {}
    if modelo:
        cambios["model"] = modelo
    if preset:
        cambios["preset"] = preset
    voice_clone.guardar_estado_voz(**cambios)
    _, modelo_final, ajustes = voice_clone.ajustes_elegidos()
    await update.message.reply_text(
        f"Hecho. Los videos se narraran con `{modelo_final}`:\n"
        f"soltura {1 - ajustes['stability']:.0%} · "
        f"parecido {ajustes['similarity_boost']:.0%} · "
        f"expresividad {ajustes['style']:.0%}\n\n"
        "Pon NARRATION_SOURCE=clon en Railway y /generar usara esta voz.",
        parse_mode="Markdown",
    )


# Roughly what a minute of narration costs in words, at synthesis pace with
# the pauses taken out. Used to turn a dossier's size into the only question
# worth asking about it: is there enough here to talk for fifteen minutes.
_PALABRAS_POR_MINUTO_SINTESIS = 132


async def handle_dossier_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/dosier <tema> - builds the research for a case and measures it.

    Costs nothing and generates nothing. The question it answers is whether
    there is enough material for a long video, which up to now has only been
    answerable by writing one and seeing whether it padded. A dossier that is
    thin says so before the script does."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    tema = " ".join(context.args).strip()
    if not tema:
        await update.message.reply_text("Dime de que caso: /dosier Gusano Morris")
        return
    await update.message.reply_text(f"Montando el dosier de *{tema}*...", parse_mode="Markdown")
    loop = asyncio.get_running_loop()

    async def trabajo():
        try:
            dosier = await loop.run_in_executor(None, research.build_dossier, tema)
        except Exception:
            logger.exception("Error montando el dosier de %r", tema)
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID, text="No he podido montar el dosier. Mira los logs.")
            return
        if not dosier:
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=f"Wikipedia no tiene articulo para «{tema}», asi que no hay dosier. "
                     "Prueba con el nombre exacto del articulo.")
            return

        # Sources are labelled, so they can be counted and sized separately -
        # a dossier that is one huge article and nine scraps is a different
        # thing from ten solid ones, and the total hides which it is.
        trozos = re.split(r"(?m)^===== (FUENTE \d+ · .*?) =====$", dosier)
        cabeceras = trozos[1::2]
        cuerpos = [t.strip() for t in trozos[2::2]]
        palabras = len(dosier.split())
        minutos = palabras / _PALABRAS_POR_MINUTO_SINTESIS

        lineas = [f"*{tema}*", f"{len(cabeceras)} fuentes · {len(dosier):,} caracteres · "
                  f"{palabras:,} palabras".replace(",", ".")]
        for cabecera, cuerpo in zip(cabeceras, cuerpos):
            nombre = cabecera.split(" · ", 1)[-1]
            lineas.append(f"  · {nombre[:60]} — {len(cuerpo.split()):,} palabras".replace(",", "."))
        lineas.append("")
        # The comparison that matters. Material is not narration: a script
        # keeps a fraction of what it reads, because a dossier repeats itself
        # across languages and carries a lot that is not story.
        lineas.append(
            f"Da para hablar {minutos:.0f} min SI se narrara entero, que no se narra: "
            f"un guion se queda con una parte de lo que lee."
        )
        lineas.append(
            f"Para 15 min hacen falta ~{15 * _PALABRAS_POR_MINUTO_SINTESIS:,} palabras "
            f"de guion.".replace(",", ".")
        )
        await context.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID, text="\n".join(lineas), parse_mode="Markdown")

    context.application.create_task(trabajo())


async def handle_catalogue_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/catalogo - comprueba que los 58 casos existen de verdad.

    Los titulos del catalogo se escribieron de memoria, y un titulo mal
    puesto no falla de forma ruidosa: falla despues, cuando ya se ha pagado
    el guion, y devuelve un dosier vacio o - peor - el articulo equivocado.
    "Silk Road" en español es la Ruta de la Seda.

    Esto pregunta por los cincuenta y ocho de golpe (la API acepta cincuenta
    titulos por peticion, o sea dos llamadas) y para cada uno que falte
    propone lo que Wikipedia si tiene con ese nombre. Propone, no corrige:
    elegir solo el primer resultado es justo como se acaba narrando la ruta
    comercial del siglo XIV."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    await update.message.reply_text(
        f"Comprobando los {len(topic_source.CATALOGUE)} casos del catalogo...")
    loop = asyncio.get_running_loop()

    async def trabajo():
        def comprobar():
            titulos = list(topic_source.CATALOGUE)
            estado = research.existen(WIKI_LANG, titulos)
            faltan = [t for t in titulos if estado.get(t) is False]
            # Only the ones that are definitely missing get a search; a title
            # left out of `estado` was never answered for, and guessing a
            # replacement for it would be inventing a problem.
            sugerencias = {t: research.buscar(WIKI_LANG, t) for t in faltan}
            sin_respuesta = [t for t in titulos if t not in estado]
            return titulos, faltan, sugerencias, sin_respuesta

        try:
            titulos, faltan, sugerencias, sin_respuesta = await loop.run_in_executor(
                None, comprobar)
        except Exception:
            logger.exception("Error comprobando el catalogo")
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID, text="No he podido comprobar el catalogo. Mira los logs.")
            return

        buenos = len(titulos) - len(faltan) - len(sin_respuesta)
        lineas = [f"*Catalogo: {buenos} de {len(titulos)} existen*"]
        if sin_respuesta:
            lineas.append(f"({len(sin_respuesta)} sin respuesta de Wikipedia, no comprobados)")
        if not faltan:
            lineas.append("\nNinguno mal. El catalogo esta limpio.")
        else:
            lineas.append(f"\n{len(faltan)} NO existen:")
            for t in faltan:
                opciones = sugerencias.get(t) or []
                if opciones:
                    lineas.append(f"  ✗ «{t}»\n      Wikipedia tiene: {' · '.join(opciones)}")
                else:
                    lineas.append(f"  ✗ «{t}»\n      Wikipedia no encuentra nada parecido.")

        # Telegram cuts a message at 4096 characters, and a silent cut here
        # would hide exactly the titles this command exists to show.
        texto = "\n".join(lineas)
        for i in range(0, len(texto), 3500):
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID, text=texto[i:i + 3500], parse_mode="Markdown")

    context.application.create_task(trabajo())


async def handle_calendar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/calendario [dias] - que aniversarios vienen y cuando publicarlos.

    No gasta cuota ni creditos: es una lista con fechas. Existe porque la
    ventaja de este canal frente a uno de noticias no es la velocidad, es que
    puede saber con un año de antelacion lo que la gente va a buscar."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    dias = next((int(a) for a in (context.args or []) if a.isdigit()), efemerides.VENTANA)
    proximas = efemerides.proximas(dias=dias)
    if not proximas:
        await update.message.reply_text(
            f"No hay ningun aniversario en los proximos {dias} dias.\n"
            "Prueba con mas margen: /calendario 60")
        return

    lineas = [f"*Aniversarios en {dias} dias*", ""]
    for e in proximas:
        cuando = "HOY o ya pasado" if e["urgente"] else f"publicar el {e['publicar']:%d/%m}"
        lineas.append(
            f"  *{e['titulo']}*\n"
            f"     {e['aniversario']:%d/%m} · {e['cumple']} aniversario · "
            f"faltan {e['faltan']} dias · {cuando}")
    lineas += ["", "El calendario propone; la demanda decide. Antes de lanzar:",
               f"/demanda {proximas[0]['titulo']}"]
    await update.message.reply_text("\n".join(lineas[:60]), parse_mode="Markdown")


async def handle_trending_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/tendencias - que se esta viendo hoy en YouTube España, noticias.

    Cuesta UNA unidad de cuota, no cien: es otra metrica distinta de las
    busquedas, asi que funciona incluso los dias en que las busquedas se han
    agotado. Y ya trae las visitas, o sea que es la forma barata de saber que
    le importa hoy a alguien antes de decidir nada.

    Marca ademas lo que esta en tendencias y no aparece en tus feeds: si lo
    mas visto del dia nunca llega por RSS, el problema no es como se elige el
    tema, es que no llega."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    await update.message.reply_text("Mirando que se ve hoy...")
    loop = asyncio.get_running_loop()

    async def trabajo():
        try:
            hoy = await loop.run_in_executor(None, tendencias.lo_que_se_ve_hoy)
            candidatos = await loop.run_in_executor(None, news_source.fetch_candidate_news, 10)
        except tendencias.SinClave as exc:
            await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=str(exc))
            return
        except Exception:
            logger.exception("Error leyendo las tendencias")
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID, text="No he podido leer las tendencias. Mira los logs.")
            return

        if not hoy:
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID, text="YouTube no me ha devuelto tendencias ahora mismo.")
            return

        lineas = ["*Lo mas visto hoy* · noticias, España", ""]
        for v in hoy[:8]:
            lineas.append(f"  {v['vistas']:,} · {v['titulo'][:58]}".replace(",", "."))

        ordenados = tendencias.ordenar_por_tendencia(list(candidatos), hoy)
        con_tiron = [c for c in ordenados if c.get("vistas_tendencia", 0) > 0]
        lineas += ["", "*De tus noticias, las que tienen tiron hoy:*"]
        if con_tiron:
            for c in con_tiron[:5]:
                lineas.append(
                    f"  {c['vistas_tendencia']:,} · {c['title'][:56]}".replace(",", "."))
        else:
            lineas.append("  Ninguna. Hoy tus feeds no traen nada de lo que se esta viendo.")

        huerfanos = tendencias.sin_cubrir(candidatos, hoy)
        if huerfanos:
            lineas += ["", "*En tendencias y NO en tus feeds:*"]
            for h in huerfanos[:4]:
                lineas.append(f"  {h['vistas']:,} · {h['titulo'][:56]}".replace(",", "."))
            lineas.append("\nSi esto pasa siempre, el problema son las fuentes, no la eleccion.")

        texto = "\n".join(lineas)
        for i in range(0, len(texto), 3500):
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID, text=texto[i:i + 3500], parse_mode="Markdown")

    context.application.create_task(trabajo())


# Un nombre abierto, y las fotos que lleguen detras van a el sin tener que
# escribirlo cada vez. Existe por dos motivos: cargar las cuatro caras de un
# caso de una sentada, y porque cuando se mandan varias fotos juntas Telegram
# solo le pone pie a LA PRIMERA - las demas llegan sin nada y se perdian.
_FOTOS_PARA: dict[str, object] = {"nombre": "", "hasta": 0.0}
_MINUTOS_ABIERTO = 15


def _nombre_abierto() -> str:
    if _FOTOS_PARA["nombre"] and time.time() < float(_FOTOS_PARA["hasta"]):
        return str(_FOTOS_PARA["nombre"])
    return ""


def _abrir_para(nombre: str) -> None:
    _FOTOS_PARA["nombre"] = nombre
    _FOTOS_PARA["hasta"] = time.time() + _MINUTOS_ABIERTO * 60


async def handle_photos_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/fotos - las imagenes que has puesto tu, y como quitarlas.

    /fotos                 las lista
    /fotos de <nombre>     abre ese nombre: las fotos que mandes van ahi
    /fotos fin             lo cierra
    /fotos borrar <nombre> quita las de esa persona
    Para añadir una suelta: mandamela con el nombre en el pie."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    args = list(context.args or [])
    if args and args[0].lower() in ("de", "para"):
        nombre = " ".join(args[1:]).strip()
        if not nombre:
            await update.message.reply_text("Dime de quien: /fotos de Rosario Porto")
            return
        _abrir_para(nombre)
        await update.message.reply_text(
            f"Venga, mandame las de *{nombre}*. Todas las fotos que llegue"
            f"n ahora van a ese nombre, sin pie ni nada.\n\n"
            f"Cuando cambies de persona: /fotos de <otro nombre>. Para cerrar: "
            f"/fotos fin.", parse_mode="Markdown")
        return
    if args and args[0].lower() in ("fin", "basta", "cerrar"):
        abierto = _nombre_abierto()
        _FOTOS_PARA["nombre"] = ""
        await update.message.reply_text(
            f"Cerrado «{abierto}»." if abierto else "No habia ningun nombre abierto.")
        return
    if args and args[0].lower() in ("borrar", "quitar"):
        nombre = " ".join(args[1:]).strip()
        if not nombre:
            await update.message.reply_text("Dime de quien: /fotos borrar Rosario Porto")
            return
        n = fotos_propias.borrar(nombre)
        await update.message.reply_text(
            f"Borradas {n} foto(s) de «{nombre}»." if n else f"No tenia ninguna de «{nombre}».")
        return

    guardadas = fotos_propias.listar()
    if not guardadas:
        await update.message.reply_text(
            "No tienes ninguna foto puesta.\n\n"
            "Para añadir una: mandamela con el nombre en el pie, por ejemplo "
            "«Rosario Porto». A partir de ahi sale en todos los videos donde "
            "se la nombre, por delante de lo que encuentre yo.")
        return
    lineas = ["*Tus fotos*", ""]
    for nombre, cuantas in guardadas:
        lineas.append(f"  · {nombre} ({cuantas})")
    lineas += ["", "Para añadir: mandame la foto con el nombre en el pie.",
               "Para quitar: /fotos borrar <nombre>"]
    await update.message.reply_text("\n".join(lineas), parse_mode="Markdown")


async def handle_incoming_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Una foto con un nombre en el pie se guarda para ese nombre."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    nombre = (update.message.caption or "").strip() or _nombre_abierto()
    if not nombre:
        await update.message.reply_text(
            "Ponle el nombre en el pie de la foto y te la guardo, por ejemplo "
            "«Rosario Porto». Asi la uso en todos los videos donde se la nombre.\n\n"
            "Si vas a mandar varias de la misma persona, dime antes "
            "/fotos de <nombre> y me las mandas seguidas.")
        return
    # El pie manda, y ademas deja el nombre abierto: cuando se mandan varias
    # juntas solo la primera trae pie, asi que el resto del album cae aqui.
    _abrir_para(nombre)

    fichero = update.message.photo[-1] if update.message.photo else update.message.document
    try:
        descarga = await fichero.get_file()
        datos = bytes(await descarga.download_as_bytearray())
    except Exception:
        logger.exception("No se ha podido descargar la foto de %r", nombre)
        await update.message.reply_text("No he podido descargarla. Prueba otra vez.")
        return

    extension = ".jpg"
    if getattr(fichero, "file_name", None) and "." in fichero.file_name:
        extension = "." + fichero.file_name.rsplit(".", 1)[-1].lower()
    ruta = await asyncio.get_running_loop().run_in_executor(
        None, fotos_propias.guardar, nombre, datos, extension)
    total = next((c for n, c in fotos_propias.listar()
                  if n.lower() == nombre.lower()), 1)
    await update.message.reply_text(
        f"Guardada para «{nombre}» ({total} en total). "
        "Se usara en todos los videos donde se la nombre, por delante de lo "
        "que encuentre yo por mi cuenta.")


_OTRO_COMANDO = re.compile(r"\s*/([a-zA-Z_]+)\s*")


def _varios_temas(args, comando: str) -> tuple[list[str], list[str]]:
    """Separa "A /oficial B /oficial C" en tres temas. Devuelve (temas, ajenos).

    Telegram solo ejecuta el comando que va al PRINCIPIO del mensaje. Si se
    escriben dos seguidos, el segundo llega como texto y se buscaba la frase
    entera - o sea que "Rosario Porto /oficial Alfonso Basterra" preguntaba
    por una persona imaginaria de cuatro nombres, y contestaba que no existe,
    que es verdad y no sirve de nada.

    Los que llevan OTRO comando dentro se devuelven aparte: ahi no se puede
    adivinar que queria, asi que se le dice en vez de hacer algo raro.
    """
    junto = " ".join(args or []).strip()
    if not junto:
        return [], []
    temas, ajenos, resto = [], [], junto
    while True:
        m = _OTRO_COMANDO.search(resto)
        if not m:
            break
        antes, nombre, resto = resto[:m.start()].strip(), m.group(1).lower(), resto[m.end():]
        if antes:
            (temas if not ajenos else ajenos).append(antes)
        if nombre != comando:
            ajenos.append("/" + nombre)
    if resto.strip():
        (ajenos if ajenos and ajenos[-1].startswith("/") else temas).append(resto.strip())
    return temas[:5], ajenos


async def handle_archivo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/archivo <tema> - metraje real y libre en Archive.org.

    Lo que nos faltaba: video EN MOVIMIENTO de hechos historicos. Para el
    calendario del canal es justo lo que hace falta, porque casi todo son
    efemerides de cosas que se filmaron."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    temas, ajenos = _varios_temas(context.args, "archivo")
    if not temas:
        await update.message.reply_text("Dime de que: /archivo Estonia ferry 1994")
        return
    if ajenos:
        await update.message.reply_text(
            "Ojo, lleva otro comando dentro (" + ", ".join(ajenos[:3]) + "), mandalo aparte.")
    await update.message.reply_text(
        "Buscando metraje libre de *" + "*, *".join(temas) + "*...", parse_mode="Markdown")

    loop = asyncio.get_running_loop()
    lineas: list[str] = []
    for tema in temas:
        try:
            piezas = await loop.run_in_executor(None, archivo.buscar, tema)
        except Exception:
            logger.exception("Error buscando en Archive.org %r", tema)
            lineas += [f"*{tema}*", "  · no he podido comprobarlo, mira los logs", ""]
            continue
        lineas.append(f"*{tema}*")
        if not piezas:
            lineas += ["  ✗ nada publicable. Hay material, pero sin licencia",
                       "    que permita usarlo en un canal monetizado.", ""]
            continue
        lineas.append(f"  ✓ {len(piezas)} piezas utilizables")
        for pz in piezas[:5]:
            año = f" ({pz['año']})" if pz.get("año") else ""
            lineas.append(f"      · {pz['titulo'][:44]}{año}")
            lineas.append(f"        {pz['licencia'][:50]}")
        lineas.append("")
    await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID,
                                   text=_recorta_pie("\n".join(lineas)),
                                   parse_mode="Markdown", disable_web_page_preview=True)


async def handle_oficial_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/oficial <nombre o caso> - ¿hay material oficial que se pueda usar?

    Sale de su pregunta, y la respuesta en España tiene dos mitades que no se
    parecen en nada, asi que el comando las separa en vez de dar un si o un
    no."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    temas, ajenos = _varios_temas(context.args, "oficial")
    if not temas:
        await update.message.reply_text("Dime de quien o de que caso: /oficial Rosario Porto")
        return
    if ajenos:
        await update.message.reply_text(
            "Ojo, esto lleva otro comando dentro (" + ", ".join(ajenos[:3]) +
            "). Telegram solo ejecuta el primero, asi que mandalo en otro mensaje.")
    await update.message.reply_text(
        "Mirando material oficial de *" + "*, *".join(temas) + "*...", parse_mode="Markdown")

    loop = asyncio.get_running_loop()
    lineas: list[str] = []
    for tema in temas:
        try:
            encontrado = await loop.run_in_executor(None, oficial.retrato, tema)
        except Exception:
            logger.exception("Error buscando material oficial de %r", tema)
            lineas += [f"*{tema}*", "  · no he podido comprobarlo, mira los logs", ""]
            continue
        lineas.append(f"*{tema}*")
        if encontrado:
            _url, fichero = encontrado
            lineas += ["  ✓ FOTO LIBRE · Wikidata tiene ficha con retrato",
                       f"      · {fichero[:52]}",
                       "      Entra sola en el proximo video, no tienes que hacer nada.", ""]
        else:
            lineas += ["  ✗ FOTO LIBRE · Wikidata no tiene retrato fichado", ""]

    lineas += [
        "  ✓ SENTENCIA · libre, y es la mejor fuente que hay",
        "      Las resoluciones judiciales no son de nadie (art. 13 LPI):",
        "      se pueden citar enteras, leerlas y sacarlas en pantalla.",
        f"      Buscador publico: {oficial.CENDOJ}",
        "",
        "  ✗ FOTOS DE POLICIA O JUZGADO · no son libres en España",
        "      Aqui no es como en EEUU. Que la difundan para que salga en",
        "      prensa no la convierte en libre: sigue teniendo dueño.",
    ]
    await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="\n".join(lineas),
                                   parse_mode="Markdown", disable_web_page_preview=True)


async def handle_viable_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/viable <caso> - ¿merece la pena hacer este video? Antes de gastar nada.

    Junta las dos preguntas que deciden un video y que hasta ahora se
    contestaban DESPUES de pagarlo:

      - ¿hay alguien buscando esto? La respuesta la da la demanda medida en
        YouTube. Sus propios numeros: los temas que le dieron 2, 3, 9, 17 y 31
        visitas tenian todos menos de diez mil vistas semanales; el que le dio
        479 tenia cinco millones.

      - ¿hay imagenes que podamos usar? Esto salio del caso Asunta. Se hizo el
        video entero - guion, voz, montaje - para descubrir al final que no
        existe ni una foto libre de la victima ni de sus padres, porque en un
        caso de sucesos español las fotos que todos conocemos son de agencia.
        Se puede mirar antes: basta con listar las imagenes del articulo.

    No genera nada, no gasta creditos y cuesta unas cien unidades de cuota."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    tema = " ".join(context.args).strip()
    if not tema:
        await update.message.reply_text("Dime de que caso: /viable Caso Asunta Basterra")
        return
    await update.message.reply_text(f"Mirando si *{tema}* da para video...", parse_mode="Markdown")
    loop = asyncio.get_running_loop()

    async def trabajo():
        def mirar():
            existe = research.existe(WIKI_LANG, tema)
            try:
                dem = demanda.medir(tema)
            except (demanda.SinClave, demanda.SinCuota) as exc:
                dem = {"medido": False, "vistas": 0, "consulta": tema, "aviso": str(exc)}
            imgs = real_photos.imagenes_del_caso(tema) if existe else []
            return existe, dem, imgs

        try:
            existe, dem, imgs = await loop.run_in_executor(None, mirar)
        except Exception:
            logger.exception("Error comprobando la viabilidad de %r", tema)
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID, text="No he podido comprobarlo. Mira los logs.")
            return

        if existe is None:
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=f"«{tema}»: Wikipedia no ha contestado. Vuelve a intentarlo.")
            return
        if existe is False:
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=f"«{tema}»: NO existe ese articulo. Sin articulo no hay dosier "
                     "ni imagenes. Comprueba el nombre exacto.")
            return

        lineas = [f"*{tema}*", ""]

        # 1. Demanda
        if not dem.get("medido"):
            lineas.append(f"  DEMANDA · no medida ({dem.get('aviso','')[:60]})")
            dem_ok = None
        else:
            dem_ok = dem["vistas"] >= DEMANDA_MINIMA
            lineas.append(
                f"  {'✓' if dem_ok else '✗'} DEMANDA · {dem['vistas']:,} vistas en 7 dias "
                f"({dem['videos']} videos, mediana {dem['mediana']:,})".replace(",", "."))

        # 2. Imagenes
        lineas.append(f"  {'✓' if imgs else '✗'} IMAGENES · {len(imgs)} libres "
                      "(articulo, otra Wikipedia y Commons)")
        for _url, fichero in imgs[:8]:
            lineas.append(f"      · {fichero[:52]}")
        if len(imgs) > 8:
            lineas.append(f"      · ...y {len(imgs) - 8} mas")
        if not imgs:
            lineas.append("      Ninguna. El video iria solo con video de archivo,")
            lineas.append("      diapositivas y lugares genericos.")

        # 3. Veredicto, que es para lo que existe el comando
        lineas.append("")
        if dem_ok is False:
            lineas.append("NO lo haria: sin demanda, da igual lo bien que quede.")
        elif dem_ok and imgs:
            lineas.append("SI: hay quien lo busca y hay con que contarlo.")
        elif dem_ok and not imgs:
            lineas.append("SE PUEDE, sabiendo lo que compras: hay demanda pero no hay")
            lineas.append("imagenes propias. Sale un video correcto y generico.")
        else:
            lineas.append("Sin la demanda no se puede decidir. Vuelve cuando haya cuota.")

        await context.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID, text="\n".join(lineas), parse_mode="Markdown")

    context.application.create_task(trabajo())


async def handle_demand_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/demanda <tema> - cuanta gente esta buscando esto ahora mismo.

    No genera nada y no gasta un credito. Existe porque la diferencia entre un
    video de 479 visitas y uno de 2 en este canal no estuvo en como se conto:
    estuvo en si habia alguien buscandolo, y eso se puede saber ANTES de
    gastarse los creditos.

    Se pueden pegar varios temas, uno por linea, para compararlos."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    bruto = " ".join(context.args).strip()
    temas = [t.strip() for t in re.split(r"/demanda\b|\n", bruto) if t.strip()][:6]
    if not temas:
        await update.message.reply_text(
            "Dime de que tema: /demanda claudia tacoronte\n"
            "Puedes pegar varios, uno por linea.")
        return
    await update.message.reply_text("Midiendo la demanda en YouTube...")
    loop = asyncio.get_running_loop()

    async def trabajo():
        try:
            medidos = await loop.run_in_executor(
                None, lambda: [demanda.medir(t) for t in temas])
        except (demanda.SinClave, demanda.SinCuota) as exc:
            await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=str(exc))
            return
        except Exception:
            logger.exception("Error midiendo la demanda")
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID, text="No he podido medir. Mira los logs.")
            return

        medidos.sort(key=lambda m: m.get("vistas", 0), reverse=True)
        lineas = [f"*Demanda en YouTube* (ultimos 7 dias)",
                  f"Minimo para hacer video: {DEMANDA_MINIMA:,} vistas".replace(",", "."), ""]
        for m in medidos:
            if not m["medido"]:
                lineas.append(f"  ? «{m['consulta']}» — no se ha podido medir")
                continue
            marca = "✓" if m["vistas"] >= DEMANDA_MINIMA else "✗"
            lineas.append(
                f"  {marca} «{m['consulta']}»\n"
                f"      {m['vistas']:,} vistas · {m['videos']} videos · "
                f"mediana {m['mediana']:,}".replace(",", "."))
        lineas.append("")
        mejor = medidos[0] if medidos else None
        if mejor and mejor.get("vistas", 0) >= DEMANDA_MINIMA:
            lineas.append(f"Yo haria «{mejor['consulta']}».")
        else:
            lineas.append("Ninguno tiene demanda suficiente hoy. Hacer video de "
                          "cualquiera de estos es gastar creditos para 3 visitas.")
        await context.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID, text="\n".join(lineas), parse_mode="Markdown")

    context.application.create_task(trabajo())


async def handle_resend_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/enviar [id] - vuelve a mandar un video ya hecho.

    Existe porque un video terminado puede quedarse en el disco sin llegar
    nunca: paso con el 68, que se monto entero, se narro entero - unos siete
    mil quinientos creditos - y no se envio porque el pie de Telegram se
    pasaba del limite. Desde el chat parecia que la generacion se habia
    parado. Volver a generarlo habria costado los creditos otra vez para
    hacer exactamente el mismo video que ya estaba hecho."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    args = [a for a in (context.args or []) if a.isdigit()]
    if args:
        video_id = int(args[0])
    else:
        video_id = storage.ultimo_video_id()
        if video_id is None:
            await update.message.reply_text("Todavia no hay ningun video que mandar.")
            return

    if storage.get_video(video_id) is None:
        await update.message.reply_text(f"No tengo ningun video con el id {video_id}.")
        return

    await update.message.reply_text(f"Mandando otra vez el video {video_id}...")
    try:
        await send_for_approval(context.bot, video_id)
    except Exception:
        logger.exception("Error reenviando el video %s", video_id)
        await update.message.reply_text(
            f"No he podido mandar el video {video_id}. Mira los logs.")


async def handle_sources_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/fuentes <caso> - which sources outside Wikipedia this case actually has.

    The reason this exists: from where the code is written, every one of these
    domains is blocked by the network, so whether the open-web layer returns
    anything cannot be checked there - only guessed at. Guessing is exactly
    how a feature gets shipped that quietly returns nothing, and the dossier
    would still look fine, because it would still have Wikipedia in it.

    This runs where the bot runs, which does reach them, and reports the
    outcome per reference: the ones read, how much they gave, the ones that
    came back dead or paywalled, and the ones rescued from the archive. It
    generates nothing and costs nothing - no model is called - so it can be
    run on a case before deciding to make a video about it."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    # Three cases pasted into one message is the normal way to send three
    # cases, and Telegram hands the whole block over as the arguments of the
    # first command. Splitting it back apart costs one line and removes the
    # only way this command can be used wrong.
    bruto = " ".join(context.args).strip()
    temas = [t.strip() for t in re.split(r"/fuentes\b", bruto) if t.strip()][:5]
    if not temas:
        await update.message.reply_text(
            "Dime de que caso: /fuentes Silk Road (mercado negro)\n"
            "Puedes pegar varios de golpe, uno por linea.")
        return
    await update.message.reply_text(
        "Buscando fuentes fuera de Wikipedia de:\n" +
        "\n".join(f"· {t}" for t in temas))
    loop = asyncio.get_running_loop()

    async def trabajo():
        def medir(tema):
            hay = research.existe(WIKI_LANG, tema)
            if hay is not True:
                return hay  # False = no existe; None = Wikipedia no contesto
            # The same articles build_dossier reads, so what this reports is
            # what a real run would get, not a different question.
            idiomas = [(WIKI_LANG, tema)]
            otros = research._translations(WIKI_LANG, tema)
            idiomas += [(l, otros[l]) for l in research._LANG_PRIORITY
                        if l in otros and l != WIKI_LANG][: research._MAX_LANGS - 1]
            candidatas = research.referencias_de(idiomas)
            return idiomas, candidatas, research.leer_referencias(candidatas)

        for tema in temas:
            try:
                medido = await loop.run_in_executor(None, medir, tema)
            except Exception:
                logger.exception("Error sondeando las fuentes de %r", tema)
                await context.bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=f"«{tema}»: ha fallado el sondeo. Mira los logs.")
                continue

            if medido is None:
                await context.bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=f"«{tema}»: Wikipedia ({WIKI_LANG}) no ha contestado a la "
                         "comprobacion. NO quiere decir que el articulo no exista. "
                         "Vuelve a lanzarlo.")
                continue
            if medido is False:
                await context.bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=f"«{tema}»: NO existe ese articulo en la Wikipedia en "
                         f"{WIKI_LANG}. No es que no tenga fuentes: es que no "
                         "existe con ese nombre exacto.")
                continue

            idiomas, candidatas, leidas = medido
            lineas = [f"*{tema}*",
                      f"Wikipedia en: {', '.join(l for l, _ in idiomas)}",
                      f"{len(candidatas)} referencias en la lista · {len(leidas)} leidas", ""]
            palabras_extra = 0
            for nombre, _pedida, url, texto in leidas:
                palabras = len(texto.split())
                palabras_extra += palabras
                marca = " (del archivo)" if "web.archive.org" in url else ""
                dominio = url.split("/")[2] if "//" in url else url
                lineas.append(
                    f"  ✓ {nombre} · {dominio}{marca} — {palabras:,} palabras".replace(",", "."))

            # Only the ones actually attempted can be called failures. The rest
            # were never tried: the budget ran out first, and reporting them as
            # dead would be inventing a result.
            intentadas = candidatas[: research._MAX_REFERENCIAS * research._INTENTOS_POR_PLAZA]
            conseguidas = {pedida for _n, pedida, _u, _t in leidas}
            for _rango, nombre, url in intentadas:
                if url in conseguidas:
                    continue
                dominio = url.split("/")[2] if "//" in url else url
                lineas.append(f"  ✗ {nombre} · {dominio} — muerta, de pago o vacia")

            lineas.append("")
            if leidas:
                lineas.append(
                    f"{palabras_extra:,} palabras que Wikipedia NO tiene.".replace(",", "."))
            elif candidatas:
                lineas.append(
                    "El articulo cita fuentes de la lista pero ninguna respondio: "
                    "muertas, de pago o sin copia en el archivo.")
            else:
                lineas.append(
                    "El articulo existe pero no cita ni una fuente de la lista. "
                    "Este caso saldria solo de Wikipedia, igual que el de cualquier otro canal.")
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID, text="\n".join(lineas), parse_mode="Markdown")

    context.application.create_task(trabajo())


async def handle_account_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/cuenta - what the ElevenLabs subscription actually allows.

    Worth a command rather than a one-off look: the two numbers that decide
    whether a cloned voice can carry this channel - credits left and whether
    the professional clone is available - are both on the account, and getting
    either wrong costs either money or half an hour of recording for nothing."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    loop = asyncio.get_running_loop()

    async def trabajo():
        try:
            datos = await loop.run_in_executor(None, voice_clone.cuenta)
        except voice_clone.CloneError as exc:
            await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=str(exc))
            return
        except Exception:
            logger.exception("Error leyendo la cuenta de ElevenLabs")
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID, text="No he podido leer la cuenta. Mira los logs.")
            return
        await context.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID, text=voice_clone.resumen_cuenta(datos))

    context.application.create_task(trabajo())


async def handle_vertex_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/vertex - says whether AI illustration is working, and if not, what to fix."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    loop = asyncio.get_running_loop()

    # /vertex con texto detras genera ESA imagen, con el estilo del canal, y la
    # manda aqui: ver si el estilo funciona cuesta entonces una imagen en vez
    # de un video entero.
    prompt = " ".join(context.args).strip() if context.args else ""
    if prompt:
        await update.message.reply_text(f"Generando una imagen de prueba: {prompt}")
        out_path = Path(DATA_DIR) / "vertex_preview.jpg"
        image_path, detail = await loop.run_in_executor(
            None, ai_images.preview, prompt, out_path, "9:16"
        )
        if image_path is None:
            await update.message.reply_text("No salio. " + detail)
            return
        with image_path.open("rb") as handle:
            await update.message.reply_photo(photo=handle, caption=detail[:1024] or prompt[:1024])
        return

    await update.message.reply_text("Probando Vertex AI, un momento...")
    works, detail = await loop.run_in_executor(None, ai_images.check_access)
    await update.message.reply_text(("OK. " if works else "NO funciona. ") + detail)


async def handle_stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/parar - gives up on the generation in progress."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    if not _pipeline_lock.locked():
        await update.message.reply_text("No hay ninguna generacion en marcha ahora mismo.")
        return
    request_stop()
    await update.message.reply_text(
        "Vale, la paro. No es instantaneo: el paso que este haciendo ahora (una llamada a la IA, "
        "un montaje de ffmpeg) no se puede interrumpir a medias, asi que se corta al terminarlo. "
        "Suele tardar entre unos segundos y un par de minutos. Te aviso cuando este parada."
    )


async def handle_voices_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/voces - que voces hay; /voz <nombre> - escuchar una."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    await update.message.reply_text(f"Voz en uso ahora mismo: {TTS_VOICE_NAME}\nPreguntando a Google...")
    try:
        voces = await asyncio.get_running_loop().run_in_executor(None, tts.list_spanish_voices)
    except Exception as exc:
        await update.message.reply_text(f"No se pudo consultar: {str(exc)[:300]}")
        return
    if not voces:
        await update.message.reply_text("Google no devuelve ninguna voz para este idioma.")
        return

    # Grouped by family because the family is what decides how natural it
    # sounds and what it costs - the individual name only picks a timbre.
    familias: dict[str, list[str]] = {}
    for nombre, genero in voces:
        partes = nombre.split("-")
        familia = partes[2] if len(partes) > 2 else "otras"
        familias.setdefault(familia, []).append(f"{nombre} ({genero[0]})")

    lineas = [f"{len(voces)} voces disponibles en {TTS_LANGUAGE_CODE}:"]
    for familia in sorted(familias, key=lambda f: (f != "Chirp3", f)):
        lineas.append(f"\n{familia} ({len(familias[familia])}):")
        lineas.extend("  " + v for v in sorted(familias[familia]))
    texto = "\n".join(lineas)
    for i in range(0, len(texto), 3500):
        await update.message.reply_text(texto[i : i + 3500])
    await update.message.reply_text("Para escuchar una: /voz es-ES-Chirp3-HD-Enceladus")


async def handle_voice_sample_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/voz <nombre> - manda un audio de muestra con esa voz."""
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    nombre = (context.args[0].strip() if context.args else "") or TTS_VOICE_NAME
    await update.message.reply_text(f"Generando muestra con {nombre}...")
    out_path = Path(DATA_DIR) / "voice_sample.mp3"
    try:
        await asyncio.get_running_loop().run_in_executor(
            None, tts.synthesize_sample, nombre, out_path
        )
    except Exception as exc:
        await update.message.reply_text(f"No salio con {nombre}: {str(exc)[:300]}")
        return
    with out_path.open("rb") as handle:
        await update.message.reply_audio(audio=handle, caption=nombre)


async def handle_reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    cleared = storage.clear_processed_sources()
    await update.message.reply_text(
        f"Listo, {cleared} noticias marcadas como vistas se han olvidado. "
        "El proximo /generar puede repetir cualquiera del feed actual."
    )


async def _warn_if_run_was_interrupted(application: Application) -> None:
    """Says so when a restart killed a generation, instead of leaving the
    chat waiting for a video that is never coming."""
    evidencia = interrupted_run_evidence()
    if not evidencia:
        return
    logger.warning("Se detecto una generacion interrumpida por un reinicio (%s).", evidencia)
    try:
        await application.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=(
                "Aviso: una generacion se quedo a medias por un reinicio del servidor "
                "(normalmente, un despliegue). No va a llegar ningun video de esa tanda. "
                "Vuelve a lanzar /generar cuando quieras."
            ),
        )
    except Exception:
        logger.exception("No se pudo avisar de la generacion interrumpida")


def build_application() -> Application:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(
        _warn_if_run_was_interrupted
    ).build()
    application.add_handler(CallbackQueryHandler(handle_decision))
    application.add_handler(CommandHandler("generar", handle_generate_command))
    application.add_handler(CommandHandler("reset", handle_reset_command))
    application.add_handler(CommandHandler("parar", handle_stop_command))
    application.add_handler(CommandHandler("voces", handle_voices_command))
    application.add_handler(CommandHandler("voz", handle_voice_sample_command))
    application.add_handler(CommandHandler("vertex", handle_vertex_command))
    application.add_handler(CommandHandler("listo", handle_done_command))
    application.add_handler(CommandHandler("rehacer", handle_redo_command))
    application.add_handler(CommandHandler("clon", handle_clone_command))
    application.add_handler(CommandHandler("cuenta", handle_account_command))
    application.add_handler(CommandHandler("tono", handle_tone_command))
    application.add_handler(CommandHandler("usar", handle_use_command))
    application.add_handler(CommandHandler("dosier", handle_dossier_command))
    application.add_handler(CommandHandler("fuentes", handle_sources_command))
    application.add_handler(CommandHandler("enviar", handle_resend_command))
    application.add_handler(CommandHandler("demanda", handle_demand_command))
    application.add_handler(CommandHandler("viable", handle_viable_command))
    application.add_handler(CommandHandler("fotos", handle_photos_command))
    application.add_handler(CommandHandler("oficial", handle_oficial_command))
    application.add_handler(CommandHandler("archivo", handle_archivo_command))
    application.add_handler(CommandHandler("tendencias", handle_trending_command))
    application.add_handler(CommandHandler("calendario", handle_calendar_command))
    application.add_handler(CommandHandler("catalogo", handle_catalogue_command))
    # Audio arriving with no command is a narration for whatever script is
    # waiting; a voice note, an audio file and a file sent "as document" are
    # three different Telegram types for the same thing.
    application.add_handler(MessageHandler(
        filters.AUDIO | filters.VOICE | filters.Document.AUDIO, handle_narration_audio))
    # Una foto con el nombre en el pie entra en tu propia coleccion.
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.Document.IMAGE, handle_incoming_photo))
    # Don't auto-generate on every restart/deploy - only at the regular interval.
    # Use /generar in the chat for an on-demand run (e.g. right after deploying).
    # Nothing generates itself in either of the two voice modes, for two
    # different reasons.
    #
    # Read by a person: the scheduled run calls the ordinary pipeline, which
    # synthesises the voice, so leaving it armed would quietly produce every
    # twelve hours exactly the kind of video this mode exists to stop making,
    # and drop it into the chat in the middle of whatever is being recorded.
    # If a human has to read it, a human starts it.
    #
    # Cloned: nothing stops it working, which is the problem. A long video is
    # around eleven thousand credits, so an unattended run twice a day would
    # spend the month's allowance in under a week, on topics nobody chose,
    # while she is asleep. Automating that is a decision worth making on
    # purpose rather than inheriting from a default.
    if NARRATION_SOURCE in ("voz", "clon"):
        logger.info(
            "Narracion por %s: el generador automatico queda desactivado. "
            "Los videos se lanzan a mano con /generar.",
            "voz propia" if NARRATION_SOURCE == "voz" else "voz clonada",
        )
    else:
        application.job_queue.run_repeating(
            pipeline_job, interval=PIPELINE_INTERVAL_SECONDS, first=PIPELINE_INTERVAL_SECONDS
        )
    return application
