import logging
import math
import random
import shutil
import subprocess
import time
from pathlib import Path

import requests

from . import ai_images, branding, oficial, real_photos, slides, fotos_propias
from .branding import BACKGROUND_COLOR
from .config import CONTENT_MODE, CHANNEL_NAME, PEXELS_API_KEY, PIXABAY_API_KEY

logger = logging.getLogger(__name__)

PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"
PIXABAY_SEARCH_URL = "https://pixabay.com/api/videos/"

_PEXELS_ORIENTATION = {"9:16": "portrait", "16:9": "landscape"}
_TARGET_DIMENSIONS = {"9:16": (1080, 1920), "16:9": (1920, 1080)}
# Used only if every other query (the scene's own keywords, then a broadened
# version of them) comes up empty. Per format, because the fallback is the one
# clip guaranteed to appear and it should at least belong to the video: a news
# studio behind a sentence about the Titanic is worse than no picture, and that
# is exactly what two scenes of the first Titanic short got.
_LAST_RESORT_QUERIES = {
    "news": "news broadcast studio",
    "topics": "server room racks blinking lights dark",
}
_LAST_RESORT_FALLBACK = "news broadcast studio"
# Showing more than 2 real photos in one shot would make already-short
# scenes feel like a rapid-fire slideshow instead of an actual news video.
_MAX_PHOTOS_PER_SCENE = 2
# Splitting a scene's screen time only makes sense if each resulting photo
# still gets a readable amount of time on screen.
_MIN_SCENE_SECONDS_FOR_MULTI_PHOTO = 6.0
# No single stock clip should hold the screen for much longer than this. A
# scene with a long narration used to get one clip for its whole length -
# one Short ended on a single shot held for 13 seconds, a quarter of the
# video.
#
# These were first set for a 60s Short, where a handful of scenes meant a
# handful of cuts. On a five-minute video the same rule produced 57 stock
# shots, one every five seconds, and that reads as randomness rather than
# pace: none of them illustrates anything in particular, so more of them only
# means more images that do not belong. Cutting the count roughly in third
# still keeps any one shot from outstaying nine seconds.
_MAX_SECONDS_PER_CLIP = 9.0
_MAX_CLIPS_PER_SCENE = 2

# How many scenes must pass between two fact cards. A card beats generic stock
# for a scene with nothing real to show, but a run of them turns the video into
# a slideshow - the complaint this is meant to answer is images that do not
# belong, not images as such. Spacing them keeps a card an accent rather than
# the format.
_MIN_SCENES_BETWEEN_CARDS = 3

# A card is, visually, a black screen with words on it. That is a fine accent
# in the middle of a video and the worst possible opening for a Short, where
# the first seconds are what decides whether a thumb stops. The opening scene
# has to be a picture, whatever else is true about it - and it loses nothing,
# because the fact the card would have stated still goes on screen as the
# corner badge over the image.
_FIRST_SCENE_ELIGIBLE_FOR_CARD = 2

# How long before a face may appear again, and how often in total. Three
# scenes is far enough apart that it reads as returning to somebody rather
# than as a loop; four appearances across a twenty-five scene video is roughly
# how often a documentary cuts back to its subject.
_ESCENAS_ENTRE_REPETICIONES = 3
_MAX_VECES_MISMA_FOTO = 4

# Longest a card may stay on screen. A card holds one still frame for the
# whole scene, so an 8-second scene became 8 seconds of black with four words
# on it - an accent turned into a dead stop. Past this the scene gets imagery
# instead, and the fact rides on the corner badge as it does everywhere else.
_MAX_CARD_SECONDS = 4.0

# Most AI illustrations one video may use. The daily cap in ai_images.py stops
# a runaway; this is the everyday one, and it is what keeps a video's cost
# predictable: at roughly four cents an image, a Short and a long video
# together come to about twenty. Past it the scene falls back to stock footage
# or a card exactly as it did when there was no AI illustration at all.
#
# The Short's share goes to three because the flag filter above frees scenes
# that used to be swallowed by a national emblem before they could ask for an
# illustration - video 60 asked for illustrations and spent nothing, because
# "China", "Espana" and "Portugal" all "found" a photo first. Three leaves a
# six-scene Short at least three shots of real footage, which is the balance
# wanted: the AI image is for what cannot be filmed, not for everything.
_MAX_AI_IMAGES = {"9:16": 3, "16:9": 4}
_MAX_AI_IMAGES_DEFAULT = 2

