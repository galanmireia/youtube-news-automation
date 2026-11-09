"""Muñecos nuevos para España Contada: mas detalle que los monigotes de palo.

Cabeza grande (se lee en el movil) pero con cuerpo de verdad: hombros,
cintura, piernas con botas; cara con ojos con brillo, cejas que expresan y
boca que habla; ropa de epoca (guerrera con botones y charreteras, banda
real, ros de general, levita y chistera, vestido con mantilla y peineta,
boina carlista); luz y sombra; y vida: respiran, parpadean, mueven la boca.

Todo se dibuja al doble de tamaño y se reduce, para que las lineas salgan
suaves.

    from munecos import Muneco, pinta
    amadeo = Muneco(**REPARTO["amadeo"])
    pinta(img, amadeo, x=540, suelo=1500, alto=900, pose="señala", gesto="contento", t=0.0)
"""
import math
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter

TINTA = (38, 28, 30)
PIEL = (244, 206, 176)
PIEL_SOMBRA = (220, 172, 140)
ORO = (226, 180, 60)
BLANCO = (252, 250, 245)
SS = 2                      # se dibuja al doble y se reduce


def _osc(c, k=0.78):
    return tuple(int(v*k) for v in c)


REPARTO = {
    "amadeo": dict(ropa=(46, 62, 112), pantalon=(36, 40, 60), franja=(170, 30, 40), pelo=(70, 44, 30),
                   barba="completa", bigote=True, charreteras=True, banda=True, guantes=True, botones=ORO),
    "prim": dict(ropa=(40, 52, 96), pantalon=(150, 36, 40), franja=None, pelo=(34, 28, 26),
                 barba="perilla", bigote=True, charreteras=True, banda=False, guantes=True, botones=ORO,
                 gorro="ros", calvo=True),
    "diputado": dict(ropa=(40, 38, 44), pantalon=(70, 66, 70), franja=None, pelo=(110, 80, 50),
                     barba="patillas", bigote=True, charreteras=False, banda=False, guantes=False,
                     botones=(30, 28, 30), gorro="chistera", chaleco=(150, 40, 50)),
    "diputado2": dict(ropa=(92, 64, 44), pantalon=(60, 56, 52), franja=None, pelo=(150, 150, 150),
                      barba="completa", bigote=True, charreteras=False, banda=False, guantes=False,
                      botones=(40, 30, 24), gorro="chistera", chaleco=(40, 100, 70)),
    "carlista": dict(ropa=(70, 74, 60), pantalon=(60, 58, 50), franja=None, pelo=(60, 40, 30),
                     barba="no", bigote=True, charreteras=False, banda=False, guantes=False,
                     botones=(180, 160, 120), gorro="boina"),
    "isabel": dict(mujer=True, ropa=(150, 40, 70), pelo=(60, 40, 30), gorro="diadema", cuello=BLANCO),
    "dama": dict(mujer=True, ropa=(110, 30, 50), pelo=(34, 26, 24), gorro="peineta"),
    "dama_negro": dict(mujer=True, ropa=(30, 28, 34), pelo=(40, 30, 26), gorro="peineta"),
}


class Muneco:
    def __init__(self, ropa=(60, 60, 90), pantalon=(40, 40, 50), franja=None, pelo=(60, 40, 30),
                 barba="no", bigote=False, charreteras=False, banda=False, guantes=False, botones=ORO,
                 gorro=None, calvo=False, mujer=False, chaleco=None, cuello=None, piel=PIEL):
        self.__dict__.update(locals())
        del self.__dict__["self"]


# Posturas: angulos (grados, 0 = hacia abajo, positivo = hacia fuera) de
# brazo y antebrazo de cada lado (izquierdo y derecho DE LA PANTALLA).
POSES = {
    "de_pie":        dict(bi=(12, 6), bd=(12, 6)),
    "brazos_arriba": dict(bi=(150, 170), bd=(150, 170)),
    "señala":        dict(bi=(12, 6), bd=(95, 90)),
    "señala_izq":    dict(bi=(95, 90), bd=(12, 6)),
    "triste":        dict(bi=(4, -6), bd=(4, -6), cabeza=8),
    "jarras":        dict(bi=(40, -60), bd=(40, -60)),
    "catalejo":      dict(bi=(12, 6), bd=(150, 250), catalejo=True),
    "encoge":        dict(bi=(60, 140), bd=(60, 140)),
    "libro":         dict(bi=(25, 95), bd=(25, 95), libro=True),
}


