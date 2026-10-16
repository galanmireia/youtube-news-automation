"""PASS IT ON — tercer corto de STILL BURNING (sin voz).

El padre le pasa su llama al hijo de pequeño juntando las cabezas. El hijo
crece, se va a la ciudad y nunca tiene tiempo de llamar. La llama del padre
se va haciendo pequeña. Al final el hijo vuelve y se la devuelve.

Lo aprendido con BURNOUT (la mitad se iba en los primeros 30 s): empieza por
el plano mas fuerte - la llama del padre casi apagada y "12 missed calls" -
y luego vuelve atras. Sin nada delicado: nadie muere, se le devuelve el fuego.

  padre: palo 0.80 (de joven) -> 0.66 -> 0.55; llama 1.0 -> 0.55 -> 0.25 -> 0.1
"""
import math, random, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corto as C
import one_more as M
import burnout as B
from corto import T, suave, parpadeo, fuente

OUT = str(Path(__file__).resolve().parent) + "/salida/"
FPS = 25
CW, CH = C.CW, C.CH
VW, VH = 1920, 1080
ROJO_P = (176, 46, 42)              # la cabeza del padre: un rojo algo mas apagado
CALIDO = (255, 186, 110)
H_AD, H_NI = 560, 330               # adulto y niño
LENTO = 1.1

# ---------------------------------------------------------------- personajes
def centro_cabeza(cab, h):
    r = h*0.13
    return cab[0], cab[1] + r*1.3, r

def gafas(d, hx, hy, r, dirx=0.0, g=4):
    s = r*1.5
    ex0 = hx + dirx*s*0.16
    rr = s*0.25
    for lado in (-1, 1):
        ex = ex0 + lado*s*0.32; ey = hy - r*0.05
        d.ellipse([ex - rr, ey - rr, ex + rr, ey + rr], outline=T, width=g)
    d.line([(ex0 - s*0.32 + rr, hy - r*0.1), (ex0 + s*0.32 - rr, hy - r*0.1)], fill=T, width=g)
    for lado in (-1, 1):
        d.line([(ex0 + lado*(s*0.32 + rr), hy - r*0.12), (hx + lado*r*0.97, hy - r*0.24)], fill=T, width=g)

def padre(img, cx, cadera, suelo, h, st, t):
    """El padre: palo mas corto, cabeza mas apagada, un poco encorvado y con gafas."""
    s = dict(palo=0.8, cabeza=ROJO_P, ceja=0.12)
    s.update(st)
    cab, mano = C.cerilla(img, cx, cadera, suelo, h, s, t)
    if not s.get("espalda"):
        hx, hy, r = centro_cabeza(cab, h)
        hx = cab[0]
        gafas(ImageDraw.Draw(img), hx, hy, r, s.get("dir", 0.0), max(3, int(h*0.009)))
    return cab, mano

def nino(img, cx, suelo, st, t, h=H_NI):
    s = dict(palo=1.0)
    s.update(st)
    return C.cerilla(img, cx, suelo - 0.2*h, suelo, h, s, t)

def hijo(img, cx, suelo, st, t, h=H_AD, cadera=None):
    s = dict(palo=1.0)
    s.update(st)
    return C.cerilla(img, cx, cadera if cadera is not None else suelo - 0.2*h, suelo, h, s, t)

def cabeza_suelta(img, hx, hy, r, color, llama, t, gafas_=False, **ojos):
    """Una cabeza de cerca, con su trozo de palo: para los planos de juntar las llamas."""
    d = ImageDraw.Draw(img)
    a = r*0.38
    d.polygon([(hx - a, hy + r*0.6), (hx + a, hy + r*0.6), (hx + a, CH + 20), (hx - a, CH + 20)], fill=(236, 228, 210), outline=T)
    d.line([(hx - a, hy + r*0.6), (hx - a, CH + 20)], fill=T, width=max(4, int(r*0.06)))
    d.line([(hx + a, hy + r*0.6), (hx + a, CH + 20)], fill=T, width=max(4, int(r*0.06)))
    if llama > 0.02:
        C.llama(d, hx, hy - r*1.0, r*1.5*llama, t)
    d.ellipse([hx - r, hy - r*1.15, hx + r, hy + r*0.95], fill=color, outline=T, width=max(5, int(r*0.06)))
    C.ojos(d, hx, hy - r*0.05, r*1.5, color, **ojos)
    if gafas_:
        gafas(d, hx, hy, r, ojos.get("dirx", 0.0), max(4, int(r*0.05)))

# ---------------------------------------------------------------- objetos
def sillon(img, cx, suelo, w, parte):
    d = ImageDraw.Draw(img); col, osc = (88, 88, 94), (66, 66, 72)
    if parte == "detras":
        d.rounded_rectangle([cx - w*0.5, suelo - w*1.12, cx + w*0.5, suelo - w*0.3], radius=int(w*0.2), fill=col, outline=T, width=5)
        d.rounded_rectangle([cx - w*0.4, suelo - w*1.02, cx + w*0.4, suelo - w*0.45], radius=int(w*0.16), fill=(96, 96, 102))
        d.rounded_rectangle([cx - w*0.48, suelo - w*0.45, cx + w*0.48, suelo - w*0.14], radius=int(w*0.08), fill=osc, outline=T, width=5)
        for lado in (-1, 1):
            d.rectangle([cx + lado*w*0.42 - 10, suelo - w*0.14, cx + lado*w*0.42 + 10, suelo], fill=(40, 40, 44))
    else:
        for lado in (-1, 1):
            x = cx + lado*w*0.5
            d.rounded_rectangle([x - w*0.13, suelo - w*0.66, x + w*0.13, suelo - w*0.12], radius=int(w*0.08), fill=col, outline=T, width=5)

def mesita(img, cx, suelo, h, lampara=True, luz_lampara=0.0, telefono=False):
    d = ImageDraw.Draw(img)
    y = suelo - h*0.5
    d.rectangle([cx - h*0.22, y, cx + h*0.22, y + h*0.04], fill=(120, 116, 110), outline=T, width=4)
    for lado in (-1, 1):
        d.line([(cx + lado*h*0.18, y + h*0.04), (cx + lado*h*0.2, suelo)], fill=T, width=6)
    if lampara:
        d.line([(cx - h*0.08, y), (cx - h*0.08, y - h*0.28)], fill=T, width=6)
        d.polygon([(cx - h*0.17, y - h*0.26), (cx + h*0.01, y - h*0.26), (cx - h*0.03, y - h*0.4), (cx - h*0.13, y - h*0.4)],
                  fill=(236, 230, 214) if luz_lampara else (190, 188, 182), outline=T)
    if telefono:
        d.rounded_rectangle([cx + h*0.04, y - h*0.025, cx + h*0.16, y], radius=4, fill=(20, 20, 24), outline=T, width=2)

