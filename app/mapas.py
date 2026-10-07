"""MAPAS DE VERDAD para los videos largos.

Un video de una hora sobre Lepanto cuenta donde estaba Chipre, de donde salio
la flota y hacia donde fue. Eso con monigotes no se entiende: hace falta ver
el Mediterraneo. Las costas son las de Natural Earth (dominio publico, via el
paquete world-atlas a escala 1:50 millones), guardadas ya convertidas en
app/data/costas.json - una lista de poligonos [[lon, lat], ...].

El guion pide el mapa con los sitios por su nombre y sus coordenadas, y el
encuadre sale solo de los sitios: el guion no tiene que saber de zooms.
"""
import json
import math
import random
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

_COSTAS = Path(__file__).parent / "data" / "costas.json"
_FUENTE = "DejaVuSans-Bold.ttf"

MAR = (163, 190, 204)
MAR_OSCURO = (134, 164, 182)
TIERRA = (232, 216, 178)
TINTA = (52, 40, 30)
PAPEL = (240, 230, 206)
COLORES = {
    "rojo": (186, 30, 36),
    "azul": (36, 74, 150),
    "verde": (34, 120, 66),
    "negro": (30, 26, 22),
    "oro": (196, 140, 20),
}


@lru_cache(maxsize=1)
def _poligonos():
    return json.loads(_COSTAS.read_text())


def _fuente(px):
    try:
        return ImageFont.truetype(_FUENTE, int(px))
    except OSError:
        return ImageFont.load_default()


def _encuadre(puntos, ancho, alto):
    """El trozo de mundo que se ve: todos los sitios con aire alrededor, nunca
    menos de 8 grados de alto (un mapa de dos ciudades vecinas no se
    entiende), y con la proporcion de la pantalla."""
    lats = [p[0] for p in puntos] or [40.0]
    lons = [p[1] for p in puntos] or [-3.7]
    lat0 = (max(lats) + min(lats))/2
    lon0 = (max(lons) + min(lons))/2
    k = math.cos(math.radians(lat0))           # un grado de longitud es mas corto
    alto_g = max((max(lats) - min(lats))*1.6, 8.0)
    ancho_g = max((max(lons) - min(lons))*k*1.45, 8.0*ancho/alto)
    if ancho_g/alto_g < ancho/alto:
        ancho_g = alto_g*ancho/alto
    else:
        alto_g = ancho_g*alto/ancho
    return lat0, lon0, k, alto_g, ancho_g


def _proyecta(lat, lon, caja, ancho, alto):
    lat0, lon0, k, alto_g, ancho_g = caja
    x = ancho/2 + (lon - lon0)*k/ancho_g*ancho
    y = alto/2 - (lat - lat0)/alto_g*alto
    return x, y


