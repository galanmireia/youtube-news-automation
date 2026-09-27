import io
import math
import logging
import subprocess
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

from .config import CHANNEL_LOGO_URL, CHANNEL_NAME

logger = logging.getLogger(__name__)

# Matches the channel's actual logo (dark warm charcoal card, red circle,
# cream-white text) so every generated graphic - intro card, name tags,
# thumbnails - reads as the same brand instead of a generic placeholder look.
BACKGROUND_COLOR = (26, 23, 21)
ACCENT_COLOR = (196, 30, 42)
TEXT_COLOR = (240, 235, 220)

_BACKGROUND_COLOR = BACKGROUND_COLOR
_ACCENT_COLOR = ACCENT_COLOR

INTRO_NARRATION = f"{CHANNEL_NAME}. Nuestra historia, en un minuto."

# YouTube avatar CDN URLs take a "=sNNN-..." size suffix; try a bigger version
# of the logo first (better quality once scaled up to full video frame size),
# falling back to the exact URL given if that request fails for any reason.
_LOGO_URL_CANDIDATES = (
    [CHANNEL_LOGO_URL.replace("=s160-", "=s800-")] if "=s160-" in CHANNEL_LOGO_URL else []
) + [CHANNEL_LOGO_URL]

_logo_cache: Image.Image | None = None
_logo_fetch_attempted = False


def _get_logo() -> Image.Image | None:
    global _logo_cache, _logo_fetch_attempted
    if _logo_cache is not None:
        return _logo_cache
    if _logo_fetch_attempted:
        return None
    _logo_fetch_attempted = True

    for url in _LOGO_URL_CANDIDATES:
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            _logo_cache = Image.open(io.BytesIO(response.content)).convert("RGB")
            return _logo_cache
        except Exception:
            continue
    logger.warning("No se pudo descargar el logo del canal, se usara una tarjeta de intro solo con texto")
    return None


def _load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