def _mezcla(a, b, k):
    return {kk: tuple(a[kk][i]*(1 - k) + b[kk][i]*k for i in range(2)) if isinstance(a[kk], tuple) else
            (b[kk] if k > 0.5 else a[kk]) for kk in a}


def _brazo(d, hombro, ang, largo, grosor, color, mano, g, lado):
    """Brazo de dos piezas con manga, puño y mano."""
    a1, a2 = math.radians(ang[0]), math.radians(ang[1])
    codo = (hombro[0] + lado*math.sin(a1)*largo*0.5, hombro[1] + math.cos(a1)*largo*0.5)
    muneca = (codo[0] + lado*math.sin(a2)*largo*0.48, codo[1] + math.cos(a2)*largo*0.48)
    for p, q in ((hombro, codo), (codo, muneca)):
        d.line([p, q], fill=TINTA, width=int(grosor + 2*g))
        for c in (p, q):
            r = (grosor + 2*g)/2
            d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=TINTA)
    for p, q in ((hombro, codo), (codo, muneca)):
        d.line([p, q], fill=color, width=int(grosor))
        for c in (p, q):
            r = grosor/2
            d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=color)
    r = grosor*0.62
    d.ellipse([muneca[0] - r, muneca[1] - r, muneca[0] + r, muneca[1] + r], fill=mano, outline=TINTA, width=g)
    return muneca


