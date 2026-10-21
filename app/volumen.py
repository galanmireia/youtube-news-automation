"""EL VOLUMEN de España Contada: monigotes con cuerpo y objetos con sombra.

Ella: "puedes mejorar los personajes y darles un poco de profundidad como en
el otro canal?". El monigote de palos pasa a tener hombros, tronco y cadera,
ropa de su color con un lado en sombra, brazos y piernas gruesos con manos y
zapatos, la cara con brillo y mofletes, y su sombra en el suelo. Las cosas,
lo mismo: un borde en sombra, un brillo y su sombra donde se apoyan.

Va aparte de monigotes.py para no engordarlo mas; monigotes.figura() llama
aqui cuando VOLUMEN esta encendido (Why Though lo apaga mientras dibuja).

TODO lo que se mezcla con transparencia pasa por _funde(): la figura que se
cae se pinta en una capa RGBA transparente, y pegar ahi un recorte en RGB
dejaba un rectangulo negro alrededor.
"""
from __future__ import annotations

import math

from PIL import Image, ImageChops, ImageDraw, ImageFilter

TINTA = (24, 24, 28)
PIEL = (253, 241, 230)

# La ropa de cada uno, la misma en todos los videos: es lo que hace que se
# les reconozca de lejos, como el pelo y la estatura.
ROPA = {
    "Don Severo": ((44, 60, 116), (40, 40, 52)),     # azul marino, el que manda
    "Anselmo":    ((138, 100, 62), (78, 70, 64)),    # marron, el testigo
    "Remedios":   ((148, 70, 124), (60, 50, 60)),    # morado, con falda
    "Perico":     ((64, 150, 84), (70, 92, 150)),    # verde y vaqueros, el pequeño
    "Bruno":      ((182, 58, 56), (48, 52, 70)),     # rojo, el soldado
}
_ROPA_SUELTA = [((88, 112, 160), (52, 54, 66)), ((120, 130, 70), (70, 62, 52)),
                ((96, 84, 140), (50, 48, 60)), ((170, 120, 60), (64, 56, 50))]
# Los que van con falda: las mujeres del reparto y las sueltas con moño.
_FALDA = ("Remedios",)


def _osc(c, k):
    return tuple(int(v*k) for v in c[:3])


def _cla(c, k):
    return tuple(min(255, int(v + (255 - v)*k)) for v in c[:3])


def _suma(a, b, k=1.0):
    return (a[0] + b[0]*k, a[1] + b[1]*k)


def _funde(img, capa, x0, y0):
    """Pega una capa RGBA en (x0, y0) respetando la transparencia, tanto si
    img es RGB (el plano) como RGBA (la capa de la figura que se cae)."""
    x0, y0 = int(x0), int(y0)
    W, H = img.size
    cx0, cy0 = max(0, -x0), max(0, -y0)
    cx1, cy1 = min(capa.width, W - x0), min(capa.height, H - y0)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    if (cx0, cy0, cx1, cy1) != (0, 0, capa.width, capa.height):
        capa = capa.crop((cx0, cy0, cx1, cy1))
    x0, y0 = x0 + cx0, y0 + cy0
    if img.mode == "RGBA":
        img.alpha_composite(capa, (x0, y0))
    else:
        img.paste(capa, (x0, y0), capa)


def ropa_de(rasgos: dict | None, papel: str | None = None):
    nombre = (rasgos or {}).get("nombre") or ""
    if nombre in ROPA:
        return ROPA[nombre]
    clave = sum(ord(c) for c in (papel or nombre or str((rasgos or {}).get("pelo")) +
                                  str((rasgos or {}).get("alto"))))
    return _ROPA_SUELTA[clave % len(_ROPA_SUELTA)]


