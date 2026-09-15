import difflib
import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

_model = None

# Below this much agreement between the transcription and the script, the two
# are not the same text and aligning them would do more harm than good.
_MIN_ALIGN_RATIO = 0.6


@dataclass
class _Word:
    """Same three fields the transcriber's words expose, so corrected words
    are interchangeable with the originals downstream."""

    start: float
    end: float
    word: str

# Shorts convention: a couple of words on screen at a time, swapping fast,
# rather than a full sentence sitting there for several seconds. Whichever
# limit is hit first closes the chunk.
_BURN_MAX_WORDS = 3
_BURN_MAX_SECONDS = 1.2
# Three words is a good rhythm but a bad width: "investigacion mexicana como"
# is three words and 27 characters, and at the burned font size that runs off
# both edges of a 1080-wide frame. Measured against the real style, a line of
# the subtitle font fits about 23 characters inside the side margins, so the
# chunk closes at 20 to leave headroom for wide glyphs.
_BURN_MAX_CHARS = 20


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


def _chunk_words(
    words: list, max_words: int, max_seconds: float, max_chars: int = _BURN_MAX_CHARS
) -> list[tuple[float, float, str]]:
    entries: list[tuple[float, float, str]] = []
    current: list = []

    def flush() -> None:
        nonlocal current
        if current:
            entries.append((current[0].start, current[-1].end, _join(current)))
            current = []

    for word in words:
        # Close the chunk BEFORE adding a word that would overflow the line,
        # unless it would leave the chunk empty: a single word longer than the
        # budget has nowhere else to go.
        if current and len(_join(current + [word])) > max_chars:
            flush()
        current.append(word)
        if len(current) >= max_words or (current[-1].end - current[0].start) >= max_seconds:
            flush()
    flush()
    return entries


def _join(chunk: list) -> str:
    return " ".join(w.word.strip() for w in chunk)


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
            # 2 means "never wrap", which silently lets a long line run off
            # both edges instead of breaking it. 0 wraps inside the margins,
            # so a chunk that still comes out too wide loses a line break
            # rather than its first and last words.
            "WrapStyle: 0",
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



def _norm(word: str) -> str:
    """Comparison form of a word: no case, no accents, no punctuation, so
    "Alozaina," and "alozaina" count as the same word."""
    folded = unicodedata.normalize("NFKD", word.lower())
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", folded)


def _align_to_script(words: list, script_text: str) -> list:
    """Replaces what the transcription heard with what the script actually
    says, keeping the transcription's timings.

    The narration is text-to-speech of a script we wrote, so the words are
    known exactly - only their timing is not. Transcribing it back can only
    lose information, and what it loses first is proper nouns: a village
    called Alozaina comes back as whatever it sounded like, and that guess is
    burned into the picture permanently. Aligning the two and preferring the
    script also restores accents and capitalisation the transcription drops.

    Returns the words unchanged if the two texts disagree too much to align
    safely, so a failed match can never scramble the subtitles."""
    script_words = script_text.split()
    if not words or not script_words:
        return words

    heard = [_norm(getattr(w, "word", "")) for w in words]
    written = [_norm(w) for w in script_words]
    matcher = difflib.SequenceMatcher(None, heard, written, autojunk=False)
    if matcher.ratio() < _MIN_ALIGN_RATIO:
        logger.info(
            "Subtitulos: transcripcion y guion solo coinciden al %.0f%%, se deja la transcripcion.",
            matcher.ratio() * 100,
        )
        return words

    aligned: list = []
    replaced = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            # Even here the script's spelling is preferable: the transcription
            # drops accents and capitals that the script has.
            for offset in range(i2 - i1):
                aligned.append(_Word(words[i1 + offset].start, words[i1 + offset].end, script_words[j1 + offset]))
            continue
        if tag == "delete" or j1 == j2:
            # Heard something the script does not have: drop it.
            continue
        span = words[i1:i2]
        # Spread the replacement words evenly across whatever time the heard
        # words occupied. For an insertion there is no time of its own, so
        # borrow the instant between the neighbours.
        if span:
            start, end = span[0].start, span[-1].end
        else:
            prev_end = words[i1 - 1].end if i1 > 0 else 0.0
            start = end = prev_end
        count = j2 - j1
        step = (end - start) / count if count else 0.0
        for k in range(count):
            aligned.append(_Word(start + k * step, start + (k + 1) * step, script_words[j1 + k]))
        replaced += count

    if replaced:
        logger.info("Subtitulos: %s palabras corregidas contra el guion.", replaced)
    return aligned

def generate_subtitles(
    audio_path: Path,
    srt_path: Path,
    burn_path: Path,
    width: int,
    height: int,
    language: str = "es",
    script_text: str = "",
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

    # What the script says beats what the transcription heard; only the
    # timings come from the transcription.
    if script_text and words:
        words = _align_to_script(words, script_text)

    _write_srt(sentence_entries, srt_path)
    # Falls back to the sentence timings if the model returned no per-word
    # timestamps, so the burned track is never empty.
    burn_entries = _chunk_words(words, _BURN_MAX_WORDS, _BURN_MAX_SECONDS) if words else sentence_entries
    write_ass(burn_entries, burn_path, width, height)
    return srt_path, burn_path
