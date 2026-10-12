"""LO QUE HACEN LOS PERSONAJES CON ALGO O CON ALGUIEN.

Ella: "si dice 'prueba a tocarte el pie con una pluma', tiene que hacerlo".
Un personaje al lado de una pluma no basta: tiene que cogerla, levantar el
pie y hacerse cosquillas. El guion lo pide con "hace":

    "hace": {"verbo": "cosquillas", "a": "pie", "con": "pluma", "cuando": "tickle"}

"a" es una parte de su propio cuerpo ("pie", "barriga", "cabeza", "boca"),
otro personaje ("persona", "mokordo"...; "persona:pie" para su pie) o una
cosa del folio ("perro"). Cada fotograma: primero se calcula como esta cada
personaje, luego aqui se retocan (se acerca al otro, lo mira, la mano va a
donde tiene que ir, el otro reacciona) y despues se pintan.
"""
import math

from . import mascota as M

VERBOS = {
    "cosquillas": "tickles the target with the object in hand (a feather by default): their own foot, "
                  "another character (who laughs and squirms), an animal",
    "toca": "touches / pokes the target with a finger or the object",
    "golpea": "bonks the target, comic (the target flinches)",
    "rasca": "scratches the target (their own head, their own foot...)",
    "da": "gives the object to another character",
    "come": "eats the object: bites, it gets smaller",
    "bebe": "drinks from the object (glass, bottle, cup)",
    "huele": "sniffs the object",
    "lanza": "throws the object at the target (or away)",
    "empuja": "pushes another character, who slides away",
    "abraza": "hugs another character",
    "mira": "looks closely at the target through a magnifying glass",
    "muestra": "holds the object up high, showing it off",
    "fuma": "smokes the object in hand (a cigarette, a vape): puffs, smoke clouds come out, coughs "
            "(only tobacco and vaping)",
    # La vida diaria. Ella: "tiene que aparecer como se limpia la cara, saliendo
    # jabon"... y no solo eso: todo lo que hace un cuerpo en un video de "que
    # pasa si".
    "lava": "washes his face: rubs it with both hands, soap foam and bubbles grow on it, then water "
            "splashes rinse it off (with \"jabon\")",
    "crema": "puts cream on his face: dabs white cream on his cheeks and rubs it in, a little sparkle "
             "(holds \"bote_crema\")",
    "mascarilla": "wears a green face mask with cucumber slices on his eyes, relaxed",
    "cepilla": "brushes his teeth: toothbrush going left-right in his mouth, foam at the mouth",
    "ducha": "takes a shower: water falling on him, foam on his head, rubbing his head",
    "seca": "dries his face with a towel, rubbing",
    "pesas": "lifts a dumbbell up and down, straining, sweat drops",
    "comba": "jumps rope: hops while the rope spins around him",
    "movil": "stares at a phone: blue screen glow on his face, scrolling with the thumb",
    "teclea": "types fast on a laptop in front of him",
    "juega": "plays a video game with a controller, buttons smashing",
    "pastilla": "takes a pill: pops it in his mouth and drinks a glass of water",
    "pesa_se": "steps on a bathroom scale and looks down at the number",
    "termometro": "has a thermometer in his mouth, feeling ill",
    "estornuda": "sneezes: winds up, then ACHOO with a spray of droplets",
    "cocina": "cooks: stirs a pan in front of him, steam rising",
    "atraca": "stuffs his face: eats fast, bite after bite, crumbs flying",
    "despierta": "an alarm clock rings next to him: he jolts awake",
    "acuesta": "sleeps IN a bed: lying down under the blanket, zzz (sleep, night, rest, recovering)",
}
# Con que lo hace si el guion no lo dice.
_CON = {"cosquillas": "pluma", "mira": "lupa", "bebe": "vaso", "come": "manzana", "lanza": "pelota",
        "da": "regalo", "fuma": "cigarrillo", "lava": "jabon", "crema": "bote_crema", "cepilla": "cepillo_dientes",
        "seca": "toalla", "pesas": "pesa", "movil": "movil", "juega": "mando", "pastilla": "pastilla",
        "termometro": "termometro", "atraca": "hamburguesa"}
# A donde va la mano si "a" es otro personaje sin parte.
_PARTE = {"cosquillas": "barriga", "toca": "barriga", "golpea": "cabeza", "rasca": "cabeza", "da": "mano",
          "empuja": "barriga", "abraza": "barriga", "lanza": "barriga", "mira": "cabeza"}
# Si no dice "a": su propio...
_A_SOLO = {"come": "boca", "bebe": "boca", "huele": "boca", "fuma": "boca", "rasca": "cabeza", "cosquillas": "barriga",
           "toca": "barriga"}
# Los de la vida diaria se hacen solos, a si mismo: sin acercarse a nadie.
_SOLO = ("lava", "crema", "mascarilla", "cepilla", "ducha", "seca", "pesas", "comba", "movil", "teclea", "juega",
         "pastilla", "pesa_se", "termometro", "estornuda", "cocina", "atraca", "despierta", "acuesta")
PARTES = ("pie", "barriga", "cabeza", "boca", "mano")
_DE_CERCA = ("cosquillas", "toca", "golpea", "rasca", "da", "empuja", "abraza")
ARRANCA = 1.0          # si no hay "cuando": cuando ya ha entrado
ACERCA = 0.7           # lo que tarda en ir hasta el otro


def que_hace(fig: dict) -> dict | None:
    h = fig.get("hace") if isinstance(fig, dict) else None
    if not isinstance(h, dict) or str(h.get("verbo") or "").lower() not in VERBOS:
        return None
    return h