def _sombra_suelo(img, x, suelo, ancho, alto):
    w, hh = ancho, alto*0.03
    capa = Image.new("RGBA", (int(2*w) + 2, int(2*hh) + 2), (0, 0, 0, 0))
    ImageDraw.Draw(capa).ellipse([0, 0, capa.width - 1, capa.height - 1], fill=(0, 0, 0, 60))
    _funde(img, capa, x - w, suelo - hh)


def _tubo(d, pts, ancho, color, g):
    """Brazo o pierna: la tinta gruesa por debajo, el color dentro y un
    brillo fino a lo largo."""
    borde = ancho + 2*max(2, g*0.9)
    d.line(pts, fill=TINTA, width=int(borde), joint="curve")
    for q in pts:
        r = borde/2
        d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=TINTA)
    d.line(pts, fill=color, width=max(1, int(ancho)), joint="curve")
    for q in pts:
        r = ancho/2
        d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=color)
    d.line([_suma(q, (-ancho*0.18, -ancho*0.05)) for q in pts], fill=_cla(color, 0.25),
           width=max(2, int(ancho*0.18)), joint="curve")


def _sombreado(img, poli, base, oscuro_hacia):
    """El poligono relleno de 'base' con la mitad del lado 'oscuro_hacia'
    (un vector) en sombra, recortado al poligono."""
    xs, ys = [p[0] for p in poli], [p[1] for p in poli]
    x0, y0 = int(min(xs)) - 2, int(min(ys)) - 2
    W, H = int(max(xs)) + 3 - x0, int(max(ys)) + 3 - y0
    if W <= 0 or H <= 0:
        return
    loc = [(p[0] - x0, p[1] - y0) for p in poli]
    capa = Image.new("RGBA", (W, H), base + (255,))
    claro = Image.new("L", (W, H), 0)
    ImageDraw.Draw(claro).polygon([(p[0] - oscuro_hacia[0], p[1] - oscuro_hacia[1]) for p in loc],
                                  fill=255)
    capa = Image.composite(capa, Image.new("RGBA", (W, H), _osc(base, 0.78) + (255,)), claro)
    mascara = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mascara).polygon(loc, fill=255)
    capa.putalpha(mascara)
    _funde(img, capa, x0, y0)


def _lado(punto, centro, n):
    return 1 if (punto[0] - centro[0])*n[0] + (punto[1] - centro[1])*n[1] >= 0 else -1


# Lo que se viste ENCIMA del tronco (la coraza, el habito, la banda): se pinta
# despues de el. La capa y el manto cuelgan por detras y van antes.
DETRAS_DEL_CUERPO = ("capa", "manto")


