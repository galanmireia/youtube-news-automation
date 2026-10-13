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


# ---------------------------------------------------------------------------
# LAS VOCES GRATIS EN ESPAÑOL, para elegir de oido ("vamos a intentar otra
# gratuita... mandame las pruebas al Telegram y te digo cual"). La de la
# release vieja de GitHub suena fatal; las buenas estan en el repositorio de
# voces de Piper en Hugging Face. Se bajan solo cuando se piden las muestras.
# ---------------------------------------------------------------------------
_HF = "https://huggingface.co/rhasspy/piper-voices/resolve/main/es"
VOCES_ES = [
    ("davefx", "España, hombre", f"{_HF}/es_ES/davefx/medium/es_ES-davefx-medium.onnx"),
    ("sharvard", "España", f"{_HF}/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx"),
    ("carlfm", "España, hombre (ligera)", f"{_HF}/es_ES/carlfm/x_low/es_ES-carlfm-x_low.onnx"),
    ("claude", "México, hombre", f"{_HF}/es_MX/claude/high/es_MX-claude-high.onnx"),
    ("ald", "México, hombre", f"{_HF}/es_MX/ald/medium/es_MX-ald-medium.onnx"),
    ("daniela", "Argentina, mujer", f"{_HF}/es_AR/daniela/high/es_AR-daniela-high.onnx"),
]
_CARPETA_ES = Path(DATA_DIR) / "piper_es"


def _baja(url: str, destino: Path) -> None:
    import requests
    if destino.exists() and destino.stat().st_size > 1000:
        return
    tmp = destino.with_suffix(destino.suffix + ".part")
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for trozo in r.iter_content(1 << 20):
                f.write(trozo)
    tmp.rename(destino)


def muestras_es(texto: str, carpeta: Path) -> list[tuple[str, Path | None, str]]:
    """Una muestra en mp3 de cada voz gratis en español (y de cada hablante
    si el modelo tiene varios). Devuelve (nombre, mp3 o None, error)."""
    import json
    from piper import PiperVoice, SynthesisConfig
    from pydub import AudioSegment
    _CARPETA_ES.mkdir(parents=True, exist_ok=True)
    carpeta.mkdir(parents=True, exist_ok=True)
    salida = []
    for nombre, desc, url in VOCES_ES:
        onnx = _CARPETA_ES / url.rsplit("/", 1)[1]
        try:
            _baja(url, onnx)
            _baja(url + ".json", onnx.with_suffix(".onnx.json"))
            conf = json.loads(onnx.with_suffix(".onnx.json").read_text())
            hablantes = conf.get("speaker_id_map") or {"": None}
            voz = PiperVoice.load(onnx, config_path=onnx.with_suffix(".onnx.json"))
            for etiqueta, sid in hablantes.items():
                wav = carpeta / f"{nombre}{etiqueta}.wav"
                with wave.open(str(wav), "wb") as w:
                    voz.synthesize_wav(texto, w, syn_config=SynthesisConfig(speaker_id=sid, length_scale=1.0))
                mp3 = wav.with_suffix(".mp3")
                AudioSegment.from_wav(wav).export(mp3, format="mp3", bitrate="128k")
                titulo = f"{nombre}{' ' + etiqueta if etiqueta else ''} · {desc}"
                salida.append((titulo, mp3, ""))
        except Exception as exc:
            logger.warning("piper: no sale la voz %s", nombre, exc_info=True)
            salida.append((f"{nombre} · {desc}", None, str(exc)[:200]))
    return salida
