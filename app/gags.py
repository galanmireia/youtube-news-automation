"""LOS GAGS DE MOKORDO ("es muy repetitivo... tiene que ser muy exagerado
las cosas que haga"): golpes de dibujos animados que se ven desde lejos.

Mokordo se pinta en una capa aparte y esa capa se deforma entera: se
aplasta bajo un yunque, se cae de cara, se derrite en un charco, se hincha
como un globo, tiembla con fantasmas de si mismo... y encima van los
añadidos (estrellas, vapor, ojos con muelle, el alma que se escapa).

El guion lo pide en la mascota: "gag": {"tipo": "aplasta", "cuando": "..."}
(o "gag": "aplasta"). Empieza cuando la voz dice "cuando"; antes, Mokordo
hace su accion normal. Cada gag dura lo que el plano: tiene su golpe y luego
se queda en el estado final (aplastado, derretido, tirado...) moviendose un
poco, para que no se congele.
"""
from __future__ import annotations

import math

from PIL import Image, ImageChops, ImageDraw

from . import mascota as _m

TINTA = _m.TINTA

# nombre -> lo que el guion debe saber (en ingles, va al prompt)
GAGS = {
    "aplasta":    "an anvil falls on him and squashes him flat as a pancake (crushed by tiredness, weight, a bill, bad news)",
    "de_cara":    "faints and falls flat on his face, stars spinning over him (collapse, exhaustion, shock)",
    "derrite":    "melts into a puddle with his eyes still blinking (heat, too tired, giving up, cringe)",
    "infla":      "inflates like a balloon and floats up (overeating, bloating, gas, pride)",
    "tiembla":    "shakes violently with ghost copies of himself (caffeine, sugar rush, cold, panic)",
    "ojos_fuera": "his eyes pop out on springs (shock, surprise, an unbelievable fact)",
    "vapor":      "turns red and steam blows out of his head (anger, stress, fever, spicy food)",
    "alma":       "his soul floats out of his body and then snaps back in (exhausted, bored to death, boring job)",
    "zombi":      "walks like a zombie, arms out, greenish, eyes half shut (no sleep, Monday morning)",
    "cabezada":   "nods off, head drooping, then jolts awake with a '!' (microsleep, boring class, drowsy)",
    "gira":       "spins like a tornado and ends up dizzy (confusion, too much information, a party)",
    "encoge":     "shrinks to tiny size (feeling small, losing, a giant number next to him)",
    "crece":      "grows huge and proud (a win, muscles, confidence)",
    "sale_volando": "gets blasted off the screen spinning, with a twinkle (a sneeze, an explosion, a kick)",
    "llora":      "cries two fountains of tears (sad, a loss, onions, a breakup)",
    "rayo":       "gets struck by lightning: flash, frizzy, smoking and charred (a sudden idea, an alarm, a shock)",
    "corazon":    "his heart pounds out of his chest (stress, caffeine, love, fear)",
}


def tipo_de(gag) -> str | None:
    if isinstance(gag, str):
        t = gag
    elif isinstance(gag, dict):
        t = gag.get("tipo") or gag.get("type")
    else:
        return None
    t = str(t or "").strip().lower().replace(" ", "_").replace("-", "_")
    return t if t in GAGS else None


# ---------------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------------
def _sale(u, dur):
    """0 -> 1 en `dur` segundos, con un pasito de mas (rebote)."""
    if u <= 0:
        return 0.0
    if u >= dur:
        return 1.0
    x = u/dur
    return 1 + 2.2*(x - 1)**3 + 1.2*(x - 1)**2


def _muelle(u, frecuencia=9.0, amort=4.0):
    """Oscilacion que se apaga: para el boing al volver."""
    return math.exp(-amort*max(0.0, u))*math.cos(frecuencia*max(0.0, u))


def _estrella(d, x, y, r, giro, color=(255, 214, 60)):
    pts = []
    for k in range(10):
        a = giro + k*math.pi/5
        rr = r if k % 2 == 0 else r*0.45
        pts.append((x + rr*math.sin(a), y - rr*math.cos(a)))
    d.polygon(pts, fill=color, outline=TINTA)


def _estrellas(img, cx, cy, r, t, n=3):
    d = ImageDraw.Draw(img)
    for k in range(n):
        a = t*4.5 + k*2*math.pi/n
        x, y = cx + r*math.cos(a), cy + r*0.35*math.sin(a)
        _estrella(d, x, y, r*0.22, t*5 + k)


def _corazon(d, x, y, r, color=(225, 45, 60)):
    pts = []
    for k in range(40):
        a = k/40*2*math.pi
        hx = 16*math.sin(a)**3
        hy = -(13*math.cos(a) - 5*math.cos(2*a) - 2*math.cos(3*a) - math.cos(4*a))
        pts.append((x + hx*r/16, y + hy*r/16))
    d.polygon(pts, fill=color, outline=TINTA)
    d.line(pts + [pts[0]], fill=TINTA, width=max(2, int(r*0.08)))


