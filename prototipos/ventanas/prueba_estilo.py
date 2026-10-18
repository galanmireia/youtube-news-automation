"""ACROSS THE STREET — prueba de estilo (dos fotogramas fijos).

El edificio de enfrente, de noche, visto desde la otra acera. En cada ventana
iluminada, detras de la cortina, siluetas: un culebron en cada casa.
  1) el edificio entero   2) la vista por los prismaticos, en una ventana
"""
import math, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1920
OUT = str(Path(__file__).resolve().parent) + "/salida/"
NEGRO = (22, 16, 26)
LUZ = (255, 176, 92)
LUZ2 = (255, 214, 140)

# ---------------------------------------------------------------- las siluetas
def tramo(d, p0, p1, w0, w1):
    """Un trozo de brazo o pierna que se estrecha, con las juntas redondas."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]; L = math.hypot(dx, dy) or 1
    nx, ny = -dy/L, dx/L
    d.polygon([(p0[0] + nx*w0/2, p0[1] + ny*w0/2), (p1[0] + nx*w1/2, p1[1] + ny*w1/2),
               (p1[0] - nx*w1/2, p1[1] - ny*w1/2), (p0[0] - nx*w0/2, p0[1] - ny*w0/2)], fill=NEGRO)
    for p, w in ((p0, w0), (p1, w1)):
        d.ellipse([p[0] - w/2, p[1] - w/2, p[0] + w/2, p[1] + w/2], fill=NEGRO)

POSES = {   # (hombro-codo, codo-mano) en grados desde "colgando": + hacia donde mira. (delante, detras)
    "de_pie": ((12, 25), (-10, -4)),
    "brazo_arriba": ((165, 175), (-15, -5)),
    "señala": ((80, 88), (-8, 2)),
    "abrazo": ((75, 125), (65, 115)),
    "manos_cara": ((28, 150), (20, 150)),
    "test": ((120, 178), (-10, -4)),
    "maleta": ((10, 20), (-6, -2)),
    "jarras": ((-50, 40), (-50, 40)),
}

def silueta(d, x, suelo, h, pose="de_pie", pelo="corto", falda=False, mira=1, inclina=0.0):
    """Una persona en silueta, con formas organicas. h: altura; mira: 1 derecha, -1 izquierda."""
    u = h/100
    x += inclina*u*4
    hx, hy = x + inclina*u*6, suelo - 92*u
    mujer = falda or pelo in ("largo", "coleta", "moño")
    sw = (9 if mujer else 11.5)*u; ww = (6.5 if mujer else 8.5)*u; hw = (10 if mujer else 9)*u
    ys, yw, yh = suelo - 81*u, suelo - 60*u, suelo - 50*u
    # el pelo de detras
    if pelo == "largo":
        d.polygon([(hx - 6.5*u, hy - 3*u), (hx + 6.5*u, hy - 3*u), (hx + 7.5*u - mira*3*u, hy + 15*u), (hx - 7.5*u - mira*3*u, hy + 15*u)], fill=NEGRO)
    elif pelo == "coleta":
        tramo(d, (hx - mira*4*u, hy - 3*u), (hx - mira*9*u, hy + 6*u), 4.5*u, 2.5*u)
    # piernas
    for lado in (-1, 1):
        cad = (x + lado*4*u, yh); rod = (x + lado*4.6*u, suelo - 27*u); tob = (x + lado*4.2*u, suelo - 3*u)
        tramo(d, cad, rod, 8.5*u, 6*u); tramo(d, rod, tob, 6*u, 3.6*u)
        d.ellipse([tob[0] - 2.5*u + mira*1.5*u, suelo - 3.5*u, tob[0] + 5*u + mira*1.5*u, suelo + 0.5*u], fill=NEGRO)
    # el cuerpo
    d.polygon([(x - sw, ys + 2*u), (x + sw, ys + 2*u), (x + ww, yw), (x + hw, yh + 2*u), (x - hw, yh + 2*u), (x - ww, yw)], fill=NEGRO)
    d.rounded_rectangle([x - sw, ys - 0.5*u, x + sw, ys + 8*u], radius=int(4*u), fill=NEGRO)     # hombros redondeados
    if falda:
        d.polygon([(x - hw, yh), (x + hw, yh), (x + hw + 5*u, suelo - 26*u), (x - hw - 5*u, suelo - 26*u)], fill=NEGRO)
    d.polygon([(hx - 2.2*u, hy + 5*u), (hx + 2.2*u, hy + 5*u), (x + 3*u, ys + 1*u), (x - 3*u, ys + 1*u)], fill=NEGRO)   # cuello
    # brazos
    a_del, a_det = POSES.get(pose, POSES["de_pie"])
    for lado, (a1, a2) in ((-mira, a_det), (mira, a_del)):
        hb = (x + lado*(sw - 1.5*u), ys + 2*u)
        r1, r2 = math.radians(a1), math.radians(a2)
        codo = (hb[0] + mira*math.sin(r1)*16*u, hb[1] + math.cos(r1)*16*u)
        mano = (codo[0] + mira*math.sin(r2)*15*u, codo[1] + math.cos(r2)*15*u)
        tramo(d, hb, codo, 5.2*u, 4*u); tramo(d, codo, mano, 4*u, 3*u)
        d.ellipse([mano[0] - 2.4*u, mano[1] - 2.6*u, mano[0] + 2.4*u, mano[1] + 2.6*u], fill=NEGRO)
        if pose == "test" and lado == mira:
            d.rounded_rectangle([mano[0] - 0.9*u, mano[1] - 9*u, mano[0] + 0.9*u, mano[1] - 1*u], radius=int(u*0.8), fill=NEGRO)
        if pose == "maleta" and lado == -mira:
            d.rounded_rectangle([mano[0] - 9*u, mano[1] - 1*u, mano[0] + 9*u, mano[1] + 14*u], radius=int(1.5*u), fill=NEGRO)
            d.arc([mano[0] - 3*u, mano[1] - 3*u, mano[0] + 3*u, mano[1] + 2*u], 180, 360, fill=NEGRO, width=int(u))
    # la cabeza de perfil: craneo, nariz, barbilla
    d.ellipse([hx - 5.6*u, hy - 6.8*u, hx + 5.6*u, hy + 6.2*u], fill=NEGRO)
    d.polygon([(hx + mira*4.8*u, hy - 1.5*u), (hx + mira*7.2*u, hy + 1.2*u), (hx + mira*5*u, hy + 2.2*u)], fill=NEGRO)
    d.ellipse([hx + mira*1.5*u - 3.5*u, hy + 1*u, hx + mira*1.5*u + 3.5*u, hy + 6.8*u], fill=NEGRO)
    if pelo == "moño":
        d.ellipse([hx - mira*2*u - 3.6*u, hy - 11*u, hx - mira*2*u + 3.6*u, hy - 4.5*u], fill=NEGRO)
    elif pelo == "corto":
        d.ellipse([hx - 6.2*u - mira*0.8*u, hy - 7.4*u, hx + 5.4*u - mira*0.8*u, hy + 1*u], fill=NEGRO)
    elif pelo == "largo":
        d.ellipse([hx - 6.6*u, hy - 7.6*u, hx + 6.2*u, hy + 2*u], fill=NEGRO)

def gato(d, x, y, s):
    d.ellipse([x - s*0.5, y - s*0.6, x + s*0.5, y], fill=NEGRO)
    d.ellipse([x - s*0.32, y - s*1.05, x + s*0.32, y - s*0.5], fill=NEGRO)
    for k in (-1, 1):
        d.polygon([(x + k*s*0.08, y - s*0.95), (x + k*s*0.3, y - s*1.2), (x + k*s*0.3, y - s*0.85)], fill=NEGRO)
    d.arc([x + s*0.2, y - s*0.7, x + s*0.9, y + s*0.1], 270, 90, fill=NEGRO, width=int(s*0.12))

# ---------------------------------------------------------------- las ventanas
def ventana(img, x0, y0, w, h, escena, encendida=True, cortina=0.4, semilla=0):
    """Una ventana del edificio de enfrente: luz calida, cortina fina y lo que pase detras, en silueta."""
    d = ImageDraw.Draw(img)
    d.rectangle([x0 - 16, y0 - 16, x0 + w + 16, y0 + h + 16], fill=(70, 62, 80))
    if not encendida:
        d.rectangle([x0, y0, x0 + w, y0 + h], fill=(28, 34, 60))
        d.line([(x0 + w*0.2, y0 + h*0.1), (x0 + w*0.45, y0 + h*0.4)], fill=(50, 60, 96), width=6)
        return
    SS = 3                                                  # se dibuja a triple tamaño y se reduce: bordes suaves
    capa = Image.new("RGB", (w*SS, h*SS), LUZ); c = ImageDraw.Draw(capa)
    for j in range(h*SS):                                  # la luz de la lampara, mas fuerte en el centro
        f = abs(j - h*SS*0.35)/(h*SS)
        c.line([(0, j), (w*SS, j)], fill=tuple(int(a - (a - b)*min(1, f*1.4)) for a, b in zip(LUZ2, LUZ)))
    escena(c, w*SS, h*SS)
    capa = capa.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(max(0.6, w/400)))   # la cortina difumina un poco
    img.paste(capa, (x0, y0)); d = ImageDraw.Draw(img)
    for lado in (-1, 1):                                    # las cortinas recogidas a los lados
        xa = x0 if lado < 0 else x0 + w - w*cortina*0.5
        d.rectangle([xa, y0, xa + w*cortina*0.5, y0 + h], fill=(236, 140, 70))
        for k in range(1, 4):
            xx = xa + w*cortina*0.5*k/4
            d.line([(xx, y0), (xx, y0 + h)], fill=(214, 116, 56), width=3)
    d.line([(x0 + w/2, y0), (x0 + w/2, y0 + h)], fill=(70, 62, 80), width=8)
    d.line([(x0, y0 + h*0.42), (x0 + w, y0 + h*0.42)], fill=(70, 62, 80), width=8)
    d.rectangle([x0 - 24, y0 + h, x0 + w + 24, y0 + h + 20], fill=(90, 82, 100))

# las escenas: un culebron en cada casa
def beso(c, w, h):
    silueta(c, w*0.43, h*1.0, h*0.86, "abrazo", "largo", True, 1, inclina=0.4)
    silueta(c, w*0.6, h*1.0, h*0.95, "abrazo", "corto", False, -1, inclina=-0.3)

def amante(c, w, h):                                       # el marido llega con su maleta; el otro, detras de la cortina
    silueta(c, w*0.45, h*1.0, h*0.86, "manos_cara", "moño", True, 1)
    silueta(c, w*0.74, h*1.0, h*0.95, "maleta", "corto", False, -1)
    silueta(c, w*0.15, h*1.0, h*0.95, "de_pie", "corto", False, 1)          # el amante, asomando tras la cortina

def test(c, w, h):
    silueta(c, w*0.5, h*1.0, h*0.86, "test", "coleta", True, 1)

def pelea(c, w, h):
    silueta(c, w*0.3, h*1.0, h*0.88, "señala", "largo", True, 1)
    silueta(c, w*0.74, h*1.0, h*0.95, "brazo_arriba", "corto", False, -1)
    c.ellipse([w*0.52 - w*0.06, h*0.3 - w*0.02, w*0.52 + w*0.06, h*0.3 + w*0.02], fill=NEGRO)     # un plato volando

def sola(c, w, h):
    silueta(c, w*0.42, h*1.0, h*0.86, "de_pie", "moño", True, 1)
    gato(c, w*0.78, h*0.6, h*0.24)
    c.rectangle([w*0.6, h*0.6, w, h*0.64], fill=NEGRO)

def maleta(c, w, h):
    silueta(c, w*0.55, h*1.0, h*0.95, "maleta", "corto", False, -1)

def vacia(c, w, h):
    c.polygon([(w*0.35, h*0.15), (w*0.65, h*0.15), (w*0.6, h*0.35), (w*0.4, h*0.35)], fill=NEGRO)   # una lampara
    c.line([(w*0.5, 0), (w*0.5, h*0.15)], fill=NEGRO, width=4)

# ---------------------------------------------------------------- el edificio de enfrente
def edificio(estrellas=True):
    img = Image.new("RGB", (W, H), (18, 22, 52)); d = ImageDraw.Draw(img)
    for j in range(0, 400):                                # el cielo de noche
        f = j/400
        d.line([(0, j), (W, j)], fill=(int(30 - 12*f), int(30 - 8*f), int(76 - 24*f)))
    rnd = random.Random(1)
    for _ in range(60):
        x, y = rnd.uniform(0, W), rnd.uniform(0, 300)
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(220, 220, 240))
    d.ellipse([820, 70, 940, 190], fill=(250, 240, 210))
    d.rectangle([40, 260, W - 40, H], fill=(52, 44, 66))
    for fila in range(0, 60):                              # ladrillo en la penumbra
        for col in range(10):
            x = 40 + col*110 + (55 if fila % 2 else 0); y = 260 + fila*30
            d.rectangle([x, y, x + 106, y + 27], outline=(60, 52, 76), width=2)
    d.rectangle([20, 230, W - 20, 270], fill=(66, 58, 82))
    escenas = [[beso, vacia, test], [amante, None, pelea], [sola, maleta, beso if False else vacia]]
    for fila in range(3):
        for col in range(3):
            esc = escenas[fila][col]
            x0, y0 = 90 + col*320, 360 + fila*440
            ventana(img, x0, y0, 260, 320, esc or vacia, encendida=esc is not None, semilla=fila*3 + col)
            d = ImageDraw.Draw(img)
            d.text((x0 + 130, y0 - 30), f"{3 - fila}{'ABC'[col]}", fill=(150, 140, 170), anchor="mm")
    d.rectangle([390, 1640, 690, H], fill=(30, 26, 40))
    d.rectangle([410, 1660, 670, H], fill=(255, 196, 120))
    d.rectangle([0, 1860, W, H], fill=(30, 30, 40))
    return img

def prismaticos(escena):
    """La vista por los prismaticos: una sola ventana, dibujada en grande."""
    img = Image.new("RGB", (W, H), (52, 44, 66)); d = ImageDraw.Draw(img)
    for fila in range(0, 30):
        for col in range(6):
            x = col*220 + (110 if fila % 2 else 0); y = fila*66
            d.rectangle([x, y, x + 214, y + 60], outline=(62, 54, 78), width=4)
    ventana(img, 150, 520, 780, 900, escena, cortina=0.28)
    mask = Image.new("L", (W, H), 0); m = ImageDraw.Draw(mask)
    r = 430
    for k in (-1, 1):
        m.ellipse([W/2 + k*250 - r, 980 - r, W/2 + k*250 + r, 980 + r], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(16))
    return Image.composite(img, Image.new("RGB", (W, H), (6, 6, 10)), mask)

if __name__ == "__main__":
    Path(OUT).mkdir(exist_ok=True)
    ed = edificio()
    ed.save(OUT + "estilo_edificio.png")
    prismaticos(amante).save(OUT + "estilo_prismaticos.png")
    a = ed.resize((540, 960)); b = Image.open(OUT + "estilo_prismaticos.png").resize((540, 960))
    hoja = Image.new("RGB", (1080, 960)); hoja.paste(a, (0, 0)); hoja.paste(b, (540, 0)); hoja.save(OUT + "estilo_hoja.jpg", quality=88)
    print("ok")
