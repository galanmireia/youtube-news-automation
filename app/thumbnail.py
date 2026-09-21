import logging
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageStat

from . import caras

# Fractions of the video to consider for the thumbnail still. All well past
# the intro card: sampling near the start meant every thumbnail was just the
# channel logo instead of anything from the story itself.
_CANDIDATE_POSITIONS = (0.25, 0.40, 0.55, 0.70)

logger = logging.getLogger(__name__)


def _extract_frame(video_path: Path, out_path: Path, timestamp: float) -> Path | None:
    result = subprocess.run(
        ["ffmpeg", "-y", "-ss", str(timestamp), "-i", str(video_path), "-frames:v", "1", str(out_path)],
        capture_output=True,
    )
    return out_path if result.returncode == 0 and out_path.exists() else None


def _video_duration(video_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ],
        capture_output=True,
    )
    try:
        return float(result.stdout.decode().strip())
    except ValueError:
        return 0.0


def _pick_frame(video_path: Path, work_path: Path) -> Path:
    """Picks the most visually interesting of several candidate stills rather
    than always grabbing the same timestamp: a shot that happens to be a
    near-black or near-empty frame makes a dead thumbnail. Standard deviation
    across the image is a decent stand-in for "has some contrast and detail"."""
    duration = _video_duration(video_path)
    best_path, best_score = None, -1.0
    for index, position in enumerate(_CANDIDATE_POSITIONS):
        candidate = work_path.with_suffix(f".cand{index}.jpg")
        timestamp = duration * position if duration else 1.0
        if _extract_frame(video_path, candidate, timestamp) is None:
            continue
        with Image.open(candidate) as image:
            score = sum(ImageStat.Stat(image.convert("RGB")).stddev) / 3
        if score > best_score:
            if best_path is not None:
                best_path.unlink(missing_ok=True)
            best_path, best_score = candidate, score
        else:
            candidate.unlink(missing_ok=True)

    if best_path is None:
        fallback = work_path.with_suffix(".cand.jpg")
        if _extract_frame(video_path, fallback, 1.0) is None:
            raise RuntimeError(f"No se pudo extraer ningun fotograma de {video_path}")
        return fallback
    return best_path


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _wrap_to_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and draw.textbbox((0, 0), candidate, font=font)[2] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _fit_title(draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int, max_lines: int):
    """Shrinks the title until it actually fits the frame. The previous code
    estimated how many characters fit from the font size, which is only a
    guess - real titles ran off the right edge, cut mid-word."""
    size = start_size
    while size > 20:
        font = _load_font(size)
        lines = _wrap_to_width(draw, text, font, max_width)
        if len(lines) <= max_lines and all(draw.textbbox((0, 0), l, font=font)[2] <= max_width for l in lines):
            return font, lines
        size -= 2
    font = _load_font(20)
    return font, _wrap_to_width(draw, text, font, max_width)[:max_lines]


