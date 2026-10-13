"""LA FICHA DE REPASO de los Shorts de España Contada.

Quien nos ve en TikTok son estudiantes ("llevo seis horas estudiando esto y
ahora me sale este video"; "lo estamos viendo en clase"). Al final de cada
historia, antes del cierre de Anselmo, sale una hoja de cuaderno con lo que
cae en el examen - cuando, quien, que paso y por que importa - y el
narrador lo lee. Esta hecha para hacerle captura.

Los puntos los saca la traduccion del guion ("repaso" en el JSON) o, si el
guion trae una seccion REPASO al final, son esos tal cual.
"""
from __future__ import annotations

import logging
import math
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

_FUENTE_MANO = Path(__file__).parent / "data" / "fuentes" / "ArchitectsDaughter.woff"
_PAPEL = (252, 249, 240)
_RAYA = (170, 200, 235)
_MARGEN = (230, 120, 120)
_TINTA = (34, 38, 70)
_ROJO = (214, 52, 52)
_FPS = 25
MAX_PUNTOS = 5
# Mas palabras que esto y el narrador no lee la ficha entera, solo las fechas.
_MAX_PALABRAS_VOZ = 32

# "REPASO:", "REPASO FINAL", "RESUMEN PARA EL EXAMEN"... (ella escribio
# "REPASO FINAL" y con la cabecera solo de "REPASO" se habria narrado como
# una escena mas)
_CABECERA = re.compile(r"^\s*[*#-]*\s*(?:REPASO|RESUMEN|PARA EL EXAMEN|FICHA)\b[^\n«»:]{0,25}:?\s*$", re.I)


def separa(texto: str) -> tuple[str, list[dict]]:
    """El guion sin su seccion REPASO (si la trae) y sus puntos. Cada linea
    de debajo de "REPASO:" es un punto."""
    lineas = texto.splitlines()
    for i, linea in enumerate(lineas):
        if _CABECERA.match(linea):
            puntos = []
            for l in lineas[i + 1:]:
                l = l.strip().lstrip("-•*·").strip()
                if l:
                    puntos.append({"texto": l, "voz": _a_voz(l)})
            return "\n".join(lineas[:i]).rstrip(), limpia(puntos)
    return texto, []


_CORRIENTES = {"se", "comienza", "empieza", "muere", "nace", "desaparece", "reinado", "llega", "termina", "acaba",
               "fin", "inicio", "la", "el", "los", "las", "un", "una", "primer", "primera", "nueva", "nuevo",
               "guerra", "batalla", "proclamación", "expulsión", "boda", "regencia", "golpe", "abdica", "firma",
               "gana", "pierde", "conquista", "funda", "crea", "aprueba", "vuelve", "sube", "cae"}


def _a_voz(texto: str) -> str:
    """Como se lee: "1843-1868 · Reinado de Isabel II" -> "De 1843 a 1868,
    reinado de Isabel II"."""
    t = texto.strip()
    m = re.match(r"^(\d{3,4})(?:\s*[-–]\s*(\d{2,4}))?\s*[·|:,.-]\s*(.+)$", t)
    if m:
        resto = m.group(3)
        # "En 912, se proclama..." pero "En 912, Abderramán III...": solo se
        # pasa a minuscula si empieza por una palabra corriente, no un nombre
        if resto.split(" ", 1)[0].lower() in _CORRIENTES:
            resto = resto[:1].lower() + resto[1:]
        t = (f"De {m.group(1)} a {m.group(2)}, " if m.group(2) else f"En {m.group(1)}, ") + resto
    else:
        t = re.sub(r"\s*[·|:]\s*", ", ", t, count=1)
    return t.rstrip(".") + "."


def limpia(puntos) -> list[dict]:
    """De lo que venga (la traduccion o el guion) a [{"texto", "voz"}],
    3-4 como mucho; menos de 2 no es una ficha."""
    salida = []
    for p in puntos or []:
        if isinstance(p, str):
            p = {"texto": p}
        if not isinstance(p, dict):
            continue
        texto = " ".join(str(p.get("texto") or "").split()).rstrip(".")
        if len(texto) > 90:
            texto = texto[:90].rsplit(" ", 1)[0]
        if not texto:
            continue
        voz = " ".join(str(p.get("voz") or "").split()) or _a_voz(texto)
        salida.append({"texto": texto, "voz": voz})
    salida = salida[:MAX_PUNTOS]
    return salida if len(salida) >= 2 else []