def arbolito(d, cx, suelo, h):
    """Un arbol de Navidad pequeño, en gris: el color solo es de las cerillas."""
    for k, (w, y0) in enumerate(((0.36, 0.42), (0.28, 0.66), (0.2, 0.88))):
        d.polygon([(cx - h*w, suelo - h*(y0 - 0.3)), (cx + h*w, suelo - h*(y0 - 0.3)), (cx, suelo - h*(y0 + 0.08))],
                  fill=(92, 96, 92), outline=T)
    d.rectangle([cx - h*0.05, suelo - h*0.12, cx + h*0.05, suelo], fill=(70, 66, 62), outline=T, width=3)
    rnd = random.Random(4)
    for _ in range(9):
        y = suelo - h*rnd.uniform(0.2, 0.8); w = h*0.3*(1 - (suelo - y)/h)
        x = cx + rnd.uniform(-w, w)
        d.ellipse([x - h*0.025, y - h*0.025, x + h*0.025, y + h*0.025], fill=(225, 225, 228), outline=T, width=2)
    d.regular_polygon((cx, suelo - h*0.96, h*0.06), 5, fill=(240, 240, 236), outline=T)

def tarta(d, cx, base, s, vela_encendida, t):
    d.rounded_rectangle([cx - s*0.5, base - s*0.36, cx + s*0.5, base], radius=int(s*0.06), fill=(238, 234, 226), outline=T, width=4)
    d.line([(cx - s*0.5, base - s*0.22), (cx + s*0.5, base - s*0.22)], fill=(170, 166, 160), width=5)
    d.rectangle([cx - s*0.035, base - s*0.62, cx + s*0.035, base - s*0.36], fill=(250, 250, 248), outline=T, width=3)
    if vela_encendida > 0.02:
        C.llama(d, cx, base - s*0.62, s*0.22*vela_encendida, t)

def caja_carton(d, x, y, w):
    d.rectangle([x - w/2, y - w*0.36, x + w/2, y + w*0.3], fill=(176, 160, 132), outline=T, width=4)
    d.line([(x - w/2, y - w*0.14), (x + w/2, y - w*0.14)], fill=(150, 134, 108), width=3)

def foto(img, cx, cy, w, inclina=0.0):
    """El marco de fotos: las dos cabezas juntas, el padre encendiendo al niño."""
    W, H = int(w), int(w*0.78)
    pic = Image.new("RGB", (1200, 936), (226, 218, 200))
    pic = C.luz(pic, 600, 380, 520, 0.4, (255, 214, 160))
    cabeza_suelta(pic, 790, 470, 230, ROJO_P, 1.0, 0.3, gafas_=True, feliz=1.0, dirx=-0.5)
    cabeza_suelta(pic, 430, 560, 160, C.ROJO, 1.0, 0.7, feliz=1.0, dirx=0.5)
    pic = Image.blend(pic, Image.new("RGB", pic.size, (214, 196, 160)), 0.18).resize((W, H), Image.LANCZOS)
    marco = Image.new("RGB", (W + 40, H + 40), (60, 58, 56))
    marco.paste(pic, (20, 20))
    ImageDraw.Draw(marco).rectangle([0, 0, W + 39, H + 39], outline=T, width=6)
    ImageDraw.Draw(marco).rectangle([18, 18, W + 21, H + 21], outline=T, width=3)
    if inclina:
        marco = marco.convert("RGBA").rotate(inclina, expand=True, resample=Image.BICUBIC)
        img.paste(marco, (int(cx - marco.width/2), int(cy - marco.height/2)), marco)
    else:
        img.paste(marco, (int(cx - marco.width/2), int(cy - marco.height/2)))

def viento(d, lt, fuerza=1.0, semilla=3):
    rnd = random.Random(semilla)
    for i in range(int(16*fuerza)):
        y = rnd.uniform(120, 760); L = rnd.uniform(140, 300); v = rnd.uniform(900, 1500)
        x = (rnd.uniform(0, CW + 600) - v*lt) % (CW + 600) - 300
        d.line([(x, y), (x + L, y - 6)], fill=(120, 120, 128), width=5)
        d.arc([x - 30, y - 34, x + 30, y + 4], 90, 250, fill=(120, 120, 128), width=5)

def pantalla_bloqueo(texto_hora, aviso):
    def ui(pant):
        W, H = pant.size; p = ImageDraw.Draw(pant)
        p.rectangle([0, 0, W, H], fill=(22, 22, 26))
        p.text((W/2, H*0.2), texto_hora, font=fuente(W*0.165), fill=(245, 245, 245), anchor="mm")
        p.rounded_rectangle([W*0.06, H*0.36, W*0.94, H*0.52], radius=26, fill=(62, 62, 68))
        p.ellipse([W*0.1, H*0.395, W*0.1 + H*0.085, H*0.48], fill=(205, 60, 50))
        p.text((W*0.1 + H*0.0425, H*0.437), "✆", font=fuente(W*0.08), fill=(250, 250, 250), anchor="mm")
        p.text((W*0.12 + H*0.1, H*0.405), "Dad", font=fuente(W*0.075), fill=(250, 250, 250), anchor="lm")
        p.text((W*0.12 + H*0.1, H*0.465), aviso, font=fuente(W*0.06), fill=(200, 200, 206), anchor="lm")
    return ui

def bg_salon(noche=0.0):
    img = M.bg("salon", claro=0.04)
    return M.oscurece(img, noche) if noche else img

def puerta_casa(img, x, suelo, abre=0.0):
    """La fachada de la casa del padre de noche: la puerta, su ventanita y la luz del porche."""
    d = ImageDraw.Draw(img)
    w, h = 300, 560
    x0, y0 = x - w/2, suelo - h
    if abre > 0:
        img2 = C.luz(img, x, suelo - h*0.45, 420*abre, 0.5*abre, CALIDO)
        img.paste(img2)
        d = ImageDraw.Draw(img)
        d.rectangle([x0, y0, x0 + w, suelo], fill=(250, 214, 160))
    ancho = w*(1 - 0.85*abre)
    d.rectangle([x0, y0, x0 + ancho, suelo], fill=(96, 90, 84), outline=T, width=6)
    if abre < 0.5:
        for k in range(2):
            d.rectangle([x0 + ancho*0.16, y0 + 50 + k*250, x0 + ancho*0.84, y0 + 220 + k*250], outline=(70, 66, 62), width=5)
        d.ellipse([x0 + ancho*0.82 - 14, suelo - h*0.48 - 14, x0 + ancho*0.82 + 14, suelo - h*0.48 + 14], fill=(200, 196, 186), outline=T, width=3)
    d.rectangle([x0 - 30, y0 - 26, x0 + w + 30, y0], fill=(70, 70, 74), outline=T, width=5)
    d.rectangle([x0 - 50, suelo, x0 + w + 50, suelo + 26], fill=(110, 110, 114), outline=T, width=4)

