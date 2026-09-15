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
# Optional second stock library, searched when Pexels has nothing of the right
# shape for a scene. Without a key the pipeline behaves exactly as before, so
# it is safe to leave unset. A free key comes from https://pixabay.com/api/docs/
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "").strip()

GOOGLE_APPLICATION_CREDENTIALS = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS", str(CREDENTIALS_DIR / "google-tts.json")
)
TTS_VOICE_NAME = os.environ.get("TTS_VOICE_NAME", "es-ES-Chirp3-HD-Callirrhoe")
TTS_LANGUAGE_CODE = os.environ.get("TTS_LANGUAGE_CODE", "es-ES")

YOUTUBE_CLIENT_SECRETS_FILE = os.environ.get(
    "YOUTUBE_CLIENT_SECRETS_FILE", str(CREDENTIALS_DIR / "youtube_client_secret.json")
)
YOUTUBE_TOKEN_FILE = os.environ.get("YOUTUBE_TOKEN_FILE", str(CREDENTIALS_DIR / "youtube_token.json"))
YOUTUBE_PRIVACY_STATUS = os.environ.get("YOUTUBE_PRIVACY_STATUS", "public")

# Minutes to hold a video back before it goes live. 0 publishes immediately.
#
# This only applies when YOUTUBE_PRIVACY_STATUS is "public": scheduling works
# by uploading as private with a publishAt time, so if the channel is already
# meant to stay private (testing), scheduling it would do the one thing that
# setting exists to prevent - make it public on its own.
YOUTUBE_PUBLISH_DELAY_MINUTES = int(os.environ.get("YOUTUBE_PUBLISH_DELAY_MINUTES", "0"))


def _materialize_credential_from_env(env_var: str, target_path: str) -> None:
    """Allows deploying without a persistent volume: if the credential's JSON
    content is provided directly as an env var, write it to the expected
    path (unless it's already there, e.g. mounted locally)."""
    content = os.environ.get(env_var)
    if not content:
        return
    path = Path(target_path)
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


_materialize_credential_from_env("GOOGLE_TTS_CREDENTIALS_JSON", GOOGLE_APPLICATION_CREDENTIALS)
_materialize_credential_from_env("YOUTUBE_CLIENT_SECRET_JSON", YOUTUBE_CLIENT_SECRETS_FILE)
_materialize_credential_from_env("YOUTUBE_TOKEN_JSON", YOUTUBE_TOKEN_FILE)

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# General headlines plus two targeted feeds. The channel's best-performing
# video so far was a crime/society story, and the general feed is mostly
# politics, so those topics rarely came up on their own. They are covered
# under the same rules as anything else: the script generator's sensitivity
# check still forces a neutral, non-speculative treatment for any story
# involving a real victim.
_DEFAULT_RSS_FEEDS = ",".join(
    [
        "https://news.google.com/rss?hl=es&gl=ES&ceid=ES:es",
        "https://news.google.com/rss/search?q=sucesos&hl=es&gl=ES&ceid=ES:es",
        "https://news.google.com/rss/search?q=tribunal+OR+juicio+OR+condena&hl=es&gl=ES&ceid=ES:es",
    ]
)
RSS_FEEDS = [feed.strip() for feed in os.environ.get("RSS_FEEDS", _DEFAULT_RSS_FEEDS).split(",") if feed.strip()]

PIPELINE_INTERVAL_SECONDS = int(os.environ.get("PIPELINE_INTERVAL_SECONDS", 60 * 60 * 12))
NEWS_LANGUAGE_HINT = os.environ.get("NEWS_LANGUAGE_HINT", "castellano, España")
CHANNEL_NAME = os.environ.get("CHANNEL_NAME", "ActualiDark")
CHANNEL_LOGO_URL = os.environ.get(
    "CHANNEL_LOGO_URL",
    "https://yt3.googleusercontent.com/7pwcunu0h_a_fxTodi6tBv1pRBHF5J7AG78RFPKAOODHFyWYd1-Zkj9NunqTeDR52aQ1ed54Lw=s160-c-k-c0x00ffffff-no-rj",
)
CHANNEL_TONE_HINT = os.environ.get(
    "CHANNEL_TONE_HINT",
    "revela el lado oculto, inquietante o menos contado de cada noticia: que se esconde detras "
    "del titular, que consecuencias no se ven a simple vista, que preguntas incomodas deja "
    "abiertas. El tono es intrigante y directo, pero SIEMPRE basado en hechos verificables de la "
    "propia noticia, nunca en especulacion sin fundamento ni teorias de conspiracion.",
)
# Burned-in subtitles are the norm on Shorts (most of the feed is watched
# muted), on top of the caption track uploaded to YouTube.
BURN_SUBTITLES = os.environ.get("BURN_SUBTITLES", "true").strip().lower() != "false"

# Background music. Drop licensed tracks (e.g. from YouTube's own Audio
# Library, which is the safest choice for monetization) into this folder as
# mp3/m4a/wav; one is picked at random per video. No folder or no files
# means videos are simply built without music.
MUSIC_DIR = Path(os.environ.get("MUSIC_DIR", str(BASE_DIR / "assets" / "music")))
# Quiet enough to sit under the narration without competing with it.
MUSIC_VOLUME = float(os.environ.get("MUSIC_VOLUME", 0.08))

LONG_VIDEO_WIDTH = int(os.environ.get("LONG_VIDEO_WIDTH", os.environ.get("VIDEO_WIDTH", 1920)))
LONG_VIDEO_HEIGHT = int(os.environ.get("LONG_VIDEO_HEIGHT", os.environ.get("VIDEO_HEIGHT", 1080)))
SHORT_VIDEO_WIDTH = int(os.environ.get("SHORT_VIDEO_WIDTH", 1080))
SHORT_VIDEO_HEIGHT = int(os.environ.get("SHORT_VIDEO_HEIGHT", 1920))

# Used for the Vertex AI Imagen fallback when neither stock footage nor a
# real public figure's photo fits a scene (reuses the Google Cloud project
# already set up for Text-to-Speech).
GOOGLE_CLOUD_PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT_ID", "lucky-album-508608-t0")
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

# Google Cloud TTS reads its credentials from this env var directly.
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", GOOGLE_APPLICATION_CREDENTIALS)
