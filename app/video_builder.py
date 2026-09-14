import subprocess
from pathlib import Path


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def _normalize_clip(clip_path: Path, duration: float, out_path: Path, width: int, height: int) -> None:
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


def burn_subtitles(video_path: Path, srt_path: Path, out_path: Path) -> Path:
    style = "FontSize=22,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=3"
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            f"subtitles={srt_path}:force_style='{style}'",
            "-c:a",
            "copy",
            str(out_path),
        ]
    )
    return out_path
