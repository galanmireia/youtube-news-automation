from pathlib import Path

from faster_whisper import WhisperModel

_model = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel("small", compute_type="int8")
    return _model


def _format_timestamp(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    hours, total_ms = divmod(total_ms, 3600000)
    minutes, total_ms = divmod(total_ms, 60000)
    secs, ms = divmod(total_ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def generate_srt(audio_path: Path, out_path: Path, language: str = "es") -> Path:
    model = _get_model()
    segments, _ = model.transcribe(str(audio_path), language=language)

    lines = []
    for i, segment in enumerate(segments, start=1):
        lines.append(str(i))
        lines.append(f"{_format_timestamp(segment.start)} --> {_format_timestamp(segment.end)}")
        lines.append(segment.text.strip())
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
