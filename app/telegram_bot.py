import asyncio
from io import BytesIO
import logging
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, MessageHandler, filters)

from . import ai_images, storage, tts, voice_align, voice_clone
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
from .youtube_uploader import upload_captions, upload_video

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
_PIPELINE_TIMEOUT_SECONDS = 25 * 60


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
    caption = f"{label}\n*{record['title']}*\n\n{record['description']}"

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
_CREDITOS_POR_VARIANTE = {"short": 700, "long": 2900}


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
            f"{'el Short' if v == 'short' else 'el largo'} ~{_CREDITOS_POR_VARIANTE[v]:,}"
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
    # Audio arriving with no command is a narration for whatever script is
    # waiting; a voice note, an audio file and a file sent "as document" are
    # three different Telegram types for the same thing.
    application.add_handler(MessageHandler(
        filters.AUDIO | filters.VOICE | filters.Document.AUDIO, handle_narration_audio))
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
