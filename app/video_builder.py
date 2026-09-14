import subprocess
from pathlib import Path

from . import branding

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


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        # subprocess.run(check=True) alone would only report the exit code -
        # ffmpeg's actual error (bad filter syntax, missing font, etc.) is on
        # stderr, and without it a failure here is undebuggable from logs.
        stderr_tail = result.stderr.decode(errors="replace")[-2000:]
        raise RuntimeError(f"ffmpeg fallo (codigo {result.returncode}): {stderr_tail}")


def _photo_background_filter(width: int, height: int) -> str:
    """Fits the whole photo inside the frame (never cropped) over a blurred,
    darkened copy of itself scaled to cover the rest, so a photo whose shape
    doesn't match the frame fills the screen instead of floating between
    black bars. The blur is done on a downscaled copy and then scaled back
    up - far cheaper than blurring at full resolution, and the upscale
    smooths it further."""
    small_w, small_h = max(2, width // _BLUR_DOWNSCALE), max(2, height // _BLUR_DOWNSCALE)
    return (
        "split=2[blurbase][fitbase];"
        f"[blurbase]scale={small_w}:{small_h}:force_original_aspect_ratio=increase,"
        f"crop={small_w}:{small_h},gblur=sigma={_BLUR_SIGMA},scale={width}:{height},"
        "eq=brightness=-0.12[blurred];"
        f"[fitbase]scale={width}:{height}:force_original_aspect_ratio=decrease[fitted];"
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
        _build_photo_segment(path, per, width, height, tag, sub_out, tmp_dir, f"{index}_{j}")
        sub_paths.append(sub_out)

    concat_list = tmp_dir / f"subconcat_{index:02d}.txt"
    concat_list.write_text("\n".join(f"file '{p.resolve()}'" for p in sub_paths))
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(out_path)])


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


def build_video(
    clip_entries: list[list[tuple[Path, dict | None]]],
    scene_durations: list[float],
    narration_path: Path,
    work_dir: Path,
    out_path: Path,
    width: int,
    height: int,
    source_name: str = "",
) -> Path:
    """Renders each scene's clip(s) - a stock video, a single real photo/AI
    image, or (for scenes with more than one named entity) a short slideshow
    of several real photos - trimmed/looped to match the scene's narration
    length, concatenates them in order, overlays a source-attribution tag
    (if given), and muxes the narration audio on top."""
    normalized_dir = work_dir / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)

    segment_paths = []
    for i, (entries, duration) in enumerate(zip(clip_entries, scene_durations)):
        seg_path = normalized_dir / f"seg_{i:02d}.mp4"
        _build_scene_segment(entries, duration + 0.3, width, height, seg_path, normalized_dir, i)
        segment_paths.append(seg_path)

    concat_list_path = work_dir / "concat_list.txt"
    concat_list_path.write_text("\n".join(f"file '{p.resolve()}'" for p in segment_paths))

    silent_video_path = work_dir / "silent_video.mp4"
    _run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_list_path),
            "-c", "copy",
            str(silent_video_path),
        ]
    )

    silent_video_path = _apply_source_caption(
        silent_video_path, source_name, scene_durations[0] if scene_durations else 0.0, width, height, work_dir
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