def _yunque(img, x, y, ancho, texto=None):
    """Un yunque de dibujos: x centro, y la base."""
    d = ImageDraw.Draw(img)
    a, g = ancho, max(3, int(ancho*0.03))
    alto = a*0.55
    gris, oscuro = (95, 98, 108), (62, 64, 72)
    cuerpo = [(x - a*0.5, y - alto), (x + a*0.38, y - alto), (x + a*0.55, y - alto*0.78), (x + a*0.18, y - alto*0.62),
              (x + a*0.12, y - alto*0.25), (x + a*0.3, y), (x - a*0.3, y), (x - a*0.12, y - alto*0.25),
              (x - a*0.15, y - alto*0.62), (x - a*0.5, y - alto*0.75)]
    d.polygon(cuerpo, fill=gris, outline=TINTA)
    d.line(cuerpo + [cuerpo[0]], fill=TINTA, width=g)
    d.line([(x - a*0.45, y - alto*0.9), (x + a*0.3, y - alto*0.9)], fill=(150, 152, 160), width=g)
    d.polygon([(x - a*0.3, y), (x + a*0.3, y), (x + a*0.22, y - alto*0.12), (x - a*0.22, y - alto*0.12)], fill=oscuro)
    if texto:
        from . import garabato
        garabato._letrero(img, str(texto)[:10].upper(), (x - a*0.02, y - alto*0.78), a*0.16, (250, 250, 250), 0)


def _vapor(img, x, y, r, t, lado):
    from . import garabato
    for k in range(3):
        u = (t*1.4 + k/3) % 1.0
        px = x + lado*r*(0.3 + 1.6*u)
        py = y - r*(0.2 + 1.2*u)
        garabato._humo(img, (px, py), r*(0.35 + 0.6*u), 0.85*(1 - u))


def _tinte(pieza, color, fuerza):
    """Tiñe la capa (multiplicando), sin tocar su transparencia."""
    if fuerza <= 0:
        return pieza
    rgb, alfa = pieza.convert("RGB"), pieza.getchannel("A")
    capa = Image.new("RGB", pieza.size, color)
    mezcla = Image.blend(rgb, ImageChops.multiply(rgb, capa), min(1.0, fuerza))
    mezcla.putalpha(alfa)
    return mezcla


def _transparente(pieza, alfa):
    a = pieza.getchannel("A").point(lambda v: int(v*alfa))
    pieza = pieza.copy()
    pieza.putalpha(a)
    return pieza


# ---------------------------------------------------------------------------
# la deformacion de la capa
# ---------------------------------------------------------------------------
def _deforma(pieza, pivote, sx=1.0, sy=1.0, giro=0.0, derrite=0.0):
    """Escala (y derrite: la base se ensancha) y gira la pieza alrededor de
    `pivote` (en coordenadas de la pieza). Devuelve (pieza, pivote nuevo,
    funcion que lleva un punto de la pieza vieja a la nueva)."""
    w, h = pieza.size
    px, py = pivote
    W, H = max(1, int(w*sx)), max(1, int(h*sy))
    if (W, H) != (w, h):
        pieza = pieza.resize((W, H), Image.BILINEAR)
    escala = lambda p: (p[0]*W/w, p[1]*H/h)
    px, py = px*W/w, py*H/h
    pasos = [escala]
    if derrite > 0:
        extra = W*derrite
        W2 = int(W + extra)
        # la fila de arriba sale estrecha y la de abajo ancha
        quad = (-extra/2*0.2, 0, 0, H, W, H, W + extra/2*0.2)
        pieza = pieza.transform((W2, H), Image.QUAD, (-extra*0.4, 0, -extra/2, H, W + extra/2, H, W + extra*0.4, 0),
                                Image.BILINEAR)
        k = W/W2 if W2 else 1

        def ensancha(p, W=W, W2=W2, H=H, extra=extra):
            # aprox.: la x se abre mas cuanto mas abajo
            f = p[1]/H if H else 0
            ancho_fila = W2/(W + extra*(0.8 - 0.8*f + 1.0*f))
            return ((p[0] + extra*(0.4 - 0.1*f))*ancho_fila, p[1])
        pasos.append(ensancha)
        px, py = ensancha((px, py))
    if abs(giro) > 0.1:
        cx0, cy0 = pieza.width/2, pieza.height/2
        pieza = pieza.rotate(giro, resample=Image.BICUBIC, expand=True)
        cx1, cy1 = pieza.width/2, pieza.height/2
        c, s = math.cos(math.radians(giro)), math.sin(math.radians(giro))

        def gira(p, cx0=cx0, cy0=cy0, cx1=cx1, cy1=cy1, c=c, s=s):
            dx, dy = p[0] - cx0, p[1] - cy0
            return (cx1 + dx*c + dy*s, cy1 - dx*s + dy*c)
        pasos.append(gira)
        px, py = gira((px, py))

    def lleva(p):
        for f in pasos:
            p = f(p)
        return p
    return pieza, (px, py), lleva