def objeto_de(fig: dict) -> str | None:
    """Lo que tiene en la mano mientras lo hace (o None)."""
    h = que_hace(fig) or {}
    verbo = str(h.get("verbo") or "").lower()
    con = h.get("con") or fig.get("lleva") or _CON.get(verbo)
    if verbo in ("empuja", "abraza", "rasca") and not h.get("con"):
        return None
    if verbo in ("toca", "golpea") and not h.get("con"):
        return None
    if verbo in ("mascarilla", "ducha", "comba", "teclea", "pesa_se", "estornuda", "cocina", "despierta", "acuesta"):
        return h.get("con")
    return con


def cara(e: dict) -> tuple:
    """(cx, cy, r) de la cara de e en este fotograma, como la pinta mascota."""
    p, h = e["p"], e["h"]
    ancho, alto = M._medidas(h, e["forma"])
    levanta = p.get("levanta", 0.0)*h
    base = e["suelo"] - levanta - h*0.07
    T = lambda q: M._transforma(q, e["cx"], base, p["estira"], p["inclina"]*e["lado"])
    c = T((h*0.02, -alto*(0.7 if e["forma"] == "judia" else 0.58)))
    return c[0], c[1], h*0.17


def _medidas(e):
    ancho, alto = M._medidas(e["h"], e["forma"])
    return ancho*1.1/math.sqrt(e["p"]["estira"]), alto*e["p"]["estira"]


def ancla(e: dict, parte: str, s: int) -> tuple:
    """Un punto del cuerpo de e, del lado s (el que mira a quien llega)."""
    p, h = e["p"], e["h"]
    ancho, alto = M._medidas(h, e["forma"])
    levanta = p.get("levanta", 0.0)*h
    pie_y = e["suelo"] - levanta
    base = pie_y - h*0.07
    T = lambda q: M._transforma(q, e["cx"], base, p["estira"], p["inclina"]*e["lado"])
    if parte == "pie":
        if e.get("pie_arriba") == s:
            x, y = M.pie_levantado(e["cx"], pie_y, h, e["forma"], s)
            return x + s*h*0.02, y - h*0.03
        return e["cx"] + s*ancho*0.55, pie_y - h*0.03
    if parte == "cabeza":
        return T((s*ancho*0.45, -alto*0.92))
    if parte == "boca":
        c = T((h*0.02, -alto*(0.7 if e["forma"] == "judia" else 0.58)))
        return c[0] + s*h*0.07, c[1] + h*0.07
    if parte == "mano":
        return T((s*(ancho*1.0 + h*0.2), -alto*0.3))
    return T((s*ancho*1.0, -alto*0.35))       # barriga


def _objetivo(h: dict, quien: str, estados: list, cosas: dict):
    """(estado del otro o None, parte, punto fijo o None)."""
    verbo = str(h.get("verbo")).lower()
    if verbo in _SOLO:
        return None, None, None
    a = str(h.get("a") or _A_SOLO.get(verbo) or "").lower().strip()
    nombre, _, parte = a.partition(":")
    if nombre in PARTES and not parte:
        return None, nombre, None
    for e in estados:
        if e["quien"] == nombre and e["quien"] != quien:
            return e, parte or _PARTE.get(verbo, "barriga"), None
    if nombre in cosas:
        return None, None, cosas[nombre]
    return None, None, None