def fachada(abre=0.0):
    img = Image.new("RGB", (CW, CH), (40, 42, 50))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, CW, 760], fill=(64, 64, 70))
    rnd = random.Random(2)
    for fila in range(16):
        for col in range(18):
            x = col*96 + (48 if fila % 2 else 0); y = fila*48
            d.rectangle([x, y, x + 92, y + 44], outline=(56, 56, 62), width=3)
    d.rectangle([0, 760, CW, CH], fill=(52, 52, 58))
    # la ventana del salon, con luz tenue
    d.rectangle([180, 240, 520, 560], fill=(150, 130, 100), outline=T, width=8)
    d.line([(350, 240), (350, 560)], fill=T, width=6); d.line([(180, 400), (520, 400)], fill=T, width=6)
    img = C.luz(img, 980, 160, 160, 0.5, (250, 240, 210))
    d = ImageDraw.Draw(img)
    d.ellipse([960, 140, 1000, 180], fill=(250, 246, 226), outline=T, width=3)
    puerta_casa(img, 980, 760, abre)
    return img

# ---------------------------------------------------------------- los planos
def p_arranque(lt, t):
    """Lo primero que se ve: la llama del padre, diminuta, temblando en la oscuridad."""
    img = M.oscurece(bg_salon(), 0.86)
    tiembla = 0.3 + 0.06*math.sin(lt*7) + 0.04*math.sin(lt*17)
    st = dict(palo=0.55, llama=tiembla, cansancio=0.75, ceja=0.5, mira=(0.6, -0.2), dir=0.4, sin_piernas=True,
              parpadeo=parpadeo(lt, 4.4, 2.0))
    tmp = img.copy(); cab, _ = padre(tmp, 800, 960, 2000, 1250, st, t)
    img = C.luz(img, cab[0], cab[1] + 40, 360, 0.18, CALIDO)
    sillon(img, 800, 1560, 1050, "detras")
    padre(img, 800, 960, 2000, 1250, st, t)
    return img, (800, 450, 1.0 + 0.012*lt)

def p_llamadas_perdidas(lt, t, hora="11:48 PM"):
    img = M.oscurece(C.recorte(B.bg_ofi(noche=0.6), 800, 600, 2.0).filter(ImageFilter.GaussianBlur(8)), 0.2)
    M.movil_grande(img, 800, 470, 780, "negro", lt, fondo_pantalla=pantalla_bloqueo(hora, "12 missed calls"))
    return img, (800, 460, 1.0 + 0.02*lt)

def p_titulo(lt, t, dur=2.8):
    img = Image.new("RGB", (CW, CH), (8, 8, 10)); d = ImageDraw.Draw(img)
    a = suave(lt/0.6)*suave((dur - lt)/0.5); c = int(8 + 240*a)
    d.text((CW/2, CH/2), "PASS IT ON", font=fuente(110), fill=(c, c, c), anchor="mm")
    return img, (CW/2, CH/2, 1.0)

def tarjeta(texto):
    return lambda lt, t: M.tarjeta(lt, 2.0, texto, 66)

SUELO_CUARTO = 860
def cuarto_nino(lt, t, enciende):
    """El niño, sin encender, en su cuarto a oscuras. Entra el padre y se agacha."""
    img = M.oscurece(C.fondo("noche"), 0.15 if enciende else 0.0)
    kx = 600
    k_llega = suave(lt/2.6)
    fx = 1500 - (1500 - 735)*k_llega
    agacha = suave((lt - 2.8)/0.8)
    st_p = dict(palo=0.8, llama=1.0, pose="anda" if lt < 2.6 else "caido", fase=lt*7 if lt < 2.6 else None,
                dir=-0.7, mira=(-0.7, 0.4*agacha), inclina=-0.13*agacha, feliz=1.0 if lt > 3.6 else 0.0)
    cad_p = SUELO_CUARTO - 0.2*H_AD + 125*agacha
    st_n = dict(llama=enciende, cansancio=0.0, mira=(0.8, -0.3) if lt > 1.2 else (0, 0.3),
                dir=0.5 if lt > 1.2 else 0.0, sorpresa=1.0 if 0.0 < enciende < 1.0 or (enciende >= 1 and lt < 0.8) else 0.0,
                feliz=1.0 if enciende >= 1 and lt >= 0.8 else 0.0, ceja=0.3 if enciende == 0 else 0.0)
    tmp = img.copy(); cab, _ = padre(tmp, fx, cad_p, SUELO_CUARTO, H_AD, st_p, t)
    img = C.luz(img, cab[0], cab[1] + 60, 300, 0.32, CALIDO)
    if enciende:
        img = C.luz(img, kx, SUELO_CUARTO - 260, 260*enciende, 0.3*enciende, CALIDO)
    nino(img, kx, SUELO_CUARTO, st_n, t)
    padre(img, fx, cad_p, SUELO_CUARTO, H_AD, st_p, t)
    return img, (760, 520, 1.12)

def p_cuarto(lt, t):
    return cuarto_nino(lt, t, 0.0)

def p_cuarto_luz(lt, t):
    img = M.oscurece(C.fondo("noche"), 0.25)
    kx, fx = 600, 840
    salta = abs(math.sin(lt*5))*26 if 0.6 < lt < 2.2 else 0
    img = C.luz(img, 720, SUELO_CUARTO - 300, 420, 0.4, CALIDO)
    nino(img, kx, SUELO_CUARTO - salta, dict(llama=1.0, feliz=1.0, dir=0.5, mira=(0.6, -0.4),
                                              pose="arriba" if salta else "caido"), t)
    padre(img, fx, SUELO_CUARTO - 0.2*H_AD, SUELO_CUARTO, H_AD, dict(palo=0.8, llama=1.0, feliz=1.0, dir=-0.6, mira=(-0.6, 0.4)), t)
    return img, (720, 520, 1.12)

def p_juntan(lt, t, dur=4.5):
    """De cerca: las dos cabezas se tocan y la llama pasa del padre al niño."""
    img = M.oscurece(C.recorte(C.fondo("noche"), 760, 520, 2.4).filter(ImageFilter.GaussianBlur(10)), 0.35)
    junta = suave(lt/0.9)
    prende = suave((lt - 1.2)/0.5)
    nx, ny, nr = 650 + 40*junta, 520, 150
    px, py, pr = 1130 - 60*junta, 430, 210
    img = C.luz(img, px, py - 240, 360, 0.3, CALIDO)
    if prende:
        img = C.luz(img, nx, ny - 200, 340*prende, 0.35*prende, CALIDO)
    cabeza_suelta(img, px, py, pr, ROJO_P, 1.0, t, gafas_=True, feliz=1.0 if lt > 2.2 else 0.0, dirx=-0.5, mira=(-0.6, 0.3))
    cabeza_suelta(img, nx, ny, nr, C.ROJO, prende, t, dirx=0.5, mira=(0.5, -0.4),
                  sorpresa=1.0 if 1.2 < lt < 2.6 else 0.0, feliz=1.0 if lt >= 2.6 else 0.0)
    if 1.0 < lt < 1.8:
        M.chispas(ImageDraw.Draw(img), (nx + px)/2, ny - nr*0.8, ((lt - 1.0)*3) % 1.0, 140, semilla=int(lt*10))
    if 1.2 < lt < 1.45:
        img = M.oscurece(img, 0.35*(1 - (lt - 1.2)/0.25), (255, 240, 220))
    return img, (860, 450, 1.0 + 0.02*lt)