def _cara(d, cx, cy, s, m, gesto, t, habla, g):
    """La cara: ojos con brillo, cejas, nariz, boca, barba."""
    # barba primero: enmarca la cara y deja las mejillas al aire
    if m.barba == "completa":
        d.chord([cx - s*0.98, cy - s*0.55, cx + s*0.98, cy + s*0.98], 0, 180, fill=m.pelo, outline=TINTA, width=g)
        d.rectangle([cx - s*0.98, cy - s*0.1, cx - s*0.82, cy + s*0.22], fill=m.pelo)
        d.rectangle([cx + s*0.82, cy - s*0.1, cx + s*0.98, cy + s*0.22], fill=m.pelo)
        d.ellipse([cx - s*0.72, cy - s*0.5, cx + s*0.72, cy + s*0.42], fill=m.piel)
    elif m.barba == "perilla":
        d.polygon([(cx - s*0.15, cy + s*0.42), (cx + s*0.15, cy + s*0.42), (cx + s*0.06, cy + s*0.78),
                   (cx - s*0.06, cy + s*0.78)], fill=m.pelo, outline=TINTA)
    elif m.barba == "patillas":
        for lado in (-1, 1):
            d.polygon([(cx + lado*s*0.97, cy - s*0.25), (cx + lado*s*0.8, cy - s*0.25),
                       (cx + lado*s*0.62, cy + s*0.5), (cx + lado*s*0.9, cy + s*0.35)], fill=m.pelo, outline=TINTA)
    # parpadeo cada ~3,3 s, 0,12 s
    parpado = 1.0 if (t % 3.3) < 0.12 else 0.0
    ojos = {"contento": 0.0, "triste": 0.35, "enfadado": 0.3, "asustado": -0.15, "sorpresa": -0.2}.get(gesto, 0.0)
    for lado in (-1, 1):
        ox, oy = cx + lado*s*0.21, cy - s*0.02
        rw, rh = s*0.085, s*0.11*(1 + (0.25 if gesto in ("asustado", "sorpresa") else 0))
        d.ellipse([ox - rw, oy - rh, ox + rw, oy + rh], fill=BLANCO, outline=TINTA, width=g)
        mira = s*0.02
        ri = rw*0.72
        d.ellipse([ox + mira - ri, oy - ri*0.9 + rh*0.15, ox + mira + ri, oy + ri*1.1 + rh*0.15], fill=(70, 46, 30))
        rp = ri*0.55
        d.ellipse([ox + mira - rp, oy - rp + rh*0.2, ox + mira + rp, oy + rp + rh*0.2], fill=(20, 14, 12))
        rb = ri*0.32
        d.ellipse([ox + mira - ri*0.35 - rb, oy - rh*0.3 - rb, ox + mira - ri*0.35 + rb, oy - rh*0.3 + rb], fill=BLANCO)
        cierre = max(parpado, ojos if ojos > 0 else 0)
        if cierre > 0:     # parpado de arriba
            d.rectangle([ox - rw - g, oy - rh - g, ox + rw + g, oy - rh + 2*rh*cierre], fill=m.piel)
            d.line([ox - rw, oy - rh + 2*rh*cierre, ox + rw, oy - rh + 2*rh*cierre], fill=TINTA, width=g)
        # ceja
        inc = {"enfadado": 22, "triste": -22, "asustado": -14, "sorpresa": -6}.get(gesto, 0)
        alto = oy - rh - s*(0.09 if gesto not in ("sorpresa", "asustado") else 0.14)
        a = math.radians(inc)*lado
        lx = s*0.11
        p1 = (ox - lx, alto - math.sin(a)*lx*(-1))
        p2 = (ox + lx, alto + math.sin(a)*lx*(-1))
        d.line([p1, p2], fill=_osc(m.pelo, 0.8) if not m.mujer else _osc(m.pelo), width=int(s*0.05))
    # nariz
    d.arc([cx - s*0.07, cy + s*0.06, cx + s*0.07, cy + s*0.2], 200, 340, fill=_osc(m.piel, 0.7), width=g)
    # boca
    by = cy + s*0.33
    abre = habla
    if gesto in ("asustado", "sorpresa") and abre < 0.5:
        abre = 0.5
    if abre > 0.08:
        h_ = s*0.04 + s*0.16*abre
        d.ellipse([cx - s*0.1, by - h_*0.4, cx + s*0.1, by + h_], fill=(110, 30, 40), outline=TINTA, width=g)
        d.ellipse([cx - s*0.06, by + h_*0.45, cx + s*0.06, by + h_*0.9], fill=(220, 100, 110))
    elif gesto == "contento":
        d.chord([cx - s*0.13, by - s*0.08, cx + s*0.13, by + s*0.12], 0, 180, fill=(110, 30, 40), outline=TINTA, width=g)
    elif gesto in ("triste", "enfadado"):
        d.arc([cx - s*0.11, by, cx + s*0.11, by + s*0.14], 200, 340, fill=TINTA, width=int(g*1.4))
    else:
        d.line([cx - s*0.08, by + s*0.03, cx + s*0.08, by + s*0.03], fill=TINTA, width=int(g*1.4))
    if m.bigote:
        for lado in (-1, 1):
            pts = [(cx, by - s*0.1), (cx + lado*s*0.14, by - s*0.13), (cx + lado*s*0.32, by - s*0.05),
                   (cx + lado*s*0.38, by - s*0.12), (cx + lado*s*0.36, by + s*0.02), (cx + lado*s*0.16, by - s*0.01),
                   (cx, by - s*0.04)]
            d.polygon(pts, fill=_osc(m.pelo, 0.9), outline=TINTA)
    # mejillas
    for lado in (-1, 1):
        mx = cx + lado*s*0.3
        d.ellipse([mx - s*0.07, cy + s*0.12, mx + s*0.07, cy + s*0.2], fill=(240, 160, 150))


