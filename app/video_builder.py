import logging
import shutil
import subprocess
import threading
import tempfile
import time
from pathlib import Path

from . import branding

logger = logging.getLogger(__name__)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}

# How long the name tag takes to slide in/out. Kept short and the hold time
# capped (see _build_photo_segment) so the tag reads as a temporary caption
# instead of a fixture stuck on screen for the whole shot.
_TAG_SLIDE_SECONDS = 0.4
_TAG_MAX_HOLD_SECONDS = 3.5

# A still photo/AI image held for several seconds with zero motion reads as
# "frozen" - a slow, subtle zoom (the classic "Ken Burns" documentary
# technique) gives every static shot its own life instead of only the stock
# video clips ever having any movement. Kept small (12% max) so it never
# creeps in far enough to crop a face/logo near the edge of the frame.
# Un 12% repartido en todo el plano es una deriva que no se ve. En vertical el
# plano dura dos segundos y medio, asi que un 26% se nota y no marea.
_ZOOM_MAX = 1.12
_ZOOM_MAX_VERTICAL = 1.26
_SOBRE_ESCALA_VERTICAL = 1.35
_ZOOM_FPS = 30

# Filling the empty space around a photo with a blurred, darkened copy of
# itself instead of black bars. Cropping to fill was tried and is not safe
# at any threshold: normal photos (roughly square, e.g. a building shot)
# still left huge bars, while a wide wordmark logo that did cross the
# threshold got cropped down to two unreadable letters. Blur-fill never
# crops, so a face, a logo or a building always stays whole.
_BLUR_DOWNSCALE = 6
_BLUR_SIGMA = 6

# How much of a photo's width may be cropped away to make it fill more of the
# frame. Fitting a photo whole inside a 9:16 frame is safe but tiny: a normal
# 16:9 press photo ends up 32% of the screen height, a thin strip floating in
# blur, and a video whose scenes are all Wikipedia photos becomes a slideshow
# of thin strips. Allowing a quarter of the width to go lifts that same photo
# to 42%, and lifts a portrait one to the full height.
_MAX_PHOTO_SIDE_CROP = 0.25

# Hard cuts between every scene read as abrupt; a short crossfade is what
# makes a cut feel deliberate. Kept brief - a long dissolve on a news video
# looks sluggish.
_TRANSITION_SECONDS = 0.25


# No single ffmpeg call here should come close to this: the slowest one
# measured (crossfading seven 1080x1920 segments) runs in under a minute on
# four cores. The limit exists because a generation stopped dead inside this
# stage for 25 minutes at roughly zero CPU - blocked, not working - and with
# no limit it would have waited for ever. Raising turns that into an ordinary
# variant failure, which the pipeline already catches, cleans up and reports.
_FFMPEG_TIMEOUT_SECONDS = 8 * 60

# A call is stuck when it stops making progress - not when it has been running
# a while, and not when its output file stops growing. Both of those proxies
# were tried and both killed healthy work: the clock took out the crossfade on
# video 53, and the file size took out videos 59, 61 and 62, because the mp4
# muxer writes in bursts and a plateau between two flushes is indistinguishable
# from a hang if the file is all you look at. _run watches ffmpeg's own
# out_time instead, which is why this threshold can stay tight.
_FFMPEG_STALL_SECONDS = 90

# How often a still-running call is checked and reports that it is alive.
# ffmpeg buffers its logging until it exits, so without this a long call looks
# identical to a hung one in the logs.
_FFMPEG_POLL_SECONDS = 30


def _run(cmd: list[str], step: str = "ffmpeg", timeout: float = _FFMPEG_TIMEOUT_SECONDS) -> None:
    """Runs one ffmpeg call, killing it if it stalls or runs past the ceiling.

    Two different failures are being guarded against. A stall - blocked at
    roughly zero CPU, never finishing on its own - is caught by watching how
    far into the output ffmpeg says it has encoded: no advance for
    _FFMPEG_STALL_SECONDS means stuck, whatever the elapsed time says. The
    timeout is only a backstop for a call that keeps working for ever.

    Progress is read from ffmpeg's own -progress stream rather than from the
    size of the output file, and that distinction is the whole point. The mp4
    muxer buffers: measured on an idle machine, a three-way crossfade left the
    output file at zero bytes for five seconds while it was demonstrably
    encoding, then grew in quarter-megabyte steps with three-second plateaus
    between them. On a loaded box - Railway's eight cores were pegged at their
    limit the morning this was found - those plateaus stretch past any
    threshold worth setting, and the watchdog kills ffmpeg for the crime of
    being slow. The frozen sizes in the logs that looked like hangs, 16.0 MB
    and 1.0 MB and 10.2 MB, are flush boundaries. out_time advances smoothly
    whatever the muxer is doing, and stops dead on a real hang, which is
    exactly the signal wanted.

    stderr goes to a temporary file rather than a pipe: a pipe can fill and
    deadlock the child while nobody is reading it, and ffmpeg is talkative.
    stdout is a pipe, but it only ever carries the progress stream, which is
    drained continuously by the reader thread below."""
    started = time.monotonic()
    # Global options, so they go before the first input. -nostdin stops ffmpeg
    # competing for the parent's stdin when it is run from a service.
    cmd = [cmd[0], "-nostdin", "-progress", "pipe:1", *cmd[1:]]
    # The output file is always the last argument of every command built here.
    out_path = Path(cmd[-1])

    def out_size() -> int:
        try:
            return out_path.stat().st_size
        except OSError:
            return 0

    with tempfile.TemporaryFile() as err_file:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=err_file, text=True, bufsize=1
        )
        # Written by the reader thread, read by the loop below. A plain dict is
        # enough: one writer, one reader, and neither cares about a torn read
        # of a pair it will see again a second later.
        progress = {"encoded": -1.0, "since": time.monotonic()}

        def drain_progress() -> None:
            for line in process.stdout:
                key, _, raw = line.strip().partition("=")
                # ffmpeg reports microseconds as out_time_us and older builds
                # milliseconds as out_time_ms; either can read "N/A" before the
                # first frame is out.
                if key not in ("out_time_us", "out_time_ms"):
                    continue
                try:
                    encoded = int(raw) / (1e6 if key == "out_time_us" else 1e3)
                except ValueError:
                    continue
                if encoded > progress["encoded"]:
                    progress.update(encoded=encoded, since=time.monotonic())

        reader = threading.Thread(target=drain_progress, daemon=True)
        reader.start()

        while True:
            try:
                returncode = process.wait(timeout=_FFMPEG_POLL_SECONDS)
                break
            except subprocess.TimeoutExpired:
                pass

            now = time.monotonic()
            logger.info(
                "  ffmpeg %s sigue: %.0fs, codificados %.1fs, salida %.1f MB",
                step, now - started, max(0.0, progress["encoded"]), out_size() / 1e6,
            )
            if now - progress["since"] >= _FFMPEG_STALL_SECONDS:
                process.kill()
                process.wait()
                raise RuntimeError(
                    f"ffmpeg atascado en '{step}': lleva {now - progress['since']:.0f}s "
                    f"sin avanzar (codificados {max(0.0, progress['encoded']):.1f}s). Proceso matado."
                )
            if now - started >= timeout:
                process.kill()
                process.wait()
                raise RuntimeError(f"ffmpeg bloqueado en '{step}' mas de {timeout:.0f}s, proceso matado")

        reader.join(timeout=5)

        logger.info("  ffmpeg %s: %.1fs", step, time.monotonic() - started)
        if returncode != 0:
            # The exit code alone is undebuggable - ffmpeg's actual error (bad
            # filter syntax, missing font, etc.) is on stderr.
            err_file.seek(0)
            stderr_tail = err_file.read().decode(errors="replace")[-2000:]
            raise RuntimeError(f"ffmpeg fallo en '{step}' (codigo {returncode}): {stderr_tail}")