# A FIXED quota does not survive the video getting longer. Four was sized for
# a twenty-scene video and ran out at scene eight of twenty-four - the sixteen
# scenes after it asked for an illustration and got stock footage of a
# keyboard. One image per four scenes keeps the ratio the number was chosen
# for, and keeps it when the long video grows to fifteen minutes.
#
# The floor is there for a Short, the ceiling because at four cents an image
# this is the largest cash cost in a video and it should stay bounded no
# matter how long a script runs.
_ESCENAS_POR_ILUSTRACION = 4
_MIN_ILUSTRACIONES = 3
_MAX_ILUSTRACIONES = 14


def _cupo_de_ilustraciones(escenas: int, aspect_ratio: str) -> int:
    if aspect_ratio == "9:16":
        return _MAX_AI_IMAGES["9:16"]
    return max(_MIN_ILUSTRACIONES,
               min(_MAX_ILUSTRACIONES, escenas // _ESCENAS_POR_ILUSTRACION))

# requests' `timeout` only limits the wait between two chunks of data, so a
# download that trickles in forever never trips it. These cap the whole
# transfer as well, because a single stuck download is enough to freeze the
# generation thread - and that thread holds the lock that stops two
# generations overlapping, so the bot answers "ya hay una generacion en
# curso" to every /generar from then on.
_DOWNLOAD_TIMEOUT = (10, 30)
_DOWNLOAD_MAX_SECONDS = 120.0
# Deliberately small: the deadline below can only be checked between chunks,
# so a large chunk size would let a slow enough trickle sit inside a single
# read for minutes without the limit ever being looked at.
_DOWNLOAD_CHUNK = 64 << 10


def _search_pexels(query: str, orientation: str) -> list[dict]:
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": 8, "orientation": orientation}
    response = requests.get(PEXELS_SEARCH_URL, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    # Namespaced so an id can never collide with one from another library and
    # wrongly mark a different clip as already used.
    return [dict(v, id=f"pexels-{v['id']}") for v in response.json().get("videos", [])]


def _search_pixabay(query: str, orientation: str) -> list[dict]:
    """Second stock library, reshaped into the same fields as a Pexels result
    so the caller does not care where a clip came from.

    Returns nothing at all when no key is configured, and never raises: this
    is an extra chance at a good clip, so a library being down or rate-limited
    must cost nothing more than that chance."""
    if not PIXABAY_API_KEY:
        return []
    params = {"q": query, "video_type": "all", "per_page": 20, "key": PIXABAY_API_KEY}
    try:
        response = requests.get(PIXABAY_SEARCH_URL, params=params, timeout=30)
        response.raise_for_status()
        hits = response.json().get("hits", [])
    except Exception:
        logger.warning("Busqueda en Pixabay fallida para %r, se sigue solo con Pexels", query, exc_info=True)
        return []

    results = []
    for hit in hits:
        files = [
            {"link": f.get("url"), "width": f.get("width") or 0, "height": f.get("height") or 0}
            for f in (hit.get("videos") or {}).values()
            if f.get("url")
        ]
        if not files:
            continue
        best = max(files, key=lambda f: f["width"] * f["height"])
        results.append(
            {
                "id": f"pixabay-{hit.get('id')}",
                "width": best["width"],
                "height": best["height"],
                "video_files": files,
            }
        )
    return results


def _pick_video_file(video: dict, target_width: int, target_height: int) -> dict:
    return min(
        video["video_files"],
        key=lambda f: abs((f.get("width") or 0) - target_width) + abs((f.get("height") or 0) - target_height),
    )


def fetch_clip_for_scene(keywords: str, out_path: Path, aspect_ratio: str, used_video_ids: set[int]) -> Path:
    orientation = _PEXELS_ORIENTATION.get(aspect_ratio, "landscape")
    target_width, target_height = _TARGET_DIMENSIONS.get(aspect_ratio, (1920, 1080))
    target_is_portrait = target_height > target_width

    def _matches_orientation(video: dict) -> bool:
        return ((video.get("height") or 0) > (video.get("width") or 0)) == target_is_portrait

    # Try the scene's own (now fairly specific) keywords first; a query that
    # happens to have zero Pexels matches falls back to a broader version of
    # itself, then to a universal query, instead of crashing the whole video.
    # Broaden by dropping words from the END, never by keeping only the last
    # one: the country leads these phrases ("mexico city street protest"), so
    # falling back to the tail ("protest") threw away precisely the word
    # keeping the footage in the right country - which is how a Hungarian
    # flag ended up in a scene about Mexico.
    words = keywords.split()
    queries = [keywords]
    for cut in range(len(words) - 1, 0, -1):
        broader = " ".join(words[:cut])
        if broader not in queries:
            queries.append(broader)
    queries.append(_LAST_RESORT_QUERIES.get(CONTENT_MODE, _LAST_RESORT_FALLBACK))

    def _choose(pool: list[dict]) -> dict:
        # Prefer a clip not already used elsewhere in this same video, and
        # pick randomly among the top matches (instead of always the single
        # top result) so the same query doesn't return the identical clip
        # every single time it's searched, in this video or in others.
        fresh = [v for v in pool if v["id"] not in used_video_ids]
        return random.choice((fresh or pool)[:5])

    # A landscape clip in a vertical Short survives only by being cropped to
    # the middle quarter of its frame, which throws away whatever the shot was
    # actually of. A wrong-shaped clip is therefore worth less than a
    # right-shaped clip from a vaguer search, so a query with no correctly
    # oriented result moves on to the broader query instead of settling. They
    # are kept aside all the same: a badly cropped clip still beats no video.
    chosen_video = None
    wrong_shape: list[dict] = []
    for query in queries:
        # Pixabay is only consulted when Pexels has nothing of the right shape
        # for this exact query - a correctly shaped clip from a second library
        # beats a broader, vaguer search of the first one.
        videos = _search_pexels(query, orientation)
        matching = [v for v in videos if _matches_orientation(v)]
        if not matching:
            wrong_shape.extend(videos)
            extra = _search_pixabay(query, orientation)
            matching = [v for v in extra if _matches_orientation(v)]
            wrong_shape.extend(v for v in extra if v not in matching)
            if matching:
                logger.info("Pexels no tenia nada vertical/horizontal para %r; usando Pixabay", query)
        if not matching:
            continue
        chosen_video = _choose(matching)
        break

    if chosen_video is None and wrong_shape:
        logger.info(
            "Sin clips con la orientacion correcta para %r; se usa uno recortado.", keywords
        )
        chosen_video = _choose(wrong_shape)

    if chosen_video is None:
        raise RuntimeError(f"No se encontraron videos de stock ni con la busqueda de respaldo para: {keywords!r}")

    used_video_ids.add(chosen_video["id"])
    video_file = _pick_video_file(chosen_video, target_width, target_height)

    _download_to_file(video_file["link"], out_path)
    return out_path


def _download_to_file(url: str, out_path: Path) -> None:
    """Streams a clip straight to disk under a total time limit.

    Reading into memory first (`response.content`) meant a 4K clip sat in RAM
    in full before being written, on top of the whisper model already loaded
    in the same process; streaming keeps only one chunk at a time."""
    deadline = time.monotonic() + _DOWNLOAD_MAX_SECONDS
    with requests.get(url, timeout=_DOWNLOAD_TIMEOUT, stream=True) as response:
        response.raise_for_status()
        with out_path.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=_DOWNLOAD_CHUNK):
                if time.monotonic() > deadline:
                    raise TimeoutError(f"La descarga de {url} supero los {_DOWNLOAD_MAX_SECONDS:.0f}s")
                fh.write(chunk)


def _clip_de_respaldo(out_path: Path, aspect_ratio: str, duracion: float) -> None:
    """Un fondo liso del color del canal, hecho aqui mismo sin pedirle nada a
    nadie.

    Existe por una razon de dinero. La narracion se paga en el paso 3 y las
    imagenes se buscan en el 4, o sea que CUALQUIER cosa que reviente aqui
    tira unos siete mil quinientos creditos ya gastados. Y habia tres formas
    de reventar, ninguna protegida: que Pexels se caiga o nos limite, que una
    busqueda no devuelva nada, y que una descarga se pase del tiempo.

    Un fondo liso detras de una escena es peor que un clip de archivo. Perder
    el video entero cuando ya esta pagada la voz es muchisimo peor, y encima
    la mayoria de estas escenas llevan encima una foto real o una diapositiva,
    asi que lo que se ve no es un rectangulo vacio.
    """
    ancho, alto = _TARGET_DIMENSIONS.get(aspect_ratio, (1920, 1080))
    r, g, b = BACKGROUND_COLOR
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error",
         "-f", "lavfi", "-i",
         f"color=c=0x{r:02x}{g:02x}{b:02x}:s={ancho}x{alto}:r=30:d={max(duracion, 1.0):.2f}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out_path)],
        check=True,
    )


def fetch_clips_for_scenes(
    scenes: list[dict], out_dir: Path, aspect_ratio: str, scene_durations: list[float], is_sensitive: bool = False,
    creditos: list[str] | None = None,
    marcas: list | None = None,
    caso: str = ""
) -> list[list[tuple[Path, dict | None]]]:
    """Returns, per scene, a list of (clip_path, name_tag) entries - normally
    just one, but up to _MAX_PHOTOS_PER_SCENE when a scene names several
    entities and is long enough to show more than one of them, so a single
    sentence mentioning two parties/institutions doesn't only ever display
    the first one."""
    out_dir.mkdir(parents=True, exist_ok=True)
    clip_entries: list[list[tuple[Path, dict | None]]] = []
    used_video_ids: set[int] = set()
    # Stock clips were already deduplicated, but real photos weren't: an
    # entity named in several scenes (e.g. "Junta Electoral Central") showed
    # the identical picture every time, which read as the video looping.
    # Las imagenes del articulo del caso, cargadas la primera vez que
    # hagan falta: si todas las personas tienen articulo propio no se pide.
    imagenes_del_caso: list[tuple[str, str]] | None = None
    used_photo_urls: set[str] = set()
    # When each photo was last shown, so a face can come back.
    ultima_aparicion: dict[str, int] = {}
    veces_usada: dict[str, int] = {}
    # Far enough back that the first eligible scene can use one.
    last_card_index = -_MIN_SCENES_BETWEEN_CARDS - 1
    ai_images_left = _cupo_de_ilustraciones(len(scenes), aspect_ratio)
    logger.info("Cupo de ilustraciones por IA para este video: %s (%s escenas).",
                ai_images_left, len(scenes))
    for i, scene in enumerate(scenes):
        duration = scene_durations[i] if i < len(scene_durations) else 0.0

        if scene.get("is_intro"):
            width, height = _TARGET_DIMENSIONS.get(aspect_ratio, (1920, 1080))
            card_path = branding.generate_intro_card(out_dir / f"clip_{i:02d}.jpg", width, height)
            clip_entries.append([(card_path, None)])
            continue

        photo_subject = (scene.get("photo_subject") or "").strip()
        # detected_entities comes from a dedicated Claude pass over the
        # final narration (see entity_extraction.py) - far more reliable
        # than the model's own inline photo_subject tagging alone. It's
        # never populated for sensitive stories (pipeline.py skips that
        # call entirely there), since it has no guaranteed way to exclude
        # a crime victim's name the way photo_subject's own prompt rule
        # does - only the model's explicit photo_subject is trusted then.
        detected_entities = [] if is_sensitive else (scene.get("detected_entities") or [])
        extra_candidates = [e.get("name", "").strip() for e in detected_entities if e.get("name", "").strip()]
        candidates = ([photo_subject] if photo_subject else []) + [
            name for name in dict.fromkeys(extra_candidates) if name != photo_subject
        ]
        # The closing scene asks viewers to subscribe, so the channel's own
        # name gets picked up as an entity. Looking it up is pointless, and a
        # loose match would put some unrelated image on screen captioned with
        # the channel name.
        candidates = [name for name in candidates if name.strip().lower() != CHANNEL_NAME.strip().lower()]

        # A slide the script asked for, before the photo lookup rather than
        # after it - so a scene that has a chronology to draw does not spend
        # two Wikipedia requests finding a picture of a campus first.
        #
        # A face beats a slide: if any entity in this scene is a person, their
        # photograph is what the viewer wants and the slide waits. Anything
        # else loses to it. That is the whole point - measured on the first
        # computing video, the "real photos" it found were five university
        # buildings and three corporate logos, and a chronology says more than
        # any of them. When entities were not extracted at all, which is what
        # happens on a sensitive story, the slide wins too: it cannot put a
        # victim on screen, which no photo lookup can promise.
        slide_spec = scene.get("slide")
        if isinstance(slide_spec, dict) and not any(
            e.get("type") == "person" for e in detected_entities
        ):
            width, height = _TARGET_DIMENSIONS.get(aspect_ratio, (1920, 1080))
            frames = slides.render(slide_spec, width, height)
            if frames:
                # Where the narration says each point, when that is known.
                momentos = None
                marca = marcas[i] if marcas and i < len(marcas) else None
                if marca:
                    narracion, tiempos = marca
                    momentos = slides.momentos_de(
                        slide_spec, len(frames), narracion, tiempos, duration
                    )
                clip = slides.construir_clip(
                    frames, out_dir / f"slide_{i:02d}.mp4", duration, momentos=momentos
                )
                if clip is not None:
                    logger.info(
                        "Escena %s: diapositiva %r con %s revelados en %.1fs (%s).",
                        i, slide_spec.get("tipo"), len(frames), duration,
                        "sincronizados con la narracion" if momentos else "repartidos por igual",
                    )
                    clip_entries.append([(clip, None)])
                    continue

        max_photos = _MAX_PHOTOS_PER_SCENE if duration >= _MIN_SCENE_SECONDS_FOR_MULTI_PHOTO else 1
        found: list[tuple[str, Path, str]] = []
        for candidate in candidates:
            if len(found) >= max_photos:
                break
            candidate_path = out_dir / f"clip_{i:02d}_{len(found)}.jpg"
            # A PERSON'S photograph may come back; a building may not.
            #
            # The protagonist of a story is named in half its scenes, and there
            # is usually exactly one free photograph of him. Refusing to repeat
            # it meant that after two scenes, six more that were about Robert
            # Morris fell through to stock footage of a courtroom gavel - a
            # stranger's gavel is not a better picture of him than his own face
            # shown again. A campus is different: it carries no story, so a
            # second look at it is just padding.
            #
            # The gap keeps it from reading as a loop, and the builder's pan
            # alternates direction on each use, so a return is not an identical
            # shot.
            es_persona = candidate in {
                e.get("name", "").strip() for e in detected_entities
                if e.get("type") == "person"
            }
            reutilizables = {
                url for url, cuando in ultima_aparicion.items()
                if es_persona
                and i - cuando >= _ESCENAS_ENTRE_REPETICIONES
                and veces_usada.get(url, 0) < _MAX_VECES_MISMA_FOTO
            }
            # Antes de rendirse: la gente de un caso de sucesos casi nunca
            # tiene articulo propio, pero sus fotos estan dentro del articulo
            # del caso. Buscando "Asunta Basterra" no sale nada; mirando las
            # imagenes de «Caso Asunta», si.
            # Lo primero de todo: si ella puso una foto para esto, es esa. No
            # se compara con nada ni se busca alternativa - lo ha decidido
            # ella, que es de quien es el canal.
            propia = fotos_propias.de(candidate, excluir=used_photo_urls - reutilizables)
            if propia is not None:
                shutil.copyfile(propia, candidate_path)
                result = (candidate_path, str(propia))
            else:
                result = real_photos.fetch_portrait(
                    candidate, candidate_path, exclude_urls=used_photo_urls - reutilizables
                )
            if result is None and caso:
                if imagenes_del_caso is None:
                    imagenes_del_caso = real_photos.imagenes_del_caso(caso)
                result = real_photos.retrato_en_el_caso(
                    candidate, imagenes_del_caso, candidate_path,
                    exclude_urls=used_photo_urls - reutilizables,
                )
            if result is None:
                # Wikidata es la cuarta fuente y es distinta de las otras
                # tres: guarda la foto de una persona aunque el articulo no la
                # lleve dentro, y ficha a gente que no tiene articulo propio -
                # que es lo normal en un caso de sucesos. Ademas dice si lo que
                # ha encontrado es una PERSONA, asi que no puede colar una
                # ciudad llamada Rosario.
                encontrado = oficial.retrato(candidate)
                if encontrado is not None:
                    url_wd, _fichero = encontrado
                    if url_wd not in (used_photo_urls - reutilizables):
                        if real_photos._download(url_wd, candidate_path):
                            result = (candidate_path, url_wd)
            if result is not None:
                photo_path, photo_url = result
                used_photo_urls.add(photo_url)
                ultima_aparicion[photo_url] = i
                veces_usada[photo_url] = veces_usada.get(photo_url, 0) + 1
                if creditos is not None and photo_url.startswith("http"):
                    # Las fotos propias no llevan el credito de Wikimedia: no
                    # vienen de ahi y poner esa atribucion seria falsearla.
                    creditos.append(photo_url)
                role = (
                    (scene.get("photo_subject_role") or "").strip()
                    if candidate == photo_subject
                    else next((e.get("descriptor", "") for e in detected_entities if e.get("name") == candidate), "")
                )
                found.append((candidate, photo_path, role))

        if candidates:
            logger.info(
                "Escena %s: candidatos a foto real %s -> %s",
                i,
                candidates,
                f"encontradas: {[name for name, _, _ in found]}" if found else "ninguna foto encontrada",
            )

        if found:
            # The lower-third caption is for FACES. A name and a role under a
            # photograph of somebody reads as a documentary; the same bar under
            # a building, a logo or a flag reads as a caption explaining the
            # obvious - "BANDERA DE ESPAÑA · bandera" - and looks amateurish.
            # The viewer can see it is a flag. Only a person needs introducing.
            personas = {
                e.get("name", "").strip()
                for e in detected_entities
                if e.get("type") == "person" and e.get("name", "").strip()
            }
            clip_entries.append([
                (path, {"name": name, "role": role} if name in personas else None)
                for name, path, role in found
            ])
            continue

        highlight = (scene.get("on_screen_highlight") or "").strip()
        # A scene with no real subject and a concrete fact to state is better
        # served by the fact than by whatever stock footage a vague search
        # returns. Only where there is something to say, and never twice close
        # together.
        if (
            highlight
            and len(highlight) > 12
            and i >= _FIRST_SCENE_ELIGIBLE_FOR_CARD
            and 0 < duration <= _MAX_CARD_SECONDS
            and i - last_card_index > _MIN_SCENES_BETWEEN_CARDS
        ):
            width, height = _TARGET_DIMENSIONS.get(aspect_ratio, (1920, 1080))
            card_path = out_dir / f"card_{i:02d}.jpg"
            branding.render_fact_card(highlight, width, height).save(card_path, quality=92)
            logger.info("Escena %s: sin sujeto real, se usa tarjeta con %r", i, highlight)
            clip_entries.append([(card_path, None)])
            last_card_index = i
            continue

        ai_image_prompt = (scene.get("ai_image_prompt") or "").strip()
        if ai_image_prompt and ai_images_left <= 0:
            logger.info(
                "Escena %s: pedia ilustracion por IA, pero este video ya ha gastado su cupo de %s.",
                i,
                _cupo_de_ilustraciones(len(scenes), aspect_ratio),
            )
            ai_image_prompt = ""
        if ai_image_prompt:
            ai_images_left -= 1
            image_path = ai_images.generate_image(ai_image_prompt, out_dir / f"clip_{i:02d}.jpg", aspect_ratio)
            if image_path is not None:
                # Same badge the stock-footage branch puts on its first clip:
                # a scene that states a fact should state it whatever kind of
                # image ends up carrying it.
                tag = {"caption": highlight} if highlight else None
                clip_entries.append([(image_path, tag)])
                continue

        # visual_keywords can be intentionally empty when the scene expected a
        # photo/AI image to be used instead; if that failed, fall back to
        # something Pexels can still search for instead of an empty query.
        # photo_subject is deliberately not part of this chain: it is a Spanish
        # proper noun meant for Wikipedia, and Pexels indexes in English, so
        # searching it returns nothing useful - a scene about Pekin searched
        # Pexels for "Pekin" and fell through to generic footage anyway.
        query = (scene.get("visual_keywords") or "").strip() or ai_image_prompt or _LAST_RESORT_QUERIES.get(CONTENT_MODE, _LAST_RESORT_FALLBACK)
        # A long scene gets several clips rather than one held for its whole
        # length. Each search excludes the clips already used, so they differ.
        clip_count = min(_MAX_CLIPS_PER_SCENE, max(1, math.ceil(duration / _MAX_SECONDS_PER_CLIP)))
        # Only the first clip carries the caption: repeating it on every cut
        # of the same scene would make it flash in and out repeatedly.
        scene_entries: list[tuple[Path, dict | None]] = []
        for j in range(clip_count):
            out_path = out_dir / f"clip_{i:02d}_{j}.mp4"
            logger.info("Escena %s: buscando clip %s/%s en Pexels para %r...", i, j + 1, clip_count, query)
            try:
                fetch_clip_for_scene(query, out_path, aspect_ratio, used_video_ids)
            except Exception:
                # La red de seguridad: aqui la narracion YA esta pagada.
                logger.warning(
                    "Escena %s: no se ha podido traer clip para %r; fondo liso.",
                    i, query, exc_info=True,
                )
                # El bucle es enumerate(scenes) desde cero, asi que el indice
                # de la duracion es i, no i-1. Con i-1 la primera escena se
                # llevaba la duracion de la ULTIMA.
                duracion = scene_durations[i] if i < len(scene_durations) else 6.0
                _clip_de_respaldo(out_path, aspect_ratio, duracion)
            tag = {"caption": highlight} if highlight and j == 0 else None
            scene_entries.append((out_path, tag))
        clip_entries.append(scene_entries)
    return clip_entries
