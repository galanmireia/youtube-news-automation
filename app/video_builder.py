import subprocess
from pathlib import Path

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def _normalize_clip(clip_path: Path, duration: float, out_path: Path, width: int, height: int) -> None:
    if clip_path.suffix.lower() in IMAGE_SUFFIXES:
        # A real person's photo: fit the whole image (no crop, so faces never
        # get cut off) and pad with black bars instead of stretching/cropping.
        vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black"
        _run(
            [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                str(clip_path),
                "-t",
                str(duration),
                "-vf",
                vf,
                "-r",
                "30",
                str(out_path),
            ]
        )
        return

    vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
    _run(
        [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(clip_path),
            "-t",
            str(duration),
            "-vf",
            vf,
            "-an",
            "-r",
            "30",
            str(out_path),
        ]
    )


def build_video(
    clip_paths: list[Path],
    scene_durations: list[float],
    narration_path: Path,
    work_dir: Path,
    out_path: Path,
    width: int,
    height: int,
) -> Path:
    """Trims/loops each stock clip to match its scene's narration length,
    concatenates them in order, and muxes the narration audio on top."""
    normalized_dir = work_dir / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)

    segment_paths = []
    for i, (clip_path, duration) in enumerate(zip(clip_paths, scene_durations)):
        seg_path = normalized_dir / f"seg_{i:02d}.mp4"
        _normalize_clip(clip_path, duration + 0.3, seg_path, width, height)
        segment_paths.append(seg_path)

    concat_list_path = work_dir / "concat_list.txt"
    concat_list_path.write_text("\n".join(f"file '{p.resolve()}'" for p in segment_paths))

    silent_video_path = work_dir / "silent_video.mp4"
    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list_path),
            "-c",
            "copy",
            str(silent_video_path),
        ]
    )

    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(silent_video_path),
            "-i",
            str(narration_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
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