def p_viento(lt, t):
    """Calle con viento. El padre tapa con la mano la llamita del niño; la suya tiembla."""
    img = M.bg("calle", claro=0.05)
    d = ImageDraw.Draw(img)
    para = lt > 2.8
    x = 380 + 110*min(lt, 2.8)
    fuerza = suave((lt - 1.0)/1.0)
    viento(d, lt, fuerza*1.2)
    rnd = random.Random(int(t*14))
    tapa = suave((lt - 3.2)/0.7)
    llama_n = 0.9 - fuerza*(1 - tapa)*rnd.uniform(0.2, 0.6)
    llama_p = 0.95 - fuerza*rnd.uniform(0.1, 0.55)
    kx, fx = x, x + 200
    fase = lt*7 if not para else None
    agacha = suave((lt - 2.9)/0.6)
    st_n = dict(llama=llama_n, pose="anda" if not para else "caido", fase=fase, dir=0.5 if lt < 4.0 else 0.6,
                mira=(0.6, -0.5) if lt > 4.0 else (0.5, 0.0), feliz=1.0 if lt > 4.6 else 0.0)
    st_p = dict(palo=0.8, llama=llama_p, pose="anda" if not para else "caido", fase=fase + 1.0 if fase else None,
                dir=-0.5 if para else 0.5, mira=(-0.6, 0.5) if para else (0.4, 0.0), inclina=-0.07*agacha,
                feliz=1.0 if lt > 4.8 else 0.0, ceja=0.0)
    cad_p = 830 - 0.2*H_AD + 60*agacha
    cab_n, _ = nino(img, kx, 830, st_n, t)
    cab_p, _ = padre(img, fx, cad_p, 830, H_AD, st_p, t)
    if tapa > 0:     # el brazo del padre, con la mano haciendo de pared delante de la llama del niño
        d = ImageDraw.Draw(img)
        hx, hy, r = centro_cabeza(cab_p, H_AD)
        hombro = (fx - H_AD*0.05 - 0.07*H_AD*agacha*0.3, hy + r*0.35 + H_AD*0.12)
        nx, ny, nr = centro_cabeza(cab_n, H_NI)
        mano = (hombro[0] + (nx + nr*1.25 - hombro[0])*tapa, hombro[1] + (ny - nr*1.7 - hombro[1])*tapa)
        codo = ((hombro[0] + mano[0])/2 + 10, max(hombro[1], mano[1]) + 30)
        d.line([hombro, codo, mano], fill=T, width=max(4, int(H_AD*0.018)), joint="curve")
        # la mano ahuecada, de canto, haciendo de pared delante de la llamita
        palma = [(mano[0] + 6, mano[1] - 46), (mano[0] - 10, mano[1] - 30), (mano[0] - 14, mano[1]),
                 (mano[0] - 6, mano[1] + 26), (mano[0] + 10, mano[1] + 20), (mano[0] + 12, mano[1] - 40)]
        d.polygon(palma, fill=(240, 236, 226), outline=T)
        d.line(palma + [palma[0]], fill=T, width=4)
    acerca = suave((lt - 2.8)/1.2)
    return img, (min(max(x + 100, 700), 900)*(1 - acerca) + (kx + 120)*acerca, 470 - 30*acerca, 1.12 + 0.5*acerca)

def p_cumple(lt, t):
    """El cumpleaños: el niño enciende él solo la vela de su tarta. El padre aplaude."""
    img = M.oscurece(M.bg("cocina", claro=0.0), 0.3)
    y = 700
    junta = suave((lt - 1.0)/0.8)*(1 - suave((lt - 2.6)/0.6))
    st_n = dict(llama=1.0, pose="caido", dir=0.6, mira=(0.6, 0.5), inclina=0.32*junta, feliz=1.0 if lt > 3.0 else 0.0)
    img = C.luz(img, 660, 500, 300, 0.3, CALIDO)
    nino(img, 640, 792, st_n, t)
    cab_p, _ = padre(img, 1150, 880 - 0.2*H_AD, 880, H_AD, dict(palo=0.78, llama=0.95, dir=-0.6, mira=(-0.6, 0.4),
                     pose="aplaude" if lt > 3.0 else "caido", feliz=1.0 if lt > 3.0 else 0.0), t)
    img = C.luz(img, cab_p[0], cab_p[1] + 60, 240, 0.2, CALIDO)
    d = ImageDraw.Draw(img)
    d.rectangle([380, y, 1000, y + 24], fill=(160, 156, 150), outline=T, width=4)
    d.rectangle([400, y + 24, 980, CH + 5], fill=(128, 126, 122), outline=T, width=4)
    vela = suave((lt - 1.9)/0.3)
    if vela:
        img = C.luz(img, 750, y - 150, 220*vela, 0.3*vela, CALIDO)
    tarta(ImageDraw.Draw(img), 750, y, 200, vela, t)
    if 1.6 < lt < 2.1:
        M.chispas(ImageDraw.Draw(img), 735, y - 135, ((lt - 1.6)*4) % 1.0, 90, semilla=int(lt*10))
    return img, (840, 480, 1.18)

def p_cena(lt, t):
    """Los dos cenando, las dos llamas iluminando la mesa."""
    img = M.bg("cocina", claro=0.0)
    img = M.oscurece(img, 0.35)
    y = 700
    img = C.luz(img, 800, 380, 520, 0.4, CALIDO)
    rie = 1.4 < lt < 3.6
    C.silla(img, 560, 440, y + 30, 230)
    nino(img, 560, y - 20, dict(llama=1.0, pose="mesa", objeto=(0, y), sin_piernas=True, dir=0.6, mira=(0.7, -0.2),
                                  feliz=1.0 if rie else 0.0), t)
    C.silla(img, 1060, 330, y + 30, 260)
    padre(img, 1060, y + 20, CH + 200, H_AD, dict(palo=0.78, llama=1.0, pose="mesa", objeto=(0, y), sin_piernas=True,
                                                   dir=-0.6, mira=(-0.7, 0.1), feliz=1.0 if rie else 0.0), t)
    d = ImageDraw.Draw(img)
    d.rectangle([300, y, 1300, y + 26], fill=(160, 156, 150), outline=T, width=4)
    d.rectangle([320, y + 26, 1280, CH + 5], fill=(128, 126, 122), outline=T, width=4)
    for cx in (560, 1060):
        d.ellipse([cx - 90, y - 14, cx + 90, y + 10], fill=(240, 240, 236), outline=T, width=3)
    return img, (800, 460, 1.04)

