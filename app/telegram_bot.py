import logging
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from . import storage
from .config import PIPELINE_INTERVAL_SECONDS, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from .pipeline import run_once
from .youtube_uploader import upload_captions, upload_video

logger = logging.getLogger(__name__)


_VARIANT_LABELS = {"short": "🔹 SHORT (vertical)", "long": "🔸 VIDEO LARGO (horizontal)"}


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
    with open(record["thumbnail_path"], "rb") as thumbnail_file:
        message = await bot.send_photo(
            chat_id=TELEGRAM_CHAT_ID,
            photo=thumbnail_file,
            caption=caption,
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
        await query.edit_message_caption(caption=f"{label}\nRechazado: {record['title']}")
        return

    await query.edit_message_caption(caption=f"{label}\nSubiendo a YouTube: {record['title']}")
    try:
        youtube_id = upload_video(
            Path(record["video_path"]),
            Path(record["thumbnail_path"]),
            record["title"],
            record["description"],
            record["tags"].split(","),
        )
        storage.set_status(video_id, "uploaded", youtube_id)

        if record["subtitle_path"]:
            try:
                upload_captions(youtube_id, Path(record["subtitle_path"]))
            except Exception:
                # Not critical: the video is already live without a captions track.
                logger.exception("Error subiendo subtitulos para el video %s", video_id)

        await query.edit_message_caption(
            caption=f"{label}\nPublicado: {record['title']}\nhttps://youtu.be/{youtube_id}"
        )
    except Exception:
        logger.exception("Error subiendo el video %s a YouTube", video_id)
        storage.set_status(video_id, "upload_failed")
        await query.edit_message_caption(caption=f"{label}\nError al subir: {record['title']}. Revisa los logs.")


async def _run_pipeline_and_notify(bot) -> None:
    try:
        video_ids = run_once()
        if not video_ids:
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="No hay noticias nuevas que procesar ahora mismo.")
            return
        for video_id in video_ids:
            await send_for_approval(bot, video_id)
    except Exception:
        logger.exception("Error ejecutando el pipeline de generacion de video")
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="Error generando el video, revisa los logs.")


async def pipeline_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_pipeline_and_notify(context.bot)


async def handle_generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return
    await update.message.reply_text("Generando video nuevo, tardara unos minutos...")
    await _run_pipeline_and_notify(context.bot)


def build_application() -> Application:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CallbackQueryHandler(handle_decision))
    application.add_handler(CommandHandler("generar", handle_generate_command))
    application.job_queue.run_repeating(pipeline_job, interval=PIPELINE_INTERVAL_SECONDS, first=15)
    return application