# A photo that does not match the frame's shape has two possible fates and
# until now only got the worse one. Fitting it whole leaves it floating in a
# band of blur - an ordinary 16:9 press photo covers 42% of a 9:16 screen, and
# a Short made of those reads as a badly cropped repost. Filling the frame and
# sliding across the photo instead shows all of it, over time, at full size.
# That is the move a human editor makes, and it is why the bars were never
# necessary.
#
# The pan uses the middle of the available travel rather than edge to edge, so
# a shot never opens or closes on the extreme rim of a picture, where the
# subject almost never is.
_PAN_TRAVEL_FRACTION = 0.70

# Below this the crop stops being a crop and becomes a keyhole: less than this
# share of the long side surviving means a panorama reduced to a crawling
# sliver, and there the blurred background genuinely is the better answer.
_MIN_PHOTO_RETAINED = 0.18

# Travel smaller than this is not a movement, it is a jitter - a photo already
# close to the frame's shape should hold still and let the Ken Burns zoom do
# the work instead.
_MIN_PAN_PIXELS = 40

# How fast the frame may travel across the photo, as a share of its own width
# per second. Without a cap the travel is simply "all of it, over the length
# of the shot", which on a 16:9 photo in a four-second scene works out at 38%
# of the frame every second - a whip-pan that is harder to watch than the bars
# it replaced. Eight per cent is a drift: enough that the shot is alive,
# slow enough to read what is in it. Where that means not reaching the ends of
# the photo, not reaching them is the right answer.
_MAX_PAN_SPEED = 0.08
_MAX_PAN_SPEED_VERTICAL = 0.22


def _probe_image_size(path: Path) -> tuple[int, int] | None:
    """The photo's pixel size, needed to decide between filling and padding.
    None when ffprobe cannot read it, which sends the caller down the old
    blurred-background path rather than guessing."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0:s=x",
            str(path),
        ],
        capture_output=True,
        timeout=30,
    )
    try:
        w, h = result.stdout.decode().strip().split("x")[:2]
        return (int(w), int(h)) if int(w) > 0 and int(h) > 0 else None
    except ValueError:
        return None


def _photo_fill_filter(
    image_w: int, image_h: int, width: int, height: int, duration: float, backwards: bool = False
) -> tuple[str, bool] | None:
    """Scales the photo until it covers the frame and slides the frame across
    it for the length of the shot. Returns the filter and whether it actually
    moves, or None when covering would cost too much of the picture, leaving
    the caller to pad instead."""
    # SOBRE-ESCALADO A PROPOSITO EN VERTICAL, y aqui estaba el motivo de que no
    # se moviera nada.
    #
    # La camara solo se movia si la imagen DESBORDABA el marco, porque el
    # recorrido es justo lo que sobra. Y una ilustracion generada ya en 9:16
    # encaja exacta: recorrido cero. Asi que en los Shorts lo unico que se
    # movia era el zoom del 12%, repartido ademas en planos de hasta nueve
    # segundos. Un dibujo bueno y quieto sigue siendo un dibujo quieto.
    #
    # Ahora en vertical se agranda un 35% a proposito para que HAYA por donde
    # moverse: un empujon cerrado sobre la cubierta, un barrido por el fuego.
    # Se pierde un tercio del dibujo en cada plano, y esta bien: con cuatro
    # planos por escena se ve entero igual, a trozos y con movimiento, que es
    # justo lo contrario de enseñarlo completo y quieto.
    cover = max(width / image_w, height / image_h)
    if height > width:
        cover *= _SOBRE_ESCALA_VERTICAL
    shown_w, shown_h = image_w * cover, image_h * cover
    # Whichever axis overflows is the one being cropped; the other fits exactly.
    retained = min(width / shown_w, height / shown_h)
    if retained < _MIN_PHOTO_RETAINED:
        return None

    scaled_w = max(width, int(shown_w // 2 * 2))
    scaled_h = max(height, int(shown_h // 2 * 2))
    travel_x, travel_y = scaled_w - width, scaled_h - height

    def used_travel(travel: int, extent: int) -> float:
        if duration <= 0:
            return 0.0
        velocidad = _MAX_PAN_SPEED_VERTICAL if height > width else _MAX_PAN_SPEED
        return min(travel * _PAN_TRAVEL_FRACTION, velocidad * extent * duration)

    moves = max(used_travel(travel_x, width), used_travel(travel_y, height)) >= _MIN_PAN_PIXELS

    def sweep(travel: int, extent: int) -> str:
        used = used_travel(travel, extent)
        if used < _MIN_PAN_PIXELS:
            return f"{travel // 2}"
        start, end = (travel - used) / 2, (travel + used) / 2
        if backwards:
            start, end = end, start
        return f"'{start:.1f}+({end - start:.1f})*min(t/{duration:.3f}\,1)'"

    chain = f"scale={scaled_w}:{scaled_h},crop={width}:{height}:x={sweep(travel_x, width)}:y={sweep(travel_y, height)}"
    return chain, moves


def _photo_background_filter(width: int, height: int) -> str:
    """Lays the photo as large as it will go over a blurred, darkened copy of
    itself, so a photo whose shape doesn't match the frame fills the screen
    instead of floating between black bars. The blur is done on a downscaled
    copy and then scaled back up - far cheaper than blurring at full
    resolution, and the upscale smooths it further.

    The photo is fitted into a box wider than the frame and then cropped back
    to it, which is what lets it come out bigger than a plain fit would give.
    _MAX_PHOTO_SIDE_CROP sets how much wider that box is, and so how much of
    the sides may be lost; the crop is centred, and anything already narrower
    than the frame is left untouched by it."""
    small_w, small_h = max(2, width // _BLUR_DOWNSCALE), max(2, height // _BLUR_DOWNSCALE)
    box_w = max(width, round(width / (1 - _MAX_PHOTO_SIDE_CROP)))
    return (
        "split=2[blurbase][fitbase];"
        f"[blurbase]scale={small_w}:{small_h}:force_original_aspect_ratio=increase,"
        f"crop={small_w}:{small_h},gblur=sigma={_BLUR_SIGMA},scale={width}:{height},"
        "eq=brightness=-0.12[blurred];"
        f"[fitbase]scale={box_w}:{height}:force_original_aspect_ratio=decrease,"
        f"crop=min(iw\,{width}):min(ih\,{height})[fitted];"
        "[blurred][fitted]overlay=(W-w)/2:(H-h)/2"
    )


def _ken_burns_filter(width: int, height: int, duration: float, zoom_out: bool = False) -> str:
    frames = max(1, round(duration * _ZOOM_FPS))
    tope = _ZOOM_MAX_VERTICAL if height > width else _ZOOM_MAX
    increment = (tope - 1) / frames
    # Alternating zoom-in and zoom-out between shots (instead of every single
    # shot doing the exact same push-in) reads as more deliberately dynamic
    # rather than one repeated motion.
    if zoom_out:
        z_expr = f"if(eq(on,0),{tope},max(zoom-{increment:.6f},1))"
    else:
        z_expr = f"min(zoom+{increment:.6f},{tope})"
    return f"zoompan=z='{z_expr}':d={frames}:s={width}x{height}:fps={_ZOOM_FPS}"


def _build_caption_over_still(
    image_path: Path, duration: float, width: int, height: int, caption: str,
    out_path: Path, tmp_dir: Path, key: str, vf_bg: str,
) -> None:
    """A still with the scene's key fact in the corner, the same box a stock
    clip gets - for pictures with no real subject to name."""
    if duration < 1.5:
        _run(["ffmpeg", "-y", "-loop", "1", "-i", str(image_path), "-t", str(duration),
              "-vf", vf_bg, "-r", str(_ZOOM_FPS), str(out_path)])
        return
    box_width, box_height = int(width * 0.42), int(height * 0.16)
    box_png = tmp_dir / f"stillcap_{key}.png"
    branding.render_highlight_box(caption, box_width, box_height).save(box_png)
    margin = int(width * 0.03)
    slide = _TAG_SLIDE_SECONDS
    hold = min(_TAG_MAX_HOLD_SECONDS, max(1.0, duration - 2 * slide))
    hold_end = slide + hold
    slide_out_end = min(duration, hold_end + slide)
    hidden_x, shown_x = -box_width, margin
    x_expr = (
        f"if(lt(t,{slide}),{hidden_x}+({shown_x}-{hidden_x})*(t/{slide}),"
        f"if(lt(t,{hold_end}),{shown_x},"
        f"if(lt(t,{slide_out_end}),{shown_x}+({hidden_x}-{shown_x})*((t-{hold_end})/({slide_out_end}-{hold_end})),{hidden_x})))"
    )
    filter_complex = f"[0:v]{vf_bg}[bg];[1:v]format=rgba[fg];[bg][fg]overlay=x='{x_expr}':y={margin}:shortest=1[outv]"
    _run([
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image_path),
        "-loop", "1", "-i", str(box_png),
        "-t", str(duration),
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-r", str(_ZOOM_FPS),
        str(out_path),
    ])


def _build_photo_segment(
    image_path: Path, duration: float, width: int, height: int, tag: dict | None, out_path: Path, tmp_dir: Path, key: str
) -> None:
    zoom_out = int(key.split("_")[0]) % 2 == 1

    # Filling the frame and panning is the first choice; the blurred
    # background is the fallback for a photo too extreme to crop and for one
    # ffprobe could not measure. A shot that already pans does not also zoom -
    # one deliberate move reads as camera work, two at once read as a screen
    # saver - so the Ken Burns push is added only when the photo sits still.
    size = _probe_image_size(image_path)
    fill = _photo_fill_filter(*size, width, height, duration, zoom_out) if size else None
    if fill is not None:
        chain, moves = fill
        vf_bg = chain if moves else f"{chain},{_ken_burns_filter(width, height, duration, zoom_out)}"
    else:
        vf_bg = f"{_photo_background_filter(width, height)},{_ken_burns_filter(width, height, duration, zoom_out)}"

    # Two kinds of still reach this function and they want different labels. A
    # real photograph of a named subject gets the name bar along the bottom
    # ("TRIBUNAL SUPREMO DE ESPAÑA / Maximo tribunal de España"). An AI
    # illustration has no name to put there - naming an invented picture would
    # be a lie - so it takes the same corner fact box a stock clip gets.
    #
    # Until today this could not happen: the AI branch produced no images at
    # all while Imagen was unreachable, so its caption tag never arrived here
    # and the code read tag["name"] unconditionally. The first video that
    # actually generated an illustration crashed on it.
    caption = (tag or {}).get("caption", "").strip() if tag else ""
    if tag and not tag.get("name") and caption:
        _build_caption_over_still(image_path, duration, width, height, caption, out_path, tmp_dir, key, vf_bg)
        return

    if not tag or not tag.get("name") or duration < 1.5:
        _run(
            [
                "ffmpeg", "-y",
                "-loop", "1", "-i", str(image_path),
                "-t", str(duration),
                "-vf", vf_bg,
                "-r", str(_ZOOM_FPS),
                str(out_path),
            ]
        )
        return

    bar_height = branding.name_tag_bar_height(height)
    tag_png = tmp_dir / f"tag_{key}.png"
    branding.render_name_tag_bar(tag["name"], tag.get("role", ""), width, bar_height).save(tag_png)

    # Slide up from fully off-screen (y=height) to its resting position near
    # the bottom, hold briefly, then slide back down and stay hidden for the
    # rest of the shot - instead of sitting fixed on screen the whole time.
    slide = _TAG_SLIDE_SECONDS
    hold = min(_TAG_MAX_HOLD_SECONDS, max(1.0, duration - 2 * slide))
    hold_end = slide + hold
    slide_out_end = min(duration, hold_end + slide)
    hidden_y, shown_y = height, height - bar_height
    y_expr = (
        f"if(lt(t,{slide}),{hidden_y}-({hidden_y}-{shown_y})*(t/{slide}),"
        f"if(lt(t,{hold_end}),{shown_y},"
        f"if(lt(t,{slide_out_end}),{shown_y}+({hidden_y}-{shown_y})*((t-{hold_end})/({slide_out_end}-{hold_end})),{hidden_y})))"
    )
    filter_complex = f"[0:v]{vf_bg}[bg];[1:v]format=rgba[fg];[bg][fg]overlay=x=0:y='{y_expr}':shortest=1[outv]"
    _run(
        [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(image_path),
            "-loop", "1", "-i", str(tag_png),
            "-t", str(duration),
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-r", str(_ZOOM_FPS),
            str(out_path),
        ]
    )


def _build_color_segment(duration: float, width: int, height: int, out_path: Path) -> None:
    """Un plano liso del color del canal. El ultimo recurso del montaje.

    No lee ningun fichero ni monta ningun grafo de filtros, o sea que no tiene
    de donde fallar: es lo que se pone cuando el clip de una escena rompe
    ffmpeg. Sale sobrio, y con la narracion y los subtitulos encima se lee
    como una pausa, no como un error.
    """
    _run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=0x101418:s={width}x{height}:r={_ZOOM_FPS}",
        "-t", f"{duration:.3f}",
        "-pix_fmt", "yuv420p",
        str(out_path),
    ])


def _build_video_clip_segment(
    clip_path: Path, duration: float, width: int, height: int, tag: dict | None, out_path: Path, tmp_dir: Path, key: str
) -> None:
    # setparams PRIMERO, y esto es lo que tiro el largo del caso Asunta en la
    # escena 24 de 31, despues de pagar la narracion entera:
    #
    #   yuv420p(tv, reserved/reserved/smpte170m, progressive)
    #   [graph -1 input from stream 0:0] Invalid color space
    #   [vf#0:0] Error reinitializing filters!
    #   Task finished with error code: -22 (Invalid argument)
    #
    # Ese "reserved/reserved" no es un color raro: es un hueco de la norma que
    # no significa nada, y ffmpeg se niega a montar el filtro con el. Venia de
    # un clip de Pexels, o sea que no hace falta material raro para toparselo:
    # basta con que a alguien se le colase mal una etiqueta al subirlo.
    #
    # Como no se puede mirar cada clip antes de bajarlo, se le imponen
    # etiquetas validas a la entrada. setparams solo reescribe los metadatos,
    # no toca un pixel, asi que a un clip sano no le hace nada.
    vf = ("setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709,"
          f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}")
    caption = (tag or {}).get("caption")

    if not caption or duration < 1.5:
        _run(
            [
                "ffmpeg", "-y",
                "-stream_loop", "-1", "-i", str(clip_path),
                "-t", str(duration),
                "-vf", vf,
                "-an",
                "-r", "30",
                str(out_path),
            ]
        )
        return

    # A generic stock clip has no real photo tying it to what's being said -
    # slide in a small caption box with the scene's own key fact (top-left)
    # so the point doesn't get lost, then slide it back out.
    box_width, box_height = int(width * 0.42), int(height * 0.16)
    box_png = tmp_dir / f"highlight_{key}.png"
    branding.render_highlight_box(caption, box_width, box_height).save(box_png)

    margin = int(width * 0.03)
    slide = _TAG_SLIDE_SECONDS
    hold = min(_TAG_MAX_HOLD_SECONDS, max(1.0, duration - 2 * slide))
    hold_end = slide + hold
    slide_out_end = min(duration, hold_end + slide)
    hidden_x, shown_x = -box_width, margin
    x_expr = (
        f"if(lt(t,{slide}),{hidden_x}+({shown_x}-{hidden_x})*(t/{slide}),"
        f"if(lt(t,{hold_end}),{shown_x},"
        f"if(lt(t,{slide_out_end}),{shown_x}+({hidden_x}-{shown_x})*((t-{hold_end})/({slide_out_end}-{hold_end})),{hidden_x})))"
    )
    filter_complex = f"[0:v]{vf}[bg];[1:v]format=rgba[fg];[bg][fg]overlay=x='{x_expr}':y={margin}:shortest=1[outv]"
    _run(
        [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(clip_path),
            "-loop", "1", "-i", str(box_png),
            "-t", str(duration),
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-r", "30",
            str(out_path),
        ]
    )


def _build_scene_segment(
    entries: list[tuple[Path, dict | None]], duration: float, width: int, height: int, out_path: Path, tmp_dir: Path, index: int
) -> None:
    if len(entries) == 1:
        path, tag = entries[0]
        if path.suffix.lower() in IMAGE_SUFFIXES:
            _build_photo_segment(path, duration, width, height, tag, out_path, tmp_dir, str(index))
        else:
            _build_video_clip_segment(path, duration, width, height, tag, out_path, tmp_dir, str(index))
        return

    # Multiple real photos found for this one scene (e.g. two political
    # parties named in the same sentence): show them as a quick slideshow
    # instead of only ever picking the first match, for a more dynamic video.
    per = duration / len(entries)
    sub_paths = []
    for j, (path, tag) in enumerate(entries):
        sub_out = tmp_dir / f"seg_{index:02d}_{j}.mp4"
        if path.suffix.lower() in IMAGE_SUFFIXES:
            _build_photo_segment(path, per, width, height, tag, sub_out, tmp_dir, f"{index}_{j}")
        else:
            _build_video_clip_segment(path, per, width, height, tag, sub_out, tmp_dir, f"{index}_{j}")
        sub_paths.append(sub_out)

    concat_list = tmp_dir / f"subconcat_{index:02d}.txt"
    concat_list.write_text("\n".join(f"file '{p.resolve()}'" for p in sub_paths))
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(out_path)])


# Crossfading every scene in one ffmpeg call means every segment is opened and
# decoded at once, and the filter graph holds frames for all of them. Measured
# at 1920x1080: 7 segments peak at 1.57GB, 14 at 2.28GB, 21 at 3.00GB. A long
# video hit 21 scenes, and on top of what the bot process already holds that was
# enough for the kernel to SIGKILL ffmpeg mid-join (exit code -9), losing the
# whole video. Capping encoder threads does not help (3.00 -> 2.82GB for 50%
# more time) and neither does capping filter threads (2.97GB) - the frames are
# the cost, so the only real fix is to hold fewer inputs at a time.
#
# Lowered from 6 to 3 after a six-way join stalled outright: the output file
# sat frozen at 16MB for two minutes until the watchdog killed it, and an
# earlier one returned 10.93 seconds where 57.63 were asked for. Both had six
# segments, all of them rendered from stills, and the offsets going in were
# correct in both cases - so the arithmetic was never the problem, the size of
# the graph was. Three inputs per call turns one fragile filter graph into a
# few small ones, at the price of joining twice. Crossfades have cost more time
# today than every other part of the build put together; making them boring is
# worth more than making them fast.
_MAX_JOIN_INPUTS = 3

# Slack added to every segment that is not the last. Without it each segment
# is rendered to exactly the length its crossfade consumes and no more, so the
# margin is zero and any rounding makes it negative - at which point xfade
# waits for frames that will never arrive, which hangs rather than fails. A
# real case: a transition needed material up to 41.958s and the running video
# ended at 41.942s, sixteen milliseconds short, and the call sat there until
# it was killed. The slack is never seen: it sits past the crossfade that
# consumes it, and it cannot lengthen the video either, since the total is
# fixed by the last segment, which does not get it.
_JOIN_MARGIN_SECONDS = 0.2

# How far short a crossfaded join may come out before it is thrown away and
# redone with hard cuts. Generous, because ordinary rounding costs fractions of
# a second; this is here to catch a collapse, not a wobble.
_MAX_JOIN_SHORTFALL_SECONDS = 2.0


def _dimensiones(path: Path) -> tuple[int, int] | None:
    """The exact pixel size of a rendered segment."""
    try:
        salida = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(path)],
            capture_output=True, text=True, timeout=30, check=True,
        ).stdout.strip()
        ancho, alto = salida.split("x")[:2]
        return int(ancho), int(alto)
    except Exception:
        return None


def _join_segments(segment_paths: list[Path], frame_marks: list[int], work_dir: Path, out_path: Path) -> Path:
    """Joins the scene segments with a short crossfade between them instead
    of hard cuts. Each transition is centred on the scene boundary, so the
    new image is fully up by the time the narration is properly into the new
    scene, and the total length still matches the narration.

    Long videos are joined in groups and the groups joined together, so no
    single ffmpeg call ever holds more than _MAX_JOIN_INPUTS segments open."""
    if len(segment_paths) > _MAX_JOIN_INPUTS:
        return _join_in_groups(segment_paths, frame_marks, work_dir, out_path)
    if len(segment_paths) == 1:
        concat_list_path = work_dir / "concat_list.txt"
        concat_list_path.write_text(f"file '{segment_paths[0].resolve()}'")
        _run(
            [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", str(concat_list_path),
                "-c", "copy",
                str(out_path),
            ]
        )
        return out_path

    inputs: list[str] = []
    for path in segment_paths:
        inputs += ["-i", str(path)]

    # Offsets come from what the files ACTUALLY contain, not from what they
    # were asked to contain. An xfade placed past the end of its accumulated
    # input does not fail - it waits for frames that will never arrive, and
    # hangs until something kills it. Predicting those lengths was tried twice
    # and was wrong twice, by fractions of a frame, so each offset is now
    # clamped against the measured length of everything joined so far and
    # cannot ask for material that is not there.
    durations = [_probe_duration(path) for path in segment_paths]
    # Every input is forced to identical frame rate, pixel format and pixel
    # aspect before it reaches a crossfade. xfade needs its two inputs to match
    # exactly, and these segments do not come from one place: some are rendered
    # from stills by zoompan, others re-encoded from stock clips whose source
    # framerate varies. A mismatch there makes the filter wait instead of fail,
    # which is indistinguishable from the hang chased above.
    # Order matters and got it wrong once: fps must come LAST. setpts rewrites
    # timestamps, which leaves ffmpeg unable to promise a constant rate, and it
    # then reports the link's frame rate as 1/0 - the exact thing xfade refuses
    # with "The inputs needs to be a constant frame rate". Normalising the
    # timebase and start time first and fixing the rate afterwards gives xfade
    # the constant rate it requires, which is most likely what was missing all
    # along: an input whose rate it cannot determine is what it was waiting on.
    # Timestamps are REBUILT from the frame index, not merely rebased. The
    # difference matters: setpts=PTS-STARTPTS fixes where a segment starts and
    # carries everything inside it through untouched, so one bad timestamp in
    # the middle of an input survives into the crossfade. Measured directly -
    # a segment given a PTS jump makes ffmpeg write without stopping, the file
    # growing past ten megabytes for ten seconds of video - and that is the
    # production symptom exactly: a join reporting 10,700 seconds encoded for
    # a group of 33, frozen, until the watchdog killed it.
    #
    # With fps forcing a constant rate first, a timebase of exactly one frame,
    # and setpts=N, every frame's time is its own index. Nothing an input says
    # about its timing can reach the crossfade, because none of it is read.
    # Every input is forced to the SAME SIZE, and this is the one that was
    # missing. xfade will not accept inputs of different dimensions - it fails
    # with "Error reinitializing filters" and an invalid-argument error, which
    # is exactly what five videos in a row produced. Reproduced deliberately:
    # two segments differing by two pixels of width give that message and no
    # other. Frame rate, timebase, pixel format and aspect were already being
    # normalised here; size never was, and size is the only one xfade refuses
    # to reconcile itself.
    #
    # The first segment sets the canvas rather than a number passed in, so the
    # join cannot disagree with what was actually rendered.
    lienzo = _dimensiones(segment_paths[0])
    escala = f"scale={lienzo[0]}:{lienzo[1]}," if lienzo else ""
    if lienzo:
        distintos = [
            (p.name, d) for p in segment_paths[1:]
            if (d := _dimensiones(p)) is not None and d != lienzo
        ]
        if distintos:
            logger.warning(
                "Segmentos con tamaño distinto de %sx%s, se reescalan: %s",
                lienzo[0], lienzo[1], distintos,
            )
    steps = [
        # fps AL FINAL, que es lo que dice el comentario de arriba y lo que el
        # codigo no hacia. Un setpts=N como ultimo filtro deja el enlace sin
        # tasa declarada, y xfade se planta con "the inputs needs to be a
        # constant frame rate; current rate of 1/0 is invalid" - que es
        # literalmente lo que fallo en el video 68. Poner fps detras del
        # ultimo setpts declara la tasa justo antes de entrar en xfade.
        f"[{i}:v]settb=1/{_ZOOM_FPS},setpts=N,"
        f"{escala}format=yuv420p,setsar=1,trim=duration={durations[i]:.3f},setpts=N,"
        f"fps={_ZOOM_FPS}[n{i}]"
        for i in range(len(segment_paths))
    ]
    current = "[n0]"
    accumulated = durations[0]
    offsets: list[float] = []
    for i in range(1, len(segment_paths)):
        boundary = frame_marks[i] / _ZOOM_FPS
        desired = boundary - _TRANSITION_SECONDS / 2
        offset = max(0.0, min(desired, accumulated - _TRANSITION_SECONDS))
        if offset < desired - 1 / _ZOOM_FPS:
            logger.warning(
                "Transicion %s adelantada %.3fs: hay %.2fs de video y la narracion la pedia en %.2fs.",
                i, desired - offset, accumulated, desired,
            )
        offsets.append(offset)
        label = f"[x{i}]"
        steps.append(
            f"{current}[n{i}]xfade=transition=fade:duration={_TRANSITION_SECONDS}:offset={offset:.3f}{label}"
        )
        current = label
        # xfade outputs from 0 to offset + the length of its second input.
        accumulated = offset + durations[i]

    filter_complex = ";".join(steps)
    esperado = frame_marks[-1] / _ZOOM_FPS
    # A join that comes out far short is the worst failure this file has: the
    # picture runs out, the last frame freezes for the rest of the narration,
    # and nothing about the video says why. It happened - six scenes totalling
    # 58 seconds joined into 11 - and could not be reproduced afterwards
    # because none of the numbers that produced it were written down. They are
    # now, before the call rather than after it.
    logger.info(
        "  union: %s segmentos, duraciones medidas %s, desfases %s, esperado %.2fs",
        len(segment_paths),
        [f"{d:.2f}" for d in durations],
        [f"{o:.2f}" for o in offsets],
        esperado,
    )
    # And a ceiling on the output, as the second half of the same defence. If
    # anything still makes the graph run away, ffmpeg stops at a length that
    # cannot be legitimate instead of encoding for ever: the join is asked for
    # `esperado` seconds and is given a couple of seconds of slack for
    # rounding, so a correct join never notices this and a runaway is bounded
    # into an ordinary short result, which the check below already handles.
    _run(
        [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", current,
            "-r", str(_ZOOM_FPS),
            "-t", f"{esperado + _MAX_JOIN_SHORTFALL_SECONDS:.3f}",
            str(out_path),
        ],
        f"transiciones x{len(segment_paths)}",
    )

    # And if it still comes out short, hard cuts beat a frozen frame. Butting
    # the segments together cannot lose time - it copies streams - so a plain
    # video is always available and is enormously better than 80% of a Short
    # being one still image.
    obtenido = _probe_duration(out_path)
    if obtenido > 0 and esperado - obtenido > _MAX_JOIN_SHORTFALL_SECONDS:
        logger.error(
            "La union con transiciones devolvio %.2fs cuando la narracion pide %.2fs "
            "(faltan %.2fs). Se rehace con cortes secos para no dejar el video congelado.",
            obtenido, esperado, esperado - obtenido,
        )
        _join_without_transitions(segment_paths, frame_marks, work_dir, out_path)
    return out_path


def _join_in_groups(segment_paths: list[Path], frame_marks: list[int], work_dir: Path, out_path: Path) -> Path:
    """Joins in two levels: each group of scenes is crossfaded on its own, then
    the group results are crossfaded together with the very same rule.

    Joining a group yields a clip half a transition shorter than the outer join
    needs from it, because its own last scene has nothing after it to overlap
    with. Rather than re-render that scene longer, the group's final frame is
    held for that half transition: those frames exist only to be consumed by
    the crossfade into the next group, so they are never seen as a freeze."""
    group_dir = work_dir / "join_groups"
    group_dir.mkdir(parents=True, exist_ok=True)

    bounds = list(range(0, len(segment_paths), _MAX_JOIN_INPUTS))
    group_paths: list[Path] = []
    group_marks: list[int] = []
    half = _TRANSITION_SECONDS / 2

    for g, start in enumerate(bounds):
        stop = min(start + _MAX_JOIN_INPUTS, len(segment_paths))
        is_last_group = stop == len(segment_paths)
        group_marks.append(frame_marks[start])

        # Frame marks restated relative to this group's own start, so the
        # inner join can use them exactly as it would for a whole video.
        local_marks = [frame_marks[i] - frame_marks[start] for i in range(start, stop + 1)]
        joined = group_dir / f"group_{g:02d}.mp4"
        logger.info("  grupo %s/%s: uniendo escenas %s-%s", g + 1, len(bounds), start + 1, stop)
        _join_segments(segment_paths[start:stop], local_marks, group_dir, joined)

        if is_last_group:
            group_paths.append(joined)
            continue
        padded = group_dir / f"group_{g:02d}_padded.mp4"
        _run(
            [
                "ffmpeg", "-y",
                "-i", str(joined),
                "-vf", f"tpad=stop_mode=clone:stop_duration={half}",
                "-r", str(_ZOOM_FPS),
                str(padded),
            ],
            f"margen grupo {g + 1}",
        )
        group_paths.append(padded)

    group_marks.append(frame_marks[-1])
    logger.info("  uniendo %s grupos", len(group_paths))
    _join_segments(group_paths, group_marks, work_dir, out_path)
    # The per-group files are only scaffolding for the join above, and at this
    # resolution they are hundreds of megabytes. The data volume is small and
    # shared with every video still waiting for approval, so they go as soon
    # as the join that needed them has finished.
    shutil.rmtree(group_dir, ignore_errors=True)
    return out_path


def _apply_source_caption(
    video_path: Path, source_name: str, intro_duration: float, width: int, height: int, work_dir: Path
) -> Path:
    """Overlays a small, constant "FUENTE: X" tag in a corner for the whole
    video (skipping the intro card) - crediting where the story comes from
    so the channel's facts read as sourced rather than just asserted. Placed
    top-right specifically because the bottom is where the per-scene name
    tag (a full-width bar) and, for stock-video scenes, the top-LEFT
    highlight box already live - a long name/role (e.g. "PARTIDO SOCIALISTA
    OBRERO ESPAÑOL") reaches far enough right to collide with anything
    placed in a bottom corner."""
    if not source_name:
        return video_path

    tag_png = work_dir / "source_tag.png"
    branding.render_source_caption(source_name, width, height).save(tag_png)
    margin = int(width * 0.02)
    out_path = work_dir / "with_source.mp4"
    _run(
        [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-loop", "1", "-i", str(tag_png),
            "-filter_complex",
            f"[1:v]format=rgba[fg];[0:v][fg]overlay=x=W-w-{margin}:y={margin}:"
            f"enable='gte(t,{intro_duration})':shortest=1",
            str(out_path),
        ]
    )
    return out_path



def _ensure_duration(path: Path, expected: float, tmp_dir: Path, index: int) -> None:
    """Pads a segment that came out shorter than asked for.

    The crossfades leave no slack: each transition is placed so that it starts
    at the last moment the running video can supply, so a segment even a frame
    short means xfade waits for frames that never arrive - and waits for ever,
    which is a hang rather than an error. Sources do come up short: a stock
    clip can decode to slightly less than its container claims, and a rounded
    duration can land just under a frame boundary.

    Holding the final frame for the missing fraction is invisible - those
    frames are inside the crossfade that follows."""
    actual = _probe_duration(path)
    if actual <= 0:
        logger.warning("No se pudo leer la duracion de %s, se sigue sin comprobarla", path.name)
        return
    shortfall = expected - actual
    # Under one frame is not worth a re-encode; xfade tolerates that much.
    if shortfall <= 1 / _ZOOM_FPS:
        return

    logger.warning(
        "Escena %s salio %.2fs corta (%.2fs de %.2fs); se alarga para que la transicion tenga material.",
        index + 1,
        shortfall,
        actual,
        expected,
    )
    padded = tmp_dir / f"seg_{index:02d}_padded.mp4"
    _run(
        [
            "ffmpeg", "-y",
            "-i", str(path),
            "-vf", f"tpad=stop_mode=clone:stop_duration={shortfall:.3f}",
            "-r", str(_ZOOM_FPS),
            str(padded),
        ],
        f"alargar escena {index + 1}",
    )
    padded.replace(path)



def _join_without_transitions(
    segment_paths: list[Path], frame_marks: list[int], work_dir: Path, out_path: Path
) -> Path:
    """Butts the segments together with hard cuts.

    The fallback for when crossfading fails. The concat demuxer reads one file
    after another rather than holding several open and aligning them, so there
    is no cross-stream synchronisation to stall on - which is what the
    crossfade does when it fails.

    It re-encodes rather than copying streams. Copying looked cheaper and was
    wrong: the demuxer needs every file to share the same codec parameters, and
    on segments whose frame rates differed it produced 17.26s of output from
    21.5s of input. Normalising through one filter chain costs a pass and
    cannot silently lose footage.

    Each segment is trimmed back to its scene's real length on the way in.
    Segments are rendered with a transition's worth of extra footage plus some
    slack, because a crossfade consumes it - with hard cuts nothing consumes
    it, so it plays. That is not merely 0.45s of surplus per scene: it
    accumulates, putting the picture a second behind the voice by the third
    scene and several seconds behind by the end. The first video built this way
    showed it, and it reads as the video being broken rather than plain."""
    concat_list = work_dir / "concat_plain.txt"
    lines = []
    for i, path in enumerate(segment_paths):
        lines.append(f"file '{path.resolve()}'")
        scene_seconds = (frame_marks[i + 1] - frame_marks[i]) / _ZOOM_FPS
        lines.append(f"outpoint {scene_seconds:.3f}")
    concat_list.write_text("\n".join(lines))
    _run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-vf", f"fps={_ZOOM_FPS},format=yuv420p,setsar=1",
            "-r", str(_ZOOM_FPS),
            str(out_path),
        ],
        "union sin transiciones",
    )
    return out_path



# Telegram bots cannot upload more than 50MB, and a five-minute 1080p video is
# several times that. The limit used to mean the approval message arrived as a
# thumbnail with a note saying the video was too big - so a long video could
# only be approved without being watched, which defeats the point of approving
# it at all.
_PREVIEW_MAX_BYTES = 45 * 1024 * 1024
# Small enough to reach a phone, large enough to judge framing, captions and
# whether the pictures match the words.
_PREVIEW_MAX_SIDE = 1280
_PREVIEW_AUDIO_BITRATE = 64_000


def make_preview(video_path: Path, out_path: Path, max_bytes: int = _PREVIEW_MAX_BYTES) -> Path | None:
    """A smaller copy of a video that fits inside Telegram's upload limit.

    Only for reviewing: the file uploaded to YouTube is always the original.
    Returns None if a preview cannot be made, leaving the caller to fall back
    to whatever it did before."""
    duration = _probe_duration(video_path)
    if duration <= 0:
        return None
    # Aim slightly under the limit: the muxer adds overhead and the encoder
    # only approximates the bitrate it is given.
    budget_bits = max_bytes * 8 * 0.92
    video_bitrate = int(budget_bits / duration) - _PREVIEW_AUDIO_BITRATE
    if video_bitrate < 150_000:
        logger.warning(
            "El video dura %.0fs: no cabe en %.0f MB ni con calidad minima.", duration, max_bytes / 1e6
        )
        return None
    try:
        _run(
            [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-vf",
                f"scale=w={_PREVIEW_MAX_SIDE}:h={_PREVIEW_MAX_SIDE}"
                ":force_original_aspect_ratio=decrease:force_divisible_by=2",
                "-b:v", str(video_bitrate),
                "-maxrate", str(int(video_bitrate * 1.3)),
                "-bufsize", str(video_bitrate * 2),
                "-preset", "veryfast",
                "-c:a", "aac", "-b:a", str(_PREVIEW_AUDIO_BITRATE),
                "-movflags", "+faststart",
                str(out_path),
            ],
            "vista previa",
        )
    except Exception:
        logger.warning("No se pudo crear la vista previa de %s", video_path.name, exc_info=True)
        return None
    size = out_path.stat().st_size
    logger.info("Vista previa: %.1f MB (original %.1f MB)", size / 1e6, video_path.stat().st_size / 1e6)
    return out_path if size <= max_bytes else None


def build_video(
    clip_entries: list[list[tuple[Path, dict | None]]],
    scene_durations: list[float],
    narration_path: Path,
    work_dir: Path,
    out_path: Path,
    width: int,
    height: int,
    source_name: str = "",
    intro_duration: float = 0.0,
) -> Path:
    """Renders each scene's clip(s) - a stock video, a single real photo/AI
    image, or (for scenes with more than one named entity) a short slideshow
    of several real photos - trimmed/looped to match the scene's narration
    length, concatenates them in order, overlays a source-attribution tag
    (if given), and muxes the narration audio on top."""
    normalized_dir = work_dir / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)

    # Each segment used to be rendered 0.3s longer than its scene as a safety
    # margin against concat coming up short. Because the segments are then
    # played back to back, that margin accumulated: every scene pushed the
    # picture another 0.3s behind the narration (measured: +0.30s after one
    # scene, +0.60s after two), so by the end of a long video the images
    # lagged several seconds behind the voice.
    # Deriving each segment's length from rounded CUMULATIVE frame positions
    # instead keeps every scene on its real timeline, and stops per-scene
    # rounding from accumulating either.
    frame_marks = [0]
    elapsed = 0.0
    for duration in scene_durations:
        elapsed += duration
        frame_marks.append(round(elapsed * _ZOOM_FPS))

    # Every segment except the last is rendered with an extra transition's
    # worth of footage, which the crossfade with the next scene then eats -
    # that is what keeps the total length (and so the narration sync) intact
    # despite each transition overlapping two scenes. The last one still gets
    # half a transition, because transitions are centred on the boundary and
    # the final one therefore starts half a transition early: without it the
    # video ends short and the audio mux clips the closing words.
    last_index = len(clip_entries) - 1
    segment_paths = []
    for i, entries in enumerate(clip_entries):
        seg_frames = max(1, frame_marks[i + 1] - frame_marks[i])
        extra = (
            _TRANSITION_SECONDS + _JOIN_MARGIN_SECONDS if i < last_index else _TRANSITION_SECONDS / 2
        )
        seg_seconds = seg_frames / _ZOOM_FPS + extra
        seg_path = normalized_dir / f"seg_{i:02d}.mp4"
        logger.info(
            "Renderizando escena %s/%s (%.1fs, %s clip(s))...", i + 1, len(clip_entries), seg_seconds, len(entries)
        )
        try:
            _build_scene_segment(entries, seg_seconds, width, height, seg_path, normalized_dir, i)
        except Exception:
            # Una escena que no se deja montar no puede costar el video entero.
            # El largo del caso Asunta murio aqui, en la 24 de 31, con la
            # narracion ya pagada: se perdieron las treinta que SI estaban
            # montadas por culpa de una. Ya existia esta idea unas lineas mas
            # abajo, para las transiciones, y es la misma: lo que se pueda
            # salvar se salva y el log dice cual es.
            logger.exception(
                "La escena %s no se ha podido montar; va con fondo liso para no "
                "perder el video entero.", i + 1,
            )
            _build_color_segment(seg_seconds, width, height, seg_path)
        _ensure_duration(seg_path, seg_seconds, normalized_dir, i)
        segment_paths.append(seg_path)

    silent_video_path = work_dir / "silent_video.mp4"
    logger.info("Uniendo %s escenas con transiciones...", len(segment_paths))
    try:
        _join_segments(segment_paths, frame_marks, work_dir, silent_video_path)
    except Exception:
        # Crossfading is the part of this that has repeatedly failed, and it is
        # also the part the video can do without. Butting the segments together
        # needs no filter graph at all - it copies streams and cannot stall -
        # so a video with hard cuts still gets made and sent for approval. A
        # plainer video beats no video, and the log says which one this is.
        logger.exception(
            "Fallaron las transiciones; se une sin ellas para no perder el video entero."
        )
        # Que propiedad no casaba. Esto ha fallado tres veces esta semana y las
        # tres se diagnostico por deduccion - primero el tamaño, luego el
        # formato de pixel - sin un solo dato delante. ffmpeg solo dice
        # "constant frame rate ... 1/0", que es el sintoma, no la causa. Con
        # esto la proxima vez se sabe: cada segmento con todo lo que xfade
        # mira, y el que se sale canta a la vista.
        for p_seg in segment_paths:
            try:
                datos = subprocess.run(
                    ["ffprobe", "-v", "error", "-select_streams", "v:0",
                     "-show_entries",
                     "stream=width,height,pix_fmt,r_frame_rate,avg_frame_rate,"
                     "time_base,sample_aspect_ratio,nb_frames,color_range",
                     "-of", "default=noprint_wrappers=1:nokey=0", str(p_seg)],
                    capture_output=True, text=True, timeout=30,
                ).stdout.strip().replace("\n", " · ")
            except Exception:
                datos = "(no se ha podido leer)"
            logger.error("  segmento %s: %s", Path(p_seg).name, datos)
        _join_without_transitions(segment_paths, frame_marks, work_dir, silent_video_path)

    # intro_duration comes from the caller because only it knows whether this
    # variant has an intro card at all - Shorts don't, and deriving it from
    # the first scene's length would hide the source tag over the opening
    # seconds of the story itself.
    silent_video_path = _apply_source_caption(
        silent_video_path, source_name, intro_duration, width, height, work_dir
    )

    silent_video_path = _cover_narration(silent_video_path, narration_path, work_dir)

    _run(
        [
            "ffmpeg", "-y",
            "-i", str(silent_video_path),
            "-i", str(narration_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            str(out_path),
        ]
    )
    return out_path


def _cover_narration(video_path: Path, narration_path: Path, work_dir: Path) -> Path:
    """Holds the last frame until the picture is at least as long as the voice.

    The mux below uses -shortest, so a picture that runs out early does not
    end the video early - it CUTS THE NARRATION. The Titanic short ended
    mid-sentence on "entonces, todo" because the joined picture came out 70.3s
    against 81.9s of narration, and nothing checked.

    Whatever loses that time in the join arithmetic is worth finding, and the
    warning below is how it gets found - but the story must not be truncated
    while we look. Holding the closing shot for the difference is the one
    outcome that is always acceptable; cutting the last sentence never is."""
    video_seconds = _probe_duration(video_path)
    narration_seconds = _probe_duration(narration_path)
    if video_seconds <= 0 or narration_seconds <= 0:
        logger.warning("No se pudo medir imagen o narracion; se mezcla sin comprobar la duracion.")
        return video_path

    shortfall = narration_seconds - video_seconds
    if shortfall <= 1 / _ZOOM_FPS:
        return video_path

    logger.warning(
        "La imagen (%.2fs) es mas corta que la narracion (%.2fs): faltan %.2fs y se cortaria el "
        "final. Se congela el ultimo plano para cubrirlos.",
        video_seconds,
        narration_seconds,
        shortfall,
    )
    covered = work_dir / "silent_video_cubierto.mp4"
    _run(
        [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", f"tpad=stop_mode=clone:stop_duration={shortfall:.3f}",
            "-r", str(_ZOOM_FPS),
            str(covered),
        ],
        "cubrir narracion",
    )
    return covered


def burn_subtitles(video_path: Path, ass_path: Path, out_path: Path) -> Path:
    """Burns the pre-styled ASS track (see subtitles.write_ass, which sets
    the styling in real pixels against the frame's own resolution) into the
    picture."""
    _run(
        [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", f"ass={ass_path}",
            "-c:a", "copy",
            str(out_path),
        ]
    )
    return out_path


def _probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        timeout=60,
    )
    try:
        return float(result.stdout.decode().strip())
    except ValueError:
        return 0.0


def mix_background_music(video_path: Path, music_path: Path, out_path: Path, volume: float) -> Path:
    """Mixes a music bed under the narration at low volume, looped to the
    video's length and faded in and out. Kept quiet by default: the music is
    there to stop the narration sounding bare, not to compete with it."""
    duration = _probe_duration(video_path)
    fade_out_start = max(0.0, duration - 2.5)
    music_chain = (
        f"[1:a]volume={volume},afade=t=in:st=0:d=1.5,"
        f"afade=t=out:st={fade_out_start:.2f}:d=2.5[music]"
    )
    _run(
        [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-stream_loop", "-1", "-i", str(music_path),
            # normalize=0 matters: amix otherwise divides every input by the
            # number of inputs, so simply adding music would quietly drop the
            # narration itself by 6 dB. The limiter then holds peaks about a
            # dB below full scale - the narration alone already peaks near
            # 0 dBFS, and adding music on top left no headroom at all, which
            # risks audible clipping once YouTube re-encodes the audio.
            "-filter_complex",
            f"{music_chain};[0:a][music]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
            "alimiter=limit=0.89:level=disabled[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac",
            "-t", str(duration),
            str(out_path),
        ]
    )
    return out_path