def cuerpo(d, P, p, cuello, cadera, alto, g, rasgos, x, suelo, s, papel=None,
           encima=None):
    """El cuerpo entero menos la cabeza. 'encima' pinta lo que se viste sobre
    el tronco, entre el tronco y los brazos."""
    img = d._image
    ropa, pantalon = ropa_de(rasgos, papel)
    pantalon = (rasgos or {}).get("calzas") or pantalon
    an = (rasgos or {}).get("ancho", 1.0)
    falda = (rasgos or {}).get("nombre") in _FALDA or (rasgos or {}).get("pelo") == "moño"
    if img.mode != "RGBA":   # en la capa del que se cae, la sombra giraria con el
        _sombra_suelo(img, x, suelo, alto*0.26*an, alto)
    d = ImageDraw.Draw(img)

    ux, uy = cadera[0] - cuello[0], cadera[1] - cuello[1]
    L = math.hypot(ux, uy) or 1.0
    u = (ux/L, uy/L)
    n = (-u[1], u[0])
    sw, hw = alto*0.105*an, alto*0.085*an
    grosor = alto*0.058*(0.8 + 0.2*an)

    for pierna in p["piernas"]:
        pts = [P(t) for t in pierna]
        k = _lado(pts[1], cadera, n)
        pts[0] = _suma(cadera, n, k*hw*0.5)
        _tubo(d, pts, grosor, pantalon, g)
        if (rasgos or {}).get("sin_pies"):
            continue
        pie = pts[-1]
        hacia = 1 if pts[-1][0] >= pts[0][0] else -1
        d.ellipse([pie[0] - grosor*0.7 + hacia*grosor*0.35, pie[1] - grosor*0.62,
                   pie[0] + grosor*0.7 + hacia*grosor*0.9, pie[1] + grosor*0.3],
                  fill=(44, 34, 30), outline=TINTA, width=max(2, g//2))

    arriba = _suma(cuello, u, -alto*0.015)
    hombro = _suma(cuello, u, alto*0.045)
    if falda:
        bajo = _suma(cadera, u, alto*0.20)
        tronco = [_suma(arriba, n, sw*0.55), _suma(hombro, n, sw), _suma(cadera, n, hw*0.85),
                  _suma(bajo, n, hw*1.75), _suma(bajo, n, -hw*1.75), _suma(cadera, n, -hw*0.85),
                  _suma(hombro, n, -sw), _suma(arriba, n, -sw*0.55)]
    else:
        abajo = _suma(cadera, u, alto*0.035)
        tronco = [_suma(arriba, n, sw*0.55), _suma(hombro, n, sw), _suma(abajo, n, hw),
                  _suma(abajo, n, -hw), _suma(hombro, n, -sw), _suma(arriba, n, -sw*0.55)]
    # La luz viene de la izquierda de la pantalla: la sombra, a la derecha.
    _sombreado(img, tronco, ropa, (sw*0.55, 0))
    d = ImageDraw.Draw(img)
    d.line(tronco + [tronco[0]], fill=TINTA, width=max(3, g), joint="curve")
    pico = [_suma(arriba, n, sw*0.38), _suma(arriba, u, alto*0.075), _suma(arriba, n, -sw*0.38)]
    d.polygon(pico, fill=(250, 250, 246), outline=TINTA)
    for k in range(3):
        b = _suma(cuello, u, alto*(0.10 + 0.07*k))
        r = alto*0.010
        d.ellipse([b[0] - r, b[1] - r, b[0] + r, b[1] + r], fill=_cla(ropa, 0.65), outline=_osc(ropa, 0.6))
    if not falda:
        c0, c1 = _suma(cadera, n, hw*1.02), _suma(cadera, n, -hw*1.02)
        d.line([c0, c1], fill=(54, 40, 32), width=max(3, int(alto*0.022)))
        r = alto*0.016
        d.rectangle([cadera[0] - r, cadera[1] - r*0.8, cadera[0] + r, cadera[1] + r*0.8],
                    fill=(214, 170, 60), outline=TINTA)

    if encima:
        encima(d)
        d = ImageDraw.Draw(img)

    for brazo in p["brazos"]:
        pts = [P(t) for t in brazo]
        k = _lado(pts[1], cuello, n)
        pts[0] = _suma(hombro, n, k*sw*0.82)
        _tubo(d, pts, grosor*0.92, (rasgos or {}).get("manga") or ropa, g)
        mano = pts[-1]
        r = grosor*0.68
        d.ellipse([mano[0] - r, mano[1] - r, mano[0] + r, mano[1] + r], fill=PIEL, outline=TINTA,
                  width=max(2, g//2))


def mejillas(d, cab, rc):
    """Despues de dibujar la cara blanca de siempre: sombra suave abajo a la
    derecha, brillo arriba a la izquierda y mofletes."""
    img = d._image
    lado = int(rc*2) + 4
    x0, y0 = cab[0] - rc - 2, cab[1] - rc - 2
    capa = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    ImageDraw.Draw(capa).ellipse([rc*0.55, rc*0.50, rc*2.55, rc*2.45], fill=(200, 150, 128, 60))
    dentro = Image.new("L", (lado, lado), 0)
    ImageDraw.Draw(dentro).ellipse([2 + rc*0.06, 2 + rc*0.06, 2 + rc*1.94, 2 + rc*1.94], fill=255)
    capa.putalpha(ImageChops.multiply(capa.getchannel("A"), dentro))
    for l in (-1, 1):
        cx, cy = rc + 2 + l*rc*0.50, rc + 2 + rc*0.24
        ImageDraw.Draw(capa).ellipse([cx - rc*0.2, cy - rc*0.13, cx + rc*0.2, cy + rc*0.13],
                                     fill=(240, 110, 110, 80))
    ImageDraw.Draw(capa).ellipse([rc + 2 - rc*0.60, rc + 2 - rc*0.68, rc + 2 - rc*0.34, rc + 2 - rc*0.50],
                                 fill=(255, 255, 255, 230))
    _funde(img, capa, x0, y0)


# ---- LAS COSAS -------------------------------------------------------------

def cosa(img, dibuja, x, y, tam, *args, apoyada=True, **kw):
    """Dibuja una cosa con volumen: se pinta sola en una capa, se le oscurece
    el borde de abajo a la derecha, se le aclara el de arriba a la izquierda
    y, si esta en el suelo, lleva su sombra debajo."""
    m = tam*1.6
    x0, y0 = int(x - m), int(y - m*1.25)
    W, H = int(2*m), int(m*1.25 + tam*0.6)
    if W <= 4 or H <= 4:
        return
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dibuja(ImageDraw.Draw(capa), x - x0, y - y0, tam, *args, **kw)
    a = capa.getchannel("A")
    caja = a.getbbox()
    if not caja:
        return
    capa = _relieve(capa, tam)
    if apoyada:
        ancho = (caja[2] - caja[0])*0.55
        _sombra_suelo(img, x0 + (caja[0] + caja[2])/2 + tam*0.06, y, ancho, tam*1.2)
    _funde(img, capa, x0, y0)


def _relieve(capa, tam):
    """Borde de abajo a la derecha en sombra y de arriba a la izquierda en
    luz, solo donde hay dibujo. Se calcula a mitad de tamaño: el desenfoque
    a tamaño entero era lo que mas tardaba de todo el fotograma."""
    a = capa.getchannel("A")
    W, H = capa.size
    w2, h2 = max(1, W//2), max(1, H//2)
    chica = a.resize((w2, h2), Image.BILINEAR)
    k = max(1, int(tam*0.035))
    borde = ImageChops.subtract(chica, ImageChops.offset(chica, -k, -k)).filter(
        ImageFilter.BoxBlur(max(1, k*0.4)))
    bk = max(1, k//2)
    luz = ImageChops.subtract(chica, ImageChops.offset(chica, bk, bk))
    borde = borde.point(lambda v: int(v*0.32)).resize((W, H), Image.BILINEAR)
    luz = luz.point(lambda v: int(v*0.30)).resize((W, H), Image.BILINEAR)
    oscuro = Image.new("RGBA", (W, H), (20, 16, 30, 0))
    oscuro.putalpha(ImageChops.multiply(borde, a))
    claro = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    claro.putalpha(ImageChops.multiply(luz, a))
    capa = Image.alpha_composite(Image.alpha_composite(capa, oscuro), claro)
    capa.putalpha(a)
    return capa


def pieza(img, pinta, tam):
    """Un mueble o una pieza del decorado (el trono, la mesa, la chimenea, el
    barco colgado en el mar) con relieve. 'pinta' dibuja en coordenadas de la
    imagen entera sobre el ImageDraw que se le pasa."""
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    pinta(ImageDraw.Draw(capa))
    caja = capa.getchannel("A").getbbox()
    if not caja:
        return
    x0, y0 = max(0, caja[0] - 4), max(0, caja[1] - 4)
    x1, y1 = min(img.width, caja[2] + 4), min(img.height, caja[3] + 4)
    _funde(img, _relieve(capa.crop((x0, y0, x1, y1)), tam), x0, y0)