def p_despedida(lt, t):
    """Quince años despues: se va a la ciudad con su caja. El padre le dice adios."""
    img = M.bg("calle", claro=0.05)
    img = C.luz(img, 1300, -80, 420, 0.4, (255, 255, 250))
    sale = lt > 1.4
    x = 700 + (180*(lt - 1.4) if sale else 0)
    saluda = math.sin(lt*7)
    cab_p, _ = padre(img, 380, 840 - 0.2*H_AD, 840, H_AD, dict(palo=0.68, llama=0.75, dir=0.6, mira=(0.7, 0.0),
                     pose="brindis", objeto=(470 + 30*saluda, 520), feliz=1.0 if lt < 2.5 else 0.0,
                     ceja=0.0 if lt < 2.5 else 0.4), t)
    st = dict(palo=1.0, llama=1.0, pose="caja", fase=(lt - 1.4)*6.5 if sale else None, dir=0.6 if sale else -0.4,
              mira=(0.6, 0.0) if sale else (-0.7, 0.0), feliz=1.0 if not sale else 0.0)
    cab, _ = hijo(img, x, 860, st, t)
    hx, hy, r = centro_cabeza(cab, H_AD)
    caja_carton(ImageDraw.Draw(img), x, hy + r*0.35 + H_AD*0.36, 180)
    return img, (min(max(x - 60, 700), 900), 470, 1.08)

def p_metro(lt, t):
    st = dict(palo=1.0, llama=0.9, pose="movil", mira=(0.3, 0.9), cansancio=0.25)
    return M.metro(lt, t, gente=True, st=st)

def p_ciudad(lt, t):
    return M.calle(lt, t, "dia", dict(x0=120, v=210, paso=8.0,
                   st=dict(palo=1.0, llama=0.9, pose="movil", dir=0.6, mira=(0.3, 0.9), cansancio=0.2)))

def p_llamada_dad(lt, t):
    """'Dad calling...' y él cuelga con el pulgar en el boton rojo."""
    img = M.oscurece(C.recorte(B.bg_ofi(), 800, 400, 2.0).filter(ImageFilter.GaussianBlur(8)), 0.25)
    cuelga = lt > 2.5
    def ui(pant):
        W, H = pant.size; p = ImageDraw.Draw(pant)
        p.rectangle([0, 0, W, H], fill=(30, 30, 34))
        p.text((W/2, H*0.25), "DAD", font=fuente(W*0.18), fill=(250, 250, 250), anchor="mm")
        p.text((W/2, H*0.34), "calling..." if not cuelga else "Call declined", font=fuente(W*0.07), fill=(170, 170, 176), anchor="mm")
        if not cuelga:
            for x, col in ((W*0.28, (210, 70, 60)), (W*0.72, (230, 230, 230))):
                p.ellipse([x - W*0.1, H*0.78 - W*0.1, x + W*0.1, H*0.78 + W*0.1], fill=col)
    pulgar = None
    k = (lt - 1.8)/0.7
    if 0 <= k <= 1.3:
        pulgar = (800 - 98*suave(min(1, k)), 470 + 780*0.28 + 120*(1 - suave(min(1, k))))
    M.movil_grande(img, 800, 470, 780, "negro", lt, fondo_pantalla=ui, pulgar=pulgar)
    return img, (800, 460, 1.0)

def chat(datos, pulgar_desde=None, pulgar_hasta=None):
    def plano(lt, t):
        img = M.fondo_chat(); img = C.luz(img, 800, 450, 420, 0.35)
        pulgar = (820 + 40*math.sin(lt*14), 790) if pulgar_desde is not None and pulgar_desde <= lt < pulgar_hasta else None
        M.movil_grande(img, 800, 470, 780, "chat", lt, datos, pulgar, contacto="Dad")
        return img, (800, 460, 1.0 + 0.015*lt)
    return plano

def p_padre_mesa(lt, t, llama=0.55, palo=0.64):
    """Solo en la mesa de la cocina, con la otra silla vacia. Mira el movil."""
    img = M.oscurece(M.bg("cocina", claro=0.0), 0.3)
    y = 700
    C.silla(img, 560, 450, y + 30, 250)                    # la silla vacia
    C.silla(img, 1060, 330, y + 30, 260)
    st = dict(palo=palo, llama=llama, pose="mesa", objeto=(0, y), sin_piernas=True, dir=-0.3,
              mira=(-0.2, 0.9) if lt < 3.2 else (-0.8, 0.0), cansancio=0.35, ceja=0.45, parpadeo=parpadeo(lt, 3.9))
    tmp = img.copy(); cab, _ = padre(tmp, 1060, y + 20, CH + 200, H_AD, st, t)
    img = C.luz(img, cab[0], cab[1] + 60, 300, 0.2*llama/0.55, CALIDO)
    padre(img, 1060, y + 20, CH + 200, H_AD, st, t)
    d = ImageDraw.Draw(img)
    d.rectangle([300, y, 1300, y + 26], fill=(160, 156, 150), outline=T, width=4)
    d.rectangle([320, y + 26, 1280, CH + 5], fill=(128, 126, 122), outline=T, width=4)
    d.ellipse([1060 - 90, y - 14, 1060 + 90, y + 10], fill=(240, 240, 236), outline=T, width=3)
    d.ellipse([560 - 90, y - 14, 560 + 90, y + 10], fill=(214, 214, 210), outline=T, width=3)
    d.rounded_rectangle([880, y - 10, 960, y + 4], radius=4, fill=(20, 20, 24))
    return img, (820, 460, 1.04 + 0.01*lt)

def p_padre_ventana(lt, t):
    """De pie junto a la ventana, mirando a la calle. Nadie viene."""
    img = M.oscurece(bg_salon(), 0.35)
    st = dict(palo=0.6, llama=0.4, espalda=True, inclina=0.02)
    tmp = img.copy(); cab, _ = padre(tmp, 800, 820 - 0.2*H_AD, 820, H_AD, st, t)
    img = C.luz(img, 800, 200, 300, 0.25, (220, 224, 236))
    img = C.luz(img, cab[0], cab[1] + 40, 220, 0.15, CALIDO)
    padre(img, 800, 820 - 0.2*H_AD, 820, H_AD, st, t)
    return img, (800, 380, 1.15 + 0.01*lt)

def p_oficina_noche(lt, t, hora="10:15 PM", con_foto=False, mira_foto=0.0):
    img = B.bg_ofi(noche=0.72)
    st = dict(palo=1.0, llama=0.85, cansancio=0.45 if not mira_foto else 0.1, ceja=0.3, dir=-0.6*mira_foto,
              mira=(-0.8*mira_foto, 0.6 if not mira_foto else 0.4), parpadeo=parpadeo(lt, 3.1))
    tmp = img.copy(); cab, _ = B.puesto(tmp, 800, 720, 680, "cerilla", st, t)
    img = C.luz(img, cab[0], cab[1] + 80, 330, 0.3, CALIDO)
    B.puesto(img, 800, 720, 680, "cerilla", st, t)
    if con_foto:
        foto(img, 470, 650, 120, inclina=4)
    C.reloj_tarjeta(img, hora, 1300, 160, 0, t)
    return img, (800, 460, 1.06 + 0.01*lt)

def p_ve_foto(lt, t):
    k = suave((lt - 1.2)/0.8)
    return p_oficina_noche(lt, t, "11:46 PM", con_foto=True, mira_foto=k)

def p_foto_cerca(lt, t):
    img = M.oscurece(C.recorte(B.bg_ofi(noche=0.72), 470, 650, 2.2).filter(ImageFilter.GaussianBlur(6)), 0.2)
    img = C.luz(img, 800, 450, 500, 0.25, CALIDO)
    foto(img, 800, 450, 820, inclina=2)
    return img, (800, 450, 1.0 + 0.02*lt)

