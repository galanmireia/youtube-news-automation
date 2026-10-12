"""Voz gratis para Why Though: Piper, una voz neuronal abierta que corre en
el propio servidor (sin pagar a Google por caracter).

El modelo (unos 120 MB) no va en el repo: se baja una vez de la release de
GitHub de rhasspy/piper y se queda en DATA_DIR. Si DATA_DIR no sobrevive a
un redeploy, se vuelve a bajar en unos segundos.
"""
from __future__ import annotations

import logging
import tarfile
import threading
import wave
from pathlib import Path

from .config import DATA_DIR

logger = logging.getLogger(__name__)

NOMBRE = "en-us-ryan-high"
_URL = "https://github.com/rhasspy/piper/releases/download/v0.0.2/voice-en-us-ryan-high.tar.gz"
_CARPETA = Path(DATA_DIR) / "piper"
# Piper habla mas deprisa que Google (con 1.15 iba a unas 185 palabras por
# minuto y el guion de 7 dias se quedaba en 9 minutos); 1.3 la deja en unas
# 165, cerca del ritmo de Google con el que se calculan los 10 minutos.
RITMO = 1.3

_AJUSTE = Path(DATA_DIR) / "voz_why.txt"
_voz = None
_cerrojo = threading.Lock()


def activa() -> bool:
    """¿Usa Why Though la voz gratis? Por defecto si; /vozgratis no la quita."""
    try:
        return _AJUSTE.read_text().strip() != "google"
    except OSError:
        return True


def elige(gratis: bool) -> None:
    _AJUSTE.write_text("piper" if gratis else "google")


def _modelo() -> Path:
    onnx = _CARPETA / f"{NOMBRE}.onnx"
    if onnx.exists() and (_CARPETA / f"{NOMBRE}.onnx.json").exists():
        return onnx
    import requests
    _CARPETA.mkdir(parents=True, exist_ok=True)
    tar = _CARPETA / "voz.tar.gz"
    logger.info("piper: bajando la voz %s...", NOMBRE)
    with requests.get(_URL, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(tar, "wb") as f:
            for trozo in r.iter_content(1 << 20):
                f.write(trozo)
    with tarfile.open(tar) as t:
        for miembro in t.getmembers():
            nombre = Path(miembro.name).name
            if miembro.isfile() and nombre in (f"{NOMBRE}.onnx", f"{NOMBRE}.onnx.json"):
                miembro.name = nombre
                t.extract(miembro, _CARPETA)
    tar.unlink(missing_ok=True)
    if not onnx.exists():
        raise RuntimeError("piper: el paquete de la voz no traia el modelo")
    return onnx


def _carga():
    global _voz
    with _cerrojo:
        if _voz is None:
            from piper import PiperVoice
            onnx = _modelo()
            _voz = PiperVoice.load(onnx, config_path=onnx.with_suffix(".onnx.json"))
        return _voz


def sintetiza(texto: str, destino: Path):
    """Una frase con Piper; devuelve un AudioSegment como _voz_google."""
    from piper import SynthesisConfig
    from pydub import AudioSegment
    voz = _carga()
    wav = Path(destino).with_suffix(".piper.wav")
    with wave.open(str(wav), "wb") as w:
        voz.synthesize_wav(texto, w, syn_config=SynthesisConfig(length_scale=RITMO))
    return AudioSegment.from_wav(wav)