# ---------------------------------------------------------------------------
# cada gag: (u = segundos desde que empieza, e = estado) -> plan
#   pose: cambios a la postura; gesto; sx, sy, giro, derrite, dx, dy (en
#   altos), pivote ("pies"/"centro"); tinte (color, fuerza); alfa;
#   fantasmas [(dx, dy, alfa)]; detras(img, geo) / encima(img, geo)
# ---------------------------------------------------------------------------
def _aplasta(u, e, gag):
    cae = 0.45
    plan = {"gesto": "sorpresa" if u < cae else "triste"}
    if u < cae:
        plan["pose"] = {"brazos": ((-110, 40), (-110, 40))}

        def encima(img, geo, u=u):
            y = geo["pies"][1] - geo["h"]*1.15 - (1 - (u/cae)**2)*img.height
            _yunque(img, geo["pies"][0], y, geo["h"]*0.85, gag.get("texto"))
        plan["encima"] = encima
        return plan
    v = u - cae
    vuelve = 2.6       # a los 2,6 s se despega como un muelle
    if v < vuelve:
        plan.update(sy=0.22 + 0.06*_muelle(v, 14, 6), sx=1.7 - 0.1*_muelle(v, 14, 6), pivote="pies",
                    pose={"brazos": ((0, 0), (0, 0)), "parpadeo": True})

        def encima(img, geo, v=v):
            _yunque(img, geo["pies"][0], geo["pies"][1] - geo["h"]*0.2, geo["h"]*0.85, gag.get("texto"))
            _estrellas(img, geo["pies"][0], geo["pies"][1] - geo["h"]*0.55, geo["h"]*0.45, v)
        plan["encima"] = encima
        return plan
    w = v - vuelve
    b = _muelle(w, 10, 3.5)
    plan.update(sy=1 + 0.35*b, sx=1 - 0.25*b, pivote="pies", gesto="mareo" if w < 2 else "triste")

    def encima(img, geo, w=w):
        # el yunque, a un lado (se ha caido)
        _yunque(img, geo["pies"][0] + geo["h"]*0.75, geo["pies"][1], geo["h"]*0.6, gag.get("texto"))
        if w < 2.5:
            _estrellas(img, geo["cabeza"][0], geo["cabeza"][1] - geo["h"]*0.3, geo["h"]*0.3, w + 3)
    plan["encima"] = encima
    return plan


def _de_cara(u, e, gag):
    lado = e["lado"]
    k = min(1.0, (u/0.45)**2)
    giro = -lado*88*k
    plan = {"giro": giro + (-lado*6*_muelle(u - 0.45, 18, 7) if u > 0.45 else 0), "pivote": (lado*0.3, 0.0),
            "gesto": "sorpresa" if u < 0.45 else "mareo",
            "pose": {"brazos": ((-150, 20), (-150, 20)) if u < 0.45 else ((-170, 0), (-170, 0))}}
    if u > 0.45:
        def encima(img, geo, u=u):
            _estrellas(img, geo["cabeza"][0], geo["cabeza"][1] - geo["h"]*0.32, geo["h"]*0.35, u)
            if u < 0.75:
                d = ImageDraw.Draw(img)
                x, y = geo["cabeza"][0], geo["pies"][1]
                for j in range(5):
                    a = math.pi + j*math.pi/4
                    d.line([(x + math.cos(a)*geo["h"]*0.3, y + math.sin(a)*geo["h"]*0.15),
                            (x + math.cos(a)*geo["h"]*0.5, y + math.sin(a)*geo["h"]*0.28)], fill=TINTA,
                           width=max(3, int(geo["h"]*0.015)))
        plan["encima"] = encima
    return plan