def p_cara_hijo(lt, t):
    img = C.recorte(B.bg_ofi(noche=0.72), 800, 330, 1.9)
    img = C.luz(img, 800, 260, 340, 0.25, CALIDO)
    st = dict(palo=1.0, llama=0.85, sin_piernas=True, pose="caido", dir=-0.2,
              mira=(-0.3, 0.5) if lt < 1.6 else (0.0, -0.1), ceja=0.6 if lt < 1.6 else 0.0,
              sorpresa=1.0 if lt >= 1.6 else 0.0)
    C.cerilla(img, 800, 1250, 2000, 1100, st, t)
    return img, (800, 450, 1.0 + 0.012*lt)

def p_corre(lt, t):
    img = M.bg("calle", oscuro=0.5)
    for x in (320, 1280):
        img = C.luz(img, x, 215, 160, 0.5, (250, 250, 235))
    x = 100 + 300*lt
    cab, _ = hijo(img, x, 830, dict(palo=1.0, llama=0.9, pose="anda", fase=lt*12, dir=0.7, mira=(0.7, 0.0), ceja=-0.0), t, h=520)
    img = C.luz(img, cab[0], cab[1] + 40, 200, 0.2, CALIDO)
    hijo(img, x, 830, dict(palo=1.0, llama=0.9, pose="anda", fase=lt*12, dir=0.7, mira=(0.7, 0.0)), t, h=520)
    return img, (min(max(x, 700), 900), 470, 1.12)

def p_puerta(lt, t):
    abre = suave((lt - 3.0)/0.8)
    img = fachada(abre)
    llega = suave(lt/1.6)
    x = 300 + (700 - 300)*llega
    toca = 1.8 < lt < 2.9
    golpe = abs(math.sin((lt - 1.8)*math.pi*2.7)) if toca else 0
    st = dict(palo=1.0, llama=0.9, pose="brindis" if toca else ("anda" if lt < 1.6 else "caido"), fase=lt*8 if lt < 1.6 else None,
              objeto=(820 - 30*golpe, 470), dir=0.6, mira=(0.7, -0.1), sorpresa=1.0 if lt > 3.2 else 0.0)
    cab, _ = hijo(img, x, 770, st, t)
    img = C.luz(img, cab[0], cab[1] + 40, 200, 0.2, CALIDO)
    hijo(img, x, 770, st, t)
    return img, (820, 460, 1.06)

SILLON_W = 380
def salon_final(lt, t, llama_p, llega=1.0, sentado=1.0, feliz_p=0.0, junta=0.0, brazo=False):
    img = M.oscurece(bg_salon(), 0.78 - 0.3*suave((llama_p - 0.15)/0.7))
    px, suelo = 640, 840
    asiento = suelo - SILLON_W*0.45
    st_p = dict(palo=0.55, llama=llama_p, dir=0.5 if llega > 0.5 else 0.1,
                mira=(0.7, -0.1) if llega > 0.5 else (0.3, -0.3), cansancio=0.7*(1 - feliz_p), ceja=0.5*(1 - feliz_p),
                feliz=feliz_p, inclina=0.05*junta, parpadeo=parpadeo(lt, 4.1))
    tmp = img.copy(); cab_p, _ = padre(tmp, px, asiento, suelo, H_AD, st_p, t)
    img = C.luz(img, cab_p[0], cab_p[1] + 60, 220 + 220*llama_p, 0.12 + 0.3*llama_p, CALIDO)
    mesita(img, 330, suelo, 520, lampara=True, telefono=True)
    sillon(img, px, suelo, SILLON_W, "detras")
    padre(img, px, asiento, suelo, H_AD, st_p, t)
    sillon(img, px, suelo, SILLON_W, "delante")
    # el hijo entra por la derecha y se sienta en un taburete al lado
    hx = 1500 - (1500 - 990)*llega
    if sentado > 0:
        tab = suelo - 95
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([990 - 110, tab, 990 + 110, tab + 26], radius=8, fill=(70, 70, 76), outline=T, width=4)
        for lado in (-1, 1):
            d.line([(990 + lado*90, tab + 26), (990 + lado*100, suelo)], fill=T, width=8)
        cad = (suelo - 0.2*H_AD)*(1 - sentado) + tab*sentado
        st_h = dict(palo=1.0, llama=0.95, dir=-0.6, mira=(-0.7, 0.1), inclina=-0.08*junta, feliz=feliz_p,
                    pose="brindis" if brazo else "caido", objeto=(px + 150, asiento - 110), sin_piernas=sentado > 0.5)
        cab_h, _ = hijo(img, hx, suelo, st_h, t, cadera=cad)
    else:
        cab_h, _ = hijo(img, hx, suelo, dict(palo=1.0, llama=0.95, pose="anda", fase=lt*7, dir=-0.6, mira=(-0.7, 0.0)), t)
    img = C.luz(img, cab_h[0], cab_h[1] + 60, 240, 0.2, CALIDO)
    return img, cab_p, cab_h

def p_sillon(lt, t):
    llega = suave((lt - 1.4)/1.8)
    sentado = suave((lt - 3.4)/0.6) if lt > 3.4 else 0.0
    img, cab_p, cab_h = salon_final(lt, t, 0.1 + 0.03*math.sin(lt*8), llega, sentado if lt > 3.4 else 0.0)
    if lt < 3.4:
        img, cab_p, cab_h = salon_final(lt, t, 0.1 + 0.03*math.sin(lt*8), llega, 0.0)
    return img, (820, 520, 1.2)

def p_devuelve(lt, t):
    """De cerca, al reves que de niño: ahora el hijo junta su cabeza con la del padre."""
    img = M.oscurece(C.recorte(bg_salon(), 820, 420, 2.4).filter(ImageFilter.GaussianBlur(10)), 0.55)
    junta = suave(lt/1.0)
    crece = suave((lt - 1.4)/1.6)
    px, py, pr = 640 + 50*junta, 470, 190
    hx, hy, rh = 1110 - 50*junta, 430, 200
    img = C.luz(img, hx, hy - 230, 360, 0.3, CALIDO)
    llama_p = 0.1 + 0.85*crece + 0.02*math.sin(lt*9)
    img = C.luz(img, px, py - 200, 200 + 220*crece, 0.12 + 0.3*crece, CALIDO)
    cabeza_suelta(img, hx, hy, rh, C.ROJO, 1.0, t, dirx=-0.5, mira=(-0.6, 0.3), cansancio=0.3 if lt < 3.0 else 0.0,
                  feliz=1.0 if lt > 3.0 else 0.0)
    cabeza_suelta(img, px, py, pr, ROJO_P, llama_p, t, gafas_=True, dirx=0.4, mira=(0.4, -0.2),
                  cansancio=0.8*(1 - crece), sorpresa=1.0 if 1.6 < lt < 2.8 else 0.0, feliz=1.0 if lt >= 2.8 else 0.0)
    return img, (860, 450, 1.0 + 0.02*lt)

