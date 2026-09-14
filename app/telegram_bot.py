import asyncio
import logging
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from . import storage
from .config import PIPELINE_INTERVAL_SECONDS, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from .pipeline import cleanup_finished_video_files, run_once
from .youtube_uploader import upload_captions, upload_video

logger = logging.getLogger(__name__)

_VARIANT_LABELS = {"short": "🔹 SHORT (vertical)", "long": "🔸 VIDEO LARGO (horizontal)"}

# run_once()/upload_video() are blocking (ffmpeg subprocesses, network I/O).
# Running them directly inside an async handler would freeze the whole bot -
# no button presses or commands would be processed until they finished. They
# run in this executor instead, and this lock keeps two pipeline runs from
# overlapping (e.g. the scheduled job and a manual /generar at the same time).
_pipeline_lock = asyncio.Lock()


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

    try:
        # Send the actual video (not just its thumbnail) so it can be watched
        # in full before deciding - Telegram bots can only upload up to 50MB,
        # so a long video that exceeds that falls back to a thumbnail-only
        # message below instead of failing the whole approval flow.
        with open(record["video_path"], "rb") as video_file, open(record["thumbnail_path"], "rb") as thumb_file:
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
        youtube_id = await loop.run_in_executor(
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

        await query.edit_message_caption(
            caption=f"{label}\nPublicado: {record['title']}\nhttps://youtu.be/{youtube_id}"
        )
    except Exception:
        logger.exception("Error subiendo el video %s a YouTube", video_id)
        storage.set_status(video_id, "upload_failed")
        await query.edit_message_caption(caption=f"{label}\nError al subir: {record['title']}. Revisa los logs.")


async def _run_pipeline_and_notify(bot) -> None:
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
            video_ids = await loop.run_in_executor(None, run_once, on_variant_done)
            if not video_ids:
                await bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID, text="No hay noticias nuevas que procesar ahora mismo."
                )
        except Exception:
            logger.exception("Error ejecutando el pipeline de generacion de video")
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="Error generando el video, revisa los logs.")


async def pipeline_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_pipeline_and_notify(context.bot)


async def handle_generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    if _pipeline_lock.locked():
        await update.message.reply_text("Ya hay una generacion en curso, espera a que termine.")
        return
    await update.message.reply_text("Generando video nuevo, tardara unos minutos...")
    await _run_pipeline_and_notify(context.bot)


async def handle_reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    cleared = storage.clear_processed_sources()
    await update.message.reply_text(
        f"Listo, {cleared} noticias marcadas como vistas se han olvidado. "
        "El proximo /generar puede repetir cualquiera del feed actual."
    )


def build_application() -> Application:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CallbackQueryHandler(handle_decision))
    application.add_handler(CommandHandler("generar", handle_generate_command))
    application.add_handler(CommandHandler("reset", handle_reset_command))
    # Don't auto-generate on every restart/deploy - only at the regular interval.
    # Use /generar in the chat for an on-demand run (e.g. right after deploying).
    application.job_queue.run_repeating(pipeline_job, interval=PIPELINE_INTERVAL_SECONDS, first=PIPELINE_INTERVAL_SECONDS)
    return application