def _derrite(u, e, gag):
    k = _sale(u, 2.2)
    plan = {"sy": 1 - 0.72*k, "derrite": 1.6*k, "pivote": "pies", "gesto": "triste",
            "pose": {"brazos": ((80 + 40*k, 60), (80 + 40*k, 60)), "parpadeo": (u % 2.3) < 0.15}}

    def detras(img, geo, k=k, u=u):
        d = ImageDraw.Draw(img)
        x, y = geo["pies"]
        r = geo["h"]*(0.3 + 0.55*k)
        oscuro = _m._oscuro(_m.COLOR, 0.8)
        d.ellipse([x - r, y - r*0.16, x + r, y + r*0.12], fill=oscuro, outline=TINTA,
                  width=max(3, int(geo["h"]*0.012)))
        # gotas que caen del cuerpo
        for j in range(3):
            v = (u*0.9 + j*0.33) % 1.0
            gx = x + (j - 1)*geo["h"]*0.35*k
            gy = y - geo["h"]*0.4*(1 - k) - geo["h"]*0.2 + v*geo["h"]*0.25
            rr = geo["h"]*0.025
            d.ellipse([gx - rr, gy - rr*1.4, gx + rr, gy + rr], fill=_m.COLOR, outline=TINTA)
    plan["detras"] = detras
    return plan


def _infla(u, e, gag):
    k = _sale(u, 1.4)
    s = 1 + 0.5*k + 0.04*math.sin(u*5)
    sube = 0.12*k*(0.6 + 0.4*math.sin(u*1.8))
    plan = {"sx": s*1.08, "sy": s, "pivote": "pies", "dy": -sube, "gesto": "sorpresa" if u < 1.6 else "contento",
            "pose": {"brazos": ((-40, 0), (-40, 0)), "piernas": u*2}}

    def detras(img, geo, k=k):
        d = ImageDraw.Draw(img)
        x, y = geo["suelo_x"], geo["suelo"]
        r = geo["h"]*0.35*(1 - 0.4*k)
        d.ellipse([x - r, y - r*0.12, x + r, y + r*0.12], fill=(0, 0, 0, 0) if img.mode == "RGBA" else None,
                  outline=(150, 145, 140), width=3)
    plan["detras"] = detras
    return plan


def _tiembla(u, e, gag):
    k = min(1.0, u/0.3)
    j = math.sin(u*63)*0.05*k + math.sin(u*41)*0.03*k
    plan = {"dx": j, "gesto": "sorpresa", "fantasmas": [(-0.09*k, 0, 0.3), (0.09*k, 0, 0.3)],
            "pose": {"brazos": ((-60 + 30*math.sin(u*50), 10), (-60 - 30*math.sin(u*47), 10))}}

    def encima(img, geo, u=u):
        d = ImageDraw.Draw(img)
        x, y, r = geo["cabeza"][0], geo["cabeza"][1], geo["h"]*0.5
        for lado in (-1, 1):
            for n in range(3):
                yy = y - r*0.4 + n*r*0.4
                x0 = x + lado*r*(1.0 + 0.1*math.sin(u*30 + n))
                d.line([(x0, yy), (x0 + lado*r*0.18, yy - r*0.08), (x0 + lado*r*0.32, yy + r*0.04)], fill=TINTA,
                       width=max(3, int(geo["h"]*0.012)))
    plan["encima"] = encima
    return plan


def _ojos_fuera(u, e, gag):
    k = _sale(u, 0.35)
    plan = {"gesto": "sorpresa", "pose": {"brazos": ((-120, 50), (-120, 50))}, "sy": 1 + 0.12*_muelle(u, 12, 5)}

    def encima(img, geo, k=k, u=u):
        d = ImageDraw.Draw(img)
        cx, cy, r = geo["cabeza"][0], geo["cabeza"][1], geo["h"]
        largo = r*(0.5*k + 0.1*_muelle(u - 0.35, 14, 3))
        for lado in (-1, 1):
            bx, by = cx + lado*r*0.08, cy - r*0.04
            ro_ = r*0.045
            d.ellipse([bx - ro_, by - ro_*1.2, bx + ro_, by + ro_*1.2], fill=TINTA)
            ex, ey = bx + lado*largo*0.75, by - largo*0.6
            # el muelle
            pts = []
            for n in range(13):
                f = n/12
                px = bx + (ex - bx)*f
                py = by + (ey - by)*f + math.sin(f*math.pi*6)*r*0.025*k
                pts.append((px, py))
            d.line(pts, fill=TINTA, width=max(3, int(r*0.012)))
            ro = r*0.13*(0.5 + 0.5*k)
            d.ellipse([ex - ro, ey - ro, ex + ro, ey + ro], fill=(255, 255, 255), outline=TINTA,
                      width=max(3, int(r*0.012)))
            rp = ro*0.45
            d.ellipse([ex - rp + lado*ro*0.2, ey - rp, ex + rp + lado*ro*0.2, ey + rp], fill=TINTA)
    plan["encima"] = encima
    plan["sin_ojos"] = k > 0.2
    return plan


def _vapor_gag(u, e, gag):
    k = min(1.0, u/0.8)
    plan = {"gesto": "enfadado", "tinte": ((255, 70, 60), 0.55*k), "sy": 1 + 0.05*math.sin(u*20)*k,
            "pose": {"brazos": ((70, -40), (70, -40))}}

    def encima(img, geo, u=u):
        cx, cy, r = geo["cabeza"][0], geo["cabeza"][1], geo["h"]*0.3
        for lado in (-1, 1):
            _vapor(img, cx + lado*r*0.9, cy - r*0.4, r*0.55, u + (0.5 if lado > 0 else 0), lado)
    plan["encima"] = encima
    return plan


