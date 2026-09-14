import logging

from . import storage
from .pipeline import cleanup_finished_video_files
from .telegram_bot import build_application

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    storage.init_db()
    removed = cleanup_finished_video_files()
    if removed:
        logger.info("Limpieza al arrancar: %s directorios de videos ya terminados eliminados.", removed)
    application = build_application()
    application.run_polling()


if __name__ == "__main__":
    main()
