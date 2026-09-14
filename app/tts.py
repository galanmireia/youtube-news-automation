from pathlib import Path

from google.cloud import texttospeech
from pydub import AudioSegment

from .config import TTS_LANGUAGE_CODE, TTS_VOICE_NAME

_client = None


def _get_client() -> texttospeech.TextToSpeechClient:
    global _client
    if _client is None:
        _client = texttospeech.TextToSpeechClient()
    return _client


def synthesize_scenes(scenes: list[dict], out_dir: Path) -> tuple[Path, list[float]]:
    """Synthesizes one audio clip per scene, concatenates them with a short
    pause in between, and returns the combined narration file plus the
    duration (in seconds) of each individual scene so the video can be
    timed to match."""
    out_dir.mkdir(parents=True, exist_ok=True)
    client = _get_client()
    voice = texttospeech.VoiceSelectionParams(language_code=TTS_LANGUAGE_CODE, name=TTS_VOICE_NAME)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.LINEAR16)

    scene_audio_paths = []
    for i, scene in enumerate(scenes):
        synthesis_input = texttospeech.SynthesisInput(text=scene["narration"])
        response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
        path = out_dir / f"scene_{i:02d}.wav"
        path.write_bytes(response.audio_content)
        scene_audio_paths.append(path)

    pause = AudioSegment.silent(duration=300)
    combined = AudioSegment.empty()
    scene_durations = []
    for path in scene_audio_paths:
        segment = AudioSegment.from_wav(path)
        scene_durations.append(len(segment) / 1000.0)
        combined += segment + pause

    final_audio_path = out_dir / "narration.wav"
    combined.export(final_audio_path, format="wav")
    return final_audio_path, scene_durations
