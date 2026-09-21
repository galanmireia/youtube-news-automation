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

# YuNet se vuelve poco fiable cuando la cara ocupa mucho en una imagen grande:
# esta entrenado con caras de un rango de tamaños, y un retrato de Commons a
# resolucion original se le sale por arriba. Medido con una foto de prueba
# real: a 256, 512, 1024 y 1536 px la encuentra siempre y en el mismo sitio; a
# 2400 no la encuentra en absoluto. Y el retrato de la duquesa venia a
# resolucion original justo desde que esta mañana cambie el buscador para
# preferir 'originalimage' sobre la miniatura, asi que ese arreglo rompio este.
#
# Se detecta sobre una copia reducida y se devuelve la caja escalada al
# tamaño de verdad. Bajar la confianza NO valia: a 0.5 encontraba algo, pero
# la caja salia descuadrada, y una miniatura encuadrada en una caja mala es
# peor que una sin encuadrar.
_LADO_PARA_DETECTAR = 1024
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
        escala = min(1.0, _LADO_PARA_DETECTAR / max(alto, ancho))
        if escala < 1.0:
            pequena = cv2.resize(imagen, (max(1, int(ancho * escala)),
                                          max(1, int(alto * escala))),
                                 interpolation=cv2.INTER_AREA)
        else:
            pequena = imagen
        alto_p, ancho_p = pequena.shape[:2]
        _, caras = _cargar(ancho_p, alto_p).detect(pequena)
        if caras is None or not len(caras):
            return None
        mejor = max(caras, key=lambda c: c[2] * c[3])
        x, y, w, h = (int(v / escala) for v in mejor[:4])
        logger.info("Cara encontrada en %s: %sx%s en (%s,%s).", ruta.name, w, h, x, y)
        return x, y, w, h
    except Exception:
        logger.warning("No se ha podido buscar la cara en %s.", ruta, exc_info=True)
        return None
