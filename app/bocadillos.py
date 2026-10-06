"""Bocadillos de comic sobre las ilustraciones.

Lo que le faltaba al canal, dicho por ella: "en los suyos hay personajes que
se hacen cosas entre ellos; en el tuyo hay una voz encima de unos dibujos". Y
tenia razon - un dibujo mas bonito no arregla que no haya nadie hablando.

No se anima la boca ni se mueve el personaje: eso es animacion de verdad y no
la podemos hacer. Lo que si se puede es lo que hacen los countryballs, que es
justo lo que ella señalo: el personaje esta quieto y lo que aparece es el
BOCADILLO. Con eso ya hay alguien hablando en pantalla.

Y va sincronizado de verdad, no a ojo: la narracion trae el tiempo de cada
caracter (voice_clone lo guarda para las diapositivas), asi que se busca la
frase entrecomillada dentro de la narracion y el bocadillo sale exactamente
cuando la voz la dice.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .branding import ACCENT_COLOR, BACKGROUND_COLOR, TEXT_COLOR

logger = logging.getLogger(__name__)

_CREMA = TEXT_COLOR
_TINTA = BACKGROUND_COLOR
_ROJO = ACCENT_COLOR
_FUENTE = "DejaVuSans-Bold.ttf"

# Una frase de bocadillo es corta por definicion: lo que cabe en un globo y se
# lee de un vistazo. Diez palabras caben en tres lineas del globo; partir una
# frase como «¡No me quites mas sangre, que ya me estoy muriendo!» en dos globos
# suena raro, asi que el tope deja entera una frase dicha de un tiron.
MAX_PALABRAS = 10


def _fuente(px: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(_FUENTE, px)
    except OSError:
        return ImageFont.load_default()


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower())
                   if unicodedata.category(c) != "Mn")


# Cuantas frases con globo y voz de personaje caben en una escena. Era 2 ("una
# frase y su respuesta: mas no cabe en cuatro segundos"), de cuando las
# escenas duraban cuatro segundos. Ahora la escena dura lo que dura su voz, y
# sus guiones traen conversaciones de seis o siete frases en el mismo sitio:
# con 2, en el #106 (Maricarmen) el traductor no partio las escenas, el tercer
# intento se acepto igual y de cada escena hablaron dos y el resto lo leyo el
# NARRADOR. "No hablan, solo narra". Los globos y las voces ya iban frase a
# frase, con su instante cada una, asi que el tope era lo unico que lo impedia.
MAX_CITAS = 8


def citas_de(narracion: str) -> list[str]:
    """TODAS las frases entrecomilladas de una escena, en orden.

    Ella: "pon menos narracion y mas conversaciones de los monigotes, que
    queda gracioso". Tiene razon y el codigo no dejaba: se cogia solo la
    PRIMERA comilla de cada escena, asi que un ida y vuelta - uno dice algo y
    el otro le contesta - se quedaba a medias, con el segundo monigote mudo
    aunque el guion hubiera escrito su respuesta.

    Se mezclan los dos tipos de comilla en una sola pasada y no una detras de
    otra: buscando primero las angulares y luego las rectas, un dialogo escrito
    con las dos salia en el orden equivocado.
    """
    if not narracion:
        return []
    fuera = []
    for m in re.finditer(r"[«“]([^»”]{2,80})[»”]|\"([^\"]{2,80})\"", narracion):
        frase = (m.group(1) or m.group(2) or "").strip(" .,;:")
        if frase and len(frase.split()) <= MAX_PALABRAS:
            fuera.append(frase)
        if len(fuera) >= MAX_CITAS:
            break
    return fuera


def todas_las_comillas(narracion: str) -> list[str]:
    """Todo lo que va entre comillas, SIN los topes de citas_de.

    Existe para poder avisar. citas_de tira en silencio la frase de mas de
    MAX_PALABRAS y la tercera de la escena - y una frase tirada no
    desaparece: la sigue diciendo la voz, pero la del NARRADOR y sin globo.
    Eso es lo que ella vio en el Motin de Esquilache ("a veces decia el
    narrador algo que tenia que decir el personaje"): «Desde hoy: sombreros
    mas pequeños y capas mas cortas» tiene nueve palabras. Comparando esta
    lista con la de citas_de se sabe que se ha quedado fuera."""
    if not narracion:
        return []
    return [(m.group(1) or m.group(2) or "").strip(" .,;:")
            for m in re.finditer(r"[«“]([^»”]{2,})[»”]|\"([^\"]{2,})\"", narracion)]


def cita_de(narracion: str) -> str:
    """La frase entrecomillada de una narracion, si la hay.

    El guion mete el dialogo DENTRO de la narracion, entre comillas. Asi la voz
    lo lee sin tener que narrar dos veces y el bocadillo solo tiene que
    encontrarlo.
    """
    for patron in (r"[«“]([^»”]{2,80})[»”]", r'"([^"]{2,80})"'):
        m = re.search(patron, narracion or "")
        if m:
            frase = m.group(1).strip(" .,;:")
            if frase and len(frase.split()) <= MAX_PALABRAS:
                return frase
    return ""


def cuando_se_dice(narracion: str, tiempos: list[float], cita: str,
                   desde: int = 0) -> tuple[float, float] | None:
    """(inicio, fin) de la frase dentro del audio de esa escena.

    tiempos[i] es el instante en que termina el caracter i, que es lo que
    guarda voice_clone. Si no cuadran las longitudes no se inventa nada: se
    devuelve None y no hay bocadillo, que es mejor que uno descuadrado.
    """
    if not cita or not tiempos or len(tiempos) != len(narracion or ""):
        return None
    # `desde` existe para la segunda frase de un dialogo: sin el, dos
    # personajes que dicen lo mismo - "«No»" y "«No»" - darian los dos el
    # mismo instante, y los dos bocadillos saldrian a la vez.
    posicion = _sin_tildes(narracion).find(_sin_tildes(cita), max(0, desde))
    if posicion < 0:
        return None
    fin_idx = min(posicion + len(cita), len(tiempos)) - 1
    inicio = tiempos[posicion - 1] if posicion > 0 else 0.0
    return max(0.0, inicio), max(inicio + 0.4, tiempos[fin_idx])


def donde_se_dice(narracion: str, cita: str, desde: int = 0) -> int:
    """En que caracter empieza esa frase, para seguir buscando tras ella."""
    return _sin_tildes(narracion or "").find(_sin_tildes(cita or ""), max(0, desde))


def dibujar(texto: str, ancho: int, alto: int, out_path: Path,
            lado: str = "izquierda") -> Path | None:
    """El globo, en PNG con transparencia, listo para superponer.

    Se dibuja UNA vez y ffmpeg lo superpone durante su ventana: generar los
    fotogramas uno a uno en PIL seria treinta veces mas lento para lo mismo.
    """
    try:
        px = max(30, int(ancho * 0.052))
        fuente = _fuente(px)
        lienzo = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
        dib = ImageDraw.Draw(lienzo)

        lineas = _repartir(dib, texto.upper(), fuente, int(ancho * 0.62))
        alto_linea = int(px * 1.25)
        an_texto = max(dib.textbbox((0, 0), l, font=fuente)[2] for l in lineas)
        al_texto = alto_linea * len(lineas)

        pad = int(px * 0.62)
        # A un lado, no centrado: el globo tapa menos dibujo y deja sitio al
        # rabo para apuntar a quien habla.
        # Arriba, en el quinto superior. Ahi hay cielo o humo en casi cualquier
        # ilustracion, asi que el globo no tapa al que habla - que era lo que
        # pasaba poniendolo a media altura: cubria el fuego y a los hombres.
        cx = int(ancho * (0.38 if lado == "izquierda" else 0.62))
        cy = int(alto * 0.20)
        caja = [cx - an_texto / 2 - pad, cy - al_texto / 2 - pad,
                cx + an_texto / 2 + pad, cy + al_texto / 2 + pad]

        # El rabo, largo y hacia abajo, que es lo que dice QUIEN habla. Corto no
        # se veia y el globo parecia un rotulo flotando.
        punta_x = cx + (int(ancho * 0.16) if lado == "izquierda" else -int(ancho * 0.16))
        punta_y = caja[3] + int(alto * 0.115)
        borde = max(3, int(px * 0.09))
        # Se dibuja dos veces: el contorno en tinta y encima el relleno, para
        # que el rabo tenga la misma linea negra que el globo.
        dib.polygon([(cx - pad * 1.1, caja[3] - 8), (cx + pad * 1.1, caja[3] - 8),
                     (punta_x, punta_y)], fill=_TINTA + (255,))
        dib.polygon([(cx - pad * 1.1 + borde * 1.6, caja[3] - 10),
                     (cx + pad * 1.1 - borde * 1.6, caja[3] - 10),
                     (punta_x, punta_y - borde * 2.2)], fill=_CREMA + (255,))
        dib.rounded_rectangle(caja, radius=int(px * 0.55),
                              fill=_CREMA + (255,), outline=_TINTA + (255,),
                              width=max(3, int(px * 0.09)))
        y = cy - al_texto / 2
        for linea in lineas:
            an = dib.textbbox((0, 0), linea, font=fuente)[2]
            dib.text((cx - an / 2, y), linea, font=fuente, fill=_TINTA + (255,))
            y += alto_linea

        lienzo.save(out_path)
        return out_path
    except Exception:
        logger.warning("No se ha podido dibujar el bocadillo %r.", texto[:30], exc_info=True)
        return None


def _repartir(dib, texto: str, fuente, ancho_max: int) -> list[str]:
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if dib.textbbox((0, 0), prueba, font=fuente)[2] <= ancho_max or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas[:3]
