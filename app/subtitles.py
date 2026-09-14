from pathlib import Path

from faster_whisper import WhisperModel

_model = None

# Shorts convention: a couple of words on screen at a time, swapping fast,
# rather than a full sentence sitting there for several seconds. Whichever
# limit is hit first closes the chunk.
_BURN_MAX_WORDS = 3
_BURN_MAX_SECONDS = 1.2


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


def _write_srt(entries: list[tuple[float, float, str]], out_path: Path) -> Path:
    lines = []
    for i, (start, end, text) in enumerate(entries, start=1):
        lines.append(str(i))
        lines.append(f"{_format_timestamp(start)} --> {_format_timestamp(end)}")
        lines.append(text)
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def _chunk_words(words: list, max_words: int, max_seconds: float) -> list[tuple[float, float, str]]:
    entries: list[tuple[float, float, str]] = []
    current: list = []
    for word in words:
        current.append(word)
        if len(current) >= max_words or (current[-1].end - current[0].start) >= max_seconds:
            entries.append((current[0].start, current[-1].end, " ".join(w.word.strip() for w in current)))
            current = []
    if current:
        entries.append((current[0].start, current[-1].end, " ".join(w.word.strip() for w in current)))
    return entries


def _format_ass_timestamp(seconds: float) -> str:
    total_cs = int(round(seconds * 100))
    hours, total_cs = divmod(total_cs, 360000)
    minutes, total_cs = divmod(total_cs, 6000)
    secs, cs = divmod(total_cs, 100)
    return f"{hours:d}:{minutes:02d}:{secs:02d}.{cs:02d}"


def write_ass(entries: list[tuple[float, float, str]], out_path: Path, width: int, height: int) -> Path:
    """Writes the burned-in track as ASS rather than SRT. ffmpeg converts an
    SRT to ASS using a fixed 384x288 reference resolution, so font sizes and
    margins given in force_style are in THAT space, not video pixels - a
    margin meant to clear the lower third silently pushed the text off
    screen entirely. Declaring PlayResX/Y as the real frame size makes every
    value below plain pixels."""
    font_size = max(24, height // 24)
    margin_v = height // 5
    margin_h = width // 12
    header = "\n".join(
        [
            "[Script Info]",
            "ScriptType: v4.00+",
            f"PlayResX: {width}",
            f"PlayResY: {height}",
            "WrapStyle: 2",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour,"
            " Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline,"
            " Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            f"Style: Main,DejaVu Sans,{font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,"
            f"-1,0,0,0,100,100,0,0,1,{max(3, font_size // 14)},2,2,{margin_h},{margin_h},{margin_v},1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]
    )
    events = [
        f"Dialogue: 0,{_format_ass_timestamp(start)},{_format_ass_timestamp(end)},Main,,0,0,0,,"
        + text.replace("\n", " ").strip()
        for start, end, text in entries
    ]
    out_path.write_text(header + "\n" + "\n".join(events) + "\n", encoding="utf-8")
    return out_path


def generate_subtitles(
    audio_path: Path, srt_path: Path, burn_path: Path, width: int, height: int, language: str = "es"
) -> tuple[Path, Path]:
    """Transcribes the narration once and writes two subtitle files from it:
    the full-sentence SRT uploaded to YouTube as a caption track (better for
    accessibility and for viewers reading along), and an ASS chunked into a
    few words at a time, which is what gets burned into the video - a whole
    sentence burned in at once is unreadable at Shorts pace."""
    model = _get_model()
    segments, _ = model.transcribe(str(audio_path), language=language, word_timestamps=True)

    sentence_entries: list[tuple[float, float, str]] = []
    words: list = []
    for segment in segments:
        sentence_entries.append((segment.start, segment.end, segment.text.strip()))
        words.extend(segment.words or [])

    _write_srt(sentence_entries, srt_path)
    # Falls back to the sentence timings if the model returned no per-word
    # timestamps, so the burned track is never empty.
    burn_entries = _chunk_words(words, _BURN_MAX_WORDS, _BURN_MAX_SECONDS) if words else sentence_entries
    write_ass(burn_entries, burn_path, width, height)
    return srt_path, burn_path
