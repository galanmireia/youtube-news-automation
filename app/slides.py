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
import subprocess
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
TIPOS = ("cifra", "cronologia", "lista", "comparacion")


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
    frames = []

    for paso in range(3):
        imagen, draw = _lienzo(width, height)
        # The figure is sized to the frame, not to a constant: a long number
        # like "1.400.000" and a short one like "99" should both fill the
        # space they are given rather than one overflowing and one looking lost.
        fuente_valor = _fit_single_line_font(
            draw, valor, ancho_util, int(height * 0.42), int(height * 0.10)
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
        if tipo == "comparacion":
            return comparacion((spec.get("izquierda") or ""), (spec.get("derecha") or ""),
                               titulo, width, height)
    except Exception:
        logger.exception("No se ha podido dibujar la diapositiva %r", spec)
        return []
    logger.info("Tipo de diapositiva desconocido: %r; se ignora.", tipo)
    return []


# How long the finished slide holds after its last point has arrived. A build
# that lands its final line and cuts immediately reads as an accident; the
# viewer needs a moment with the whole thing.
_REMATE = 0.30


def construir_clip(
    frames: list[Image.Image], out_path: Path, duracion: float, fps: int = 30
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