def planifica(estados: list, cosas: dict, ancho: int, t: float) -> list:
    """Retoca los estados de este fotograma (acercarse, mirar, mano, pie,
    lo que lleva, como reacciona el otro). Devuelve lo que vuela (lo que se
    lanza) para pintarlo encima de todo."""
    vuelan = []
    planes = []
    # 1) quien hace que, acercarse y mirarle
    for e in estados:
        h = que_hace(e["fig"])
        if not h:
            continue
        verbo = str(h.get("verbo")).lower()
        if h.get("_t") is not None:
            t0 = float(h["_t"])
        elif e["fig"].get("_ya"):
            t0 = 0.2
        else:
            t0 = ARRANCA + float(e["fig"].get("_retraso", 0.0))
        u = t - t0
        otro, parte, fijo = _objetivo(h, e["quien"], estados, cosas)
        planes.append((e, h, verbo, u, otro, parte, fijo))
        if u < 0:
            continue
        hacia = otro["cx"] if otro else (fijo[0] if fijo else None)
        if hacia is not None and abs(hacia - e["cx"]) > 2:
            e["lado"] = 1 if hacia > e["cx"] else -1
        if otro is not None and verbo in _DE_CERCA:
            # Va hasta el otro andando, hasta tenerlo al alcance.
            hueco = _medidas(otro)[0] + _medidas(e)[0] + e["h"]*{"abraza": 0.05, "cosquillas": 0.3}.get(verbo, 0.18)
            meta = otro["cx"] - e["lado"]*hueco
            if abs(meta - e["cx"]) > hueco*0.1 and (meta - e["cx"])*e["lado"] > 0:
                s = M._suave(u/ACERCA)
                e["cx"] += (meta - e["cx"])*s
                if u < ACERCA:
                    e["p"]["piernas"] = u*16
                    e["p"]["levanta"] = e["p"].get("levanta", 0.0) + abs(math.sin(u*16))*0.04
        elif fijo is not None and (verbo in _DE_CERCA or verbo == "mira"):
            meta = fijo[0] - e["lado"]*(_medidas(e)[0] + fijo[2]*0.45 + e["h"]*(0.4 if verbo == "mira" else 0.12))
            if (meta - e["cx"])*e["lado"] > 0:
                e["cx"] += (meta - e["cx"])*M._suave(u/ACERCA)
                if u < ACERCA:
                    e["p"]["piernas"] = u*16
        if parte == "pie" and otro is None and verbo in ("cosquillas", "rasca", "toca"):
            e["pie_arriba"] = e["lado"]
            e["p"]["inclina"] = e["p"]["inclina"]*0.3 + 14*M._suave(u/0.4)
            e["p"]["levanta"] = 0.0
    # 2) como reacciona el otro
    for e, h, verbo, u, otro, parte, fijo in planes:
        v = u - ACERCA
        if otro is None or v < 0:
            continue
        op = otro["p"]
        if verbo == "cosquillas":
            otro["gesto"] = "riendo"
            op["inclina"] = op["inclina"] + 12*math.sin(v*17)
            op["levanta"] = op.get("levanta", 0.0) + abs(math.sin(v*9))*0.08
            otro["cx"] += math.sin(v*31)*otro["h"]*0.015
        elif verbo in ("toca", "golpea"):
            fase = (v % 0.7)/0.7 if verbo == "golpea" else min(1.0, v/0.9)
            if verbo == "golpea" and fase < 0.35 or verbo == "toca" and 0.3 < fase:
                otro["gesto"] = "asustado" if verbo == "golpea" else "sorpresa"
                op["inclina"] = op["inclina"] + e["lado"]*(14 if verbo == "golpea" else 6)
                otro["cx"] += math.sin(v*50)*otro["h"]*(0.012 if verbo == "golpea" else 0.004)
        elif verbo == "empuja":
            otro["cx"] += e["lado"]*otro["h"]*0.55*M._suave(v/1.2)
            e["cx"] += e["lado"]*otro["h"]*0.55*M._suave(v/1.2)
            otro["gesto"] = "sorpresa"
            op["inclina"] = op["inclina"] + e["lado"]*10
        elif verbo == "abraza":
            otro["gesto"] = e["gesto"] = "contento"
            # el otro tambien le rodea con el brazo, por la espalda
            otro["alcanza"] = {-e["lado"]: (e["cx"] - e["lado"]*_medidas(e)[0]*0.6, e["suelo"] - e["h"]*0.38)}
            otro["lado"] = -e["lado"]
        elif verbo == "da" and v > 0.8:
            otro["gesto"] = "contento"
            otro["lado"] = -e["lado"]
        elif verbo == "lanza" and v > 0.95:
            otro["gesto"] = "asustado"
            op["inclina"] = op["inclina"] + e["lado"]*12*math.exp(-(v - 0.95)*3)
    # 3) la mano, el pie y lo que lleva
    for e, h, verbo, u, otro, parte, fijo in planes:
        if u < 0:
            continue
        s = e["lado"]
        v = u - (ACERCA if (otro is not None or fijo is not None) and (verbo in _DE_CERCA or verbo == "mira")
                 else 0.3)
        con = objeto_de(e["fig"])
        e["brazo_lleva"] = False
        meta = None
        if otro is not None:
            meta = ancla(otro, parte, -s)
        elif fijo is not None:
            meta = (fijo[0] - s*fijo[2]*0.3, fijo[1])
        elif parte in PARTES:
            meta = ancla(e, parte, s)
        if v < 0:
            # mientras se acerca: lo lleva por delante
            e["alcanza"] = {s: (e["cx"] + s*(_medidas(e)[0] + e["h"]*0.22), e["suelo"] - e["h"]*0.5)}
            if con:
                e["objeto"] = {"que": con, "modo": "punta", "escala": 0.8}
            continue
        if verbo in ("cosquillas", "rasca"):
            rapido = 19 if verbo == "cosquillas" else 14
            if meta and otro is None and fijo is None and parte == "pie" and con:
                # su propio pie: la mano por encima y delante, la pluma hacia la planta
                pie = (meta[0] + math.cos(v*rapido)*e["h"]*0.03, meta[1] + math.sin(v*rapido*1.3)*e["h"]*0.02)
                e["alcanza"] = {s: (pie[0] + s*e["h"]*0.05, pie[1] - e["h"]*0.2)}
                e["objeto"] = {"que": con, "modo": "punta", "apunta": pie, "escala": 0.75}
                continue
            if meta:
                meta = (meta[0] + math.cos(v*rapido)*e["h"]*0.05, meta[1] + math.sin(v*rapido*1.3)*e["h"]*0.025)
                e["alcanza"] = {s: (meta[0] - s*e["h"]*(0.22 if con else 0.0), meta[1] + (e["h"]*0.04 if con else 0))}
            if con:
                e["objeto"] = {"que": con, "modo": "punta", "apunta": meta, "escala": 0.8}
        elif verbo in ("toca", "golpea"):
            fase = (v % 0.7)/0.7 if verbo == "golpea" else min(1.0, v/0.9)
            ida = math.sin(fase*math.pi) if verbo == "golpea" else M._suave(fase*1.6)
            if meta:
                reposo = (e["cx"] + s*e["h"]*0.3, e["suelo"] - e["h"]*0.5)
                e["alcanza"] = {s: (reposo[0] + (meta[0] - reposo[0])*ida, reposo[1] + (meta[1] - reposo[1])*ida)}
            if con:
                e["objeto"] = {"que": con, "modo": "punta", "apunta": meta}
            if verbo == "golpea":
                e["gesto"] = "enfadado" if e["gesto"] == "neutro" else e["gesto"]
        elif verbo in ("come", "bebe", "huele"):
            if verbo == "bebe":
                e["p"]["inclina"] = e["p"]["inclina"]*0.3 - 10*M._suave(v/0.5)
            else:
                e["p"]["inclina"] *= 0.4
            boca = ancla(e, "boca", s)
            if verbo == "come":
                ciclo = (v % 0.9)/0.9
                cerca = math.sin(min(1.0, ciclo/0.6)*math.pi)
                bocados = int(v/0.9) + (1 if ciclo > 0.3 else 0)
                escala = max(0.25, 1 - 0.2*bocados)
                e["gesto"] = "sorpresa" if 0.15 < ciclo < 0.35 else "contento"
            else:
                cerca, escala = M._suave(v/0.5), 1.0
                e["gesto"] = "contento"
            lejos = (e["cx"] + s*e["h"]*0.42, e["suelo"] - e["h"]*0.4)
            mano = (lejos[0] + (boca[0] + s*e["h"]*0.08 - lejos[0])*cerca, lejos[1] + (boca[1] + e["h"]*0.05 - lejos[1])*cerca)
            e["alcanza"] = {s: mano}
            if con:
                giro = -s*55*cerca if verbo == "bebe" else 0
                e["objeto"] = {"que": con, "modo": "centro", "escala": escala, "giro": giro}
        elif verbo == "fuma":
            # Cada calada: la mano a la boca, aspira (la brasa se enciende),
            # baja la mano y echa el humo. Y entre caladas, el hilo de humo.
            ciclo = (v % 2.6)/2.6
            cerca = math.sin(min(1.0, ciclo/0.45)*math.pi/2) if ciclo < 0.45 else \
                max(0.0, 1 - (ciclo - 0.45)/0.15)
            e["p"]["inclina"] *= 0.4
            if e["gesto"] in ("contento", "riendo"):
                e["gesto"] = "neutro"          # que no parezca que lo disfruta
            boca = ancla(e, "boca", s)
            lejos = (e["cx"] + s*e["h"]*0.45, e["suelo"] - e["h"]*0.38)
            mano = (lejos[0] + (boca[0] + s*e["h"]*0.05 - lejos[0])*cerca,
                    lejos[1] + (boca[1] + e["h"]*0.04 - lejos[1])*cerca)
            e["alcanza"] = {s: mano}
            if 0.3 < ciclo < 0.45:
                e["p"]["estira"] *= 1.04            # aspira
                e["gesto"] = "neutro"
            if con:
                vaper = "vape" in str(con) or con == "vapeador"
                # el cigarro se va gastando: uno entero en unos 12 segundos, y
                # la ceniza crece y se cae cada poco
                consumo = min(0.92, max(0.0, v/12.0))
                ceniza = (v/2.2) % 1.0
                e["objeto"] = {"que": con, "modo": "centro", "escala": 0.75 if not vaper else 0.65,
                               "giro": (0 if s > 0 else 180) if not vaper else -s*70,
                               "desplaza": (s*0.1, 0.0) if not vaper else (0.0, -0.05),
                               "consumo": consumo if not vaper else None, "ceniza": ceniza}
                tam = e["h"]*0.36*0.75
                punta = (mano[0] + s*tam*(0.11 + 0.72*(1 - 0.9*consumo) + 0.06 + 0.22*ceniza), mano[1])
                if not vaper and ceniza < 0.3 and v > 2.2:
                    # la ceniza que se acaba de caer
                    vuelan.append({"que": "ceniza", "pos": (punta[0] - s*tam*0.1, punta[1] + (ceniza/0.3)*e["h"]*0.35),
                                   "tam": tam*0.06})
                if not vaper:
                    for k in range(3):        # el hilo de humo de la punta
                        u2 = ((v*0.8 + k/3) % 1.0)
                        vuelan.append({"que": "humo", "pos": (punta[0] + math.sin(u2*7 + k)*e["h"]*0.03,
                                                              punta[1] - u2*e["h"]*0.4),
                                       "tam": e["h"]*(0.025 + 0.04*u2), "alfa": 0.7*(1 - u2)})
            echa = (v % 2.6) - 2.6*0.6
            if echa > 0:                     # echa el humo: una nube que crece y sube
                for k in range(4):
                    u2 = echa/1.0 - k*0.12
                    if 0 < u2 < 1:
                        vuelan.append({"que": "humo", "pos": (boca[0] + s*e["h"]*(0.08 + u2*0.35),
                                                              boca[1] - u2*e["h"]*0.3 + k*e["h"]*0.02),
                                       "tam": e["h"]*(0.05 + 0.13*u2), "alfa": 0.85*(1 - u2)})
        elif verbo == "mira":
            punto = meta or (e["cx"] + s*e["h"]*0.8, e["suelo"] - e["h"]*0.4)
            # la lupa entre sus ojos y lo que mira
            ojo = ancla(e, "boca", s)
            lupa = (ojo[0] + (punto[0] - ojo[0])*0.45, ojo[1] + (punto[1] - ojo[1])*0.45 - e["h"]*0.05)
            e["alcanza"] = {s: (lupa[0], lupa[1] + e["h"]*0.08)}
            e["gesto"] = "sorpresa"
            e["p"]["inclina"] = e["p"]["inclina"]*0.3 + 10
            if con:
                e["objeto"] = {"que": con, "modo": "centro", "escala": 1.2, "giro": -s*20}
        elif verbo == "muestra":
            sube = M._suave(v/0.4)
            top = e["suelo"] - e["h"]*(0.95 + 0.05*math.sin(v*5))
            e["alcanza"] = {s: (e["cx"] + s*e["h"]*0.3, e["suelo"] - e["h"]*0.45 + (top - e["suelo"] + e["h"]*0.45)*sube)}
            e["gesto"] = "contento"
            if con:
                e["objeto"] = {"que": con, "modo": "centro", "escala": 1.3, "giro": 6*math.sin(v*4)}
        elif verbo == "da":
            pasa = M._suave(v/0.8)
            if meta:
                mitad = ((e["cx"] + meta[0])/2, meta[1])
                e["alcanza"] = {s: mitad if pasa < 1 else (e["cx"] + s*e["h"]*0.3, e["suelo"] - e["h"]*0.5)}
                if pasa >= 1 and otro is not None:
                    otro["alcanza"] = {-s: mitad}
                    otro["brazo_lleva"] = False
                    if con:
                        otro["objeto"] = {"que": con, "modo": "centro"}
                elif con:
                    e["objeto"] = {"que": con, "modo": "centro"}
        elif verbo == "empuja":
            if meta:
                e["alcanza"] = {s: meta, -s: (meta[0], meta[1] - e["h"]*0.08)}
            e["p"]["inclina"] = e["p"]["inclina"]*0.3 + 16
            e["p"]["piernas"] = v*12 if v < 1.2 else None
        elif verbo == "abraza":
            if otro is not None:
                lejos = otro["cx"] + s*_medidas(otro)[0]*0.5
                e["alcanza"] = {s: (lejos, e["suelo"] - e["h"]*0.42)}
                e["p"]["inclina"] = e["p"]["inclina"]*0.3 + 8
        elif verbo in _SOLO:
            vuelan += _vida_diaria(e, verbo, v, con, s)
        elif verbo == "lanza":
            if v < 0.25:          # coge impulso: el brazo atras y arriba
                e["alcanza"] = {s: (e["cx"] - s*e["h"]*0.15, e["suelo"] - e["h"]*0.85)}
                if con:
                    e["objeto"] = {"que": con, "modo": "centro"}
            else:
                e["alcanza"] = {s: (e["cx"] + s*e["h"]*0.45, e["suelo"] - e["h"]*0.6)}
                if con:
                    va = (v - 0.25)/0.7
                    a = (e["cx"] + s*e["h"]*0.45, e["suelo"] - e["h"]*0.7)
                    b = meta or (a[0] + s*ancho, a[1])
                    if va < 1:
                        x = a[0] + (b[0] - a[0])*va
                        y = a[1] + (b[1] - a[1])*va - math.sin(va*math.pi)*e["h"]*0.5
                        vuelan.append({"que": con, "pos": (x, y), "giro": -s*va*540, "tam": e["h"]*0.3})
                    elif otro is not None or fijo is not None:
                        # rebota y se queda en el suelo, al lado
                        caida = min(1.0, (va - 1)/0.5)
                        x = b[0] - s*e["h"]*0.25*caida
                        suelo = (otro["suelo"] if otro else fijo[1] + fijo[2]*0.5) - e["h"]*0.15
                        y = b[1] + (suelo - b[1])*caida**2
                        vuelan.append({"que": con, "pos": (x, y), "giro": -s*(540 + 200*caida), "tam": e["h"]*0.3})
    return vuelan