def escena(puntos: list[dict]) -> dict | None:
    """La escena que se añade al final del Short (antes del cierre)."""
    puntos = limpia(puntos)
    if not puntos:
        return None
    voz = "Para el examen. " + " ".join(p["voz"].rstrip(".") + "." for p in puntos)
    compacto = False
    if len(voz.split()) > _MAX_PALABRAS_VOZ:
        # LA FICHA LARGA NO SE LEE ENTERA: la de Abderramán duraba 25 s y el
        # Short se fue a casi 3 minutos. Se dicen solo las fechas y la ficha
        # se va rellenando en pantalla (se hace captura, no hace falta oirla).
        fechas = [m.group(1) for m in (re.match(r"^\s*(\d{3,4})", p_["texto"]) for p_ in puntos) if m]
        if len(fechas) >= 2:
            lista = ", ".join(fechas[:-1]) + " y " + fechas[-1]
            voz = f"Para el examen, apúntate estas fechas: {lista}."
        else:
            voz = "Para el examen, haz captura de esto: es lo que tienes que saberte."
        compacto = True
    return {"narration": voz, "visual_keywords": "", "photo_subject": "", "photo_subject_role": "",
            "ai_image_prompt": "", "on_screen_highlight": "", "is_repaso": True, "repaso": puntos,
            "repaso_compacto": compacto}


