"""Monigotes: las escenas del canal, dibujadas con codigo.

Sustituye a la ilustracion por IA en vertical, y no es un apaño barato: es
mejor en las cuatro cosas que importaban.

GRATIS E INSTANTANEO. Cuatro centimos y siete segundos por imagen pasan a
cero y medio segundo. Un Short de cinco escenas se ahorra 20 centimos, y una
animacion de 36 fotogramas que con Gemini costaria 1,44 $ aqui cuesta nada.

IGUAL EN TODOS LOS PLANOS. Era el fallo de fondo del #82: cinco ilustraciones
preciosas que no se conocian entre si, o sea cinco imagenes de stock dibujadas.
Un monigote se dibuja idéntico siempre, por construccion.

SE MUEVE DE VERDAD. Una pose es una lista de PUNTOS, asi que entre dos poses
hay infinitas intermedias. El personaje anda, levanta el brazo o se sienta -
no es un zoom sobre una foto quieta, que es lo unico que se podia hacer antes.

Y LO PUEDO VER YO. Esto es lo que mas cambia. Llevaba el dia ajustando el
aspecto a ciegas, quemandole a ella videos de 50 centimos para enterarme de
como habia quedado. Con esto genero, miro y corrijo sin gastar nada: los
primeros cuatro fallos - monigotes pequeños, sobraba cielo, las piernas
sentadas hacian un zigzag y el arbol parecia una flor - los vi yo antes de
enseñar nada.

La idea es suya, mirando un canal de 22.000 visitas dibujado con palotes:
"igual es mejor hacer imagenes mas simples como estas".
"""
from __future__ import annotations

import logging
import math
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Los colores de las cosas. Un perro blanco, un caballo blanco y una espada
# blanca eran tres siluetas del mismo color, y en un movil eso es un dibujo
# sin terminar. No hace falta mas que un color por cosa: lo que las distingue
# es la FORMA, el color solo dice de que estan hechas.
PARDO       = (176, 132, 92)    # el perro
CASTAÑO     = (146, 100, 62)    # el caballo
MADERA      = (150, 106, 66)    # cascos, ruedas
ACERO       = (198, 202, 208)   # hojas de espada
HIERRO      = (86, 88, 94)      # cañones
PAPEL_VIEJO = (244, 236, 214)   # paginas
# Un granate que no se confunde con el rojo de las banderas ni con la ropa
# (que no tiene color propio, solo TINTA/blanco). Declarada aqui arriba y no
# donde se usa por primera vez, porque _capa() la lleva como valor por
# defecto y eso se fija al DEFINIR la funcion: puesta mas abajo en el
# fichero, el import entero revienta con un NameError.
CAPA_COLOR  = (94, 30, 38)
PIEDRA        = (168, 162, 152) # murallas
PIEDRA_CLARA  = (214, 206, 190) # iglesias
MADERA_PUERTA = (112, 76, 48)   # portones

TINTA = (24, 22, 20)
TINTA_CLARA = (244, 238, 226)

# Sobre que fondos hay que dibujar con tinta CLARA. Lo encontre midiendo el
# movimiento: en 'noche' salia un 96% de fotogramas quietos y en 'campo' un
# 8%, con la misma animacion. No fallaba la animacion - fallaba que un
# monigote de tinta negra sobre un azul de noche no se ve. Si no lo detecta
# una resta de fotogramas, tampoco lo ve quien mira.
_FONDOS_OSCUROS = frozenset({"noche"})
ROJO = (214, 40, 40)
FONDOS = {
    "campo":  [(0.00, 0.40, (126, 196, 232)), (0.40, 1.00, (122, 193, 96))],
    "calle":  [(0.00, 0.42, (232, 214, 186)), (0.42, 1.00, (196, 176, 150))],
    "salon":  [(0.00, 0.70, (238, 222, 200)), (0.70, 1.00, (180, 150, 118))],
    "noche":  [(0.00, 0.64, (44, 56, 92)),    (0.64, 1.00, (58, 70, 58))],
    "liso":   [(0.00, 1.00, (243, 229, 213))],
}

def _jit(p, r, rnd):
    return (p[0] + rnd.uniform(-r, r), p[1] + rnd.uniform(-r, r))

def _linea(d, pts, g, rnd, color=TINTA, temblor=2.2):
    """Una polilinea con pulso, que es lo que la hace parecer dibujada."""
    finos = []
    for a, b in zip(pts, pts[1:]):
        n = max(2, int(math.dist(a, b) / 26))
        for i in range(n):
            t = i / n
            finos.append(_jit((a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t), temblor, rnd))
    finos.append(pts[-1])
    d.line(finos, fill=color, width=g, joint="curve")

def _circulo(d, c, r, g, rnd, relleno=(255,255,255), color=TINTA):
    pts = []
    for i in range(37):
        a = i/36*2*math.pi
        rr = r + rnd.uniform(-r*0.035, r*0.035)
        pts.append((c[0]+math.cos(a)*rr, c[1]+math.sin(a)*rr))
    if relleno: d.polygon(pts, fill=relleno)
    d.line(pts, fill=color, width=g, joint="curve")

# Poses: puntos en unidades de ALTURA de la figura, origen en los pies.
_POSES = {
    "de_pie":   {"cuello": (0, -.70), "cadera": (0, -.38),
                 "brazos": [[(0,-.66),(-.13,-.50),(-.17,-.33)], [(0,-.66),(.13,-.50),(.17,-.33)]],
                 "piernas":[[(0,-.38),(-.09,-.19),(-.11,0)],   [(0,-.38),(.09,-.19),(.11,0)]]},
    "sentado":  {"cuello": (0, -.46), "cadera": (0, -.09),
                 "brazos": [[(0,-.42),(-.14,-.30),(-.17,-.13)], [(0,-.42),(.15,-.31),(.21,-.15)]],
                 "piernas":[[(0,-.09),(.19,-.22),(.31,-.01)],   [(0,-.09),(.21,-.05),(.34,-.01)]]},
    "brazos_arriba": {"cuello": (0,-.70), "cadera": (0,-.38),
                 # Separados de la cabeza: pegados parecian un marco alrededor
                 # de la cara en vez de dos brazos en alto.
                 "brazos": [[(0,-.66),(-.26,-.76),(-.34,-.96)], [(0,-.66),(.26,-.76),(.34,-.96)]],
                 "piernas":[[(0,-.38),(-.10,-.19),(-.13,0)],    [(0,-.38),(.10,-.19),(.13,0)]]},
    "señala":   {"cuello": (0,-.70), "cadera": (0,-.38),
                 "brazos": [[(0,-.66),(-.12,-.52),(-.15,-.36)], [(0,-.66),(.20,-.64),(.34,-.62)]],
                 "piernas":[[(0,-.38),(-.09,-.19),(-.11,0)],    [(0,-.38),(.09,-.19),(.11,0)]]},
    # Sentado a una mesa: el tronco recto y los antebrazos hacia delante, que
    # es lo que queda ENCIMA del tablero cuando la mesa se pinta despues.
    "en_mesa":  {"cuello": (0,-.52), "cadera": (0,-.26),
                 "brazos": [[(0,-.48),(-.16,-.40),(-.26,-.34)], [(0,-.48),(.16,-.40),(.26,-.34)]],
                 "piernas":[[(0,-.26),(.16,-.26),(.20,-.02)],   [(0,-.26),(.09,-.25),(.11,-.02)]]},
    # Inclinado hacia delante: el cuello va por delante de la cadera. Tieso
    # parecia que trotaba en una cinta, no que corria.
    "corriendo":{"cuello": (.07,-.68), "cadera": (0,-.37),
                 "brazos": [[(.065,-.64),(-.14,-.56),(-.24,-.44)], [(.065,-.64),(.25,-.58),(.37,-.64)]],
                 "piernas":[[(0,-.37),(-.22,-.22),(-.30,-.04)], [(0,-.37),(.16,-.18),(.30,-.10)]]},
    # La otra mitad de la zancada. Correr no es una postura, son dos que se
    # alternan: sin esto el monigote iba en plancha, deslizando.
    "corriendo_b":{"cuello": (.07,-.68), "cadera": (0,-.37),
                 "brazos": [[(.065,-.64),(.27,-.56),(.37,-.44)], [(.065,-.64),(-.11,-.58),(-.23,-.64)]],
                 "piernas":[[(0,-.37),(.20,-.20),(.30,-.06)],  [(0,-.37),(-.18,-.20),(-.28,-.08)]]},

    # ---- VERBOS -----------------------------------------------------------
    #
    # Lo que faltaba, y se veia en el #90: de doce monigotes, SIETE no se
    # movian, y una escena entera estaba congelada. No era culpa del guion.
    # El repertorio no tenia un solo verbo - de_pie, sentado, señala,
    # brazos_arriba, en_mesa, corriendo -, asi que "firmaron el tratado" o
    # "cruzaban el rio" solo se podian dibujar como alguien de pie
    # señalandolo. Un monigote que señala lo que cuentas no es un monigote
    # HACIENDOLO.
    #
    # Las que acaban en _b son la otra mitad de un movimiento que se repite,
    # como corriendo/corriendo_b: remar, cavar, pelear y empujar no son
    # posturas, son ciclos, y se animan solos sin que el guion pida nada.

    # REMAR: tronco echado adelante y brazos estirados, luego tiron al pecho.
    "remando":  {"cuello": (.07,-.50), "cadera": (0,-.14),
                 "brazos": [[(.04,-.46),(.18,-.44),(.32,-.40)], [(.04,-.46),(.18,-.40),(.32,-.36)]],
                 "piernas":[[(0,-.14),(.20,-.17),(.31,-.02)],   [(0,-.14),(.22,-.09),(.34,-.02)]]},
    "remando_b":{"cuello": (-.05,-.51), "cadera": (0,-.14),
                 "brazos": [[(-.03,-.47),(.08,-.40),(-.02,-.34)], [(-.03,-.47),(.10,-.36),(0,-.31)]],
                 "piernas":[[(0,-.14),(.20,-.17),(.31,-.02)],   [(0,-.14),(.22,-.09),(.34,-.02)]]},

    # CAVAR / PICAR: doblado, las dos manos juntas abajo; luego las levanta.
    "cavando":  {"cuello": (.10,-.58), "cadera": (0,-.36),
                 "brazos": [[(.06,-.55),(.18,-.44),(.26,-.24)], [(.06,-.55),(.20,-.42),(.28,-.22)]],
                 "piernas":[[(0,-.36),(-.11,-.18),(-.15,0)],    [(0,-.36),(.12,-.19),(.17,0)]]},
    "cavando_b":{"cuello": (.04,-.64), "cadera": (0,-.37),
                 "brazos": [[(.02,-.61),(.10,-.72),(.02,-.86)], [(.02,-.61),(.13,-.70),(.05,-.84)]],
                 "piernas":[[(0,-.37),(-.11,-.19),(-.15,0)],    [(0,-.37),(.12,-.19),(.17,0)]]},

    # PELEAR: zancada y el brazo de la espada arriba; luego el tajo adelante.
    "peleando": {"cuello": (.05,-.68), "cadera": (0,-.38),
                 "brazos": [[(0,-.64),(-.17,-.57),(-.28,-.52)], [(0,-.64),(.16,-.77),(.27,-.93)]],
                 "piernas":[[(0,-.38),(-.17,-.21),(-.28,0)],    [(0,-.38),(.17,-.23),(.29,0)]]},
    "peleando_b":{"cuello": (.09,-.67), "cadera": (0,-.38),
                 "brazos": [[(0,-.63),(-.15,-.55),(-.24,-.48)], [(0,-.63),(.24,-.62),(.40,-.54)]],
                 "piernas":[[(0,-.38),(-.19,-.20),(-.31,0)],    [(0,-.38),(.19,-.24),(.32,0)]]},

    # EMPUJAR: el cuerpo volcado hacia delante y los dos brazos estirados.
    "empujando":{"cuello": (.12,-.65), "cadera": (0,-.38),
                 "brazos": [[(.04,-.62),(.18,-.61),(.32,-.60)], [(.04,-.62),(.18,-.57),(.32,-.56)]],
                 "piernas":[[(0,-.38),(-.17,-.22),(-.31,-.02)], [(0,-.38),(.11,-.20),(.17,0)]]},
    # La otra mitad es el ARRANQUE, no un temblor: se recoge, dobla los codos
    # y vuelve a volcarse. Medido, la primera version movia 0.045 - o sea
    # nada - y empujar sin recogerse no se lee como empujar.
    "empujando_b":{"cuello": (-.02,-.68), "cadera": (-.04,-.38),
                 "brazos": [[(-.06,-.64),(.04,-.60),(.14,-.62)], [(-.06,-.64),(.04,-.56),(.14,-.58)]],
                 "piernas":[[(-.04,-.38),(-.13,-.22),(-.22,-.01)],[(-.04,-.38),(.13,-.21),(.21,0)]]},

    # FIRMAR / ESCRIBIR: en la mesa pero con una mano garabateando. Para un
    # canal de historia esto sale en uno de cada tres videos - un tratado, una
    # cedula, una sentencia - y no habia forma de dibujarlo.
    "firmando": {"cuello": (.05,-.51), "cadera": (0,-.26),
                 "brazos": [[(.02,-.47),(-.14,-.40),(-.22,-.34)], [(.02,-.47),(.17,-.41),(.27,-.33)]],
                 "piernas":[[(0,-.26),(.16,-.26),(.20,-.02)],   [(0,-.26),(.09,-.25),(.11,-.02)]]},
    # Y firmar tiene que VERSE: el brazo entero barre el papel y la cabeza
    # sigue a la mano. Moviendo solo la punta de la mano medía 0.063, que a
    # tamaño de movil es un pixel y medio.
    "firmando_b":{"cuello": (-.02,-.53), "cadera": (0,-.26),
                 "brazos": [[(.02,-.47),(-.14,-.40),(-.22,-.34)], [(.02,-.47),(.08,-.44),(.10,-.32)]],
                 "piernas":[[(0,-.26),(.16,-.26),(.20,-.02)],   [(0,-.26),(.09,-.25),(.11,-.02)]]},

    # CARGAR: doblado bajo el peso, las manos por encima de los hombros.
    "cargando": {"cuello": (.08,-.62), "cadera": (0,-.36),
                 "brazos": [[(.04,-.58),(-.13,-.66),(-.05,-.74)], [(.04,-.58),(.15,-.66),(.07,-.74)]],
                 "piernas":[[(0,-.36),(-.13,-.20),(-.11,0)],    [(0,-.36),(.13,-.20),(.16,0)]]},

    # CAERSE: todo el cuerpo torcido y los brazos por el aire.
    "cayendose":{"cuello": (-.15,-.64), "cadera": (-.05,-.36),
                 "brazos": [[(-.11,-.60),(-.28,-.71),(-.37,-.87)], [(-.11,-.60),(.09,-.73),(.19,-.88)]],
                 "piernas":[[(-.05,-.36),(-.21,-.25),(-.36,-.15)],[(-.05,-.36),(.11,-.19),(.18,0)]]},

    # MIRAR A LO LEJOS: la mano de visera. El vigia, el que descubre algo.
    "mirando":  {"cuello": (0,-.70), "cadera": (0,-.38),
                 "brazos": [[(0,-.66),(-.14,-.54),(-.13,-.39)], [(0,-.66),(.19,-.73),(.09,-.81)]],
                 "piernas":[[(0,-.38),(-.09,-.19),(-.11,0)],    [(0,-.38),(.09,-.19),(.11,0)]]},

    # REZAR: las manos juntas al pecho y la cabeza un poco baja.
    "rezando":  {"cuello": (.02,-.67), "cadera": (0,-.38),
                 "brazos": [[(0,-.63),(-.13,-.55),(-.02,-.49)], [(0,-.63),(.13,-.55),(.02,-.49)]],
                 "piernas":[[(0,-.38),(-.08,-.19),(-.10,0)],    [(0,-.38),(.08,-.19),(.10,0)]]},

    # DAR / ENTREGAR: el brazo estirado con la mano abierta hacia el otro.
    "dando":    {"cuello": (0,-.70), "cadera": (0,-.38),
                 "brazos": [[(0,-.66),(-.12,-.52),(-.15,-.36)], [(0,-.66),(.21,-.59),(.38,-.55)]],
                 "piernas":[[(0,-.38),(-.09,-.19),(-.11,0)],    [(0,-.38),(.09,-.19),(.11,0)]]},

    # BEBER: la mano con el vaso en la boca. La pone la entrega del vaso: el
    # que lo recibe se lo bebe de golpe.
    "bebiendo_b":{"cuello": (-.02,-.70), "cadera": (0,-.38),
                 "brazos": [[(0,-.66),(-.12,-.52),(-.15,-.36)], [(0,-.66),(.17,-.68),(.10,-.78)]],
                 "piernas":[[(0,-.38),(-.09,-.19),(-.11,0)],    [(0,-.38),(.09,-.19),(.11,0)]]},

    # EN LA CAMA: incorporado, la espalda en el cabecero y las piernas
    # estiradas bajo la colcha. La cama la pone montar(), pegada a quien la
    # usa, como la mesita del que firma: el guion no tiene que cuadrar la x
    # de la cama con la del rey. Para Farinelli y Felipe V, que no salia de
    # ella.
    "en_cama":  {"cuello": (0,-.66), "cadera": (0,-.34),
                 "brazos": [[(0,-.62),(-.09,-.50),(-.01,-.40)], [(0,-.62),(.12,-.50),(.22,-.41)]],
                 "piernas":[[(0,-.34),(.18,-.35),(.36,-.35)],  [(0,-.34),(.18,-.33),(.36,-.33)]]},

    # EN CAMILLA: el mismo cuerpo que en la cama (el respaldo de la camilla
    # va levantado), pero sobre la camilla de ambulancia, y RODANDO: la
    # sacan de casa. Para Maricarmen, y para cualquier herido o enfermo al
    # que se llevan.
    "en_camilla": {"cuello": (0,-.66), "cadera": (0,-.34),
                   "brazos": [[(0,-.62),(-.09,-.50),(-.01,-.40)], [(0,-.62),(.07,-.48),(.14,-.40)]],
                   "piernas":[[(0,-.34),(.18,-.35),(.36,-.35)],  [(0,-.34),(.18,-.33),(.36,-.33)]]},

    # CANTAR: los brazos abiertos como en la opera, y se mecen solos. Las
    # notas musicales las pinta figura() al lado de la cabeza.
    "cantando": {"cuello": (-.02,-.71), "cadera": (0,-.38),
                 "brazos": [[(0,-.66),(-.20,-.67),(-.34,-.76)], [(0,-.66),(.20,-.67),(.34,-.76)]],
                 "piernas":[[(0,-.38),(-.09,-.19),(-.11,0)],    [(0,-.38),(.09,-.19),(.11,0)]]},
    "cantando_b":{"cuello": (.02,-.70), "cadera": (0,-.38),
                 "brazos": [[(0,-.66),(-.18,-.60),(-.30,-.57)], [(0,-.66),(.18,-.60),(.30,-.57)]],
                 "piernas":[[(0,-.38),(-.09,-.19),(-.11,0)],    [(0,-.38),(.09,-.19),(.11,0)]]},

    # ANDAR: como correr pero sin prisa - erguido, paso corto, brazos que
    # acompañan. "El mayordomo entra", "se acerca", "se va": en casi todos
    # los guiones alguien entra o sale, y hasta ahora solo se podia correr.
    "andando":  {"cuello": (.02,-.70), "cadera": (0,-.38),
                 "brazos": [[(.01,-.66),(-.08,-.52),(-.12,-.38)], [(.01,-.66),(.09,-.52),(.14,-.40)]],
                 "piernas":[[(0,-.38),(-.10,-.19),(-.15,0)],    [(0,-.38),(.09,-.20),(.15,-.02)]]},
    "andando_b":{"cuello": (.02,-.70), "cadera": (0,-.38),
                 "brazos": [[(.01,-.66),(.09,-.52),(.14,-.40)], [(.01,-.66),(-.08,-.52),(-.12,-.38)]],
                 "piernas":[[(0,-.38),(.09,-.20),(.15,-.02)],  [(0,-.38),(-.10,-.19),(-.15,0)]]},

    # DE RODILLAS: una rodilla en el suelo y las manos hacia arriba. Ante el
    # rey, suplicando, pidiendo la mano, rindiendose: sale en media historia
    # de España.
    "de_rodillas":{"cuello": (.02,-.55), "cadera": (0,-.25),
                 "brazos": [[(.02,-.51),(.13,-.43),(.21,-.50)], [(.02,-.51),(.11,-.40),(.19,-.46)]],
                 "piernas":[[(0,-.25),(.15,-.25),(.15,0)],     [(0,-.25),(-.05,0),(-.21,0)]]},

    # BAILAR: un brazo arriba, la cadera a un lado y un pie levantado; y al
    # reves. Fiestas, verbenas, el que celebra.
    "bailando": {"cuello": (-.04,-.70), "cadera": (.02,-.38),
                 "brazos": [[(-.03,-.66),(-.17,-.80),(-.10,-.96)], [(-.03,-.66),(.20,-.62),(.31,-.71)]],
                 "piernas":[[(.02,-.38),(-.08,-.19),(-.10,0)],  [(.02,-.38),(.15,-.23),(.09,-.07)]]},
    "bailando_b":{"cuello": (.04,-.70), "cadera": (-.02,-.38),
                 "brazos": [[(.03,-.66),(-.20,-.62),(-.31,-.71)], [(.03,-.66),(.17,-.80),(.10,-.96)]],
                 "piernas":[[(-.02,-.38),(-.15,-.23),(-.09,-.07)], [(-.02,-.38),(.08,-.19),(.10,0)]]},

    # APLAUDIR: las manos se separan y se juntan delante del pecho.
    "aplaudiendo":{"cuello": (0,-.70), "cadera": (0,-.38),
                 "brazos": [[(0,-.66),(-.14,-.56),(-.17,-.63)], [(0,-.66),(.14,-.56),(.17,-.63)]],
                 "piernas":[[(0,-.38),(-.09,-.19),(-.11,0)],    [(0,-.38),(.09,-.19),(.11,0)]]},
    # EL TORTAZO, por dentro: la mano arriba y atras, y luego a la cara del
    # otro. No se ofrecen al guion (acaban en _b): las mueve animar() cuando
    # alguien recibe una "bofetada".
    "alzada_b": {"cuello": (-.03,-.70), "cadera": (0,-.38),
                 "brazos": [[(-.02,-.66),(-.13,-.52),(-.16,-.37)], [(-.02,-.66),(-.06,-.90),(-.16,-1.08)]],
                 "piernas":[[(0,-.38),(-.09,-.19),(-.11,0)],    [(0,-.38),(.11,-.19),(.15,0)]]},
    "bofeton_b":{"cuello": (.06,-.69), "cadera": (0,-.38),
                 "brazos": [[(.04,-.65),(-.10,-.52),(-.14,-.37)], [(.04,-.65),(.26,-.82),(.46,-.94)]],
                 "piernas":[[(0,-.38),(-.12,-.19),(-.16,0)],    [(0,-.38),(.12,-.19),(.18,0)]]},
    "aplaudiendo_b":{"cuello": (0,-.70), "cadera": (0,-.38),
                 "brazos": [[(0,-.66),(-.10,-.56),(-.015,-.61)], [(0,-.66),(.10,-.56),(.015,-.61)]],
                 "piernas":[[(0,-.38),(-.09,-.19),(-.11,0)],    [(0,-.38),(.09,-.19),(.11,0)]]},
}

# Lo que se mueve SOLO: la otra mitad de cada ciclo. El guion no tiene que
# pedirlo - y por eso funciona, porque lo que hay que pedir se olvida.
_CICLOS = {
    "corriendo": "corriendo_b",
    "remando":   "remando_b",
    "cavando":   "cavando_b",
    "peleando":  "peleando_b",
    "empujando": "empujando_b",
    "firmando":  "firmando_b",
    "cantando":  "cantando_b",
    "andando":   "andando_b",
    "bailando":  "bailando_b",
    "aplaudiendo": "aplaudiendo_b",
}


# NADIE SE QUEDA CONGELADO.
#
# En el #90, de doce monigotes SIETE no se movieron: el guion les puso pose y
# no pose_fin, y una postura sin destino y sin ciclo es una foto. Una escena
# entera - la 6 - salio con las dos figuras quietas.
#
# Pedirselo mejor al guion no lo arregla: lleva dos dias demostrado que lo que
# solo esta escrito en el prompt se difumina. Asi que si el guion no dice a
# donde va una figura, se le pone un destino que pega con lo que hace. No es
# inventarse la escena, es no dejarla parada.
# Las que dan por hecho que hay una mesa delante.
_POSES_DE_MESA = ("en_mesa", "firmando")

_ACOMPAÑA = {
    "de_pie":        "señala",
    "señala":        "de_pie",
    "sentado":       "en_mesa",
    "en_mesa":       "sentado",
    "brazos_arriba": "de_pie",
    "mirando":       "señala",
    "rezando":       "de_pie",
    "dando":         "de_pie",
    "cargando":      "de_pie",
    "cayendose":     "de_pie",
    # En la cama tambien se gesticula - con los brazos, sin levantarse
    # (animar() lo compone con _en_cama_con).
    "en_cama":       "señala",
}


# COMO SE LE CUENTAN AL GUION. Aqui, pegado a las posturas, y no copiado a
# mano en el prompt: una lista de posturas que se ofrecen y otra de posturas
# que se saben dibujar es exactamente la forma que ya costo la taberna, el
# arbol y el campo de la gracia.
POSES_EXPLICADAS = {
    "de_pie":        "quieto, de pie",
    "sentado":       "sentado en el suelo o en un banco",
    "en_mesa":       "sentado a una mesa, los brazos encima",
    "brazos_arriba": "los brazos en alto: celebra, se indigna, se rinde",
    "señala":        "señala algo con el brazo estirado",
    "corriendo":     "CORRE Y SE DESPLAZA por el plano, hacia donde mira. SALE corriendo: pose de_pie y pose_fin corriendo (arranca y se va). LLEGA corriendo: pose corriendo y pose_fin la de cuando llega (entra y se para). Corriendo a secas: cruza el plano",
    "remando":       "REMA - cruza un rio, va en galera, escapa en barca",
    "cavando":       "CAVA o PICA - mina, entierra, desentierra, abre una zanja",
    "peleando":      "PELEA con la espada en alto - batalla, duelo, motin",
    "empujando":     "EMPUJA algo pesado con las dos manos",
    "firmando":      "FIRMA o ESCRIBE en una mesa - un tratado, una cedula, una condena",
    "cargando":      "CARGA un peso al hombro, doblado",
    "cayendose":     "SE CAE, se desploma, sale por los aires",
    "mirando":       "OTEA a lo lejos con la mano de visera - vigia, descubre algo",
    "rezando":       "REZA con las manos juntas",
    "dando":         "ENTREGA algo, tiende la mano al otro",
    "en_camilla":    "SE LA LLEVAN EN CAMILLA: tumbado en una camilla de ambulancia que sale rodando hacia donde mira. Para el que sacan de casa, el herido, el enfermo, el desahuciado",
    "en_cama":       "EN LA CAMA, incorporado: la cama se dibuja sola alrededor y ocupa sitio hacia donde mira, asi que ponlo a un lado (x 0.25-0.32) y a los demas al otro (x 0.72 o mas). Para quien no se levanta, esta enfermo, lo despiertan",
    "cantando":      "CANTA con los brazos abiertos, y le salen notas musicales",
    "andando":       "ANDA y se desplaza hacia donde mira. ENTRA andando: pose andando y pose_fin la de cuando llega. SALE andando: pose de_pie y pose_fin andando. Andando a secas: cruza el plano",
    "de_rodillas":   "DE RODILLAS: ante el rey, suplicando, pidiendo la mano, rindiendose",
    "bailando":      "BAILA - fiesta, verbena, celebracion",
    "aplaudiendo":   "APLAUDE - la corte, el publico, los que celebran",
}


def _las_posturas_estan_explicadas() -> None:
    faltan = set(POSES_VALIDAS) - set(POSES_EXPLICADAS)
    sobran = set(POSES_EXPLICADAS) - set(POSES_VALIDAS)
    if faltan or sobran:
        raise RuntimeError(
            f"POSES_EXPLICADAS y POSES_VALIDAS no dicen lo mismo. Sin explicar: "
            f"{sorted(faltan)}. Explicadas y no dibujables: {sorted(sobran)}.")


def _destino(f: dict) -> str | None:
    """A donde va esta figura. Nunca a ningun sitio.

    Tambien cubre el caso de que el guion pida la MISMA postura dos veces,
    que es lo que hizo en el #90 - "señala->señala", "de_pie->de_pie" - y que
    en el log parecia movimiento sin serlo.
    """
    pedido = f.get("pose_fin")
    salida = _una_de(pedido, POSES_VALIDAS, "") if pedido else None
    pose = _una_de(f.get("pose"), POSES_VALIDAS, "de_pie")
    if salida and salida != pose:
        return salida
    # Si el verbo tiene ciclo ya se anima solo en animar(); si no, compañera.
    return None if pose in _CICLOS else _ACOMPAÑA.get(pose)


def _los_ciclos_se_mueven() -> None:
    """Que un verbo se mueva de verdad, comprobado al arrancar.

    No es adorno. Escribi "empujando" y "firmando" a ojo y las dos salieron
    practicamente quietas - 0.045 y 0.063 de altura de figura, o sea un pixel
    y medio en un movil -, y desde fuera eso es indistinguible de una postura
    que funciona: el video sale, nadie peta, y el monigote no hace nada. Que
    es exactamente lo que ella vio en el #90 y yo no.

    Se mide sobre los puntos del esqueleto y no sobre los pixeles, porque la
    respiracion mueve la figura entera unos pixeles y una medida en pixeles no
    distingue eso de un brazo. Ya me paso una vez con el encuadre.
    """
    import math
    minimo = 0.12
    flojos = []
    for a, b in _CICLOS.items():
        for nombre in (a, b):
            if nombre not in _POSES:
                raise RuntimeError(f"El ciclo {a!r} nombra una postura que no existe: {nombre!r}")
        pa, pb = (([_POSES[n]["cuello"], _POSES[n]["cadera"]]
                   + [x for br in _POSES[n]["brazos"] for x in br]
                   + [x for pi in _POSES[n]["piernas"] for x in pi]) for n in (a, b))
        recorrido = max(math.dist(x, y) for x, y in zip(pa, pb))
        if recorrido < minimo:
            flojos.append(f"{a} ({recorrido:.3f})")
    if flojos:
        raise RuntimeError(
            f"Estos verbos casi no se mueven, asi que no son verbos: {', '.join(flojos)}. "
            f"Lo que mas se mueva tiene que recorrer al menos {minimo} de la altura de "
            f"la figura, o a tamaño de movil no se ve.")


_los_ciclos_se_mueven()

def _cara(d, c, r, g, rnd, gesto, tinta=TINTA):
    o = r*0.30
    ojo = max(3, int(r*0.10))
    for lado in (-1, 1):
        cx, cy = c[0]+lado*o, c[1]-r*0.12
        if gesto == "enfadado":
            _linea(d, [(cx-ojo*1.6, cy-ojo*1.8), (cx+ojo*1.6, cy-ojo*0.6)][::lado], g, rnd,
                   color=tinta, temblor=1)
        d.ellipse([cx-ojo, cy-ojo, cx+ojo, cy+ojo], fill=tinta)
    b = (c[0], c[1]+r*0.34)
    if gesto in ("sorpresa", "grito"):
        rr = r*(0.20 if gesto=="sorpresa" else 0.28)
        _circulo(d, b, rr, g, rnd, relleno=tinta, color=tinta)
    elif gesto == "contento":
        d.arc([b[0]-r*.34, b[1]-r*.34, b[0]+r*.34, b[1]+r*.20], 15, 165, fill=tinta, width=g)
    elif gesto == "enfadado":
        d.arc([b[0]-r*.30, b[1]-r*.06, b[0]+r*.30, b[1]+r*.42], 195, 345, fill=tinta, width=g)
    elif gesto == "triste":                  # la boca hacia abajo, grande
        d.arc([b[0]-r*.34, b[1]-r*.02, b[0]+r*.34, b[1]+r*.50], 200, 340, fill=tinta, width=int(g*1.2))
    elif gesto == "asustado":                # la D tumbada y negra: el miedo de los dibujos
        d.chord([b[0]-r*.36, b[1]-r*.10, b[0]+r*.36, b[1]+r*.52], 180, 360, fill=tinta)
    elif gesto == "bostezo":                 # el ovalo enorme, con la lengua
        d.ellipse([b[0]-r*.24, b[1]-r*.22, b[0]+r*.24, b[1]+r*.46], fill=tinta)
        d.ellipse([b[0]-r*.13, b[1]+r*.18, b[0]+r*.13, b[1]+r*.40], fill=(214, 70, 80))
    elif gesto == "riendo":                  # la carcajada: la D grande y los ojos cerrados
        d.chord([b[0]-r*.36, b[1]-r*.14, b[0]+r*.36, b[1]+r*.50], 0, 180, fill=tinta)
        d.chord([b[0]-r*.20, b[1]+r*.16, b[0]+r*.20, b[1]+r*.46], 0, 180, fill=(214, 70, 80))
    elif gesto == "asco":                    # la boca en zigzag
        pts = [(b[0] - r*.30 + k*r*.12, b[1] + (r*.08 if k % 2 else -r*.04)) for k in range(6)]
        _linea(d, pts, g, rnd, color=tinta, temblor=0.6)
    else:
        _linea(d, [(b[0]-r*.22, b[1]), (b[0]+r*.22, b[1])], g, rnd, color=tinta, temblor=1)


# ---- GORROS ----------------------------------------------------------------
# Lo que convierte a un monigote en ALGUIEN. Es todo lo que hace falta: nadie
# necesita una cara parecida para entender que ese es el cura y ese el general.

# Los que ENVUELVEN la cabeza se pintan ANTES que ella, o tapan la cara. Es
# el mismo asunto que la mesa: lo que rodea va detras, lo que se apoya encima
# va delante. La capucha de monje tapaba la cara entera.
GORROS_DETRAS = ("monje", "peineta", "toca")


def _gorro(d, cab, rc, g, rnd, cual):
    x, y = cab
    arriba = y - rc*0.88          # donde apoya, en la coronilla
    oro, rojo, azul = (214,164,40), ROJO, (58,84,150)

    if cual == "corona_grande":
        # La de la reina niña: le queda enorme, se le cae hasta los ojos y va
        # torcida. "Una corona que casi le tapa la cara."
        b, alto_c = rc*1.35, rc*1.05
        base = y - rc*0.30                    # a la altura de las cejas
        inc = rc*0.28                         # torcida: un lado mas bajo
        pts = [(x-b, base + inc), (x-b*.55, base - alto_c + inc*.5), (x-b*.15, base - alto_c*.35),
               (x, base - alto_c*1.05), (x+b*.15, base - alto_c*.35),
               (x+b*.55, base - alto_c - inc*.5), (x+b, base - inc)]
        d.polygon(pts + [(x+b, base - inc + rc*.30), (x-b, base + inc + rc*.30)], fill=(236, 186, 40))
        _linea(d, pts + [(x+b, base - inc + rc*.30), (x-b, base + inc + rc*.30), pts[0]], g, rnd,
               color=(150, 110, 20))
        for k, px in enumerate((-.55, 0, .55)):
            d.ellipse([x + b*px - rc*.12, base - rc*.02 + inc*(-px) - rc*.12 + rc*.15,
                       x + b*px + rc*.12, base - rc*.02 + inc*(-px) + rc*.12 + rc*.15],
                      fill=(ROJO, (40, 110, 200), ROJO)[k])
    elif cual == "corona":
        b = rc*0.95
        _linea(d, [(x-b, arriba), (x-b*.5, arriba-rc*.62), (x, arriba-rc*.05),
                   (x+b*.5, arriba-rc*.62), (x+b, arriba)], g, rnd, color=oro)
    elif cual == "corona_imperial":  # cerrada: arcos, terciopelo rojo y cruz. El emperador
        b = rc*1.0
        base = arriba + rc*0.05
        d.pieslice([x-b*0.9, base-rc*1.15, x+b*0.9, base+rc*0.55], 180, 360, fill=(170, 24, 40))
        for k in (-0.55, 0, 0.55):                       # los arcos
            d.arc([x-b*0.9*abs(k) - rc*0.12 if k else x-rc*0.12, base-rc*1.15,
                   x+b*0.9*abs(k) + rc*0.12 if k else x+rc*0.12, base+rc*0.55], 180, 360,
                  fill=oro, width=g)
        d.rounded_rectangle([x-b, base-rc*0.28, x+b, base+rc*0.05], radius=int(rc*0.08),
                            fill=oro, outline=TINTA, width=max(2, g//2))
        for k, color in ((-0.6, rojo), (0, azul), (0.6, rojo)):   # las piedras
            r = rc*0.09
            d.ellipse([x+b*k-r, base-rc*0.17-r, x+b*k+r, base-rc*0.17+r], fill=color)
        cy = base - rc*1.05                               # la bola y la cruz
        d.ellipse([x-rc*0.13, cy-rc*0.13, x+rc*0.13, cy+rc*0.13], fill=oro, outline=TINTA)
        d.line([(x, cy-rc*0.13), (x, cy-rc*0.55)], fill=oro, width=g)
        d.line([(x-rc*0.18, cy-rc*0.38), (x+rc*0.18, cy-rc*0.38)], fill=oro, width=g)
    elif cual == "comandante":      # bicornio: el de Napoleon, se lee al vuelo
        _linea(d, [(x-rc*1.45, arriba-rc*.10), (x-rc*.30, arriba-rc*.95),
                   (x+rc*.30, arriba-rc*.95), (x+rc*1.45, arriba-rc*.10),
                   (x, arriba+rc*.16), (x-rc*1.45, arriba-rc*.10)], g, rnd, color=azul)
        d.line([(x, arriba-rc*.80), (x, arriba+rc*.10)], fill=rojo, width=g)
    elif cual == "tricornio":       # el XVIII español
        _linea(d, [(x-rc*1.35, arriba), (x, arriba-rc*.92), (x+rc*1.35, arriba),
                   (x, arriba+rc*.22), (x-rc*1.35, arriba)], g, rnd)
    elif cual == "sombrero":        # ala ancha, el del motin
        d.ellipse([x-rc*1.5, arriba-rc*.16, x+rc*1.5, arriba+rc*.16],
                  fill=(255,255,255), outline=TINTA, width=g)
        _linea(d, [(x-rc*.62, arriba), (x-rc*.56, arriba-rc*.78),
                   (x+rc*.56, arriba-rc*.78), (x+rc*.62, arriba)], g, rnd)
    elif cual == "casco":           # morrion de conquistador, con cresta
        _linea(d, [(x-rc*1.15, arriba+rc*.10), (x-rc*.80, arriba-rc*.62),
                   (x+rc*.80, arriba-rc*.62), (x+rc*1.15, arriba+rc*.10)], g, rnd)
        _linea(d, [(x-rc*.55, arriba-rc*.60), (x, arriba-rc*1.15),
                   (x+rc*.55, arriba-rc*.60)], g, rnd)
    elif cual == "mitra":           # obispo, Inquisicion
        _linea(d, [(x-rc*.78, arriba+rc*.08), (x-rc*.60, arriba-rc*.70),
                   (x, arriba-rc*1.45), (x+rc*.60, arriba-rc*.70),
                   (x+rc*.78, arriba+rc*.08), (x-rc*.78, arriba+rc*.08)], g, rnd)
        d.line([(x, arriba-rc*1.30), (x, arriba)], fill=oro, width=g)
    elif cual == "dux":             # el dux de Venecia: el corno ducal, con su cuerno detras
        base = arriba + rc*0.12
        pts = [(x - rc*.80, base), (x - rc*.70, base - rc*.70), (x - rc*.10, base - rc*.95),
               (x + rc*.55, base - rc*1.45), (x + rc*.80, base - rc*.55), (x + rc*.80, base)]
        d.polygon(pts, fill=(236, 186, 40))
        _linea(d, pts + [pts[0]], g, rnd)
        d.line([(x - rc*.80, base - rc*.12), (x + rc*.80, base - rc*.12)], fill=(250, 248, 244),
               width=int(g*1.4))
    elif cual == "tiara":           # el Papa: la triple corona blanca con cruz
        base, alto_t = arriba + rc*0.10, rc*1.45
        cuerpo = [(x - rc*.70, base), (x - rc*.62, base - alto_t*.55), (x - rc*.38, base - alto_t*.92),
                  (x, base - alto_t), (x + rc*.38, base - alto_t*.92), (x + rc*.62, base - alto_t*.55),
                  (x + rc*.70, base)]
        d.polygon(cuerpo, fill=(246, 242, 232))
        _linea(d, cuerpo + [cuerpo[0]], g, rnd)
        for k in (0.18, 0.48, 0.76):                # las tres coronas
            yy = base - alto_t*k
            ancho_k = rc*(.70 - .30*k)
            d.line([(x - ancho_k, yy), (x + ancho_k, yy)], fill=oro, width=int(g*1.3))
        cima = base - alto_t
        d.line([(x, cima), (x, cima - rc*.35)], fill=oro, width=g)
        d.line([(x - rc*.14, cima - rc*.22), (x + rc*.14, cima - rc*.22)], fill=oro, width=g)
    elif cual == "monje":           # capucha que ENVUELVE la cabeza
        pts = []
        for i in range(19):
            a = math.pi + i/18*math.pi          # media vuelta por arriba
            pts.append((x + math.cos(a)*rc*1.34,
                        y + math.sin(a)*rc*1.34 - rc*0.02))
        pts = [(x-rc*1.34, y+rc*0.78)] + pts + [(x+rc*1.34, y+rc*0.78)]
        d.polygon(pts, fill=(146, 116, 82))
        _linea(d, pts, g, rnd, color=(86, 64, 42), temblor=1.4)
    elif cual == "boina":
        _linea(d, [(x-rc*1.0, arriba+rc*.12), (x-rc*.7, arriba-rc*.55),
                   (x+rc*.7, arriba-rc*.55), (x+rc*1.0, arriba+rc*.12),
                   (x-rc*1.0, arriba+rc*.12)], g, rnd, color=rojo)
        d.line([(x+rc*.55, arriba-rc*.62), (x+rc*.75, arriba-rc*.88)], fill=rojo, width=g)
    elif cual == "marinero":        # gorro de pico
        _linea(d, [(x-rc*1.05, arriba+rc*.05), (x, arriba-rc*.75),
                   (x+rc*1.05, arriba+rc*.05)], g, rnd, color=azul)
    elif cual == "peluca":          # la empolvada del XVIII: Borbones, ministros, corte
        blanco = (246, 244, 236)
        d.chord([x-rc*1.05, y-rc*1.08, x+rc*1.05, y+rc*0.30], 180, 360, fill=blanco,
                outline=TINTA, width=max(2, g//2))
        for lado in (-1, 1):
            for k in range(2):
                cx, cy, r = x + lado*rc*1.02, y - rc*0.18 + k*rc*0.46, rc*0.27
                d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=blanco, outline=TINTA, width=max(2, g//2))
    elif cual == "turbante":        # Al-Andalus, el sultan, el embajador
        # Grande y abombado, con las vueltas de tela y la joya delante: pequeño
        # parecia una gorra de marinero.
        tela = (242, 238, 226)
        d.ellipse([x-rc*1.30, arriba-rc*1.30, x+rc*1.30, arriba+rc*0.45],
                  fill=tela, outline=TINTA, width=g)
        for k in range(3):
            y0 = arriba - rc*1.10 + rc*0.42*k
            d.arc([x-rc*1.25, y0, x+rc*1.25, y0 + rc*0.9], 200, 340,
                  fill=(170, 160, 140), width=max(2, g//2))
        d.ellipse([x-rc*0.22, arriba-rc*0.62, x+rc*0.22, arriba-rc*0.18], fill=ROJO,
                  outline=TINTA, width=max(2, g//2))
        _linea(d, [(x, arriba-rc*0.62), (x+rc*0.25, arriba-rc*1.45)], max(2, g//2), rnd,
               color=(40, 110, 90), temblor=0.6)
    elif cual == "chistera":        # el XIX: politicos, banqueros, Isabel II
        negro = (34, 32, 34)
        d.rectangle([x-rc*0.62, arriba-rc*1.30, x+rc*0.62, arriba], fill=negro)
        d.rectangle([x-rc*0.62, arriba-rc*0.36, x+rc*0.62, arriba-rc*0.16], fill=(150, 28, 40))
        d.ellipse([x-rc*1.10, arriba-rc*0.14, x+rc*1.10, arriba+rc*0.14], fill=negro)
    elif cual == "dormir":          # gorro de dormir con borla: recien levantado, en pijama
        # Cae hacia un lado, a rayas, con la borla colgando: se lee como
        # "pijama" al vuelo. Colon saliendo en pijama cuando gritan tierra.
        pts = [(x - rc*1.02, arriba + rc*0.20), (x - rc*0.55, arriba - rc*0.75),
               (x + rc*0.45, arriba - rc*0.95), (x + rc*1.55, arriba - rc*0.05),
               (x + rc*0.95, arriba + rc*0.25)]
        d.polygon(pts, fill=(96, 132, 196))
        for k in (0.30, 0.62):
            a = (x - rc*1.02 + (x + rc*0.45 - x + rc*1.02)*k, arriba + rc*0.2 - rc*1.15*k)
            b = (a[0] + rc*0.75, a[1] + rc*0.55)
            d.line([a, b], fill=(236, 240, 248), width=max(3, int(g*1.4)))
        _linea(d, pts + [pts[0]], g, rnd, temblor=1.2)
        d.rounded_rectangle([x - rc*1.10, arriba - rc*0.05, x + rc*1.10, arriba + rc*0.32],
                            radius=int(rc*0.14), fill=(236, 240, 248), outline=TINTA,
                            width=max(2, g//2))
        _circulo(d, (x + rc*1.60, arriba + rc*0.12), rc*0.26, max(2, g//2), rnd,
                 relleno=(236, 240, 248), color=TINTA)
    elif cual == "toca":            # la toca de monja: velo negro y la cara enmarcada en blanco
        # Detras de la cabeza (GORROS_DETRAS): primero el velo negro hasta
        # los hombros, luego el blanco un poco mas grande que la cara, y la
        # cara se pinta encima - queda el aro blanco alrededor.
        d.polygon([(x - rc*1.30, y + rc*1.85), (x - rc*1.35, y - rc*0.2), (x - rc*0.95, y - rc*1.15),
                   (x, y - rc*1.35), (x + rc*0.95, y - rc*1.15), (x + rc*1.35, y - rc*0.2),
                   (x + rc*1.30, y + rc*1.85)], fill=(28, 26, 30))
        d.ellipse([x - rc*1.16, y - rc*1.16, x + rc*1.16, y + rc*1.22], fill=(248, 248, 244),
                  outline=TINTA, width=max(2, g//2))
    elif cual == "peineta":         # peineta y mantilla: la dama española
        # La mantilla se pinta DETRAS de la cara (ver GORROS_DETRAS), cayendo
        # por los lados hasta los hombros; la peineta asoma por encima.
        mantilla = (36, 30, 34)
        d.polygon([(x - rc*1.25, y + rc*1.75), (x - rc*1.30, y - rc*0.3), (x - rc*0.9, y - rc*1.05),
                   (x, y - rc*1.25), (x + rc*0.9, y - rc*1.05), (x + rc*1.30, y - rc*0.3),
                   (x + rc*1.25, y + rc*1.75)], fill=mantilla)
        carey = (150, 88, 40)
        d.pieslice([x - rc*0.95, arriba - rc*1.25, x + rc*0.95, arriba + rc*0.55], 180, 360,
                   fill=carey, outline=TINTA, width=max(2, g//2))
        for k in range(5):
            a = math.pi + (k + 0.5)*math.pi/5
            d.line([(x, arriba - rc*0.1), (x + math.cos(a)*rc*0.85, arriba - rc*0.35 + math.sin(a)*rc*0.80)],
                   fill=(110, 60, 26), width=max(2, g//2))


def _capa(d, x, cuello, cadera, alto, g, rnd, tinta=TINTA, color=CAPA_COLOR):
    """La capa, colgando de los hombros por DETRAS del cuerpo.

    Un trapecio ancho por abajo y estrecho arriba, del mismo color en los
    dos lados: no hace falta mas para que se lea como tela colgando. Se
    dibuja ANTES que el torso y los brazos, que es la misma regla de
    siempre - lo que rodea va detras, lo que se apoya encima va delante -,
    asi que el cuerpo y los brazos salen por encima de ella, como si la
    llevara puesta y no pegada.
    """
    arriba = alto*0.06
    abajo = cadera[1] + alto*0.32
    pts = [(x-arriba, cuello[1]-alto*0.02), (x+arriba, cuello[1]-alto*0.02),
           (x+alto*0.30, abajo), (x, abajo+alto*0.035), (x-alto*0.30, abajo)]
    d.polygon(pts, fill=color)
    _linea(d, pts + [pts[0]], g, rnd, color=tinta, temblor=1.6)


ARMADURA_COLOR = (150, 150, 158)


def _armadura(d, x, cuello, cadera, alto, g, rnd, tinta=TINTA, color=ARMADURA_COLOR):
    """La coraza: a diferencia de la capa, no cuelga suelta por detras, va
    AJUSTADA al torso - de hombro a cadera y sin volar - para un soldado o
    caballero medieval (Reconquista, batallas de la Independencia...). Misma
    firma que _capa, mismo hueco en figura(): las lineas del cuerpo se
    dibujan encima despues, igual que con la capa, y se siguen viendo.
    """
    arriba, abajo = alto * 0.10, alto * 0.14
    pts = [(x - arriba, cuello[1]), (x + arriba, cuello[1]),
           (x + abajo, cadera[1]), (x - abajo, cadera[1])]
    d.polygon(pts, fill=color)
    _linea(d, pts + [pts[0]], g, rnd, color=tinta, temblor=1.2)
    _linea(d, [(x, cuello[1]), (x, cadera[1])], max(2, g // 2), rnd, color=tinta)


def _manto(d, x, cuello, cadera, alto, g, rnd, tinta=TINTA, color=(128, 24, 48)):
    """El manto real: la capa de rey o de reina, roja, larga y con el borde
    de armiño - blanco con motas negras -, que es lo que la distingue de la
    capa de cualquiera. Con la corona, ya no hace falta decir quien reina."""
    arriba, abajo = alto*0.08, cadera[1] + alto*0.40
    pts = [(x - arriba, cuello[1] - alto*0.02), (x + arriba, cuello[1] - alto*0.02),
           (x + alto*0.34, abajo), (x - alto*0.34, abajo)]
    d.polygon(pts, fill=color)
    _linea(d, pts + [pts[0]], g, rnd, color=tinta, temblor=1.4)
    borde = alto*0.035
    d.rectangle([x - alto*0.34, abajo - borde, x + alto*0.34, abajo + borde], fill=(250, 248, 240))
    for k in range(7):
        px = x - alto*0.30 + alto*0.10*k
        d.ellipse([px - borde*0.3, abajo - borde*0.3, px + borde*0.3, abajo + borde*0.3],
                  fill=tinta)
    d.ellipse([x - arriba*1.4, cuello[1] - alto*0.04, x + arriba*1.4, cuello[1] + alto*0.03],
              fill=(250, 248, 240))


# LO QUE UN PERSONAJE PUEDE LLEVAR PUESTO, por nombre - igual que COSAS y
# _BANDERAS. Ella lo dijo clarisimo viendo la capa: "esto va a ser mas cosas
# en diferentes videos, tienes que estar preparado". Asi que anadir la
# siguiente prenda - un delantal, una venda, lo que pida la proxima historia -
# es escribir una funcion con esta misma firma y meterla aqui, una linea.
# Nada mas se toca: ni figura(), ni limpia(), ni el prompt, que la lee de
# OBJETOS_VALIDOS y no de una lista copiada a mano.
def _gorguera(d, x, cuello, cadera, alto, g, rnd, tinta=TINTA, color=(250, 248, 240)):
    """La gorguera: el cuello de encaje blanco en rueda de los Austrias, el
    de los cuadros de Felipe II y del Siglo de Oro. Con ella el personaje ya
    es del XVI o del XVII sin decir nada."""
    cx, cy, rx, ry = cuello[0], cuello[1] + alto*0.012, alto*0.15, alto*0.052
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=color, outline=tinta, width=max(2, g//2))
    for k in range(10):
        a = k/10*2*math.pi
        d.arc([cx + math.cos(a)*rx*0.7 - rx*0.32, cy + math.sin(a)*ry*0.7 - ry*0.5,
               cx + math.cos(a)*rx*0.7 + rx*0.32, cy + math.sin(a)*ry*0.7 + ry*0.5],
              0, 360, fill=(190, 186, 176), width=max(1, g//3))


def _banda(d, x, cuello, cadera, alto, g, rnd, tinta=TINTA, color=(40, 80, 170)):
    """La banda cruzada al pecho con su medalla: general, rey del XIX,
    presidente. Lo que distingue al que manda cuando ya no hay corona."""
    ancho = alto*0.035
    a = (x - alto*0.10, cuello[1] + alto*0.02)
    b = (x + alto*0.10, cadera[1] + alto*0.01)
    d.polygon([(a[0] - ancho, a[1]), (a[0] + ancho, a[1] - ancho*0.6),
               (b[0] + ancho, b[1]), (b[0] - ancho, b[1] + ancho*0.6)], fill=color, outline=tinta)
    m = (x + alto*0.02, (cuello[1] + cadera[1])/2)
    r = alto*0.028
    d.ellipse([m[0] - r, m[1] - r, m[0] + r, m[1] + r], fill=ORO_ESPAÑA, outline=tinta,
              width=max(2, g//2))


def _banda_espana(d, x, cuello, cadera, alto, g, rnd, tinta=TINTA):
    """La banda con los colores de España: rojo, gualda, rojo. Para cuando
    sale España en persona, o el que va de patriota. Una bandera en la mano,
    con los brazos abajo, le tapaba la cara."""
    _banda(d, x, cuello, cadera, alto, g, rnd, tinta, color=ROJO_ESPAÑA)
    ancho = alto*0.017
    a = (x - alto*0.10, cuello[1] + alto*0.02)
    b = (x + alto*0.10, cadera[1] + alto*0.01)
    d.polygon([(a[0] - ancho, a[1]), (a[0] + ancho, a[1] - ancho*0.6),
               (b[0] + ancho, b[1]), (b[0] - ancho, b[1] + ancho*0.6)], fill=ORO_ESPAÑA)


def _habito(d, x, cuello, cadera, alto, g, rnd, tinta=TINTA, color=(122, 92, 62)):
    """El habito de fraile hasta los pies, con su cordon: frailes, monjes,
    inquisidores. Con "gorro":"monje" es la capucha y el habito entero."""
    abajo = cadera[1] + alto*0.36
    pts = [(x - alto*0.07, cuello[1]), (x + alto*0.07, cuello[1]),
           (x + alto*0.20, abajo), (x - alto*0.20, abajo)]
    d.polygon(pts, fill=color)
    _linea(d, pts + [pts[0]], g, rnd, color=tinta, temblor=1.4)
    d.line([(x - alto*0.10, cadera[1] - alto*0.02), (x + alto*0.10, cadera[1] - alto*0.02)],
           fill=(236, 226, 200), width=max(3, g))
    d.line([(x + alto*0.04, cadera[1] - alto*0.02), (x + alto*0.06, cadera[1] + alto*0.14)],
           fill=(236, 226, 200), width=max(2, g//2))


def _vestido(d, x, cuello, cadera, alto, g, rnd, tinta=TINTA, color=(150, 50, 70)):
    """Vestido largo de mujer, con la falda abierta hasta los pies. Remedios
    era la unica mujer del reparto: con esto cualquier figura es una mujer
    (la que se cruza Juana, la vecina, la criada)."""
    abajo = cadera[1] + alto*0.34
    pts = [(x - alto*0.06, cuello[1] + alto*0.01), (x + alto*0.06, cuello[1] + alto*0.01),
           (x + alto*0.07, cadera[1] - alto*0.04), (x + alto*0.24, abajo),
           (x - alto*0.24, abajo), (x - alto*0.07, cadera[1] - alto*0.04)]
    d.polygon(pts, fill=color)
    _linea(d, pts + [pts[0]], g, rnd, color=tinta, temblor=1.4)
    d.line([(x - alto*0.075, cadera[1] - alto*0.04), (x + alto*0.075, cadera[1] - alto*0.04)],
           fill=tinta, width=max(2, g//2))


def _luto(d, x, cuello, cadera, alto, g, rnd, tinta=TINTA):
    """El mismo vestido, negro: la viuda. Juana de luto por Felipe."""
    _vestido(d, x, cuello, cadera, alto, g, rnd, tinta, color=(34, 32, 36))


def _mano_vendada(d, x, cuello, cadera, alto, g, rnd, tinta=TINTA):
    """No se pinta aqui: va en la MANO, y la mano depende de la postura. La
    pinta figura() despues de los brazos (ver _venda_en_la_mano)."""


def _venda_en_la_mano(d, mano, alto, g, rnd, tinta=TINTA):
    """La mano izquierda de Cervantes en Lepanto: una bola de venda blanca
    con sus vueltas y una mancha roja pequeña. Sin la mancha parecia un
    guante; con mas sangre, el video ya no seria para todos los publicos."""
    x, y = mano
    r = alto*0.075
    caja = [x - r, y - r*0.85, x + r, y + r*0.85]
    d.rounded_rectangle(caja, radius=int(r*0.6), fill=(250, 248, 240), outline=tinta,
                        width=max(2, g//2))
    for k in (-0.4, 0.05, 0.5):
        _linea(d, [(x - r*0.85, y + r*k - r*0.2), (x + r*0.85, y + r*k + r*0.2)],
               max(2, g//3), rnd, color=(190, 184, 172), temblor=0.4)
    d.ellipse([x + r*0.05, y - r*0.35, x + r*0.45, y + r*0.0], fill=(200, 40, 40))


OBJETOS = {
    "capa": _capa,
    "armadura": _armadura,
    "manto": _manto,
    "gorguera": _gorguera,
    "banda": _banda,
    "banda_espana": _banda_espana,
    "habito": _habito,
    "vestido": _vestido,
    "luto": _luto,
    "mano_vendada": _mano_vendada,
}
OBJETOS_VALIDOS = tuple(OBJETOS)
# Las que van por encima de todo, cabeza incluida.
OBJETOS_ENCIMA = ("gorguera",)


def _nota(d, x, y, tam, g, rnd, doble=False):
    """Una nota musical (o dos unidas): cabeza negra inclinada, palito y
    banderin."""
    cabezas = [(x, y)] + ([(x + tam*0.9, y - tam*0.25)] if doble else [])
    for cx, cy in cabezas:
        d.ellipse([cx - tam*0.34, cy - tam*0.24, cx + tam*0.34, cy + tam*0.24], fill=TINTA)
        _linea(d, [(cx + tam*0.30, cy), (cx + tam*0.30, cy - tam*1.25)], g, rnd, temblor=0.6)
    if doble:
        (ax, ay), (bx, by) = cabezas
        d.line([(ax + tam*0.30, ay - tam*1.25), (bx + tam*0.30, by - tam*1.25)],
               fill=TINTA, width=int(g*1.8))
    else:
        _linea(d, [(x + tam*0.30, y - tam*1.25), (x + tam*0.62, y - tam*0.90)], g, rnd,
               temblor=0.6)


def figura(d, x, suelo, alto, rnd, pose="de_pie", gesto="neutro", gorro=None, espejo=False,
           pose_mezclada=None, tinta=TINTA, relleno=(255, 255, 255), rasgos=None, objeto=None):
    p = pose_mezclada or _POSES[pose]
    s = -1 if espejo else 1
    # El ancho separa los brazos y las piernas del eje: la abuela es redonda y
    # el mandamas seco, y eso se ve de lejos. Antes solo engordaba el trazo.
    ancho = (rasgos or {}).get("ancho", 1.0)
    P = lambda t: (x + t[0]*alto*s*ancho, suelo + t[1]*alto)
    rasgos = rasgos or {}
    g = max(5, int(alto*0.022*(0.6 + 0.4*rasgos.get("ancho", 1.0))))
    rc = alto*0.145*rasgos.get("cabeza", 1.0)
    cuello = P(p["cuello"]); cadera = P(p["cadera"])
    if pose == "corriendo":
        # Lineas de velocidad y polvo DETRAS, del lado contrario al que mira:
        # es lo que en un dibujo dice "va rapido" aunque el plano este quieto.
        detras, gris = -s, (150, 146, 140)
        for alto_y, largo in ((0.58, .30), (0.44, .40), (0.30, .26)):
            y0 = suelo - alto*alto_y
            x0 = x + detras*alto*0.20
            _linea(d, [(x0, y0), (x0 + detras*alto*largo, y0)], max(2, int(g*0.7)), rnd,
                   color=gris, temblor=0.8)
        for dx, dy, r in ((0.26, 0.02, 0.040), (0.38, 0.05, 0.030)):
            _circulo(d, (x + detras*alto*dx, suelo - alto*dy), alto*r, max(2, g//2), rnd,
                     relleno=(222, 214, 200), color=gris)
    if pose == "cantando":
        # Las notas suben y bajan con los brazos: la fase sale de por donde va
        # la mano en el ciclo cantando/cantando_b.
        mano = p["brazos"][1][2][1]
        fase = min(1.0, max(0.0, (mano + 0.76) / 0.19))
        for k, (dx, dy, tam) in enumerate(((0.22, 0.98, 0.075), (0.36, 1.06, 0.060),
                                            (-0.24, 1.02, 0.065))):
            sube = alto*0.05*(fase if k % 2 == 0 else 1 - fase)
            _nota(d, x + s*alto*dx, suelo - alto*dy - sube, alto*tam, max(2, int(g*0.8)), rnd,
                  doble=(k == 1))
    dibuja_objeto = OBJETOS.get(objeto)
    if dibuja_objeto and objeto not in OBJETOS_ENCIMA:
        dibuja_objeto(d, x, cuello, cadera, alto, g, rnd, tinta=tinta)
    _linea(d, [cuello, cadera], g, rnd, color=tinta)
    camiseta = rasgos.get("camiseta")
    if camiseta:
        # La camiseta de color de la gente de Why Though: un trapecio sobre el
        # tronco, debajo de los brazos. Da color al folio en blanco y deja
        # distinguir a cada uno de un vistazo.
        ancho_h, ancho_c = alto*0.075*ancho, alto*0.062*ancho
        baja = (cuello[0] + (cadera[0] - cuello[0])*0.05, cuello[1] + (cadera[1] - cuello[1])*0.05)
        tronco = [(baja[0] - ancho_h, baja[1]), (baja[0] + ancho_h, baja[1]),
                  (cadera[0] + ancho_c, cadera[1]), (cadera[0] - ancho_c, cadera[1])]
        d.polygon(tronco, fill=camiseta)
        _linea(d, tronco + [tronco[0]], max(2, int(g*0.8)), rnd, color=tinta, temblor=0.8)
    for m in p["brazos"] + p["piernas"]:
        _linea(d, [P(t) for t in m], g, rnd, color=tinta)
    if objeto == "mano_vendada":
        # La otra mano, la que no coge las cosas: la izquierda.
        _venda_en_la_mano(d, P(p["brazos"][0][-1]), alto, g, rnd, tinta=tinta)
    cab = (cuello[0], cuello[1]-rc*0.95)
    if gorro in GORROS_DETRAS:
        _gorro(d, cab, rc, g, rnd, gorro)
    # El pelo va DETRAS de la cabeza, como la capucha: es lo que asoma por
    # los lados. Y por debajo del gorro, que es del papel de hoy.
    if rasgos.get("pelo", "nada") != "nada":
        _pelo(d, cab, rc, g, rnd, rasgos["pelo"], tinta=tinta)
    # La barba gris del abuelo de Why Though va DETRAS de la cara: asoma por
    # debajo como la de un sabio y deja ver la boca. La de Don Severo y
    # Anselmo, blanca y por delante, es la de España Contada.
    if rasgos.get("barba_gris"):
        _barba(d, (cab[0], cab[1] + rc*0.35), rc*1.05, g, rnd, tinta=tinta, relleno=(196, 196, 200))
    _circulo(d, cab, rc, g, rnd, relleno=relleno, color=tinta)
    _cara(d, cab, rc, g, rnd, gesto, tinta=tinta)
    if rasgos.get("gafas"):
        o = rc*0.30
        for lado in (-1, 1):
            cx, cy = cab[0] + lado*o, cab[1] - rc*0.12
            d.ellipse([cx - rc*0.21, cy - rc*0.21, cx + rc*0.21, cy + rc*0.21], outline=tinta, width=max(2, g//2))
        d.line([(cab[0] - o + rc*0.21, cab[1] - rc*0.14), (cab[0] + o - rc*0.21, cab[1] - rc*0.14)],
               fill=tinta, width=max(2, g//2))
    # Y estos DELANTE de la cara, que es donde estan.
    if rasgos.get("barba"):
        _barba(d, cab, rc, g, rnd, tinta=tinta, relleno=relleno)
    if rasgos.get("parche"):
        _parche(d, cab, rc, g, rnd, tinta=tinta)
    if gorro and gorro not in GORROS_DETRAS:
        _gorro(d, cab, rc, g, rnd, gorro)
    # La gorguera, la ULTIMA: la cabeza descansa sobre ella. Pintada antes que
    # la cabeza, la cara la tapaba entera y no se veia.
    if dibuja_objeto and objeto in OBJETOS_ENCIMA:
        dibuja_objeto(d, x, cuello, cadera, alto, g, rnd, tinta=tinta)
    return cab

def tachado(d, caja, rnd, g):
    x0,y0,x1,y1 = caja
    _linea(d, [(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)], g, rnd)
    _linea(d, [(x0,y0),(x1,y1)], int(g*1.7), rnd, color=ROJO, temblor=3)
    _linea(d, [(x1,y0),(x0,y1)], int(g*1.7), rnd, color=ROJO, temblor=3)

def arbol(d, x, suelo, alto, rnd):
    g = max(5, int(alto*0.05))
    _linea(d, [(x, suelo), (x, suelo-alto*0.70)], g, rnd, color=(112,78,48))
    c = (x, suelo-alto*0.92); r = alto*0.46
    for _ in range(9):
        cx = c[0] + rnd.uniform(-r*.55, r*.55); cy = c[1] + rnd.uniform(-r*.42, r*.42)
        rr = r * rnd.uniform(.34, .62)
        pts = [(cx+math.cos(i/17*2*math.pi)*rr*rnd.uniform(.82,1.18),
                cy+math.sin(i/17*2*math.pi)*rr*.8*rnd.uniform(.82,1.18)) for i in range(18)]
        pts.append(pts[0])
        d.line(pts, fill=(58,138,58), width=max(3,int(g*0.55)), joint="curve")

# QUIEN ES CADA UNO EN ESTA HISTORIA. Ella: "los personajes tienen que ser los
# que estamos usando, pero tiene que parecer la reina". El reparto es fijo -
# Remedios es Remedios en todos los videos -, pero hoy hace de reina, y eso
# el espectador no lo sabe si nadie se lo dice. Asi que el papel sale escrito
# debajo de sus pies la primera vez que aparece, como el rotulo con el nombre
# en un documental. Debajo y no encima: arriba van los globos, y entre el
# 70% y el 80% de la pantalla van los subtitulos.
_LARGO_PAPEL = 24
_ARTICULOS = {"el", "la", "los", "las", "un", "una"}


def clave_de_papel(papel) -> str:
    """El papel sin mayusculas, tildes ni articulo: "La Reina" y "reina" son
    la misma persona. Lo usan el comprobador del guion (el mismo papel, el
    mismo monigote) y la etiqueta (se escribe una vez por papel)."""
    import unicodedata
    t = unicodedata.normalize("NFKD", str(papel or "").lower())
    palabras = "".join(c if c.isalnum() else " " for c in t
                       if not unicodedata.combining(c)).split()
    while palabras and palabras[0] in _ARTICULOS:
        palabras = palabras[1:]
    return " ".join(palabras)


def _pinta_papeles(d, spec, w, h, pies):
    figuras = sorted((f for f in spec.get("figuras", []) if f.get("papel")),
                     key=lambda f: f["x"])
    if not figuras:
        return
    fuente = _fuente_cartel(int(h*0.021))
    ocupado = []                              # (x0, x1, fila) de lo ya puesto
    for f in figuras:
        texto = f["papel"].upper()
        ancho = d.textlength(texto, font=fuente) + h*0.028
        alto = fuente.size*1.55
        x0 = min(max(w*f["x"] - ancho/2, w*0.02), w*0.98 - ancho)
        fila = 0
        while any(fi == fila and not (x0 + ancho < a or x0 > b) for a, b, fi in ocupado):
            fila += 1                         # dos juntos: el segundo, una fila mas abajo
        ocupado.append((x0, x0 + ancho, fila))
        # Nunca por encima del 81,5%: los subtitulos incrustados acaban en el
        # 80% (MarginV = alto/5 en subtitles.py) y suben desde ahi.
        y0 = max(pies + h*0.016, h*0.815) + fila*(alto + h*0.008)
        d.rounded_rectangle([x0, y0, x0 + ancho, y0 + alto], radius=int(alto*0.25),
                            fill=(26, 23, 21))
        d.rectangle([x0, y0 + alto*0.18, x0 + h*0.005, y0 + alto*0.82], fill=(196, 30, 42))
        d.text((x0 + h*0.016, y0 + (alto - fuente.size)/2 - fuente.size*0.08), texto,
               font=fuente, fill=(240, 235, 220))


# DONDE Y CUANDO, ARRIBA. Del video de monigotes de un compañero, lo mejor
# que tenia y lo mas facil de copiar: un cartelito rojo arriba - "Olivenza",
# "20 de mayo de 1801" - que situa al espectador sin gastar ni una palabra de
# voz. Va del 3% al 6% del alto: los globos empiezan hacia el 7%, y los
# subtitulos y las etiquetas estan abajo.
_LARGO_ROTULO = 40


def _pinta_rotulo(d, spec, w, h):
    texto = spec.get("rotulo")
    if not texto:
        return
    px = int(h*0.021)
    fuente = _fuente_cartel(px)
    while d.textlength(texto, font=fuente) > w*0.84 and px > h*0.013:
        px -= 2
        fuente = _fuente_cartel(px)
    ancho = d.textlength(texto, font=fuente) + h*0.034
    alto = fuente.size*1.65
    x0, y0 = (w - ancho)/2, h*0.030
    d.rounded_rectangle([x0, y0, x0 + ancho, y0 + alto], radius=int(alto*0.28),
                        fill=ROJO_ESPAÑA)
    d.text((w/2, y0 + alto/2), texto, font=fuente, fill=(255, 250, 240), anchor="mm")


# LA CAMA VA CON QUIEN ESTA EN ELLA. Como la mesita del que firma: si la
# postura es "en_cama" (al empezar o al acabar la escena), la cama se pinta en
# la x de esa figura, en dos pasadas - cabecero, somier y almohada DETRAS del
# monigote, y la colcha DELANTE, tapandole las piernas. Asi parece que esta
# dentro, en cualquier decorado y sin que el guion cuadre nada.
_ACOSTADAS = ("en_cama", "en_camilla")
_COLCHA = (156, 32, 44)
_EMBOZO = (246, 240, 226)


def _camas(d, spec, h, w, pies_de, rnd, g, parte):
    for f in spec.get("figuras", []):
        if not {f.get("pose"), f.get("pose_fin")} & set(_ACOSTADAS):
            continue
        A = h*f.get("alto", 0.30)
        x, pies = w*f["x"], pies_de(f)
        s = -1 if f.get("espejo") else 1
        if "en_camilla" in (f.get("pose"), f.get("pose_fin")):
            _camilla(d, x, pies, A, s, rnd, g, parte)
            continue
        cab, pie = x - s*A*0.13, x + s*A*0.46
        izq, der = min(cab, pie), max(cab, pie)
        if parte == "detras":
            # Somier y patas.
            d.rectangle([izq, pies - A*0.30, der, pies - A*0.15], fill=MADERA)
            _linea(d, [(izq, pies - A*0.30), (der, pies - A*0.30), (der, pies - A*0.15),
                       (izq, pies - A*0.15), (izq, pies - A*0.30)], g, rnd, temblor=1.2)
            for px in (izq + A*0.03, der - A*0.03):
                _linea(d, [(px, pies - A*0.15), (px, pies)], int(g*1.6), rnd,
                       color=MADERA_OSCURA, temblor=0.8)
            # Cabecero alto, de rey, con remate dorado; y los pies, mas bajos.
            for bx, alto_b in ((cab, 0.80), (pie, 0.42)):
                ancho_b = A*0.075
                d.rounded_rectangle([bx - ancho_b, pies - A*alto_b, bx + ancho_b, pies],
                                    radius=int(ancho_b*0.9), fill=MADERA_OSCURA,
                                    outline=TINTA, width=max(2, g//2))
                d.ellipse([bx - ancho_b*0.8, pies - A*(alto_b + 0.06), bx + ancho_b*0.8,
                           pies - A*(alto_b - 0.02)], fill=ORO_ESPAÑA, outline=TINTA,
                          width=max(2, g//2))
            # La almohada, entre el cabecero y la espalda.
            ax = x - s*A*0.04
            d.rounded_rectangle([ax - A*0.10, pies - A*0.50, ax + A*0.10, pies - A*0.33],
                                radius=int(A*0.06), fill=_EMBOZO, outline=TINTA,
                                width=max(2, g//2))
        else:
            # La colcha: de la cintura a los pies, con el bulto de los pies al
            # final y el embozo blanco doblado arriba.
            x0, x1 = x - s*A*0.07, pie - s*A*0.05
            arriba = pies - A*0.37
            pts = [(x0, arriba), (x + s*A*0.30, arriba + A*0.01),
                   (x1 - s*A*0.06, arriba - A*0.04), (x1, arriba + A*0.02),
                   (x1, pies - A*0.12), (x0, pies - A*0.12)]
            d.polygon(pts, fill=_COLCHA)
            _linea(d, pts + [pts[0]], g, rnd, temblor=1.2)
            d.rectangle([min(x0, x0 + s*A*0.16), arriba + A*0.005,
                         max(x0, x0 + s*A*0.16), pies - A*0.125], fill=_EMBOZO)
            _linea(d, [(x0 + s*A*0.16, arriba + A*0.01), (x0 + s*A*0.16, pies - A*0.12)],
                   max(2, g//2), rnd, temblor=0.8)
            # Una franja dorada, que es la cama de un rey.
            d.line([(x0 + s*A*0.18, pies - A*0.19), (x1, pies - A*0.19)],
                   fill=ORO_ESPAÑA, width=max(3, g))


def _camilla(d, x, pies, A, s, rnd, g, parte):
    """La camilla de ambulancia: tubo de metal, ruedas, colchoneta y sabana
    blanca con su manta azul. Mas baja y mas fina que la cama del rey."""
    cab, pie = x - s*A*0.13, x + s*A*0.46
    izq, der = min(cab, pie), max(cab, pie)
    metal, oscuro = (176, 182, 190), (90, 96, 104)
    if parte == "detras":
        tablero = pies - A*0.20
        d.rectangle([izq, tablero - A*0.10, der, tablero], fill=(236, 238, 240))
        _linea(d, [(izq, tablero), (der, tablero)], int(g*1.4), rnd, color=oscuro, temblor=0.6)
        for px in (izq + A*0.06, der - A*0.06):         # patas en X y ruedas
            _linea(d, [(px - A*0.05, tablero), (px + A*0.05, pies - A*0.03)], g, rnd,
                   color=metal, temblor=0.6)
            _linea(d, [(px + A*0.05, tablero), (px - A*0.05, pies - A*0.03)], g, rnd,
                   color=metal, temblor=0.6)
            for dx in (-A*0.05, A*0.05):
                r = A*0.028
                d.ellipse([px + dx - r, pies - r*2, px + dx + r, pies], fill=TINTA)
        # el respaldo levantado y la almohada
        ax = x - s*A*0.04
        d.rounded_rectangle([ax - A*0.10, pies - A*0.50, ax + A*0.10, pies - A*0.30],
                            radius=int(A*0.06), fill=_EMBOZO, outline=TINTA, width=max(2, g//2))
        _linea(d, [(der + A*0.04 if s < 0 else izq - A*0.04, tablero - A*0.12),
                   (der + A*0.04 if s < 0 else izq - A*0.04, tablero - A*0.02)],
               int(g*1.2), rnd, color=oscuro, temblor=0.6)      # el asa de empujar
    else:
        x0, x1 = x - s*A*0.07, pie - s*A*0.05
        arriba = pies - A*0.37
        pts = [(x0, arriba), (x + s*A*0.30, arriba + A*0.01),
               (x1 - s*A*0.06, arriba - A*0.03), (x1, arriba + A*0.02),
               (x1, pies - A*0.20), (x0, pies - A*0.20)]
        d.polygon(pts, fill=(120, 170, 210))
        _linea(d, pts + [pts[0]], g, rnd, temblor=1.2)
        d.rectangle([min(x0, x0 + s*A*0.14), arriba + A*0.005,
                     max(x0, x0 + s*A*0.14), pies - A*0.205], fill=_EMBOZO)
        for k in (0.30, 0.42):                       # las correas
            cx = x + s*A*k
            d.line([(cx, arriba), (cx, pies - A*0.20)], fill=TINTA, width=max(3, g))


def escena(spec, w=1080, h=1920, semilla=0):
    rnd = random.Random(semilla)
    img = Image.new("RGB", (w, h), (255,255,255)); d = ImageDraw.Draw(img)
    for y0, y1, col in FONDOS[spec.get("fondo","liso")]:
        d.rectangle([0, int(h*y0), w, int(h*y1)], fill=col)
    suelo = int(h*spec.get("suelo", 0.66))
    g_base = max(4, int(w*0.006))
    _sembrar(d, w, h, suelo, spec.get("fondo", "liso"), random.Random(semilla + 77), g_base)
    if spec.get("arbol"): arbol(d, w*spec["arbol"], suelo, h*0.16, rnd)
    g = max(5, int(h*0.006))
    for t in spec.get("tachados", []):
        lado = w*t.get("tam", 0.17)
        cx, cy = w*t["x"], h*t["y"]
        tachado(d, (cx-lado/2, cy-lado/2, cx+lado/2, cy+lado/2), rnd, g)
    def _pinta_cosas(delante):
        for c in spec.get("cosas", []):
            f = COSAS.get(c.get("que"))
            if f is None or bool(c.get("delante")) != delante:
                continue
            tam = h*float(c.get("tam", 0.14))
            # y por defecto: apoyada en el suelo. El sol y las nubes van donde
            # se les diga, que es arriba.
            py = h*float(c["y"]) if c.get("y") is not None else suelo
            f(d, w*float(c.get("x", 0.5)), py, tam, rnd,
              max(4, int(w*0.006)), TINTA_CLARA if oscuro else TINTA)

    oscuro = spec.get("fondo") in _FONDOS_OSCUROS
    tinta = TINTA_CLARA if oscuro else TINTA
    relleno = (38, 44, 66) if oscuro else (255, 255, 255)
    _pinta_cosas(delante=False)
    g_cama = max(4, int(w*0.006))
    _camas(d, spec, h, w, lambda f: suelo, rnd, g_cama, "detras")
    adornos = []
    for f in spec.get("figuras", []):
        alto_f = h*f.get("alto", 0.30)
        adornos.append(_dibuja_figura(
            img, d, f, w*f["x"], suelo + alto_f*_RESPIRACION*f.get("_bocanada", 0.0),
            alto_f, rnd, tinta=tinta, relleno=relleno,
            rasgos=REPARTO.get(f.get("quien") or ""), objeto=f.get("objeto")))
    _camas(d, spec, h, w, lambda f: suelo, rnd, g_cama, "delante")
    _pinta_cosas(delante=True)
    _pinta_adornos(d, adornos, rnd)
    spec["_cabezas"] = [(fx, fy - fa*0.86, fa) for _, fx, fy, fa in adornos]
    _pinta_papeles(d, spec, w, h, suelo)
    _pinta_rotulo(d, spec, w, h)
    return img


def sombrero(d, c, ancho, rnd, g):
    """Sombrero de ala ancha: el objeto por el que ardio Madrid."""
    a = ancho
    d.ellipse([c[0]-a/2, c[1]-a*.10, c[0]+a/2, c[1]+a*.10], fill=(255,255,255), outline=TINTA, width=g)
    _linea(d, [(c[0]-a*.22, c[1]), (c[0]-a*.20, c[1]-a*.34),
               (c[0]+a*.20, c[1]-a*.34), (c[0]+a*.22, c[1])], g, rnd)

def capa(d, c, alto, rnd, g):
    a = alto
    _linea(d, [(c[0]-a*.28, c[1]-a*.46), (c[0]+a*.28, c[1]-a*.46),
               (c[0]+a*.42, c[1]+a*.46), (c[0]-a*.42, c[1]+a*.46),
               (c[0]-a*.28, c[1]-a*.46)], g, rnd)

def bocadillo(d, texto, c, ancho, rnd, apunta_a, fuente):
    alto = ancho*0.46
    x0, y0, x1, y1 = c[0]-ancho/2, c[1]-alto/2, c[0]+ancho/2, c[1]+alto/2
    g = max(5, int(ancho*0.012))
    d.rounded_rectangle([x0,y0,x1,y1], radius=int(alto*0.32), fill=(255,255,255), outline=TINTA, width=g)
    rabo = [(c[0]-ancho*.10, y1-g), (apunta_a[0], apunta_a[1]), (c[0]+ancho*.10, y1-g)]
    d.polygon(rabo, fill=(255,255,255)); _linea(d, rabo, g, rnd, temblor=1.2)
    d.rounded_rectangle([x0+g,y0+g,x1-g,y1-g], radius=int(alto*0.30), fill=(255,255,255))
    caja = d.textbbox((0,0), texto, font=fuente)
    d.text((c[0]-(caja[2]-caja[0])/2, c[1]-(caja[3]-caja[1])/2-caja[1]), texto, font=fuente, fill=TINTA)


# ---- MOVIMIENTO ------------------------------------------------------------
# Esto es lo que el dibujo por IA no podia hacer de ninguna manera: una pose es
# una lista de PUNTOS, asi que entre dos poses hay infinitas intermedias. Se
# interpolan y el monigote se mueve de verdad, no es un zoom sobre una foto
# quieta.

def _mezcla(a, b, t):
    """Una pose intermedia entre dos, con t de 0 a 1."""
    suave = t*t*(3 - 2*t)          # arranca y frena, no a tiron
    lerp = lambda p, q: (p[0]+(q[0]-p[0])*suave, p[1]+(q[1]-p[1])*suave)
    return {
        "cuello": lerp(a["cuello"], b["cuello"]),
        "cadera": lerp(a["cadera"], b["cadera"]),
        "brazos": [[lerp(p, q) for p, q in zip(ma, mb)]
                   for ma, mb in zip(a["brazos"], b["brazos"])],
        "piernas": [[lerp(p, q) for p, q in zip(ma, mb)]
                    for ma, mb in zip(a["piernas"], b["piernas"])],
    }


def _decorado(paso, semilla, tam=None):
    """El sitio donde pasa la escena, elegido por NOMBRE.

    Esto faltaba y era grave: animar() llamaba siempre a interior(), que es el
    monasterio, para cualquier interior. O sea que la taberna estaba
    construida, probada y enseñada... y no se dibujaba nunca. El guion podia
    pedir "taberna" y salia un refectorio.
    """
    w, h = tam or (_ANCHO_BASE, _ALTO_BASE)
    if paso.get("interior"):
        return montar(paso, w, h, semilla=semilla)
    return escena(paso, w, h, semilla=semilla)


def _fuente(alto_img):
    from PIL import ImageFont
    import glob
    for patron in ("/usr/share/fonts/**/DejaVuSans-Bold.ttf",
                   "/usr/share/fonts/**/*Bold*.ttf"):
        for f in glob.glob(patron, recursive=True):
            try:
                return ImageFont.truetype(f, max(22, int(alto_img*0.030)))
            except Exception:
                continue
    return ImageFont.load_default()


def _pinta_bocadillo(img, texto, apunta_x, rnd, fila=0):
    """El globo, DENTRO del propio dibujo.

    Antes se pegaba con ffmpeg encima del plano ya montado. Aqui sale mejor y
    mas simple: como los fotogramas se dibujan de uno en uno y se sabe el
    segundo de cada uno, el globo se pinta solo en los que tocan. La
    sincronia es exacta por construccion, sin filtros ni ventanas.
    """
    w, h = img.size
    d = ImageDraw.Draw(img)
    f = _fuente(h)
    # Que quepa: se parte en lineas antes de dibujar nada.
    palabras, lineas, linea = texto.split(), [], ""
    for p in palabras:
        if d.textlength((linea + " " + p).strip(), font=f) > w*0.68:
            lineas.append(linea.strip()); linea = p
        else:
            linea = (linea + " " + p).strip()
    if linea:
        lineas.append(linea)
    lineas = lineas[:3]
    alto_linea = f.size*1.32
    ancho = max(w*0.30, max(d.textlength(l, font=f) for l in lineas) + w*0.10)
    alto = alto_linea*len(lineas) + h*0.022
    # LA RESPUESTA VA DEBAJO Y DEL LADO DE QUIEN CONTESTA. Los dos globos se
    # pintaban centrados en el mismo sitio, asi que en un dialogo el segundo
    # tapaba al primero y parecia un fallo de dibujo en vez de una
    # conversacion. Se desplaza un poco hacia su monigote - no del todo, que
    # entonces se sale por el borde - y baja una fila.
    cx = w*0.50 + (apunta_x - w*0.50)*0.30
    cx = min(max(cx, w*0.30), w*0.70)
    cy = h*(0.135 + 0.135*fila)
    x0, y0, x1, y1 = cx-ancho/2, cy-alto/2, cx+ancho/2, cy+alto/2
    g = max(4, int(w*0.006))
    d.rounded_rectangle([x0, y0, x1, y1], radius=int(alto*0.30),
                        fill=(255, 255, 255), outline=TINTA, width=g)
    rabo = [(cx-ancho*.09, y1-g//2), (apunta_x, y1 + h*0.075), (cx+ancho*.09, y1-g//2)]
    d.polygon(rabo, fill=(255, 255, 255))
    _linea(d, rabo, g, rnd, temblor=1.0)
    d.line([(cx-ancho*.09, y1-g//2), (cx+ancho*.09, y1-g//2)], fill=(255,255,255), width=g)
    for i, l in enumerate(lineas):
        d.text((cx - d.textlength(l, font=f)/2,
                cy - alto_linea*len(lineas)/2 + i*alto_linea), l, font=f, fill=TINTA)
    return img


# Cada cuanto se repite el movimiento. ESTE ERA EL FALLO del video #84: el
# personaje iba de una pose a otra UNA vez, estirada a lo largo de los cinco
# segundos del plano - y con suavizado al entrar y al salir, asi que se
# pasaba la mayor parte del plano casi quieto. Eso no es animacion, es una
# foto deformandose despacio. Ella lo dijo en dos palabras: "se tiene que
# mover mas".
#
# Segundo y cuarto es el ritmo de un gesto humano: levantar el brazo, bajarlo.
# En un plano de cinco segundos eso son cuatro repeticiones en vez de media.
_SEGUNDOS_POR_CICLO = 1.25

# Nadie esta nunca completamente quieto. Un personaje que no cambia de pose
# sigue respirando y balanceandose un poco, y cada uno con su propio compas -
# si van todos a la vez parecen un coro y canta muchisimo.
_RESPIRACION = 0.012      # de la altura de la figura
_SEGUNDOS_RESPIRACION = 2.3


# CORRER ES IRSE DE SITIO. Ella: "cuando dices sale corriendo deberia parecer
# que el monigote corre". Y no lo parecia: movia las piernas en el mismo
# punto, tieso y a paso de trote, como en una cinta de gimnasio. Correr son
# cuatro cosas a la vez - avanzar, ir inclinado, zancada rapida con saltito y
# polvo detras -, y faltaban tres. La inclinacion esta en la pose; el resto,
# aqui y en figura().
#
# Y segun lo que pida el guion no es la misma carrera:
#   "de_pie" -> "corriendo"   SALE corriendo: arranca en su sitio y se va
#   "corriendo" -> "de_pie"   LLEGA corriendo: entra y se para en su sitio
#   "corriendo" a secas       cruza el plano corriendo
# Hacia donde mira ("espejo") es hacia donde corre.
_SEGUNDOS_PAPEL = 2.2
_SEGUNDOS_POR_ZANCADA = 0.42
_VELOCIDAD_CARRERA = 0.13     # pantallas por segundo
_ARRANQUE = 0.30              # lo que tarda en arrancar o en frenar, del plano


# Andar es lo mismo que correr - entrar, salir, cruzar -, mas despacio, con
# el paso mas largo y sin saltito ni polvo.
_DESPLAZAMIENTOS = {
    # pose: (la otra mitad del paso, pantallas por segundo, segundos por paso, saltito)
    "corriendo": ("corriendo_b", _VELOCIDAD_CARRERA, _SEGUNDOS_POR_ZANCADA, 3.0),
    "andando":   ("andando_b", 0.07, 0.62, 0.6),
    "en_camilla": ("en_camilla", 0.06, 0.62, 0.0),
}


def _carrera(f: dict, reloj: float, segundos: float, desfase: float) -> dict | None:
    pose, fin = f.get("pose"), f.get("pose_fin")
    modo = pose if pose in _DESPLAZAMIENTOS else (fin if fin in _DESPLAZAMIENTOS else None)
    if modo is None:
        return None
    mitad, velocidad, paso, saltito = _DESPLAZAMIENTOS[modo]
    p = min(1.0, max(0.0, reloj/max(segundos, 1e-6)))
    if isinstance(f.get("_hacia"), (int, float)):
        # Va a un sitio concreto (la camilla a la ambulancia) y llega con
        # tiempo de verse alli: en el 70% de la escena, frenando al final.
        q = min(1.0, p/0.70)
        q = 1 - (1 - q)**2
        return {"pose": modo, "pose_mezclada": None, "_bocanada": 0.0,
                "x": f["x"] + (f["_hacia"] - f["x"])*q}
    recorrido = min(velocidad*segundos, 0.55)*(-1 if f.get("espejo") else 1)
    x0 = f["x"]
    zancada = (reloj/paso + desfase) % 1.0
    zancada = 1 - abs(1 - 2*zancada)
    corre = {"pose": modo,
             "pose_mezclada": _mezcla(_POSES[modo], _POSES[mitad], zancada),
             # Un saltito en cada paso: negativo es hacia arriba.
             "_bocanada": -saltito*abs(math.sin(math.pi*reloj/paso))}
    if pose != modo:
        if p < _ARRANQUE:
            return {"x": x0, "pose_mezclada": _mezcla(_POSES.get(pose, _POSES["de_pie"]),
                                                     _POSES[modo], p/_ARRANQUE)}
        x = x0 + (p - _ARRANQUE)/(1 - _ARRANQUE)*recorrido
    elif fin and fin not in (modo, mitad):
        if p >= 1 - _ARRANQUE:
            return {"x": x0, "pose": fin,
                    "pose_mezclada": _mezcla(_POSES[modo], _POSES[fin],
                                             (p - (1 - _ARRANQUE))/_ARRANQUE)}
        x = x0 - (1 - p/(1 - _ARRANQUE))*recorrido
    else:
        x = x0 + (p - 0.5)*recorrido
    corre["x"] = min(0.97, max(0.03, x))
    return corre


# LOS EFECTOS: lo que le PASA al monigote, encima de lo que hace. Ella: "hay
# que meterle mas efectos a los personajes, como el de caerse". En Farinelli
# el remate era "Farinelli se cae al suelo" y no se cayo: la postura
# "cayendose" solo lo torcia de pie. Un monigote que se cae tiene que acabar
# EN EL SUELO, con su pum y sus estrellitas. Van aparte de la postura porque
# se suman a ella: se puede cantar temblando o estar en la cama con Zzz.
EFECTOS_EXPLICADOS = {
    "caida":    "SE CAE AL SUELO de verdad: se va de espaldas, se queda tumbado con estrellitas y suena el pum. Justo al acabar la ultima frase de la escena: el remate, el desmayo, el tortazo",
    "salto":    "SALTA de alegria dando botes con los brazos arriba (con su boing)",
    "temblor":  "TIEMBLA de miedo o de frio, y suda",
    "humo":     "ECHA HUMO por la cabeza de lo enfadado que esta",
    "sorpresa": "da un respingo al empezar la escena y le sale una exclamacion roja encima",
    "zzz":      "DUERME o se muere de aburrimiento: le salen Zzz",
    "lagrimas": "LLORA a chorros",
    "mareo":    "MAREADO: estrellitas dando vueltas alrededor de la cabeza",
    "bofetada": "LE DAN UNA BOFETADA: el que esta mas cerca se le acerca y le pega, suena el ¡ZAS!, se le va la cabeza y se queda con estrellitas. Va en el que la RECIBE, y el que la da tiene que estar en la escena",
    "idea":     "SE LE OCURRE ALGO: se le enciende una bombilla encima. 'Se le ilumina la cara', 'ya se', el plan",
    "confuso":  "NO ENTIENDE NADA: le salen interrogaciones. 'Se queda pensando', 'no entiende nada'",
    "camara":   "MIRA A CAMARA: la camara se le acerca de golpe a la cara, al acabar la ultima frase de la escena. La reaccion: 'mira a camara indignado', 'se queda mirando a camara'",
    "sudor":    "SUDA A CHORROS: le saltan gotas de la cabeza todo el rato. Calor, esfuerzo, nervios, el que acaba de hacer deporte",
    "corona":   "SE SACA UNA CORONA DEL BOLSILLO Y SE LA PONE: empieza sin nada en la cabeza y acaba coronado (con el 'gorro' que lleve, corona si no). El que se proclama rey, 'ya tengo hasta la corona'",
    "entrega":  "LE DA A OTRO LO QUE LLEVA: va con su 'lleva' (el vaso, la carta, la corona), se acerca al que esta mas cerca, estira el brazo y se lo pasa; desde ahi lo tiene el otro. Si es un vaso, el otro se lo bebe de golpe. Va en el que lo DA. 'El sirviente le da un vaso de agua', 'le entrega la carta'",
    "enamorado":"ENAMORADO: le suben corazones. Bodas, reyes que se casan, el que se derrite",
}
EFECTOS_VALIDOS = tuple(EFECTOS_EXPLICADOS)
# Que sonido lleva cada efecto, y cuanto dura. Lo usa visuals para apuntar el
# instante exacto y pipeline para mezclarlo.
SONIDO_DEL_EFECTO = {"caida": ("golpe", 0.9), "salto": ("boing", 0.6), "bofetada": ("zas", 0.4)}
_DURA_CAIDA = 0.45
_DURA_CORONA = 1.0        # del bolsillo a la cabeza


def momento_del_efecto(efecto, segundos, globos=None) -> float:
    """En que segundo de la escena empieza. La caida, al acabar la ULTIMA
    frase - es la reaccion al remate - y si no queda hueco, hacia el final
    igualmente, para que se vea tumbado un rato."""
    if efecto == "camara":
        # MIENTRAS dice su frase mirando a camara, no despues: el zoom al
        # acabar la frase dejaba dos segundos de silencio con la cara quieta,
        # "demasiados parones cuando enfoca".
        ultimo = max((g for g in (globos or []) if g), key=lambda g: float(g["hasta"]), default=None)
        if ultimo is not None:
            return max(0.2, min(float(ultimo["desde"]), segundos - 0.8))
        return max(0.2, min(segundos*0.4, segundos - 0.8))
    if efecto == "bofetada":
        # Entre la primera frase y la segunda ("Señora, eso no se hace" /
        # TORTAZO / "Manos blancas no ofenden"), o al poco de empezar, que al
        # que la da le hace falta medio segundo para llegar.
        orden = sorted((g for g in (globos or []) if g), key=lambda g: float(g["desde"]))
        if len(orden) >= 2:
            return max(0.6, min(float(orden[0]["hasta"]) + 0.1, segundos - 0.8))
        return min(0.6, max(0.3, segundos - 0.8))
    if efecto == "caida":
        fin = max((float(g["hasta"]) for g in (globos or []) if g), default=None)
        tope = max(0.3, segundos - 0.9)
        if fin is not None:
            return max(0.3, min(fin, tope))
        return max(0.3, min(segundos*0.6, tope))
    if efecto == "sorpresa":
        return 0.12
    if efecto == "corona":
        # Mientras dice su primera frase: "De hecho, ya tengo hasta la corona".
        orden = sorted((g for g in (globos or []) if g), key=lambda g: float(g["desde"]))
        if orden:
            return max(0.2, min(float(orden[0]["desde"]) + 0.2, segundos - 1.2))
        return max(0.2, min(segundos*0.3, segundos - 1.2))
    if efecto == "entrega":
        # Nada mas empezar: que se vea el vaso pasar de una mano a otra antes
        # de que el que lo recibe diga su frase.
        return min(0.6, max(0.2, segundos*0.2))
    if efecto == "idea":
        # La bombilla, a mitad de la primera frase: primero se ve apagada y
        # luego se enciende, que es lo que la hace una idea y no una lampara.
        fin = min((float(g["hasta"]) for g in (globos or []) if g), default=None)
        return max(0.4, min(fin*0.5 if fin else segundos*0.3, segundos*0.5))
    return 0.0


def _efecto(f, reloj, segundos):
    """Lo que el efecto le cambia a la figura en este instante."""
    e = f.get("efecto")
    if not e:
        return {}
    t0 = f.get("efecto_desde")
    t0 = momento_del_efecto(e, segundos) if t0 is None else float(t0)
    t = reloj - t0
    s = -1 if f.get("espejo") else 1
    out = {"_reloj": reloj, "_efecto_t": t}
    if e == "caida" and t >= 0:
        p = min(1.0, t/_DURA_CAIDA)
        giro = 90*p*p                              # cae cada vez mas deprisa
        if t > _DURA_CAIDA:                        # y rebota un poco al llegar
            r = t - _DURA_CAIDA
            giro = 90 - 10*math.exp(-r*8)*abs(math.sin(r*16))
        # De espaldas, que es como se cae uno en un dibujo... salvo que por
        # ese lado no quepa: Farinelli, pegado al borde, se cayo fuera de la
        # pantalla y solo se veia una pierna.
        largo = 0.95*f.get("alto", 0.3)*_ALTO_BASE/_ANCHO_BASE
        lado = s
        if not 0.04 <= f.get("x", 0.5) - lado*largo <= 0.96:
            lado = -lado
        out.update({"_giro": giro*lado, "pose": "cayendose", "pose_mezclada": None,
                    "gesto": "sorpresa"})
    elif e == "salto":
        out["_dy"] = -0.13*abs(math.sin(math.pi*reloj/0.55))
        if f.get("pose") not in _ACOSTADAS:
            out.update({"pose": "brazos_arriba", "pose_mezclada": None})
        out["gesto"] = "contento"
    elif e == "temblor":
        out["_dx"] = 0.012*math.sin(2*math.pi*reloj*11)
    elif e == "humo":
        out["_dx"] = 0.006*math.sin(2*math.pi*reloj*7)
        out["gesto"] = "enfadado"
    elif e == "bofetada" and 0 <= t < 0.5:
        # El tortazo: la cabeza se va hacia un lado y vuelve, rapido.
        out["_dx"] = 0.10*math.sin(math.pi*t/0.5)*math.exp(-t*3)*(-s)
        out["gesto"] = "sorpresa"
    elif e == "sorpresa" and 0 <= t < 0.35:
        out["_dy"] = -0.10*math.sin(math.pi*t/0.35)
    elif e == "lagrimas":
        out["gesto"] = f.get("gesto") if f.get("gesto") in ("grito", "enfadado") else "sorpresa"
    elif e == "corona":
        # Sin nada en la cabeza hasta que se la pone. Saca la corona del
        # bolsillo (la mano abajo), la sube con los brazos y al llegar arriba
        # ya es su gorro.
        out["_corona"] = f.get("gorro") if (f.get("gorro") or "").startswith("corona") else "corona"
        if t < _DURA_CORONA:
            out["gorro"] = None
            if t > 0.30:
                q = min(1.0, (t - 0.30)/(_DURA_CORONA - 0.30))
                out["pose_mezclada"] = _mezcla(_POSES["de_pie"], _POSES["brazos_arriba"], q)
        else:
            out["gorro"] = out["_corona"]
            if t < _DURA_CORONA + 0.6:
                out["gesto"] = "contento"
    return out


def _de_noche(img):
    """DE NOCHE: el plano entero en azul oscuro, con luna. "Todo esta oscuro"
    en el barco de Colon, el rey que vive de noche, la conspiracion: los
    decorados son todos de dia y la noche no se podia contar."""
    w, h = img.size
    capa = Image.new("RGB", (w, h), (18, 26, 64))
    img = Image.blend(img, capa, 0.42)
    d = ImageDraw.Draw(img)
    cx, cy, r = w*0.82, h*0.11, w*0.055
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(250, 238, 170))
    d.ellipse([cx - r*1.45, cy - r*1.15, cx + r*0.35, cy + r*0.95], fill=(40, 48, 92))
    return img


_CARA_EN_PANTALLA = 0.13  # lo que ocupa la cara al acabar el zoom, del alto
_DURA_ZOOM = 0.22         # de golpe, como en las comedias


def _caja_del_zoom(paso, tam):
    """El recorte del "mira a camara": de todo el plano a su cara, de golpe.
    La cara queda en el centro y algo por debajo, que arriba van los globos."""
    w, h = tam
    for k, f in enumerate(paso.get("figuras", [])):
        if f.get("efecto") != "camara" or f.get("_efecto_t", -1) < 0:
            continue
        cabezas = paso.get("_cabezas") or []
        if k >= len(cabezas):
            return None
        hx, hy, alto_f = cabezas[k]
        p = min(1.0, f["_efecto_t"]/_DURA_ZOOM)
        p = 1 - (1 - p)**3                      # entra rapido y frena
        # Cuanto acercarse depende de lo grande que sea: con un zoom fijo, a
        # Perico, que es bajito, se le seguia viendo la cara pequeña.
        cara = 2*0.145*alto_f
        zoom = min(3.0, max(1.6, _CARA_EN_PANTALLA*h/max(cara, 1)))
        cw, ch = w/zoom, h/zoom
        x0 = min(max(hx - cw/2, 0), w - cw)
        y0 = min(max(hy - ch*0.45, 0), h - ch)
        return (x0*p, y0*p, w + (x0 + cw - w)*p, h + (y0 + ch - h)*p)
    return None


def _coreografia_del_tortazo(spec, paso, reloj, segundos):
    """El que da la bofetada existe: es el mas cercano al que la recibe. Se
    le acerca, levanta la mano y le pega justo en el instante del efecto.
    Antes solo se veia el ZAS encima de Calomarde y Luisa Carlota quieta en
    la otra punta: "no se entiende lo de la bofetada"."""
    figs = paso.get("figuras", [])
    for k, victima in enumerate(figs):
        if victima.get("efecto") != "bofetada":
            continue
        otros = [(abs(o["x"] - victima["x"]), j) for j, o in enumerate(figs) if j != k]
        if not otros:
            continue
        j = min(otros)[1]
        quien, x0 = figs[j], spec["figuras"][j]["x"]
        t0 = victima.get("efecto_desde")
        t0 = momento_del_efecto("bofetada", segundos) if t0 is None else float(t0)
        lado = 1 if victima["x"] >= x0 else -1      # hacia donde esta la victima
        destino = victima["x"] - lado*0.15
        llegar = max(0.2, t0 - 0.30)
        p = min(1.0, max(0.0, reloj/llegar))
        p = p*p*(3 - 2*p)
        quien["x"] = x0 + (destino - x0)*p
        quien["espejo"] = lado < 0
        quien["efecto"] = None
        if reloj < llegar:
            quien["pose"], quien["pose_mezclada"] = "andando", _mezcla(
                _POSES["andando"], _POSES["andando_b"], (reloj/0.3) % 1.0)
        elif reloj < t0:                            # la mano arriba
            quien["pose_mezclada"] = _mezcla(_POSES["de_pie"], _POSES["alzada_b"],
                                             (reloj - llegar)/max(t0 - llegar, 0.05))
        elif reloj < t0 + 0.12:                     # ¡ZAS!
            quien["pose_mezclada"] = _mezcla(_POSES["alzada_b"], _POSES["bofeton_b"],
                                             (reloj - t0)/0.12)
        else:
            quien["pose_mezclada"] = _mezcla(_POSES["bofeton_b"], _POSES["de_pie"],
                                             min(1.0, (reloj - t0 - 0.12)/0.5))
        quien["gesto"] = "enfadado"
        # Y la cabeza de la victima se va hacia el otro lado del golpe.
        if victima.get("_dx"):
            victima["_dx"] = abs(victima["_dx"])*lado


_LLEGA_ENTREGA = 0.45     # lo que tarda en acercarse con el brazo estirado
_PASA_ENTREGA = 0.25      # las dos manos juntas: aqui cambia de dueño
_BEBE = 1.0               # el trago, de golpe


def _coreografia_de_la_entrega(spec, paso, reloj, segundos):
    """EL QUE DA Y EL QUE RECIBE. "El sirviente le da un vaso de agua": el
    vaso tiene que pasar de una mano a otra, y no aparecer en la de Felipe.
    El que lo da se acerca al que tiene mas cerca con el brazo estirado,
    el otro estira el suyo, y en cuanto se juntan las manos el vaso es del
    otro. Si es un vaso, se lo bebe de golpe."""
    figs = paso.get("figuras", [])
    for k, da in enumerate(figs):
        if spec["figuras"][k].get("efecto") != "entrega" or not spec["figuras"][k].get("lleva"):
            continue
        otros = [(abs(o["x"] - da["x"]), j) for j, o in enumerate(figs) if j != k]
        if not otros:
            continue
        j = min(otros)[1]
        recibe, x0 = figs[j], spec["figuras"][k]["x"]
        que = spec["figuras"][k]["lleva"]
        t0 = da.get("efecto_desde")
        t0 = momento_del_efecto("entrega", segundos) if t0 is None else float(t0)
        t = reloj - t0
        lado = 1 if recibe["x"] >= x0 else -1
        # Las manos se juntan: el brazo de "dando" llega a 0.38 del alto de
        # cada uno, asi que se para a esa distancia y no encima del otro.
        alcance = 0.38*(da.get("alto", 0.3) + recibe.get("alto", 0.3))*_ALTO_BASE/_ANCHO_BASE
        destino = recibe["x"] - lado*max(0.12, min(alcance*0.85, abs(recibe["x"] - x0)))
        da["espejo"] = lado < 0
        da["efecto"] = None
        if t < 0:
            da["lleva"] = que
            recibe["lleva"] = recibe.get("lleva") if recibe.get("lleva") != que else None
            continue
        p = min(1.0, t/_LLEGA_ENTREGA)
        p = p*p*(3 - 2*p)
        da["x"] = x0 + (destino - x0)*p
        tiende = _mezcla(_POSES["de_pie"], _POSES["dando"], p)
        if t < _LLEGA_ENTREGA + _PASA_ENTREGA:
            da["lleva"], da["pose"], da["pose_mezclada"] = que, "dando", tiende
            if recibe.get("pose") not in _ACOSTADAS + _POSES_DE_MESA:
                q = p
                recibe["espejo"] = lado > 0
                recibe["pose_mezclada"] = _mezcla(_POSES["de_pie"], _POSES["dando"], q)
            continue
        # Ya es del otro: el que lo daba baja el brazo.
        t1 = t - _LLEGA_ENTREGA - _PASA_ENTREGA
        da["lleva"] = None
        da["pose_mezclada"] = _mezcla(_POSES["dando"], _POSES["de_pie"], min(1.0, t1/0.4))
        recibe["lleva"] = que
        if recibe.get("pose") in _ACOSTADAS + _POSES_DE_MESA:
            continue
        recibe["espejo"] = lado > 0
        if que == "vaso" and t1 < 0.25 + _BEBE + 0.3:
            # A la boca, el trago y abajo otra vez.
            if t1 < 0.25:
                recibe["pose_mezclada"] = _mezcla(_POSES["dando"], _POSES["bebiendo_b"], t1/0.25)
            elif t1 < 0.25 + _BEBE:
                recibe["pose_mezclada"] = _POSES["bebiendo_b"]
                recibe["_dy"] = recibe.get("_dy", 0.0) - 0.01*abs(math.sin(math.pi*(t1 - 0.25)/0.33))
            else:
                recibe["pose_mezclada"] = _mezcla(_POSES["bebiendo_b"], _POSES["de_pie"],
                                                  (t1 - 0.25 - _BEBE)/0.3)
        elif t1 < 0.4:
            recibe["pose_mezclada"] = _mezcla(_POSES["dando"], _POSES["de_pie"], t1/0.4)


def _en_cama_con(nombre):
    """Los brazos de otra postura sin salir de la cama: el rey en la cama
    que levanta los brazos no se pone de pie para hacerlo."""
    base, otra = _POSES["en_cama"], _POSES.get(nombre, _POSES["de_pie"])
    dx = base["cuello"][0] - otra["cuello"][0]
    dy = base["cuello"][1] - otra["cuello"][1]
    return {"cuello": base["cuello"], "cadera": base["cadera"],
            "brazos": [[(px + dx, py + dy) for px, py in b] for b in otra["brazos"]],
            "piernas": base["piernas"]}


def _estrella(d, cx, cy, r, g):
    pts = []
    for k in range(10):
        a = -math.pi/2 + k*math.pi/5
        rr = r if k % 2 == 0 else r*0.45
        pts.append((cx + math.cos(a)*rr, cy + math.sin(a)*rr))
    d.polygon(pts, fill=(255, 214, 40), outline=TINTA)


def _adornos_de_efecto(d, f, x, y, alto, rnd):
    """Lo que se dibuja alrededor: estrellitas, humo, Zzz, lagrimas..."""
    e = f.get("efecto")
    if not e:
        return
    reloj, t = f.get("_reloj", 0.0), f.get("_efecto_t", 0.0)
    rasgos = REPARTO.get(f.get("quien") or "") or {}
    s = -1 if f.get("espejo") else 1
    p = f.get("pose_mezclada") or _POSES.get(f.get("pose") or "de_pie", _POSES["de_pie"])
    rc = alto*0.145*rasgos.get("cabeza", 1.0)
    hx = x + p["cuello"][0]*alto*s*rasgos.get("ancho", 1.0)
    hy = y + p["cuello"][1]*alto - rc*0.95
    giro = math.radians(f.get("_giro", 0.0))
    if giro:                                   # la cabeza, donde ha caido
        dx, dy = hx - x, hy - y
        hx = x + dx*math.cos(giro) + dy*math.sin(giro)
        hy = y - dx*math.sin(giro) + dy*math.cos(giro)
    g = max(2, int(alto*0.012))
    if e == "sudor":
        # Gotas que salen de la frente hacia los lados y caen, en bucle.
        for k in range(5):
            fase = (reloj*1.3 + k/5) % 1.0
            lado = -1 if k % 2 else 1
            ax = hx + lado*rc*(0.55 + 0.9*fase)
            ay = hy - rc*0.6 + rc*(-0.4*math.sin(math.pi*fase) + 1.6*fase*fase)
            r = rc*0.15
            d.polygon([(ax, ay - r*1.8), (ax + r, ay), (ax, ay + r), (ax - r, ay)], fill=(110, 180, 235),
                      outline=(60, 120, 180))
    if e == "corona" and 0 <= t < _DURA_CORONA + 0.4:
        if t < _DURA_CORONA:
            mx, my = p["brazos"][1][-1]
            mano = (x + mx*alto*s*rasgos.get("ancho", 1.0), y + my*alto)
            cima = (hx, hy)
            q = 0.0 if t < 0.30 else min(1.0, (t - 0.30)/(_DURA_CORONA - 0.30))
            q = q*q*(3 - 2*q)
            cx = mano[0] + (cima[0] - mano[0])*q
            cy = mano[1] + (cima[1] - mano[1])*q
            tam = rc*(0.55 + 0.45*q)              # en la mano, mas pequeña
            _gorro(d, (cx, cy), tam, g, rnd, f.get("_corona") or "corona")
        else:                                     # el destello al ponersela
            r = rc*(0.5 + (t - _DURA_CORONA)*1.5)
            for k in range(8):
                a = k*math.pi/4
                d.line([(hx + math.cos(a)*r*0.6, hy - rc*0.9 + math.sin(a)*r*0.6),
                        (hx + math.cos(a)*r, hy - rc*0.9 + math.sin(a)*r)],
                       fill=(255, 210, 60), width=max(2, g))
    if e == "bofetada" and 0 <= t < 0.35:
        # El impacto en la mejilla, del lado de donde viene la mano: una
        # estrella amarilla grande. Sin ella no se leia como un golpe.
        de_donde = -1 if f.get("_dx", 0.0) > 0 else 1
        cx, cy, r = hx + de_donde*rc*0.95, hy + rc*0.05, rc*(0.9 - t)
        pts = []
        for k in range(16):
            a = k*math.pi/8
            rr = r if k % 2 == 0 else r*0.45
            pts.append((cx + math.cos(a)*rr, cy + math.sin(a)*rr))
        d.polygon(pts, fill=(255, 220, 40), outline=(210, 30, 40))
        for k in range(3):                           # lineas del manotazo
            yy = cy - rc*0.5 + k*rc*0.5
            d.line([(cx + de_donde*rc*1.1, yy), (cx + de_donde*rc*2.2, yy - rc*0.25)],
                   fill=TINTA, width=max(2, g))
    if e == "bofetada" and 0 <= t < 0.6:
        fuente = _fuente_cartel(int(alto*0.15))
        d.text((hx + s*rc*1.8, hy - rc*0.9), "¡ZAS!", font=fuente, anchor="mm",
               fill=(210, 30, 40), stroke_width=max(3, g*2), stroke_fill=(255, 255, 255))
    if e == "caida" and t >= _DURA_CAIDA or e == "mareo" or (e == "bofetada" and t >= 0.5):
        vuelta = reloj*5.5
        for k in range(3):
            a = vuelta + k*2*math.pi/3
            _estrella(d, hx + math.cos(a)*rc*1.35, hy - rc*0.9 + math.sin(a)*rc*0.45,
                      rc*0.28, g)
    if e == "caida" and _DURA_CAIDA <= t < _DURA_CAIDA + 0.5:
        # El golpe: polvo a ras de suelo y un PUM que dura medio segundo.
        r = (t - _DURA_CAIDA)/0.5
        cae = 1 if f.get("_giro", 0.0) > 0 else -1
        for k in (-1, 1):
            cx = x - cae*alto*0.45 + k*alto*(0.15 + 0.25*r)
            _circulo(d, (cx, y - alto*0.03), alto*(0.04 + 0.03*r), g, rnd,
                     relleno=(222, 214, 200), color=(150, 146, 140))
        fuente = _fuente_cartel(int(alto*0.16))
        # Alto, por encima de camas y mesas: a ras de suelo lo tapaba la colcha.
        d.text((x - cae*alto*0.45, y - alto*0.80), "¡PUM!", font=fuente, anchor="mm",
               fill=(210, 30, 40), stroke_width=max(3, g*2), stroke_fill=(255, 255, 255))
    elif e == "humo":
        for k in range(3):
            fase = (reloj*1.3 + k/3) % 1.0
            r = rc*(0.22 + 0.35*fase)
            cx = hx + s*rc*(0.2 + 0.5*fase)*(1 if k % 2 else -1)
            _circulo(d, (cx, hy - rc*1.3 - fase*alto*0.28), r, g, rnd,
                     relleno=(200, 198, 196), color=(130, 128, 126))
    elif e == "temblor":
        for k, lado in enumerate((-1, 1)):
            fase = (reloj*1.6 + k*0.5) % 1.0
            gx, gy = hx + lado*rc*1.25, hy - rc*0.4 + fase*rc*0.9
            d.polygon([(gx, gy - rc*0.28), (gx + rc*0.13, gy), (gx, gy + rc*0.12),
                       (gx - rc*0.13, gy)], fill=(120, 180, 235), outline=TINTA)
    elif e == "sorpresa" and t >= 0:
        fuente = _fuente_cartel(int(alto*0.20))
        d.text((hx, hy - rc*2.1), "!", font=fuente, anchor="mm", fill=(210, 30, 40),
               stroke_width=max(3, g*2), stroke_fill=(255, 255, 255))
    elif e == "zzz":
        fuente_base = int(alto*0.07)
        for k in range(3):
            fase = (reloj*0.6 + k/3) % 1.0
            fuente = _fuente_cartel(max(10, int(fuente_base*(0.7 + 0.8*fase))))
            d.text((hx + s*rc*(1.0 + 1.6*fase), hy - rc*(1.0 + 2.2*fase)), "Z", font=fuente,
                   anchor="mm", fill=(40, 70, 140), stroke_width=max(2, g),
                   stroke_fill=(255, 255, 255))
    elif e == "idea":
        # La bombilla: se enciende con un destello y los rayos laten.
        bx, by, br = hx, hy - rc*2.25, rc*0.52
        encendida = t >= 0
        d.ellipse([bx - br, by - br, bx + br, by + br],
                  fill=(255, 226, 70) if encendida else (236, 236, 226), outline=TINTA, width=g)
        d.rectangle([bx - br*0.42, by + br*0.85, bx + br*0.42, by + br*1.35],
                    fill=(170, 170, 170), outline=TINTA, width=max(2, g//2))
        if encendida:
            late = 1.0 + 0.18*math.sin(reloj*9)
            for k in range(8):
                a = -math.pi/2 + (k - 3.5)*math.pi/7.5
                _linea(d, [(bx + math.cos(a)*br*1.35, by + math.sin(a)*br*1.35),
                           (bx + math.cos(a)*br*1.35*late*1.35, by + math.sin(a)*br*1.35*late*1.35)],
                       g, rnd, color=(230, 170, 20), temblor=0.5)
    elif e == "confuso":
        fuente = _fuente_cartel(int(alto*0.13))
        for k, (dx, dy) in enumerate(((-0.9, -1.9), (0.3, -2.4), (1.2, -1.8))):
            baila = rc*0.18*math.sin(reloj*4 + k*2.1)
            d.text((hx + dx*rc, hy + dy*rc + baila), "?", font=fuente, anchor="mm",
                   fill=(40, 70, 150), stroke_width=max(3, g*2), stroke_fill=(255, 255, 255))
    elif e == "enamorado":
        for k in range(3):
            fase = (reloj*0.7 + k/3) % 1.0
            cx = hx + rc*(-0.9 + 0.9*k) + rc*0.3*math.sin(reloj*3 + k)
            cy = hy - rc*(1.2 + 2.4*fase)
            r = rc*(0.22 + 0.12*(1 - fase))
            d.ellipse([cx - r, cy - r, cx, cy], fill=(220, 40, 70))
            d.ellipse([cx, cy - r, cx + r, cy], fill=(220, 40, 70))
            d.polygon([(cx - r, cy - r*0.45), (cx + r, cy - r*0.45), (cx, cy + r*0.9)],
                      fill=(220, 40, 70))
    elif e == "lagrimas":
        # A CHORROS: dos surtidores en arco desde los ojos. Con gotitas
        # sueltas no se veia a tamaño de movil.
        for lado in (-1, 1):
            for k in range(5):
                fase = (reloj*1.8 + k/5) % 1.0
                gx = hx + lado*rc*(0.30 + 1.1*fase)
                gy = hy - rc*0.05 + rc*(2.6*fase*fase - 0.5*fase)
                rr = rc*0.17
                d.ellipse([gx - rr, gy - rr*1.5, gx + rr, gy + rr], fill=(80, 150, 230),
                          outline=TINTA)


# LO QUE SE LLEVA EN LA MANO. "Cuando coge el catalejo": las cosas estaban
# en el suelo o flotando, nunca en la mano de nadie. Ahora una figura puede
# llevar una, y va donde este su mano en cada fotograma - si señala, la
# carta va con el brazo. El catalejo es especial: va al ojo, que es como se
# usa, y el que lo lleva se pone la mano de visera.
LLEVABLES_EXPLICADOS = {
    "catalejo":  "el catalejo, mirando por el: '¡tierra!', el vigia, el almirante",
    "carta":     "una carta con lacre: noticias, ordenes, la declaracion de guerra",
    "pergamino": "un pergamino: el tratado, la ley, la bula",
    "dinero":    "la bolsa del dinero: el premio, el soborno, los impuestos",
    "espada":    "la espada en la mano",
    "antorcha":  "una antorcha",
    "libro":     "un libro",
    "naranjas":  "naranjas",
    "pan":       "una hogaza de pan",
    "cesta":     "una cesta",
    "bandera_espana": "una bandera en la mano (vale cualquier bandera_ de las cosas)",
    "pancarta":  "una pancarta de manifestacion: protestas, la vivienda, las huelgas",
    "movil":     "un movil en la mano: el Bizum, la foto, el que lo graba todo",
    "periodico": "un periodico: ultima hora, la noticia, el que lo lee en alto",
    "pelota":    "una pelota en la mano: el juego de pelota, el partido",
    "vaso":      "un vaso de agua en la mano: el que bebe, el que pide agua",
    "maletin":   "el maletin negro del medico: medicos, curanderos, boticarios",
    "calendario": "una hoja de calendario (OCTUBRE, el 15 grande y el 4 tachado) en la mano: fechas, el cambio de calendario de 1582",
    "ataud":     "el ataud AL HOMBRO, como quien carga un muerto: Juana la Loca, entierros, el cortejo",
}
_TAM_LLEVADO = {"pelota": 0.14, "vaso": 0.17, "maletin": 0.22, "calendario": 0.32, "espada": 0.40, "antorcha": 0.30, "bandera": 0.50, "pergamino": 0.20,
                "carta": 0.16, "dinero": 0.18, "libro": 0.16, "cesta": 0.20,
                "pancarta": 0.60, "movil": 0.16, "periodico": 0.26}


def _llevable(que) -> str | None:
    que = (que or "").strip().lower()
    if que in LLEVABLES_EXPLICADOS or (que.startswith("bandera") and que in COSAS):
        return que if COSAS.get(que) or que == "catalejo" else None
    return None


def _catalejo_al_ojo(d, x, y, alto, s, g):
    laton = (206, 164, 70)
    tramos = ((0.00, 0.13, .030), (0.12, 0.25, .025), (0.24, 0.36, .020))
    for k, (a, b, r) in enumerate(tramos):
        x0, x1 = x + s*alto*a, x + s*alto*b
        d.rectangle([min(x0, x1), y - alto*r, max(x0, x1), y + alto*r],
                    fill=laton if k != 1 else (178, 136, 56), outline=TINTA, width=max(2, g//2))
    punta = x + s*alto*0.36
    d.ellipse([punta - alto*0.012, y - alto*0.02, punta + alto*0.012, y + alto*0.02],
              fill=(150, 190, 220), outline=TINTA)


def _pinta_llevado(d, f, x, y, alto, rnd, rasgos):
    que = f.get("lleva")
    if not que:
        return
    p = f.get("pose_mezclada") or _POSES.get(f.get("pose") or "de_pie", _POSES["de_pie"])
    s = -1 if f.get("espejo") else 1
    anc = (rasgos or {}).get("ancho", 1.0)
    g = max(4, int(alto*0.018))
    if que == "ataud":
        # Al hombro, no en la mano: tumbado sobre el hombro, un poco por
        # detras de la cabeza, y se mueve con el que lo carga (corre, se cae).
        cx = x + p["cuello"][0]*alto*s*anc
        cy = y + p["cuello"][1]*alto + alto*0.03
        _ataud(d, cx - s*alto*0.12, cy, alto*0.42, rnd, max(3, int(alto*0.012)))
        return
    if que == "catalejo":
        rc = alto*0.145*(rasgos or {}).get("cabeza", 1.0)
        hx = x + p["cuello"][0]*alto*s*anc
        hy = y + p["cuello"][1]*alto - rc*0.95
        _catalejo_al_ojo(d, hx + s*rc*0.30, hy - rc*0.10, alto, s, g)
        return
    mx, my = p["brazos"][1][-1]
    hx, hy = x + mx*alto*s*anc, y + my*alto
    clase = "bandera" if que.startswith("bandera") else que
    tam = alto*_TAM_LLEVADO.get(clase, 0.18)
    dibuja = COSAS.get(que)
    if dibuja:
        # La mano lo coge por abajo: el palo de la bandera, la empuñadura, el
        # borde de la carta.
        agarre = 0.15 if clase in ("bandera", "espada", "antorcha", "pancarta") else 0.45
        dibuja(d, hx, hy + tam*agarre, tam, rnd, max(3, g))


# Lo que se lleva al hombro va DETRAS del cuerpo: el ataud pintado encima le
# tapaba la cara al que lo cargaba.
_LLEVADOS_DETRAS = ("ataud",)


def _dibuja_figura(img, d, f, x, y, alto, rnd, **kw):
    """figura() con su efecto: movida, girada si se ha caido, y con sus
    adornos. La que se cae se pinta en una capa aparte y se gira entera
    sobre los pies, que es lo que hace que caiga y no que se tuerza."""
    x += f.get("_dx", 0.0)*alto
    y += f.get("_dy", 0.0)*alto
    args = (alto, rnd, f.get("pose", "de_pie"), f.get("gesto", "neutro"), f.get("gorro"),
            f.get("espejo", False), f.get("pose_mezclada"))
    giro = f.get("_giro", 0.0)
    if giro:
        capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
        dc = ImageDraw.Draw(capa)
        # Lo que lleva cae con el: el ataud de Juana se cae con quien lo carga.
        if f.get("lleva") in _LLEVADOS_DETRAS:
            _pinta_llevado(dc, f, x, y, alto, rnd, kw.get("rasgos"))
        figura(dc, x, y, *args, **kw)
        if f.get("lleva") not in _LLEVADOS_DETRAS:
            _pinta_llevado(dc, f, x, y, alto, rnd, kw.get("rasgos"))
        capa = capa.rotate(giro, center=(x, y), resample=Image.BICUBIC)
        img.paste(capa, (0, 0), capa)
    else:
        if f.get("lleva") in _LLEVADOS_DETRAS:
            _pinta_llevado(d, f, x, y, alto, rnd, kw.get("rasgos"))
        figura(d, x, y, *args, **kw)
        if f.get("lleva") not in _LLEVADOS_DETRAS:
            _pinta_llevado(d, f, x, y, alto, rnd, kw.get("rasgos"))
    # Los adornos (el PUM, las estrellitas, el humo) NO van aqui: van al
    # final, encima de la colcha y de las mesas de delante, que si no los
    # tapaban. Se devuelve donde pintarlos.
    return (f, x, y, alto)


def _pinta_adornos(d, pendientes, rnd):
    for f, x, y, alto in pendientes:
        _adornos_de_efecto(d, f, x, y, alto, rnd)


def animar(spec, segundos=2.5, fps=15, vaiven=True, bocadillo=None, bocadillos=None, tam=None,
           calma=1.0):
    """Los fotogramas de una escena donde cada figura va de 'pose' a 'pose_fin'.

    El temblor de la linea cambia cada tres fotogramas y no cada uno: cada uno
    parpadea y marea, y quieto parece un PDF. Tres es el hervor de la
    animacion dibujada a mano de toda la vida.
    """
    total = max(2, int(segundos*fps))
    for n in range(total):
        reloj = n/fps
        # El movimiento se REPITE cada ciclo en vez de estirarse por el plano.
        t = (reloj % _SEGUNDOS_POR_CICLO)/_SEGUNDOS_POR_CICLO
        if vaiven:
            t = 1 - abs(1 - 2*t)   # va y vuelve, para que el bucle no salte
        paso = dict(spec)
        paso["figuras"] = []
        for k, f in enumerate(spec.get("figuras", [])):
            g = dict(f)
            fin = f.get("pose_fin")
            # Cada figura con su propio desfase: si el movimiento de las tres
            # empieza en el mismo fotograma parecen marionetas de un hilo.
            desfase = k*0.37
            # calma > 1: el vaiven entre postura y postura va mas despacio
            # (el video largo, que es para dormirse; en el Short, 1).
            tk = (reloj/(_SEGUNDOS_POR_CICLO*calma) + desfase) % 1.0
            tk = 1 - abs(1 - 2*tk) if vaiven else tk
            # Los verbos se animan SOLOS: correr, remar, cavar, pelear,
            # empujar y firmar no son gestos, son ciclos. Si el guion no pide
            # a donde va, el movimiento sale igual - y eso importa mas que
            # parecer elegante, porque lo que hay que pedir se olvida y en el
            # #90 siete de doce monigotes salieron congelados.
            if not fin:
                fin = _CICLOS.get(f.get("pose"))
            if fin and fin != f.get("pose"):
                if f.get("pose") == "en_cama" and fin != "de_pie":
                    g["pose_mezclada"] = _mezcla(_POSES["en_cama"], _en_cama_con(fin), tk)
                else:
                    g["pose_mezclada"] = _mezcla(_POSES[f.get("pose","de_pie")], _POSES[fin], tk)
            # RESPIRACION: sube y baja un poco aunque no cambie de pose.
            g["_bocanada"] = math.sin(2*math.pi*(reloj/_SEGUNDOS_RESPIRACION + desfase))
            carrera = _carrera(f, reloj, segundos, desfase)
            if carrera:
                g.update(carrera)
            g.update(_efecto(f, reloj, segundos))
            # La etiqueta con el papel, solo un par de segundos: lo justo para
            # leer "LA REINA" y que no se quede tapando el suelo todo el plano.
            if reloj > _SEGUNDOS_PAPEL:
                g["papel"] = None
            paso["figuras"].append(g)
        _señala_a_quien(paso, bocadillos, reloj)
        _coreografia_del_tortazo(spec, paso, reloj, segundos)
        _coreografia_de_la_entrega(spec, paso, reloj, segundos)
        rnd = random.Random(1000 + n//3)
        # tam: el video largo es horizontal; sin decirlo, sale el del Short.
        img = _decorado(paso, semilla=1000 + n//3, tam=tam)
        if paso.get("noche"):
            img = _de_noche(img)
        caja = _caja_del_zoom(paso, img.size)
        if caja:
            img = img.crop(tuple(int(v) for v in caja)).resize(img.size, Image.LANCZOS)
        # UNO O DOS. Dos es una conversacion: uno dice algo y el otro le
        # contesta, cada globo en SU instante y apuntando a SU monigote. Si se
        # solapan en el tiempo se pintan los dos, que es como se dibuja una
        # discusion.
        ahora = n/fps
        for fila, globo in enumerate(bocadillos if bocadillos is not None
                                     else ([bocadillo] if bocadillo else [])):
            if globo and globo["desde"] <= ahora <= globo["hasta"]:
                # EL GLOBO SIGUE A QUIEN HABLA. Si corre, el rabo va con el:
                # se mira donde esta en ESTE fotograma, no donde empezo.
                x = globo.get("x", 0.5)
                i = globo.get("figura")
                if isinstance(i, int) and 0 <= i < len(paso["figuras"]):
                    x = paso["figuras"][i]["x"]
                px = img.size[0]*x
                if caja:                    # con zoom, el rabo sigue a su cara
                    px = min(img.size[0]*0.95, max(img.size[0]*0.05,
                             (px - caja[0])/(caja[2] - caja[0])*img.size[0]))
                # Arriba y abajo, alternando: la tercera frase vuelve arriba,
                # que la primera ya se ha ido. Con fila tal cual, desde que
                # caben ocho frases por escena, la quinta caia fuera del plano.
                img = _pinta_bocadillo(img, globo["texto"], px, rnd, fila % 2)
        # De uno en uno, no la lista entera: 15 fotogramas por segundo a
        # 1080x1920 son 90 MB por segundo de escena en memoria.
        yield img


# ---- LO QUE EL GUION PUEDE PEDIR -------------------------------------------
# Vocabulario CERRADO a proposito. El guion elige de estas listas y de ninguna
# otra: si pide "fondo: catedral gotica al atardecer" no hay nada que dibujar,
# y una escena que no se puede dibujar es un hueco en el video. Lo que no se
# reconoce no rompe nada, se sustituye por lo mas parecido y se apunta.
FONDOS_VALIDOS = tuple(FONDOS)
# Derivadas, no copiadas: las mitades de ciclo (_b) no se ofrecen al guion
# porque no son posturas, son el otro fotograma de una. Escribir la lista a
# mano es como se perdieron la taberna y el arbol.
POSES_VALIDAS = tuple(p for p in _POSES if not p.endswith("_b"))
GESTOS_VALIDOS = ("neutro", "sorpresa", "contento", "enfadado", "grito",
                  "triste", "asustado", "bostezo", "asco", "riendo")
# Explicados aqui y no tecleados en el prompt, como todo lo demas: la lista
# del prompt estaba escrita a mano y cada gorro nuevo habria sido invisible.
GORROS_EXPLICADOS = {
    "corona":     "rey o reina",
    "corona_imperial": "corona CERRADA de emperador, con arcos, terciopelo rojo y cruz: emperadores (Carlos V, Alfonso VII emperador de Hispania), el rey de mas rango cuando hay dos reyes",
    "corona_grande": "una corona que le queda ENORME, torcida y tapandole los ojos: el rey o la reina niño",
    "comandante": "bicornio: general, Napoleon, oficial de 1808",
    "tricornio":  "el del siglo XVIII: ministros, guardias, Godoy",
    "sombrero":   "ala ancha: el del pueblo, el del motin",
    "casco":      "morrion de conquistador o de soldado de los tercios",
    "mitra":      "obispo, inquisidor",
    "monje":      "capucha de fraile o monje",
    "boina":      "el campesino, el pueblo, el XIX y XX",
    "marinero":   "gorro de marinero",
    "peluca":     "peluca blanca empolvada del XVIII: Borbones, cortesanos, ministros",
    "turbante":   "Al-Andalus, sultanes, embajadores de Oriente",
    "dux":        "EL DUX DE VENECIA: el gorro dorado con un cuerno detras (Sebastiano Venier, el gobernante de Venecia)",
    "tiara":      "EL PAPA: la triple corona blanca con cruz (Pio quinto, el Papa Luna en su trono). Un obispo o un cardenal llevan mitra",
    "chistera":   "sombrero de copa del XIX: politicos, banqueros, caballeros",
    "peineta":    "peineta y mantilla negra: la dama española",
    "toca":       "toca de monja, velo negro y la cara enmarcada en blanco: monjas, abadesas, conventos",
    "dormir":     "gorro de dormir con borla: en pijama, recien levantado, en la cama",
}
GORROS_VALIDOS = tuple(GORROS_EXPLICADOS)
# (OBJETOS_VALIDOS ya esta declarada arriba, junto a OBJETOS: el sombrero no
# esta porque YA es un gorro, no hacia falta una segunda forma de pedir lo
# mismo.)
# Se rellena abajo, con las recetas: asi no puede haber una lista de sitios
# que ofrezco al guion y otra de sitios que se saben dibujar.
INTERIORES_VALIDOS: tuple = ()

_MAX_FIGURAS = 4

# Lo minimo que tienen que separarse dos cosas en horizontal, en pantallas.
_SEPARACION = 0.13


def _una_de(valor, validas, por_defecto):
    v = (valor or "").strip().lower()
    return v if v in validas else por_defecto


def limpia(spec: dict) -> dict:
    """La escena que ha pedido el guion, dejada en algo que se sabe dibujar."""
    if not isinstance(spec, dict):
        return {"fondo": "liso", "figuras": [{"x": 0.5, "pose": "de_pie"}]}
    figuras = []
    crudas = spec.get("figuras")
    for f in (crudas if isinstance(crudas, list) else [])[:_MAX_FIGURAS]:
        if not isinstance(f, dict):
            continue
        gorro = (f.get("gorro") or "").strip().lower()
        # El personaje del reparto trae su estatura consigo: el mandamas es
        # alto y la abuela bajita SIEMPRE, en todos los videos. Si el guion
        # pide otra cosa se ignora, porque eso es justo lo que romperia que se
        # les reconozca.
        quien = (f.get("quien") or "").strip().lower()
        quien = quien if quien in REPARTO else None
        por_defecto = REPARTO[quien]["alto"] if quien else 0.34
        figuras.append({
            "quien": quien,
            "x": min(0.88, max(0.12, float(f.get("x", 0.5) or 0.5))),
            "alto": por_defecto if quien else min(
                0.46, max(0.18, float(f.get("alto", 0.34) or 0.34))),
            "pose": _una_de(f.get("pose"), POSES_VALIDAS, "de_pie"),
            "pose_fin": _destino(f),
            "gesto": _una_de(f.get("gesto"), GESTOS_VALIDOS, "neutro"),
            "gorro": gorro if gorro in GORROS_VALIDOS else None,
            "objeto": _una_de(f.get("objeto"), OBJETOS_VALIDOS, "") or None,
            "espejo": bool(f.get("espejo")),
            "papel": (str(f.get("papel") or "").strip()[:_LARGO_PAPEL] or None),
            "efecto": _una_de(f.get("efecto"), EFECTOS_VALIDOS, "") or None,
            "lleva": _llevable(f.get("lleva")),
            "efecto_desde": (float(f["efecto_desde"])
                             if isinstance(f.get("efecto_desde"), (int, float)) else None),
        })
        # En la cama no se lleva manto: en Farinelli el rey salio con el manto
        # de la reina puesto encima de la colcha, un triangulo rojo gigante
        # que tapaba la cama entera.
        ultima = figuras[-1]
        if {ultima["pose"], ultima["pose_fin"]} & set(_ACOSTADAS) and ultima["objeto"] in ("manto", "capa"):
            ultima["objeto"] = None
        # El que mira por el catalejo se lo lleva al ojo con la mano de visera,
        # y se queda asi: si luego señalara, el catalejo flotaria solo.
        if ultima["lleva"] == "catalejo" and ultima["pose"] in ("de_pie", "señala", "mirando"):
            ultima["pose"], ultima["pose_fin"] = "mirando", None
    # LA CAMA OCUPA SITIO. Se pinta hacia donde mira quien esta en ella, y
    # en Farinelli el cantante acabo de pie encima de los pies de la cama,
    # medio tapado: el guion no sabe cuanto mide una cama. Aqui si: el de la
    # cama va a un lado y los demas, pasado el pie de la cama.
    for c in [f for f in figuras if "en_cama" in (f["pose"], f["pose_fin"])][:1]:
        lado = -1 if c["espejo"] else 1
        largo = 0.46*c["alto"]*(_ALTO_BASE/_ANCHO_BASE)
        # Pegada al borde si hay mas gente: con tres personajes (el rey en la
        # cama y dos al lado) no cabian sin montarse uno encima del otro.
        hay_mas = len(figuras) > 2
        c["x"] = (min(c["x"], 0.22 if hay_mas else 0.30) if lado > 0
                  else max(c["x"], 0.78 if hay_mas else 0.70))
        pie = c["x"] + lado*(largo + 0.13)
        otros = []
        for o in figuras:
            if o is c:
                continue
            if lado > 0 and o["x"] > c["x"] - 0.05:
                o["x"] = min(0.88, max(o["x"], pie)); otros.append(o)
            elif lado < 0 and o["x"] < c["x"] + 0.05:
                o["x"] = max(0.12, min(o["x"], pie)); otros.append(o)
        # Y separados entre ellos: empujados todos al pie de la cama acababan
        # uno encima del otro (Luisa Carlota tapando a Calomarde).
        _reparte(otros, desde=min(pie, 0.88) if lado > 0 else max(pie, 0.12), lado=lado)
    if not figuras:
        # Una escena sin nadie es un fondo de color. Antes que eso, alguien.
        figuras = [{"x": 0.5, "alto": 0.34, "pose": "de_pie", "pose_fin": None,
                    "gesto": "neutro", "gorro": None, "espejo": False}]
    tachados = []
    for t in (spec.get("tachados") if isinstance(spec.get("tachados"), list) else [])[:3]:
        if isinstance(t, dict):
            tachados.append({"x": min(0.9, max(0.1, float(t.get("x", 0.5) or 0.5))),
                             "y": min(0.5, max(0.12, float(t.get("y", 0.28) or 0.28))),
                             "tam": min(0.26, max(0.10, float(t.get("tam", 0.18) or 0.18)))})
    # El interior manda sobre el fondo: si el guion pide "monasterio" no hay
    # que mirar el fondo plano. Se me colaba porque limpia() se comia la clave
    # entera y el monasterio salia como campo liso.
    dentro = (spec.get("interior") or "").strip().lower()
    dentro = dentro if dentro in INTERIORES_VALIDOS else None
    # EN EL SALON DEL TRONO, EL QUE SE SIENTA SE SIENTA EN EL TRONO. La reina
    # niña salia sentada en el suelo delante de un pupitre (sentado se anima
    # hacia en_mesa, y sin mesa en el decorado se pinta una). En el trono no
    # se escribe: sin mesita, y en el centro, que es donde esta el trono.
    if dentro == "salon_trono":
        sentados = [f for f in figuras if f["pose"] == "sentado"]
        for f in sentados:
            if f["pose_fin"] in _POSES_DE_MESA:
                f["pose_fin"] = None
        if sentados:
            sentados[0]["x"] = 0.50
            izq = [f for f in figuras if f is not sentados[0] and f["x"] <= 0.5]
            der = [f for f in figuras if f is not sentados[0] and f["x"] > 0.5]
            _reparte(der, desde=0.70, lado=1)
            _reparte(izq, desde=0.30, lado=-1)
    # El tope se cuenta sobre las cosas BUENAS, no sobre lo que llega. Con el
    # tope arriba, un "dragon" que no se sabe dibujar ocupaba el sitio de una
    # casa que si: se pedian cinco, se colaban dos malas y se perdia la buena.
    cosas = []
    for c in (spec.get("cosas") if isinstance(spec.get("cosas"), list) else []):
        if len(cosas) >= 4:
            break
        if not isinstance(c, dict):
            continue
        que = (c.get("que") or "").strip().lower()
        if que not in COSAS or COSAS[que] is None:
            continue
        cosas.append({"que": que,
                      "x": min(0.95, max(0.05, float(c.get("x", 0.5) or 0.5))),
                      "y": (min(0.95, max(0.05, float(c["y"]))) 
                            if c.get("y") is not None else None),
                      "tam": min(0.34, max(0.05, float(c.get("tam", 0.14) or 0.14))),
                      "delante": bool(c.get("delante"))})
    # QUE NO SE PISEN. El guion elige la x de cada cosa y de cada persona sin
    # ver el resultado, asi que dos acaban en el mismo sitio: en la primera
    # prueba el perro salio DEBAJO del cañon. Aqui se separan, que es algo que
    # el dibujo puede garantizar y el guion no.
    # Se busca el hueco LIBRE mas cercano al sitio que pidio el guion. Mi
    # primer intento empujaba a un lado y a otro segun con quien chocara, y
    # rebotaba: el perro iba del cañon al soldado y vuelta, doce veces, y se
    # quedaba encima del cañon igual. Buscar en vez de empujar no puede
    # oscilar.
    ocupadas = [f["x"] for f in figuras]
    for c in cosas:
        if c["y"] is not None:          # lo del cielo no estorba a nadie
            continue
        libre = lambda px: all(abs(o - px) >= _SEPARACION for o in ocupadas)
        if not libre(c["x"]):
            sitios = [0.05 + 0.02*k for k in range(46)]
            candidato = min((p for p in sitios if libre(p)),
                            key=lambda p: abs(p - c["x"]), default=None)
            if candidato is not None:
                c["x"] = round(candidato, 3)
        ocupadas.append(c["x"])

    _camilla_a_la_ambulancia(figuras, cosas)
    habla_x = (float(spec["habla_x"])
               if isinstance(spec.get("habla_x"), (int, float)) else None)
    hablan = hablan_de(spec, figuras)
    if hablan:
        # Si el guion dice QUIEN habla, manda eso y no la x: la x era una
        # forma indirecta de decir lo mismo y es la que se equivocaba.
        habla_x = next(f["x"] for f in figuras if nombre_de(f) == hablan[0])
    return _montar_escena({"interior": dentro, "cosas": cosas,
            "fondo": _una_de(spec.get("fondo"), FONDOS_VALIDOS, "liso"),
            "suelo": min(0.86, max(0.58, float(spec.get("suelo", 0.70 if dentro else 0.74)
                                              or 0.74))),
            "figuras": figuras, "tachados": tachados,
            "habla_x": habla_x, "hablan": hablan, "a_quien": a_quien_de(spec, figuras),
            "rotulo": (" ".join(str(spec.get("rotulo") or "").split())[:_LARGO_ROTULO] or None),
            "noche": bool(spec.get("noche")),
            "arbol": spec.get("arbol") if isinstance(spec.get("arbol"), (int, float)) else None})


def _reparte(figs, desde, lado, hueco=0.15):
    """Pone las figuras de un lado en fila, sin pisarse, a partir de 'desde'."""
    figs = sorted(figs, key=lambda f: f["x"]*lado)
    x = desde
    for f in figs:
        f["x"] = round(min(0.90, max(0.10, max(f["x"]*lado, x*lado)*lado)), 3)
        x = f["x"] + lado*hueco


def nombre_de(f: dict) -> str:
    """Como se nombra a una figura en "hablan" y "a_quien": su personaje del
    reparto o, si no es de los cinco (la mujer con la que se cruza Juana, la
    monja), su papel. Remedios era la unica mujer: con dos mujeres en una
    historia, la segunda no podia decir nada."""
    return f.get("quien") or clave_de_papel(f.get("papel"))


def hablan_de(spec: dict, figuras: list[dict]) -> list[str] | None:
    """La lista "hablan" del guion, si se puede usar: un nombre del reparto
    por cada frase entrecomillada, y todos presentes en la escena."""
    crudo = spec.get("hablan") if isinstance(spec, dict) else None
    if not isinstance(crudo, list) or not crudo:
        return None
    presentes = {nombre_de(f) for f in figuras} - {""}
    nombres = [n if n in presentes else clave_de_papel(n)
               for n in (str(n or "").strip().lower() for n in crudo)]
    return nombres if all(n in presentes for n in nombres) else None


def _camilla_a_la_ambulancia(figuras, cosas):
    """Si en la escena hay camilla y ambulancia, la camilla va A la
    ambulancia: la ambulancia a la derecha con las puertas abiertas hacia la
    camilla, y la camilla rueda hasta ellas. "La ambulancia cogiendo a
    Maricarmen de la camilla": rodando hacia ningun sitio no se entendia."""
    amb = next((c for c in cosas if c.get("que") == "ambulancia"), None)
    cam = next((f for f in figuras if f.get("pose") == "en_camilla"), None)
    if not (amb and cam):
        return
    amb["tam"] = min(float(amb.get("tam") or 0.12), 0.12)
    amb["x"] = 0.70
    amb.pop("y", None)
    proporcion = _ALTO_BASE/_ANCHO_BASE
    puertas = amb["x"] - 1.15*amb["tam"]*proporcion
    cam["espejo"] = False
    cam["x"] = 0.16
    cam["_hacia"] = round(max(cam["x"], puertas - 0.46*cam["alto"]*proporcion), 3)
    for f in figuras:                     # los demas, que no tapen el camino
        if f is not cam and 0.10 < f["x"] < puertas:
            f["x"] = 0.92 if f["x"] > 0.5 else 0.06


def a_quien_de(spec: dict, figuras: list[dict]) -> list[str] | None:
    """La lista "a_quien" del guion: a quien se dirige cada frase, si se
    dirige a alguien en concreto que esta en la escena ("" si no)."""
    crudo = spec.get("a_quien") if isinstance(spec, dict) else None
    if not isinstance(crudo, list) or not crudo:
        return None
    presentes = {nombre_de(f) for f in figuras} - {""}
    nombres = [str(n or "").strip().lower() for n in crudo]
    nombres = [n if n in presentes else clave_de_papel(n) for n in nombres]
    return [n if n in presentes else "" for n in nombres]


def a_quien_dicen(escena: dict, cuantas: int) -> list[int | None]:
    """El puesto en la escena de a quien va cada frase, o None. Sale de la
    MISMA limpia() que quienes_dicen, asi que los puestos coinciden."""
    limpio = limpia(escena)
    lista = limpio.get("a_quien") or []
    puesto = {nombre_de(f): i for i, f in enumerate(limpio["figuras"]) if nombre_de(f)}
    return [puesto.get(lista[k]) if k < len(lista) and lista[k] else None
            for k in range(cuantas)]


# SEÑALA A QUIEN LE HABLA. "Lo unico que le falta es señalar a cada uno": en
# el #107 España le decia "tu quieres recuperar tu piso", "tu quieres que se
# quede", "y tu quieres salir en la tele" a tres personas distintas, y en
# pantalla no se sabia a cual. Mientras dura su globo, el que habla se gira
# hacia el otro y le señala, y el señalado da un respingo con cara de
# sorpresa: con tres en el plano, el respingo es lo que dice a cual.
def _señala_a_quien(paso, globos, reloj):
    figs = paso.get("figuras") or []
    for globo in globos or []:
        i, a = (globo or {}).get("figura"), (globo or {}).get("a")
        if not (isinstance(i, int) and isinstance(a, int) and i != a
                and 0 <= i < len(figs) and 0 <= a < len(figs)):
            continue
        desde, hasta = float(globo["desde"]), float(globo["hasta"])
        if not desde - 0.15 <= reloj <= hasta + 0.35:
            continue
        habla, otro = figs[i], figs[a]
        if habla.get("pose") in _ACOSTADAS or habla.get("pose") in _DESPLAZAMIENTOS:
            continue
        habla.update({"pose": "señala", "pose_mezclada": None,
                      "espejo": otro["x"] < habla["x"]})
        otro["gesto"] = "sorpresa"
        dentro = reloj - desde
        if 0 <= dentro <= 0.4:
            otro["_dy"] = otro.get("_dy", 0.0) - 0.035*math.sin(math.pi*dentro/0.4)


# QUIEN DICE CADA FRASE. Una sola funcion para el globo y para la voz.
#
# Antes el guion solo podia decir quien habla PRIMERO ("habla_x", una
# posicion), y la respuesta se adivinaba: "el que este mas lejos". Con dos
# personajes que se turnan eso acierta; con tres en el plano, o con alguien
# que dice dos frases seguidas, se equivoca - y ella lo vio en el Motin de
# Esquilache: "se confundia quien decia quien". Encima la adivinanza estaba
# escrita DOS veces, una en visuals para el globo y otra en voces para la
# voz, que es como acaban no coincidiendo.
#
# Ahora el guion puede decirlo tal cual - "hablan": ["mandamas", "chaval"] -
# y si no lo dice, se adivina como antes. Las dos mitades leen de aqui.
def quienes_dicen(escena: dict, cuantas: int) -> list[dict]:
    limpio = limpia(escena)
    figuras = limpio["figuras"]
    # Su puesto en la escena, para que el globo pueda buscarle en cada
    # fotograma: el que corre no esta donde empezo.
    for i, f in enumerate(figuras):
        f["_i"] = i
    hablan = limpio.get("hablan")
    if hablan and len(hablan) >= cuantas:
        por_nombre = {nombre_de(f): f for f in figuras if nombre_de(f)}
        return [por_nombre[n] for n in hablan[:cuantas]]
    x = limpio.get("habla_x")
    quien = (min(figuras, key=lambda f: abs(f["x"] - x)) if x is not None else figuras[0])
    otro = max(figuras, key=lambda f: abs(f["x"] - quien["x"])) if len(figuras) > 1 else quien
    return [quien if k % 2 == 0 else otro for k in range(cuantas)]


_ANCHO_BASE, _ALTO_BASE = 1080, 1920

# La camara. Con las ilustraciones de IA habia al menos un zoom lento; con los
# monigotes el plano se quedo clavado del todo, y un plano clavado se nota
# aunque dentro haya movimiento. Un empuje del 7% y una deriva lateral: poco,
# pero quita la sensacion de foto.
_EMPUJE = 0.045


def _camara(img, t):
    """El recorte de este instante: entra despacio y deriva un poco."""
    w, h = img.size
    zoom = 1.0 + _EMPUJE*t
    cw, ch = w/zoom, h/zoom
    # La deriva va hacia el centro, asi que el plano se cierra sobre la accion.
    x = (w-cw)*(0.5 + 0.30*math.cos(math.pi*t))
    y = (h-ch)*0.5
    return img.crop((int(x), int(y), int(x+cw), int(y+ch)))
_FPS = 15


def render(spec: dict, out_path: Path, ancho: int, alto: int,
           segundos: float, bocadillo: dict | None = None,
           bocadillos: list | None = None) -> Path | None:
    """La escena, ya montada como clip de video de la duracion que se pida.

    Devuelve None si algo falla, nunca revienta: una escena sin clip cae en la
    cadena de siempre (foto real, imagen del articulo, archivo), que es lo que
    hace que un fallo aqui cueste un plano y no el video.
    """
    try:
        limpio = limpia(spec)
        # EL TOPE ERA DE 12 SEGUNDOS, y una escena mas larga se rellenaba
        # repitiendo su principio: en Colon, la escena del «¡AHÍ!» y las dos
        # frases del narrador duraba 15 s y el «¡AHÍ!» volvia a salir justo
        # antes de la careta. El tope estaba por la memoria - todos los
        # fotogramas de la escena a la vez -, y ahora se guardan de uno en uno.
        segundos = max(1.0, min(40.0, float(segundos)))
        total = max(2, int(segundos*_FPS))
        carpeta = Path(out_path).with_suffix("")
        carpeta.mkdir(parents=True, exist_ok=True)
        medio = None
        for i, img in enumerate(animar(limpio, segundos=segundos, fps=_FPS,
                                       bocadillo=bocadillo, bocadillos=bocadillos)):
            cuadro = _camara(img, i/max(1, total-1)).resize((ancho, alto), Image.LANCZOS)
            cuadro.save(carpeta / f"{i:04d}.png")
            if i == total//2:
                medio = cuadro
        orden = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(_FPS),
                 "-i", str(carpeta / "%04d.png"),
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                 "-r", "30", str(out_path)]
        subprocess.run(orden, check=True, capture_output=True, timeout=180)
        # Un fotograma suelto para la miniatura. La lista de 'retratos' la lee
        # thumbnail.py con PIL, y un mp4 ahi dentro es una excepcion: la
        # portada de un video de monigotes tiene que ser un monigote.
        if medio is not None:
            medio.save(Path(out_path).with_suffix(".jpg"), quality=92)
        for f in carpeta.glob("*.png"):
            f.unlink()
        carpeta.rmdir()
        quienes = ", ".join(
            f"{f['pose']}{'->' + f['pose_fin'] if f['pose_fin'] else ''}"
            f"{'/' + f['gorro'] if f['gorro'] else ''}" for f in limpio["figuras"])
        logger.info("Monigotes: %s en %r, %.1fs (%s).", quienes,
                    limpio.get("interior") or limpio["fondo"], segundos, out_path.name)
        return Path(out_path)
    except Exception:
        logger.warning("No se ha podido dibujar la escena de monigotes.", exc_info=True)
        return None


# ---- DECORADOS -------------------------------------------------------------
# Un fondo de dos bandas de color vale para un campo o una calle, y no vale
# para un sitio: un refectorio, una taberna, un salon del trono. Lo que hace
# que parezca una habitacion y no unas pegatinas sobre un color es el ORDEN:
#
#   pared -> ventana -> velas -> bancos -> FIGURAS -> LA MESA DELANTE -> loza
#
# La mesa se pinta DESPUES de la gente. Por eso los brazos se apoyan encima y
# las piernas quedan debajo, que es lo que se ve en cualquier escena de estas
# bien hecha.

PIEDRA = (150, 144, 134)
MADERA = (150, 106, 62)
MADERA_OSCURA = (112, 78, 44)


def _pared_piedra(d, w, h, suelo, rnd):
    d.rectangle([0, 0, w, suelo], fill=PIEDRA)
    d.rectangle([0, suelo, w, h], fill=(108, 100, 92))
    g = max(3, int(w*0.0045))
    for _ in range(30):
        bw = rnd.uniform(w*.05, w*.13); bh = bw*rnd.uniform(.32, .52)
        bx = rnd.uniform(0, w-bw); by = rnd.uniform(0, suelo-bh)
        _linea(d, [(bx,by),(bx+bw,by),(bx+bw,by+bh),(bx,by+bh),(bx,by)], g, rnd,
               color=(104, 98, 90), temblor=1.8)


def _resplandor(img, c, r, color=(255, 214, 120)):
    """El halo de una vela. Va en su propia capa porque necesita transparencia."""
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dd = ImageDraw.Draw(capa)
    for k in range(7, 0, -1):
        rr = r*k/7
        dd.ellipse([c[0]-rr, c[1]-rr, c[0]+rr, c[1]+rr], fill=color + (12,))
    return Image.alpha_composite(img.convert("RGBA"), capa).convert("RGB")


def _vela(d, x, y, alto, rnd, g):
    _linea(d, [(x-alto*.16, y), (x-alto*.16, y-alto), (x+alto*.16, y-alto),
               (x+alto*.16, y), (x-alto*.16, y)], g, rnd, temblor=1.2)
    d.rectangle([x-alto*.15, y-alto*.98, x+alto*.15, y-2], fill=(248, 244, 232))
    llama = [(x, y-alto*1.44), (x+alto*.14, y-alto*1.06), (x, y-alto*.98),
             (x-alto*.14, y-alto*1.06), (x, y-alto*1.44)]
    d.polygon(llama, fill=(250, 176, 60)); _linea(d, llama, max(2, g//2), rnd, temblor=1)


def _ventana_arco(d, cx, cy, ancho, alto, rnd, g):
    izq, der = cx-ancho/2, cx+ancho/2
    arco = cy-alto/2
    d.rounded_rectangle([izq, arco, der, cy+alto/2], radius=int(ancho*0.48),
                        fill=(38, 44, 86), outline=TINTA, width=g)
    d.rectangle([izq+g, cy, der-g, cy+alto/2-g], fill=(38, 44, 86))
    d.polygon([(izq+g, cy+alto/2-g), (cx-ancho*.16, cy), (cx+ancho*.10, cy+alto*.18),
               (der-g, cy+alto*.06), (der-g, cy+alto/2-g)], fill=(62, 74, 106))
    luna = (cx-ancho*.14, arco+alto*.22); rl = ancho*.13
    d.ellipse([luna[0]-rl, luna[1]-rl, luna[0]+rl, luna[1]+rl], fill=(248, 232, 150))
    d.ellipse([luna[0]-rl*1.5, luna[1]-rl*1.25, luna[0]+rl*.55, luna[1]+rl*1.25],
              fill=(38, 44, 86))
    for _ in range(6):
        ex, ey = rnd.uniform(izq+ancho*.18, der-ancho*.12), rnd.uniform(arco+alto*.10, cy-alto*.06)
        re = ancho*rnd.uniform(.022, .040)
        d.polygon([(ex, ey-re), (ex+re*.34, ey-re*.34), (ex+re, ey), (ex+re*.34, ey+re*.34),
                   (ex, ey+re), (ex-re*.34, ey+re*.34), (ex-re, ey), (ex-re*.34, ey-re*.34)],
                  fill=(250, 226, 130))


def _banco(d, x, y, ancho, rnd, g):
    alto = ancho*0.34
    _linea(d, [(x-ancho/2, y-alto), (x+ancho/2, y-alto), (x+ancho/2, y-alto*.70),
               (x-ancho/2, y-alto*.70), (x-ancho/2, y-alto)], g, rnd, temblor=1.4)
    d.rectangle([x-ancho/2+g, y-alto+g, x+ancho/2-g, y-alto*.70-g], fill=MADERA)
    for lado in (-1, 1):
        px = x + lado*ancho*.36
        _linea(d, [(px, y-alto*.70), (px, y)], int(g*2.2), rnd, color=MADERA_OSCURA, temblor=1.2)


def _mesa(d, y, ancho_img, rnd, g):
    """La mesa, DELANTE de la gente. Ese es todo el truco."""
    x0, x1 = ancho_img*0.10, ancho_img*0.90
    grosor = ancho_img*0.030
    _linea(d, [(x0, y), (x1, y), (x1, y+grosor), (x0, y+grosor), (x0, y)], g, rnd, temblor=1.6)
    d.rectangle([x0+g, y+g, x1-g, y+grosor-g], fill=MADERA)
    for px in (x0+ancho_img*.06, ancho_img*.50, x1-ancho_img*.06):
        _linea(d, [(px, y+grosor), (px, y+grosor+ancho_img*0.22)], int(g*2.6), rnd,
               color=MADERA_OSCURA, temblor=1.2)


def _cuenco(d, x, y, ancho, rnd, g):
    """El cuenco se APOYA en el tablero: base en y, cuerpo hacia arriba.

    Lo tenia centrado en y, o sea medio cuenco flotando por encima de las
    caras y el otro medio colgando por debajo de la mesa como un pendulo."""
    boca = y - ancho*0.42
    d.chord([x-ancho/2, boca-ancho*.30, x+ancho/2, y], 0, 180,
            fill=(146, 104, 58), outline=TINTA, width=g)
    for _ in range(30):
        a = rnd.uniform(0, 6.283); rr = rnd.uniform(0, ancho*.40)
        bx = x + math.cos(a)*rr
        by = boca - ancho*.10 + math.sin(a)*rr*.22
        rb = ancho*.052
        d.ellipse([bx-rb, by-rb, bx+rb, by+rb], fill=(168, 34, 44), outline=(120,20,28))
    d.ellipse([x-ancho/2, boca-ancho*.17, x+ancho/2, boca+ancho*.17],
              fill=None, outline=TINTA, width=g)


def _jarra(d, x, y, alto, rnd, g):
    _linea(d, [(x-alto*.34, y-alto), (x+alto*.34, y-alto), (x+alto*.28, y),
               (x-alto*.28, y), (x-alto*.34, y-alto)], g, rnd, temblor=1.2)
    d.polygon([(x-alto*.32, y-alto*.94), (x+alto*.32, y-alto*.94),
               (x+alto*.26, y-g), (x-alto*.26, y-g)], fill=(198, 152, 104))
    d.arc([x+alto*.20, y-alto*.80, x+alto*.62, y-alto*.30], 290, 70, fill=TINTA, width=g)


# Los sitios que se saben montar: el guion elige por NOMBRE, no describe una
# catedral gotica al atardecer. INTERIORES_VALIDOS esta arriba, con el resto
# del vocabulario.
def interior(spec: dict, w: int, h: int, semilla: int = 0):
    """Una habitacion de verdad, montada por capas."""
    rnd = random.Random(semilla)
    sitio = spec.get("interior", "monasterio")
    suelo = int(h*spec.get("suelo", 0.70))
    img = Image.new("RGB", (w, h), PIEDRA)
    d = ImageDraw.Draw(img)
    g = max(4, int(w*0.006))

    _pared_piedra(d, w, h, suelo, rnd)
    if sitio in ("monasterio", "taberna"):
        # En vertical el quinto de arriba es del bocadillo, asi que la ventana
        # baja. En apaisado cabe arriba sin estorbar.
        vertical = h > w
        _ventana_arco(d, w*0.50, h*(0.36 if vertical else 0.23),
                      w*(0.20 if vertical else 0.155),
                      h*(0.17 if vertical else 0.30), rnd, g)

    # Velas en repisas. Se apuntan y su halo se compone al final, porque la
    # transparencia tiene que ir sobre TODO lo que ya esta pintado.
    velas = []
    for x, y in ((0.10, 0.20), (0.27, 0.16), (0.78, 0.19), (0.92, 0.26)):
        cx, cy = w*x, h*y
        _linea(d, [(cx-w*.055, cy), (cx+w*.055, cy)], int(g*1.8), rnd, color=MADERA_OSCURA)
        _vela(d, cx, cy, h*0.042, rnd, g)
        velas.append((cx, cy - h*0.030))

    linea_mesa = suelo - h*0.02
    for f in spec.get("figuras", []):
        alto_f = h*f.get("alto", 0.30)
        figura(d, w*f["x"],
               linea_mesa + h*0.075 + alto_f*_RESPIRACION*f.get("_bocanada", 0.0),
               alto_f, rnd,
               f.get("pose", "en_mesa"), f.get("gesto", "neutro"),
               f.get("gorro"), f.get("espejo", False), f.get("pose_mezclada"),
               rasgos=REPARTO.get(f.get("quien") or ""))

    _mesa(d, linea_mesa, w, rnd, g)                      # DELANTE de la gente
    _cuenco(d, w*0.50, linea_mesa, w*0.11, rnd, g)
    for x in (0.26, 0.38, 0.70):
        _jarra(d, w*x, linea_mesa + h*0.004, h*0.035, rnd, g)
    _vela(d, w*0.62, linea_mesa, h*0.035, rnd, g)
    velas.append((w*0.62, linea_mesa - h*0.025))

    for c in velas:
        img = _resplandor(img, c, h*0.075)
    return img


# ---- EL REPARTO ------------------------------------------------------------
# Idea suya, y es la que puede hacer el canal: "que sean los mismos entre
# video y video, para que el espectador los reconozca aunque esten en una
# historia diferente".
#
# La gente vuelve a un canal por la GENTE, no por el tema. Si siempre sale el
# mismo viejo del bigote, aunque hoy este en Lepanto y mañana en un motin, se
# vuelve "el canal ese del viejo". Eso no se consigue con el gorro, porque el
# gorro es el PAPEL y cambia en cada historia: hace falta algo que no cambie
# nunca - el pelo, el bigote, la estatura, la forma de la cabeza.
#
# Son cinco y estan pensados para cubrir cualquier escena de historia de
# España sin repetirse: quien manda, quien obedece, quien lo cuenta, quien lo
# sufre y quien se aprovecha.
# YA PREPARADOS: cada uno con su nombre, su pinta y su papel escritos aqui de
# una vez, no inventados en cada video. El guion no los describe ni los
# elige por rasgos - los llama por su nombre y ya estan.
REPARTO = {
    "cronista": {"alto": 0.38, "cabeza": 0.95, "ancho": 1.0,
                 "pelo": "raya", "barba": True,
                 "nombre": "Anselmo",
                 "pinta": "barbudo, alto y flaco",
                 "papel": "el TESTIGO. Ni manda ni obedece: esta ahi mirando y comentando "
                          "lo que hacen los demas. Es los ojos del espectador, y por eso "
                          "sale en TODOS los videos y casi siempre es quien suelta la "
                          "frase del bocadillo"},
    "abuela":   {"alto": 0.25, "cabeza": 1.12, "ancho": 1.25,
                 "pelo": "moño",
                 "nombre": "Remedios",
                 "pinta": "bajita, redonda, con moño",
                 "papel": "LA QUE NO SE CALLA. Dice la verdad incomoda que nadie quiere "
                          "oir, y normalmente tiene razon"},
    "chaval":   {"alto": 0.21, "cabeza": 1.05, "ancho": 0.9,
                 "pelo": "punta",
                 "nombre": "Perico",
                 "pinta": "el mas pequeño, con pelos de punta",
                 "papel": "EL QUE PREGUNTA lo que nadie se atreve, y el que se mete donde "
                          "no le llaman"},
    "mandamas": {"alto": 0.45, "cabeza": 0.90, "ancho": 0.95,
                 "pelo": "nada", "barba": True,
                 "nombre": "Don Severo",
                 "pinta": "el mas alto, calvo y con barba",
                 "papel": "EL QUE MANDA, o el que cree que manda: rey, obispo, general, "
                          "ministro, alcalde. El que firma el papel que fastidia a todos"},
    "soldado":  {"alto": 0.32, "cabeza": 1.0, "ancho": 1.3,
                 "pelo": "tonsura", "parche": True,
                 "nombre": "Bruno",
                 "pinta": "ancho, con parche en el ojo",
                 "papel": "EL QUE SE LLEVA LOS PALOS: soldado, marinero, campesino, minero. "
                          "El que cumple la orden y paga las consecuencias"},
}
REPARTO_VALIDO = tuple(REPARTO)
# LOS DEL CANAL EN INGLES: gente cualquiera, cabezona, sin pelo o con coleta,
# como los de los videos de "por que pasa esto". Despues de REPARTO_VALIDO a
# proposito: el guion de España Contada no los ofrece.
REPARTO.update({
    "persona":   {"alto": 0.60, "cabeza": 1.30, "ancho": 1.0, "pelo": "nada", "camiseta": (52, 120, 220), "nombre": "",
                  "pinta": "", "papel": ""},
    "persona_b": {"alto": 0.56, "cabeza": 1.30, "ancho": 1.0, "pelo": "moño", "camiseta": (232, 90, 140), "nombre": "",
                  "pinta": "", "papel": ""},
    "nino":      {"alto": 0.40, "cabeza": 1.35, "ancho": 0.9, "pelo": "punta", "camiseta": (60, 175, 80), "nombre": "",
                  "pinta": "", "papel": ""},
    "abuelo":    {"alto": 0.56, "cabeza": 1.30, "ancho": 1.0, "pelo": "nada", "barba_gris": True,
                  "camiseta": (150, 105, 65),
                  "gafas": True, "nombre": "", "pinta": "", "papel": ""},
})


def _pelo(d, cab, rc, g, rnd, cual, tinta=TINTA):
    """Lo que no cambia nunca, por debajo del gorro del dia."""
    x, y = cab
    if cual == "raya":                       # dos mechones que ASOMAN
        for lado in (-1, 1):
            _linea(d, [(x+lado*rc*0.70, y-rc*0.78),
                       (x+lado*rc*1.24, y-rc*0.20),
                       (x+lado*rc*1.16, y+rc*0.46)], g, rnd, color=tinta, temblor=1.8)
    elif cual == "moño":
        c = (x, y-rc*1.18)
        _circulo(d, c, rc*0.42, g, rnd, relleno=None, color=tinta)
        _linea(d, [(x-rc*.55, y-rc*.80), (x, y-rc*.96), (x+rc*.55, y-rc*.80)], g, rnd,
               color=tinta, temblor=1.4)
    elif cual == "punta":
        for k in (-1, 0, 1):
            _linea(d, [(x+k*rc*0.42, y-rc*0.88),
                       (x+k*rc*0.52, y-rc*1.34)], g, rnd, color=tinta, temblor=2.2)
    elif cual == "tonsura":                  # calva con corona de pelo
        for lado in (-1, 1):
            _linea(d, [(x+lado*rc*0.82, y-rc*0.52),
                       (x+lado*rc*1.22, y-rc*0.06),
                       (x+lado*rc*1.10, y+rc*0.52)], g, rnd, color=tinta, temblor=1.8)


def _barba(d, cab, rc, g, rnd, tinta=TINTA, relleno=(255, 255, 255)):
    """Una barba que CUELGA por debajo de la cabeza.

    Empece con bigote y no cabe: en una cara de monigote, del tamaño de una
    moneda en pantalla, un bigote se come la boca y se lee como un
    manchurron. Probado dos veces - primero parecian sonreir, luego parecian
    tristes. La barba va por FUERA del circulo de la cabeza, asi que no pisa
    ni los ojos ni la boca, y se reconoce a un metro del movil.
    """
    pts = []
    for i in range(15):
        a = i/14*math.pi                       # media vuelta por abajo
        pts.append((cab[0] + math.cos(math.pi - a)*rc*0.92,
                    cab[1] + math.sin(a)*rc*1.55 + rc*0.18))
    contorno = [(cab[0]-rc*0.92, cab[1]+rc*0.18)] + pts + [(cab[0]+rc*0.92, cab[1]+rc*0.18)]
    d.polygon(contorno, fill=relleno)
    _linea(d, contorno, g, rnd, color=tinta, temblor=2.0)


def _parche(d, cab, rc, g, rnd, tinta=TINTA):
    ojo = (cab[0]-rc*0.30, cab[1]-rc*0.12)
    r = rc*0.26
    d.ellipse([ojo[0]-r, ojo[1]-r, ojo[0]+r, ojo[1]+r], fill=tinta)
    _linea(d, [(cab[0]-rc*.95, cab[1]-rc*.42), (cab[0]+rc*.85, cab[1]-rc*.02)],
           max(2, g//2), rnd, color=tinta, temblor=1.2)


# ---- LAS COSAS -------------------------------------------------------------
# "Si habla de perro dibuja un perro". Es lo que le faltaba a la escena para
# contar algo: los monigotes ponen quien, el fondo pone donde, y esto pone DE
# QUE se esta hablando. Un plano con un barco ardiendo dice mas que tres
# monigotes gesticulando en un campo vacio.
#
# Todas se dibujan apoyadas en su base, como se apoya una cosa en el suelo, y
# con el mismo pulso tembloroso que el resto: si una sale con linea limpia
# canta que es de otro sitio.

def _perro(d, x, y, t, rnd, g, tinta=TINTA):
    """De perfil, con hocico. El primero salia como un bicho: la cabeza era un
    circulo suelto con una raya saliendo."""
    lomo = [(x-t*.46, y-t*.34), (x-t*.10, y-t*.40), (x+t*.28, y-t*.36)]
    # El tronco RELLENO y antes que nada. Pintando solo la cabeza quedaba un
    # perro blanco con la cara marron, que es peor que dejarlo todo blanco.
    d.polygon(lomo + [(x+t*.24, y-t*.14), (x-t*.40, y-t*.14)], fill=PARDO)
    # las patas, tambien de perfil y del mismo color, para que no floten
    for px in (-.38, -.20, .06, .22):
        d.line([(x+t*px, y-t*.15), (x+t*px+t*.02, y)], fill=PARDO, width=max(3, g+2))
    _linea(d, lomo, g, rnd, color=tinta)
    _linea(d, [(x-t*.46, y-t*.34), (x-t*.40, y-t*.14), (x+t*.24, y-t*.14),
               (x+t*.28, y-t*.36)], g, rnd, color=tinta)
    for px in (-.38, -.20, .06, .22):
        _linea(d, [(x+t*px, y-t*.15), (x+t*px+t*.02, y)], g, rnd, color=tinta)
    cuello_p = [(x+t*.28, y-t*.36), (x+t*.44, y-t*.58), (x+t*.56, y-t*.52), (x+t*.38, y-t*.30)]
    d.polygon(cuello_p, fill=PARDO)
    _linea(d, [(x+t*.28, y-t*.36), (x+t*.44, y-t*.58)], g, rnd, color=tinta)
    cab = (x+t*.52, y-t*.66)
    _circulo(d, cab, t*.15, g, rnd, relleno=PARDO, color=tinta)
    hocico = [(cab[0]+t*.06, cab[1]-t*.02), (cab[0]+t*.30, cab[1]+t*.02),
              (cab[0]+t*.30, cab[1]+t*.12), (cab[0]+t*.04, cab[1]+t*.12)]
    d.polygon(hocico, fill=PARDO); _linea(d, hocico, g, rnd, color=tinta)
    d.ellipse([cab[0]+t*.26, cab[1]+t*.01, cab[0]+t*.34, cab[1]+t*.09], fill=tinta)
    _linea(d, [(cab[0]-t*.08, cab[1]-t*.13), (cab[0]-t*.20, cab[1]+t*.14)], g, rnd, color=tinta)
    d.ellipse([cab[0]-t*.04, cab[1]-t*.06, cab[0]+t*.02, cab[1]], fill=tinta)
    _linea(d, [(x-t*.46, y-t*.34), (x-t*.64, y-t*.60)], g, rnd, color=tinta)


def _caballo(d, x, y, t, rnd, g, tinta=TINTA):
    """La cabeza era un bloque cuadrado flotando. Ahora es una cuña pegada al
    cuello, que es lo que hace que se lea como un caballo."""
    lomo = [(x-t*.50, y-t*.56), (x-t*.10, y-t*.62), (x+t*.36, y-t*.58)]
    d.polygon(lomo + [(x+t*.30, y-t*.30), (x-t*.44, y-t*.30)], fill=CASTAÑO)
    for px in (-.42, -.24, .10, .28):
        d.line([(x+t*px, y-t*.31), (x+t*px+t*.04, y)], fill=CASTAÑO, width=max(3, g+2))
    _linea(d, lomo, g, rnd, color=tinta)
    _linea(d, [(x-t*.50, y-t*.56), (x-t*.44, y-t*.30), (x+t*.30, y-t*.30),
               (x+t*.36, y-t*.58)], g, rnd, color=tinta)
    for px in (-.42, -.24, .10, .28):
        _linea(d, [(x+t*px, y-t*.31), (x+t*px+t*.04, y)], g, rnd, color=tinta)
    cuello = [(x+t*.30, y-t*.58), (x+t*.50, y-t*1.02), (x+t*.66, y-t*1.00),
              (x+t*.50, y-t*.56)]
    d.polygon(cuello, fill=CASTAÑO); _linea(d, cuello, g, rnd, color=tinta)
    cabeza = [(x+t*.50, y-t*1.02), (x+t*.86, y-t*1.06), (x+t*.90, y-t*.90),
              (x+t*.62, y-t*.92), (x+t*.50, y-t*1.02)]
    d.polygon(cabeza, fill=CASTAÑO); _linea(d, cabeza, g, rnd, color=tinta)
    d.ellipse([x+t*.80, y-t*1.02, x+t*.86, y-t*.96], fill=tinta)
    _linea(d, [(x+t*.34, y-t*.62), (x+t*.52, y-t*1.04)], max(2, g), rnd, color=tinta, temblor=3.0)
    _linea(d, [(x-t*.50, y-t*.56), (x-t*.66, y-t*.20)], g, rnd, color=tinta, temblor=3.0)


def _barco(d, x, y, t, rnd, g, tinta=TINTA):
    casco = [(x-t*.62, y-t*.28), (x+t*.62, y-t*.28), (x+t*.42, y), (x-t*.42, y), (x-t*.62, y-t*.28)]
    d.polygon(casco, fill=MADERA); _linea(d, casco, g, rnd, color=tinta)
    _linea(d, [(x, y-t*.28), (x, y-t*1.15)], g, rnd, color=tinta)              # mastil
    vela = [(x+t*.04, y-t*1.10), (x+t*.46, y-t*.62), (x+t*.04, y-t*.40)]
    d.polygon(vela, fill=(255, 255, 255)); _linea(d, vela, g, rnd, color=tinta)
    vela2 = [(x-t*.04, y-t*1.10), (x-t*.40, y-t*.66), (x-t*.04, y-t*.46)]
    d.polygon(vela2, fill=(255, 255, 255)); _linea(d, vela2, g, rnd, color=tinta)


def _casa(d, x, y, t, rnd, g, tinta=TINTA):
    """Con las paredes RELLENAS. Las dibujaba a linea suelta, asi que en una
    calle se veia el cielo a traves de las casas."""
    d.polygon([(x-t*.42, y), (x-t*.42, y-t*.60), (x+t*.42, y-t*.60), (x+t*.42, y)],
              fill=(232, 222, 202))
    d.polygon([(x-t*.52, y-t*.58), (x, y-t*1.00), (x+t*.52, y-t*.58)], fill=(168, 96, 72))
    _linea(d, [(x-t*.42, y), (x-t*.42, y-t*.60), (x+t*.42, y-t*.60), (x+t*.42, y)],
           g, rnd, color=tinta)
    _linea(d, [(x-t*.52, y-t*.58), (x, y-t*1.00), (x+t*.52, y-t*.58), (x-t*.52, y-t*.58)],
           g, rnd, color=tinta)
    d.polygon([(x-t*.12, y), (x-t*.12, y-t*.34), (x+t*.12, y-t*.34), (x+t*.12, y)],
              fill=(120, 82, 54))
    _linea(d, [(x-t*.12, y), (x-t*.12, y-t*.34), (x+t*.12, y-t*.34), (x+t*.12, y)],
           g, rnd, color=tinta)
    d.rectangle([x+t*.18, y-t*.52, x+t*.32, y-t*.38], fill=(150, 190, 214),
                outline=tinta, width=max(2, g//2))


def _iglesia(d, x, y, t, rnd, g, tinta=TINTA):
    d.rectangle([x-t*.46, y-t*.66, x+t*.46, y], fill=PIEDRA_CLARA)
    d.rectangle([x-t*.20, y-t*1.14, x+t*.20, y-t*.64], fill=PIEDRA_CLARA)
    _linea(d, [(x-t*.46, y), (x-t*.46, y-t*.66), (x+t*.46, y-t*.66), (x+t*.46, y)],
           g, rnd, color=tinta)
    _linea(d, [(x-t*.20, y-t*.64), (x-t*.20, y-t*1.14), (x+t*.20, y-t*1.14), (x+t*.20, y-t*.64)],
           g, rnd, color=tinta)
    _linea(d, [(x, y-t*1.14), (x, y-t*1.46)], g, rnd, color=tinta)
    _linea(d, [(x-t*.13, y-t*1.34), (x+t*.13, y-t*1.34)], g, rnd, color=tinta)
    d.arc([x-t*.16, y-t*.40, x+t*.16, y+t*.06], 180, 360, fill=tinta, width=g)


def _castillo(d, x, y, t, rnd, g, tinta=TINTA):
    # RELLENO. A linea suelta se veia el cielo a traves del castillo, que es
    # el mismo fallo que ya tenian las casas de una calle.
    d.rectangle([x-t*.60, y-t*.72, x+t*.60, y], fill=PIEDRA)
    for k in range(6):
        px = x - t*.60 + t*1.20*k/6
        d.rectangle([px, y-t*.92, px+t*.10, y-t*.70], fill=PIEDRA)
    _linea(d, [(x-t*.60, y), (x-t*.60, y-t*.72), (x+t*.60, y-t*.72), (x+t*.60, y)],
           g, rnd, color=tinta)
    almena = [(x-t*.60, y-t*.72)]
    for k in range(6):
        px = x - t*.60 + t*1.20*k/6
        almena += [(px, y-t*.92), (px+t*.10, y-t*.92), (px+t*.10, y-t*.72), (px+t*.20, y-t*.72)]
    _linea(d, almena, g, rnd, color=tinta)
    d.rectangle([x-t*.14, y-t*.34, x+t*.14, y], fill=MADERA_PUERTA)
    _linea(d, [(x-t*.14, y), (x-t*.14, y-t*.34), (x+t*.14, y-t*.34), (x+t*.14, y)],
           g, rnd, color=tinta)


def _espada(d, x, y, t, rnd, g, tinta=TINTA):
    """Salia identica a la cruz. Una espada tiene PUNTA, guarda corta y
    empuñadura larga - y se dibuja inclinada, que es como se sostiene."""
    hoja = [(x-t*.10, y-t*.34), (x+t*.02, y-t*.40), (x+t*.34, y-t*1.12),
            (x+t*.20, y-t*1.16), (x-t*.10, y-t*.34)]
    d.polygon(hoja, fill=ACERO); _linea(d, hoja, g, rnd, color=tinta)
    _linea(d, [(x-t*.26, y-t*.44), (x+t*.16, y-t*.26)], max(g, int(t*.06)), rnd, color=tinta)
    _linea(d, [(x-t*.06, y-t*.32), (x-t*.18, y-t*.04)], max(g, int(t*.07)), rnd, color=tinta)
    _circulo(d, (x-t*.19, y-t*.02), t*.07, g, rnd, relleno=None, color=tinta)


def _canion(d, x, y, t, rnd, g, tinta=TINTA):
    """No se entendia nada. Un cañon es un TUBO que se estrecha, sobre dos
    ruedas, y apuntando claramente a un lado."""
    tubo = [(x-t*.34, y-t*.56), (x+t*.62, y-t*.46), (x+t*.62, y-t*.28),
            (x-t*.34, y-t*.16), (x-t*.34, y-t*.56)]
    d.polygon(tubo, fill=HIERRO); _linea(d, tubo, g, rnd, color=tinta)
    _linea(d, [(x+t*.62, y-t*.46), (x+t*.70, y-t*.48), (x+t*.70, y-t*.26),
               (x+t*.62, y-t*.28)], g, rnd, color=tinta)
    _linea(d, [(x-t*.36, y-t*.44), (x-t*.10, y-t*.06)], g, rnd, color=tinta)
    for cx, r in ((-.26, .22), (.14, .16)):
        _circulo(d, (x+t*cx, y-t*r), t*r, g, rnd, relleno=MADERA, color=tinta)


def _fuego(d, x, y, t, rnd, g, tinta=TINTA):
    for k, (ancho, alto, col) in enumerate(((.42, .90, (232, 120, 30)),
                                            (.26, .62, (248, 186, 60)))):
        llama = [(x-t*ancho, y)]
        for i in range(7):
            f = i/6
            llama.append((x - t*ancho + 2*t*ancho*f,
                          y - t*alto*(0.4 + 0.6*math.sin(math.pi*f)) + rnd.uniform(-t*.06, t*.06)))
        llama.append((x+t*ancho, y))
        d.polygon(llama, fill=col)
        _linea(d, llama, max(2, g//2), rnd, color=tinta, temblor=2.4)


def _dinero(d, x, y, t, rnd, g, tinta=TINTA):
    for i, (dx, dy, r) in enumerate(((-.22, -.10, .18), (.16, -.09, .16), (-.02, -.30, .17))):
        c = (x+t*dx, y+t*dy)
        _circulo(d, c, t*r, g, rnd, relleno=(236, 196, 88), color=tinta)


# Nacio de la Guerra de las Naranjas: Godoy corto unas naranjas cerca de
# Elvas y se las mando a la reina como si fueran el parte de guerra - el
# objeto ES el chiste, igual que la capa de Esquilache. Misma pila que el
# dinero, coloreada de naranja, con una hoja arriba para que no se lea como
# monedas.
def _naranjas(d, x, y, t, rnd, g, tinta=TINTA):
    for dx, dy, r in ((-.22, -.06, .20), (.18, -.05, .19), (-.02, -.32, .19)):
        c = (x+t*dx, y+t*dy)
        _circulo(d, c, t*r, g, rnd, relleno=(230, 126, 34), color=tinta)
    hoja = [(x-t*.02, y-t*.51), (x+t*.10, y-t*.58), (x+t*.03, y-t*.46)]
    d.polygon(hoja, fill=(92, 148, 68))


def _mapa(d, x, y, t, rnd, g, tinta=TINTA):
    """Un mapa de pergamino con una costa y una X roja. Todo ministro que
    declara una guerra lo hace delante de uno, y "Don Severo, con un mapa"
    estaba en el guion sin nada que dibujar."""
    x0, x1, y0, y1 = x - t*.46, x + t*.46, y - t*.62, y - t*.04
    hoja = [(x0, y0), (x1, y0 + t*.03), (x1 - t*.02, y1), (x0 + t*.02, y1 - t*.02)]
    d.polygon(hoja, fill=PAPEL_VIEJO)
    _linea(d, hoja + [hoja[0]], g, rnd, color=tinta)
    costa = [(x0 + t*(.10 + .08*k), y0 + t*(.12 + .10*(k % 2) + .05*k)) for k in range(9)]
    _linea(d, costa, max(2, g//2), rnd, color=(92, 120, 160), temblor=1.8)
    cx, cy = x + t*.18, y - t*.22
    for sx in (-1, 1):
        _linea(d, [(cx - t*.07, cy - sx*t*.07), (cx + t*.07, cy + sx*t*.07)], g, rnd, color=ROJO)


def _cesta(d, x, y, t, rnd, g, tinta=TINTA):
    """Una cesta de mimbre llena de naranjas: la que llega a la corte en vez
    del parte de guerra, y la de cualquier escena de mercado."""
    for dx, dy in ((-.16, -.40), (.14, -.42), (-.01, -.52)):
        _circulo(d, (x + t*dx, y + t*dy), t*.15, g, rnd, relleno=(230, 126, 34), color=tinta)
    cuerpo = [(x - t*.36, y - t*.40), (x + t*.36, y - t*.40), (x + t*.28, y), (x - t*.28, y)]
    d.polygon(cuerpo, fill=(176, 132, 76))
    _linea(d, cuerpo + [cuerpo[0]], g, rnd, color=tinta)
    for k in (1, 2):
        yy = y - t*.40*k/3
        _linea(d, [(x - t*(.28 + .08*k/3), yy), (x + t*(.28 + .08*k/3), yy)],
               max(2, g//2), rnd, color=(126, 90, 50))
    d.arc([x - t*.34, y - t*.78, x + t*.34, y - t*.10], 180, 360, fill=tinta, width=g)


def _pan(d, x, y, t, rnd, g, tinta=TINTA):
    """Una hogaza. Sale en cualquier motin de hambre o carestia - ya
    aparecio nombrada de pasada en Esquilache ("solo venia a comprar pan")
    sin que hubiera nada que dibujar para ello."""
    cuerpo = [(x - t*.28, y), (x - t*.30, y - t*.16), (x - t*.14, y - t*.26),
              (x + t*.14, y - t*.26), (x + t*.30, y - t*.16), (x + t*.28, y)]
    d.polygon(cuerpo, fill=(196, 148, 84))
    _linea(d, cuerpo + [cuerpo[0]], g, rnd, color=tinta)
    for dx in (-.10, .02, .14):
        _linea(d, [(x + t*dx, y - t*.22), (x + t*(dx-.05), y - t*.10)],
               max(2, g // 2), rnd, color=tinta)


def _escudo(d, x, y, t, rnd, g, tinta=TINTA, color=(150, 30, 34)):
    """Escudo de gota, el de toda batalla medieval - Reconquista, batallas
    de la Independencia. Sin esto una escena de asedio o combate cuerpo a
    cuerpo solo tenia la espada."""
    arriba = y - t*.62
    pts = [(x - t*.26, arriba), (x + t*.26, arriba), (x + t*.26, y - t*.20),
           (x, y), (x - t*.26, y - t*.20)]
    d.polygon(pts, fill=color)
    _linea(d, pts + [pts[0]], g, rnd, color=tinta)
    _linea(d, [(x, arriba), (x, y - t*.05)], max(2, g // 2), rnd, color=tinta)


# El naranjal donde Godoy las corto. Es el mismo "arbol" de siempre - mismo
# tronco, misma copa - con naranjas colgando, porque un arbol cualquiera no
# dice "naranjal" y la escena de cortarlas necesita que se note de que
# arbol son.
def _naranjo(d, x, y, t, rnd, g, tinta=TINTA):
    alto = t * 1.6
    arbol(d, x, y, alto, rnd)
    copa_y = y - alto * 0.92
    r = alto * 0.46
    for _ in range(5):
        fx = x + rnd.uniform(-r * .5, r * .5)
        fy = copa_y + rnd.uniform(-r * .32, r * .36)
        _circulo(d, (fx, fy), t * .055, g, rnd, relleno=(230, 126, 34), color=tinta)


def _libro(d, x, y, t, rnd, g, tinta=TINTA):
    """Salia una pajarita: tenia las paginas al reves. Un libro abierto son
    dos hojas que se hunden en el centro y suben por fuera."""
    izq = [(x-t*.02, y-t*.10), (x-t*.44, y-t*.22), (x-t*.44, y-t*.56),
           (x-t*.02, y-t*.44)]
    der = [(x+t*.02, y-t*.10), (x+t*.44, y-t*.22), (x+t*.44, y-t*.56),
           (x+t*.02, y-t*.44)]
    for hoja in (izq, der):
        d.polygon(hoja, fill=PAPEL_VIEJO); _linea(d, hoja + [hoja[0]], g, rnd, color=tinta)
    _linea(d, [(x, y-t*.44), (x, y-t*.10)], g, rnd, color=tinta)
    for k in (1, 2):
        _linea(d, [(x-t*.36, y-t*.50+t*.08*k), (x-t*.08, y-t*.40+t*.08*k)],
               max(2, g//2), rnd, color=tinta)
        _linea(d, [(x+t*.08, y-t*.40+t*.08*k), (x+t*.36, y-t*.50+t*.08*k)],
               max(2, g//2), rnd, color=tinta)


# ---- BANDERAS ---------------------------------------------------------------
# Ella, viendo el #91: "hay que darles color a las banderas y esas cosas". Y
# tenia razon de sobra: el video iba de una isla que es española medio año y
# francesa el otro medio, y las dos banderas se dibujaban EXACTAMENTE IGUAL,
# un paño rojo liso. La unica imagen que contaba el tema de un vistazo estaba
# sin usar.
#
# Las franjas van en fracciones del paño, de arriba a abajo o de izquierda a
# derecha, que es como estan hechas casi todas.
ROJO_ESPAÑA  = (198, 11, 30)
ORO_ESPAÑA   = (255, 196, 0)
AZUL_FRANCIA = (0, 85, 164)
ROJO_FRANCIA = (239, 65, 53)
BLANCO       = (250, 248, 244)

_BANDERAS = {
    # (franjas, horizontal)   franjas = [(color, parte del paño), ...]
    "bandera":           ([((170, 44, 44), 1.0)], True),
    "bandera_espana":    ([(ROJO_ESPAÑA, .25), (ORO_ESPAÑA, .50), (ROJO_ESPAÑA, .25)], True),
    "bandera_francia":   ([(AZUL_FRANCIA, 1/3), (BLANCO, 1/3), (ROJO_FRANCIA, 1/3)], False),
    "bandera_blanca":    ([(BLANCO, 1.0)], True),
    "bandera_inglaterra": ([(BLANCO, 1.0)], True),   # la cruz se pinta aparte
    # Las que va a pedir la historia de España, no solo la guerra de las
    # naranjas: Portugal (1801, y todas las demas), EEUU (1898, el Maine),
    # Holanda (Flandes y los tercios), Austria (la guerra de Sucesion),
    # Marruecos (la guerra de Africa, Annual) y la cruz de Borgoña, que es la
    # de los tercios y los carlistas. Lo que no son franjas - la esfera de
    # Portugal, el cuartel de EEUU, la estrella, el aspa - va en _ADORNOS.
    "bandera_portugal":  ([((0, 102, 51), .40), ((206, 17, 38), .60)], False),
    "bandera_eeuu":      ([(((178, 34, 52) if k % 2 == 0 else BLANCO), 1/7) for k in range(7)], True),
    "bandera_holanda":   ([((238, 124, 20), 1/3), (BLANCO, 1/3), ((24, 64, 140), 1/3)], True),
    "bandera_austria":   ([((200, 16, 46), 1/3), (BLANCO, 1/3), ((200, 16, 46), 1/3)], True),
    "bandera_marruecos": ([((193, 39, 45), 1.0)], True),
    "bandera_borgona":   ([(BLANCO, 1.0)], True),
    # LEPANTO. Los dos bandos del Mediterraneo en el siglo XVI: la media luna
    # otomana, el leon de San Marcos de Venecia, las llaves del Papa y el
    # estandarte azul de la Liga Santa que llevaba don Juan de Austria.
    "bandera_otomana":   ([((196, 30, 40), 1.0)], True),
    "bandera_venecia":   ([((150, 20, 34), 1.0)], True),
    "bandera_papal":     ([((246, 206, 60), .5), (BLANCO, .5)], False),
    "bandera_liga_santa": ([((40, 70, 150), 1.0)], True),
}


def _en_paño(borde, u0, u1, v0, v1):
    """Un trozo del paño en sus propias coordenadas (u a lo largo, v de
    arriba a abajo), siguiendo la ondulacion y el espejo del trapo - asi lo
    que va encima no se sale de la bandera cuando esta ondea al reves."""
    (ax, ay), (bx, by), (cx, cy), (dx, dy) = borde

    def p(u, v):
        tx, ty = ax + (bx-ax)*u, ay + (by-ay)*u
        fx, fy = dx + (cx-dx)*u, dy + (cy-dy)*u
        return (tx + (fx-tx)*v, ty + (fy-ty)*v)
    return [p(u0, v0), p(u1, v0), p(u1, v1), p(u0, v1)]


def _centro_paño(borde, u, v):
    return _en_paño(borde, u, u, v, v)[0]


def _adorno_portugal(d, borde, t, g, rnd):
    cx, cy = _centro_paño(borde, .40, .50)
    _circulo(d, (cx, cy), t*.075, max(2, g//2), rnd, relleno=(255, 204, 0), color=TINTA)


def _adorno_eeuu(d, borde, t, g, rnd):
    d.polygon(_en_paño(borde, 0, .42, 0, 4/7), fill=(60, 59, 110))
    for u, v in ((.10, .15), (.28, .15), (.19, .32), (.10, .47), (.28, .47)):
        cx, cy = _centro_paño(borde, u, v)
        d.ellipse([cx - t*.012, cy - t*.012, cx + t*.012, cy + t*.012], fill=BLANCO)


def _adorno_marruecos(d, borde, t, g, rnd):
    cx, cy = _centro_paño(borde, .50, .50)
    r = t*.10
    puntas = [(cx + r*math.sin(k*4*math.pi/5), cy - r*math.cos(k*4*math.pi/5)) for k in range(6)]
    _linea(d, puntas, max(2, g//2), rnd, color=(0, 98, 51), temblor=0.6)


def _adorno_borgona(d, borde, t, g, rnd):
    # El aspa de Borgoña son dos troncos cruzados, nudosos: con temblor alto
    # se lee como palo y no como una X de tachado.
    for a, b in (((.10, .10), (.90, .90)), ((.90, .10), (.10, .90))):
        _linea(d, [_centro_paño(borde, *a), _centro_paño(borde, *b)], int(g*1.7), rnd,
               color=ROJO_ESPAÑA, temblor=2.4)


def _adorno_otomana(d, borde, t, g, rnd):
    """Media luna y estrella blancas."""
    cx, cy = _centro_paño(borde, .44, .50)
    r = t*.12
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BLANCO)
    rojo = (196, 30, 40)
    d.ellipse([cx - r*.55, cy - r*.85, cx + r*1.15, cy + r*.85], fill=rojo)
    ex, ey, re_ = cx + r*1.05, cy, t*.045
    puntas = []
    for k in range(10):
        a = -math.pi/2 + k*math.pi/5
        rr = re_ if k % 2 == 0 else re_*.45
        puntas.append((ex + rr*math.cos(a), ey + rr*math.sin(a)))
    d.polygon(puntas, fill=BLANCO)


def _adorno_venecia(d, borde, t, g, rnd):
    """El leon alado de San Marcos, en oro: cuerpo, cabeza con melena, un ala
    y la cola. A este tamaño no hace falta mas para que sea un leon."""
    oro = (236, 186, 40)
    cx, cy = _centro_paño(borde, .50, .55)
    r = t*.06
    d.ellipse([cx - r*1.6, cy - r*.6, cx + r*1.2, cy + r*.7], fill=oro)          # cuerpo
    d.ellipse([cx + r*.7, cy - r*1.5, cx + r*2.0, cy - r*.2], fill=oro)          # melena
    d.polygon([(cx - r*.6, cy - r*.4), (cx - r*1.4, cy - r*2.2), (cx + r*.4, cy - r*.6)], fill=oro)  # ala
    for px in (-1.2, -.4, .5, 1.0):                                               # patas
        d.line([(cx + r*px, cy + r*.4), (cx + r*px, cy + r*1.3)], fill=oro, width=max(2, g//2))
    d.line([(cx - r*1.5, cy), (cx - r*2.2, cy - r*.9)], fill=oro, width=max(2, g//2))  # cola


def _adorno_papal(d, borde, t, g, rnd):
    """Las llaves de San Pedro, cruzadas."""
    cx, cy = _centro_paño(borde, .50, .50)
    r = t*.11
    for lado in (-1, 1):
        a, b = (cx - lado*r, cy + r), (cx + lado*r*.8, cy - r*.8)
        d.line([a, b], fill=TINTA, width=max(2, g//2))
        d.ellipse([b[0] - r*.25, b[1] - r*.25, b[0] + r*.25, b[1] + r*.25], outline=TINTA,
                  width=max(2, g//2))
        d.line([a, (a[0] + lado*r*.3, a[1])], fill=TINTA, width=max(2, g//2))


def _adorno_liga_santa(d, borde, t, g, rnd):
    """La cruz dorada sobre azul del estandarte de la Liga Santa."""
    oro = (236, 186, 40)
    _linea(d, [_centro_paño(borde, .50, .14), _centro_paño(borde, .50, .88)], int(g*1.5), rnd,
           color=oro, temblor=0.6)
    _linea(d, [_centro_paño(borde, .28, .36), _centro_paño(borde, .72, .36)], int(g*1.5), rnd,
           color=oro, temblor=0.6)


_ADORNOS = {
    "bandera_otomana": _adorno_otomana, "bandera_venecia": _adorno_venecia,
    "bandera_papal": _adorno_papal, "bandera_liga_santa": _adorno_liga_santa,
    "bandera_portugal": _adorno_portugal, "bandera_eeuu": _adorno_eeuu,
    "bandera_marruecos": _adorno_marruecos, "bandera_borgona": _adorno_borgona,
}


def _paño(d, x, y, t, rnd, g, tinta, franjas, horizontal, hacia=1):
    """El trapo de una bandera, ondeando, con sus franjas dentro.

    Se dibuja como cuatro esquinas y se reparte por dentro en trozos rectos:
    una franja curvada seria mas bonita y a este tamaño no se notaria, y las
    franjas rectas se leen mejor en un movil.
    """
    x0, x1 = x, x + hacia*t*.56
    arriba_i, arriba_d = y - t*1.06, y - t*.92
    abajo_i,  abajo_d  = y - t*.66,  y - t*.62
    borde = [(x0, arriba_i), (x1, arriba_d), (x1, abajo_d), (x0, abajo_i)]

    corrido = 0.0
    for color, parte in franjas:
        a, b = corrido, corrido + parte
        corrido = b
        if horizontal:
            trozo = [(x0, arriba_i + (abajo_i-arriba_i)*a), (x1, arriba_d + (abajo_d-arriba_d)*a),
                     (x1, arriba_d + (abajo_d-arriba_d)*b), (x0, arriba_i + (abajo_i-arriba_i)*b)]
        else:
            # OJO con el max() aqui: con la bandera al reves x1-x0 es NEGATIVO,
            # y max(negativo, 1e-6) da 1e-6. Eso reventaba la interpolacion y
            # la bandera espejada salia con el contorno y sin franjas.
            vuelo = (x1 - x0) or 1e-6
            xa, xb = x0 + vuelo*a, x0 + vuelo*b
            arr = lambda xx: arriba_i + (arriba_d-arriba_i)*((xx-x0)/vuelo)
            aba = lambda xx: abajo_i + (abajo_d-abajo_i)*((xx-x0)/vuelo)
            trozo = [(xa, arr(xa)), (xb, arr(xb)), (xb, aba(xb)), (xa, aba(xa))]
        d.polygon(trozo, fill=color)
    return borde


def _bandera_de(nombre):
    franjas, horizontal = _BANDERAS[nombre]

    def dibuja(d, x, y, t, rnd, g, tinta=TINTA):
        _linea(d, [(x, y), (x, y-t*1.10)], g, rnd, color=tinta)
        # El trapo ondea hacia donde HAY SITIO. Puesta en el lado derecho del
        # plano, la bandera se salia por el borde y se veia media Francia.
        ancho = getattr(getattr(d, "_image", None), "width", 0)
        hacia = -1 if (ancho and x + t*.62 > ancho) else 1
        borde = _paño(d, x, y, t, rnd, g, tinta, franjas, horizontal, hacia)
        if nombre == "bandera_inglaterra":  # noqa: la cruz, encima del paño
            cx, cy = x + hacia*t*.28, y - t*.84
            d.rectangle([cx-t*.04, cy-t*.16, cx+t*.04, cy+t*.16], fill=ROJO_ESPAÑA)
            d.rectangle([min(cx-t*.24, cx+t*.24), cy-t*.04,
                         max(cx-t*.24, cx+t*.24), cy+t*.04], fill=ROJO_ESPAÑA)
        adorno = _ADORNOS.get(nombre)
        if adorno:
            adorno(d, borde, t, g, rnd)
        _linea(d, borde, g, rnd, color=tinta)
    return dibuja


def _cruz(d, x, y, t, rnd, g, tinta=TINTA):
    _linea(d, [(x, y), (x, y-t*.90)], max(g, int(t*.08)), rnd, color=tinta)
    _linea(d, [(x-t*.28, y-t*.62), (x+t*.28, y-t*.62)], max(g, int(t*.08)), rnd, color=tinta)


def _olla(d, x, y, t, rnd, g, tinta=TINTA):
    """Era un cuenco con una raya encima. Una olla tiene ASAS y tapa."""
    cuerpo = [(x-t*.32, y-t*.46), (x+t*.32, y-t*.46), (x+t*.26, y), (x-t*.26, y)]
    d.polygon(cuerpo, fill=(146, 142, 136)); _linea(d, cuerpo + [cuerpo[0]], g, rnd, color=tinta)
    for lado in (-1, 1):
        d.arc([x+lado*t*.30-t*.12, y-t*.46, x+lado*t*.30+t*.12, y-t*.22],
              0, 360, fill=tinta, width=g)
    _linea(d, [(x-t*.38, y-t*.48), (x+t*.38, y-t*.48)], g, rnd, color=tinta)
    _circulo(d, (x, y-t*.56), t*.07, g, rnd, relleno=(255, 255, 255), color=tinta)


def _montaña(d, x, y, t, rnd, g, tinta=TINTA):
    _linea(d, [(x-t*.80, y), (x-t*.24, y-t*.86), (x+t*.06, y-t*.46),
               (x+t*.34, y-t*.72), (x+t*.86, y)], g, rnd, color=tinta)


def _nube(d, x, y, t, rnd, g, tinta=TINTA):
    for dx, r in ((-.28, .22), (0, .30), (.28, .22)):
        _circulo(d, (x+t*dx, y), t*r, g, rnd, relleno=(255, 255, 255), color=tinta)


def _sol(d, x, y, t, rnd, g, tinta=TINTA):
    _circulo(d, (x, y), t*.30, g, rnd, relleno=(250, 214, 90), color=tinta)
    for k in range(8):
        a = k/8*2*math.pi
        _linea(d, [(x+math.cos(a)*t*.40, y+math.sin(a)*t*.40),
                   (x+math.cos(a)*t*.58, y+math.sin(a)*t*.58)], g, rnd, color=tinta)


# ---- MAS COSAS, pensadas para lo que sale en la historia de España -------
# Motines y fiestas (la multitud, el toro, la guitarra), la corte y los
# tratados (el pergamino, la carta), los barcos y las Americas (el cofre, el
# catalejo, el barril), y las mazmorras (la antorcha, las cadenas).

def _multitud(d, x, y, t, rnd, g, tinta=TINTA):
    """Un gentio de fondo: "aparecen cincuenta monigotes" en Esquilache no
    tenia con que dibujarse. Pequeños, grises y con los brazos arriba, para
    que se lean como masa y no le roben el plano a los que hablan."""
    gris, relleno = (120, 112, 104), (236, 232, 224)
    for k in range(9):
        px = x + t*(-2.6 + 5.2*k/8) + t*0.10*rnd.uniform(-1, 1)
        alto = t*(1.9 + 0.35*((k*7) % 3)/2)
        pose = ("brazos_arriba", "señala", "brazos_arriba", "de_pie")[k % 4]
        figura(d, px, y - t*0.02*(k % 2), alto, rnd, pose, "grito", None, k % 2 == 1,
               tinta=gris, relleno=relleno)


def _toro(d, x, y, t, rnd, g, tinta=TINTA):
    """El toro, de perfil y negro: fiestas, plazas, y medio refranero."""
    negro = (40, 34, 32)
    d.ellipse([x - t*.62, y - t*.72, x + t*.40, y - t*.28], fill=negro)
    for px in (-.45, -.25, .10, .28):
        _linea(d, [(x + t*px, y - t*.36), (x + t*px, y)], int(g*1.8), rnd, color=negro, temblor=0.6)
    d.ellipse([x + t*.30, y - t*.82, x + t*.66, y - t*.46], fill=negro)
    marfil = (236, 226, 200)
    for dx in (.36, .58):
        _linea(d, [(x + t*dx, y - t*.78), (x + t*(dx - .06), y - t*.96), (x + t*(dx + .04), y - t*1.02)],
               g, rnd, color=marfil, temblor=0.5)
    _linea(d, [(x - t*.60, y - t*.62), (x - t*.78, y - t*.40), (x - t*.74, y - t*.26)],
           max(2, g//2), rnd, color=negro)
    d.ellipse([x + t*.50, y - t*.72, x + t*.56, y - t*.66], fill=(230, 60, 40))


def _guitarra(d, x, y, t, rnd, g, tinta=TINTA):
    """La guitarra española, de pie: fiestas, tabernas, el que canta."""
    madera = (200, 142, 76)
    d.ellipse([x - t*.20, y - t*.40, x + t*.20, y], fill=madera, outline=tinta, width=g)
    d.ellipse([x - t*.15, y - t*.66, x + t*.15, y - t*.34], fill=madera, outline=tinta, width=g)
    d.ellipse([x - t*.06, y - t*.36, x + t*.06, y - t*.24], fill=(60, 40, 24))
    d.rectangle([x - t*.03, y - t*1.02, x + t*.03, y - t*.62], fill=(110, 72, 40), outline=tinta)
    d.rectangle([x - t*.05, y - t*1.14, x + t*.05, y - t*1.00], fill=(90, 58, 32), outline=tinta)


def _pergamino(d, x, y, t, rnd, g, tinta=TINTA):
    """El pergamino enrollado por arriba y por abajo: el tratado, la bula, la
    real cedula, el mapa del tesoro."""
    papel = (240, 226, 186)
    d.rectangle([x - t*.24, y - t*.86, x + t*.24, y - t*.10], fill=papel)
    _linea(d, [(x - t*.24, y - t*.86), (x - t*.24, y - t*.10)], max(2, g//2), rnd)
    _linea(d, [(x + t*.24, y - t*.86), (x + t*.24, y - t*.10)], max(2, g//2), rnd)
    for yy in (y - t*.90, y - t*.08):
        d.rounded_rectangle([x - t*.30, yy - t*.06, x + t*.30, yy + t*.06], radius=int(t*.05),
                            fill=(214, 196, 150), outline=tinta, width=max(2, g//2))
    for k in range(4):
        yy = y - t*(.72 - .14*k)
        _linea(d, [(x - t*.16, yy), (x + t*(.16 - .06*(k == 3)), yy)], max(1, g//3), rnd,
               color=(120, 100, 70), temblor=0.8)
    d.ellipse([x + t*.04, y - t*.30, x + t*.18, y - t*.16], fill=ROJO)


def _cofre(d, x, y, t, rnd, g, tinta=TINTA):
    """El cofre abierto con el oro dentro: tesoros, las Indias, el botin."""
    madera = (130, 84, 44)
    d.rectangle([x - t*.40, y - t*.40, x + t*.40, y], fill=madera, outline=tinta, width=g)
    d.polygon([(x - t*.40, y - t*.40), (x - t*.34, y - t*.78), (x + t*.34, y - t*.78),
               (x + t*.40, y - t*.40)], fill=(150, 98, 52), outline=tinta)
    for k in range(6):
        cx = x - t*.28 + t*.11*k
        d.ellipse([cx - t*.07, y - t*.50, cx + t*.07, y - t*.36], fill=ORO_ESPAÑA, outline=tinta)
    for bx in (-.30, .30):
        d.rectangle([x + t*bx - t*.03, y - t*.40, x + t*bx + t*.03, y], fill=(200, 160, 60))
    d.rectangle([x - t*.06, y - t*.30, x + t*.06, y - t*.18], fill=(200, 160, 60), outline=tinta)


def _barril(d, x, y, t, rnd, g, tinta=TINTA):
    """El barril: polvora, vino, las bodegas de un galeon."""
    d.rounded_rectangle([x - t*.24, y - t*.62, x + t*.24, y], radius=int(t*.12),
                        fill=(156, 104, 58), outline=tinta, width=g)
    for yy in (.12, .50):
        d.line([(x - t*.24, y - t*yy), (x + t*.24, y - t*yy)], fill=(80, 70, 64), width=max(3, g))
    for dx in (-.10, .10):
        d.line([(x + t*dx, y - t*.60), (x + t*dx, y - t*.02)], fill=(120, 78, 42), width=max(1, g//3))


def _antorcha(d, x, y, t, rnd, g, tinta=TINTA):
    """La antorcha: mazmorras, castillos de noche, la turba que viene."""
    _linea(d, [(x - t*.03, y), (x + t*.03, y - t*.62)], int(g*1.6), rnd, color=(110, 72, 40))
    llama = [(x + t*.03, y - t*1.02), (x + t*.14, y - t*.74), (x + t*.07, y - t*.60),
             (x - t*.04, y - t*.62), (x - t*.08, y - t*.78)]
    d.polygon(llama, fill=(250, 150, 40))
    d.polygon([(x + t*.03, y - t*.88), (x + t*.08, y - t*.72), (x, y - t*.64)], fill=(255, 224, 90))


def _catalejo(d, x, y, t, rnd, g, tinta=TINTA):
    """El catalejo: el vigia, el almirante, "¡tierra a la vista!"."""
    laton = (206, 164, 70)
    for k, (x0, x1, r) in enumerate(((-.50, -.10, .08), (-.12, .22, .065), (.20, .48, .05))):
        d.rectangle([x + t*x0, y - t*(.30 + r), x + t*x1, y - t*(.30 - r)],
                    fill=laton if k != 1 else (178, 136, 56), outline=tinta, width=max(2, g//2))
    d.ellipse([x - t*.54, y - t*.40, x - t*.46, y - t*.20], fill=(150, 190, 220), outline=tinta)


def _carta(d, x, y, t, rnd, g, tinta=TINTA):
    """La carta cerrada con lacre: noticias, ordenes, la declaracion de
    guerra que llega por correo."""
    papel = (244, 238, 222)
    d.rectangle([x - t*.34, y - t*.46, x + t*.34, y], fill=papel, outline=tinta, width=g)
    d.line([(x - t*.34, y - t*.46), (x, y - t*.18), (x + t*.34, y - t*.46)], fill=tinta, width=g)
    d.ellipse([x - t*.07, y - t*.26, x + t*.07, y - t*.12], fill=ROJO, outline=tinta)


def _cadenas(d, x, y, t, rnd, g, tinta=TINTA):
    """Cadenas colgando de la pared, con su grillete: carceles y mazmorras."""
    hierro = (110, 110, 116)
    for k in range(6):
        cy = y - t + t*0.13*k
        if k % 2 == 0:
            d.ellipse([x - t*.05, cy - t*.08, x + t*.05, cy + t*.08], outline=hierro, width=max(3, g))
        else:
            d.ellipse([x - t*.08, cy - t*.05, x + t*.08, cy + t*.05], outline=hierro, width=max(3, g))
    d.arc([x - t*.13, y - t*.30, x + t*.13, y - t*.04], 0, 360, fill=hierro, width=max(4, int(g*1.4)))


# Lo de la vivienda: la manifestacion, el Bizum, la noticia del final y el
# politico que viene con su camara. Sirven igual para cualquier protesta,
# cualquier "ultima hora" y cualquier rueda de prensa.
def _pancarta(d, x, y, t, rnd, g, tinta=TINTA):
    """Pancarta de manifestacion: un palo y un carton con letras rojas."""
    _linea(d, [(x, y), (x, y - t*1.05)], g, rnd, color=MADERA_OSCURA)
    ancho, alto = t*0.95, t*0.48
    x0, y0 = x - ancho/2, y - t*1.25
    d.rectangle([x0, y0, x0 + ancho, y0 + alto], fill=(250, 248, 240))
    _linea(d, [(x0, y0), (x0 + ancho, y0), (x0 + ancho, y0 + alto), (x0, y0 + alto), (x0, y0)],
           g, rnd, color=tinta, temblor=1.2)
    texto = "¡VIVIENDA!"
    px = int(alto*0.42)
    for _ in range(10):
        f = _fuente_cartel(px)
        if d.textlength(texto, font=f) <= ancho*0.86 or px <= 10:
            break
        px = int(px*0.88)
    d.text((x - d.textlength(texto, font=f)/2, y0 + alto*0.26), texto, font=f, fill=ROJO_ESPAÑA)


def _movil(d, x, y, t, rnd, g, tinta=TINTA):
    """Un movil con la pantalla encendida y un Bizum entrando."""
    ancho, alto = t*0.50, t*0.90
    x0, y0 = x - ancho/2, y - alto
    d.rounded_rectangle([x0, y0, x0 + ancho, y], radius=int(ancho*0.16), fill=(40, 40, 46),
                        outline=tinta, width=max(2, g//2))
    m = ancho*0.10
    d.rectangle([x0 + m, y0 + m*1.6, x0 + ancho - m, y - m*1.6], fill=(120, 200, 230))
    d.rounded_rectangle([x0 + m*1.6, y0 + alto*0.30, x0 + ancho - m*1.6, y0 + alto*0.46],
                        radius=int(m), fill=(80, 190, 120))


def _periodico(d, x, y, t, rnd, g, tinta=TINTA):
    """El periodico abierto: titular gordo y columnas. La ultima hora."""
    ancho, alto = t*1.05, t*0.75
    x0, y0 = x - ancho/2, y - alto
    d.rectangle([x0, y0, x0 + ancho, y], fill=(236, 232, 220))
    _linea(d, [(x0, y0), (x0 + ancho, y0), (x0 + ancho, y), (x0, y), (x0, y0)],
           max(2, g//2), rnd, color=tinta, temblor=1.0)
    _linea(d, [(x, y0), (x, y)], max(2, g//3), rnd, color=(160, 156, 146), temblor=0.6)
    for lado in (0, 1):
        cx0 = x0 + ancho*(0.06 + 0.5*lado)
        d.rectangle([cx0, y0 + alto*0.10, cx0 + ancho*0.38, y0 + alto*0.24], fill=tinta)
        for k in range(4):
            yy = y0 + alto*(0.38 + 0.14*k)
            _linea(d, [(cx0, yy), (cx0 + ancho*0.38, yy)], max(2, g//3), rnd,
                   color=(120, 116, 108), temblor=0.6)


def _camara_tv(d, x, y, t, rnd, g, tinta=TINTA):
    """Camara de television en su tripode, con el pilotito rojo de grabando."""
    for dx in (-0.30, 0.0, 0.30):
        _linea(d, [(x, y - t*0.55), (x + t*dx, y)], g, rnd, color=tinta)
    cw, ch = t*0.62, t*0.34
    cx0, cy0 = x - cw*0.55, y - t*0.55 - ch
    d.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + ch], radius=int(ch*0.18), fill=(54, 54, 62),
                        outline=tinta, width=g)
    d.rectangle([cx0 + cw, cy0 + ch*0.22, cx0 + cw + t*0.16, cy0 + ch*0.78], fill=(30, 30, 36),
                outline=tinta, width=max(2, g//2))
    r = ch*0.12
    d.ellipse([cx0 + cw*0.12 - r, cy0 + ch*0.25 - r, cx0 + cw*0.12 + r, cy0 + ch*0.25 + r],
              fill=(230, 40, 40))
    d.text((cx0 + cw*0.30, cy0 + ch*0.28), "TV", font=_fuente_cartel(int(ch*0.42)),
           fill=(240, 240, 240))


def _ataud(d, x, y, t, rnd, g, tinta=TINTA):
    """El ataud, tumbado: la caja de madera oscura con su tapa, mas ancha
    por los hombros, y una cruz dorada. x es el centro, y la base."""
    largo, alto = t*1.6, t*0.38
    x0, x1 = x - largo/2, x + largo/2
    caja = [(x0, y - alto*0.15), (x0 + largo*0.22, y - alto), (x1, y - alto*0.80), (x1, y),
            (x0 + largo*0.22, y), (x0, y - alto*0.15)]
    d.polygon(caja, fill=(86, 52, 30))
    _linea(d, caja, g, rnd, color=tinta, temblor=1.0)
    tapa = [(x0 - t*0.03, y - alto*0.30), (x0 + largo*0.22, y - alto*1.18),
            (x1 + t*0.03, y - alto*0.98), (x1 + t*0.03, y - alto*0.78)]
    d.polygon(tapa + [(x0 + largo*0.22, y - alto*0.90)], fill=(110, 70, 40))
    _linea(d, tapa, max(2, g//2), rnd, color=tinta, temblor=1.0)
    cx, cy = x0 + largo*0.56, y - alto*0.52
    d.line([(cx - t*0.12, cy), (cx + t*0.12, cy)], fill=ORO_ESPAÑA, width=max(3, g))
    d.line([(cx - t*0.04, cy - t*0.10), (cx - t*0.04, cy + t*0.10)], fill=ORO_ESPAÑA, width=max(3, g))
    for px in (x0 + largo*0.30, x0 + largo*0.80):           # las asas
        d.line([(px - t*0.05, y - alto*0.45), (px + t*0.05, y - alto*0.45)], fill=(200, 170, 90),
               width=max(2, g//2))


def _calendario(d, x, y, t, rnd, g, tinta=TINTA):
    """La hoja del calendario: OCTUBRE en rojo, un 15 enorme y el 4 de ayer
    tachado en la esquina. Para los diez dias que desaparecieron en 1582, y
    para cualquier fecha que importe."""
    ancho, alto = t*0.80, t*0.95
    x0, y0 = x - ancho/2, y - alto
    d.rectangle([x0, y0, x0 + ancho, y], fill=(250, 248, 240), outline=tinta, width=max(2, g//2))
    d.rectangle([x0, y0, x0 + ancho, y0 + alto*0.24], fill=ROJO_ESPAÑA)
    for k in range(4):                                   # las anillas
        ax = x0 + ancho*(0.2 + 0.2*k)
        d.line([(ax, y0 - alto*0.05), (ax, y0 + alto*0.05)], fill=tinta, width=max(2, g//2))
    def escribe(texto, px, cx, cy, color):
        for _ in range(10):
            f = _fuente_cartel(px)
            if d.textlength(texto, font=f) <= ancho*0.84 or px <= 8:
                break
            px = int(px*0.88)
        caja = d.textbbox((0, 0), texto, font=f)
        d.text((cx - (caja[2] - caja[0])/2, cy - (caja[3] - caja[1])/2 - caja[1]), texto,
               font=f, fill=color)
    escribe("OCTUBRE", int(alto*0.15), x, y0 + alto*0.12, (255, 255, 255))
    escribe("15", int(alto*0.48), x, y0 + alto*0.60, tinta)
    cx, cy = x0 + ancho*0.18, y0 + alto*0.34                # el 4, tachado
    escribe("4", int(alto*0.14), cx, cy, (120, 116, 108))
    d.line([(cx - alto*0.07, cy + alto*0.06), (cx + alto*0.07, cy - alto*0.06)],
           fill=ROJO_ESPAÑA, width=max(3, g))


def _pelota(d, x, y, t, rnd, g, tinta=TINTA):
    """La pelota del juego de pelota: de cuero, con su costura."""
    r = t*0.32
    cy = y - r
    d.ellipse([x - r, cy - r, x + r, cy + r], fill=(238, 228, 205), outline=tinta, width=max(2, g//2))
    d.arc([x - r*0.6, cy - r, x + r*1.4, cy + r], 120, 240, fill=(150, 90, 50), width=max(2, g//2))


def _vaso(d, x, y, t, rnd, g, tinta=TINTA):
    """Un vaso de agua bien fria, con sus gotitas por fuera."""
    alto, arriba, abajo = t*0.70, t*0.46, t*0.34
    pts = [(x - arriba/2, y - alto), (x + arriba/2, y - alto), (x + abajo/2, y), (x - abajo/2, y)]
    d.polygon(pts, fill=(225, 238, 245))
    agua = [(x - arriba*0.46, y - alto*0.75), (x + arriba*0.46, y - alto*0.75),
            (x + abajo/2 - g/2, y - g/2), (x - abajo/2 + g/2, y - g/2)]
    d.polygon(agua, fill=(120, 185, 230))
    _linea(d, pts + [pts[0]], max(2, g//2), rnd, color=tinta, temblor=0.8)
    for k in (-0.18, 0.14):                       # las gotas de lo fria que esta
        gx, gy, r = x + t*k, y - alto*0.45, t*0.035
        d.ellipse([gx - r, gy - r, gx + r, gy + r*1.6], fill=(150, 205, 240))


def _maletin(d, x, y, t, rnd, g, tinta=TINTA):
    """El maletin negro del medico, con su asa y su cierre."""
    ancho, alto = t*0.95, t*0.55
    x0, y0 = x - ancho/2, y - alto
    d.arc([x - ancho*0.18, y0 - alto*0.35, x + ancho*0.18, y0 + alto*0.25], 180, 360,
          fill=tinta, width=max(3, g))
    d.rounded_rectangle([x0, y0, x0 + ancho, y], radius=int(alto*0.25), fill=(40, 34, 30),
                        outline=tinta, width=max(2, g//2))
    d.line([(x0, y0 + alto*0.35), (x0 + ancho, y0 + alto*0.35)], fill=(80, 70, 62), width=max(2, g//2))
    d.rectangle([x - ancho*0.06, y0 + alto*0.25, x + ancho*0.06, y0 + alto*0.45], fill=ORO_ESPAÑA)


def _tienda(d, x, y, t, rnd, g, tinta=TINTA):
    """Tienda de campaña de las de ahora, la iglu de colores: la acampada.
    La del campamento del ejercito es otra (lona y palo), esta es de Sol."""
    colores = ((60, 130, 200), (230, 140, 40), (80, 160, 90), (200, 70, 70))
    color = colores[int(x) % len(colores)]
    ancho, alto = t*1.3, t*0.75
    caja = [x - ancho/2, y - alto, x + ancho/2, y + alto]   # media elipse: la cupula
    d.chord(caja, 180, 360, fill=color)
    d.arc(caja, 180, 360, fill=tinta, width=g)
    _linea(d, [(x - ancho/2, y), (x + ancho/2, y)], g, rnd, color=tinta, temblor=1.0)
    _linea(d, [(x - ancho*0.30, y - alto*0.80), (x, y - alto), (x + ancho*0.30, y - alto*0.80)],
           max(2, g//2), rnd, color=tinta, temblor=1.0)
    puerta = [(x - ancho*0.16, y), (x, y - alto*0.62), (x + ancho*0.16, y)]
    d.polygon(puerta, fill=(40, 36, 34))
    _linea(d, puerta, max(2, g//2), rnd, color=tinta, temblor=1.0)


def _ambulancia(d, x, y, t, rnd, g, tinta=TINTA):
    """La ambulancia, de lado, con las puertas de atras abiertas: es donde
    acaba la camilla. x es el centro, y el suelo."""
    largo, alto = t*2.3, t*1.05
    x0, x1 = x - largo/2, x + largo/2
    techo = y - alto
    blanco, rojo, cristal = (246, 246, 242), (214, 40, 40), (150, 196, 228)
    # caja de atras y cabina (la cabina al lado derecho, mas baja)
    d.rounded_rectangle([x0, techo, x0 + largo*0.70, y - t*0.14], radius=int(t*0.06),
                        fill=blanco, outline=tinta, width=g)
    cab = [(x0 + largo*0.70, techo + alto*0.22), (x0 + largo*0.86, techo + alto*0.22),
           (x1, techo + alto*0.55), (x1, y - t*0.14), (x0 + largo*0.70, y - t*0.14)]
    d.polygon(cab, fill=blanco)
    _linea(d, cab + [cab[0]], g, rnd, color=tinta, temblor=1.0)
    d.polygon([(x0 + largo*0.73, techo + alto*0.28), (x0 + largo*0.85, techo + alto*0.28),
               (x0 + largo*0.95, techo + alto*0.53), (x0 + largo*0.73, techo + alto*0.53)],
              fill=cristal, outline=tinta)
    # franja roja y la cruz
    d.rectangle([x0, y - t*0.42, x1, y - t*0.32], fill=rojo)
    cx, cy, r = x0 + largo*0.35, techo + alto*0.36, t*0.17
    d.rectangle([cx - r, cy - r*0.32, cx + r, cy + r*0.32], fill=rojo)
    d.rectangle([cx - r*0.32, cy - r, cx + r*0.32, cy + r], fill=rojo)
    # la sirena azul
    d.rectangle([x0 + largo*0.30, techo - t*0.10, x0 + largo*0.42, techo], fill=(60, 110, 230),
                outline=tinta, width=max(2, g//2))
    # las puertas de atras abiertas, a la izquierda
    for k, ancho in ((0, t*0.30), (1, t*0.22)):
        px = x0 - ancho*(0.6 + 0.5*k)
        d.polygon([(x0, techo + t*0.04), (px, techo + t*0.10 + k*t*0.05),
                   (px, y - t*0.20 - k*t*0.04), (x0, y - t*0.16)], fill=(236, 236, 232),
                  outline=tinta)
    # ruedas
    for rx in (x0 + largo*0.18, x0 + largo*0.84):
        rr = t*0.16
        d.ellipse([rx - rr, y - rr*2, rx + rr, y], fill=(40, 40, 44), outline=tinta, width=g)
        d.ellipse([rx - rr*0.45, y - rr*1.45, rx + rr*0.45, y - rr*0.55], fill=(170, 170, 176))


COSAS = {
    "perro": _perro, "caballo": _caballo, "barco": _barco, "casa": _casa,
    "iglesia": _iglesia, "castillo": _castillo, "espada": _espada,
    "galera": lambda d, x, y, t, rnd, g, tinta=TINTA: _galera(d, x, y, t*0.95, rnd, g),
    "galeaza": lambda d, x, y, t, rnd, g, tinta=TINTA: _galeaza(d, x, y, t, rnd, g),
    "gondola": lambda d, x, y, t, rnd, g, tinta=TINTA: _gondola(d, x, y, t, rnd, g),
    "canion": _canion, "fuego": _fuego, "dinero": _dinero, "libro": _libro,
    "cruz": _cruz, "olla": _olla, "montaña": _montaña, "naranjas": _naranjas,
    "naranjo": _naranjo, "pan": _pan, "escudo": _escudo, "mapa": _mapa,
    "cesta": _cesta,
    "multitud": _multitud, "toro": _toro, "guitarra": _guitarra, "pergamino": _pergamino,
    "cofre": _cofre, "barril": _barril, "antorcha": _antorcha, "catalejo": _catalejo,
    "carta": _carta, "cadenas": _cadenas,
    "campana": lambda d, x, y, t, rnd, g, tinta=TINTA: _campana(d, x, y, t, rnd, g),
    "pancarta": _pancarta, "movil": _movil, "periodico": _periodico, "camara_tv": _camara_tv,
    "tienda": _tienda, "ambulancia": _ambulancia, "ataud": _ataud, "calendario": _calendario,
    "pelota": _pelota, "vaso": _vaso, "maletin": _maletin,
    "nube": _nube, "sol": _sol,
    # El arbol ya existia pero con otra firma, y por estar aqui a None se
    # caia en silencio: el prompt lo ofrecia y limpia() lo tiraba.
    "arbol": lambda d, x, y, t, rnd, g, tinta=TINTA: arbol(d, x, y, t*1.6, rnd),
}
# Las banderas, todas de la misma fabrica: cambia el reparto de franjas, no el
# dibujo. Escribir cinco funciones casi iguales es como se acaba teniendo una
# que se actualiza y cuatro que no.
COSAS.update({nombre: _bandera_de(nombre) for nombre in _BANDERAS})

COSAS_VALIDAS = tuple(COSAS)


# ---- DECORADOS CON FONDO -----------------------------------------------------
# Ella, enseñandome una taberna dibujada con palotes igual que los mios pero
# con entramado de madera, chimenea de ladrillo, mapas en las mesas y el
# puerto por la ventana: "las escenas siempre son las mismas, igual no
# necesitan mas movimiento si no mejorar la imagen, el fondo".
#
# Tiene razon y cambia la prioridad. En esa imagen no se mueve NADA y te
# quedas mirandola, porque hay cosas que ver. Lo mio eran dos bandas de color
# planas, asi que todas las escenas se parecian aunque los monigotes hicieran
# cosas distintas.
#
# Lo que da profundidad es tener CAPAS: algo al fondo que se ve por un hueco
# (el mar por la ventana), la habitacion en medio, y algo delante que corta el
# plano (una viga, una mesa). Eso es lo que separa un decorado de un fondo.

MADERA_CLARA = (186, 146, 96)
LADRILLO = (166, 86, 68)
PIEDRA_CLARA = (196, 190, 180)


def _tablas(d, w, y0, y1, rnd, g, n=9):
    """Suelo de tablas con fuga: las juntas se juntan hacia el fondo."""
    d.rectangle([0, y0, w, y1], fill=MADERA)
    fuga = (w*0.5, y0 - (y1-y0)*1.2)
    for k in range(n+1):
        px = w*k/n
        _linea(d, [(px, y1), (fuga[0] + (px-fuga[0])*0.22, y0)], max(2, g//2), rnd,
               color=MADERA_OSCURA, temblor=1.2)
    for k in range(1, 4):                      # juntas transversales
        yy = y1 - (y1-y0)*(k/4)**1.7
        _linea(d, [(0, yy), (w, yy)], max(2, g//2), rnd, color=MADERA_OSCURA, temblor=1.4)


def _entramado(d, w, y0, y1, rnd, g, postes=4):
    """Pared de entramado: yeso entre vigas de madera."""
    d.rectangle([0, y0, w, y1], fill=(226, 214, 192))
    grueso = w*0.035
    for k in range(postes+1):
        px = w*k/postes - grueso/2
        d.rectangle([px, y0, px+grueso, y1], fill=MADERA_CLARA)
        _linea(d, [(px, y0), (px, y1)], max(2, g//2), rnd, color=MADERA_OSCURA, temblor=1.4)
        _linea(d, [(px+grueso, y0), (px+grueso, y1)], max(2, g//2), rnd,
               color=MADERA_OSCURA, temblor=1.4)
    for yy in (y0 + (y1-y0)*0.06, y1 - (y1-y0)*0.06):
        d.rectangle([0, yy-grueso/2, w, yy+grueso/2], fill=MADERA_CLARA)
        _linea(d, [(0, yy-grueso/2), (w, yy-grueso/2)], max(2, g//2), rnd,
               color=MADERA_OSCURA, temblor=1.4)
        _linea(d, [(0, yy+grueso/2), (w, yy+grueso/2)], max(2, g//2), rnd,
               color=MADERA_OSCURA, temblor=1.4)


def _chimenea(d, x, y_suelo, ancho, alto, rnd, g, encendida=True):
    x0, x1 = x-ancho/2, x+ancho/2
    y0 = y_suelo - alto
    d.rectangle([x0, y0, x1, y_suelo], fill=LADRILLO)
    fila_h = alto/9
    for f in range(9):                         # ladrillos a matajunta
        yy = y0 + f*fila_h
        _linea(d, [(x0, yy), (x1, yy)], max(2, g//2), rnd, color=(126, 62, 48), temblor=1.0)
        desfase = (ancho/4) if f % 2 else 0
        px = x0 + desfase
        while px < x1:
            _linea(d, [(px, yy), (px, yy+fila_h)], max(2, g//2), rnd,
                   color=(126, 62, 48), temblor=1.0)
            px += ancho/2
    _linea(d, [(x0, y0), (x1, y0), (x1, y_suelo)], g, rnd, color=TINTA)
    _linea(d, [(x0, y0), (x0, y_suelo)], g, rnd, color=TINTA)
    hueco = [(x-ancho*.28, y_suelo), (x-ancho*.28, y_suelo-alto*.30),
             (x, y_suelo-alto*.42), (x+ancho*.28, y_suelo-alto*.30),
             (x+ancho*.28, y_suelo)]
    d.polygon(hueco, fill=(42, 36, 32)); _linea(d, hueco, g, rnd, color=TINTA)
    if encendida:
        _fuego(d, x, y_suelo-alto*.02, ancho*.34, rnd, max(2, g//2), TINTA)
        for lado in (-1, 1):                   # leños
            _linea(d, [(x+lado*ancho*.20, y_suelo-alto*.02),
                       (x-lado*ancho*.06, y_suelo-alto*.06)], g, rnd, color=MADERA_OSCURA)


def _ventana_al_mar(d, x, y, ancho, alto, rnd, g, barcos=2):
    """Un hueco con OTRO mundo detras: es lo que da fondo a la escena."""
    x0, y0, x1, y1 = x-ancho/2, y-alto/2, x+ancho/2, y+alto/2
    d.rectangle([x0, y0, x1, y1], fill=(146, 198, 232))
    d.rectangle([x0, y0+alto*0.52, x1, y1], fill=(92, 140, 186))
    for k in range(barcos):
        bx = x0 + ancho*(0.22 + 0.42*k)
        _barco(d, bx, y0+alto*(0.62+0.06*k), ancho*0.26, rnd, max(2, g//2), TINTA)
    _linea(d, [(x0, y1-alto*0.36), (x1, y1-alto*0.30)], max(2, g//2), rnd,
           color=(120, 92, 62), temblor=1.4)     # el muelle
    _linea(d, [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], int(g*1.6), rnd, color=TINTA)
    _linea(d, [(x, y0), (x, y1)], g, rnd, color=TINTA)


def _adoquines(d, x0, y0, x1, y1, rnd, g):
    """Con FUGA hacia el fondo. En filas rectas parecia una pared de ladrillo
    puesta de pie, no una calle."""
    d.rectangle([x0, y0, x1, y1], fill=PIEDRA_CLARA)
    ancho_total = x1 - x0
    centro = (x0 + x1)/2
    fila, yy = 0, y0
    while yy < y1:
        f = (yy - y0)/max(1.0, y1 - y0)         # 0 al fondo, 1 delante
        alto = (y1-y0)*(0.035 + 0.075*f)
        # Cerca todo es mas ancho y esta mas abierto: eso es la fuga.
        ancho = ancho_total*(0.06 + 0.10*f)
        px = centro - ancho_total*(0.55 + 0.1*f) + (ancho/2 if fila % 2 else 0)
        while px < x1 + ancho:
            _linea(d, [(px, yy), (px+ancho*.92, yy+alto*.08),
                       (px+ancho*.88, yy+alto), (px-ancho*.04, yy+alto*.92), (px, yy)],
                   max(2, g//2), rnd, color=(150, 144, 136), temblor=1.4)
            px += ancho
        yy += alto; fila += 1


def _mesa_con_cosas(d, x, y, ancho, rnd, g, papeles=2, jarras=2, alto=None):
    alto = alto if alto else ancho*0.30
    tablero = [(x-ancho/2, y-alto), (x+ancho/2, y-alto),
               (x+ancho*0.42, y-alto*0.72), (x-ancho*0.42, y-alto*0.72)]
    d.polygon(tablero, fill=MADERA_CLARA); _linea(d, tablero+[tablero[0]], g, rnd, color=TINTA)
    for lado in (-1, 1):
        px = x + lado*ancho*0.36
        _linea(d, [(px, y-alto*0.74), (px, y)], int(g*1.8), rnd, color=MADERA_OSCURA)
    for k in range(papeles):
        px = x - ancho*0.22 + ancho*0.34*k
        hoja = [(px-ancho*.13, y-alto*1.02), (px+ancho*.13, y-alto*1.04),
                (px+ancho*.15, y-alto*.88), (px-ancho*.15, y-alto*.86)]
        d.polygon(hoja, fill=(248, 242, 226)); _linea(d, hoja+[hoja[0]], max(2, g//2), rnd, color=TINTA)
        for j in range(2):
            _linea(d, [(px-ancho*.09, y-alto*(.98-.05*j)), (px+ancho*.09, y-alto*(.99-.05*j))],
                   max(2, g//3), rnd, color=(150, 140, 126), temblor=1.6)
    for k in range(jarras):
        px = x + ancho*(0.30 - 0.52*k)
        _jarra(d, px, y-alto*0.92, ancho*0.075, rnd, max(2, g//2))


def _taburete(d, x, y, t, rnd, g):
    d.ellipse([x-t*.30, y-t*.62, x+t*.30, y-t*.44], fill=MADERA_CLARA, outline=TINTA, width=g)
    for px in (-.22, 0, .22):
        _linea(d, [(x+t*px, y-t*.52), (x+t*px*1.5, y)], int(g*1.4), rnd, color=MADERA_OSCURA)


def _cartel(d, x, y, ancho, texto, rnd, g):
    """El cartel colgado. Lo de la imagen que me paso: es lo que le pone
    NOMBRE al sitio sin que la voz tenga que decirlo."""
    lineas = texto.upper().split("\n")[:3]
    alto = ancho*(0.30 + 0.18*len(lineas))
    x0, y0, x1, y1 = x-ancho/2, y, x+ancho/2, y+alto
    _linea(d, [(x-ancho*.42, y), (x-ancho*.42, y-ancho*.22)], g, rnd, color=TINTA)
    _linea(d, [(x+ancho*.42, y), (x+ancho*.42, y-ancho*.22)], g, rnd, color=TINTA)
    _linea(d, [(x-ancho*.55, y-ancho*.22), (x+ancho*.55, y-ancho*.22)], int(g*1.4), rnd, color=TINTA)
    d.rectangle([x0, y0, x1, y1], fill=MADERA_CLARA)
    _linea(d, [(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)], int(g*1.5), rnd, color=TINTA)
    # La letra se MIDE y se encoge hasta que cabe. Sin esto "LA TABERNA DEL
    # PUERTO" se salia del tablero por los dos lados: elegia el tamaño por la
    # altura del cartel y no miraba lo ancho que era el texto.
    px = int(alto/(len(lineas)+0.6))
    for _ in range(14):
        f = _fuente_cartel(px)
        if max(d.textlength(l, font=f) for l in lineas) <= ancho*0.84 or px <= 12:
            break
        px = int(px*0.88)
    salto = alto*0.80/len(lineas)
    arriba = y0 + (alto - salto*len(lineas))/2
    for i, l in enumerate(lineas):
        d.text((x - d.textlength(l, font=f)/2, arriba + i*salto), l, font=f, fill=(74, 52, 34))


def _fuente_cartel(px):
    from PIL import ImageFont
    import glob
    for patron in ("/usr/share/fonts/**/DejaVuSerif-Bold.ttf",
                   "/usr/share/fonts/**/DejaVuSans-Bold.ttf"):
        for f in glob.glob(patron, recursive=True):
            try:
                return ImageFont.truetype(f, max(12, px))
            except Exception:
                continue
    return ImageFont.load_default()


def taberna(spec: dict, w: int, h: int, semilla: int = 0):
    """Una taberna de puerto, montada por capas de profundidad.

      1. la pared del fondo, con su entramado
      2. un hueco al mar y una chimenea encendida - el "otro mundo"
      3. mesas del fondo, mas pequeñas, con su gente
      4. el suelo de tablas
      5. LAS FIGURAS
      6. la mesa de delante con mapas y jarras, POR DELANTE de la gente
      7. una viga cruzando arriba, que es lo que mete al espectador dentro
    """
    rnd = random.Random(semilla)
    vertical = h > w
    suelo = int(h*spec.get("suelo", 0.70))
    img = Image.new("RGB", (w, h), (226, 214, 192))
    d = ImageDraw.Draw(img)
    g = max(4, int(w*0.006))

    _entramado(d, w, 0, suelo, rnd, g, postes=3 if vertical else 5)
    _ventana_al_mar(d, w*0.26, h*(0.30 if vertical else 0.32),
                    w*0.34, h*(0.16 if vertical else 0.26), rnd, g)
    _chimenea(d, w*0.78, suelo, w*0.30, h*(0.30 if vertical else 0.46), rnd, g)
    _tablas(d, w, suelo, h, rnd, g, n=7 if vertical else 11)

    # Gente del fondo, pequeña: llena el sitio sin robar el plano.
    for x, alto in ((0.42, 0.10), (0.56, 0.095)):
        figura(d, w*x, suelo + h*0.02, h*alto, rnd, "en_mesa", "neutro")
    _mesa_con_cosas(d, w*0.49, suelo + h*0.03, w*0.24, rnd, max(2, g//2),
                    papeles=1, jarras=1, alto=h*0.035)

    velas = []
    for f in spec.get("figuras", []):
        alto_f = h*f.get("alto", 0.30)
        figura(d, w*f["x"], suelo + h*0.27 + alto_f*_RESPIRACION*f.get("_bocanada", 0.0),
               alto_f, rnd, f.get("pose", "en_mesa"), f.get("gesto", "neutro"),
               f.get("gorro"), f.get("espejo", False), f.get("pose_mezclada"),
               rasgos=REPARTO.get(f.get("quien") or ""))

    _mesa_con_cosas(d, w*0.46, suelo + h*0.34, w*0.92, rnd, g, papeles=2, jarras=2,
                    alto=h*0.075)
    _taburete(d, w*0.90, suelo + h*0.36, h*0.09, rnd, g)
    # Un banco cruzando abajo: cierra el plano y quita el metro de suelo
    # vacio que quedaba. Es lo que en la referencia hace la barandilla.
    _banco(d, w*0.42, h*1.02, w*0.62, rnd, g)

    # La viga de delante: el marco que mete al espectador DENTRO del sitio.
    d.rectangle([0, 0, w, h*0.055], fill=MADERA_CLARA)
    _linea(d, [(0, h*0.055), (w, h*0.055)], int(g*1.6), rnd, color=MADERA_OSCURA)
    for px in (0.12, 0.88):
        d.rectangle([w*px-w*0.022, 0, w*px+w*0.022, h*0.30], fill=MADERA_CLARA)
        _linea(d, [(w*px-w*0.022, 0), (w*px-w*0.022, h*0.30)], g, rnd, color=MADERA_OSCURA)
        _linea(d, [(w*px+w*0.022, 0), (w*px+w*0.022, h*0.30)], g, rnd, color=MADERA_OSCURA)

    # La pared de la izquierda salia pelada. Dos cosas colgadas y ya hay algo
    # que mirar mientras habla la voz.
    # Colgadas de la pared, y solo lo que se cuelga de verdad: el libro
    # flotaba a media pared como un fantasma.
    for px, py, que, tam in ((0.13, 0.52, "espada", 0.10), (0.15, 0.72, "olla", 0.05)):
        COSAS[que](d, w*px, h*py, h*tam, rnd, max(2, g//2), TINTA)
    _linea(d, [(w*0.09, h*0.73), (w*0.21, h*0.73)], int(g*1.4), rnd, color=MADERA_OSCURA)
    _vela(d, w*0.36, suelo - h*0.01, h*0.035, rnd, max(2, g//2))

    letrero = spec.get("cartel")
    if letrero:
        _cartel(d, w*0.50, h*0.10, w*0.42, str(letrero)[:40], rnd, g)

    img = _resplandor(img, (w*0.78, suelo - h*0.10), h*0.16)
    return img


# ---- EL SUELO CON COSAS ------------------------------------------------------
# Del video que me paso: dos monigotes en una savana, y el suelo NO es una
# banda verde - tiene matas de hierba, piedras sueltas y arboles de distintos
# tamaños repartidos. Eso es lo que hace que el plano aguante veinte segundos
# de voz encima. Y es barato: son bucles.
#
# Va sembrado con semilla fija por escena, asi que los matojos no bailan de un
# fotograma a otro - que es justo lo que pasaria sembrandolos al azar en cada
# uno, y marearia.

def _mata(d, x, y, t, rnd, g, color=(72, 132, 52)):
    for k in (-1, 0, 1):
        _linea(d, [(x + k*t*0.18, y),
                   (x + k*t*0.34, y - t*rnd.uniform(0.55, 1.0))], g, rnd,
               color=color, temblor=1.6)


def _piedra(d, x, y, t, rnd, g, color=(150, 142, 132)):
    pts = []
    for i in range(9):
        a = i/8*math.pi
        pts.append((x - math.cos(a)*t*rnd.uniform(.8, 1.1),
                    y - math.sin(a)*t*rnd.uniform(.45, .7)))
    pts += [(x + t, y), (x - t, y)]
    d.polygon(pts, fill=color)
    _linea(d, pts + [pts[0]], max(2, g//2), rnd, color=TINTA, temblor=1.2)


_SIEMBRA = {
    "campo": {"matas": 34, "piedras": 9, "arboles": 3, "verde": (72, 132, 52)},
    "calle": {"matas": 5,  "piedras": 16, "arboles": 1, "verde": (120, 112, 96)},
    "noche": {"matas": 20, "piedras": 7, "arboles": 2, "verde": (44, 62, 44)},
    "liso":  {"matas": 0,  "piedras": 0, "arboles": 0, "verde": (72, 132, 52)},
    "salon": {"matas": 0,  "piedras": 0, "arboles": 0, "verde": (72, 132, 52)},
}


def _sembrar(d, w, h, suelo, fondo, rnd, g):
    """Lo que llena el suelo. Las cosas de detras, mas pequeñas y mas palidas:
    es lo unico que hace falta para que haya profundidad."""
    plan = _SIEMBRA.get(fondo)
    if not plan:
        return
    # Un par de nubes: el cielo se quedaba como un rectangulo azul enorme y
    # vacio, que es la mitad de arriba del plano en vertical.
    if plan["arboles"] and fondo != "noche":
        for _ in range(2):
            _nube(d, w*rnd.uniform(0.08, 0.92), suelo*rnd.uniform(0.18, 0.55),
                  h*rnd.uniform(0.035, 0.055), rnd, max(3, g//2))
    hondo = h - suelo
    # Los arboles van EN EL HORIZONTE, no repartidos por el prado: sembrados
    # hacia delante salian entre las piernas de la gente, y ademas pequeños,
    # con lo que parecian arbustos en un palo. En la referencia estan todos en
    # la linea del fondo y son grandes.
    for _ in range(plan["arboles"]):
        arbol(d, w*rnd.uniform(0.02, 0.98), suelo + hondo*rnd.uniform(0.0, 0.05),
              h*rnd.uniform(0.13, 0.19), rnd)
    for _ in range(plan["matas"]):
        f = rnd.uniform(0, 1)
        _mata(d, w*rnd.uniform(0.01, 0.99), suelo + hondo*f,
              h*(0.016 + 0.038*f), rnd, max(3, int(g*(0.5 + 0.7*f))),
              color=plan["verde"])
    for _ in range(plan["piedras"]):
        f = rnd.uniform(0.1, 1)
        _piedra(d, w*rnd.uniform(0.03, 0.97), suelo + hondo*f,
                h*(0.006 + 0.022*f), rnd, max(2, int(g*(0.4 + 0.6*f))))


# ---- MOTOR DE DECORADOS ------------------------------------------------------
# "¿Has hecho mas escenarios o solo esa? Tiene que tener muchas mas". Tiene
# razon, y el problema no era la idea: era que monte el monasterio y la
# taberna como funciones a medida, asi que cada sitio nuevo costaba media hora
# y siempre habria dos.
#
# Aqui un decorado es una RECETA: paredes, suelo, lo que hay al fondo, los
# muebles y lo que cuelga. Añadir un sitio son tres lineas, y todos heredan
# gratis lo que ya funciona - el orden por capas, el resplandor de las velas,
# la gente delante y los muebles de primer termino por encima.

def _pared(d, w, y0, y1, clase, rnd, g):
    if clase == "entramado":
        _entramado(d, w, y0, y1, rnd, g)
    elif clase == "piedra":
        _pared_piedra(d, w, y1, y1, rnd)
        d.rectangle([0, y0, w, y1], fill=PIEDRA)
        rr = random.Random(7)
        for _ in range(30):
            bw = rr.uniform(w*.05, w*.13); bh = bw*rr.uniform(.32, .52)
            bx = rr.uniform(0, w-bw); by = rr.uniform(y0, y1-bh)
            _linea(d, [(bx,by),(bx+bw,by),(bx+bw,by+bh),(bx,by+bh),(bx,by)], max(2, g//2),
                   rnd, color=(104, 98, 90), temblor=1.6)
    elif clase == "encalada":
        d.rectangle([0, y0, w, y1], fill=(238, 232, 220))
        for _ in range(7):                      # grietas
            x = rnd.uniform(0, w); y = rnd.uniform(y0, y1)
            _linea(d, [(x, y), (x+rnd.uniform(-w*.04, w*.04), y+rnd.uniform(0, (y1-y0)*.2))],
                   max(2, g//3), rnd, color=(206, 198, 184), temblor=3.0)
    elif clase == "ladrillo":
        d.rectangle([0, y0, w, y1], fill=LADRILLO)
        fila = (y1-y0)/12
        for f in range(12):
            yy = y0 + f*fila
            _linea(d, [(0, yy), (w, yy)], max(2, g//2), rnd, color=(126, 62, 48), temblor=1.0)
            px = (w/8) if f % 2 else 0
            while px < w:
                _linea(d, [(px, yy), (px, yy+fila)], max(2, g//2), rnd,
                       color=(126, 62, 48), temblor=1.0)
                px += w/4
    elif clase == "azulejos":
        # El palacio del sultan: azulejos blancos con su dibujo azul y una
        # cenefa turquesa. Es lo que dice "Oriente" sin escribirlo.
        d.rectangle([0, y0, w, y1], fill=(236, 232, 220))
        lado = (y1 - y0)/7
        rr = random.Random(5)
        fila = 0
        yy = y0 + (y1 - y0)*0.42
        while yy < y1:
            xx = (lado/2 if fila % 2 else 0)
            while xx < w:
                cx, cy = xx + lado/2, yy + lado/2
                r = lado*0.32
                d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=(38, 96, 160))
                d.ellipse([cx - r*.3, cy - r*.3, cx + r*.3, cy + r*.3], fill=(236, 232, 220))
                xx += lado
            yy += lado
            fila += 1
        cenefa = y0 + (y1 - y0)*0.38
        d.rectangle([0, cenefa, w, cenefa + (y1 - y0)*0.04], fill=(40, 150, 150))
        _linea(d, [(0, cenefa), (w, cenefa)], max(2, g//2), rnd, temblor=0.8)
    elif clase == "papel":
        # El papel pintado de un piso de toda la vida: rayas y florecitas, y
        # un zocalo de madera abajo. Es lo que dice "casa de alquiler de
        # siempre" sin que haga falta un cartel.
        d.rectangle([0, y0, w, y1], fill=(226, 206, 160))
        franja = w/9
        for k in range(10):
            d.rectangle([k*franja, y0, k*franja + franja*0.42, y1], fill=(214, 190, 140))
        rr = random.Random(11)
        for k in range(10):
            for f in range(9):
                fx = k*franja + franja*0.71 + rr.uniform(-2, 2)
                fy = y0 + (f + 0.5 + 0.5*(k % 2))*(y1 - y0)/9
                r = w*0.007
                d.ellipse([fx-r, fy-r, fx+r, fy+r], fill=(176, 92, 78))
        zocalo = y1 - (y1 - y0)*0.10
        d.rectangle([0, zocalo, w, y1], fill=MADERA)
        _linea(d, [(0, zocalo), (w, zocalo)], g, rnd, temblor=1.0)
    elif clase == "blanca":                      # el folio en blanco del canal en ingles
        d.rectangle([0, y0, w, y1], fill=(252, 252, 250))
    else:                                        # "cielo"
        d.rectangle([0, y0, w, y1], fill=(146, 198, 232))


def _piso(d, w, h, suelo, clase, rnd, g):
    if clase == "tablas":
        _tablas(d, w, suelo, h, rnd, g)
    elif clase == "adoquines":
        _adoquines(d, 0, suelo, w, h, rnd, g)
    elif clase == "losas":
        d.rectangle([0, suelo, w, h], fill=(176, 170, 160))
        paso = (h-suelo)/5
        for k in range(6):
            yy = suelo + k*paso
            _linea(d, [(0, yy), (w, yy)], max(2, g//2), rnd, color=(140, 134, 124), temblor=1.4)
        for k in range(5):
            _linea(d, [(w*k/4, suelo), (w*(k/4-0.25)+w*0.5, h)], max(2, g//2), rnd,
                   color=(140, 134, 124), temblor=1.4)
    elif clase == "tierra":
        d.rectangle([0, suelo, w, h], fill=(166, 138, 104))
        for _ in range(14):
            _piedra(d, rnd.uniform(0, w), rnd.uniform(suelo, h), h*rnd.uniform(.006, .016),
                    rnd, max(2, g//2), color=(150, 126, 96))
    elif clase == "hierba":
        d.rectangle([0, suelo, w, h], fill=(122, 193, 96))
    elif clase == "nada":
        d.rectangle([0, suelo, w, h], fill=(252, 252, 250))
    elif clase == "linea":
        # Folio en blanco con una raya ondulada de suelo, a mano, justo donde
        # pisan (montar los pone un 6% por debajo de la linea del suelo).
        d.rectangle([0, suelo, w, h], fill=(252, 252, 250))
        y = suelo + h*0.06
        pts = [(x, y + h*0.006*math.sin(x/(w*0.05))) for x in range(int(w*0.08), int(w*0.92), 16)]
        _linea(d, pts, max(4, g), rnd, color=TINTA, temblor=1.2)
    else:
        d.rectangle([0, suelo, w, h], fill=MADERA)


def _puerta_arco(d, x, y, ancho, alto, rnd, g, fuera=(146, 198, 232)):
    """Un vano con luz detras: barato y abre el plano."""
    x0, y0, x1 = x-ancho/2, y-alto, x+ancho/2
    d.rounded_rectangle([x0, y0, x1, y], radius=int(ancho*0.48), fill=fuera)
    d.rectangle([x0, y-alto*0.4, x1, y], fill=fuera)
    _linea(d, [(x0, y), (x0, y0+ancho*0.3)], int(g*1.4), rnd, color=TINTA)
    _linea(d, [(x1, y), (x1, y0+ancho*0.3)], int(g*1.4), rnd, color=TINTA)
    d.arc([x0, y0, x1, y0+ancho], 180, 360, fill=TINTA, width=int(g*1.4))


def _estante(d, x, y, ancho, rnd, g, ollas=2):
    _linea(d, [(x-ancho/2, y), (x+ancho/2, y)], int(g*1.8), rnd, color=MADERA_OSCURA)
    for k in range(ollas):
        px = x - ancho*0.28 + ancho*0.56*k/max(1, ollas-1) if ollas > 1 else x
        _olla(d, px, y, ancho*0.22, rnd, max(2, g//2))


def _estandarte(d, x, y, ancho, alto, rnd, g, color=(170, 44, 44), franja=None, aspa=None):
    paño = [(x-ancho/2, y), (x+ancho/2, y), (x+ancho/2, y+alto),
            (x, y+alto*0.86), (x-ancho/2, y+alto)]
    d.polygon(paño, fill=color); _linea(d, paño+[paño[0]], g, rnd, color=TINTA)
    if franja:
        d.rectangle([x-ancho/2, y+alto*0.34, x+ancho/2, y+alto*0.54], fill=franja)
    if aspa:
        for a, b in (((-.40, .08), (.40, .78)), ((.40, .08), (-.40, .78))):
            _linea(d, [(x + ancho*a[0], y + alto*a[1]), (x + ancho*b[0], y + alto*b[1])],
                   int(g*1.6), rnd, color=aspa, temblor=2.0)
    _linea(d, [(x-ancho*0.62, y), (x+ancho*0.62, y)], int(g*1.4), rnd, color=MADERA_OSCURA)


def _trono(d, x, y, ancho, rnd, g):
    alto = ancho*1.5
    respaldo = [(x-ancho/2, y), (x-ancho/2, y-alto), (x-ancho*0.28, y-alto*1.14),
                (x, y-alto*1.0), (x+ancho*0.28, y-alto*1.14), (x+ancho/2, y-alto),
                (x+ancho/2, y)]
    d.polygon(respaldo, fill=MADERA_CLARA); _linea(d, respaldo+[respaldo[0]], g, rnd, color=TINTA)
    d.rectangle([x-ancho*0.6, y-alto*0.36, x+ancho*0.6, y-alto*0.24], fill=(170, 44, 44))
    _linea(d, [(x-ancho*0.6, y-alto*0.36), (x+ancho*0.6, y-alto*0.36)], g, rnd, color=TINTA)


def _mastil(d, x, suelo, h, rnd, g):
    _linea(d, [(x, suelo), (x, h*0.03)], int(g*2.4), rnd, color=MADERA_OSCURA)
    _linea(d, [(x-h*0.14, h*0.16), (x+h*0.14, h*0.16)], int(g*1.6), rnd, color=MADERA_OSCURA)
    vela = [(x-h*0.13, h*0.17), (x+h*0.13, h*0.17), (x+h*0.09, h*0.40), (x-h*0.09, h*0.40)]
    d.polygon(vela, fill=(248, 244, 232)); _linea(d, vela+[vela[0]], g, rnd, color=TINTA)
    for lado in (-1, 1):
        _linea(d, [(x, h*0.05), (x+lado*h*0.22, suelo)], max(2, g//2), rnd, color=TINTA)


MURALLA = (184, 172, 150)
LONA = (232, 222, 196)


def _almena(d, x0, x1, arriba, alto, rnd, g):
    d.rectangle([x0, arriba - alto, x1, arriba], fill=MURALLA)
    _linea(d, [(x0, arriba), (x0, arriba - alto), (x1, arriba - alto), (x1, arriba)],
           max(2, g//2), rnd, color=TINTA)


def _muralla(d, w, h, suelo, rnd, g):
    """Una ciudad sitiada vista desde fuera: el lienzo de piedra de lado a
    lado, dos torres y la puerta cerrada en medio. Sirve para cualquier
    asedio - Olivenza y Elvas, pero tambien Numancia, Zaragoza, Gerona o
    Granada -, que es de lo que mas hay en historia de España."""
    arriba = suelo - h*0.17
    d.rectangle([0, arriba, w, suelo], fill=MURALLA)
    _linea(d, [(0, arriba), (w, arriba)], g, rnd, color=TINTA)
    diente = w*0.05
    px = 0.0
    while px < w:
        _almena(d, px, px + diente, arriba, diente*0.8, rnd, g)
        px += diente*2
    piedras = random.Random(11)
    for _ in range(18):
        bx = piedras.uniform(0, w); by = piedras.uniform(arriba + h*0.01, suelo - h*0.02)
        _linea(d, [(bx, by), (bx + w*0.05, by)], max(2, g//3), rnd,
               color=(140, 130, 112), temblor=1.4)
    for tx in (0.16, 0.84):
        x0, x1, top = w*tx - w*0.08, w*tx + w*0.08, suelo - h*0.27
        d.rectangle([x0, top, x1, suelo], fill=MURALLA)
        _linea(d, [(x0, suelo), (x0, top), (x1, top), (x1, suelo)], g, rnd, color=TINTA)
        for k in range(3):
            cx = x0 + (x1 - x0)*k*0.4
            _almena(d, cx, cx + (x1 - x0)*0.2, top, diente*0.8, rnd, g)
        d.rectangle([w*tx - w*0.008, top + h*0.03, w*tx + w*0.008, top + h*0.07],
                    fill=(60, 50, 44))
    _puerta_arco(d, w*0.5, suelo, w*0.16, h*0.13, rnd, g, fuera=(78, 58, 42))


def _tiendas(d, w, h, suelo, rnd, g):
    """Un campamento: tiendas de lona en fila, la del medio con banderin.
    Toda guerra tiene un rato de esperar en el campamento, y hasta ahora eso
    solo se podia contar en un campo vacio."""
    for k, (tx, tam) in enumerate(((0.16, 0.20), (0.50, 0.26), (0.84, 0.20))):
        T, X, base = w*tam, w*tx, suelo + h*0.005
        alto = T*0.78
        lona = [(X - T/2, base), (X, base - alto), (X + T/2, base)]
        d.polygon(lona, fill=LONA)
        _linea(d, lona + [lona[0]], g, rnd, color=TINTA)
        puerta = [(X - T*0.12, base), (X, base - alto*0.55), (X + T*0.12, base)]
        d.polygon(puerta, fill=(92, 74, 56))
        _linea(d, puerta, max(2, g//2), rnd, color=TINTA)
        if k == 1:
            punta = base - alto
            _linea(d, [(X, punta), (X, punta - h*0.06)], g, rnd, color=MADERA_OSCURA)
            pen = [(X, punta - h*0.06), (X + T*0.22, punta - h*0.045), (X, punta - h*0.03)]
            d.polygon(pen, fill=ROJO_ESPAÑA)
            _linea(d, pen + [pen[0]], max(2, g//2), rnd, color=TINTA)


def _naranjos(d, w, h, suelo, rnd, g):
    """El naranjal: una fila de naranjos en el horizonte, con la gente
    delante - el sitio donde se cortaron las naranjas de la guerra."""
    for x in (0.10, 0.36, 0.64, 0.90):
        _naranjo(d, w*x, suelo + h*0.004, h*rnd.uniform(0.10, 0.12), rnd, g)


# Cada sitio es una receta. Añadir uno son tres lineas y hereda gratis el
# orden por capas, el resplandor de las velas y la gente delante.
#
#   pared / piso  : de que estan hechos
#   fondo         : lo que hay pegado a la pared (chimenea, ventana, puerta...)
#   muebles       : lo que hay en el suelo, DETRAS de la gente
#   delante       : lo que tapa a la gente por abajo (la mesa, una barandilla)
#   cuelga        : lo colgado de la pared
#   velas         : donde hay lumbre, para el resplandor
_DECORADOS = {
    "taberna":      {"pared": "entramado", "piso": "tablas",
                     "fondo": [("ventana_mar", .26, .34, .34), ("chimenea", .78, 1.0, .30)],
                     "muebles": [("mesa_fondo", .49, .03, .24), ("taburete", .90, .10, .09)],
                     "delante": [("mesa", .46, .34, .92)],
                     "cuelga": [("espada", .13, .40, .10)], "velas": [(.78, -.10)]},
    "monasterio":   {"pared": "piedra", "piso": "losas",
                     "fondo": [("ventana_arco", .50, .36, .20)],
                     "muebles": [("estante", .18, .06, .22)],
                     "delante": [("mesa", .50, .30, .94)],
                     "cuelga": [("cruz", .84, .38, .09)], "velas": [(.12, -.30), (.88, -.30)]},
    "salon_trono":  {"pared": "piedra", "piso": "losas",
                     "fondo": [("trono", .50, 1.0, .22), ("estandarte", .16, .22, .13),
                               ("estandarte", .84, .22, .13)],
                     "muebles": [], "delante": [],
                     "cuelga": [("espada", .26, .34, .11), ("espada", .74, .34, .11)],
                     "velas": [(.08, -.34), (.92, -.34)]},
    "cocina":       {"pared": "encalada", "piso": "losas",
                     "fondo": [("chimenea", .74, 1.0, .34), ("ventana_arco", .22, .34, .16)],
                     "muebles": [("estante", .30, .30, .30)],
                     "delante": [("mesa", .44, .32, .90)],
                     "cuelga": [("olla", .50, .30, .06)], "velas": [(.74, -.12)]},
    "iglesia":      {"pared": "piedra", "piso": "losas",
                     "fondo": [("ventana_arco", .28, .30, .17), ("ventana_arco", .72, .30, .17),
                               ("cruz_grande", .50, .58, .22)],
                     "muebles": [("banco_fondo", .50, .30, .56)],
                     "delante": [("banco_fondo", .50, .46, .96)],
                     "cuelga": [], "velas": [(.20, -.26), (.80, -.26), (.50, -.10)]},
    "calle":        {"pared": "cielo", "piso": "adoquines",
                     "fondo": [("casas", .5, 1.0, 1.0)],
                     "muebles": [], "delante": [], "cuelga": [], "velas": []},
    "mercado":      {"pared": "cielo", "piso": "adoquines",
                     "fondo": [("casas", .5, 1.0, 1.0), ("puesto", .20, 1.0, .28),
                               ("puesto", .80, 1.0, .28)],
                     "muebles": [("olla_suelo", .50, .06, .07)],
                     "delante": [("mesa", .50, .34, .84)], "cuelga": [], "velas": []},
    "cubierta":     {"pared": "cielo_mar", "piso": "tablas",
                     "fondo": [("mastil", .50, 1.0, 1.0)],
                     "muebles": [("olla_suelo", .84, .08, .06)],
                     "delante": [("barandilla", .5, .30, 1.0)], "cuelga": [], "velas": []},
    "batalla_naval": {"pared": "cielo_mar", "piso": "tablas",
                     "fondo": [("batalla_naval", .5, 1.0, 1.0), ("mastil", .50, 1.0, 1.0)],
                     "muebles": [],
                     "delante": [("barandilla", .5, .30, 1.0)], "cuelga": [], "velas": []},
    "palacio_otomano": {"pared": "azulejos", "piso": "losas",
                     "fondo": [("arcos_otomanos", .5, 1.0, 1.0), ("estandarte_otomano", .10, .20, .12),
                               ("estandarte_otomano", .90, .20, .12)],
                     "muebles": [("divan", .50, .0, .34)], "delante": [], "cuelga": [], "velas": []},
    "constantinopla": {"pared": "cielo_mar", "piso": "tablas",
                     "fondo": [("mezquitas", .5, 1.0, 1.0)], "muebles": [], "delante": [],
                     "cuelga": [("galera", .20, .70, .10), ("galera", .82, .70, .08)], "velas": []},
    "venecia":      {"pared": "cielo", "piso": "adoquines",
                     "fondo": [("palacio_ducal", .5, 1.0, 1.0)], "muebles": [], "delante": [],
                     "cuelga": [], "velas": []},
    "vaticano":     {"pared": "cielo", "piso": "adoquines",
                     "fondo": [("san_pedro", .5, 1.0, 1.0)], "muebles": [], "delante": [],
                     "cuelga": [], "velas": []},
    "hospital":     {"pared": "encalada", "piso": "losas",
                     "fondo": [("ventana_arco", .50, .26, .14), ("cruz_grande", .18, .40, .10)],
                     "muebles": [("camastros", .5, .0, 1.0)], "delante": [], "cuelga": [],
                     "velas": [(.82, -.30)]},
    "costa":        {"pared": "cielo_mar", "piso": "tierra",
                     "fondo": [("costa", .5, 1.0, 1.0)], "muebles": [], "delante": [],
                     "cuelga": [("galera", .40, .66, .07), ("galera", .62, .66, .06)], "velas": []},
    "mina":         {"pared": "roca", "piso": "tierra",
                     "fondo": [("puntales", .5, 1.0, 1.0)],
                     "muebles": [], "delante": [], "cuelga": [], "velas": [(.30, -.30), (.70, -.24)]},
    # Los cuatro de la guerra de las naranjas, pensados para servir despues:
    # el ministro que declara la guerra, la ciudad sitiada, el campamento
    # donde se espera y el campo donde pasa lo que sea que pase.
    # Sin mesa de primer termino: pegada al borde de abajo quedaba lejos de
    # las manos, y el que firmaba el tratado firmaba en el aire. Sin ella, el
    # que firma lleva su propia mesa delante (ver tiene_mesa en montar()).
    "despacho":     {"pared": "encalada", "piso": "tablas",
                     "fondo": [("ventana_arco", .80, .34, .15)],
                     "muebles": [], "delante": [],
                     "cuelga": [("mapa", .38, .40, .15)], "velas": [(.12, -.30)]},
    "murallas":     {"pared": "cielo", "piso": "tierra",
                     "fondo": [("muralla", .5, 1.0, 1.0)],
                     "muebles": [], "delante": [], "cuelga": [], "velas": []},
    "campamento":   {"pared": "cielo", "piso": "hierba",
                     "fondo": [("tiendas", .5, 1.0, 1.0)],
                     "muebles": [], "delante": [], "cuelga": [], "velas": []},
    "naranjal":     {"pared": "cielo", "piso": "hierba",
                     "fondo": [("naranjos", .5, 1.0, 1.0)],
                     "muebles": [], "delante": [], "cuelga": [], "velas": []},
    # El dormitorio de un rey, para Felipe V y Farinelli y para cualquier
    # historia de alguien que no sale de la cama. La cama no esta aqui: la
    # pone la postura "en_cama", pegada a quien la usa.
    "dormitorio":   {"pared": "encalada", "piso": "tablas",
                     "fondo": [("ventana_arco", .70, .36, .15), ("estandarte", .34, .24, .11),
                               ("cortinas", .5, 1.0, 1.0)],
                     "muebles": [], "delante": [], "cuelga": [], "velas": [(.52, -.30)]},
    # Hechos sin que ningun guion los pidiera todavia, porque van a salir: el
    # puerto de donde salen las flotas y la Armada, la mazmorra de la
    # Inquisicion y de los presos, y la selva de las Americas.
    "puerto":       {"pared": "cielo_mar", "piso": "tablas",
                     "fondo": [], "muebles": [], "delante": [],
                     "cuelga": [("barco", .22, .665, .14), ("barco", .78, .665, .10),
                                ("barril", .06, .70, .07), ("barril", .94, .70, .06)],
                     "velas": []},
    "mazmorra":     {"pared": "piedra", "piso": "tierra",
                     "fondo": [("reja", .50, .26, .16)], "muebles": [], "delante": [],
                     "cuelga": [("antorcha", .12, .46, .10), ("antorcha", .88, .46, .10),
                                ("cadenas", .30, .44, .12), ("cadenas", .70, .44, .12)],
                     "velas": []},
    "selva":        {"pared": "cielo", "piso": "hierba",
                     "fondo": [("selva", .5, 1.0, 1.0)],
                     "muebles": [], "delante": [], "cuelga": [], "velas": []},
    # La plaza tomada: las casas, las tiendas de campaña ya plantadas y las
    # pancartas. Las tiendas iban como "cosas" y en el #107 el guion no las
    # pidio: si el sitio ES una acampada, las tiendas son del sitio.
    "acampada":     {"pared": "cielo", "piso": "adoquines",
                     "fondo": [("casas", .5, 1.0, 1.0)],
                     "muebles": [("acampada", .5, 0, 1.0)], "delante": [], "cuelga": [],
                     "velas": []},
    # El piso de alquiler de toda la vida: papel pintado, visillos, el cuadro,
    # el reloj y el aparador con la radio. Para la renta antigua, y para
    # cualquier historia que pase en una casa normal y no en un palacio.
    "piso":         {"pared": "papel", "piso": "tablas",
                     "fondo": [("ventana_piso", .70, .30, .26), ("cuadro", .30, .25, .15),
                               ("reloj", .11, .29, .07)],
                     "muebles": [("aparador", .88, .02, .20)], "delante": [],
                     "cuelga": [], "velas": []},
}
DECORADOS_VALIDOS = tuple(_DECORADOS)

# Lo que ve el guion de cada sitio. Va aqui, al lado de las recetas, y no
# escrito a mano en el prompt: la lista del prompt estaba tecleada y cada
# sitio nuevo que se dibujara aqui habria sido invisible para el guion - el
# mismo fallo que la taberna que se dibujaba y no se usaba. Al arrancar se
# comprueba que no falte ni sobre ninguno.
DECORADOS_EXPLICADOS = {
    "taberna":     "mesas, chimenea, ventana al puerto",
    "monasterio":  "piedra, ventana de arco, mesa larga",
    "salon_trono": "trono, estandartes CON LA BANDERA DE ESPAÑA, espadas en la pared: la corte de los reyes de España. Para el sultan es palacio_otomano; para el Papa, vaticano o iglesia",
    "venecia":     "VENECIA: el Palacio Ducal rosa con sus arcos y el campanile de San Marcos. El dux, el Senado veneciano, la Republica de Venecia",
    "vaticano":    "ROMA, EL VATICANO: la fachada de San Pedro con su cupula. El Papa, la Santa Sede, los cardenales",
    "hospital":    "UN HOSPITAL ANTIGUO: sala encalada con camastros en fila y una cruz. Heridos, enfermos, epidemias (Cervantes herido en Mesina)",
    "costa":       "UN PUEBLO DE LA COSTA con su torre vigia y galeras en el mar: ataques de corsarios y piratas berberiscos, desembarcos",
    "cocina":      "fogon, estantes con ollas, mesa: la casa de la gente corriente de cualquier siglo antiguo",
    "iglesia":     "arcos, cruz, bancos",
    "calle":       "casas, adoquines",
    "mercado":     "puestos con toldo, casas, adoquines",
    "cubierta":    "cubierta de barco, mastil, el mar detras",
    "batalla_naval": "LA CUBIERTA DE UNA GALERA EN PLENA BATALLA: galeras en el mar con humo de cañonazos, fogonazos y una ardiendo. Lepanto, la Armada Invencible, Trafalgar, cualquier combate en el mar",
    "palacio_otomano": "EL PALACIO DEL SULTAN: azulejos azules, arcos apuntados, divan rojo con cojines y estandartes con la media luna. Selim segundo, Soliman, la corte otomana, cualquier corte de Oriente o de Al-Andalus por dentro",
    "constantinopla": "CONSTANTINOPLA desde el puerto: cupulas y minaretes al otro lado del agua y galeras. La capital otomana, el Bosforo; vale tambien para cualquier ciudad de Oriente vista desde el mar",
    "mina":        "puntales de madera, tierra, oscuridad",
    "despacho":    "el despacho de un ministro: mesa con papeles, mapa en la pared",
    "murallas":    "una ciudad sitiada vista desde fuera: muralla, torres, puerta",
    "campamento":  "el campamento de un ejercito: tiendas de lona, banderin",
    "naranjal":    "campo de naranjos con las naranjas colgando",
    "dormitorio":  "el dormitorio de un rey: cortinones rojos, tapiz, ventana de noche. La cama la pone la postura en_cama",
    "puerto":      "el muelle con barcos en el mar: flotas, la Armada, Colon zarpando, los que llegan",
    "mazmorra":    "carcel de piedra con reja, cadenas y antorchas: presos, Inquisicion, cautivos",
    "selva":       "la selva de las Americas, con palmeras: Colon, Cortes, Pizarro, expediciones",
    "acampada":    "una plaza de ciudad tomada por una acampada: tiendas de campaña de colores y pancartas. Protestas, la Puerta del Sol, el 15-M, sentadas",
    "piso":        "un piso de alquiler normal del siglo XX (tiene RADIO: NUNCA para historias de antes de 1900; una casa antigua es la cocina): papel pintado, visillos, cuadro, reloj de pared. Caseros, inquilinos, familias de ahora",
}
_sin_explicar = set(DECORADOS_VALIDOS) ^ set(DECORADOS_EXPLICADOS)
if _sin_explicar:
    raise RuntimeError(f"Decorados sin explicar o explicados sin receta: {sorted(_sin_explicar)}")
# El folio en blanco del canal en ingles. Despues de la comprobacion y de
# DECORADOS_VALIDOS: es solo de ese canal y el guion en español no lo ofrece.
_DECORADOS["blanco"] = {"pared": "blanca", "piso": "linea", "fondo": [], "muebles": [],
                        "delante": [], "cuelga": [], "velas": []}
_DECORADOS["folio"] = {"pared": "blanca", "piso": "nada", "fondo": [], "muebles": [],
                       "delante": [], "cuelga": [], "velas": []}


def _cortinas(d, w, h, suelo, rnd, g):
    """Cortinones de palacio: la galeria de arriba con sus ondas y un cortinon
    recogido a cada lado. Es lo que hace que el dormitorio sea el de un rey y
    no el despacho con otra luz."""
    rojo, oscuro = (150, 28, 40), (112, 20, 30)
    arriba, galeria = h*0.10, h*0.155
    for lado in (-1, 1):
        borde = 0 if lado < 0 else w
        dentro = borde - lado*w*0.15
        recogido = suelo - (suelo - arriba)*0.42
        pts = [(borde, arriba), (dentro, arriba), (borde - lado*w*0.07, recogido),
               (borde - lado*w*0.10, suelo), (borde, suelo)]
        d.polygon(pts, fill=rojo)
        _linea(d, pts[1:4], g, rnd, temblor=1.2)
        for k in (0.35, 0.65):                  # los pliegues
            _linea(d, [(borde - lado*w*0.15*k, arriba + h*0.06),
                       (borde - lado*w*0.07*k, recogido),
                       (borde - lado*w*0.10*k, suelo)], max(2, g//2), rnd,
                   color=oscuro, temblor=1)
        d.ellipse([borde - lado*w*0.075 - w*0.02, recogido - h*0.012,
                   borde - lado*w*0.075 + w*0.02, recogido + h*0.012], fill=ORO_ESPAÑA,
                  outline=TINTA, width=max(2, g//2))
    d.rectangle([0, arriba - h*0.02, w, galeria], fill=rojo)
    ondas = 7
    for k in range(ondas):
        x0, x1 = w*k/ondas, w*(k + 1)/ondas
        d.chord([x0, galeria - h*0.03, x1, galeria + h*0.03], 0, 180, fill=rojo)
    d.line([(0, galeria - h*0.035), (w, galeria - h*0.035)], fill=ORO_ESPAÑA, width=max(3, g))
    _linea(d, [(0, arriba - h*0.02), (w, arriba - h*0.02)], g, rnd, temblor=1)


def _reja(d, cx, cy, ancho, alto, rnd, g):
    """El ventanuco alto con barrotes de la mazmorra, con un poco de cielo."""
    d.rectangle([cx - ancho/2, cy - alto/2, cx + ancho/2, cy + alto/2], fill=(120, 160, 200),
                outline=TINTA, width=g)
    for k in range(1, 5):
        bx = cx - ancho/2 + ancho*k/5
        d.line([(bx, cy - alto/2), (bx, cy + alto/2)], fill=(60, 60, 64), width=max(3, g))


def _selva(d, w, h, suelo, rnd, g):
    """La selva de las Americas: palmeras y matas grandes. Colon, Cortes,
    Pizarro, las expediciones."""
    verde, oscuro, tronco = (58, 138, 64), (34, 100, 48), (132, 94, 58)
    for k, (px, alto) in enumerate(((.10, .34), (.34, .28), (.62, .36), (.88, .30))):
        bx, top = w*px, suelo - h*alto
        pts = [(bx + w*0.02*math.sin(i/6*math.pi)*(1 if k % 2 else -1), suelo - (suelo - top)*i/6)
               for i in range(7)]
        _linea(d, pts, int(g*2.2), rnd, color=tronco, temblor=1)
        cx, cy = pts[-1]
        for a in range(7):
            ang = math.pi*(1.05 + a*0.15)
            fx, fy = cx + math.cos(ang)*w*0.13, cy + math.sin(ang)*h*0.03 + h*0.04*abs(math.cos(ang))
            d.polygon([(cx, cy), (fx, fy), (cx + (fx - cx)*0.6, fy + h*0.015)], fill=verde, outline=oscuro)
            fx2 = cx - math.cos(ang)*w*0.13
            d.polygon([(cx, cy), (fx2, fy), (cx + (fx2 - cx)*0.6, fy + h*0.015)], fill=verde, outline=oscuro)
    for k in range(7):
        bx = w*(0.05 + 0.15*k)
        d.pieslice([bx - w*0.09, suelo - h*0.07, bx + w*0.09, suelo + h*0.03], 180, 360,
                   fill=oscuro if k % 2 else verde, outline=TINTA)


def _ventana_piso(d, cx, cy, ancho, alto, rnd, g):
    """Ventana de piso con cuarterones y visillos, y los tejados de enfrente."""
    izq, der, arr, aba = cx-ancho/2, cx+ancho/2, cy-alto/2, cy+alto/2
    d.rectangle([izq, arr, der, aba], fill=(150, 196, 228))
    for k in range(3):                          # los tejados de enfrente
        tx = izq + ancho*(0.18 + 0.32*k)
        d.rectangle([tx - ancho*0.14, aba - alto*0.30, tx + ancho*0.14, aba], fill=(210, 170, 130))
        d.polygon([(tx - ancho*0.17, aba - alto*0.30), (tx, aba - alto*0.42),
                   (tx + ancho*0.17, aba - alto*0.30)], fill=(170, 74, 58))
    _linea(d, [(izq, arr), (der, arr), (der, aba), (izq, aba), (izq, arr)], g, rnd, temblor=1.0)
    _linea(d, [(cx, arr), (cx, aba)], g, rnd, temblor=1.0)
    _linea(d, [(izq, cy), (der, cy)], max(2, g//2), rnd, temblor=1.0)
    for lado in (-1, 1):                        # los visillos recogidos
        borde = izq if lado < 0 else der
        pts = [(borde, arr), (borde - lado*ancho*0.22, arr), (borde - lado*ancho*0.08, cy),
               (borde - lado*ancho*0.16, aba), (borde, aba)]
        d.polygon(pts, fill=(246, 242, 232))
        _linea(d, pts[1:4], max(2, g//2), rnd, color=(190, 182, 168), temblor=1.2)
    d.rectangle([izq - ancho*0.06, aba, der + ancho*0.06, aba + alto*0.06], fill=MADERA_CLARA,
                outline=TINTA, width=max(2, g//2))


def _cuadro(d, cx, cy, ancho, rnd, g):
    """El cuadro del salon: un paisaje con su marco dorado, un poco torcido."""
    alto = ancho*0.72
    marco = ancho*0.09
    d.polygon([(cx-ancho/2, cy-alto/2+ancho*0.02), (cx+ancho/2, cy-alto/2-ancho*0.02),
               (cx+ancho/2, cy+alto/2-ancho*0.02), (cx-ancho/2, cy+alto/2+ancho*0.02)],
              fill=ORO_ESPAÑA, outline=TINTA)
    i0, i1 = cx-ancho/2+marco, cx+ancho/2-marco
    j0, j1 = cy-alto/2+marco, cy+alto/2-marco
    d.rectangle([i0, j0, i1, j1], fill=(170, 210, 232))
    d.polygon([(i0, j1), (i0 + (i1-i0)*0.35, j0 + (j1-j0)*0.35), (i0 + (i1-i0)*0.6, j1)],
              fill=(110, 140, 96))
    d.polygon([(i0 + (i1-i0)*0.4, j1), (i0 + (i1-i0)*0.72, j0 + (j1-j0)*0.25), (i1, j1)],
              fill=(88, 120, 80))
    r = (i1-i0)*0.09
    d.ellipse([i1 - r*3, j0 + r, i1 - r, j0 + r*3], fill=(248, 220, 110))
    _linea(d, [(cx, cy-alto/2-ancho*0.22), (cx-ancho*0.3, cy-alto/2), (cx+ancho*0.3, cy-alto/2),
               (cx, cy-alto/2-ancho*0.22)], max(2, g//2), rnd, temblor=1.0)


def _reloj_pared(d, cx, cy, ancho, rnd, g):
    """Reloj de pendulo colgado: el tiempo que pasa, que es de lo que va."""
    alto = ancho*2.4
    d.rounded_rectangle([cx-ancho/2, cy-alto*0.30, cx+ancho/2, cy+alto*0.70],
                        radius=int(ancho*0.18), fill=MADERA_OSCURA, outline=TINTA, width=g)
    r = ancho*0.36
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(246, 240, 224), outline=TINTA, width=max(2, g//2))
    _linea(d, [(cx, cy), (cx, cy - r*0.72)], max(2, g//2), rnd, temblor=0.6)
    _linea(d, [(cx, cy), (cx + r*0.5, cy + r*0.2)], max(2, g//2), rnd, temblor=0.6)
    vy = cy + alto*0.42
    d.rectangle([cx-ancho*0.30, cy + r*1.3, cx+ancho*0.30, cy + alto*0.62], fill=(70, 50, 30))
    _linea(d, [(cx, cy + r*1.3), (cx + ancho*0.08, vy)], max(2, g//2), rnd, color=ORO_ESPAÑA,
           temblor=0.6)
    rp = ancho*0.11
    d.ellipse([cx + ancho*0.08 - rp, vy - rp, cx + ancho*0.08 + rp, vy + rp], fill=ORO_ESPAÑA)


def _aparador(d, x, y, ancho, rnd, g):
    """El aparador del salon con su radio encima."""
    alto = ancho*0.62
    d.rectangle([x-ancho/2, y-alto, x+ancho/2, y], fill=MADERA, outline=TINTA, width=g)
    for k in (-1, 1):
        d.rectangle([x + k*ancho*0.25 - ancho*0.21, y-alto*0.86, x + k*ancho*0.25 + ancho*0.21,
                     y-alto*0.12], outline=MADERA_OSCURA, width=max(2, g//2))
        d.ellipse([x + k*ancho*0.06 - g, y-alto*0.5 - g, x + k*ancho*0.06 + g, y-alto*0.5 + g],
                  fill=ORO_ESPAÑA)
    rw, rh = ancho*0.38, ancho*0.28                 # la radio
    d.rounded_rectangle([x-rw/2, y-alto-rh, x+rw/2, y-alto], radius=int(rh*0.45),
                        fill=(140, 92, 52), outline=TINTA, width=max(2, g//2))
    d.rectangle([x-rw*0.36, y-alto-rh*0.70, x+rw*0.10, y-alto-rh*0.25], fill=(232, 214, 170))
    for k in (0.24, 0.38):
        rr = rh*0.10
        d.ellipse([x+rw*k-rr, y-alto-rh*0.48-rr, x+rw*k+rr, y-alto-rh*0.48+rr], fill=TINTA)


def _galera(d, x, y, t, rnd, g, s=1):
    """Una galera de lejos: casco largo y bajo, la fila de remos y una vela
    latina. Distinta del barco de Colon, que es alto y de velas cuadradas."""
    casco = [(x - t*0.9, y - t*0.16), (x + t*0.9, y - t*0.22), (x + t*0.7, y), (x - t*0.75, y)]
    d.polygon(casco, fill=MADERA); _linea(d, casco + [casco[0]], max(2, g//2), rnd, color=TINTA)
    for k in range(7):
        rx = x - t*0.6 + k*t*0.2
        _linea(d, [(rx, y - t*0.05), (rx - s*t*0.10, y + t*0.16)], max(1, g//3), rnd, color=TINTA,
               temblor=0.3)
    _linea(d, [(x, y - t*0.18), (x, y - t*0.95)], max(2, g//2), rnd, color=MADERA_OSCURA)
    vela = [(x - s*t*0.45, y - t*0.30), (x + s*t*0.55, y - t*1.05), (x + s*t*0.10, y - t*0.30)]
    d.polygon(vela, fill=(248, 244, 232)); _linea(d, vela + [vela[0]], max(2, g//2), rnd, color=TINTA)


def _batalla_naval(d, w, h, suelo, rnd, g):
    """LEPANTO al fondo: galeras en el horizonte, humo de los cañonazos, un
    fogonazo y una galera ardiendo. Sin esto la cubierta era la de Colon con
    otra gente: no se veia ninguna batalla."""
    mar = suelo - h*0.06
    rr = random.Random(11)
    for k, (px, t) in enumerate(((0.09, 0.080), (0.29, 0.062), (0.50, 0.050),
                                 (0.71, 0.064), (0.91, 0.082))):
        X, T = w*px, h*t
        # El humo detras de cada galera: bolas grises que suben.
        for j in range(4):
            r = T*rr.uniform(0.35, 0.55)*(1 + j*0.25)
            cx, cy = X + rr.uniform(-T*0.4, T*0.4), mar - T*(0.9 + j*0.55)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(150, 146, 140, 255))
        _galera(d, X, mar + T*0.10, T, rnd, g, s=1 if px < 0.5 else -1)
        if k in (1, 3):                               # fogonazo de cañon
            fx = X + (T*0.95 if px < 0.5 else -T*0.95)
            puntas = []
            for a in range(10):
                rad = T*(0.45 if a % 2 else 0.22)
                ang = a*math.pi/5
                puntas.append((fx + math.cos(ang)*rad, mar - T*0.05 + math.sin(ang)*rad))
            d.polygon(puntas, fill=(255, 196, 60), outline=(220, 90, 30))
    COSAS["fuego"](d, w*0.91, mar - h*0.05, h*0.08, rnd, max(2, g//2))


def _arco_apuntado(d, cx, base, ancho, alto, rnd, g, relleno):
    pts = [(cx - ancho/2, base), (cx - ancho/2, base - alto*0.55)]
    for i in range(1, 12):
        t = i/12
        pts.append((cx - ancho/2 + ancho/2*t, base - alto*0.55 - alto*0.45*math.sin(t*math.pi/2)))
    pts.append((cx, base - alto))
    for i in range(11, 0, -1):
        t = i/12
        pts.append((cx + ancho/2 - ancho/2*t, base - alto*0.55 - alto*0.45*math.sin(t*math.pi/2)))
    pts += [(cx + ancho/2, base - alto*0.55), (cx + ancho/2, base)]
    d.polygon(pts, fill=relleno)
    _linea(d, pts, g, rnd, color=TINTA)


def _mezquitas(d, w, base, alto, rnd, g, color=(214, 200, 176)):
    """La silueta de Constantinopla: cupulas con sus minaretes. La misma
    sirve para la Alhambra de lejos o cualquier ciudad de Oriente."""
    for k, (px, ancho) in enumerate(((0.10, .10), (0.30, .16), (0.55, .20), (0.80, .13))):
        cx, a = w*px, w*ancho
        cuerpo = [cx - a/2, base - alto*0.35, cx + a/2, base]
        d.rectangle(cuerpo, fill=color, outline=TINTA, width=max(2, g//2))
        d.pieslice([cx - a*0.38, base - alto*0.35 - a*0.38, cx + a*0.38, base - alto*0.35 + a*0.38],
                   180, 360, fill=color, outline=TINTA, width=max(2, g//2))
        d.line([(cx, base - alto*0.35 - a*0.38), (cx, base - alto*0.35 - a*0.50)], fill=TINTA,
               width=max(2, g//2))
        for lado in (-1, 1):                     # los minaretes
            mx = cx + lado*a*0.62
            d.rectangle([mx - w*0.006, base - alto*0.95, mx + w*0.006, base], fill=color,
                        outline=TINTA, width=max(1, g//3))
            d.polygon([(mx - w*0.008, base - alto*0.95), (mx, base - alto*1.12),
                       (mx + w*0.008, base - alto*0.95)], fill=(140, 120, 100))


def _campana(d, x, y, t, rnd, g):
    """Una campana de iglesia colgada de su yugo: las que repicaron por
    toda Europa con la noticia de Lepanto."""
    oro = (196, 150, 52)
    arriba = y - t
    d.line([(x - t*0.35, arriba), (x + t*0.35, arriba)], fill=MADERA_OSCURA, width=int(g*1.6))
    for lado in (-1, 1):
        d.line([(x + lado*t*0.35, arriba), (x + lado*t*0.35, y)], fill=MADERA_OSCURA, width=g)
    cuerpo = [(x - t*0.12, arriba + t*0.12), (x + t*0.12, arriba + t*0.12), (x + t*0.17, arriba + t*0.45),
              (x + t*0.27, arriba + t*0.62), (x - t*0.27, arriba + t*0.62), (x - t*0.17, arriba + t*0.45)]
    d.polygon(cuerpo, fill=oro)
    _linea(d, cuerpo + [cuerpo[0]], g, rnd)
    d.ellipse([x - t*0.05, arriba + t*0.62, x + t*0.05, arriba + t*0.72], fill=TINTA)


def _galeaza(d, x, y, t, rnd, g):
    """La galeaza veneciana: una galera grande, con castillos a proa y popa
    llenos de cañones. Las seis de Lepanto abrieron la batalla."""
    _galera(d, x, y, t, rnd, g)
    for lado in (-1, 1):
        cx = x + lado*t*0.62
        caja = [cx - t*0.20, y - t*0.42, cx + t*0.20, y - t*0.14]
        d.rectangle(caja, fill=MADERA_OSCURA, outline=TINTA, width=max(2, g//2))
        for k in (-0.1, 0.06):
            d.ellipse([cx + t*k - t*0.03, y - t*0.31, cx + t*k + t*0.03, y - t*0.25], fill=TINTA)


def _gondola(d, x, y, t, rnd, g):
    """La gondola de Venecia: negra, larga, con las puntas levantadas y el
    gondolero de pie con su remo."""
    casco = [(x - t*0.9, y - t*0.32), (x - t*0.7, y - t*0.06), (x + t*0.7, y - t*0.06),
             (x + t*0.9, y - t*0.36), (x + t*0.75, y), (x - t*0.75, y)]
    d.polygon(casco, fill=(28, 26, 30))
    _linea(d, casco + [casco[0]], max(2, g//2), rnd)
    d.line([(x + t*0.45, y - t*0.95), (x + t*0.70, y + t*0.10)], fill=MADERA, width=max(2, g//2))


def _palacio_ducal(d, w, suelo, h, rnd, g):
    """Venecia: el Palacio Ducal rosa y blanco con sus dos filas de arcos, y
    el campanile de San Marcos al lado."""
    x0, x1 = w*0.04, w*0.66
    alto = h*0.40
    d.rectangle([x0, suelo - alto, x1, suelo], fill=(236, 200, 190), outline=TINTA, width=g)
    rr = random.Random(3)
    for k in range(40):                                   # el rombo rosa de la fachada
        px, py = rr.uniform(x0, x1), rr.uniform(suelo - alto, suelo - alto*0.45)
        r = w*0.006
        d.polygon([(px, py - r), (px + r, py), (px, py + r), (px - r, py)], fill=(214, 150, 150))
    ancho = (x1 - x0)/12
    for fila, (arriba, abajo) in enumerate(((0.42, 0.22), (0.20, 0.0))):
        for k in range(12):
            cx = x0 + ancho*(k + 0.5)
            yb = suelo - alto*abajo
            ya = suelo - alto*arriba
            d.rectangle([cx - ancho*0.32, ya + ancho*0.32, cx + ancho*0.32, yb], fill=(70, 60, 64))
            d.pieslice([cx - ancho*0.32, ya, cx + ancho*0.32, ya + ancho*0.64], 180, 360, fill=(70, 60, 64))
    cx = w*0.80                                           # el campanile
    d.rectangle([cx - w*0.035, suelo - h*0.58, cx + w*0.035, suelo], fill=(176, 92, 72),
                outline=TINTA, width=g)
    d.rectangle([cx - w*0.04, suelo - h*0.64, cx + w*0.04, suelo - h*0.56], fill=(236, 226, 206),
                outline=TINTA, width=max(2, g//2))
    d.polygon([(cx - w*0.04, suelo - h*0.64), (cx, suelo - h*0.78), (cx + w*0.04, suelo - h*0.64)],
              fill=(80, 130, 110), outline=TINTA)


def _san_pedro(d, w, suelo, h, rnd, g):
    """Roma: la fachada de San Pedro con sus columnas y la cupula detras."""
    cx = w*0.5
    d.pieslice([cx - w*0.13, suelo - h*0.66, cx + w*0.13, suelo - h*0.40], 180, 360,
               fill=(196, 206, 214), outline=TINTA, width=g)
    d.line([(cx, suelo - h*0.66), (cx, suelo - h*0.72)], fill=TINTA, width=g)
    d.line([(cx - w*0.008, suelo - h*0.70), (cx + w*0.008, suelo - h*0.70)], fill=TINTA, width=g)
    d.rectangle([cx - w*0.30, suelo - h*0.44, cx + w*0.30, suelo], fill=(232, 222, 200),
                outline=TINTA, width=g)
    d.polygon([(cx - w*0.12, suelo - h*0.44), (cx, suelo - h*0.52), (cx + w*0.12, suelo - h*0.44)],
              fill=(232, 222, 200), outline=TINTA)
    for k in range(9):
        px = cx - w*0.27 + k*w*0.0675
        d.rectangle([px - w*0.008, suelo - h*0.38, px + w*0.008, suelo], fill=(214, 204, 182),
                    outline=TINTA, width=max(1, g//3))


def _camastros(d, w, suelo, h, rnd, g):
    """El hospital: una fila de camastros con sabanas blancas al fondo."""
    for k in range(4):
        cx = w*(0.14 + 0.24*k)
        y = suelo + h*0.02
        d.rectangle([cx - w*0.08, y - h*0.06, cx + w*0.08, y], fill=MADERA, outline=TINTA, width=max(2, g//2))
        d.rectangle([cx - w*0.08, y - h*0.085, cx + w*0.08, y - h*0.05], fill=(244, 240, 230),
                    outline=TINTA, width=max(2, g//2))
        d.ellipse([cx - w*0.075, y - h*0.11, cx - w*0.035, y - h*0.075], fill=(250, 248, 244),
                  outline=TINTA, width=max(1, g//3))


def _costa(d, w, suelo, h, rnd, g):
    """Un pueblo de la costa: casas blancas en lo alto y la torre de vigia,
    la que avisaba cuando venian los corsarios."""
    base = suelo - h*0.06
    for k in range(6):
        px = w*(0.05 + 0.08*k)
        alto = h*rnd.uniform(0.07, 0.10)
        d.rectangle([px, base - alto, px + w*0.06, base], fill=(246, 244, 236), outline=TINTA, width=max(2, g//2))
        d.rectangle([px + w*0.02, base - alto*0.6, px + w*0.035, base - alto*0.3], fill=(80, 110, 150))
    tx = w*0.86
    d.rectangle([tx - w*0.03, base - h*0.30, tx + w*0.03, base], fill=PIEDRA_CLARA, outline=TINTA, width=g)
    for k in range(3):
        d.rectangle([tx - w*0.03 + k*w*0.024, base - h*0.33, tx - w*0.018 + k*w*0.024, base - h*0.30],
                    fill=PIEDRA_CLARA, outline=TINTA, width=max(1, g//3))


def _divan(d, x, y, ancho, rnd, g):
    """El divan del sultan: bajo, largo, rojo, con cojines."""
    alto = ancho*0.22
    d.rounded_rectangle([x - ancho/2, y - alto, x + ancho/2, y], radius=int(alto*0.3),
                        fill=(170, 40, 50), outline=TINTA, width=g)
    d.rectangle([x - ancho/2, y - alto*1.9, x + ancho/2, y - alto*0.9], fill=(140, 30, 40),
                outline=TINTA, width=max(2, g//2))
    for k in (-0.32, 0, 0.32):
        cx = x + ancho*k
        d.ellipse([cx - ancho*0.09, y - alto*1.55, cx + ancho*0.09, y - alto*0.85],
                  fill=(236, 186, 40), outline=TINTA, width=max(2, g//2))


def _pieza_fondo(d, w, h, suelo, que, x, y, tam, rnd, g):
    X, Y, T = w*x, h*y, w*tam
    if que == "ventana_mar":      _ventana_al_mar(d, X, h*y, T, h*tam*0.55, rnd, g)
    elif que == "ventana_arco":   _ventana_arco(d, X, h*y, T, h*tam*0.95, rnd, g)
    elif que == "chimenea":       _chimenea(d, X, suelo, T, h*tam, rnd, g)
    elif que == "trono":          _trono(d, X, suelo, T, rnd, g)
    elif que == "estandarte":
        # Los dos eran del mismo rojo, asi que un salon del trono parecia una
        # pared con dos manchas iguales. Luego el de la derecha fue "el azul
        # de la casa", azul con una franja blanca - y ella pregunto "¿que es
        # esa bandera azul y blanca?": no era de nadie, y en pantalla parecia
        # la de algun pais. Ahora es la cruz de Borgoña, la que ondeaba de
        # verdad en los palacios y los ejercitos de España: rojo y gualda a un
        # lado, aspa roja al otro, y las dos son nuestras.
        if X < w/2:
            _estandarte(d, X, h*y, T, h*tam*1.9, rnd, g, color=ROJO_ESPAÑA, franja=ORO_ESPAÑA)
        else:
            _estandarte(d, X, h*y, T, h*tam*1.9, rnd, g, color=BLANCO, aspa=ROJO_ESPAÑA)
    elif que == "cruz_grande":    _cruz(d, X, h*y, h*tam, rnd, int(g*1.6), TINTA)
    elif que == "mastil":         _mastil(d, X, suelo, h, rnd, g)
    elif que == "batalla_naval":  _batalla_naval(d, w, h, suelo, rnd, g)
    elif que == "arcos_otomanos":
        for px in (0.30, 0.70):
            _arco_apuntado(d, w*px, suelo, w*0.16, h*0.42, rnd, g, (24, 40, 74))
    elif que == "estandarte_otomano":
        _estandarte(d, X, h*y, T, h*tam*1.9, rnd, g, color=(196, 30, 40))
        cx, cy, r = X, h*y + h*tam*0.75, T*0.20
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BLANCO)
        d.ellipse([cx - r*.45, cy - r*.85, cx + r*1.2, cy + r*.85], fill=(196, 30, 40))
    elif que == "palacio_ducal":  _palacio_ducal(d, w, suelo, h, rnd, g)
    elif que == "san_pedro":      _san_pedro(d, w, suelo, h, rnd, g)
    elif que == "costa":          _costa(d, w, suelo, h, rnd, g)
    elif que == "mezquitas":
        _mezquitas(d, w, suelo - h*0.06, h*0.22, rnd, g)
    elif que == "casas":
        for k in range(5):
            px = w*(0.08 + 0.21*k)
            _casa(d, px, suelo + h*0.005, h*rnd.uniform(0.17, 0.25), rnd, g, TINTA)
    elif que == "puesto":
        toldo = [(X-T*.6, suelo-h*.20), (X+T*.6, suelo-h*.20),
                 (X+T*.5, suelo-h*.13), (X-T*.5, suelo-h*.13)]
        d.polygon(toldo, fill=(198, 88, 76)); _linea(d, toldo+[toldo[0]], g, rnd, color=TINTA)
        for lado in (-1, 1):
            _linea(d, [(X+lado*T*.5, suelo-h*.14), (X+lado*T*.5, suelo)], g, rnd, color=MADERA_OSCURA)
        _mesa_con_cosas(d, X, suelo, T*1.1, rnd, max(2, g//2), papeles=1, jarras=1, alto=h*0.045)
    elif que == "muralla":        _muralla(d, w, h, suelo, rnd, g)
    elif que == "tiendas":        _tiendas(d, w, h, suelo, rnd, g)
    elif que == "naranjos":       _naranjos(d, w, h, suelo, rnd, g)
    elif que == "cortinas":       _cortinas(d, w, h, suelo, rnd, g)
    elif que == "reja":           _reja(d, X, h*y, T, h*tam*0.7, rnd, g)
    elif que == "selva":          _selva(d, w, h, suelo, rnd, g)
    elif que == "ventana_piso":   _ventana_piso(d, X, h*y, T, h*tam*0.62, rnd, g)
    elif que == "cuadro":         _cuadro(d, X, h*y, T, rnd, g)
    elif que == "reloj":          _reloj_pared(d, X, h*y, T, rnd, g)
    elif que == "puntales":
        for k in range(3):
            px = w*(0.16 + 0.34*k)
            _linea(d, [(px, suelo), (px, h*0.10)], int(g*2.6), rnd, color=MADERA_OSCURA)
        _linea(d, [(0, h*0.10), (w, h*0.10)], int(g*2.6), rnd, color=MADERA_OSCURA)


def _pieza_mueble(d, w, h, suelo, que, x, y, tam, rnd, g):
    X, Y, T = w*x, suelo + h*y, w*tam
    if que == "mesa_fondo":
        _mesa_con_cosas(d, X, Y, T, rnd, max(2, g//2), papeles=1, jarras=1, alto=h*0.035)
    elif que == "taburete":   _taburete(d, X, Y, h*tam, rnd, g)
    elif que == "estante":    _estante(d, X, h*y, T, rnd, g)
    elif que == "banco_fondo":_banco(d, X, Y, T, rnd, g)
    elif que == "olla_suelo": _olla(d, X, Y, h*tam, rnd, g)
    elif que == "mesa":       _mesa_con_cosas(d, X, Y, T, rnd, g, alto=h*0.075)
    elif que == "aparador":   _aparador(d, X, Y, T, rnd, g)
    elif que == "divan":      _divan(d, X, Y, T, rnd, g)
    elif que == "camastros":  _camastros(d, w, suelo, h, rnd, g)
    elif que == "acampada":
        rr = random.Random(5)
        for k in range(7):                                # fila de atras, mas pequeñas
            _tienda(d, w*(0.07 + 0.145*k) + rr.uniform(-10, 10), suelo + h*0.035,
                    h*rr.uniform(0.060, 0.075), rnd, max(2, g//2))
        for px in (0.03, 0.97):                           # y dos delante, en los bordes
            _tienda(d, w*px, suelo + h*0.11, h*0.095, rnd, g)
        for px in (0.30, 0.70):
            _pancarta(d, w*px, suelo - h*0.02, h*0.10, rnd, max(2, g//2))
    elif que == "barandilla":
        _linea(d, [(0, Y), (w, Y)], int(g*2.6), rnd, color=MADERA_OSCURA)
        for k in range(7):
            px = w*(0.07 + 0.145*k)
            _linea(d, [(px, Y), (px, h)], int(g*1.8), rnd, color=MADERA_OSCURA)


_NAVEGAN = ("barco", "galera", "galeaza", "gondola")


def montar(spec: dict, w: int, h: int, semilla: int = 0):
    """Un decorado cualquiera, montado desde su receta y por capas.

    El orden es el mismo para todos, y es lo que hace que un sitio nuevo
    cueste tres lineas de receta en vez de media hora de funcion a medida:

      pared -> lo del fondo -> suelo -> muebles -> GENTE -> muebles de
      delante -> lo colgado -> marco -> resplandores
    """
    receta = _DECORADOS.get(spec.get("interior"))
    if receta is None:
        return escena(spec, w, h, semilla)
    rnd = random.Random(semilla)
    suelo = int(h*spec.get("suelo", 0.66))
    img = Image.new("RGB", (w, h), (226, 214, 192))
    d = ImageDraw.Draw(img)
    g = max(4, int(w*0.006))

    clase = receta["pared"]
    if clase == "cielo_mar":
        _pared(d, w, 0, suelo, "cielo", rnd, g)
        d.rectangle([0, suelo - h*0.06, w, suelo], fill=(92, 140, 186))
    elif clase == "roca":
        _pared(d, w, 0, suelo, "piedra", rnd, g)
        d.rectangle([0, 0, w, suelo], fill=(96, 86, 76))
    else:
        _pared(d, w, 0, suelo, clase, rnd, g)

    for que, x, y, tam in receta["fondo"]:
        _pieza_fondo(d, w, h, suelo, que, x, y, tam, rnd, g)
    # Lo colgado de la pared, DETRAS de todo lo demas: es pared. Lo tenia al
    # final, despues incluso de los muebles de delante, y las espadas del
    # salon del trono salian clavadas en la cabeza de los monigotes.
    for que, x, y, tam in receta["cuelga"]:
        f = COSAS.get(que)
        if f:
            f(d, w*x, h*y, h*tam, rnd, max(2, g//2), TINTA)
    _piso(d, w, h, suelo, receta["piso"], rnd, g)
    for que, x, y, tam in receta["muebles"]:
        _pieza_mueble(d, w, h, suelo, que, x, y, tam, rnd, g)

    # DONDE PISA LA GENTE. Tenia un +0.24 fijo, puesto para la taberna: ahi
    # hay una mesa por delante que les tapa medio cuerpo, asi que hundirlos es
    # lo correcto. En un salon del trono NO hay mesa, y ese mismo +0.24 les
    # dejaba los pies al 90% de la pantalla - mas el 4,5% que recorta la
    # camara -, o sea con las piernas cortadas por el borde y un agujero
    # vacio enorme entre la pared y ellos.
    #
    # Asi que depende del decorado, no de un numero suelto: si hay algo
    # delante, se hunden para que lo tape; si no, pisan cerca de la linea del
    # suelo, que es donde pisa la gente.
    # Y con TOPE: pase lo que pase, los pies no bajan del 86% de la pantalla.
    # Un decorado con mesa mas un personaje alto mas el recorte de camara se
    # comian las piernas por el borde de abajo, y eso no puede depender de que
    # los numeros del decorado esten bien elegidos.
    hunde = h*(0.24 if receta["delante"] else 0.06)
    pies = min(suelo + hunde, h*0.86)

    # LAS COSAS. Esto faltaba ENTERO, y no se veia desde ningun log.
    #
    # "El fondo tambien es importante: si habla de perro dibuja un perro". Eso
    # se hizo, y funciona... en exteriores. escena() las pinta; montar(), que
    # es por donde pasan los nueve decorados, no las pintaba. O sea que en una
    # taberna, una iglesia o un salon del trono el guion podia pedir el barco,
    # la bandera o el dinero, limpia() los validaba y los devolvia, y luego
    # nadie los dibujaba. Silencio absoluto: el video salia, nada petaba.
    #
    # En el #91 se ve: banderas en las escenas de campo, ninguna cosa en las
    # de interior.
    def _pinta_cosas(delante):
        for c in spec.get("cosas", []):
            dibuja = COSAS.get(c.get("que"))
            if dibuja is None or bool(c.get("delante")) != delante:
                continue
            # A ras de la misma linea que pisa la gente, o donde se diga si va
            # por el aire.
            py = h*float(c["y"]) if c.get("y") is not None else pies
            tam = h*float(c.get("tam", 0.14))
            # LOS BARCOS VAN EN EL MAR. Con el mar de fondo (la cubierta, el
            # puerto, la batalla) una galera "en el suelo" salia gigante
            # encima de las tablas de la cubierta, como varada en el barco.
            # Se mandan al agua, lejos y del tamaño de lejos.
            if c.get("que") in _NAVEGAN and receta["pared"] == "cielo_mar" and c.get("y") is None:
                py, tam = suelo - h*0.012, min(tam, h*0.10)
            dibuja(d, w*float(c.get("x", 0.5)), py, tam, rnd, max(4, int(w*0.006)))

    _pinta_cosas(delante=False)
    _camas(d, spec, h, w, lambda f: pies, rnd, max(4, int(w*0.006)), "detras")
    adornos = []
    for f in spec.get("figuras", []):
        alto_f = h*f.get("alto", 0.30)
        adornos.append(_dibuja_figura(
            img, d, f, w*f["x"], pies + alto_f*_RESPIRACION*f.get("_bocanada", 0.0),
            alto_f, rnd, rasgos=REPARTO.get(f.get("quien") or ""), objeto=f.get("objeto")))

    _camas(d, spec, h, w, lambda f: pies, rnd, max(4, int(w*0.006)), "delante")

    # QUIEN FIRMA, FIRMA SOBRE ALGO. "en_mesa" y "firmando" son posturas de
    # estar sentado a una mesa: los brazos se apoyan en un tablero que en la
    # taberna o la cocina existe, y en un salon del trono no. Sin esto el que
    # firma el tratado escribe en el aire, sentado en nada.
    #
    # Es el mismo asunto del +0.24 de la taberna: una postura que da por hecho
    # un mueble del primer decorado donde la probe.
    tiene_mesa = any(que == "mesa" for que, *_ in receta["muebles"] + receta["delante"])
    if not tiene_mesa:
        for f in spec.get("figuras", []):
            if f.get("pose") in _POSES_DE_MESA or f.get("pose_fin") in _POSES_DE_MESA:
                alto_f = h*f.get("alto", 0.30)
                # A la altura de las MANOS, que en estas posturas estan a un
                # tercio de la figura. Estaba al 10% - una mesita a ras de
                # suelo -, y Godoy firmaba el tratado en el aire.
                _mesa_con_cosas(d, w*f["x"] + alto_f*0.10, pies + alto_f*0.06,
                                alto_f*0.78, rnd, max(2, g//2),
                                papeles=1, jarras=0, alto=alto_f*0.34)

    for que, x, y, tam in receta["delante"]:
        _pieza_mueble(d, w, h, suelo, que, x, y, tam, rnd, g)
    _pinta_cosas(delante=True)
    _pinta_adornos(d, adornos, rnd)
    spec["_cabezas"] = [(fx, fy - fa*0.86, fa) for _, fx, fy, fa in adornos]
    _pinta_papeles(d, spec, w, h, pies)
    _pinta_rotulo(d, spec, w, h)

    if spec.get("cartel"):
        _cartel(d, w*0.50, h*0.09, w*0.44, str(spec["cartel"])[:40], rnd, g)
    for vx, vy in receta["velas"]:
        _vela(d, w*vx, suelo + h*vy, h*0.035, rnd, max(2, g//2))
        img = _resplandor(img, (w*vx, suelo + h*vy - h*0.03), h*0.10)
    return img


# La lista que ve el guion ES la de las recetas, no una copia a mano.
INTERIORES_VALIDOS = DECORADOS_VALIDOS


# ---- MONTAR LA ESCENA --------------------------------------------------------
# "Es muy importante montar las escenas y tener claro los personajes". En el
# video de Carlos II se ve el problema: los monigotes estan de pie uno al lado
# del otro MIRANDO AL FRENTE, como en una foto de orla. Nadie mira a nadie, no
# se sabe quien habla y los demas no reaccionan.
#
# El guion elige la x, el espejo y el gesto de cada uno por separado y sin ver
# el resultado, asi que sale un grupo, no una escena. Esto lo monta el codigo,
# que es donde se puede GARANTIZAR - igual que la separacion o el tope de los
# pies.

# Lo que pone la cara de quien escucha, segun lo que pone la de quien habla.
_REACCION = {
    "grito":     "sorpresa",
    "enfadado":  "sorpresa",
    "sorpresa":  "neutro",
    "contento":  "contento",
    "neutro":    "neutro",
}


def _montar_escena(limpio: dict) -> dict:
    """Coloca a la gente para que se vea QUIEN habla y a quien.

    Tres cosas, y ninguna se le puede pedir al guion de forma fiable:

    SE MIRAN. Quien habla mira hacia los demas y los demas hacia el. Un
    monigote mirando al frente mientras otro le grita no es una escena.

    EL QUE HABLA DESTACA. Un poco mas alto y hacia el centro: en un movil,
    sin eso, no se sabe de cual sale el bocadillo aunque el rabo apunte.

    Y LOS DEMAS REACCIONAN. Si alguien grita y el de al lado tiene cara
    neutra, el plano se cae. Solo se toca a quien venia en 'neutro': si el
    guion pidio una cara concreta, manda el guion.
    """
    figuras = limpio.get("figuras") or []
    if len(figuras) < 2:
        return limpio

    habla = limpio.get("habla_x")
    if isinstance(habla, (int, float)):
        quien = min(figuras, key=lambda f: abs(f["x"] - float(habla)))
    else:
        quien = figuras[0]
    centro = sum(f["x"] for f in figuras)/len(figuras)

    for f in figuras:
        if f is quien:
            # Mira hacia donde esta el resto, y destaca un poco.
            f["espejo"] = f["x"] > centro
            f["alto"] = min(0.46, f["alto"]*1.08)
            f["x"] = f["x"] + (centro - f["x"])*0.12
        else:
            f["espejo"] = f["x"] > quien["x"]
            if f.get("gesto", "neutro") == "neutro":
                f["gesto"] = _REACCION.get(quien.get("gesto", "neutro"), "sorpresa")
    limpio["habla_x"] = quien["x"]
    return limpio


# Al final del todo, que es donde ya existe POSES_VALIDAS.
_las_posturas_estan_explicadas()