def _texto_con_halo(d, xy, texto, fuente, color, halo=PAPEL, ancla="mm", grosor=None):
    grosor = grosor if grosor is not None else max(2, fuente.size//8)
    d.text(xy, texto, font=fuente, fill=color, anchor=ancla, stroke_width=grosor, stroke_fill=halo)


def _flecha(d, a, b, color, grosor, curva=0.18, rayas=True):
    """Una ruta: curva, a trazos y con punta. Recta parecia una linea de
    metro; curva parece un barco que va de un sitio a otro."""
    (x0, y0), (x1, y1) = a, b
    mx, my = (x0 + x1)/2, (y0 + y1)/2
    dx, dy = x1 - x0, y1 - y0
    cx, cy = mx - dy*curva, my + dx*curva
    pts = []
    for i in range(41):
        t = i/40
        pts.append(((1-t)**2*x0 + 2*(1-t)*t*cx + t*t*x1, (1-t)**2*y0 + 2*(1-t)*t*cy + t*t*y1))
    # La punta no llega encima del sitio: se para un poco antes.
    largo = math.hypot(dx, dy) or 1
    corte = max(0, len(pts) - 1 - int(40*min(0.25, grosor*5/largo)))
    tramo = pts[:corte + 1]
    for i in range(len(tramo) - 1):
        if rayas and (i//2) % 2:
            continue
        d.line([tramo[i], tramo[i + 1]], fill=color, width=grosor)
    (px, py), (qx, qy) = tramo[-2], tramo[-1]
    ang = math.atan2(qy - py, qx - px)
    tam = grosor*4.2
    punta = [(qx + math.cos(ang)*tam*0.6, qy + math.sin(ang)*tam*0.6),
             (qx + math.cos(ang + 2.5)*tam, qy + math.sin(ang + 2.5)*tam),
             (qx + math.cos(ang - 2.5)*tam, qy + math.sin(ang - 2.5)*tam)]
    d.polygon(punta, fill=color)


def _batalla(d, x, y, r, g):
    """Dos espadas cruzadas en rojo: aqui hubo una batalla."""
    for lado in (-1, 1):
        d.line([(x - lado*r, y - r), (x + lado*r, y + r)], fill=COLORES["rojo"], width=g)
        d.line([(x - lado*r*0.55 - r*0.28, y - lado*0 - r*0.45),
                (x - lado*r*0.55 + r*0.28, y - r*0.45 + lado*0)], fill=COLORES["rojo"], width=g)
    d.ellipse([x - r*1.5, y - r*1.5, x + r*1.5, y + r*1.5], outline=COLORES["rojo"], width=max(2, g//2))


def mapa(spec: dict, ancho: int = 1920, alto: int = 1080, progreso: float = 1.0) -> Image.Image:
    """Dibuja el mapa. spec:
      titulo:  "EL MEDITERRANEO EN 1571" (opcional)
      lugares: [{"nombre": "Mesina", "lat": 38.19, "lon": 15.55,
                 "tipo": "ciudad" | "batalla" | "capital"}]
      zonas:   [{"nombre": "IMPERIO OTOMANO", "lat": 39, "lon": 32, "color": "verde"}]
      flechas: [{"de": "Mesina", "a": "Lepanto", "color": "rojo"}]
    progreso (0-1) dibuja las flechas a medias: con eso se anima la ruta."""
    lugares = [l for l in spec.get("lugares") or [] if _coord(l)]
    zonas = [z for z in spec.get("zonas") or [] if _coord(z)]
    puntos = [_coord(l) for l in lugares] + [_coord(z) for z in zonas]
    caja = _encuadre(puntos, ancho, alto)

    img = Image.new("RGB", (ancho, alto), MAR)
    d = ImageDraw.Draw(img)
    # Unas lineas de olas suaves en el mar: un mar liso parecia un hueco.
    rnd = random.Random(7)
    for _ in range(90):
        x, y = rnd.uniform(0, ancho), rnd.uniform(0, alto)
        d.arc([x, y, x + ancho*0.018, y + ancho*0.008], 200, 340, fill=MAR_OSCURO, width=2)

    g = max(2, int(alto*0.0035))
    lat0, lon0, k, alto_g, ancho_g = caja
    margen = 4
    for poli in _poligonos():
        lons = [p[0] for p in poli]
        lats = [p[1] for p in poli]
        if (max(lons) < lon0 - ancho_g/k/2 - margen or min(lons) > lon0 + ancho_g/k/2 + margen
                or max(lats) < lat0 - alto_g/2 - margen or min(lats) > lat0 + alto_g/2 + margen):
            continue
        pts = [_proyecta(la, lo, caja, ancho, alto) for lo, la in poli]
        d.polygon(pts, fill=TIERRA, outline=TINTA)
        d.line(pts + [pts[0]], fill=TINTA, width=g, joint="curve")

    # Las zonas (reinos, imperios): letras grandes, separadas y transparentes,
    # como en los mapas antiguos. Van debajo de todo lo demas.
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dc = ImageDraw.Draw(capa)
    for z in zonas:
        x, y = _proyecta(*_coord(z), caja, ancho, alto)
        color = COLORES.get(z.get("color") or "negro", COLORES["negro"])
        texto = " ".join(str(z.get("nombre", "")).upper())
        dc.text((x, y), texto, font=_fuente(alto*0.034), fill=color + (120,), anchor="mm")
    img.paste(capa, (0, 0), capa)
    d = ImageDraw.Draw(img)

    sitio = {str(l.get("nombre", "")).strip().lower(): _proyecta(*_coord(l), caja, ancho, alto)
             for l in lugares}
    flechas = spec.get("flechas") or []
    for n, f in enumerate(flechas):
        a = sitio.get(str(f.get("de", "")).strip().lower())
        b = sitio.get(str(f.get("a", "")).strip().lower())
        if not a or not b:
            continue
        # Con progreso, las flechas salen una detras de otra.
        tramo = min(1.0, max(0.0, progreso*len(flechas) - n))
        if tramo <= 0:
            continue
        fin = (a[0] + (b[0] - a[0])*tramo, a[1] + (b[1] - a[1])*tramo)
        _flecha(d, a, fin, COLORES.get(f.get("color") or "rojo", COLORES["rojo"]),
                max(3, int(alto*0.007)))

    f_lugar = _fuente(alto*0.030)
    for l in lugares:
        x, y = sitio[str(l.get("nombre", "")).strip().lower()]
        tipo = (l.get("tipo") or "ciudad").lower()
        r = alto*0.010
        if tipo == "batalla":
            _batalla(d, x, y, alto*0.016, max(3, int(alto*0.006)))
            dy = alto*0.045
        else:
            if tipo == "capital":
                r *= 1.4
            d.ellipse([x - r*1.6, y - r*1.6, x + r*1.6, y + r*1.6], fill=PAPEL)
            d.ellipse([x - r, y - r, x + r, y + r], fill=TINTA)
            dy = alto*0.032
        _texto_con_halo(d, (x, y - dy), str(l.get("nombre", "")), f_lugar, TINTA)

    titulo = (spec.get("titulo") or "").strip()
    if titulo:
        f_t = _fuente(alto*0.050)
        caja_t = d.textbbox((0, 0), titulo.upper(), font=f_t)
        tw, th = caja_t[2] - caja_t[0], caja_t[3] - caja_t[1]
        x0, y0 = (ancho - tw)/2 - alto*0.04, alto*0.04
        d.rounded_rectangle([x0, y0, x0 + tw + alto*0.08, y0 + th + alto*0.05], radius=int(alto*0.015),
                            fill=PAPEL, outline=TINTA, width=g)
        d.text((ancho/2, y0 + (th + alto*0.05)/2), titulo.upper(), font=f_t, fill=TINTA, anchor="mm")

    # El marco, doble, de mapa antiguo.
    d.rectangle([alto*0.012, alto*0.012, ancho - alto*0.012, alto - alto*0.012], outline=TINTA, width=g*2)
    d.rectangle([alto*0.026, alto*0.026, ancho - alto*0.026, alto - alto*0.026], outline=TINTA, width=g)
    return img.filter(ImageFilter.SMOOTH)


def _coord(sitio):
    try:
        lat, lon = float(sitio.get("lat")), float(sitio.get("lon"))
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon
