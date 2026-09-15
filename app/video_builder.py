import logging
import shutil
import subprocess
import threading
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
_ZOOM_MAX = 1.12
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

# Crossfading gets far less rope than anything else here. A join that is going
# to work takes well under a minute - the slowest measured was 52s for seven
# 1080x1920 segments - and one that is going to stall never finishes at all.
# Waiting the full eight minutes to learn which it was is pure loss, and a long
# video makes five of these calls. Cut it short and take the hard-cut fallback.
_JOIN_TIMEOUT_SECONDS = 2 * 60


# How often a still-running ffmpeg call reports that it is alive. Borrowed from
# MoneyPrinterTurbo (MIT), which logs the same thing for the same reason: ffmpeg
# buffers its output until it exits, so a long call looks identical to a hung
# one in the logs. Reporting the output file's size alongside the elapsed time
# is what separates the two - a growing file is work, a static one is a stall.
# Yesterday that distinction had to be guessed at from CPU metrics.
_FFMPEG_HEARTBEAT_SECONDS = 30


def _heartbeat(step: str, out_path: Path, started: float, stop: threading.Event) -> None:
    while not stop.wait(_FFMPEG_HEARTBEAT_SECONDS):
        size = out_path.stat().st_size / 1e6 if out_path.exists() else 0.0
        logger.info("  ffmpeg %s sigue: %.0fs, salida %.1f MB", step, time.monotonic() - started, size)


def _run(cmd: list[str], step: str = "ffmpeg", timeout: float = _FFMPEG_TIMEOUT_SECONDS) -> None:
    started = time.monotonic()
    # The output file is always the last argument of every command built here.
    stop = threading.Event()
    reporter = threading.Thread(target=_heartbeat, args=(step, Path(cmd[-1]), started, stop), daemon=True)
    reporter.start()
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        # subprocess.run kills the child before raising.
        raise RuntimeError(f"ffmpeg bloqueado en '{step}' mas de {timeout:.0f}s, proceso matado") from exc
    finally:
        stop.set()
    logger.info("  ffmpeg %s: %.1fs", step, time.monotonic() - started)
    if result.returncode != 0:
        # subprocess.run(check=True) alone would only report the exit code -
        # ffmpeg's actual error (bad filter syntax, missing font, etc.) is on
        # stderr, and without it a failure here is undebuggable from logs.
        stderr_tail = result.stderr.decode(errors="replace")[-2000:]
        raise RuntimeError(f"ffmpeg fallo en '{step}' (codigo {result.returncode}): {stderr_tail}")


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
    increment = (_ZOOM_MAX - 1) / frames
    # Alternating zoom-in and zoom-out between shots (instead of every single
    # shot doing the exact same push-in) reads as more deliberately dynamic
    # rather than one repeated motion.
    if zoom_out:
        z_expr = f"if(eq(on,0),{_ZOOM_MAX},max(zoom-{increment:.6f},1))"
    else:
        z_expr = f"min(zoom+{increment:.6f},{_ZOOM_MAX})"
    return f"zoompan=z='{z_expr}':d={frames}:s={width}x{height}:fps={_ZOOM_FPS}"


def _build_photo_segment(
    image_path: Path, duration: float, width: int, height: int, tag: dict | None, out_path: Path, tmp_dir: Path, key: str
) -> None:
    zoom_out = int(key.split("_")[0]) % 2 == 1
    vf_bg = f"{_photo_background_filter(width, height)},{_ken_burns_filter(width, height, duration, zoom_out)}"

    if not tag or duration < 1.5:
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


def _build_video_clip_segment(
    clip_path: Path, duration: float, width: int, height: int, tag: dict | None, out_path: Path, tmp_dir: Path, key: str
) -> None:
    vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
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
_MAX_JOIN_INPUTS = 6

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
    steps = [
        f"[{i}:v]settb=AVTB,setpts=PTS-STARTPTS,fps={_ZOOM_FPS},format=yuv420p,setsar=1[n{i}]"
        for i in range(len(segment_paths))
    ]
    current = "[n0]"
    accumulated = durations[0]
    for i in range(1, len(segment_paths)):
        boundary = frame_marks[i] / _ZOOM_FPS
        desired = boundary - _TRANSITION_SECONDS / 2
        offset = max(0.0, min(desired, accumulated - _TRANSITION_SECONDS))
        if offset < desired - 1 / _ZOOM_FPS:
            logger.warning(
                "Transicion %s adelantada %.3fs: hay %.2fs de video y la narracion la pedia en %.2fs.",
                i, desired - offset, accumulated, desired,
            )
        label = f"[x{i}]"
        steps.append(
            f"{current}[n{i}]xfade=transition=fade:duration={_TRANSITION_SECONDS}:offset={offset:.3f}{label}"
        )
        current = label
        # xfade outputs from 0 to offset + the length of its second input.
        accumulated = offset + durations[i]

    filter_complex = ";".join(steps)
    _run(
        [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", current,
            "-r", str(_ZOOM_FPS),
            str(out_path),
        ],
        f"transiciones x{len(segment_paths)}",
        timeout=_JOIN_TIMEOUT_SECONDS,
    )
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
        _build_scene_segment(entries, seg_seconds, width, height, seg_path, normalized_dir, i)
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
        _join_without_transitions(segment_paths, frame_marks, work_dir, silent_video_path)

    # intro_duration comes from the caller because only it knows whether this
    # variant has an intro card at all - Shorts don't, and deriving it from
    # the first scene's length would hide the source tag over the opening
    # seconds of the story itself.
    silent_video_path = _apply_source_caption(
        silent_video_path, source_name, intro_duration, width, height, work_dir
    )

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
