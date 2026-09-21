"""De que hablamos hoy: historia de España.

Sustituye al calendario de efemerides de sucesos, que era el nicho anterior.
Y no es una lista de titulos escrita de memoria - eso ya salio mal dos veces,
con articulos inventados que no existian en Wikipedia - sino las CATEGORIAS de
la Wikipedia en español, que se recorren y devuelven articulos que existen
seguro porque vienen de ella.

La otra razon para tirar de Wikipedia: para un Short hace falta UN hecho, no
un dosier. Y el primer parrafo de un articulo historico casi siempre trae el
hecho entero.
"""
from __future__ import annotations

import logging
import random

from . import research

logger = logging.getLogger(__name__)

# De lo concreto a lo general. Un Short necesita algo que pase, con gente
# dentro: "Batallas de España" da material; "Historia de España" da ensayos.
CATEGORIAS = (
    "Categoría:Batallas de España",
    "Categoría:Conquista de América",
    "Categoría:Reyes de España",
    "Categoría:Guerra civil española",
    "Categoría:Naufragios de España",
    "Categoría:Historia militar de España",
    "Categoría:Exploradores de España",
    "Categoría:Inquisición española",
    "Categoría:Al-Ándalus",
    "Categoría:Reconquista",
    "Categoría:Epidemias en España",
    "Categoría:Motines y revueltas en España",
    "Categoría:Atentados en España",
    "Categoría:Científicos de España",
    "Categoría:Monarcas de Castilla",
    "Categoría:Siglo de Oro",
)

# Lo que NO es un hecho contable en cuarenta segundos.
_NO_SIRVE = (
    "anexo:", "categoría:", "plantilla:", "wikiproyecto:", "portal:",
    "lista de", "cronología", "bibliografía", "historiografía",
)
_MINIMO_TITULO = 8


def _vale(titulo: str) -> bool:
    bajo = titulo.lower()
    if len(titulo) < _MINIMO_TITULO:
        return False
    return not any(malo in bajo for malo in _NO_SIRVE)


def articulos_de(categoria: str, cuantos: int = 200) -> list[str]:
    datos = research.peticion(
        "https://es.wikipedia.org/w/api.php",
        {"action": "query", "list": "categorymembers", "cmtitle": categoria,
         "cmlimit": min(500, cuantos), "cmnamespace": 0, "format": "json"},
    )
    if not datos:
        return []
    miembros = (datos.get("query") or {}).get("categorymembers") or []
    return [m["title"] for m in miembros if m.get("title") and _vale(m["title"])]


def candidatos(cuantos: int = 12, semilla: int | None = None) -> list[str]:
    """Temas posibles para los Shorts de hoy, de categorias distintas.

    De categorias DISTINTAS a proposito: tirando de una sola saldrian cinco
    batallas seguidas, y un canal que repite el mismo tipo de video cinco veces
    aburre antes de que te suscribas.
    """
    azar = random.Random(semilla)
    elegidas = azar.sample(CATEGORIAS, min(len(CATEGORIAS), max(4, cuantos // 2)))
    salida: list[str] = []
    for categoria in elegidas:
        articulos = articulos_de(categoria)
        if not articulos:
            continue
        azar.shuffle(articulos)
        salida.extend(articulos[:2])
    azar.shuffle(salida)
    logger.info("Historia: %s candidatos de %s categorias.", len(salida), len(elegidas))
    return salida[:cuantos]