def _cabeza(d, cx, cy, s, m, gesto, t, habla, g):
    """s: el radio de la cabeza."""
    # pelo de detras (mujer: moño)
    if m.mujer:
        d.ellipse([cx - s*0.55, cy - s*1.15, cx + s*0.55, cy - s*0.35], fill=m.pelo, outline=TINTA, width=g)
    # orejas
    for lado in (-1, 1):
        ox = cx + lado*s*0.93
        d.ellipse([ox - s*0.16, cy - s*0.1, ox + s*0.16, cy + s*0.25], fill=m.piel, outline=TINTA, width=g)
    d.ellipse([cx - s, cy - s*0.98, cx + s, cy + s*0.92], fill=m.piel, outline=TINTA, width=g)
    # pelo de arriba
    if m.mujer:
        d.chord([cx - s*1.02, cy - s*1.02, cx + s*1.02, cy + s*0.4], 180, 360, fill=m.pelo, outline=TINTA, width=g)
        d.line([cx, cy - s*0.98, cx, cy - s*0.4], fill=_osc(m.pelo, 0.6), width=g)
    elif m.calvo:
        for lado in (-1, 1):
            d.chord([cx + lado*s*0.55 - s*0.45, cy - s*0.75, cx + lado*s*0.55 + s*0.45, cy + s*0.15],
                    (120 if lado < 0 else 330), (240 if lado < 0 else 60), fill=m.pelo)
    else:
        d.chord([cx - s*1.0, cy - s*1.0, cx + s*1.0, cy + s*0.3], 190, 350, fill=m.pelo, outline=TINTA, width=g)
        d.polygon([(cx - s*0.4, cy - s*0.92), (cx + s*0.1, cy - s*0.5), (cx + s*0.55, cy - s*0.85)], fill=m.pelo)
    _cara(d, cx, cy + s*0.05, s, m, gesto, t, habla, g)


def _gorro(d, cx, cy, s, m, g):
    top = cy - s*0.92
    if m.gorro == "ros":                     # el ros de general: copa alta, visera, borla
        d.polygon([(cx - s*0.62, top + s*0.18), (cx + s*0.62, top + s*0.18), (cx + s*0.5, top - s*0.55),
                   (cx - s*0.5, top - s*0.55)], fill=(34, 40, 70), outline=TINTA)
        d.rectangle([cx - s*0.6, top + s*0.02, cx + s*0.6, top + s*0.12], fill=ORO)
        d.chord([cx - s*0.75, top + s*0.08, cx + s*0.75, top + s*0.42], 0, 180, fill=(20, 20, 24), outline=TINTA)
        d.ellipse([cx - s*0.12, top - s*0.72, cx + s*0.12, top - s*0.5], fill=(200, 40, 40), outline=TINTA)
        d.line([cx, top - s*0.5, cx, top - s*0.3], fill=ORO, width=g*2)
    elif m.gorro == "chistera":
        d.rectangle([cx - s*0.55, top - s*0.95, cx + s*0.55, top + s*0.12], fill=(26, 24, 28), outline=TINTA, width=g)
        d.rectangle([cx - s*0.56, top - s*0.08, cx + s*0.56, top + s*0.04], fill=(140, 30, 40))
        d.ellipse([cx - s*0.9, top + s*0.02, cx + s*0.9, top + s*0.22], fill=(26, 24, 28), outline=TINTA, width=g)
    elif m.gorro == "boina":                 # boina roja carlista, grande y con borla
        d.ellipse([cx - s*1.15, top - s*0.45, cx + s*1.05, top + s*0.3], fill=(196, 30, 40), outline=TINTA, width=g)
        d.ellipse([cx - s*0.12 + s*0.2, top - s*0.62, cx + s*0.12 + s*0.2, top - s*0.38], fill=ORO, outline=TINTA)
    elif m.gorro == "peineta":               # peineta de carey y mantilla negra
        d.pieslice([cx - s*0.95, top - s*1.1, cx + s*0.95, top + s*0.6], 200, 340, fill=(120, 70, 30), outline=TINTA, width=g)
        for k in range(9):
            a = math.radians(200 + 140*k/8)
            x2, y2 = cx + math.cos(a)*s*0.95, top - s*0.25 + math.sin(a)*s*0.85
            d.line([cx, top - s*0.25, x2, y2], fill=(90, 50, 20), width=g)
        manto = [(cx - s*0.9, top - s*0.3), (cx + s*0.9, top - s*0.3), (cx + s*1.35, cy + s*1.9), (cx - s*1.35, cy + s*1.9)]
        return manto
    elif m.gorro == "diadema":
        d.polygon([(cx - s*0.6, top + s*0.15), (cx - s*0.45, top - s*0.3), (cx - s*0.2, top - s*0.05),
                   (cx, top - s*0.4), (cx + s*0.2, top - s*0.05), (cx + s*0.45, top - s*0.3), (cx + s*0.6, top + s*0.15)],
                  fill=ORO, outline=TINTA)
        for k in (-0.45, 0, 0.45):
            d.ellipse([cx + s*k - s*0.06, top - s*0.08, cx + s*k + s*0.06, top + s*0.04], fill=(200, 30, 60))
    elif m.gorro == "corona":
        d.polygon([(cx - s*0.7, top + s*0.2), (cx - s*0.75, top - s*0.45), (cx - s*0.38, top - s*0.12),
                   (cx, top - s*0.55), (cx + s*0.38, top - s*0.12), (cx + s*0.75, top - s*0.45), (cx + s*0.7, top + s*0.2)],
                  fill=ORO, outline=TINTA)
        for k in (-0.75, 0, 0.75):
            d.ellipse([cx + s*k - s*0.08, top - s*0.58 + (0 if k else -0.0), cx + s*k + s*0.08, top - s*0.42], fill=BLANCO, outline=TINTA)
        for k, col in ((-0.4, (40, 90, 200)), (0, (200, 30, 40)), (0.4, (40, 160, 80))):
            d.ellipse([cx + s*k - s*0.08, top - s*0.02, cx + s*k + s*0.08, top + s*0.13], fill=col)
    return None


