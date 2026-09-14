"""Ejecuta esto UNA VEZ en tu ordenador (no en Railway) para autorizar la
subida a YouTube de forma interactiva y generar el token que luego se sube
al servidor.

Uso, desde la raiz del repo:
    python -m scripts.authorize_youtube
"""

from app.config import YOUTUBE_TOKEN_FILE
from app.youtube_uploader import get_credentials

if __name__ == "__main__":
    get_credentials()
    print(f"Autorizacion completada. Token guardado en: {YOUTUBE_TOKEN_FILE}")
    print("Sube ese archivo (o su contenido como variable de entorno) al servidor de Railway.")
