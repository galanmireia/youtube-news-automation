import logging

from . import storage
from .config import RSS_FEEDS
from .pipeline import cleanup_finished_video_files
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
    removed = cleanup_finished_video_files()
    if removed:
        logger.info("Limpieza al arrancar: %s directorios de videos ya terminados eliminados.", removed)
    application = build_application()
    application.run_polling()


if __name__ == "__main__":
    main()
