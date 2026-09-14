import logging

from . import storage
from .telegram_bot import build_application

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main() -> None:
    storage.init_db()
    application = build_application()
    application.run_polling()


if __name__ == "__main__":
    main()