def _cuerpo_hombre(d, cx, suelo, u, m, pose, t, g, anda):
    cadera = suelo - u*0.34
    hombro_y = suelo - u*0.66
    resp = math.sin(t*2.2)*u*0.004
    # piernas (andando: se cruzan)
    for lado in (-1, 1):
        sw = math.sin(t*9 + (0 if lado < 0 else math.pi))*u*0.05 if anda else 0
        x0 = cx + lado*u*0.06
        pie = (x0 + sw, suelo - u*0.03)
        d.line([(x0, cadera), pie], fill=TINTA, width=int(u*0.095 + 2*g))
        d.line([(x0, cadera), pie], fill=m.pantalon, width=int(u*0.095))
        if m.franja:
            d.line([(x0 + lado*u*0.03, cadera + u*0.02), (pie[0] + lado*u*0.03, pie[1] - u*0.06)], fill=m.franja, width=int(u*0.014))
        d.rounded_rectangle([pie[0] - u*0.05 + lado*u*0.01, pie[1] - u*0.06, pie[0] + u*0.06 + lado*u*0.03, pie[1] + u*0.03],
                            radius=int(u*0.03), fill=(24, 20, 20), outline=TINTA, width=g)
    # guerrera / levita
    ancho_h, ancho_c, faldon = u*0.17, u*0.13, u*0.18
    torso = [(cx - ancho_h, hombro_y - resp), (cx + ancho_h, hombro_y - resp), (cx + ancho_c, cadera - u*0.02),
             (cx + faldon, cadera + u*0.08), (cx - faldon, cadera + u*0.08), (cx - ancho_c, cadera - u*0.02)]
    d.polygon(torso, fill=m.ropa, outline=TINTA, width=g)
    if m.chaleco:
        d.polygon([(cx - u*0.06, hombro_y + u*0.02), (cx + u*0.06, hombro_y + u*0.02), (cx + u*0.05, cadera),
                   (cx - u*0.05, cadera)], fill=m.chaleco, outline=TINTA)
        d.polygon([(cx - u*0.035, hombro_y + u*0.01), (cx + u*0.035, hombro_y + u*0.01), (cx, hombro_y + u*0.08)], fill=BLANCO)
    else:
        for fila in (-1, 1):
            for k in range(5):
                by = hombro_y + u*(0.05 + 0.055*k)
                bx = cx + fila*u*0.04
                d.ellipse([bx - u*0.012, by - u*0.012, bx + u*0.012, by + u*0.012], fill=m.botones, outline=TINTA)
    # cinturon / fajin
    d.rectangle([cx - ancho_c - u*0.005, cadera - u*0.045, cx + ancho_c + u*0.005, cadera - u*0.015],
                fill=(30, 26, 26) if not m.charreteras else (190, 40, 50), outline=TINTA)
    if m.banda:                       # la banda real, del hombro a la cadera
        d.polygon([(cx - ancho_h + u*0.02, hombro_y + u*0.01), (cx - ancho_h + u*0.08, hombro_y),
                   (cx + ancho_c + u*0.01, cadera - u*0.06), (cx + ancho_c - u*0.04, cadera - u*0.01)],
                  fill=(110, 170, 225), outline=TINTA)
        d.line([(cx - ancho_h + u*0.05, hombro_y + u*0.005), (cx + ancho_c - u*0.015, cadera - u*0.035)], fill=BLANCO, width=int(u*0.016))
    # cuello alto
    d.rectangle([cx - u*0.05, hombro_y - u*0.03, cx + u*0.05, hombro_y + u*0.01],
                fill=(190, 40, 50) if m.charreteras else BLANCO, outline=TINTA)
    # brazos
    p = POSES.get(pose, POSES["de_pie"])
    manos = []
    for lado, clave in ((-1, "bi"), (1, "bd")):
        ang = p[clave]
        if pose == "de_pie":
            ang = (ang[0] + math.sin(t*2.2)*2, ang[1])
        hombro = (cx + lado*(ancho_h - u*0.01), hombro_y + u*0.02 - resp)
        manos.append(_brazo(d, hombro, ang, u*0.36, u*0.07, m.ropa, BLANCO if m.guantes else m.piel, g, lado))
        if m.charreteras:
            d.ellipse([hombro[0] - u*0.05, hombro[1] - u*0.035, hombro[0] + u*0.05, hombro[1] + u*0.02], fill=ORO, outline=TINTA, width=g)
            for k in range(5):
                fx = hombro[0] - u*0.04 + u*0.02*k
                d.line([fx, hombro[1] + u*0.015, fx, hombro[1] + u*0.05], fill=ORO, width=g)
    if p.get("catalejo"):
        mx, my = manos[1]
        d.rounded_rectangle([mx - u*0.02, my - u*0.03, mx + u*0.22, my + u*0.03], radius=int(u*0.02), fill=(200, 160, 60), outline=TINTA, width=g)
        d.rectangle([mx + u*0.16, my - u*0.035, mx + u*0.2, my + u*0.035], fill=(140, 100, 40), outline=TINTA)
    if p.get("libro"):
        mx = (manos[0][0] + manos[1][0])/2
        my = (manos[0][1] + manos[1][1])/2
        d.rectangle([mx - u*0.12, my - u*0.09, mx + u*0.12, my + u*0.06], fill=(120, 40, 40), outline=TINTA, width=g)
        d.rectangle([mx - u*0.105, my - u*0.075, mx - u*0.005, my + u*0.045], fill=(246, 238, 220))
        d.rectangle([mx + u*0.005, my - u*0.075, mx + u*0.105, my + u*0.045], fill=(246, 238, 220))
    return hombro_y - resp


