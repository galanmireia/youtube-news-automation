import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from .config import (
    YOUTUBE_CLIENT_SECRETS_FILE,
    YOUTUBE_PRIVACY_STATUS,
    YOUTUBE_PUBLISH_DELAY_MINUTES,
    YOUTUBE_TOKEN_FILE,
)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# YouTube caps the combined tags string (joined with commas) at 500 characters.
MAX_TAGS_CHARS = 480

logger = logging.getLogger(__name__)


def _fit_tags(tags: list[str]) -> list[str]:
    fitted = []
    used = 0
    for tag in tags:
        tag = tag.strip()
        if not tag:
            continue
        added = len(tag) + (1 if fitted else 0)  # account for the joining comma
        if used + added > MAX_TAGS_CHARS:
            break
        fitted.append(tag)
        used += added
    return fitted


def get_credentials() -> Credentials:
    """Loads a cached OAuth token, refreshing it if needed. The very first
    token must be generated locally (see scripts/authorize_youtube.py)
    since the interactive consent screen can't run on a headless server."""
    token_path = Path(YOUTUBE_TOKEN_FILE)
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(YOUTUBE_CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json())

    return creds


def _publish_status() -> tuple[dict, datetime | None]:
    """Builds the status block, and says when the video will actually be live.

    A scheduled upload is a private video carrying a publishAt time - YouTube
    ignores publishAt on anything that is already public, so the two have to
    be set together. Returns the time it will go live, or None if it goes live
    on upload.

    Holding a video back is not an algorithmic trick; YouTube gives no
    advantage to a video that sat private first. What the delay actually buys
    is that the high-resolution transcode has finished before anyone watches:
    a video that goes public the instant it finishes uploading is often only
    available in 360p for its first minutes, which is exactly when its
    retention is being measured."""
    if YOUTUBE_PUBLISH_DELAY_MINUTES <= 0 or YOUTUBE_PRIVACY_STATUS != "public":
        return {"privacyStatus": YOUTUBE_PRIVACY_STATUS, "selfDeclaredMadeForKids": False}, None

    publish_at = datetime.now(timezone.utc) + timedelta(minutes=YOUTUBE_PUBLISH_DELAY_MINUTES)
    return (
        {
            "privacyStatus": "private",
            "publishAt": publish_at.isoformat().replace("+00:00", "Z"),
            "selfDeclaredMadeForKids": False,
        },
        publish_at,
    )


def upload_video(
    video_path: Path, thumbnail_path: Path, title: str, description: str, tags: list[str]
) -> tuple[str, datetime | None]:
    """Uploads the video and returns its id together with the moment it goes
    public, which is None when it is already public (or staying private)."""
    youtube = build("youtube", "v3", credentials=get_credentials())

    status, publish_at = _publish_status()
    if publish_at is not None:
        logger.info("Subiendo en privado, publicacion programada para %s UTC.", publish_at.strftime("%Y-%m-%d %H:%M"))

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": _fit_tags(tags),
            "categoryId": "25",  # News & Politics
            "defaultLanguage": "es",
            "defaultAudioLanguage": "es",
        },
        "status": status,
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = response["id"]

    try:
        youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(thumbnail_path))).execute()
    except HttpError as exc:
        # Custom thumbnails require a phone-verified channel; the video itself
        # already uploaded fine, so this shouldn't fail the whole operation.
        logger.warning("No se pudo establecer la miniatura personalizada para %s: %s", video_id, exc)

    return video_id, publish_at


def upload_captions(video_id: str, srt_path: Path, language: str = "es") -> None:
    youtube = build("youtube", "v3", credentials=get_credentials())
    body = {"snippet": {"videoId": video_id, "language": language, "name": "Español", "isDraft": False}}
    media = MediaFileUpload(str(srt_path), mimetype="application/octet-stream")
    youtube.captions().insert(part="snippet", body=body, media_body=media).execute()
