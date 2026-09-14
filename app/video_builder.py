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
# "frozen" - a slow, subtle zoom-in (the classic "Ken Burns" documentary
# technique) gives every static shot its own life instead of only the stock
# video clips ever having any movement. Kept small (12% max) so it never
# creeps in far enough to crop a face/logo near the edge of the frame.
_ZOOM_MAX = 1.12
_ZOOM_FPS = 30


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        # subprocess.run(check=True) alone would only report the exit code -
        # ffmpeg's actual error (bad filter syntax, missing font, etc.) is on
        # stderr, and without it a failure here is undebuggable from logs.
        stderr_tail = result.stderr.decode(errors="replace")[-2000:]
        raise RuntimeError(f"ffmpeg fallo (codigo {result.returncode}): {stderr_tail}")


def _photo_scale_pad_filter(width: int, height: int) -> str:
    # Fit the whole image (no crop, so faces/logos never get cut off) and pad
    # with black bars instead of stretching/cropping.
    return f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black"


def _ken_burns_filter(width: int, height: int, duration: float) -> str:
    frames = max(1, round(duration * _ZOOM_FPS))
    increment = (_ZOOM_MAX - 1) / frames
    return f"zoompan=z='min(zoom+{increment:.6f},{_ZOOM_MAX})':d={frames}:s={width}x{height}:fps={_ZOOM_FPS}"


def _build_photo_segment(
    image_path: Path, duration: float, width: int, height: int, tag: dict | None, out_path: Path, tmp_dir: Path, key: str
) -> None:
    vf_bg = f"{_photo_scale_pad_filter(width, height)},{_ken_burns_filter(width, height, duration)}"

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


def _build_video_clip_segment(clip_path: Path, duration: float, width: int, height: int, out_path: Path) -> None:
    vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
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


def _build_scene_segment(
    entries: list[tuple[Path, dict | None]], duration: float, width: int, height: int, out_path: Path, tmp_dir: Path, index: int
) -> None:
    if len(entries) == 1:
        path, tag = entries[0]
        if path.suffix.lower() in IMAGE_SUFFIXES:
            _build_photo_segment(path, duration, width, height, tag, out_path, tmp_dir, str(index))
        else:
            _build_video_clip_segment(path, duration, width, height, out_path)
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


def build_video(
    clip_entries: list[list[tuple[Path, dict | None]]],
    scene_durations: list[float],
    narration_path: Path,
    work_dir: Path,
    out_path: Path,
    width: int,
    height: int,
) -> Path:
    """Renders each scene's clip(s) - a stock video, a single real photo/AI
    image, or (for scenes with more than one named entity) a short slideshow
    of several real photos - trimmed/looped to match the scene's narration
    length, concatenates them in order, and muxes the narration audio on
    top."""
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


def burn_subtitles(video_path: Path, srt_path: Path, out_path: Path, width: int, height: int) -> Path:
    # Without original_size, libass assumes a small default reference resolution
    # and scales the text up to the real frame size, making it huge. BorderStyle=1
    # draws an outline/shadow instead of a solid box, so the video stays visible.
    font_size = max(20, height // 32)
    margin_v = height // 12
    style = (
        f"FontSize={font_size},PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,"
        f"BorderStyle=1,Outline=2,Shadow=1,MarginV={margin_v}"
    )
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            f"subtitles={srt_path}:original_size={width}x{height}:force_style='{style}'",
            "-c:a",
            "copy",
            str(out_path),
        ]
    )
    return out_path