def _cuerpo_mujer(d, cx, suelo, u, m, pose, t, g, anda):
    """Vestido de crinolina hasta el suelo, talle estrecho, mangas."""
    cintura = suelo - u*0.42
    hombro_y = suelo - u*0.64
    resp = math.sin(t*2.2)*u*0.004
    vaiven = math.sin(t*9)*u*0.012 if anda else 0
    falda = [(cx - u*0.08, cintura), (cx + u*0.08, cintura), (cx + u*0.30 + vaiven, suelo), (cx - u*0.30 + vaiven, suelo)]
    d.polygon(falda, fill=m.ropa, outline=TINTA, width=g)
    for k in (-0.15, 0, 0.15):
        d.line([(cx + u*k*0.3, cintura + u*0.02), (cx + u*k + vaiven, suelo - u*0.01)], fill=_osc(m.ropa, 0.75), width=g)
    d.line([(cx - u*0.3 + vaiven, suelo - u*0.03), (cx + u*0.3 + vaiven, suelo - u*0.03)], fill=_osc(m.ropa, 0.6), width=int(u*0.02))
    torso = [(cx - u*0.13, hombro_y - resp), (cx + u*0.13, hombro_y - resp), (cx + u*0.08, cintura), (cx - u*0.08, cintura)]
    d.polygon(torso, fill=m.ropa, outline=TINTA, width=g)
    if m.cuello:
        d.chord([cx - u*0.1, hombro_y - u*0.04, cx + u*0.1, hombro_y + u*0.06], 0, 180, fill=m.cuello, outline=TINTA)
    p = POSES.get(pose, POSES["de_pie"])
    for lado, clave in ((-1, "bi"), (1, "bd")):
        hombro = (cx + lado*u*0.12, hombro_y + u*0.02 - resp)
        _brazo(d, hombro, p[clave], u*0.32, u*0.06, m.ropa, m.piel, g, lado)
    return hombro_y - resp


