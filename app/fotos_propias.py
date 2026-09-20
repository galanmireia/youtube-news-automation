"""Las fotos que pone ella, que van por delante de todo lo demas.

El sistema busca imagenes en Wikipedia, Commons, Pexels y Pixabay porque son
las que se pueden usar sin pensarlo. Pero hay casos - los de sucesos
españoles, sobre todo - donde de las personas no existe ninguna imagen libre:
las que todo el mundo ha visto son de agencia. El caso Asunta se monto entero
para descubrir eso al final.

Esto es la salida: ella manda la foto al bot, dice de quien es, y se usa. El
sistema no opina sobre de donde sale ni la compara con nada. Es su canal, y
una redaccion decide esto foto a foto; aqui pasa igual, salvo que la decision
la toma antes y una sola vez por imagen.

Lo que si hace, porque es utilidad y no juicio: recordar el nombre con el que
la guardo, para que la misma foto valga en todos los videos donde aparezca esa
persona sin tener que volver a mandarla.
"""
import json
import logging
import re
import unicodedata
from pathlib import Path

from .config import DATA_DIR

logger = logging.getLogger(__name__)

CARPETA = Path(DATA_DIR) / "fotos_propias"
_INDICE = CARPETA / "indice.json"


def _fold(texto: str) -> str:
    plano = unicodedata.normalize("NFKD", texto.lower().strip())
    return "".join(c for c in plano if not unicodedata.combining(c))


def _cargar() -> dict:
    try:
        return json.loads(_INDICE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _guardar(indice: dict) -> None:
    CARPETA.mkdir(parents=True, exist_ok=True)
    _INDICE.write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8")


def guardar(nombre: str, datos: bytes, extension: str = ".jpg") -> Path:
    """Guarda una foto bajo un nombre. Si ya habia una con ese nombre, se
    añade: una persona puede tener varias y asi no sale siempre la misma."""
    CARPETA.mkdir(parents=True, exist_ok=True)
    clave = _fold(nombre)
    indice = _cargar()
    existentes = indice.get(clave, {}).get("ficheros", [])
    seguro = re.sub(r"[^a-z0-9]+", "_", clave).strip("_") or "foto"
    destino = CARPETA / f"{seguro}_{len(existentes)}{extension}"
    destino.write_bytes(datos)
    indice[clave] = {"nombre": nombre.strip(), "ficheros": existentes + [destino.name]}
    _guardar(indice)
    logger.info("Foto propia guardada para %r: %s", nombre, destino.name)
    return destino


def de(nombre: str, excluir: set[str] | None = None) -> Path | None:
    """La foto que ella puso para este nombre, si la hay.

    El emparejado es generoso a proposito: ella escribe "Rosario Porto" y el
    guion puede pedir "Rosario Porto Ortega". Si uno contiene al otro, es la
    misma persona - lo ha dicho ella al guardarla, y su palabra vale mas que
    cualquier comprobacion que yo pueda hacer sobre su propia foto.
    """
    excluir = excluir or set()
    pedido = _fold(nombre)
    if not pedido:
        return None
    indice = _cargar()
    for clave, datos in indice.items():
        if clave not in pedido and pedido not in clave:
            continue
        for fichero in datos.get("ficheros", []):
            ruta = CARPETA / fichero
            if ruta.exists() and str(ruta) not in excluir:
                logger.info("«%s»: usando la foto que pusiste tu (%s).", nombre, fichero)
                return ruta
    return None


def listar() -> list[tuple[str, int]]:
    return [(d.get("nombre", c), len(d.get("ficheros", [])))
            for c, d in sorted(_cargar().items())]


def borrar(nombre: str) -> int:
    indice = _cargar()
    clave = _fold(nombre)
    coincidencias = [c for c in indice if c == clave or clave in c or c in clave]
    borradas = 0
    for c in coincidencias:
        for fichero in indice[c].get("ficheros", []):
            try:
                (CARPETA / fichero).unlink()
                borradas += 1
            except OSError:
                pass
        del indice[c]
    _guardar(indice)
    return borradas