def _alma(u, e, gag):
    k = _sale(u, 1.0)
    vuelve = u > 3.2
    plan = {"gesto": "triste", "pose": {"parpadeo": True, "brazos": ((85, 20), (85, 20))},
            "sy": 0.92 if not vuelve else 1 + 0.2*_muelle(u - 3.2, 14, 5)}
    if not vuelve:
        def encima(img, geo, k=k, u=u):
            pieza = geo["pieza"]
            alma = _transparente(_tinte(pieza.convert("RGBA"), (235, 240, 255), 0.0), 0.45)
            blanca = Image.new("RGBA", alma.size, (250, 252, 255, 0))
            blanca.putalpha(alma.getchannel("A").point(lambda v: min(255, int(v*1.6))))
            blanca = blanca.resize((int(blanca.width*0.55), int(blanca.height*0.55)))
            sube = geo["h"]*0.4*k
            ola = math.sin(u*3)*geo["h"]*0.06
            x0, y0 = geo["pos"]
            x0 += pieza.width*0.22
            d = ImageDraw.Draw(img)
            # la estela que la une al cuerpo
            for n in range(8):
                f = n/8
                rr = geo["h"]*0.05*(1 - f*0.6)
                px = x0 + blanca.width/2 + ola*f + math.sin(u*4 + f*5)*geo["h"]*0.04
                py = y0 + pieza.height*0.25 - sube*f
                d.ellipse([px - rr, py - rr, px + rr, py + rr], fill=(235, 240, 252))
            img.paste(blanca, (int(x0 + ola), int(y0 - sube)), blanca)
        plan["encima"] = encima
    return plan


def _zombi(u, e, gag):
    plan = {"gesto": "zombi", "colorea": ((110, 200, 95), 0.55), "dx": -e["lado"]*0.0 + 0.12*math.sin(u*0.6),
            "giro": 4*math.sin(u*2.2),
            "pose": {"brazos": ((-5, 0), (-5, 0)), "piernas": u*3.5, "parpadeo": False}}
    return plan


def _cabezada(u, e, gag):
    ciclo = 2.6
    v = u % ciclo
    if v < 1.8:
        giro = -e["lado"]*22*(v/1.8)**2
        plan = {"giro": giro, "pivote": "pies", "gesto": "dormido", "pose": {"parpadeo": True}}
    else:
        w = v - 1.8
        plan = {"giro": -e["lado"]*22*math.exp(-w*10)*math.cos(w*25), "pivote": "pies", "gesto": "sorpresa",
                "sy": 1 + 0.15*_muelle(w, 15, 4)}

        def encima(img, geo, w=w):
            from . import garabato
            garabato._letrero(img, "!", (geo["cabeza"][0] + geo["h"]*0.32, geo["cabeza"][1] - geo["h"]*0.35),
                              geo["h"]*0.45, (225, 40, 40), 10, garabato._escala_pop(w))
        plan["encima"] = encima
    return plan


def _gira(u, e, gag):
    if u < 2.0:
        rapido = min(1.0, u/0.4)
        f = math.cos(u*22*rapido)
        plan = {"sx": max(0.12, abs(f)), "sy": 1 + 0.1*rapido, "dy": -0.08*rapido, "gesto": "sorpresa"}

        def detras(img, geo, u=u):
            d = ImageDraw.Draw(img)
            x, y = geo["pies"][0], geo["pies"][1] - geo["h"]*0.5
            for n in range(4):
                r = geo["h"]*(0.35 + 0.08*n)
                a0 = (u*600 + n*90) % 360
                d.arc([x - r, y - r*0.6, x + r, y + r*0.6], a0, a0 + 120, fill=(120, 120, 130),
                      width=max(3, int(geo["h"]*0.01)))
        plan["detras"] = detras
        return plan
    w = u - 2.0
    plan = {"gesto": "mareo", "giro": 10*math.sin(w*3), "pivote": "pies"}

    def encima(img, geo, w=w):
        _estrellas(img, geo["cabeza"][0], geo["cabeza"][1] - geo["h"]*0.32, geo["h"]*0.3, w)
    plan["encima"] = encima
    return plan


def _encoge(u, e, gag):
    k = _sale(u, 0.7)
    s = 1 - 0.65*k
    return {"sx": s, "sy": s, "pivote": "pies", "gesto": "sorpresa" if u < 1 else "triste"}


def _crece(u, e, gag):
    k = _sale(u, 0.8)
    s = 1 + 0.32*k
    return {"sx": s, "sy": s, "pivote": "pies", "gesto": "contento",
            "pose": {"brazos": ((-100, -50), (-100, -50))}}


def _sale_volando(u, e, gag):
    if u < 0.25:
        return {"sy": 1 - 0.3*(u/0.25), "sx": 1 + 0.2*(u/0.25), "pivote": "pies", "gesto": "sorpresa"}
    v = u - 0.25
    plan = {"dx": 1.8*v*e["lado"], "dy": -2.2*v + 0.6*v*v, "giro": -e["lado"]*720*v, "pivote": "centro",
            "gesto": "sorpresa", "pose": {"brazos": ((-130, 0), (-130, 0))}}
    if v > 0.9:
        plan["oculto"] = True

        def encima(img, geo, v=v):
            if v < 1.6:
                d = ImageDraw.Draw(img)
                x = min(img.width*0.92, max(img.width*0.08, geo["pies"][0] + e["lado"]*img.width*0.32))
                _estrella(d, x, img.height*0.12, geo["h"]*0.12*(1 - abs(v - 1.25)/0.35), v*8, (255, 255, 255))
        plan["encima"] = encima
    return plan


def _llora(u, e, gag):
    plan = {"gesto": "llora", "pose": {"brazos": ((60, 70), (60, 70))}, "sy": 1 - 0.04*abs(math.sin(u*6))}

    def encima(img, geo, u=u):
        d = ImageDraw.Draw(img)
        cx, cy, h = geo["cabeza"][0], geo["cabeza"][1], geo["h"]
        for lado in (-1, 1):
            ox, oy = cx + lado*h*0.09, cy + h*0.0
            for n in range(9):
                f = ((u*1.8 + n/9) % 1.0)
                x = ox + lado*h*0.55*f
                y = oy - h*0.12*math.sin(f*math.pi)*1.3 + h*0.35*f*f
                rr = h*0.034*(1 - 0.3*f)
                d.ellipse([x - rr, y - rr*1.2, x + rr, y + rr], fill=(120, 190, 245), outline=(60, 120, 190), width=2)
    plan["encima"] = encima
    return plan


def _rayo(u, e, gag):
    if u < 0.6:
        plan = {"gesto": "sorpresa", "sy": 1.1, "pose": {"brazos": ((-140, 30), (-140, 30))},
                "tinte": ((255, 255, 255), 0.0) if int(u*20) % 2 else ((40, 40, 40), 0.85)}

        def encima(img, geo, u=u):
            d = ImageDraw.Draw(img)
            x, y = geo["cabeza"][0], geo["cabeza"][1] - geo["h"]*0.2
            pts = [(x + geo["h"]*0.05, 0), (x - geo["h"]*0.12, y*0.45), (x + geo["h"]*0.06, y*0.5),
                   (x - geo["h"]*0.1, y*0.85), (x + geo["h"]*0.12, y*0.5), (x - geo["h"]*0.04, y*0.45),
                   (x + geo["h"]*0.18, 0)]
            d.polygon(pts, fill=(255, 230, 60), outline=TINTA)
            if int(u*20) % 2 == 0:
                blanco = Image.new("RGB", img.size, (255, 255, 240))
                img.paste(Image.blend(img.convert("RGB"), blanco, 0.45))
        plan["encima"] = encima
        return plan
    w = u - 0.6
    plan = {"gesto": "mareo", "tinte": ((70, 60, 60), 0.55), "pose": {"parpadeo": (w % 1.5) < 0.15}}

    def encima(img, geo, w=w):
        from . import garabato
        cx, cy = geo["cabeza"]
        for k in range(2):
            v = (w*0.7 + k*0.5) % 1.0
            garabato._humo(img, (cx + (k - 0.5)*geo["h"]*0.3, cy - geo["h"]*(0.35 + 0.5*v)), geo["h"]*(0.08 + 0.1*v),
                           0.7*(1 - v))
    plan["encima"] = encima
    return plan


def _corazon_gag(u, e, gag):
    latido = abs(math.sin(u*7))**6
    plan = {"gesto": "sorpresa", "sy": 1 + 0.04*latido, "pose": {"brazos": ((40, 60), (40, 60))}}

    def encima(img, geo, latido=latido):
        d = ImageDraw.Draw(img)
        x = geo["pies"][0] + e["lado"]*geo["h"]*(0.05 + 0.18*latido)
        y = geo["pies"][1] - geo["h"]*0.42
        _corazon(d, x, y, geo["h"]*(0.13 + 0.12*latido))
        if latido > 0.5:
            for k in range(3):
                a = -0.6 + k*0.6
                d.line([(x + math.cos(a)*geo["h"]*0.3, y + math.sin(a)*geo["h"]*0.3),
                        (x + math.cos(a)*geo["h"]*0.4, y + math.sin(a)*geo["h"]*0.4)], fill=TINTA,
                       width=max(3, int(geo["h"]*0.012)))
    plan["encima"] = encima
    return plan


