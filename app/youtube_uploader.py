import logging
import re
import shutil
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.auth.exceptions import RefreshError
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
    NARRATION_LANG,
)

# youtube.upload sube el video y nada mas. La pista de subtitulos se sube con
# captions().insert, que pide force-ssl, y por eso desde el primer dia todos
# los videos han subido bien y sus subtitulos han fallado con "Insufficient
# Permission". Los subtitulos incrustados en la imagen se veian igual, asi que
# no se notaba; lo que se perdia es la pista que YouTube LEE para saber de que
# va el video y a quien recomendarselo.
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

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


class AutorizacionCaducada(RuntimeError):
    """El token de YouTube murio. No se arregla solo."""


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
            try:
                creds.refresh(Request())
            except RefreshError as exc:
                # "invalid_grant: Token has been expired or revoked" no se
                # arregla reintentando: hay que volver a autorizar a mano. Lo
                # normal es que la aplicacion de Google siga en modo "Testing",
                # donde los permisos CADUCAN A LOS SIETE DIAS - que es justo lo
                # que llevaba esta. Publicarla quita ese limite.
                raise AutorizacionCaducada(
                    "La autorizacion de YouTube ya no vale (%s). Hay que volver a "
                    "autorizar: 'python -m scripts.authorize_youtube' en tu "
                    "ordenador, y el contenido del token nuevo a la variable "
                    "YOUTUBE_TOKEN_JSON de Railway. Y en Google Cloud, pon la "
                    "aplicacion 'En produccion' o volvera a caducar en una "
                    "semana." % exc
                ) from exc
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



def _nombre_con_palabras(video_path: Path, title: str) -> Path:
    """Copia el fichero con el titulo por nombre antes de subirlo.

    Efecto pequeño y honestamente discutible - YouTube no lo usa como señal de
    posicionamiento - pero es gratis y no puede hacer daño. "caso-asunta-13-
    anos-despues.mp4" en vez de "final_subtitled.mp4". Lo que NO es cierto es
    el mito de que asi "YouTube entiende de que va": de eso se encargan el
    titulo, la descripcion y los subtitulos.
    """
    limpio = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    trozos = [t for t in re.split(r"[^a-zA-Z0-9]+", limpio) if t]
    nombre = "-".join(trozos).lower()[:70] or "video"
    destino = video_path.with_name(f"{nombre}.mp4")
    if destino == video_path:
        return video_path
    try:
        shutil.copyfile(video_path, destino)
        return destino
    except OSError:
        return video_path


def _esperar_a_que_procese(youtube, video_id: str, minutos: int = 12) -> bool:
    """Espera a que YouTube termine de procesar el HD. Devuelve si lo logro.

    ESTE SI ES EL TRUCO DE VERDAD, y es la version cierta de lo que ella
    intuia. El mito dice que hay que dejarlo en privado un rato "para que
    YouTube entienda de que va"; eso es falso. Lo que si pasa es mas prosaico
    y mas grave: al publicar, YouTube todavia esta generando las resoluciones
    altas, y durante esos minutos QUIEN ABRE EL VIDEO LO VE EN 360p.

    Y esos minutos son justo cuando el algoritmo esta midiendo si la gente se
    queda. O sea que la primera tanda de espectadores -la que decide si el
    video se distribuye o se entierra- juzga la peor version que va a existir.

    Cuesta una unidad de cuota por consulta.
    """
    limite = time.time() + minutos * 60
    while time.time() < limite:
        try:
            r = youtube.videos().list(part="processingDetails", id=video_id).execute()
        except HttpError:
            return False
        items = r.get("items") or []
        if not items:
            return False
        estado = items[0].get("processingDetails", {}).get("processingStatus")
        if estado == "succeeded":
            logger.info("Video %s procesado; ya se puede publicar en calidad buena.", video_id)
            return True
        if estado == "failed":
            logger.warning("YouTube dice que fallo el procesado de %s.", video_id)
            return False
        time.sleep(20)
    logger.warning("El video %s sigue procesando tras %s minutos; se publica igual.",
                   video_id, minutos)
    return False


def _hacer_publico(youtube, video_id: str) -> None:
    youtube.videos().update(
        part="status",
        body={"id": video_id, "status": {"privacyStatus": "public",
                                         "selfDeclaredMadeForKids": False}},
    ).execute()
    logger.info("Video %s publicado.", video_id)

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
            # These two are not cosmetic. defaultAudioLanguage is the field
            # YouTube uses to decide who gets recommended the video, and it
            # is the same field the niche study filtered on to find English
            # channels in the first place. An English video tagged "es" is
            # served to a Spanish-speaking audience: the whole point of
            # writing it in English fails at distribution rather than at
            # content, which is the hardest kind of failure to notice.
            "defaultLanguage": NARRATION_LANG,
            "defaultAudioLanguage": NARRATION_LANG,
        },
        "status": status,
    }
    # Si el destino es publico, se sube EN PRIVADO y se publica despues de que
    # YouTube termine de procesar el HD. Ver _esperar_a_que_procese.
    publicar_al_final = (status.get("privacyStatus") == "public")
    if publicar_al_final:
        status = {**status, "privacyStatus": "private"}
        body_status = status
    else:
        body_status = status
    body["status"] = body_status

    subir = _nombre_con_palabras(video_path, title)
    media = MediaFileUpload(str(subir), chunksize=-1, resumable=True, mimetype="video/mp4")
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

    if publicar_al_final:
        _esperar_a_que_procese(youtube, video_id)
        try:
            _hacer_publico(youtube, video_id)
        except HttpError as exc:
            # Queda privado y visible en Studio: mejor eso que perderlo.
            logger.error("El video %s se subio pero no se ha podido publicar: %s", video_id, exc)
            raise

    if subir != video_path:
        subir.unlink(missing_ok=True)

    return video_id, publish_at


def upload_captions(video_id: str, srt_path: Path, language: str = NARRATION_LANG) -> None:
    youtube = build("youtube", "v3", credentials=get_credentials())
    body = {"snippet": {"videoId": video_id, "language": language, "name": "Español", "isDraft": False}}
    media = MediaFileUpload(str(srt_path), mimetype="application/octet-stream")
    youtube.captions().insert(part="snippet", body=body, media_body=media).execute()