def _relieve(capa, tam):
    """Luz arriba a la izquierda, sombra abajo a la derecha, solo donde hay dibujo."""
    a = capa.getchannel("A")
    k = max(2, int(tam*0.012))
    sombra = ImageChops.subtract(a, ImageChops.offset(a, -k, -k)).filter(ImageFilter.GaussianBlur(k*0.6))
    luz = ImageChops.subtract(a, ImageChops.offset(a, k, k)).filter(ImageFilter.GaussianBlur(k*0.6))
    negro = Image.new("RGBA", capa.size, (40, 20, 40, 0))
    negro.putalpha(sombra.point(lambda v: int(v*0.35)))
    blanco = Image.new("RGBA", capa.size, (255, 250, 235, 0))
    blanco.putalpha(luz.point(lambda v: int(v*0.25)))
    capa = Image.alpha_composite(capa, negro)
    capa = Image.alpha_composite(capa, blanco)
    capa.putalpha(a)
    return capa


def pose_entre(a, b, k):
    """Postura intermedia entre dos (k de 0 a 1): para que lleguen a ella y no aparezcan."""
    pa, pb = POSES[a], POSES[b]
    out = dict(pb)
    for c in ("bi", "bd"):
        out[c] = tuple(pa[c][i] + (pb[c][i] - pa[c][i])*k for i in range(2))
    out["cabeza"] = pa.get("cabeza", 0) + (pb.get("cabeza", 0) - pa.get("cabeza", 0))*k
    return out