def _burbujas(cx, cy, r, n, v, semilla, sube=True):
    """n burbujas pegadas a una zona (la cara, la boca, la cabeza) que tiemblan
    y alguna se escapa hacia arriba."""
    sale = []
    for k in range(int(n)):
        a = (k*2.39996 + semilla) % (2*math.pi)
        d = r*(0.35 + 0.6*((k*0.618) % 1.0))
        bx, by = cx + math.cos(a)*d, cy + math.sin(a)*d*0.8
        if sube and k % 4 == 3:
            u = (v*0.7 + k*0.17) % 1.0
            by -= u*r*2.2
            bx += math.sin(u*9 + k)*r*0.2
        sale.append({"que": "burbuja", "pos": (bx + math.sin(v*6 + k)*r*0.03, by), "tam": r*(0.16 + 0.12*((k*7) % 3)/2)})
    return sale


def _gotas(cx, cy, r, v, n=8, hacia=0, cae=True):
    """Gotas de agua que salen disparadas (o caen) desde un punto."""
    sale = []
    for k in range(n):
        u = (v*1.3 + k/n) % 1.0
        a = -math.pi/2 + (k - n/2)*0.35 + hacia
        dist = u*r*2.4
        gx = cx + math.cos(a)*dist
        gy = cy + math.sin(a)*dist + (u*u*r*2.0 if cae else 0)
        sale.append({"que": "agua", "pos": (gx, gy), "tam": r*0.15, "alfa": 1 - u})
    return sale