def _draw_text_intro_card(image: Image.Image, width: int, height: int) -> None:
    draw = ImageDraw.Draw(image)

    accent_thickness = max(4, height // 150)
    accent_y = height // 2
    draw.rectangle([0, accent_y, width, accent_y + accent_thickness], fill=_ACCENT_COLOR)

    title_font = _load_font("DejaVuSans-Bold.ttf", max(40, width // 10))
    title_text = CHANNEL_NAME.upper()
    title_box = draw.textbbox((0, 0), title_text, font=title_font)
    title_w, title_h = title_box[2] - title_box[0], title_box[3] - title_box[1]
    draw.text(
        ((width - title_w) / 2, accent_y - accent_thickness - title_h - 20),
        title_text,
        font=title_font,
        fill=TEXT_COLOR,
    )

    tagline_font = _load_font("DejaVuSans-Bold.ttf", max(20, width // 28))
    tagline_text = "TU INFORMADOR DE CONFIANZA"
    tagline_box = draw.textbbox((0, 0), tagline_text, font=tagline_font)
    tagline_w = tagline_box[2] - tagline_box[0]
    draw.text(
        ((width - tagline_w) / 2, accent_y + accent_thickness + 20),
        tagline_text,
        font=tagline_font,
        fill=_ACCENT_COLOR,
    )


def generate_intro_card(out_path: Path, width: int, height: int) -> Path:
    """Builds the opening scene every video starts with: the channel's real
    logo centered on its brand background. Falls back to a plain text-drawn
    card (name + tagline) if the logo can't be downloaded for any reason, so
    a network hiccup never breaks video generation."""
    image = Image.new("RGB", (width, height), _BACKGROUND_COLOR)

    logo = _get_logo()
    if logo is not None:
        logo_size = int(min(width, height) * 0.55)
        logo_resized = logo.resize((logo_size, logo_size), Image.LANCZOS)

        # The logo file is a square with a white background. Pasting it as-is
        # put a white box on the dark card - it read as a sticker stuck on
        # top rather than part of the design. Masking to the inscribed circle
        # keeps only the logo's own round badge.
        # Inset slightly: the badge doesn't quite touch the edge of the file,
        # so masking at the exact inscribed circle leaves a thin white rim.
        inset = max(1, round(logo_size * 0.015))
        mask = Image.new("L", (logo_size, logo_size), 0)
        ImageDraw.Draw(mask).ellipse([inset, inset, logo_size - 1 - inset, logo_size - 1 - inset], fill=255)

        image.paste(logo_resized, ((width - logo_size) // 2, (height - logo_size) // 2), mask)
    else:
        _draw_text_intro_card(image, width, height)

    image.save(out_path, quality=92)
    return out_path


def name_tag_bar_height(frame_height: int) -> int:
    """Bar height as a fraction of the frame - noticeably smaller than the
    old baked-in version (which was ~1/9th of the frame and stayed on
    screen for the whole shot) since it now only needs to read clearly
    during its brief slide-in/hold/slide-out instead of being a permanent
    fixture."""
    return max(50, frame_height // 13)


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    return draw.textbbox((0, 0), text, font=font)[2]


def _fit_single_line_font(
    draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int, min_size: int
) -> ImageFont.FreeTypeFont:
    """Largest font size at which the text still fits on one line. Names like
    "Universidad Autonoma del Estado de Mexico" overflow the bar at the
    nominal size and used to be drawn straight off the right edge, cut
    mid-word."""
    size = start_size
    font = _load_font("DejaVuSans-Bold.ttf", size)
    while size > min_size and _text_width(draw, text, font) > max_width:
        size -= 2
        font = _load_font("DejaVuSans-Bold.ttf", size)
    return font


def render_name_tag_bar(name: str, role: str, width: int, bar_height: int) -> Image.Image:
    """Renders just the TV-news-style lower third (name + role over a solid
    bar) as its own transparent image, sized to the bar's own height rather
    than the full frame. video_builder composites this onto the photo with
    an animated vertical position (sliding up from off-screen, holding
    briefly, sliding back down) instead of baking it permanently into the
    photo, so it reads as a temporary caption rather than a fixed label."""
    bar = Image.new("RGBA", (width, bar_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bar)

    accent_thickness = max(3, bar_height // 12)
    draw.rectangle([0, 0, width, accent_thickness], fill=_ACCENT_COLOR + (255,))
    draw.rectangle([0, accent_thickness, width, bar_height], fill=(0, 0, 0, 190))

    left_margin = width * 0.04
    available_width = int(width - left_margin * 2)

    name_text = name.upper()
    name_font = _fit_single_line_font(draw, name_text, available_width, max(18, bar_height // 3), 14)
    name_y = accent_thickness + bar_height // 10
    draw.text((left_margin, name_y), name_text, font=name_font, fill=TEXT_COLOR + (255,))

    if role:
        role_font = _fit_single_line_font(draw, role, available_width, max(13, bar_height // 5), 11)
        name_box = draw.textbbox((0, 0), name_text, font=name_font)
        role_y = name_y + (name_box[3] - name_box[1]) + bar_height // 14
        draw.text((left_margin, role_y), role, font=role_font, fill=(220, 220, 220, 255))

    return bar


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if current and _text_width(draw, trial, font) > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def render_highlight_box(text: str, box_width: int, box_height: int) -> Image.Image:
    """Small caption card for scenes that end up using generic stock video
    (no real photo tied to what's being said) - shows the scene's own key
    fact so the point doesn't get lost in an otherwise generic shot."""
    box = Image.new("RGBA", (box_width, box_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(box)

    draw.rounded_rectangle([0, 0, box_width, box_height], radius=box_height // 6, fill=(0, 0, 0, 190))
    accent_width = max(4, box_width // 45)
    draw.rectangle([0, 0, accent_width, box_height], fill=_ACCENT_COLOR + (255,))

    text_left = accent_width + box_height // 4
    available_width = box_width - text_left - box_height // 6
    max_lines = 3

    # Shrink until the wrapped text fits the box in both directions - a word
    # too long for one line (e.g. "INVESTIGA") otherwise just runs past the
    # edge of the card and gets clipped mid-word.
    size = max(16, box_height // 4)
    while size > 14:
        font = _load_font("DejaVuSans-Bold.ttf", size)
        lines = _wrap_text(draw, text.upper(), font, available_width)
        fits_width = all(_text_width(draw, line, font) <= available_width for line in lines)
        if fits_width and len(lines) <= max_lines and len(lines) * (size + 6) <= box_height - box_height // 6:
            break
        size -= 2
    else:
        font = _load_font("DejaVuSans-Bold.ttf", 14)
        lines = _wrap_text(draw, text.upper(), font, available_width)[:max_lines]

    line_height = font.size + 6
    total_h = line_height * len(lines)
    y = (box_height - total_h) / 2
    for line in lines:
        draw.text((text_left, y), line, font=font, fill=TEXT_COLOR + (255,))
        y += line_height

    return box


def render_source_caption(source_name: str, width: int, height: int) -> Image.Image:
    """Small, unobtrusive source-attribution tag shown in a corner for the
    whole video (after the intro) - crediting where the story comes from so
    the channel's facts read as sourced instead of just asserted."""
    font_size = max(14, height // 45)
    font = _load_font("DejaVuSans-Bold.ttf", font_size)
    text = f"FUENTE: {source_name.upper()}"

    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    text_box = probe.textbbox((0, 0), text, font=font)
    pad = font_size // 2
    tag_w, tag_h = text_box[2] - text_box[0] + pad * 2, text_box[3] - text_box[1] + pad * 2

    tag = Image.new("RGBA", (tag_w, tag_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tag)
    draw.rounded_rectangle([0, 0, tag_w, tag_h], radius=tag_h // 4, fill=(0, 0, 0, 165))
    draw.text((pad - text_box[0], pad - text_box[1]), text, font=font, fill=(220, 220, 220, 255))
    return tag


def render_fact_card(text: str, width: int, height: int) -> Image.Image:
    """A full-frame card carrying one fact, for scenes with nothing real to show.

    Abstract stories - company transparency, whether AI is dangerous - have no
    photographable subject, so stock footage answers them with skyscrapers and
    office meetings that illustrate nothing. Enough of those and the video
    reads as random images with a voice over them. A card stating the scene's
    own key fact is at least about what is being said, and looks deliberate
    rather than borrowed.

    Deliberately plain: the channel's colours, one accent rule, generous
    margins, text as large as it can be while still fitting."""
    image = Image.new("RGB", (width, height), _BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)

    # These cards are stills, and stills get a slow zoom of up to 1.12x in the
    # video, which shows only the middle ~89% of the frame and crops the rest.
    # At a 10% margin that clipped the last letter of the widest line - checked
    # on a real rendered segment, not assumed. Everything therefore sits inside
    # a margin wide enough to survive the closest the zoom ever gets.
    rule_width = max(6, width // 120)
    margin = int(width * 0.155)
    draw.rectangle([margin, int(height * 0.33), margin + rule_width, int(height * 0.67)], fill=_ACCENT_COLOR)

    text_left = margin + rule_width + int(width * 0.05)
    max_text_width = width - text_left - margin
    # Start large and shrink until the wrapped text fits the middle third; a
    # card exists to be read from a phone, so the text should be as big as the
    # space honestly allows rather than a fixed size that sometimes overflows.
    max_text_height = int(height * 0.30)
    size = int(height * 0.075)
    while size > 12:
        font = _load_font("DejaVuSans-Bold.ttf", size)
        lines = _wrap_text(draw, text.upper(), font, max_text_width)
        line_height = int(size * 1.25)
        # Height is not enough on its own. Wrapping breaks between words, so a
        # single word wider than the column has nowhere to go and simply runs
        # off the edge - which is what happened to "INCUMPLIO" on a short text,
        # where the fitting loop left the font large because three lines fitted
        # the height comfortably. Each line has to measure narrow enough too.
        fits_width = all(_text_width(draw, line, font) <= max_text_width for line in lines)
        fits_height = len(lines) * line_height <= max_text_height and len(lines) <= 5
        if fits_width and fits_height:
            break
        size -= 2

    block_height = len(lines) * line_height
    y = (height - block_height) // 2
    for line in lines:
        draw.text((text_left, y), line, font=font, fill=TEXT_COLOR)
        y += line_height
    return image

# Lo que va debajo del nombre en la careta. Corto a proposito: a este tamaño
# una frase larga no se lee en un movil.
_TAGLINE = "Nuestra historia, en un minuto"


def _fichero_de_fuente() -> str:
    """La ruta del .ttf, que drawtext necesita como fichero y no como nombre.

    PIL encuentra "DejaVuSans-Bold.ttf" por nombre porque busca en las rutas
    del sistema; ffmpeg no, quiere la ruta entera. Se saca de la propia fuente
    que ya carga PIL, asi que ambas usan la misma y no pueden descuadrarse.
    """
    try:
        ruta = getattr(_load_font("DejaVuSans-Bold.ttf", 24), "path", "")
        if ruta and Path(ruta).exists():
            return str(ruta)
    except Exception:
        pass
    for tentativa in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                      "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(tentativa).exists():
            return tentativa
    return ""


def _ffmpeg(orden: list[str]) -> None:
    resultado = subprocess.run(orden, capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(f"ffmpeg fallo montando la careta: {resultado.stderr[-400:]}")


def generar_careta(out_path: Path, width: int, height: int, duracion: float) -> Path:
    """La careta del canal, en movimiento. Sustituye a la tarjeta quieta.

    Lo que ella dijo del logo en medio de la pantalla: "tiene que ser
    profesional, no un logo en la mitad". Asi que no hay logo. Hay tipografia,
    que es lo que hacen las caretas seriaspor una razon - se lee en un movil a
    tamaño miniatura, y no envejece.

    Tres tiempos en dos segundos y medio:

      - una regla roja que se abre desde el centro,
      - el nombre, que aparece por debajo de ella,
      - y la linea de abajo, mas tarde y mas pequeña.

    Se hace con ffmpeg y drawtext, sin dependencias nuevas y sin navegador,
    que es lo que descartaba Remotion aqui. Y va en 9:16 igual que en 16:9
    porque todo se mide contra el ancho.
    """
    fuente = _fichero_de_fuente()
    alto_nombre = int(width * (0.075 if height > width else 0.055))
    alto_linea = int(alto_nombre * 0.30)
    grosor = max(2, int(height * 0.004))
    medio_y = int(height * 0.47)

    fondo = "0x%02x%02x%02x" % _BACKGROUND_COLOR
    rojo = "0x%02x%02x%02x" % _ACCENT_COLOR
    crema = "0x%02x%02x%02x" % TEXT_COLOR

    # La regla se abre desde el centro: media anchura a cada lado, con un
    # arranque rapido que frena al final, que es lo que hace que parezca
    # dibujada y no estirada.
    mitad = f"min(1,(t/0.45))*({int(width * 0.16)})"
    regla = (f"drawbox=x='{width // 2}-({mitad})':y={medio_y}:"
             f"w='2*({mitad})':h={grosor}:color={rojo}@1:t=fill")

    # El nombre entra cuando la regla ya esta puesta, subiendo unos pixeles.
    sube = f"{medio_y + int(height * 0.055)}-min(1,max(0,(t-0.40)/0.5))*{int(height * 0.015)}"
    nombre = (f"drawtext=fontfile='{fuente}':text='{CHANNEL_NAME.upper()}':"
              f"fontsize={alto_nombre}:fontcolor={crema}:alpha='min(1,max(0,(t-0.40)/0.45))':"
              f"x=(w-text_w)/2:y='{sube}'")

    # Y la linea de abajo, la ultima y la mas discreta.
    pie = (f"drawtext=fontfile='{fuente}':text='{_TAGLINE}':"
           f"fontsize={alto_linea}:fontcolor={crema}:alpha='0.62*min(1,max(0,(t-0.95)/0.5))':"
           f"x=(w-text_w)/2:y={medio_y + int(height * 0.075) + alto_nombre}")

    # Funde a negro al final para empalmar con lo que venga detras.
    fundido = f"fade=t=in:st=0:d=0.25,fade=t=out:st={max(0.0, duracion - 0.4):.2f}:d=0.4"

    _ffmpeg([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c={fondo}:s={width}x{height}:r=30",
        "-t", f"{duracion:.3f}",
        "-vf", f"{regla},{nombre},{pie},{fundido},format=yuv420p",
        "-pix_fmt", "yuv420p",
        str(out_path),
    ])
    return out_path


# LA CARETA DEL SHORT, A MITAD DEL VIDEO.
#
# Ella: "quiero que durante el video, no al principio, pero igual si al
# segundo diez, en todos haga una intro de la marca España Contada y el nombre
# de la historia". Es lo de las series: primero te enganchan y luego sale el
# titulo. Al principio no, porque los primeros segundos de un Short deciden si
# se quedan, y gastarlos en el nombre del canal es gastarlos en algo que
# todavia no les importa.
#
# Va dibujada fotograma a fotograma y no con drawtext porque lleva a Anselmo
# asomando por abajo y saludando, igual que en el banner del canal: el
# personaje es la marca tanto como el nombre.
# 4 segundos y no 2,4: con 2,4 el titulo se veia entero poco mas de un
# segundo, y ella lo dijo viendo el #98: "no da tiempo a leer el titulo".
DURACION_CARETA_SHORT = 4.0
_FPS_CARETA = 15


def _suave(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t*t*(3 - 2*t)


def _mezcla_color(a, b, t):
    return tuple(int(x + (y - x)*t) for x, y in zip(a, b))


def _titulo_en_lineas(draw, texto, ancho_max, tam_inicial):
    tam = tam_inicial
    while tam > 24:
        fuente = _load_font("DejaVuSans-Bold.ttf", tam)
        lineas = _wrap_text(draw, texto, fuente, ancho_max)
        if len(lineas) <= 3:
            return fuente, lineas
        tam = int(tam*0.88)
    fuente = _load_font("DejaVuSans-Bold.ttf", tam)
    return fuente, _wrap_text(draw, texto, fuente, ancho_max)[:3]


def careta_short(out_path: Path, width: int, height: int, titulo: str,
                 duracion: float = DURACION_CARETA_SHORT) -> Path:
    """La careta del Short: la regla roja que se abre, ESPAÑA CONTADA, el
    nombre de la historia y Anselmo saludando desde abajo. Con campana."""
    import random
    import re
    import shutil
    from . import monigotes, sonidos

    titulo = re.sub(r"\s*\(.*?\)\s*", " ", titulo or "").strip().upper()
    carpeta = Path(out_path).with_suffix("")
    carpeta.mkdir(parents=True, exist_ok=True)
    medio_y = int(height*0.36)
    grosor = max(4, int(height*0.004))
    nombre_f = _load_font("DejaVuSans-Bold.ttf", int(width*0.085))
    pie_f = _load_font("DejaVuSans-Bold.ttf", int(width*0.032))
    total = max(2, int(duracion*_FPS_CARETA))

    for n in range(total):
        t = n/_FPS_CARETA
        img = Image.new("RGB", (width, height), _BACKGROUND_COLOR)
        d = ImageDraw.Draw(img)

        # La regla se abre desde el centro.
        mitad = width*0.34*_suave(t/0.45)
        d.rectangle([width/2 - mitad, medio_y, width/2 + mitad, medio_y + grosor],
                    fill=_ACCENT_COLOR)

        # El nombre del canal entra por encima, subiendo un poco.
        a = _suave((t - 0.30)/0.40)
        texto = CHANNEL_NAME.upper()
        caja = d.textbbox((0, 0), texto, font=nombre_f)
        d.text(((width - (caja[2]-caja[0]))/2, medio_y - (caja[3]-caja[1]) - height*0.03 + (1-a)*18),
               texto, font=nombre_f, fill=_mezcla_color(_BACKGROUND_COLOR, TEXT_COLOR, a))

        # Y el nombre de la historia, debajo y mas grande: es lo que se lee.
        if titulo:
            b = _suave((t - 0.65)/0.40)
            fuente, lineas = _titulo_en_lineas(d, titulo, int(width*0.84), int(width*0.095))
            alto_linea = fuente.size*1.18
            y = medio_y + height*0.04 + (1-b)*18
            for linea in lineas:
                w_l = _text_width(d, linea, fuente)
                d.text(((width - w_l)/2, y), linea, font=fuente,
                       fill=_mezcla_color(_BACKGROUND_COLOR, _ACCENT_COLOR, b))
                y += alto_linea
            pie = "UNA HISTORIA DE"
            w_p = _text_width(d, pie, pie_f)
            d.text(((width - w_p)/2, medio_y - height*0.135 + (1-a)*18), pie, font=pie_f,
                   fill=_mezcla_color(_BACKGROUND_COLOR, (170, 160, 146), a*0.9))

        # Anselmo sube desde abajo y saluda, como en el banner del canal.
        sube = _suave((t - 0.15)/0.5)
        alto_f = height*0.40
        suelo = height*1.10 + (1 - sube)*height*0.25
        # Saludar es la mano en alto yendo de lado a lado. Mezclando "brazos
        # arriba" con "señala" parecia que señalaba el titulo.
        base = monigotes._POSES["de_pie"]
        vaiven = math.sin(2*math.pi*t/0.55)
        pose = {"cuello": base["cuello"], "cadera": base["cadera"], "piernas": base["piernas"],
                "brazos": [base["brazos"][0],
                           [(0, -.66), (.20, -.84), (.22 + .13*vaiven, -1.03)]]}
        monigotes.figura(d, width*0.70, suelo, alto_f, random.Random(n//3), "de_pie",
                         "contento", pose_mezclada=pose, espejo=True,
                         tinta=monigotes.TINTA_CLARA, relleno=(107, 90, 70),
                         rasgos=monigotes.REPARTO.get("cronista"))

        # Funde al final para volver a la historia sin tiron.
        if t > duracion - 0.25:
            oscuro = Image.new("RGB", (width, height), _BACKGROUND_COLOR)
            img = Image.blend(img, oscuro, _suave((t - (duracion - 0.25))/0.25))
        img.save(carpeta/f"{n:04d}.png")

    campana = carpeta/"campana.wav"
    sonido = sonidos.pista([("campana", 0.05, 1.8)], duracion, campana, volumen=0.30)
    orden = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(_FPS_CARETA),
             "-i", str(carpeta/"%04d.png")]
    orden += (["-i", str(sonido)] if sonido else
              ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])
    orden += ["-t", f"{duracion:.3f}", "-map", "0:v", "-map", "1:a",
              "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-r", "30",
              "-c:a", "aac", "-ar", "44100", "-ac", "2", str(out_path)]
    _ffmpeg(orden)
    shutil.rmtree(carpeta, ignore_errors=True)
    return Path(out_path)