def p_juntos(lt, t):
    img, cab_p, cab_h = salon_final(lt, t, 0.95, 1.0, 1.0, feliz_p=1.0, junta=0.0, brazo=lt > 1.0)
    return img, (800, 520, 1.25 - 0.012*lt)

def p_final(lt, t, dur=8.0):
    img = Image.new("RGB", (CW, CH), (8, 8, 10)); d = ImageDraw.Draw(img)
    for t0, txt, y, px in ((0.5, "Someone gave you your fire.", 380, 64), (2.0, "Call them.", 470, 64)):
        a = suave((lt - t0)/0.7)*suave((dur - lt)/0.8); c = int(8 + 242*a)
        d.text((CW/2, y), txt, font=fuente(px), fill=(c, c, c), anchor="mm")
    a = suave((lt - 3.8)/0.8)*suave((dur - lt)/0.8)
    if a > 0:
        c = int(8 + 150*a)
        d.text((CW/2 + 25, 690), "STILL BURNING", font=fuente(34), fill=(c, c, c), anchor="mm")
        x = CW/2 - 175
        d.rounded_rectangle([x - 5, 670, x + 5, 720], radius=4, fill=tuple(int(8 + (v - 8)*a) for v in (225, 218, 200)))
        d.ellipse([x - 12, 652, x + 12, 678], fill=tuple(int(8 + (v - 8)*a) for v in C.ROJO))
        if a > 0.6: C.llama(d, x, 655, 30*a, t)
    return img, (CW/2, CH/2, 1.0)

# ---------------------------------------------------------------- el montaje
L = LENTO
GUION = [
    (p_arranque, 5.0, []),
    (p_llamadas_perdidas, 2.8, [(0.3, "vibra")]),
    (lambda lt, t: p_titulo(lt, t, 2.8), 2.8, []),
    (tarjeta("30 YEARS EARLIER"), 2.0, [(0.2, "tic")]),
    (p_cuarto, 4.2, []),
    (lambda lt, t: p_juntan(lt, t), 4.5, [(1.2, "fuu")]),
    (p_cuarto_luz, 3.5, []),
    (p_viento, 7.5, [(0.8, "viento6.5")]),
    (p_cumple, 5.5, [(1.7, "fuu"), (3.0, "aplauso")]),
    (p_cena, 5.0, []),
    (tarjeta("15 YEARS LATER"), 2.0, [(0.2, "tic")]),
    (p_despedida, 7.0, []),
    (p_metro, 3.5, []),
    (p_ciudad, 4.0, []),
    (p_llamada_dad, 4.5, [(0.0, "tono2.5"), (2.5, "tap")]),
    (chat([(1, "Busy. Call you later.", 2.4, 1.6), (0, "Delivered", 2.6, 0)], 0.6, 2.4), 4.5*L, [(2.4, "envia")]),
    (p_padre_mesa, 5.5, []),
    (tarjeta("MARCH"), 1.6, [(0.2, "tic")]),
    (chat([(1, "Busy. Call you later.", -1, 0), (-1, "Happy birthday, son!", 0.6, 0), (0, "Seen", 2.4, 0)]), 5.0*L, [(0.6, "ding")]),
    (lambda lt, t: p_oficina_noche(lt, t, "10:15 PM"), 4.0, []),
    (lambda lt, t: p_padre_mesa(lt, t, 0.38, 0.6), 4.5, []),
    (tarjeta("DECEMBER"), 1.6, [(0.2, "tic")]),
    (chat([(-1, "Happy birthday, son!", -1, 0), (0, "Seen", -1, 0), (-1, "Coming for Christmas?", 0.6, 0),
           (1, "Can't this year.", 3.2, 1.4), (-1, "It's ok. I understand.", 5.0, 0)], 1.8, 3.2), 7.0*L,
     [(0.6, "ding"), (3.2, "envia"), (5.0, "ding")]),
    (p_padre_ventana, 5.0, []),
    (tarjeta("CHRISTMAS EVE"), 1.6, [(0.2, "tic")]),
    (p_ve_foto, 6.0, []),
    (p_foto_cerca, 4.0, []),
    (p_cara_hijo, 3.5, []),
    (lambda lt, t: p_llamadas_perdidas(lt, t, "11:52 PM"), 2.5, [(0.3, "vibra")]),
    (p_corre, 5.0, []),
    (p_puerta, 5.0, [(1.85, "toc"), (2.2, "toc"), (2.55, "toc"), (3.0, "puerta")]),
    (p_sillon, 7.0, []),
    (p_devuelve, 6.0, [(1.4, "fuu")]),
    (p_juntos, 7.0, []),
    (lambda lt, t: p_final(lt, t, 8.0), 8.0, []),
    (M.negro, 2.0, []),
]

def tabla():
    t = 0.0; out = []
    for fn, dur, sfx in GUION:
        out.append((t, t + dur, fn, sfx)); t += dur
    return out, t

TABLA, DUR = tabla()
_I = {fn: a for a, b, fn, s in TABLA}
INFANCIA = _I[p_cuarto]
LEJOS = TABLA[10][0]                # 15 YEARS LATER
SOLO = _I[p_padre_mesa]
FOTO = _I[p_ve_foto]
VUELVE = _I[p_corre]
FINAL = DUR - 10.0

def fotograma(t):
    for a, b, fn, _ in TABLA:
        if a <= t < b:
            img, (cx, cy, z) = fn(t - a, t)
            break
    else:
        img, (cx, cy, z) = M.negro(0)
    img = C.recorte(img, cx, cy, z) if z > 1.001 or abs(cx - CW/2) > 1 else img
    img = img.resize((VW, VH), Image.LANCZOS)
    if t < 0.6:
        img = M.oscurece(img, 1 - t/0.6)
    return M.vineta(img)

