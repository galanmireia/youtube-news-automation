import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
CREDENTIALS_DIR = BASE_DIR / "credentials"
CREDENTIALS_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "state.db"

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")

PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]

GOOGLE_APPLICATION_CREDENTIALS = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS", str(CREDENTIALS_DIR / "google-tts.json")
)
TTS_VOICE_NAME = os.environ.get("TTS_VOICE_NAME", "es-ES-Standard-A")
TTS_LANGUAGE_CODE = os.environ.get("TTS_LANGUAGE_CODE", "es-ES")

YOUTUBE_CLIENT_SECRETS_FILE = os.environ.get(
    "YOUTUBE_CLIENT_SECRETS_FILE", str(CREDENTIALS_DIR / "youtube_client_secret.json")
)
YOUTUBE_TOKEN_FILE = os.environ.get("YOUTUBE_TOKEN_FILE", str(CREDENTIALS_DIR / "youtube_token.json"))
YOUTUBE_PRIVACY_STATUS = os.environ.get("YOUTUBE_PRIVACY_STATUS", "public")

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

RSS_FEEDS = [
    feed.strip()
    for feed in os.environ.get("RSS_FEEDS", "https://news.google.com/rss?hl=es&gl=ES&ceid=ES:es").split(",")
    if feed.strip()
]

PIPELINE_INTERVAL_SECONDS = int(os.environ.get("PIPELINE_INTERVAL_SECONDS", 60 * 60 * 12))
NEWS_LANGUAGE_HINT = os.environ.get("NEWS_LANGUAGE_HINT", "castellano, España")
VIDEO_WIDTH = int(os.environ.get("VIDEO_WIDTH", 1920))
VIDEO_HEIGHT = int(os.environ.get("VIDEO_HEIGHT", 1080))

# Google Cloud TTS reads its credentials from this env var directly.
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", GOOGLE_APPLICATION_CREDENTIALS)