_PLANES = {"aplasta": _aplasta, "de_cara": _de_cara, "derrite": _derrite, "infla": _infla, "tiembla": _tiembla,
           "ojos_fuera": _ojos_fuera, "vapor": _vapor_gag, "alma": _alma, "zombi": _zombi, "cabezada": _cabezada,
           "gira": _gira, "encoge": _encoge, "crece": _crece, "sale_volando": _sale_volando, "llora": _llora,
           "rayo": _rayo, "corazon": _corazon_gag}

# Gestos que el dibujo no tiene: el mas parecido.
_GESTO = {"zombi": "agotado", "llora": "triste", "mareo": "mareado"}
GESTOS = ("contento", "riendo", "enamorado", "sorpresa", "asustado", "grito", "enfadado", "triste", "asco",
          "pensativo", "mareado", "confuso", "bostezo", "agotado", "dormido", "neutro")


def empieza(gag) -> float:
    return float(gag.get("_t", 0.3)) if isinstance(gag, dict) else 0.3


def pinta(img, est: dict, gag, reloj: float):
    """Pinta a Mokordo haciendo el gag. Devuelve (cabeza, manos) como
    mascota.pinta_estado (ya movidas a donde han acabado)."""
    tipo = tipo_de(gag)
    gag = gag if isinstance(gag, dict) else {"tipo": gag}
    u = reloj - empieza(gag)
    if not tipo or u < 0:
        return _m.pinta_estado(img, est)
    plan = _PLANES[tipo](u, est, gag)
    est = dict(est)
    est["habla"] = None           # la cara la pone el gag
    est["p"] = dict(est["p"], **(plan.get("pose") or {}))
    if plan.get("gesto"):
        est["gesto"] = _gesto_valido(_GESTO.get(plan["gesto"], plan["gesto"]))
    h = est["h"]
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    _m.SIN_SOMBRA[0] = True
    try:
        cabeza, manos = _m.pinta_estado(capa, est)
    finally:
        _m.SIN_SOMBRA[0] = False
    caja = capa.getbbox()
    if not caja:
        return cabeza, manos
    pieza = capa.crop(caja)
    x0, y0 = caja[0], caja[1]
    pv = plan.get("pivote")
    if pv == "centro":
        piv = (est["cx"], est["suelo"] - h*0.45)
    elif isinstance(pv, tuple):
        piv = (est["cx"] + pv[0]*h, est["suelo"] - pv[1]*h)
    else:
        piv = (est["cx"], est["suelo"])
    tinte = plan.get("tinte")
    if tinte:
        pieza = _tinte(pieza, tinte[0], tinte[1])
    if plan.get("colorea"):
        color, fuerza = plan["colorea"]
        alfa = pieza.getchannel("A")
        rgb = pieza.convert("RGB")
        pieza = Image.blend(rgb, Image.new("RGB", rgb.size, color), fuerza)
        # que no se pierdan las rayas: la tinta vuelve encima
        oscuro = rgb.convert("L").point(lambda v: 255 if v < 70 else 0)
        pieza.paste(rgb, (0, 0), oscuro)
        pieza.putalpha(alfa)
    pieza, pp, lleva = _deforma(pieza, (piv[0] - x0, piv[1] - y0), plan.get("sx", 1.0), plan.get("sy", 1.0),
                                plan.get("giro", 0.0), plan.get("derrite", 0.0))
    destino = (piv[0] + plan.get("dx", 0.0)*h, piv[1] + plan.get("dy", 0.0)*h)
    pos = (int(destino[0] - pp[0]), int(destino[1] - pp[1]))

    def mueve(p):
        q = lleva((p[0] - x0, p[1] - y0))
        return (q[0] + pos[0], q[1] + pos[1])
    cab = mueve(cabeza[:2])
    geo = {"h": h, "pies": mueve((est["cx"], est["suelo"])), "cabeza": cab, "suelo": est["suelo"],
           "suelo_x": est["cx"], "pieza": pieza, "pos": pos}
    if not plan.get("oculto") and plan.get("dy", 0.0) > -0.3:
        # la sombra, debajo de lo que haya quedado de el
        ancho = max(pieza.width*0.5, h*0.15)
        sx_ = destino[0] - pp[0] + pieza.width/2
        ImageDraw.Draw(img).ellipse([sx_ - ancho*0.55, est["suelo"] - h*0.02, sx_ + ancho*0.55, est["suelo"] + h*0.02],
                                    fill=(222, 218, 210))
    if plan.get("detras"):
        plan["detras"](img, geo)
    if not plan.get("oculto"):
        if pieza.mode != "RGBA":
            pieza = pieza.convert("RGBA")
        for fdx, fdy, fa in plan.get("fantasmas") or []:
            fantasma = _transparente(pieza, fa)
            img.paste(fantasma, (int(pos[0] + fdx*h), int(pos[1] + fdy*h)), fantasma)
        img.paste(pieza, pos, pieza)
    if plan.get("encima"):
        plan["encima"](img, geo)
    cabeza = (cab[0], cab[1]) + tuple(cabeza[2:])
    manos = [mueve(mn) for mn in manos] if manos else manos
    return cabeza, manos