def _vida_diaria(e: dict, verbo: str, v: float, con, s: int) -> list:
    """Lo que hace solo: lavarse, cepillarse, hacer pesas, mirar el movil...
    Mueve sus manos y su cara, y devuelve lo que sale (espuma, agua, vapor,
    migas...) para pintarlo encima de todo."""
    h = e["h"]
    cx, cy, r = cara(e)
    p = e["p"]
    vu = []
    if verbo == "lava":
        ciclo = v % 4.2
        frota = (math.cos(v*12)*h*0.02, math.sin(v*14)*h*0.015)
        e["alcanza"] = {s: (cx + s*r*0.75 + frota[0], cy + r*0.1 + frota[1]),
                        -s: (cx - s*r*0.75 - frota[0], cy + r*0.15 - frota[1])}
        e["gesto"] = "contento"
        p["inclina"] *= 0.3
        if ciclo < 2.6:           # el jabon: la espuma crece
            vu += _burbujas(cx, cy, r*1.05, 6 + ciclo*9, v, 1.0)
            if v < 0.8 and con:
                e["objeto"] = {"que": con, "modo": "centro", "escala": 0.6}
        else:                     # el aclarado: agua que salpica, la espuma se va
            quedan = max(0, 26 - (ciclo - 2.6)*18)
            vu += _burbujas(cx, cy, r, quedan, v, 1.0, sube=False)
            vu += _gotas(cx, cy - r*0.2, r, v, n=10, cae=True)
    elif verbo == "crema":
        e["gesto"] = "contento"
        dab = (v % 0.9)/0.9
        sitio = int(v/0.9) % 3
        puntos = [(cx - r*0.55, cy + r*0.15), (cx + r*0.55, cy + r*0.15), (cx, cy - r*0.55)]
        px, py = puntos[sitio]
        cerca = math.sin(dab*math.pi)
        lejos = (e["cx"] + s*h*0.4, e["suelo"] - h*0.45)
        e["alcanza"] = {s: (lejos[0] + (px - lejos[0])*cerca, lejos[1] + (py - lejos[1])*cerca)}
        if con:
            e["objeto"] = {"que": con, "modo": "centro", "escala": 0.55}
        for k, (qx, qy) in enumerate(puntos):
            hecha = v/0.9 - k            # cuanto hace que se puso esa
            if hecha > 0:
                vu.append({"que": "crema", "pos": (qx, qy), "tam": r*0.3, "alfa": max(0.0, 1 - hecha/3.5)})
        if v > 3:
            vu.append({"que": "destello", "pos": (cx + r*1.1, cy - r*0.9), "tam": r*0.25*(0.7 + 0.3*math.sin(v*6))})
    elif verbo == "mascarilla":
        e["gesto"] = "contento"
        p["inclina"] = p["inclina"]*0.3 - 6
        capa = min(1.0, v/0.8)
        vu.append({"que": "mascarilla", "pos": (cx, cy + r*0.05), "tam": r*1.15, "alfa": capa})
        if v > 0.5:
            for lado in (-1, 1):
                vu.append({"que": "pepino", "pos": (cx + lado*r*0.36, cy - r*0.12), "tam": r*1.1, "giro": 0})
        vu.append({"que": "zzz", "pos": (cx + r*1.2, cy - r*1.0), "tam": r*0.4, "alfa": 0.5 + 0.5*math.sin(v*2)})
    elif verbo == "cepilla":
        boca = (cx + s*r*0.15, cy + r*0.45)
        e["alcanza"] = {s: (boca[0] + s*r*0.55 + math.sin(v*22)*r*0.18, boca[1] + r*0.12)}
        if con:
            e["objeto"] = {"que": con, "modo": "centro", "escala": 0.55, "giro": 180 if s > 0 else 0,
                           "desplaza": (-s*0.08, -0.02)}
        vu += _burbujas(boca[0], boca[1], r*0.6, 4 + min(14, v*5), v, 2.0)
    elif verbo == "ducha":
        e["gesto"] = "contento"
        e["alcanza"] = {s: (cx + s*r*0.5 + math.sin(v*10)*r*0.15, cy - r*1.05),
                        -s: (cx - s*r*0.5 - math.sin(v*10)*r*0.15, cy - r*1.0)}
        vu += _burbujas(cx, cy - r*1.0, r*0.9, 14, v, 3.0)
        for k in range(16):
            u = (v*1.6 + k/16) % 1.0
            gx = cx + (k - 7.5)*r*0.2 + math.sin(k*3)*r*0.1
            vu.append({"que": "agua", "pos": (gx, cy - r*2.6 + u*h*0.9), "tam": r*0.12, "alfa": 0.9})
    elif verbo == "seca":
        roza = math.sin(v*9)*r*0.35
        e["alcanza"] = {s: (cx + roza + s*r*0.2, cy + r*0.1), -s: (cx + roza - s*r*0.2, cy + r*0.2)}
        e["gesto"] = "contento"
        if con:
            e["objeto"] = {"que": con, "modo": "centro", "escala": 0.9, "giro": math.sin(v*9)*12}
    elif verbo == "pesas":
        ciclo = (v % 1.3)/1.3
        sube = math.sin(ciclo*math.pi)
        e["alcanza"] = {s: (e["cx"] + s*h*0.42, e["suelo"] - h*(0.4 + 0.55*sube))}
        e["gesto"] = "enfadado" if sube > 0.5 else "neutro"
        p["estira"] *= 1 - 0.03*sube
        if con:
            e["objeto"] = {"que": con, "modo": "centro", "escala": 0.7}
        if v > 1.5:
            vu += [{"que": "agua", "pos": (cx - s*r*(1.0 + 0.4*u), cy - r*0.6 - r*math.sin(u*math.pi)), "tam": r*0.09,
                    "alfa": 1 - u, "sudor": True} for u in [((v*0.9 + k*0.33) % 1.0) for k in range(3)]]
    elif verbo == "comba":
        fase = (v*2.2) % 1.0
        p["levanta"] = p.get("levanta", 0.0) + max(0.0, math.sin(fase*math.pi))*0.12
        e["alcanza"] = {s: (e["cx"] + s*h*0.38, e["suelo"] - h*0.35), -s: (e["cx"] - s*h*0.38, e["suelo"] - h*0.35)}
        vu.append({"que": "comba_arco", "pos": (e["cx"], e["suelo"] - h*0.35 - p["levanta"]*h), "tam": h,
                   "fase": fase, "ancho": h*0.38})
    elif verbo == "movil":
        e["gesto"] = "neutro"
        p["inclina"] = p["inclina"]*0.3 + 6
        movil = (cx + s*r*0.9, cy + r*0.9)
        e["alcanza"] = {s: movil}
        if con:
            e["objeto"] = {"que": con, "modo": "centro", "escala": 0.5}
        e["mira"] = (movil[0], movil[1] - h*0.05)
        vu.append({"que": "pantalla", "pos": (movil[0], movil[1] - h*0.04), "tam": r, "hacia": (cx, cy)})
    elif verbo == "teclea":
        mesa = (e["cx"] + s*h*0.42, e["suelo"] - h*0.42)
        e["alcanza"] = {s: (mesa[0] + s*h*0.05, mesa[1] - abs(math.sin(v*16))*h*0.04),
                        -s: (mesa[0] - s*h*0.06, mesa[1] - abs(math.cos(v*16))*h*0.04)}
        e["mira"] = mesa
        vu.append({"que": "portatil", "pos": (mesa[0], mesa[1] - h*0.12), "tam": h*0.42, "giro": 0})
    elif verbo == "juega":
        mando = (cx + s*r*0.4, cy + r*1.6)
        tiembla = math.sin(v*30)*r*0.05
        e["alcanza"] = {s: (mando[0] + s*r*0.35, mando[1] + tiembla), -s: (mando[0] - s*r*0.35, mando[1] - tiembla)}
        e["gesto"] = "sorpresa" if (v % 2.0) < 0.4 else "contento"
        vu.append({"que": "mando", "pos": (mando[0], mando[1]), "tam": r*1.0, "giro": 0})
    elif verbo == "pastilla":
        boca = (cx + s*r*0.2, cy + r*0.45)
        lejos = (e["cx"] + s*h*0.42, e["suelo"] - h*0.4)
        if v < 1.0:
            cerca = math.sin(min(1.0, v/0.6)*math.pi/2) if v < 0.6 else max(0.0, 1 - (v - 0.6)/0.4)
            e["alcanza"] = {s: (lejos[0] + (boca[0] - lejos[0])*cerca, lejos[1] + (boca[1] - lejos[1])*cerca)}
            if v < 0.6:
                e["objeto"] = {"que": con or "pastilla", "modo": "centro", "escala": 0.35}
        else:
            cerca = M._suave((v - 1.0)/0.5)
            e["alcanza"] = {s: (lejos[0] + (boca[0] + s*r*0.2 - lejos[0])*cerca, lejos[1] + (boca[1] - lejos[1])*cerca)}
            e["objeto"] = {"que": "vaso", "modo": "centro", "escala": 0.6, "giro": -s*55*cerca}
            p["inclina"] = p["inclina"]*0.3 - 10*cerca
    elif verbo == "pesa_se":
        vu.append({"que": "bascula", "pos": (e["cx"], e["suelo"] + h*0.01), "tam": h*0.55, "giro": 0, "suelo": True})
        e["mira"] = (e["cx"] + s*h*0.1, e["suelo"])
        p["inclina"] = p["inclina"]*0.3 + 8
        p["levanta"] = 0.03
        if v > 1.2:
            e["gesto"] = "asustado"
            vu.append({"que": "numero", "pos": (e["cx"] + s*h*0.5, e["suelo"] - h*0.15),
                       "tam": h*0.12, "texto": "?!"})
    elif verbo == "termometro":
        e["gesto"] = "triste"
        boca = (cx + s*r*0.3, cy + r*0.45)
        if con:
            e["objeto"] = {"que": con, "modo": "centro", "escala": 0.5, "giro": -s*70}
        e["alcanza"] = {s: (boca[0] + s*r*0.6, boca[1] + r*0.1)}
        if v > 1.0:
            vu += [{"que": "agua", "pos": (cx - s*r*1.05, cy - r*0.5 + ((v*0.7) % 1.0)*r*0.8), "tam": r*0.1, "alfa": 1.0,
                    "sudor": True}]
    elif verbo == "estornuda":
        ciclo = v % 2.6
        if ciclo < 1.0:          # se le viene: echa la cabeza atras
            p["inclina"] = p["inclina"]*0.3 - 14*M._suave(ciclo)
            e["gesto"] = "sorpresa"
        else:                     # ¡achis!
            u = min(1.0, (ciclo - 1.0)/0.9)
            p["inclina"] = p["inclina"]*0.3 + 16*(1 - u)
            e["gesto"] = "grito"
            boca = (cx + s*r*0.6, cy + r*0.4)
            for k in range(12):
                a = (k - 6)*0.12
                d_ = u*h*(0.5 + 0.3*((k*7) % 3)/2)
                vu.append({"que": "agua", "pos": (boca[0] + s*math.cos(a)*d_, boca[1] + math.sin(a)*d_ + u*u*h*0.1),
                           "tam": r*0.12, "alfa": 1 - u})
            vu.append({"que": "humo", "pos": (boca[0] + s*u*h*0.35, boca[1]), "tam": h*(0.05 + 0.12*u),
                       "alfa": 0.7*(1 - u)})
            if u < 0.6:
                vu.append({"que": "numero", "pos": (boca[0] + s*h*0.45, cy - r*1.2), "tam": h*0.13, "texto": "ACHOO!"})
    elif verbo == "cocina":
        sarten = (e["cx"] + s*h*0.5, e["suelo"] - h*0.38)
        e["alcanza"] = {s: (sarten[0] + math.cos(v*6)*h*0.05, sarten[1] - h*0.05 + math.sin(v*6)*h*0.02)}
        e["mira"] = sarten
        vu.append({"que": con if con in ("sarten", "olla") else "sarten", "pos": sarten, "tam": h*0.45, "giro": 0})
        for k in range(3):
            u = (v*0.6 + k/3) % 1.0
            vu.append({"que": "humo", "pos": (sarten[0] - h*0.05 + math.sin(u*7 + k)*h*0.04, sarten[1] - h*0.08 - u*h*0.5),
                       "tam": h*(0.03 + 0.06*u), "alfa": 0.6*(1 - u)})
    elif verbo == "atraca":
        ciclo = (v % 0.5)/0.5
        cerca = math.sin(min(1.0, ciclo/0.6)*math.pi)
        boca = (cx + s*r*0.3, cy + r*0.45)
        lejos = (e["cx"] + s*h*0.4, e["suelo"] - h*0.42)
        e["alcanza"] = {s: (lejos[0] + (boca[0] - lejos[0])*cerca, lejos[1] + (boca[1] - lejos[1])*cerca)}
        e["gesto"] = "sorpresa" if 0.2 < ciclo < 0.45 else "contento"
        if con:
            e["objeto"] = {"que": con, "modo": "centro", "escala": max(0.3, 0.85 - 0.06*int(v/0.5))}
        for k in range(5):
            u = (v*1.8 + k/5) % 1.0
            vu.append({"que": "miga", "pos": (boca[0] + s*u*h*0.25 + (k - 2)*h*0.02, boca[1] + u*u*h*0.35),
                       "tam": r*0.13})
    elif verbo == "acuesta":
        # En la cama, de frente como en los dibujos animados: el cabecero y la
        # almohada detras, la manta por delante hasta el pecho, los ojos
        # cerrados y las zetas. Respira despacio.
        p["inclina"] = 0.0
        p["levanta"] = 0.0
        p["estira"] = 1.0 + 0.025*math.sin(v*2.2)
        e["gesto"] = "contento"
        e["alcanza"] = {}
        e["debajo"] = [{"que": "cabecero", "pos": (e["cx"], e["suelo"]), "tam": h}]
        vu.append({"que": "manta", "pos": (e["cx"], e["suelo"]), "tam": h})
        vu.append({"que": "zzz", "pos": (e["cx"] + h*0.35, e["suelo"] - h*0.85 - 0.04*h*math.sin(v*2)),
                   "tam": h*0.14, "alfa": 1.0})
    elif verbo == "despierta":
        reloj = (e["cx"] + s*h*0.55, e["suelo"] - h*0.05)
        tiembla = math.sin(v*40)*h*0.01 if v < 2.5 else 0.0
        vu.append({"que": con or "despertador", "pos": (reloj[0] + tiembla, reloj[1] - h*0.12), "tam": h*0.3,
                   "giro": tiembla*2})
        if v < 2.5:
            vu.append({"que": "ring", "pos": (reloj[0], reloj[1] - h*0.25), "tam": h*0.18, "fase": v})
        if 0.4 < v < 0.8:
            p["levanta"] = p.get("levanta", 0.0) + 0.25*math.sin((v - 0.4)/0.4*math.pi)
            e["gesto"] = "asustado"
        elif v >= 0.8:
            e["gesto"] = "bostezo" if v > 1.6 else "sorpresa"
    return vu


