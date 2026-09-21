"""Donde esta la cara en una foto.

Esto existe por una bronca justa: le di una miniatura que era su foto con un
rotulo encima, y eso no es una miniatura, es una plantilla. Una de verdad
lleva la cara grande, recortada del fondo y con el texto donde no la tapa - y
nada de eso se puede hacer sin saber DONDE esta la cara.

Se usa YuNet, el detector que trae OpenCV. Pesa 227 KB y corre en el
procesador en unas centesimas, o sea que cabe de sobra en la maquina de
Railway, que no tiene tarjeta grafica. No reconoce a nadie: solo dice "aqui
hay una cara", que es todo lo que hace falta para encuadrar.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_MODELO = Path(__file__).resolve().parent.parent / "assets" / "modelos" / "deteccion_caras_yunet.onnx"
_CONFIANZA = 0.7
_detector = None


def disponible() -> bool:
    return _MODELO.exists()


def _cargar(ancho: int, alto: int):
    global _detector
    import cv2
    if _detector is None:
        _detector = cv2.FaceDetectorYN.create(str(_MODELO), "", (ancho, alto), _CONFIANZA)
    _detector.setInputSize((ancho, alto))
    return _detector


def la_cara(ruta: Path) -> tuple[int, int, int, int] | None:
    """(x, y, ancho, alto) de la cara mas grande, o None.

    La MAS GRANDE y no la primera: en una foto de juicio hay publico al fondo,
    y la que importa es la que esta en primer plano.
    """
    if not disponible():
        return None
    try:
        import cv2
        imagen = cv2.imread(str(ruta))
        if imagen is None:
            return None
        alto, ancho = imagen.shape[:2]
        _, caras = _cargar(ancho, alto).detect(imagen)
        if caras is None or not len(caras):
            return None
        mejor = max(caras, key=lambda c: c[2] * c[3])
        x, y, w, h = (int(v) for v in mejor[:4])
        logger.info("Cara encontrada en %s: %sx%s en (%s,%s).", ruta.name, w, h, x, y)
        return x, y, w, h
    except Exception:
        logger.warning("No se ha podido buscar la cara en %s.", ruta, exc_info=True)
        return None
