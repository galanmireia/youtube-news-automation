import io
import logging
from pathlib import Path

from google.cloud import texttospeech
from pydub import AudioSegment

from .config import TTS_LANGUAGE_CODE, TTS_VOICE_NAME

logger = logging.getLogger(__name__)

_client = None

# Chirp3-HD (generative) voices have a much lower per-request text limit than
# Standard/Neural2 voices. Scenes are batched into chunks under this size so
# each chunk still gets one natural, continuous take instead of gluing
# together tiny single-sentence clips (which is what sounded choppy/robotic).
MAX_CHUNK_CHARS = 600


def _get_client() -> texttospeech.TextToSpeechClient:
    global _client
    if _client is None:
        _client = texttospeech.TextToSpeechClient()
    return _client


# What a sample says. Long enough to judge rhythm and intonation rather than
# just timbre, and written in the channel's own register so the voice is heard
# doing the job it will actually do.
SAMPLE_TEXT = (
    "El trece de noviembre de dos mil dos, el casco del Prestige se abrio a "
    "treinta millas de la Costa da Morte. Lo que vino despues fue el mayor "
    "desastre medioambiental de la historia de España."
)


def list_spanish_voices() -> list[tuple[str, str]]:
    """Asks Google which Spanish voices this project can actually use, as
    (name, gender) pairs sorted by name.

    Asking beats remembering: Google adds and retires voice families every few
    months, and a guessed name comes back as an error that reads like a
    configuration problem. This is the same lesson the image models taught -
    the live catalogue is the only reliable list."""
    client = _get_client()
    response = client.list_voices(language_code=TTS_LANGUAGE_CODE)
    voces = []
    for voice in response.voices:
        genero = texttospeech.SsmlVoiceGender(voice.ssml_gender).name.lower()
        voces.append((voice.name, genero))
    return sorted(voces)


def synthesize_sample(voice_name: str, out_path: Path, text: str = SAMPLE_TEXT) -> Path:
    """One spoken sample in a named voice, so a voice can be HEARD before the
    channel commits to it. Judging a voice by its name is guesswork; judging it
    by a paragraph of the channel's own narration is not."""
    client = _get_client()
    voice = texttospeech.VoiceSelectionParams(language_code=TTS_LANGUAGE_CODE, name=voice_name)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text), voice=voice, audio_config=audio_config
    )
    out_path.write_bytes(response.audio_content)
    return out_path


def _synthesize(client, voice, audio_config, text: str) -> AudioSegment:
    response = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text), voice=voice, audio_config=audio_config
    )
    return AudioSegment.from_wav(io.BytesIO(response.audio_content))


def _group_scenes(scenes: list[dict]) -> list[list[dict]]:
    groups: list[list[dict]] = []
    current: list[dict] = []
    current_len = 0
    for scene in scenes:
        text_len = len(scene["narration"])
        if current and current_len + text_len > MAX_CHUNK_CHARS:
            groups.append(current)
            current, current_len = [], 0
        current.append(scene)
        current_len += text_len
    if current:
        groups.append(current)
    return groups


def synthesize_scenes(scenes: list[dict], out_dir: Path) -> tuple[Path, list[float]]:
    """Synthesizes each group of consecutive scenes in a single TTS call (for
    natural, continuous prosody instead of choppy sentence-by-sentence audio),
    and returns per-scene durations - measured independently and rescaled to
    match each group's real duration - so the video can be timed to match."""
    out_dir.mkdir(parents=True, exist_ok=True)
    client = _get_client()
    voice = texttospeech.VoiceSelectionParams(language_code=TTS_LANGUAGE_CODE, name=TTS_VOICE_NAME)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.LINEAR16)

    pause = AudioSegment.silent(duration=250)
    combined = AudioSegment.empty()
    scene_durations: list[float] = []

    for group in _group_scenes(scenes):
        individual_durations = [
            len(_synthesize(client, voice, audio_config, scene["narration"])) / 1000.0 for scene in group
        ]
        group_audio = _synthesize(client, voice, audio_config, " ".join(s["narration"] for s in group))

        total_individual = sum(individual_durations) or 1.0
        scale = (len(group_audio) / 1000.0) / total_individual
        scene_durations.extend(d * scale for d in individual_durations)

        combined += group_audio + pause

    final_audio_path = out_dir / "narration.wav"
    combined.export(final_audio_path, format="wav")
    return final_audio_path, scene_durations
