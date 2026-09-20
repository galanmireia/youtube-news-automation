"""El calendario del canal: que sucesos tienen aniversario y cuando.

De donde sale esto. El video mas visto de hoy en noticias de España tenia
3.454.779 visitas y era un documental del 11-S - y ella vio lo que yo no vi:
no los tiene porque el 11-S sea famoso, los tiene porque estamos en
septiembre. En marzo ese mismo video mide una fraccion. Yo habia cogido un
pico estacional y lo habia leido como demanda permanente.

Pero eso, bien mirado, es mejor que lo que yo decia. Un aniversario es
predecible con un año de antelacion: hoy ya se sabe que el 26 de abril la
gente buscara Chernobil y el 11 de marzo el 11-M. Y encaja justo con la
limitacion real del canal, que es la velocidad. Una noticia hay que
publicarla en horas y aqui un video tarda veinte minutos en montarse y hay
que revisarlo. Un aniversario se prepara con dos semanas.

De ahi el modelo: documentales de sucesos conocidos, publicados en la ventana
de su aniversario. Evergreen con un pico anual garantizado - el video sigue
sirviendo el resto del año y cada año vuelve a subir solo.

CUIDADO AL LEER LA DEMANDA DE ESTA LISTA: medir Chernobil en octubre da una
cifra baja, y descartarlo por eso seria el mismo error de antes al reves. La
demanda de un tema de aqui se mide EN SU VENTANA, no hoy.

Los titulos son los de Wikipedia porque son los que lee el dosier, y estan
escritos de memoria - o sea que hay que comprobarlos con /catalogo antes de
fiarse. Ya paso hoy: "Silk Road (mercado negro)" no existia.
"""
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)

# Cuantos dias antes del aniversario conviene publicar. La ola de busquedas
# empieza dias antes y YouTube necesita tiempo para indexar y empezar a
# enseñarlo: llegar el mismo dia es llegar tarde.
DIAS_ANTES = 4

# Ventana por defecto para "que viene ahora".
VENTANA = 21

# (mes, dia, año, titulo en Wikipedia). El año es para poder decir "40
# aniversario", que es un gancho en si mismo y un dato para la miniatura.
CALENDARIO: list[tuple[int, int, int, str]] = [
    # Enero
    (1, 13, 2012, "Naufragio del Costa Concordia"),
    (1, 13, 2019, "Caso Julen"),
    (1, 28, 1986, "Accidente del transbordador espacial Challenger"),
    # Febrero
    (2, 1, 2003, "Accidente del transbordador espacial Columbia"),
    (2, 12, 2005, "Incendio del Edificio Windsor"),
    (2, 23, 1981, "Golpe de Estado en España de 1981"),
    # Marzo
    (3, 11, 2004, "Atentados del 11 de marzo de 2004"),
    (3, 11, 2011, "Accidente nuclear de Fukushima I"),
    (3, 24, 2015, "Vuelo 9525 de Germanwings"),
    (3, 24, 1989, "Exxon Valdez"),
    (3, 27, 1977, "Accidente de Los Rodeos"),
    # Abril
    (4, 15, 1912, "Hundimiento del RMS Titanic"),
    (4, 20, 2010, "Explosión de Deepwater Horizon"),
    (4, 25, 1998, "Desastre de Aznalcóllar"),
    (4, 26, 1986, "Accidente de Chernóbil"),
    # Mayo
    (5, 6, 1937, "Desastre del Hindenburg"),
    (5, 7, 1915, "Hundimiento del RMS Lusitania"),
    # Junio
    (6, 14, 2017, "Incendio de la Torre Grenfell"),
    (6, 19, 1987, "Atentado de Hipercor"),
    # Julio
    (7, 11, 1978, "Accidente del camping Los Alfaques"),
    (7, 12, 1997, "Asesinato de Miguel Ángel Blanco"),
    (7, 24, 2013, "Accidente ferroviario de Santiago de Compostela"),
    (7, 25, 2000, "Vuelo 4590 de Air France"),
    # Agosto
    (8, 4, 2020, "Explosiones de Beirut de 2020"),
    (8, 5, 2010, "Accidente de la mina San José"),
    (8, 20, 2008, "Vuelo 5022 de Spanair"),
    (8, 24, 79, "Erupción del Vesubio en 79"),
    # Septiembre
    (9, 11, 2001, "Atentados del 11 de septiembre de 2001"),
    (9, 19, 2021, "Erupción volcánica de La Palma de 2021"),
    (9, 21, 2013, "Caso Asunta"),
    (9, 28, 1994, "Naufragio del MS Estonia"),
    # Octubre
    (10, 20, 1982, "Rotura de la presa de Tous"),
    (10, 29, 2024, "Inundaciones de octubre de 2024 en España"),
    # Noviembre
    (11, 1, 1755, "Terremoto de Lisboa de 1755"),
    (11, 13, 2002, "Desastre del Prestige"),
    (11, 28, 2016, "Vuelo 2933 de LaMia"),
    # Diciembre
    (12, 3, 1984, "Desastre de Bhopal"),
    (12, 20, 1987, "Desastre del Doña Paz"),
]


def _aniversario(mes: int, dia: int, hoy: date) -> date:
    """El proximo aniversario de esta fecha a partir de hoy."""
    try:
        este_año = date(hoy.year, mes, dia)
    except ValueError:  # 29 de febrero
        este_año = date(hoy.year, mes, 28)
    if este_año >= hoy:
        return este_año
    try:
        return date(hoy.year + 1, mes, dia)
    except ValueError:
        return date(hoy.year + 1, mes, 28)


def proximas(dias: int = VENTANA, hoy: date | None = None) -> list[dict]:
    """Los aniversarios que caen dentro de la ventana, el mas cercano primero.

    Cada uno con la fecha en que conviene PUBLICAR, que no es el aniversario
    sino unos dias antes."""
    hoy = hoy or date.today()
    salida = []
    for mes, dia, año, titulo in CALENDARIO:
        cuando = _aniversario(mes, dia, hoy)
        faltan = (cuando - hoy).days
        if faltan > dias:
            continue
        salida.append({
            "titulo": titulo,
            "aniversario": cuando,
            "faltan": faltan,
            "publicar": cuando - timedelta(days=DIAS_ANTES),
            "cumple": cuando.year - año,
            "urgente": faltan <= DIAS_ANTES,
        })
    salida.sort(key=lambda e: e["faltan"])
    return salida


def por_cercania(hoy: date | None = None) -> list[str]:
    """Todos los titulos, ordenados por lo cerca que esta su aniversario.

    Es lo que usa el catalogo: asi el tema que toca sale solo, sin que nadie
    tenga que acordarse de que el 26 de abril es Chernobil."""
    hoy = hoy or date.today()
    conf = sorted(CALENDARIO, key=lambda e: (_aniversario(e[0], e[1], hoy) - hoy).days)
    return [titulo for _m, _d, _a, titulo in conf]