def sonidos(visual: dict, segundos: float) -> list:
    """El zas de cada golpe y el whoosh de lo que se lanza."""
    salida = []
    quienes = []
    if isinstance(visual.get("mascota"), dict):
        quienes.append(visual["mascota"])
    quienes += [f for f in visual.get("figuras") or [] if isinstance(f, dict)]
    for i, fig in enumerate(quienes):
        h = que_hace(fig)
        if not h:
            continue
        verbo = str(h["verbo"]).lower()
        t0 = float(h["_t"]) if h.get("_t") is not None else (0.2 if fig.get("_ya") else ARRANCA + 0.22*i)
        cerca = ACERCA if verbo in _DE_CERCA else 0.3
        if verbo == "golpea":
            k = 0
            while t0 + cerca + 0.25 + k*0.7 < segundos and k < 6:
                salida.append(("zas", max(0.0, t0 + cerca + 0.25 + k*0.7), 0.3))
                k += 1
        elif verbo == "lanza":
            salida.append(("whoosh", max(0.0, t0 + cerca + 0.25), 0.4))
        elif verbo == "da":
            salida.append(("pop", max(0.0, t0 + cerca + 0.8), 0.25))
        elif verbo == "come":
            for k in range(4):
                salida.append(("pop", max(0.0, t0 + cerca + 0.3 + k*0.9), 0.15))
        elif verbo in ("lava", "ducha", "cepilla"):
            for k in range(6):          # las burbujas
                salida.append(("pop", t0 + 0.3 + 0.35 + k*0.45, 0.12))
        elif verbo == "estornuda":
            k = 0
            while t0 + 0.3 + 1.0 + k*2.6 < segundos and k < 3:
                salida.append(("puf", t0 + 0.3 + 1.0 + k*2.6, 0.4))
                k += 1
        elif verbo == "despierta":
            salida.append(("campana", t0 + 0.3, 1.8))
        elif verbo == "atraca":
            for k in range(6):
                salida.append(("pop", t0 + 0.3 + 0.2 + k*0.5, 0.12))
        elif verbo == "comba":
            for k in range(6):
                salida.append(("boing", t0 + 0.3 + k*0.45, 0.2))
    return [s for s in salida if 0 <= s[1] < segundos]