def pinta(img, m: Muneco, x, suelo, alto, pose="de_pie", gesto="neutro", t=0.0, habla=0.0,
          espejo=False, anda=False, efecto=None, gorro=None, desde="de_pie", llega=0.45):
    """'desde' y 'llega': empieza en esa postura y tarda 'llega' segundos en la pedida."""
    k = 1 - (1 - min(1.0, t/llega))**3 if llega else 1.0
    POSES["_ahora"] = pose_entre(desde, pose, k) if desde in POSES and pose in POSES else POSES.get(pose, POSES["de_pie"])
    pose = "_ahora"
    """Pinta el muñeco con los pies en (x, suelo) y 'alto' pixeles de alto."""
    w = int(alto*0.9)*SS
    h = int(alto*1.25)*SS
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    u = alto*SS
    cx, sl = w/2, h - u*0.04
    g = max(2, int(u*0.009))
    if m.mujer:
        cuello_y = _cuerpo_mujer(d, cx, sl, u, m, pose, t, g, anda)
    else:
        cuello_y = _cuerpo_hombre(d, cx, sl, u, m, pose, t, g, anda)
    s = u*0.16
    inclina = POSES.get(pose, {}).get("cabeza", 0)
    hy = cuello_y - s*0.86 + inclina*u*0.002
    d.rectangle([cx - u*0.035, cuello_y - u*0.05, cx + u*0.035, cuello_y + u*0.01], fill=m.piel, outline=TINTA)
    gorro_real = gorro if gorro is not None else m.gorro
    m2 = Muneco(**{**m.__dict__, "gorro": gorro_real})
    if gorro_real == "peineta":            # la mantilla va DETRAS de la cabeza
        capa_m = Image.new("RGBA", capa.size, (0, 0, 0, 0))
        manto = _gorro(ImageDraw.Draw(capa_m), cx, hy, s, m2, g)
        mant = Image.new("RGBA", capa.size, (0, 0, 0, 0))
        dm = ImageDraw.Draw(mant)
        dm.polygon(manto, fill=(20, 18, 22, 210), outline=TINTA)
        for k in range(12):
            yy = manto[0][1] + (manto[2][1] - manto[0][1])*k/12
            dm.line([(manto[3][0], yy), (manto[2][0], yy)], fill=(60, 56, 62, 120), width=g)
        capa = Image.alpha_composite(mant, capa)
        d = ImageDraw.Draw(capa)
    _cabeza(d, cx, hy, s, m2, gesto, t, habla, g)
    if gorro_real:
        _gorro(d, cx, hy, s, m2, g)
    # efectos
    if efecto == "sudor":
        for k, (dx, dy) in enumerate(((-1.1, -0.6), (1.15, -0.4), (0.9, -0.95))):
            fase = (t*1.6 + k*0.33) % 1
            ex, ey = cx + dx*s, hy + dy*s + fase*s*0.6
            d.polygon([(ex, ey - s*0.18), (ex - s*0.09, ey), (ex + s*0.09, ey)], fill=(120, 190, 255), outline=TINTA)
            d.ellipse([ex - s*0.09, ey - s*0.07, ex + s*0.09, ey + s*0.11], fill=(120, 190, 255), outline=TINTA)
    elif efecto == "lagrimas":
        for lado in (-1, 1):
            fase = (t*1.2 + (0.5 if lado > 0 else 0)) % 1
            ex, ey = cx + lado*s*0.21, hy + s*0.15 + fase*s*0.7
            d.ellipse([ex - s*0.05, ey - s*0.07, ex + s*0.05, ey + s*0.07], fill=(120, 190, 255), outline=TINTA)
    elif efecto == "mareo":
        for k in range(3):
            a = t*4 + k*2.09
            ex, ey = cx + math.cos(a)*s*1.1, hy - s*1.2 + math.sin(a)*s*0.25
            pts = [(ex + math.cos(math.radians(90 + 72*i))*s*(0.16 if i % 2 == 0 else 0.07),
                    ey - math.sin(math.radians(90 + 72*i))*s*(0.16 if i % 2 == 0 else 0.07)) for i in range(10)]
            pts = [(ex + math.cos(math.radians(90 + 36*i))*s*(0.17 if i % 2 == 0 else 0.07),
                    ey - math.sin(math.radians(90 + 36*i))*s*(0.17 if i % 2 == 0 else 0.07)) for i in range(10)]
            d.polygon(pts, fill=(255, 220, 40), outline=TINTA)
    elif efecto == "confuso":
        from PIL import ImageFont
        f = ImageFont.truetype("/usr/share/fonts/opentype/inter/InterDisplay-Black.otf", int(s*0.6))
        for k, dx in enumerate((-0.9, 0, 0.9)):
            yy = hy - s*1.45 - math.sin(t*5 + k)*s*0.08
            d.text((cx + dx*s, yy), "?", font=f, fill=(255, 255, 255), stroke_width=g*2, stroke_fill=TINTA, anchor="mm")
    capa = _relieve(capa, u)
    if espejo:
        capa = capa.transpose(Image.FLIP_LEFT_RIGHT)
    capa = capa.resize((w//SS, h//SS), Image.LANCZOS)
    # sombra en el suelo
    som = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(som).ellipse([x - alto*0.24, suelo - alto*0.03, x + alto*0.24, suelo + alto*0.03], fill=(0, 0, 0, 70))
    img.alpha_composite(som.filter(ImageFilter.GaussianBlur(alto*0.015)))
    img.alpha_composite(capa, (int(x - capa.width/2), int(suelo - capa.height + alto*0.04)))
