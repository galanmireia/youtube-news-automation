"""Slides for the things a camera cannot photograph.

A disaster has photographs. A worm does not. Measured on the first computing
video: of twenty-five scenes, fourteen fell through to generic stock footage -
"server racks overheating warning lights night", "frozen computer screen error
network outage" - and of the eight that found a real photograph, five were
university buildings and three were corporate logos. That is not illustration,
it is wallpaper, and it is the whole of the "me aburre" complaint.

The answer is not a better stock search. There is no footage of a program
copying itself between machines in 1988. What there is, and what the dossier
is full of, is NUMBERS and SEQUENCE: six thousand machines, ten percent of the
internet, ninety-nine lines, three years' probation, a chronology that runs
over three days. Those can be drawn, and drawn better than any photograph of a
server rack would say them.

Every slide here BUILDS. It returns a list of frames rather than one image,
and the video shows them in turn, so a point arrives as the narration reaches
it instead of the viewer reading the whole slide in the first second and then
waiting. That is the difference between a slide and a caption, and it was the
part of the original request that the existing single fact card never had.

Design rules, so these look like one channel and not four:
  - the channel's own palette, never a new one
  - one idea per slide; a slide that needs a paragraph is a script problem
  - the number is the hero, at a size no photograph competes with
  - nothing decorative: every mark on the frame carries information
"""
import logging
import re
import subprocess
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw

from .branding import (
    ACCENT_COLOR,
    BACKGROUND_COLOR,
    TEXT_COLOR,
    _fit_single_line_font,
    _load_font,
    _text_width,
    _wrap_text,
)

logger = logging.getLogger(__name__)

# Dimmer than the body text: a slide has a foreground and a background, and
# without that separation everything shouts at once and nothing reads.
_MUTED_COLOR = (150, 143, 132)
# What a point that has not arrived yet looks like. Present, so the viewer can
# see the shape of what is coming, but clearly not the one being spoken.
_PENDING_COLOR = (92, 86, 79)

_FONT = "DejaVuSans-Bold.ttf"
_FONT_LIGHT = "DejaVuSans.ttf"

# The slide kinds the script may ask for. Anything else is ignored rather than
# guessed at - a misspelled kind should fall through to the ordinary imagery,
# not render as an empty frame.
TIPOS = ("cifra", "cronologia", "lista", "comparacion", "barras", "proporcion")


def _alto_linea(fuente) -> int:
    """One line's height, from the FONT rather than from the text in it.

    Measuring each line's own bounding box makes the leading depend on
    whether that line happens to contain an accent or a descender - so
    "maquinas habia" sits further from its neighbour than a line of
    lowercase does, and a wrapped paragraph comes out visibly uneven. The
    font's ascent and descent are the same for every line, which is what
    consistent leading means."""
    ascenso, descenso = fuente.getmetrics()
    return int((ascenso + descenso) * 1.18)


def _parrafo(
    draw: ImageDraw.ImageDraw, texto: str, fuente, x: int, y: int, ancho: int, color
) -> int:
    """Wrapped text with even leading. Returns the y below the last line."""
    alto = _alto_linea(fuente)
    for linea in _wrap_text(draw, texto, fuente, ancho):
        draw.text((x, y), linea, font=fuente, fill=color)
        y += alto
    return y


def _alto_parrafo(draw: ImageDraw.ImageDraw, texto: str, fuente, ancho: int) -> int:
    return len(_wrap_text(draw, texto, fuente, ancho)) * _alto_linea(fuente)