def _cover(image: Image.Image, width: int, height: int) -> Image.Image:
    """Fills the frame without distorting it.

    The previous version resized straight to the target, which for a vertical
    Short turned into a horizontal thumbnail meant squashing 9:16 into 16:9 -
    the ship got fat and the illustration bent. Scaling to cover and cropping
    the overflow keeps everything the shape it was drawn."""
    origen_w, origen_h = image.size
    escala = max(width / origen_w, height / origen_h)
    nuevo = image.resize((max(1, round(origen_w * escala)), max(1, round(origen_h * escala))))
    izquierda = (nuevo.width - width) // 2
    # Cropped from the upper third rather than the centre: the lower part of a
    # frame is where this pipeline puts its own name bars and caption boxes.
    # Cuanto mas vertical es el original, mas arriba se recorta. Una foto de
    # retrato lleva la cara en la mitad de arriba, y recortando por el tercio
    # la cara caia justo donde luego va el texto: se leia el titulo y se comia
    # la barbilla. Un quinto la sube lo suficiente para que el texto quede
    # sobre los hombros, que es donde no molesta.
    sobra = max(0, nuevo.height - height)
    divisor = 5 if origen_h > origen_w * 1.2 else 3
    arriba = min(sobra // divisor, sobra)
    return nuevo.crop((izquierda, arriba, izquierda + width, arriba + height))


def _thumbnail_text(title: str) -> str:
    """The part of the title worth putting on the picture.

    A full headline set large enough to read at listing size needs three lines
    and buries the image. Titles here are built as "Subject: the hook", so the
    hook alone is both the shorter half and the interesting one; failing that,
    the first few words."""
    texto = title.strip()
    for separador in (": ", " - ", " | ", "? ", "; "):
        if separador in texto:
            cabeza, _, cola = texto.partition(separador)
            # Keep whichever half actually says something, preferring the hook.
            texto = cola if len(cola.split()) >= 3 else cabeza
            break
    palabras = texto.split()
    if len(palabras) > 7:
        texto = " ".join(palabras[:7])
    return texto.upper().rstrip(" ,.;:")


def _la_cara_que_mas_sale(retratos: list[Path] | None) -> Path | None:
    """La protagonista del video, que es la que tiene que ir en la portada.

    Aqui estaba el fallo de fondo, y no era de dibujo sino de eleccion: la
    miniatura se sacaba del video eligiendo el fotograma con MAS CONTRASTE
    (la desviacion tipica de la imagen), y eso puntua altisimo un camino de
    bosque lleno de hojas y bajisimo una cara sobre fondo liso. O sea que
    elegia textura justo cuando lo que hace clicar en un caso de sucesos es
    una persona mirandote.

    La lista llega con repeticiones a proposito - una entrada por cada vez que
    esa foto se uso - asi que la mas repetida es la que mas sale en el video.
    """
    if not retratos:
        return None
    veces: dict[str, int] = {}
    for ruta in retratos:
        veces[str(ruta)] = veces.get(str(ruta), 0) + 1
    for ruta, _ in sorted(veces.items(), key=lambda par: -par[1]):
        camino = Path(ruta)
        if camino.exists() and camino.stat().st_size > 0:
            return camino
    return None


def _con_fuerza(imagen: Image.Image) -> Image.Image:
    """Mas contraste y un poco mas de color. Una miniatura apagada no se ve.

    Se mira a tamaño de sello en un movil, compitiendo con veinte mas. Lo que
    en pantalla grande parece exagerado, ahi es lo justo.
    """
    imagen = ImageEnhance.Contrast(imagen).enhance(1.18)
    imagen = ImageEnhance.Color(imagen).enhance(1.12)
    return ImageEnhance.Brightness(imagen).enhance(1.04)


def _sombra_abajo(imagen: Image.Image, alto_banda: int) -> Image.Image:
    """Un degradado negro por abajo, en vez de la caja negra de antes.

    La caja opaca tapaba un tercio de la foto y se veia el corte recto, que es
    lo que hace que una miniatura parezca una plantilla. Un degradado oscurece
    lo justo para que el texto se lea y deja que la imagen siga.
    """
    ancho, alto = imagen.size
    degradado = Image.new("L", (1, alto), 0)
    for y in range(alto):
        desde = alto - alto_banda
        if y <= desde:
            valor = 0
        else:
            avance = (y - desde) / max(1, alto_banda)
            valor = int(235 * (avance ** 1.5))
        degradado.putpixel((0, y), valor)
    mascara = degradado.resize((ancho, alto))
    negro = Image.new("RGB", imagen.size, (0, 0, 0))
    return Image.composite(negro, imagen, mascara)



# ----------------------------------------------- la miniatura con cara
#
# La primera version fue una bronca merecida: "me estas poniendo una puta foto
# normal y corriente en vez de generar una miniatura entera". Y tenia razon -
# era su foto con un rotulo encima, que es lo que hace cualquiera en treinta
# segundos.
#
# Una miniatura que funciona hace tres cosas, y ninguna se puede hacer sin
# saber DONDE esta la cara:
#
#   1. La cara grande. Ocupando casi la mitad del alto, no perdida en un plano
#      general. Se mira a tamaño de sello: una cara pequeña no es una cara, es
#      una mancha.
#   2. La cara SEPARADA del fondo. Un fondo nitido compite con ella; borroso y
#      oscuro, la empuja hacia delante.
#   3. El texto DONDE NO LA TAPA. Antes el titulo caia sobre la barbilla
#      porque se ponia siempre abajo, mirase quien mirase.
_CARA_DEL_ALTO = 0.46      # cuanto del alto ocupa la cara
_CARA_ALTURA_OJOS = 0.40   # a que altura queda su centro
_DESENFOQUE = 14


def _encuadrar_en_la_cara(ruta: Path, width: int, height: int) -> Image.Image | None:
    """Recorta la foto para que la cara salga grande y a un lado.

    A un lado y no en el centro porque el otro lado es donde va el texto. Con
    la cara centrada solo quedan las esquinas, y ahi no cabe nada que se lea.
    """
    caja = caras.la_cara(ruta)
    if caja is None:
        return None
    x, y, ancho_cara, alto_cara = caja
    origen = Image.open(ruta).convert("RGB")

    escala = (height * _CARA_DEL_ALTO) / max(1, alto_cara)
    nuevo = origen.resize((max(1, round(origen.width * escala)),
                           max(1, round(origen.height * escala))), Image.LANCZOS)
    centro_x = (x + ancho_cara / 2) * escala
    centro_y = (y + alto_cara / 2) * escala

    # La cara a la DERECHA y el texto a la izquierda: se lee de izquierda a
    # derecha, asi que el ojo entra por el texto y acaba en la cara.
    izquierda = int(centro_x - width * 0.66)
    arriba = int(centro_y - height * _CARA_ALTURA_OJOS)

    # Si el recorte se sale, se rellena con el propio fondo estirado en vez de
    # con negro: un borde negro delata el apaño enseguida.
    relleno = _cover(origen, width, height).filter(ImageFilter.GaussianBlur(_DESENFOQUE * 2))
    lienzo = relleno.copy()
    lienzo.paste(nuevo, (-izquierda, -arriba))
    return lienzo


def _separar_del_fondo(imagen: Image.Image, width: int, height: int) -> Image.Image:
    """Nitido donde esta el sujeto, borroso y oscuro en el resto.

    No es un recorte de verdad - para eso haria falta un modelo de segmentacion
    y varios cientos de megas - pero hace el mismo trabajo: manda la mirada a
    la cara. Y al ser un degradado no tiene bordes recortados, que es lo que
    hace que un recorte mal hecho cante mas que no recortar.
    """
    fondo = imagen.filter(ImageFilter.GaussianBlur(_DESENFOQUE))
    fondo = ImageEnhance.Brightness(fondo).enhance(0.55)
    fondo = ImageEnhance.Color(fondo).enhance(0.55)

    mascara = Image.new("L", (width, height), 0)
    pincel = ImageDraw.Draw(mascara)
    cx, cy = int(width * 0.66), int(height * _CARA_ALTURA_OJOS)
    rx, ry = int(width * 0.34), int(height * 0.62)
    pincel.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
    mascara = mascara.filter(ImageFilter.GaussianBlur(int(width * 0.06)))
    return Image.composite(imagen, fondo, mascara)

def generate_thumbnail(video_path: Path, title: str, out_path: Path, width: int, height: int,
                       retratos: list[Path] | None = None) -> Path:
    # Primero la cara. Solo si no hay ninguna se vuelve al fotograma del video.
    foto = _la_cara_que_mas_sale(retratos)
    frame_path = None
    con_cara = False
    if foto is not None:
        encuadrada = _encuadrar_en_la_cara(foto, width, height)
        if encuadrada is not None:
            image = _con_fuerza(_separar_del_fondo(encuadrada, width, height))
            con_cara = True
            logger.info("Miniatura: encuadrada en la cara de %s.", foto.name)
        else:
            image = _con_fuerza(_cover(Image.open(foto).convert("RGB"), width, height))
            logger.info("Miniatura: %s no tiene cara detectable; encuadre normal.", foto.name)
    else:
        frame_path = _pick_frame(video_path, out_path)
        image = _con_fuerza(_cover(Image.open(frame_path).convert("RGB"), width, height))
        logger.info("Miniatura: sin caras en el video, se usa un fotograma.")

    margin = int(width * 0.045)
    # CUATRO PALABRAS, no siete, y mas grandes. Una miniatura se lee en el
    # tiempo que tarda un pulgar en pasar por encima; siete palabras a tamaño
    # pequeño no se leen, se ignoran.
    # Con cara, el texto vive en la mitad izquierda y en tres lineas: es una
    # columna estrecha al lado del sujeto, no una banda cruzandole la cara.
    ancho_texto = int(width * 0.52) if con_cara else width - margin * 2
    font, lines = _fit_title(
        draw=ImageDraw.Draw(image), text=_thumbnail_text(title),
        max_width=ancho_texto - margin,
        start_size=max(48, width // (7 if con_cara else 8)),
        max_lines=3 if con_cara else 2,
    )

    line_height = int(font.size * 1.12)
    if not con_cara:
        image = _sombra_abajo(image, line_height * len(lines) + margin * 3)

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    if con_cara:
        # Centrado en vertical en su columna: al lado de la cara, no debajo.
        y = (height - line_height * len(lines)) // 2
    else:
        y = height - line_height * len(lines) - margin
    for line in lines:
        # Contorno negro: sobre una foto el blanco solo desaparece en cuanto
        # cae encima de algo claro - una camisa, el cielo.
        for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2), (-2, 2), (2, -2)):
            draw.text((margin + dx, y + dy), line, font=font, fill=(0, 0, 0, 230))
        draw.text((margin, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_height

    # La regla roja del canal, corta y encima del texto, como firma.
    regla_y = (((height - line_height * len(lines)) // 2) if con_cara
               else (height - line_height * len(lines) - margin)) - max(10, height // 55)
    draw.rectangle([margin, regla_y, margin + int(width * 0.10), regla_y + max(5, height // 200)],
                   fill=(196, 30, 42, 255))

    combined = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    combined.save(out_path, quality=92)
    if frame_path is not None:
        frame_path.unlink(missing_ok=True)
    return out_path