def _gesto_valido(g):
    return g if g in GESTOS else "sorpresa"


# ---------------------------------------------------------------------------
# SONIDO Y CAMARA DE CADA GAG: el silbido del yunque que cae y el CLANG, la
# pantalla que tiembla con el golpe, el zoom a la cara cuando se le salen
# los ojos. (nombre, segundo desde que empieza el gag, duracion)
# ---------------------------------------------------------------------------
SONIDOS = {
    "aplasta": [("golpe", 0.07, 0.9), ("clang", 0.45, 1.2), ("muelle", 3.05, 0.8)],
    "de_cara": [("golpe", 0.07, 0.9), ("splat", 0.45, 0.5)],
    "derrite": [("trombon", 0.0, 2.2)],
    "infla": [("estira", 0.0, 1.4)],
    "tiembla": [("traqueteo", 0.0, 2.0)],
    "ojos_fuera": [("muelle", 0.0, 0.8), ("zas", 0.02, 0.3)],
    "vapor": [("vapor", 0.2, 1.8)],
    "alma": [("fantasma", 0.0, 2.6), ("zas", 3.2, 0.3)],
    "zombi": [("grunido", 0.2, 1.6)],
    "cabezada": [("ronquido", 0.5, 1.2), ("zas", 1.8, 0.3), ("ronquido", 3.1, 1.2), ("zas", 4.4, 0.3)],
    "gira": [("whoosh", 0.0, 0.5), ("whoosh", 0.5, 0.5), ("whoosh", 1.0, 0.5), ("whoosh", 1.5, 0.5),
             ("chispa", 2.0, 0.6)],
    "encoge": [("silbato_baja", 0.0, 0.8)],
    "crece": [("silbato_sube", 0.0, 0.9)],
    "sale_volando": [("zas", 0.25, 0.3), ("silbato_sube", 0.3, 0.9), ("chispa", 1.2, 0.5)],
    "llora": [("llanto", 0.0, 2.0)],
    "rayo": [("zap", 0.0, 0.7), ("puf", 0.6, 0.4)],
    "corazon": [("latido", 0.0, 2.8)],
}
# (segundo, fuerza) de los golpes que sacuden la pantalla
IMPACTOS = {
    "aplasta": [(0.45, 1.0), (3.05, 0.35)], "de_cara": [(0.45, 0.8)], "rayo": [(0.0, 0.7), (0.3, 0.5)],
    "sale_volando": [(0.25, 0.6)], "tiembla": [(0.1, 0.3), (0.6, 0.3), (1.1, 0.3)], "ojos_fuera": [(0.05, 0.5)],
    "cabezada": [(1.8, 0.45), (4.4, 0.45)], "vapor": [(0.3, 0.3)], "crece": [(0.6, 0.35)], "alma": [(3.2, 0.4)],
    "corazon": [(0.0, 0.15), (0.45, 0.15), (0.9, 0.15)],
}
# los de la cara: la camara se le acerca (los de cuerpo entero, no)
CERCA = ("ojos_fuera", "vapor", "llora", "rayo", "corazon", "cabezada", "tiembla")


def sonidos(visual: dict, segundos: float) -> list:
    ma = (visual or {}).get("mascota")
    if not isinstance(ma, dict):
        return []
    tipo = tipo_de(ma.get("gag"))
    if not tipo:
        return []
    t0 = empieza(ma["gag"]) if isinstance(ma["gag"], dict) else 0.3
    return [(n, t0 + t, d) for n, t, d in SONIDOS.get(tipo, []) if 0 <= t0 + t < segundos]


def camara(visual: dict) -> tuple[list, float | None]:
    """([(segundo, fuerza)] de los golpes, segundo en que la camara se
    acerca a la cara o None)."""
    ma = (visual or {}).get("mascota")
    if not isinstance(ma, dict):
        return [], None
    tipo = tipo_de(ma.get("gag"))
    if not tipo:
        return [], None
    t0 = empieza(ma["gag"]) if isinstance(ma["gag"], dict) else 0.3
    return [(t0 + t, k) for t, k in IMPACTOS.get(tipo, [])], (t0 if tipo in CERCA else None)