def _lienzo(width: int, height: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    imagen = Image.new("RGB", (width, height), BACKGROUND_COLOR)
    return imagen, ImageDraw.Draw(imagen)


def _regla(draw: ImageDraw.ImageDraw, x: int, y: int, ancho: int, alto: int) -> None:
    """The channel's accent rule. The one piece of furniture these share."""
    draw.rectangle([x, y, x + ancho, y + alto], fill=ACCENT_COLOR)


def _titulo(draw: ImageDraw.ImageDraw, texto: str, width: int, y: int) -> int:
    """A small caps heading over an accent rule. Returns the y below it."""
    if not texto:
        return y
    margen = int(width * 0.08)
    fuente = _fit_single_line_font(
        draw, texto.upper(), int(width - margen * 2), max(18, width // 38), 14
    )
    hueco = max(10, width // 90)
    grosor = max(3, width // 340)
    _regla(draw, margen, y, max(40, width // 18), grosor)
    y += grosor + hueco
    draw.text((margen, y), texto.upper(), font=fuente, fill=_MUTED_COLOR)
    return y + _alto_linea(fuente) + hueco


def cifra(valor: str, unidad: str, pie: str, width: int, height: int) -> list[Image.Image]:
    """One number, at the size the number deserves.

    Three frames: the figure, then its unit, then the line that gives it
    meaning. "6.000" means nothing; "6.000 ordenadores" means little; "el diez
    por ciento de todo internet" is the sentence the viewer repeats afterwards,
    and it lands last because that is the order the narration says it in."""
    margen = int(width * 0.08)
    ancho_util = width - margen * 2

    # Said the way it is spoken, not written out in full. "1.400.000.000" is
    # thirteen glyphs; at the size a hero number wants, on a vertical frame,
    # it did not fit at the smallest size the fitter would go to and ran off
    # both edges. It is also not how anybody reads it aloud.
    try:
        valor = _valor_corto(float(valor.replace(".", "").replace(",", ".")))
    except (AttributeError, ValueError):
        pass

    frames = []
    for paso in range(3):
        imagen, draw = _lienzo(width, height)
        # The figure is sized to the frame, not to a constant: a long number
        # and a short one like "99" should both fill the space they are given
        # rather than one overflowing and one looking lost. The floor is low
        # enough that something always fits.
        fuente_valor = _fit_single_line_font(
            draw, valor, ancho_util, int(height * 0.42), int(height * 0.05)
        )
        caja = draw.textbbox((0, 0), valor, font=fuente_valor)
        alto_valor = caja[3] - caja[1]
        y = int(height * 0.32) - alto_valor // 2
        draw.text((margen, y - caja[1]), valor, font=fuente_valor, fill=TEXT_COLOR)
        y += alto_valor + int(height * 0.03)

        _regla(draw, margen, y, max(60, width // 12), max(4, width // 300))
        y += max(4, width // 300) + int(height * 0.045)

        if paso >= 1 and unidad:
            fuente_unidad = _fit_single_line_font(
                draw, unidad.upper(), ancho_util, max(22, width // 26), 16
            )
            draw.text((margen, y), unidad.upper(), font=fuente_unidad, fill=ACCENT_COLOR)
            y += _alto_linea(fuente_unidad) + int(height * 0.03)

        if paso >= 2 and pie:
            fuente_pie = _load_font(_FONT_LIGHT, max(20, width // 34))
            _parrafo(draw, pie, fuente_pie, margen, y, ancho_util, _MUTED_COLOR)

        frames.append(imagen)
    return frames


def cronologia(puntos: list[str], titulo: str, width: int, height: int) -> list[Image.Image]:
    """Dated events down a spine, arriving one at a time.

    The events that have not arrived are drawn dim rather than left blank. A
    viewer who can see that three more things are coming waits for them; one
    looking at empty space assumes the slide is finished.

    Every measurement here is taken ONCE, before the frames, and reused by all
    of them. The first version sized the indent from the current event's dot,
    which is larger than the others - so the text shifted sideways each time
    the highlight moved, a jitter invisible in a still and impossible to miss
    in the video.
    """
    puntos = [p for p in puntos if p.strip()][:5]
    if not puntos:
        return []
    margen = int(width * 0.08)

    # Measured on a throwaway canvas so the layout is identical in every frame.
    medidor = ImageDraw.Draw(Image.new("RGB", (width, height)))
    fuente = _load_font(_FONT, max(20, width // 40))
    fuente_fecha = _load_font(_FONT, max(18, width // 48))
    radio_max = max(7, width // 140)
    espina_x = margen + radio_max
    texto_x = espina_x + radio_max * 3
    ancho_texto = width - texto_x - margen

    partidos = []
    for punto in puntos:
        fecha, _, hecho = punto.partition(" - ")
        if not hecho:
            fecha, _, hecho = punto.partition(" — ")
        partidos.append((fecha.strip(), hecho.strip()) if hecho else ("", punto.strip()))

    # Each event is as tall as its own text needs, plus a constant gap - so a
    # two-line event does not overlap the next one and a chronology of short
    # events does not leave half the frame empty.
    separacion = max(14, height // 46)
    altos = []
    for fecha, hecho in partidos:
        alto = _alto_parrafo(medidor, hecho, fuente, ancho_texto)
        if fecha:
            alto += _alto_linea(fuente_fecha)
        altos.append(alto + separacion)

    y0 = _titulo(medidor, titulo, width, int(height * 0.11))
    disponible = int(height * 0.92) - y0
    total = sum(altos)
    # Centred in what is left, so the block sits in the frame rather than
    # hanging from the top with a dead third underneath.
    y0 += max(0, (disponible - total) // 2)

    frames = []
    for revelados in range(1, len(puntos) + 1):
        imagen, draw = _lienzo(width, height)
        _titulo(draw, titulo, width, int(height * 0.11))

        centros = []
        y = y0
        for i, (fecha, hecho) in enumerate(partidos):
            centro = y + (_alto_linea(fuente_fecha) if fecha else _alto_linea(fuente)) // 2
            centros.append(centro)
            y += altos[i]

        # The spine reaches the event being spoken and no further.
        if revelados > 1:
            draw.rectangle(
                [espina_x - max(1, width // 960), centros[0],
                 espina_x + max(1, width // 960), centros[revelados - 1]],
                fill=ACCENT_COLOR,
            )

        y = y0
        for i, (fecha, hecho) in enumerate(partidos):
            visible = i < revelados
            actual = i == revelados - 1
            radio = radio_max if actual else max(5, width // 200)
            draw.ellipse(
                [espina_x - radio, centros[i] - radio, espina_x + radio, centros[i] + radio],
                fill=ACCENT_COLOR if visible else _PENDING_COLOR,
            )
            color = TEXT_COLOR if actual else (_MUTED_COLOR if visible else _PENDING_COLOR)
            ty = y
            if fecha:
                draw.text((texto_x, ty), fecha.upper(), font=fuente_fecha,
                          fill=ACCENT_COLOR if actual else color)
                ty += _alto_linea(fuente_fecha)
            _parrafo(draw, hecho, fuente, texto_x, ty, ancho_texto, color)
            y += altos[i]

        frames.append(imagen)
    return frames


def lista(puntos: list[str], titulo: str, width: int, height: int) -> list[Image.Image]:
    """Numbered points appearing as they are spoken."""
    puntos = [p.strip() for p in puntos if p.strip()][:5]
    if not puntos:
        return []
    margen = int(width * 0.08)
    medidor = ImageDraw.Draw(Image.new("RGB", (width, height)))
    fuente = _load_font(_FONT, max(22, width // 34))
    fuente_num = _load_font(_FONT, max(26, width // 26))

    # The indent comes from the widest number, not from each one, so a list
    # that reaches double figures does not step sideways at the tenth point.
    ancho_num = max(_text_width(medidor, f"{i + 1}", fuente_num) for i in range(len(puntos)))
    texto_x = margen + ancho_num + max(18, width // 60)
    ancho_texto = width - texto_x - margen

    separacion = max(16, height // 40)
    altos = [_alto_parrafo(medidor, punto, fuente, ancho_texto) + separacion for punto in puntos]

    y0 = _titulo(medidor, titulo, width, int(height * 0.13))
    y0 += max(0, (int(height * 0.92) - y0 - sum(altos)) // 2)

    frames = []
    for revelados in range(1, len(puntos) + 1):
        imagen, draw = _lienzo(width, height)
        _titulo(draw, titulo, width, int(height * 0.13))
        y = y0
        for i, punto in enumerate(puntos):
            visible = i < revelados
            actual = i == revelados - 1
            color = TEXT_COLOR if actual else (_MUTED_COLOR if visible else _PENDING_COLOR)
            draw.text((margen, y), f"{i + 1}", font=fuente_num,
                      fill=ACCENT_COLOR if visible else _PENDING_COLOR)
            _parrafo(draw, punto, fuente, texto_x, y, ancho_texto, color)
            y += altos[i]
        frames.append(imagen)
    return frames


def comparacion(
    izquierda: str, derecha: str, titulo: str, width: int, height: int
) -> list[Image.Image]:
    """Two things side by side, the second arriving after the first.

    For the shape this subject keeps producing: what it was meant to do
    against what it did, what was claimed against what was found, the cost
    before and after. The reveal matters more here than anywhere else - the
    whole point is the second panel landing against the first."""
    izquierda, derecha = izquierda.strip(), derecha.strip()
    if not izquierda or not derecha:
        return []
    margen = int(width * 0.07)
    separacion = int(width * 0.05)
    medidor = ImageDraw.Draw(Image.new("RGB", (width, height)))
    fuente = _load_font(_FONT, max(22, width // 32))

    ancho_panel = (width - margen * 2 - separacion) // 2
    ancho_texto = ancho_panel - margen
    y0 = _titulo(medidor, titulo, width, int(height * 0.13))
    alto_panel = int(height * 0.90) - y0
    grosor = max(4, width // 300)

    frames = []
    for revelados in (1, 2):
        imagen, draw = _lienzo(width, height)
        _titulo(draw, titulo, width, int(height * 0.13))
        for i, texto in enumerate((izquierda, derecha)):
            visible = i < revelados
            x = margen + i * (ancho_panel + separacion)
            draw.rectangle([x, y0, x + ancho_panel, y0 + alto_panel],
                           fill=(34, 30, 28) if visible else (30, 27, 25))
            _regla(draw, x, y0, ancho_panel if visible else ancho_panel // 4, grosor)
            alto_texto = _alto_parrafo(medidor, texto, fuente, ancho_texto)
            _parrafo(
                draw, texto, fuente, x + margen // 2,
                y0 + (alto_panel - alto_texto) // 2, ancho_texto,
                TEXT_COLOR if visible else _PENDING_COLOR,
            )
        frames.append(imagen)
    return frames


def _valor_legible(valor: float) -> str:
    """A number as Spanish writes it, without trailing noise."""
    if valor == int(valor):
        return f"{int(valor):,}".replace(",", ".")
    return f"{valor:,.1f}".replace(",", "@").replace(".", ",").replace("@", ".")


def _valor_corto(valor: float) -> str:
    """The same number, short enough not to outweigh the bar it labels.

    "10.000.000.000" is thirteen glyphs and reads as a row of zeros rather
    than as a quantity; rendered on a bar it was wider than the bar. Spanish
    says it in two words, and two words is what a viewer with four seconds
    actually reads."""
    if valor >= 1_000_000:
        millones = valor / 1_000_000
        texto = _valor_legible(round(millones, 1) if millones < 10 else round(millones))
        return f"{texto} millones"
    return _valor_legible(valor)


def barras(
    puntos: list[dict], titulo: str, width: int, height: int
) -> list[Image.Image]:
    """Magnitudes compared, one bar arriving at a time.

    One series, so one colour and no legend - the heading says what is being
    measured, and a legend box with a single swatch would only restate it. The
    UNIT belongs in that heading too, for the same reason: repeating "$" on
    every bar is the legend problem again, one row down.

    No gridlines either. With five bars or fewer the value sits on each bar's
    tip, and a direct label is worth more than the axis it replaces; drawing
    both would be ink that is not data. The bar is capped well inside its band
    so the leftover is air rather than a filled slot, its end is rounded and
    its base is square, and the label moves outside the bar when it will not
    fit inside with room to breathe - a clipped number is worse than one
    standing beside the bar.
    """
    limpios = []
    for punto in puntos[:5]:
        if not isinstance(punto, dict):
            continue
        etiqueta = str(punto.get("etiqueta") or "").strip()
        try:
            valor = float(str(punto.get("valor")).replace(".", "").replace(",", "."))
        except (TypeError, ValueError):
            continue
        if etiqueta and valor > 0:
            limpios.append((etiqueta, valor))
    if len(limpios) < 2:
        # One bar is not a comparison; that is a figure, and `cifra` draws it
        # better than a chart with nothing to compare against would.
        return []

    margen = int(width * 0.08)
    medidor = ImageDraw.Draw(Image.new("RGB", (width, height)))
    fuente_etq = _load_font(_FONT, max(20, width // 46))
    fuente_val = _load_font(_FONT, max(22, width // 40))

    mayor = max(v for _, v in limpios)
    ancho_etq = max(_text_width(medidor, e, fuente_etq) for e, _ in limpios)
    x0 = margen + ancho_etq + max(20, width // 60)
    ancho_max = width - x0 - margen - max(90, width // 12)

    y0 = _titulo(medidor, titulo, width, int(height * 0.13))
    banda = int((height * 0.88 - y0) / len(limpios))
    # Capped inside the band: the leftover is air, not a filled slot.
    grosor = min(int(banda * 0.5), max(28, height // 18))
    radio = max(4, grosor // 6)

    frames = []
    for revelados in range(1, len(limpios) + 1):
        imagen, draw = _lienzo(width, height)
        _titulo(draw, titulo, width, int(height * 0.13))
        for i, (etiqueta, valor) in enumerate(limpios):
            visible = i < revelados
            actual = i == revelados - 1
            cy = y0 + banda * i + banda // 2
            arriba, abajo = cy - grosor // 2, cy + grosor // 2

            color_texto = TEXT_COLOR if actual else (_MUTED_COLOR if visible else _PENDING_COLOR)
            draw.text(
                (x0 - max(20, width // 60) - _text_width(draw, etiqueta, fuente_etq),
                 cy - _alto_linea(fuente_etq) // 2),
                etiqueta, font=fuente_etq, fill=color_texto,
            )
            if not visible:
                continue
            largo = max(radio * 2, int(ancho_max * valor / mayor))
            # Square at the baseline, rounded at the data end.
            draw.rectangle([x0, arriba, x0 + largo - radio, abajo], fill=ACCENT_COLOR)
            draw.rounded_rectangle(
                [x0 + largo - radio * 2, arriba, x0 + largo, abajo],
                radius=radio, fill=ACCENT_COLOR,
            )
            texto_val = _valor_corto(valor)
            ancho_val = _text_width(draw, texto_val, fuente_val)
            # Measured, not assumed: inside only when it fits with padding.
            hueco = max(14, width // 90)
            if ancho_val + hueco * 2 <= largo:
                # Set INSIDE the fill, so the colour is chosen against the
                # fill and not against the surface. Computed rather than
                # eyeballed: the surface colour on this red is 3.03:1, which
                # fails for anything but large text; the ink colour is 4.94:1.
                vx, color_val = x0 + largo - hueco - ancho_val, TEXT_COLOR
            else:
                vx, color_val = x0 + largo + hueco, color_texto
            draw.text((vx, cy - _alto_linea(fuente_val) // 2), texto_val,
                      font=fuente_val, fill=color_val)
        frames.append(imagen)
    return frames


def proporcion(
    parte: str, de_cada: str, titulo: str, pie: str, width: int, height: int
) -> list[Image.Image]:
    """One share of a whole: the number, then the share filling its track.

    A single percentage is a figure before it is a chart, so the number leads
    and the bar follows to say how much of the whole that is. The remainder is
    a step off the surface rather than a second colour - there is one measure
    here, and a second hue would invent a second series."""
    try:
        porcentaje = float(str(parte).replace("%", "").replace(",", ".").strip())
    except (TypeError, ValueError):
        return []
    if not 0 < porcentaje <= 100:
        return []

    margen = int(width * 0.08)
    ancho_util = width - margen * 2
    medidor = ImageDraw.Draw(Image.new("RGB", (width, height)))
    fuente_cifra = _fit_single_line_font(
        medidor, f"{_valor_legible(porcentaje)}%", ancho_util,
        int(height * 0.30), int(height * 0.12),
    )
    # Fitted to the frame, not set at a nominal size. "de todos los ordenadores
    # conectados en 1988" at a fixed size ran off the right edge and the last
    # word was cut in half - a label that does not fit is measured, never
    # clipped. Shrunk to a floor first, then allowed to wrap below it.
    fuente_de = _fit_single_line_font(
        medidor, (de_cada or "").upper(), ancho_util, max(22, width // 30), max(15, width // 52)
    )
    fuente_pie = _load_font(_FONT_LIGHT, max(20, width // 36))

    frames = []
    for paso in range(3):
        imagen, draw = _lienzo(width, height)
        y = _titulo(draw, titulo, width, int(height * 0.12)) if titulo else int(height * 0.18)

        texto_cifra = f"{_valor_legible(porcentaje)}%"
        draw.text((margen, y), texto_cifra, font=fuente_cifra, fill=TEXT_COLOR)
        y += _alto_linea(fuente_cifra) + int(height * 0.04)

        alto_pista = max(18, height // 34)
        radio = alto_pista // 2
        draw.rounded_rectangle([margen, y, margen + ancho_util, y + alto_pista],
                               radius=radio, fill=(46, 41, 38))
        if paso >= 1:
            largo = max(alto_pista, int(ancho_util * porcentaje / 100))
            draw.rounded_rectangle([margen, y, margen + largo, y + alto_pista],
                                   radius=radio, fill=ACCENT_COLOR)
        y += alto_pista + int(height * 0.035)

        if paso >= 1 and de_cada:
            y = _parrafo(draw, de_cada.upper(), fuente_de, margen, y, ancho_util, _MUTED_COLOR)
            y += int(height * 0.025)
        if paso >= 2 and pie:
            _parrafo(draw, pie, fuente_pie, margen, y, ancho_util, _MUTED_COLOR)
        frames.append(imagen)
    return frames


def render(spec: dict, width: int, height: int) -> list[Image.Image]:
    """Draws whatever slide the script asked for, or nothing.

    Returning an empty list is a valid answer and the caller falls back to
    ordinary imagery. A half-filled slide is worse than a stock clip: the
    stock clip at least does not look broken."""
    tipo = (spec.get("tipo") or "").strip().lower()
    titulo = (spec.get("titulo") or "").strip()
    try:
        if tipo == "cifra":
            valor = (spec.get("valor") or "").strip()
            if not valor:
                return []
            return cifra(valor, (spec.get("unidad") or "").strip(),
                         (spec.get("pie") or "").strip(), width, height)
        if tipo == "cronologia":
            return cronologia(spec.get("puntos") or [], titulo, width, height)
        if tipo == "lista":
            return lista(spec.get("puntos") or [], titulo, width, height)
        if tipo == "barras":
            return barras(spec.get("puntos") or [], titulo, width, height)
        if tipo == "proporcion":
            return proporcion(spec.get("parte") or "", (spec.get("de_cada") or "").strip(),
                              titulo, (spec.get("pie") or "").strip(), width, height)
        if tipo == "comparacion":
            return comparacion((spec.get("izquierda") or ""), (spec.get("derecha") or ""),
                               titulo, width, height)
    except Exception:
        logger.exception("No se ha podido dibujar la diapositiva %r", spec)
        return []
    logger.info("Tipo de diapositiva desconocido: %r; se ignora.", tipo)
    return []


# Words that appear in every sentence and identify nothing. Anchoring a
# reveal on "para" would place it at the first preposition in the scene.
_VACIAS = frozenset("""
para pero como cuando donde porque aunque desde hasta sobre entre sin con los las una unos unas
que del por más muy fue era son han hay este esta esto ese esa eso sus nos les ya solo tras
the and that this with from they were been have has had for but not you all can its
what when where which while about after before because through another between against
would could should their there these those them then than over under into more most
some such only just also very much many said says told when who whom whose how why
""".split())


def _palabras_ancla(texto: str) -> list[str]:
    """The words in a slide point worth looking for in the narration.

    Longest first: a long word is a rarer word, and a rarer word lands where
    the point is actually said rather than at the first "que" in the scene."""
    palabras = re.findall(r"[^\W\d_]{4,}", texto, re.UNICODE)
    utiles = [p for p in palabras if _fold(p) not in _VACIAS]
    return sorted(utiles, key=len, reverse=True)


def _fold(texto: str) -> str:
    plano = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in plano if not unicodedata.combining(c))


def _anclas_del_spec(spec: dict, revelados: int) -> list[str]:
    """What each reveal after the first is 'about', as text to look for."""
    tipo = (spec.get("tipo") or "").strip().lower()
    if tipo in ("cronologia", "lista"):
        puntos = [str(p) for p in (spec.get("puntos") or [])][:revelados]
        return puntos + [""] * (revelados - len(puntos))
    if tipo == "barras":
        puntos = spec.get("puntos") or []
        return [str(p.get("etiqueta", "")) if isinstance(p, dict) else ""
                for p in puntos][:revelados]
    if tipo == "comparacion":
        return [str(spec.get("izquierda") or ""), str(spec.get("derecha") or "")][:revelados]
    if tipo == "cifra":
        return [str(spec.get("valor") or ""), str(spec.get("unidad") or ""),
                str(spec.get("pie") or "")][:revelados]
    if tipo == "proporcion":
        return [str(spec.get("parte") or ""), str(spec.get("de_cada") or ""),
                str(spec.get("pie") or "")][:revelados]
    return [""] * revelados


def momentos_de(
    spec: dict, revelados: int, narracion: str, tiempos: list[float], duracion: float
) -> list[float] | None:
    """When each reveal should appear, read off the narration's own timing.

    The slide and the narration say the same things in different words, but
    they share the rare ones - a name, a program, a place - and the API
    returns the time of every character it spoke. So each point is placed at
    the moment its rarest word is said, and a point whose words never appear
    keeps its share of what is left.

    Returns None when nothing could be matched at all, and the caller shares
    the scene out evenly as before: a slide built on one lucky match and four
    guesses is worse than one that is honestly even."""
    if revelados < 2 or not narracion or len(tiempos) != len(narracion) or duracion <= 0:
        return None

    plano = _fold(narracion)
    anclas = _anclas_del_spec(spec, revelados)
    # Never before the scene starts; the first reveal is the slide appearing.
    momentos: list[float | None] = [0.0] + [None] * (revelados - 1)
    # Searched left to right and never backwards: the points are in the order
    # the script wrote them, and a later point matching an earlier word would
    # put the reveals out of sequence.
    desde = 0
    encontrados = 0
    for i in range(1, revelados):
        for palabra in _palabras_ancla(anclas[i]):
            pos = plano.find(_fold(palabra), desde)
            if pos == -1:
                continue
            fin = min(pos + len(palabra), len(tiempos)) - 1
            momentos[i] = float(tiempos[fin])
            desde = pos + len(palabra)
            encontrados += 1
            break

    if not encontrados:
        return None

    # Points nobody said are spread evenly between the two that were, so an
    # unmatched point still arrives in its place in the run rather than all
    # of them piling up at one end.
    definitivos: list[float] = [0.0] * revelados
    i = 0
    while i < revelados:
        if momentos[i] is not None:
            definitivos[i] = momentos[i]
            i += 1
            continue
        # How many in a row have no moment, and what brackets them.
        j = i
        while j < revelados and momentos[j] is None:
            j += 1
        antes = definitivos[i - 1] if i > 0 else 0.0
        despues = momentos[j] if j < revelados else duracion
        paso = (max(despues, antes) - antes) / (j - i + 1)
        for k in range(i, j):
            definitivos[k] = antes + paso * (k - i + 1)
        i = j
    # Monotonic: a matched point can still fall before one that was filled in.
    for i in range(1, revelados):
        definitivos[i] = max(definitivos[i], definitivos[i - 1])

    # A reveal that lands with no time to be read is worse than one slightly
    # early, so each gets a floor and the last must still be seen.
    minimo = min(0.6, duracion / (revelados * 2))
    for i in range(1, revelados):
        definitivos[i] = max(definitivos[i], definitivos[i - 1] + minimo)
    tope = duracion - minimo
    if definitivos[-1] > tope:
        # Squeezed back from the end, keeping the order.
        for i in range(revelados - 1, 0, -1):
            definitivos[i] = min(definitivos[i], tope - minimo * (revelados - 1 - i))
            definitivos[i] = max(definitivos[i], definitivos[i - 1] + 0.05)
    return definitivos


# How long the finished slide holds after its last point has arrived. A build
# that lands its final line and cuts immediately reads as an accident; the
# viewer needs a moment with the whole thing.
_REMATE = 0.30


def construir_clip(
    frames: list[Image.Image], out_path: Path, duracion: float, fps: int = 30,
    momentos: list[float] | None = None,
) -> Path | None:
    """Turns the reveal into a video clip of exactly `duracion` seconds.

    A clip and not a still, deliberately: the builder gives stills a slow Ken
    Burns zoom, which is right for a photograph and wrong for type - it
    resamples the text every frame and softens it. An .mp4 is treated as
    footage and passes through at its own size.

    The reveals share the scene evenly, since each one answers to roughly a
    clause of narration, except that the last holds a little longer so the
    completed slide is seen as a whole before the cut."""
    if not frames or duracion <= 0:
        return None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rutas = []
    for i, frame in enumerate(frames):
        ruta = out_path.parent / f"{out_path.stem}_{i:02d}.png"
        frame.save(ruta)
        rutas.append(ruta)

    if momentos and len(momentos) == len(frames):
        # Each reveal lasts until the next one is due. The moments come from
        # where the narration actually says each point, so a slide whose first
        # item is dwelt on and whose last three arrive in a rush is built that
        # way too.
        limites = list(momentos) + [duracion]
        duraciones = [max(0.15, limites[i + 1] - limites[i]) for i in range(len(frames))]
    else:
        # No moments: share the scene out evenly. This was the only behaviour,
        # and it is a guess - "each reveal answers to roughly a clause" was
        # something I assumed rather than measured, and she heard it drift.
        remate = min(_REMATE, duracion / (len(frames) + 1))
        por_frame = (duracion - remate) / len(frames)
        duraciones = [por_frame] * len(frames)
        duraciones[-1] += remate

    # A second of slack on the final image, so the frame count below always
    # has material to reach. It is trimmed off, and it lands on the frame that
    # holds anyway.
    duraciones[-1] += 1.0
    lista = out_path.parent / f"{out_path.stem}_lista.txt"
    lineas = []
    for ruta, dur in zip(rutas, duraciones):
        lineas.append(f"file '{ruta.name}'")
        lineas.append(f"duration {dur:.3f}")
    lineas.append(f"file '{rutas[-1].name}'")
    lista.write_text("\n".join(lineas) + "\n")

    orden = [
        "ffmpeg", "-y", "-nostdin", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(lista),
        "-vsync", "cfr", "-r", str(fps),
        "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast",
        # Counted in FRAMES, not seconds. Measured: on a source of still
        # images the demuxer builds, "-t 16.1" returned 15.767 - a third of a
        # second short, every time - and the join would then have had to
        # stretch the clip to cover its scene. A frame count is exact by
        # construction, and 483 frames at 30fps came back as 16.100000.
        "-frames:v", str(max(1, round(duracion * fps))),
        str(out_path),
    ]
    try:
        subprocess.run(orden, check=True, capture_output=True, timeout=180)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        salida = getattr(exc, "stderr", b"") or b""
        logger.warning("No se ha podido montar el clip de la diapositiva: %s",
                       salida.decode("utf-8", "replace")[:300])
        return None
    finally:
        lista.unlink(missing_ok=True)
        for ruta in rutas:
            ruta.unlink(missing_ok=True)
    logger.info(
        "Diapositiva montada: %s fotogramas en %.2fs (%s).",
        len(frames), duracion, out_path.name,
    )
    return out_path
