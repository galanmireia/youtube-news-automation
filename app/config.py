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
# Who reads the narration. "tts" synthesises it, which is what the channel
# did while it was publishing several videos a day. "voz" writes the script,
# sends it to be read aloud, and waits for the recording - slower by a whole
# human, and the single biggest quality difference between this channel and
# the ones that work.
# Voice cloning, used to answer one question cheaply: does a clone of the
# channel's own voice sound like her, or like a synthesiser wearing her
# timbre. Absent by default - nothing calls ElevenLabs unless this is set.
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()

NARRATION_SOURCE = os.environ.get("NARRATION_SOURCE", "tts").strip().lower()

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
# Which kind of channel this is.
#
# "news": stories arrive from RSS feeds, a picker chooses the best one, and the
#   script is written as same-day news. This is what the channel ran as first.
# "topics": subjects come from a curated catalogue of engineering and disaster
#   cases and the facts come from their Wikipedia article. Evergreen, which is
#   the point - a news video is dead in a week and never accumulates the watch
#   hours the channel needs, while a case from 1912 still earns views in three
#   years.
#
# Everything downstream - script, voice, pictures, subtitles, upload - is shared;
# only where the subject and its facts come from differs.
CONTENT_MODE = os.environ.get("CONTENT_MODE", "news").strip().lower()

CHANNEL_NAME = os.environ.get("CHANNEL_NAME", "ActualiDark")
CHANNEL_LOGO_URL = os.environ.get(
    "CHANNEL_LOGO_URL",
    "https://yt3.googleusercontent.com/7pwcunu0h_a_fxTodi6tBv1pRBHF5J7AG78RFPKAOODHFyWYd1-Zkj9NunqTeDR52aQ1ed54Lw=s160-c-k-c0x00ffffff-no-rj",
)
# Who the channel is, per format. The news identity is built on the headline -
# what is behind it, what it does not say - and reads as nonsense applied to a
# ship that sank in 1912, so each mode gets its own. An explicit
# CHANNEL_TONE_HINT still overrides both.
_TONE_HINTS = {
    "news": (
        "revela el lado oculto, inquietante o menos contado de cada noticia: que se esconde detras "
        "del titular, que consecuencias no se ven a simple vista, que preguntas incomodas deja "
        "abiertas. El tono es intrigante y directo, pero SIEMPRE basado en hechos verificables de la "
        "propia noticia, nunca en especulacion sin fundamento ni teorias de conspiracion."
    ),
    "topics": (
        "cuenta casos reales de informatica y tecnologia - intrusiones, fraudes, filtraciones, "
        "software que fallo y empresas que se cayeron - explicando EL MECANISMO: que hizo esa "
        "persona exactamente, por que funciono, que fallo tecnico lo permitio y que señal ignoro "
        "alguien. No cuenta que hubo un hackeo, explica COMO se hizo, contado para que lo entienda "
        "quien no sabe de esto pero sin simplificarlo hasta que deje de ser verdad. El tono es "
        "documental, preciso y sobrio: el drama lo ponen los hechos y las cifras, nunca los "
        "adjetivos ni el morbo. Todo anclado en lo documentado, jamas en especulacion."
    ),
}
CHANNEL_TONE_HINT = os.environ.get("CHANNEL_TONE_HINT") or _TONE_HINTS.get(
    CONTENT_MODE, _TONE_HINTS["news"]
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

# Most an AI illustration can cost in a day, counted in images. Google's own
# Vertex quotas are per MINUTE, so they bound how fast money can be spent, not
# how much: at the default 10 a minute a runaway loop could still bill for
# thousands of images in a day. This is the ceiling that actually holds,
# because it is ours. Past it the pipeline goes back to stock footage and fact
# cards, which is the behaviour it already has when Imagen is unavailable, so
# hitting the cap costs a video nothing but the AI illustration.
AI_IMAGES_DAILY_LIMIT = int(os.environ.get("AI_IMAGES_DAILY_LIMIT", "40"))

# Dollars per million output tokens, used to turn the token count Google
# returns into a price per image. THIS IS A DEFAULT, NOT A VERIFIED RATE: 30 is
# the published figure for the Gemini image models this was written against,
# but the 3.x ones are recent and may well be priced differently. It is an
# environment variable precisely so the real number can be put in without
# touching code, and every message that uses it says which rate it used.
AI_IMAGE_USD_PER_MILLION_OUTPUT_TOKENS = float(
    os.environ.get("AI_IMAGE_USD_PER_MILLION_OUTPUT_TOKENS", "30")
)

# Google Cloud TTS reads its credentials from this env var directly.
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", GOOGLE_APPLICATION_CREDENTIALS)