def _fuente(px: int, mano: bool = True):
    if mano:
        try:
            return ImageFont.truetype(str(_FUENTE_MANO), max(10, int(px)))
        except OSError:
            pass
    for f in ("DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, max(10, int(px)))
        except OSError:
            continue
    return ImageFont.load_default()


def _parte(texto: str, fuente, ancho: float) -> list[str]:
    palabras, lineas, actual = texto.split(), [], ""
    for p in palabras:
        prueba = (actual + " " + p).strip()
        if fuente.getlength(prueba) <= ancho or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = p
    if actual:
        lineas.append(actual)
    return lineas


def _momentos(puntos: list[dict], segundos: float, compacto: bool = False) -> list[float]:
    """Cuando sale cada punto: cuando el narrador empieza a decirlo (la voz
    va a ritmo parejo, asi que se reparte por letras). En la ficha compacta
    (solo se dicen las fechas), repartidos y todos fuera antes del final."""
    if compacto:
        hueco = max(0.3, (segundos*0.8 - 0.6)/max(1, len(puntos)))
        return [0.6 + k*hueco for k in range(len(puntos))]
    cab = len("Para el examen. ")
    largos = [len(p["voz"]) + 1 for p in puntos]
    total = cab + sum(largos)
    habla = max(1.0, segundos - 0.4)
    t, salida = cab/total*habla, []
    for n in largos:
        salida.append(max(0.4, t - 0.15))
        t += n/total*habla
    return salida


def _fotograma(puntos, tema, t, momentos, w, h):
    img = Image.new("RGB", (w, h), _PAPEL)
    d = ImageDraw.Draw(img)
    # el cuaderno: rayas azules y el margen rojo
    paso = int(h*0.045)
    for y in range(int(h*0.16), int(h*0.98), paso):
        d.line([(0, y), (w, y)], fill=_RAYA, width=2)
    d.line([(int(w*0.12), 0), (int(w*0.12), h)], fill=_MARGEN, width=4)
    # agujeros de anilla
    for y in (0.2, 0.5, 0.8):
        r = w*0.022
        d.ellipse([w*0.045 - r, h*y - r, w*0.045 + r, h*y + r], fill=(225, 220, 208))
    # el titulo, subrayado a rotulador
    entra = min(1.0, t/0.35)
    titulo = "PARA EL EXAMEN"
    px = int(h*0.06)
    f_tit = _fuente(px)
    while f_tit.getlength(titulo) > w*0.8 and px > 20:
        px -= 2
        f_tit = _fuente(px)
    tw = f_tit.getlength(titulo)
    x0 = w*0.16
    d.text((x0, h*0.05), titulo, font=f_tit, fill=_ROJO)
    d.line([(x0, h*0.05 + h*0.075), (x0 + tw*entra, h*0.05 + h*0.075 + 4)], fill=_ROJO, width=8)
    arriba = h*0.25
    if tema:
        f_tema = _fuente(int(h*0.028))
        lineas_tema = _parte(tema.upper(), f_tema, w*0.8)
        if len(lineas_tema) > 2:
            lineas_tema = lineas_tema[:2]
            lineas_tema[1] = lineas_tema[1].rstrip(" .,:") + "…"
        for k, linea in enumerate(lineas_tema):
            d.text((x0, h*0.14 + k*h*0.034), linea, font=f_tema, fill=(90, 90, 110))
        arriba = max(arriba, h*0.14 + len(lineas_tema)*h*0.034 + h*0.03)
    # los puntos, de uno en uno, con su "check"
    px = int(h*0.033)
    while px > int(h*0.022):
        f_p = _fuente(px)
        lineas_total = sum(len(_parte(p["texto"], f_p, w*0.72)) for p in puntos)
        if arriba + lineas_total*px*1.24 + len(puntos)*h*0.02 <= h*0.635:
            break
        px -= 2
    f_p = _fuente(px)
    salto = px*1.24
    y = arriba
    for p, desde in zip(puntos, momentos):
        lineas = _parte(p["texto"], f_p, w*0.72)
        alto_p = len(lineas)*salto + h*0.02
        if t >= desde:
            k = min(1.0, (t - desde)/0.25)
            # la marca de check que se dibuja
            cx, cy = w*0.19, y + h*0.022
            s = w*0.03
            d.line([(cx - s, cy), (cx - s*0.3, cy + s*0.7)], fill=(40, 160, 80), width=7)
            if k > 0.5:
                d.line([(cx - s*0.3, cy + s*0.7), (cx - s*0.3 + (s*1.6)*(k - 0.5)*2, cy + s*0.7 - s*1.9*(k - 0.5)*2)],
                       fill=(40, 160, 80), width=7)
            fecha = re.match(r"^\s*(\d{3,4}(?:\s*[-–]\s*\d{2,4})?\s*[·|:]?)", p["texto"])
            fecha = fecha.group(1) if fecha else ""
            for j, linea in enumerate(lineas):
                # se escribe de izquierda a derecha; la fecha, en rojo
                visible = linea[:max(1, int(len(linea)*min(1.0, (t - desde)/0.45)))]
                x = w*0.25
                if j == 0 and fecha and visible.startswith(fecha.strip()[:1]):
                    roja = visible[:len(fecha)]
                    d.text((x, y), roja, font=f_p, fill=_ROJO)
                    x += f_p.getlength(roja)
                    visible = visible[len(fecha):]
                d.text((x, y + j*salto), visible, font=f_p, fill=_TINTA)
        y += alto_p
    # el aviso de captura, cuando ya estan todos
    if momentos and t > momentos[-1] + 0.6:
        f_ok = _fuente(int(h*0.028), mano=False)
        aviso = "📌 GUÁRDALO PARA REPASAR"
        aviso = aviso.replace("📌 ", "")
        ancho = f_ok.getlength(aviso) + w*0.06
        bx, by = (w - ancho)/2, min(h*0.655, y + h*0.008)
        pulso = 1 + 0.03*math.sin(t*6)
        d.rounded_rectangle([bx, by, bx + ancho*pulso, by + h*0.05], radius=int(h*0.02), fill=(255, 214, 60),
                            outline=_TINTA, width=3)
        d.text((bx + w*0.03, by + h*0.01), aviso, font=f_ok, fill=_TINTA)
    return img


def render(puntos: list[dict], out_path: Path, ancho: int, alto: int, segundos: float,
           tema: str = "", compacto: bool = False) -> Path | None:
    """El clip de la ficha. None si algo falla (el Short sale sin ella)."""
    try:
        puntos = limpia(puntos)
        if not puntos:
            return None
        segundos = max(2.0, min(30.0, float(segundos)))
        momentos = _momentos(puntos, segundos, compacto)
        total = int(segundos*_FPS)
        proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                 "-s", f"{ancho}x{alto}", "-r", str(_FPS), "-i", "-", "-c:v", "libx264",
                                 "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out_path)],
                                stdin=subprocess.PIPE)
        ultimo = None
        for n in range(total):
            img = _fotograma(puntos, tema, n/_FPS, momentos, ancho, alto)
            proc.stdin.write(img.tobytes())
            ultimo = img
        proc.stdin.close()
        if proc.wait() != 0:
            return None
        if ultimo is not None:
            ultimo.save(Path(out_path).with_suffix(".jpg"), quality=90)
        return Path(out_path)
    except Exception:
        logger.warning("La ficha de repaso no ha salido; el Short sigue sin ella.", exc_info=True)
        return None