# ---------------------------------------------------------------- sonido
SR = 44100
def musica():
    n = int(DUR*SR); t = np.arange(n)/SR; out = np.zeros(n)
    nota = M.nota
    secciones = [
        (0, INFANCIA, [[45, 52, 57, 60]], 5.0, 0.0, 12),                                                            # el arranque: suspendido
        (INFANCIA, LEJOS, [[48, 55, 60, 64], [53, 57, 60, 65], [55, 59, 62, 67], [48, 55, 60, 64]], 2.2, 0.06, 24),  # la infancia
        (LEJOS, SOLO, [[57, 60, 64, 67], [53, 57, 60, 64], [48, 55, 60, 64], [55, 59, 62, 64]], 2.5, 0.05, 12),     # la ciudad
        (SOLO, FOTO, [[57, 60, 64], [50, 53, 57, 60], [52, 55, 59], [57, 60, 64]], 3.2, 0.035, 12),                  # el padre solo
        (FOTO, VUELVE, [[45, 52, 57], [41, 48, 53, 57]], 3.5, 0.03, 12),                                              # la foto
        (VUELVE, FINAL, [[48, 55, 60, 64], [55, 59, 62, 67], [57, 60, 64, 69], [53, 57, 60, 65]], 2.4, 0.055, 24),  # vuelve
        (FINAL, DUR, [[48, 55, 60, 64], [53, 57, 60, 65]], 3.0, 0.035, 12),
    ]
    for a, b, acordes, dur, vp, octava in secciones:
        i = 0; t0 = a
        while t0 < b:
            ac = acordes[i % len(acordes)]
            s0, s1 = int(t0*SR), min(n, int((min(b, t0 + dur) + 0.8)*SR))
            tt = t[s0:s1] - t0; fin = min(b, t0 + dur) - t0
            env = np.minimum(1, tt/0.9)*np.exp(-np.maximum(0, tt - fin)*5)
            vol = 0.045 if vp else 0.03
            for m in ac:
                f = nota(m); out[s0:s1] += vol*env*(np.sin(2*np.pi*f*tt) + 0.25*np.sin(2*np.pi*2*f*tt + 0.4))
            out[s0:s1] += 0.06*env*np.sin(2*np.pi*nota(ac[0] - 12)*tt)
            if vp:
                paso = dur/4
                for k, m in enumerate([ac[0], ac[-2], ac[1], ac[-1]]):
                    pa = t0 + k*paso
                    if pa >= b: break
                    a0 = int(pa*SR); a1 = min(n, a0 + int(1.8*SR)); ta = t[a0:a1] - pa; f = nota(m + octava)
                    out[a0:a1] += vp*np.exp(-ta*2.4)*(np.sin(2*np.pi*f*ta) + 0.2*np.sin(2*np.pi*3*f*ta))
            t0 += dur; i += 1
    ir_n = int(1.8*SR)
    ir = np.random.default_rng(2).standard_normal(ir_n)*np.exp(-np.arange(ir_n)/SR*3.2); ir[0] = 1.0; ir /= np.sqrt(np.sum(ir**2))
    Ln = n + ir_n
    wet = np.fft.irfft(np.fft.rfft(out, Ln)*np.fft.rfft(ir, Ln), Ln)[:n]
    out = 0.65*out + 0.35*wet/np.max(np.abs(wet))*np.max(np.abs(out))
    return out + 0.003*np.random.default_rng(1).standard_normal(n)

def efectos():
    n = int(DUR*SR); out = np.zeros(n); rnd = np.random.default_rng(5)
    def pon(t0, *xs):
        for x in xs:
            s0 = int(t0*SR); s1 = min(n, s0 + len(x))
            if s0 < n: out[s0:s1] += x[:s1 - s0]
    def tono(f, d, vol, at=0.005, ca=8.0):
        tt = np.arange(int(d*SR))/SR
        return vol*np.sin(2*np.pi*f*tt)*np.minimum(1, tt/at)*np.exp(-tt*ca)
    def ruido(d, vol, suav=20):
        return vol*np.convolve(rnd.standard_normal(int(d*SR)), np.ones(suav)/suav, mode="same")
    for a, b, fn, sfx in TABLA:
        for t0, tipo in sfx:
            T0 = a + t0
            if tipo == "fuu":
                x = ruido(0.8, 0.3, 60); env = np.minimum(1, np.arange(len(x))/(0.04*SR))*np.exp(-np.arange(len(x))/SR*4)
                pon(T0, x*env)
            elif tipo.startswith("viento"):
                d = float(tipo[6:]); x = ruido(d, 0.5, 400)
                tt = np.arange(len(x))/SR
                x *= np.minimum(1, tt/1.0)*np.minimum(1, (d - tt)/0.8)*(0.6 + 0.4*np.sin(tt*2.3))
                pon(T0, x)
            elif tipo.startswith("tono"):
                d = float(tipo[4:]); k = 0.0
                while k < d:
                    pon(T0 + k, tono(880, 0.35, 0.06, 0.01, 2), tono(1320, 0.35, 0.04, 0.01, 2)); k += 0.9
            elif tipo == "vibra":
                for k in range(2):
                    tt = np.arange(int(0.35*SR))/SR
                    pon(T0 + k*0.5, 0.08*np.sign(np.sin(2*np.pi*150*tt))*np.minimum(1, tt/0.01)*np.minimum(1, (0.35 - tt)/0.03))
            elif tipo == "aplauso":
                for _ in range(40):
                    pon(T0 + rnd.uniform(0, 1.6), ruido(0.03, 0.1, 2)*np.exp(-np.arange(int(0.03*SR))/SR*90))
            elif tipo == "tap":
                pon(T0, ruido(0.03, 0.25, 3), tono(1200, 0.04, 0.05, 0.001, 60))
            elif tipo == "ding":
                pon(T0, tono(1318, 0.6, 0.08, 0.002, 5), tono(1976, 0.5, 0.04, 0.002, 6))
            elif tipo == "envia":
                tt = np.arange(int(0.18*SR))/SR; pon(T0, 0.06*np.sin(2*np.pi*(700 + 2600*tt)*tt)*np.exp(-tt*10))
            elif tipo == "tic":
                pon(T0, tono(880, 0.25, 0.05, 0.002, 12))
            elif tipo == "toc":
                pon(T0, ruido(0.06, 0.5, 30)*np.exp(-np.arange(int(0.06*SR))/SR*60), tono(140, 0.12, 0.25, 0.001, 30))
            elif tipo == "puerta":
                tt = np.arange(int(0.9*SR))/SR
                pon(T0, 0.05*np.sin(2*np.pi*(320 + 90*np.sin(tt*9))*tt)*np.exp(-tt*3))
    return out

def audio(ruta):
    mus = musica(); fx = efectos()
    mix = mus/np.max(np.abs(mus))*0.42 + fx
    fo = int(2.5*SR); mix[-fo:] *= np.linspace(1, 0, fo)
    pcm = (np.clip(mix, -0.98, 0.98)*32767).astype(np.int16)
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

def main():
    Path(OUT).mkdir(exist_ok=True)
    args = sys.argv[1:]
    if args and args[0] == "fotos":
        for i, (a, b, fn, _) in enumerate(TABLA):
            for k, f in enumerate((0.3, 0.85)):
                fotograma(a + (b - a)*f).resize((640, 360)).save(OUT + f"pio_{i:02d}_{k}.jpg", quality=85)
        print(f"{len(TABLA)} planos, {DUR:.1f} s"); return
    if args and args[0] == "en":
        for s in args[1:]:
            fotograma(float(s)).resize((960, 540)).save(OUT + f"pio_en_{float(s):06.2f}.jpg", quality=85)
        return
    audio(OUT + "pass_it_on_audio.wav")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}", "-r", str(FPS),
                          "-i", "-", "-i", OUT + "pass_it_on_audio.wav", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19",
                          "-preset", "medium", "-c:a", "aac", "-b:a", "192k", "-shortest", OUT + "PASS_IT_ON.mp4"], stdin=subprocess.PIPE)
    for i in range(int(DUR*FPS)):
        p.stdin.write(fotograma(i/FPS).tobytes())
    p.stdin.close(); p.wait()
    print(f"hecho: {DUR:.1f} s")

if __name__ == "__main__":
    main()
