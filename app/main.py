import logging

from . import storage
from .config import PIXABAY_API_KEY, RSS_FEEDS, TTS_LANGUAGE_CODE, TTS_VOICE_NAME
from .pipeline import cleanup_finished_video_files, note_interrupted_run, sweep_orphan_build_files
from .telegram_bot import build_application

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    storage.init_db()
    # RSS_FEEDS is also settable as an environment variable, which silently
    # overrides the list in config.py - so adding a feed there can look done
    # while production keeps reading whatever the variable says. Print what is
    # actually in use rather than having to guess from which stories come up.
    logger.info("Feeds RSS en uso (%s):", len(RSS_FEEDS))
    for feed in RSS_FEEDS:
        logger.info("  - %s", feed)
    # Same reasoning as the feeds above: an optional source that silently does
    # nothing when unset is worth stating outright, so nobody has to deduce
    # from the footage whether it is actually in play. The key itself is never
    # logged.
    logger.info(
        "Banco de video secundario (Pixabay): %s",
        "configurado" if PIXABAY_API_KEY else "sin clave, solo se usara Pexels",
    )
    # Before the sweep: it deletes the half-finished build that is the only
    # trace a restart killed a generation, and the bot announces that on
    # startup so nobody is left waiting for a video that is not coming.
    if note_interrupted_run():
        logger.warning("Habia una generacion a medias; se avisara en Telegram.")
    # Same reasoning as the feeds: an environment variable silently overriding
    # the code default is invisible until somebody wonders why the voice
    # changed. The voice family is what decides how natural it sounds.
    logger.info("Voz de narracion en uso: %s (%s)", TTS_VOICE_NAME, TTS_LANGUAGE_CODE)
    sweep_orphan_build_files()
    removed = cleanup_finished_video_files()
    if removed:
        logger.info("Limpieza al arrancar: %s directorios de videos ya terminados eliminados.", removed)
    application = build_application()
    application.run_polling()


if __name__ == "__main__":
    main()
