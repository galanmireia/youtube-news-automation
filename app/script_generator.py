import json
import logging
import re

import anthropic

from . import bocadillos, llm_usage
from .spanish import MIN_TASA_ACENTOS, tasa_de_acentos
from .config import CONTENT_MODE, ANTHROPIC_API_KEY, CHANNEL_NAME, CHANNEL_TONE_HINT, CLAUDE_MODEL, NEWS_LANGUAGE_HINT, NARRATION_LANG

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Where the instructions end and the day's story begins. Everything before it
# is identical on every call and is what gets cached.
_STORY_MARKER = "===== MATERIAL DE PARTIDA ====="

# The two genres the channel can be in. Everything else in the prompt - photos,
# subtitles, spelling, figures on screen, SEO - is the same for both; only the
# shape of the story and what the source material is differ, so they are
# variables rather than a second copy of a seventeen-thousand-character
# template that would drift out of sync on the first edit.
_GENRE_BLOCKS = {
    "news": {
        "sensitivity_block": """AVISO DE SENSIBILIDAD (evalua esto ANTES de escribir): si la noticia trata sobre una muerte,
un crimen violento, una victima identificable, una tragedia o una desgracia personal real, O sobre
una ACUSACION, INVESTIGACION O SOSPECHA todavia no probada que recae sobre una persona concreta e
identificable (un detenido, un investigado, un imputado, un sospechoso, alguien "relacionado con" o
"vinculado a" algo), YouTube puede desmonetizar el video si el tono es sensacionalista o
"intrigante". En ese caso,
DEJA DE LADO el angulo de "lado oculto" del canal y escribe en su lugar como un medio de noticias
serio: tono neutral, respetuoso con las victimas y sus familias, sin especular sobre la
investigacion mas alla de lo confirmado, sin dramatizar ni usar ganchos tipo clickbait. El
"analisis" en estos casos debe centrarse en contexto social o estadistico legitimo (por ejemplo,
cifras del fenomeno, respuesta institucional, precedentes similares), nunca en morbo sobre la
victima concreta. Si la noticia NO es sensible (politica, tecnologia, economia, cultura, etc.),
aplica con normalidad el tono intrigante del canal descrito arriba.""",
        "structure_block": """Estructura obligatoria del guion ({duration_hint}, en este orden):
1. Gancho: una frase que enganche (intrigante si la noticia lo permite, sobria si es sensible), con una pregunta o dato relacionado (no el titular tal cual).
2. Contexto: que ha pasado antes, quien esta implicado, por que existe esta noticia ahora.
3. El hecho: los datos concretos de la noticia, explicados con tus propias palabras.
4. Analisis: en noticias normales, la parte de la historia que no suele contarse a simple vista,
   las consecuencias reales o las preguntas que deja abiertas. En noticias sensibles, contexto
   social o estadistico legitimo, tratado con seriedad. Esta es la parte que aporta valor real y
   diferencia el canal de un simple agregador de titulares.
5. Cierre: una reflexion o pregunta abierta al espectador, y llamada a suscribirse (en noticias
   sensibles, sobria y sin banalizar).""",
        "source_block": """===== MATERIAL DE PARTIDA =====
Noticia de partida (usala solo como disparador de hechos, NO la copies ni parafrasees frase a
frase):""",
    },
    "topics": {
        "sensitivity_block": """AVISO DE SENSIBILIDAD (evalua esto ANTES de escribir): este canal cuenta catastrofes, asi que
CASI TODOS los casos tienen victimas mortales. Eso por si solo NO los hace "sensibles" a efectos de
este campo. Una catastrofe documentada, contada con tono documental, sin morbo y sin recrearse en
el sufrimiento de nadie, monetiza con total normalidad - y ese tono ya te lo impone la estructura
de mas abajo, no hace falta nada mas.

Marca "is_sensitive" como true SOLO en estos dos casos:
- El suceso es muy reciente (ultimos dos años) y hay victimas identificables cuyas familias siguen
  en duelo publico.
- El relato se apoya en una acusacion, investigacion o juicio TODAVIA NO RESUELTO contra una
  persona concreta e identificable (un acusado sin sentencia, un directivo imputado, un sospechoso).
En esos dos casos: tono de medio serio, presuncion de inocencia, y nunca montes el gancho sobre la
culpabilidad de nadie.

En todo lo demas - que sera la inmensa mayoria de los casos del catalogo - "is_sensitive" es false.
Un gusano de 1988 o un fraude ya juzgado NO son sensibles en este sentido: son
historia documentada, y tratarlos como sensibles solo empeora el video sin proteger a nadie.""",
        "structure_block": """Este video es un RECOPILATORIO. Cuentas UN caso por cada bloque
"########## CASO:" que venga en el material, en un solo video. No es una historia larga: son
varias cortas seguidas.

POR QUE ESO CAMBIA LA ESCRITURA ENTERA, y es lo mas importante de estas instrucciones: en una
historia larga puedes tardar dos minutos en arrancar porque el espectador ya ha decidido
quedarse. Aqui no. Cada caso dura entre noventa segundos y tres minutos y compite con el boton
de saltar, asi que cada uno tiene que abrir con lo mas extraño que tenga, no con contexto.

EL ORDEN IMPORTA Y LO DECIDES TU: el caso mas fuerte va el PRIMERO, porque decide si alguien
sigue viendo pasados treinta segundos. El segundo mas fuerte va el ULTIMO, porque es lo que
sostiene hasta el final. Los flojos, en medio. No respetes el orden en que vienen en el
material.

ESTRUCTURA:

0. ENTRADILLA, 15-25 segundos. La promesa del video, no un indice. NO enumeres los casos que
   vienen ("hoy veremos Cicada 3301, Webdriver Torso y..."), eso es un menu y la gente se va al
   que le suena. Abre con el detalle mas raro de TODOS los casos, sin decir de cual es, y
   promete el resto. Ejemplo: "One of these videos was uploaded seventy seven thousand times by
   a channel that has never said a word. Nobody has ever explained why." Di cuantos casos son.

Y despues, POR CADA CASO, en este orden:

1. LA IMAGEN RARA. El dato concreto e incomprensible con el que abre el caso, en la primera
   frase, sin situar nada antes. No "en 2013 aparecio en internet un acertijo"; si "A message
   appeared on an imageboard at three in the morning, and solving it required a book that did
   not exist yet." Anuncia el numero del caso ("Number four.") para que se note el avance:
   saber cuanto queda es la mitad de por que estos videos se ven enteros.

2. QUE ERA EN REALIDAD. Corto. Que es la cosa, cuando, donde, y las dos o tres cifras que dicen
   el tamaño. Nada de inventario.

3. EL GIRO. Lo que lo convirtio en un misterio: lo que alguien encontro, lo que no encajaba, lo
   que se descubrio despues. Aqui van los datos que solo estan en las fuentes de primera mano.
   Es el centro del caso y la razon por la que este video no es el de al lado.

4. QUE SE SABE Y QUE NO. Cierra separando las dos cosas EXPLICITAMENTE: lo que esta
   documentado y lo que sigue sin explicacion. Si el caso se resolvio, dilo - "resuelto" es un
   final, no un fracaso. Si no, di exactamente que es lo que falta por saber.

   ESTO NO ES OPCIONAL Y NO ES SOLO HONESTIDAD: un canal de misterios que insinua sin afirmar
   es un canal que acaba desmonetizado por desinformacion. Nunca sugieras una explicacion que
   las fuentes no sostengan, nunca uses "dicen que" ni "algunos creen", y nunca dejes
   entender que hay algo sobrenatural o una conspiracion si el material no lo documenta.
   Un misterio real contado con precision da mas miedo que uno inflado.

Y AL FINAL, CIERRE de 10-15 segundos: una frase que una los casos - que es lo que tienen en
comun - y la llamada a suscribirse. No resumas lo ya contado.

CUANDO UN CASO TIENE PROTAGONISTA, USALO. Si en el material hay una persona con nombre que
tomo la decision o que lo encontro, el caso se cuenta a traves de ella: "el universitario que
tumbo medio internet" se recuerda y "el ataque de Mirai" no. Si no la hay, o si la unica
identificable esta acusada de algo TODAVIA NO RESUELTO, no la fuerces y no la inventes:
entonces el protagonista es la cosa - la señal, la emision, el puzle - y "que queria" es para
lo que se hizo. Nunca montes un caso sobre la culpa de alguien cuyo proceso siga abierto.

TONO: documental, sobrio y preciso. El drama lo ponen los hechos y las cifras, no los adjetivos.
Tener un protagonista NO es licencia para novelar: no le atribuyas pensamientos, miedos ni
intenciones que no esten en la fuente. Puedes contar lo que hizo y lo que dijo; no lo que sentia.
Si hubo victimas, se mencionan con respeto y sin detalles morbosos: nunca describas agonias,
heridas ni el sufrimiento de personas concretas. No especules sobre causas que la investigacion no
haya establecido - si algo esta en disputa, di que esta en disputa.""",
        "source_block": """===== MATERIAL DE PARTIDA =====
VARIAS fuentes sobre el mismo caso, cada una con su cabecera: el articulo principal, el mismo
articulo en otros idiomas - escritos por separado, no son traducciones -, los articulos de las
personas, los sitios y las maquinas que salen en la historia, y ademas FUENTES DE PRIMERA MANO:
las que cita la enciclopedia, leidas directamente. Vienen etiquetadas por lo que son.

- "registro publico" es un documento oficial: una acusacion, una sentencia, un informe, una
  alerta. Es la unica fuente del dosier con cifras y fechas exactas. Cuando una cifra aparezca
  ahi, esa es la cifra: gana a la enciclopedia y gana a la prensa.
- "reportaje largo" es alguien que fue y lo miro durante meses. De ahi salen las personas, las
  escenas y los detalles que no estan en ningun resumen.
- "prensa" sirve para confirmar una fecha.
- "del archivo" es una pagina que ya no existe, rescatada. En casos de internet suele ser el
  material original: lo que se publico entonces, tal y como se publico.

Estas fuentes son el motivo de que este video pueda contar algo que no cuenta el de al lado: el
resto de canales leen la enciclopedia y ya esta. Usalas.

REGLA ABSOLUTA con ellas: se leen para saber QUE PASO, nunca para copiar COMO se cuenta. Ni una
frase, ni media. Los hechos no son de nadie; la redaccion si, y reproducirla es plagio y ademas
tumba la monetizacion. Cuenta lo que averiguaste con tus palabras.

Como usarlo, porque de esto depende que el video tenga algo que contar:
- CRUZALAS. El dato bueno casi nunca esta en la fuente principal. La version inglesa suele traer
  el detalle tecnico; la del pais donde paso, el juicio y las consecuencias; el articulo de una
  persona, que fue de ella despues. Ahi es donde estan las cifras y los nombres que hacen que un
  video no parezca un resumen de enciclopedia.
- Si dos fuentes se contradicen en una cifra, di la horquilla o quedate con la mas conservadora, y
  nunca presentes como cierto un dato que solo aparece en una y la otra desmiente.
- PROHIBIDO rellenar. Si el material no da para la duracion pedida, haz el video mas corto. Un
  video corto y denso se ve entero; uno largo con paja se abandona a los dos minutos, y eso es
  exactamente lo que hay que evitar.
- Los HECHOS salen de aqui y no de tu memoria: cifras, fechas y nombres tienen que estar en el
  texto. Lo que si tienes que hacer es reordenarlo y contarlo como una historia - NO lo resumas
  fuente a fuente ni copies sus frases:""",
    },
}

# Como se escribe la narracion, que depende del idioma y no es cosmetico: el
# sintetizador pronuncia SEGUN COMO ESTE ESCRITO, y lo que le estorba en
# español (una tilde que falta) no tiene nada que ver con lo que le estorba en
# ingles (una cifra que lee mal).
#
# Esto estaba escrito a fuego en ingles desde que el canal se paso al ingles
# por la mañana, asi que al volver al español la variable no sirvio de nada:
# el prompt seguia diciendo "EN INGLES" y el guion salio en ingles. Un ajuste
# que se puede cambiar por variable pero que el texto del prompt contradice no
# es un ajuste, es una trampa.
_ORTOGRAFIA = {
    "es": """COMO SE ESCRIBE LA NARRACION, MUY IMPORTANTE: el campo "narration" lo lee en voz alta un
sintetizador, y lo lee SEGUN COMO ESTE ESCRITO. Una palabra sin su tilde se pronuncia con el
acento en la silaba equivocada y suena a robot. Escribe en español PERFECTAMENTE acentuado, con
todas las tildes, eñes y signos de apertura: "investigacion" NO, "investigación" SI; "murio" NO,
"murió" SI; "mas" NO, "más" SI; "ano" NO, "año" SI.

Fijate en que ESTAS INSTRUCCIONES estan escritas sin tildes por motivos tecnicos: NO imites ese
estilo, tu texto debe ir correctamente acentuado.

- Nunca uses puntos suspensivos ni guiones para marcar una pausa: el sintetizador no los
  respeta. Usa punto.
- Frases cortas. Nada de frases largas encadenadas con comas: la voz las lee de corrido, sin
  aire, y cansa.""",
    "en": """COMO SE ESCRIBE LA NARRACION, MUY IMPORTANTE: el campo "narration" lo lee en voz alta un
sintetizador, y lo lee SEGUN COMO ESTE ESCRITO. En ingles los problemas no son las tildes sino
estos:

- NUMEROS: escribe con letra los que se leen mal en cifra. "seventy-seven thousand videos", no
  "77,000 videos". Los años si van en cifra (1988, 2013).
- SIGLAS: la primera vez el nombre completo y la sigla despues.
- NADA DE URLS NI DE RUTAS en la narracion.
- Nunca uses puntos suspensivos ni guiones para marcar una pausa. Usa punto.
- Frases cortas. Nada de frases largas encadenadas con comas.""",
}


PROMPT_TEMPLATE = """Eres el guionista y analista del canal de YouTube "{channel_name}" en {language}.

REGLA PRINCIPAL, por encima de todo lo demas: el video SIEMPRE tiene que poder monetizarse en
YouTube. Esto significa: nunca "reused/repetitious content" (resumir el titular con otras
palabras sin aportar nada propio), nunca sensacionalismo en temas sensibles (ver aviso mas abajo),
y nunca contenido que viole derechos de autor.

Cada guion debe leerse como una pieza de analisis periodistico con voz editorial propia, no como
una lectura plana de la fuente.

Identidad del canal: {tone_hint}

{sensitivity_block}

PRESUNCION DE INOCENCIA (obligatorio siempre que haya una acusacion no resuelta): nadie esta
condenado hasta que lo diga una sentencia. Escribe "presunto"/"presunta", "segun la investigacion",
"la fiscalia sostiene", "de acuerdo con el medio que lo publica" - y NUNCA afirmes como hecho probado algo
que solo es una sospecha, ni construyas el gancho sobre la culpabilidad de esa persona. Di
explicitamente en el guion en que punto esta el caso (denuncia, investigacion abierta, juicio
pendiente, condena firme). Presentar a una persona identificable como culpable de algo que no esta
probado desmonetiza el video y ademas es un problema legal real para el canal.

Formato de este video: {format_hint}

{structure_block}

PUNTUACION Y RITMO (la narracion la lee una voz sintetica): los signos son la UNICA forma que
tienes de dirigir como suena. La voz no interpreta lo que quisiste decir, pronuncia lo que
escribiste, y hace pausa donde hay coma o punto y en ningun otro sitio.
- Punto para el golpe. Una frase corta y un punto pesan mas que una coma. "Nobody ever
  answered." suena; "Nobody ever answered and six days later..." se diluye.
- Coma antes del dato que quieres que se oiga: "El casco se abrio, a treinta millas de la costa."
- Si algo es una PREGUNTA, escribela como pregunta de verdad, con ¿ y ? - asi la voz sube al final
  y suena a pregunta. Una pregunta escrita como afirmacion se lee plana y pierde todo el efecto.
  Esto importa especialmente en el gancho, que muchas veces es la pregunta del video.
- Nada de frases largas encadenadas con comas: la voz las lee de corrido, sin aire, y cansa.
- Nunca uses puntos suspensivos ni guiones para marcar una pausa: no los respeta. Usa punto.

{bloque_ortografia}

Estas instrucciones estan escritas en español porque son para ti; TODO lo que va al video -
"narration", "title", "description", "on_screen_highlight", los titulos de las diapositivas y
los "tags" - va EN {language}.

Recuerda: SIEMPRE anclado en los hechos de la noticia original. Nunca inventes conspiraciones ni
afirmes cosas que no esten respaldadas por la fuente.

Fotos reales de personas y sitios concretos: para cada escena, si esa narracion nombra
directamente (a) una persona real identificable por su nombre o su cargo, O (b) un lugar,
edificio, organismo o empresa con nombre propio que casi seguro tenga articulo en Wikipedia con
foto, rellena "photo_subject" con su nombre EXACTO tal y como lo titula la Wikipedia en {language},
para enseñar su foto real en vez de un video generico o una ilustracion inventada.

Ejemplos de este canal: "Ross Ulbricht", "Edward Snowden", "Elizabeth Holmes", "Kevin Mitnick",
"Federal Bureau of Investigation", "National Security Agency", "4chan", "Tor Project",
"Silk Road (marketplace)". Si el nombre existe igual en varios sitios, desambigualo como lo hace
la Wikipedia: "Polybius (urban legend)", no "Polybius".

NUNCA sustituyas por una escena generica algo que tiene nombre propio y es real: si existe, casi
siempre hay foto. Y al reves, NUNCA pongas "photo_subject" para algo que no es una entidad con
articulo propio - "the deep web", "a server room", "an imageboard" no son sujetos de foto: esos
van en "visual_keywords".

EN UN CASO DE SUCESOS TIENES QUE PEDIR TU LAS CARAS, Y ESTO ES OBLIGATORIO.

Cuando un caso es sensible, el sistema NO detecta personas por su cuenta a proposito: nadie debe
poner una cara sin que alguien lo haya decidido. El que lo decide eres tu, aqui, escena por
escena. Si no rellenas "photo_subject" con el nombre de una persona, en ese video no sale ni una
sola cara - y un caso de sucesos sin caras es un expediente leido en voz alta.

Asi que, en la escena donde se la nombra por primera vez, rellena "photo_subject" con:
- la victima, una vez;
- cada persona con SENTENCIA FIRME, diciendo la condena en la narracion;
- los sitios con nombre propio: el pueblo, el juzgado, la ciudad.

Pon el nombre tal cual, aunque creas que esa persona no tiene articulo propio en Wikipedia - que
casi nunca lo tiene. El sistema sabe buscarla dentro del articulo del caso, que es donde suelen
estar estas fotos.

LAS PERSONAS DE UN CASO DE SUCESOS, que es donde hay que afinar:

- La foto de una victima SI se puede usar, una vez y con respeto, cuando el caso va de ella y la
  imagen viene de las fuentes libres de siempre (Wikipedia, Commons). Contar un caso sin poner
  nunca cara a quien le paso lo deja en un expediente. Ponla en la escena donde se la nombra, no
  repetida por todo el video, y NUNCA junto a la narracion de como murio.
- NUNCA imagenes de violencia, del cuerpo, del lugar con restos, ni nada que reconstruya el daño.
  Lo que descarta YouTube no es que aparezca una cara, es lo grafico y lo morboso.
- NUNCA la cara de alguien acusado de algo TODAVIA SIN RESOLVER. Ahi no hay matiz: presuncion de
  inocencia. Condenado por sentencia firme si, con la condena dicha.
- NUNCA generes con IA la imagen de una persona real identificable, ni victima ni condenada. Una
  cara inventada de alguien que existe es un invento presentado como documento.
- Si no hay imagen libre de esa persona, no pasa nada y NO la sustituyas por una parecida: van el
  lugar, el juzgado, los documentos y la cronologia, que es donde este canal es bueno.

Cuando rellenes "photo_subject", rellena tambien "photo_subject_role" en 2-4 palabras: para una
persona, su cargo o titulo actual (ej. "Ministro de Transportes"); para un lugar/institucion, un
descriptor corto (ej. "Universidad publica en Granada") o dejalo vacio si el nombre ya se explica
solo.

MUY IMPORTANTE, el lugar va PRIMERO: si la noticia ocurre en un sitio concreto, la PRIMERA escena
que lo nombre (normalmente el gancho) es la que debe llevar ese "photo_subject", no una escena
posterior. Poner video de archivo generico mientras se nombra el pueblo, y enseñar la foto real del
pueblo dos escenas despues, deja al espectador viendo gente anonima cualquiera justo cuando se le
esta diciendo donde paso todo. Si varias escenas seguidas hablan del mismo sitio, repite el mismo
"photo_subject" en ellas en lugar de dejarlo vacio: es preferible ver el sitio real otra vez que
un video de stock que no es ese sitio.

Deja ambos campos vacios ("") en las escenas que no hablen de ningun lugar ni entidad concreta, y SIEMPRE vacios si la persona
nombrada es una victima de un crimen/tragedia o un particular sin relevancia publica (evita mostrar
la foto real de victimas o personas privadas - esta excepcion es solo para personas, nunca aplica a
lugares).

{bloque_ilustracion}

{bloque_primera_imagen}

Palabras clave visuales ("visual_keywords"): RELLENALAS SIEMPRE, en TODAS las escenas, tambien
cuando ya hayas puesto "photo_subject" o "ai_image_prompt". Son la red de seguridad: si la foto real
no aparece o la ilustracion falla, esto es lo unico que queda, y una escena que llega aqui sin nada
acaba mostrando el clip generico de relleno - en el primer video del Titanic, dos escenas acabaron
enseñando un plato de informativos. Si la escena ya tiene foto real o ilustracion, estas palabras
simplemente no se usan; no cuestan nada y evitan ese desastre. tienen que representar visualmente LO QUE SE DICE EN ESA FRASE CONCRETA, no un tema
generico de todo el video. Antes de escribirlas, identifica la accion, objeto o entorno mas
concreto que menciona ESA narracion en particular, y descríbelo en ingles, 2-5 palabras, de forma
que exista de verdad en un banco de video de stock (Pexels). Ejemplos: si la narracion dice "el
banco central subio los tipos de interes", mejor "central bank building exterior" que algo vago
como "finance concept"; si dice "cientos de personas protestaron en la calle", mejor "crowd protest
street march" que "social unrest". Evita conceptos abstractos que no se pueden filmar (mal:
"government pressure", "economic uncertainty", "political tension"). No incluyas nombres propios de
personas, empresas o lugares con nombre propio (para eso estan "photo_subject" y "ai_image_prompt")
- en su lugar
describe el TIPO de escena/objeto/entorno, pero con la maxima especificidad posible dentro de eso
(mejor "tech startup office workspace" que "office"; mejor "riot police street clash" que "police").
MUY IMPORTANTE - variedad: dos escenas del mismo guion NUNCA deben llevar las mismas palabras clave
o describir la misma imagen generica, aunque el tema de fondo sea el mismo (ej. no repitas "press
conference" en varias escenas de una noticia politica) - cada escena debe aportar una imagen
distinta, o el video se siente repetitivo y aburrido.
MUY IMPORTANTE - sitio correcto: cuando la escena sea de justicia, policia, gobierno o
cualquier imagen institucional generica, di SIEMPRE el pais real del caso dentro de las palabras
clave ("new york federal courthouse", "london police officer", "moscow radio tower"). NUNCA dejes
terminos sin pais como "courthouse", "police car" o "government building": los bancos de stock
devuelven casi siempre imagenes de Estados Unidos para esos terminos, y en un caso ruso o japones
queda mal y confunde. La mayoria de estos casos son de Estados Unidos y ahi coincide, pero
comprueba caso por caso en vez de darlo por hecho.

DIAPOSITIVAS DE DATOS ("slide"): son graficos del canal, dibujados con su tipografia y sus
colores, que se CONSTRUYEN punto por punto mientras hablas. Existen porque hay escenas que no
tienen nada que fotografiar - no hay una foto de un programa copiandose entre ordenadores, ni de
una cifra - y sin diapositiva esas escenas acaban con video de stock generico (un teclado, una
sala de servidores) que no dice nada y aburre.

Usa una diapositiva cuando la escena tenga DATOS o SECUENCIA: cifras, fechas, una enumeracion de
causas, un antes y un despues. NO la uses para ambiente ni para emocion, y NUNCA en una escena
que ya tenga "photo_subject" con una persona: la cara real de alguien siempre gana.

Pon una diapositiva cada 5 o 6 escenas, no en todas: si todo es diapositiva, ninguna destaca.
En un video largo eso son entre 8 y 11; en un Short, una o ninguna. Reparte los datos entre ellas en lugar de acumularlos en una - una diapositiva cuenta
UNA idea. Y escribe los puntos cortos, de una linea: son para leerse de un vistazo mientras
hablas, no para leerse en voz alta.

Cuatro tipos, cada uno con su forma exacta:

  "slide": {{"tipo": "cifra", "valor": "6.000", "unidad": "ordenadores infectados",
             "pie": "una frase corta que le da sentido a la cifra"}}
      Para UNA cifra que importe. "valor" va solo con el numero y su separador de miles;
      la unidad y el pie van aparte. Es el tipo que mas se usa.

  "slide": {{"tipo": "cronologia", "titulo": "Tres días de noviembre",
             "puntos": ["2 nov 1988, 20:30 - se suelta el gusano",
                        "3 nov, madrugada - cae Berkeley"]}}
      Para lo que pasa en orden. Entre 3 y 5 puntos, cada uno "fecha - qué pasó" con un guion
      separando las dos partes. Las fechas cortas.

  "slide": {{"tipo": "lista", "titulo": "Por dónde entraba",
             "puntos": ["un fallo en sendmail", "contraseñas débiles"]}}
      Para causas, errores, consecuencias. Entre 2 y 5 puntos.

  "slide": {{"tipo": "barras", "titulo": "Coste de la limpieza, en dólares",
             "puntos": [{{"etiqueta": "Gusano Morris (1988)", "valor": "10000000"}},
                        {{"etiqueta": "WannaCry (2017)", "valor": "4000000000"}}]}}
      Un GRAFICO DE BARRAS, para comparar magnitudes: costes, numero de afectados, duracion.
      Entre 2 y 5 barras (con una sola no hay nada que comparar). "valor" va solo con el numero,
      sin puntos, sin comas y sin simbolos - la UNIDAD va en el titulo, no en cada barra.

  "slide": {{"tipo": "proporcion", "titulo": "Cuanto internet cayo", "parte": "10",
             "de_cada": "de todos los ordenadores conectados en 1988",
             "pie": "Unas 6.000 maquinas de las 60.000 que existian."}}
      Para UNA parte de un todo. "parte" es el porcentaje, solo el numero. Usalo cuando la
      noticia diga "el X% de" algo; si solo tienes la cifra absoluta, usa "cifra".

  "slide": {{"tipo": "comparacion", "titulo": "Lo que quería y lo que hizo",
             "izquierda": "contar cuántas máquinas había",
             "derecha": "tumbar el diez por ciento de la red"}}
      Para dos cosas enfrentadas: lo previsto contra lo ocurrido, lo declarado contra lo probado,
      el antes contra el despues.

Todo el texto de la diapositiva va EN {language}: se lee en pantalla, en el mismo idioma que se
esta narrando. Un rotulo en otro idioma que la voz canta muchisimo.

En las escenas que no lleven diapositiva, pon "slide": null. No inventes cifras ni fechas para
poder poner una: si la escena no tiene datos en la noticia, no lleva diapositiva. Esto vale
DOBLE para "barras" y "proporcion": un grafico con un numero inventado miente con mucha mas
autoridad que una frase, porque parece medido. Si solo tienes una de las dos cifras que hacen
falta para comparar, usa "cifra" y no un grafico.

Texto destacado en pantalla ("on_screen_highlight"): para cada escena, un texto corto EN ESPAÑOL
(3 a 6 palabras) con el dato o hecho mas concreto y verificable de esa narracion, para reforzar
visualmente el mensaje cuando la escena termine usando un video generico de stock (sin foto real
de nadie). Debe ser un dato factual de la noticia, nunca una opinion ni relleno. Ejemplos: si la
narracion dice "el paro subio al 12% este trimestre", "on_screen_highlight": "Paro: 12% este
trimestre"; si dice "mas de tres mil personas fueron desalojadas", "on_screen_highlight": "3.000
personas desalojadas". Si la narracion de esa escena concreta NO da ningun dato factual o hecho
concreto (por ejemplo, es una transicion, una reflexion, una pregunta abierta o la llamada a
suscribirse), deja el campo como cadena vacia ("") en vez de forzar un texto vago o generico como
"una ley" o "el analisis" - es preferible no mostrar nada a mostrar un texto que no aporta
informacion real.

PRIORIZA SIEMPRE LAS CIFRAS. Este texto puede acabar ocupando la pantalla entera, asi que tiene que
sostenerse solo, sin la voz. Una cantidad, un plazo, una fecha, un porcentaje o un numero de
afectados se lee de un vistazo y se recuerda; un resumen de lo que acaba de decirse no aporta nada
porque el espectador ya lo esta oyendo. Si la escena contiene un numero, ESE es el texto destacado.
Ejemplo real de lo que NO hay que hacer: en una noticia sobre una condena de 194.000 euros a un
organismo publico, el texto elegido fue "Incumplio riesgos laborales" - una parafrasis de la propia
narracion. Lo correcto era "194.000 euros de indemnizacion": la cifra es lo que sorprende y lo que
se retiene. Entre un dato con numero y uno sin el, elige siempre el que lleva numero.

Requisitos de SEO para YouTube (importante, esto determina si el video se encuentra en buscador y
sugeridos):
- "title": lleva SIEMPRE un numero o una promesa de tiempo. Es la forma del nicho, medida en
  los canales que funcionan, y no es decorativa: el numero dice cuanto dura el compromiso
  ("son cuatro cosas, no una clase") y la promesa de tiempo dice lo mismo de otra manera.
  Maximo 90 caracteres, en {language}, con gancho pero sin exagerar (nada de MAYUSCULAS sostenidas
  ni "you won't believe").
  * CON NUMERO: "4 Internet Mysteries That Have Never Been Solved", "5 Broadcasts Nobody Can
    Explain". El numero es el de casos que cuentas de verdad.
  * CON PROMESA DE TIEMPO: "The Internet's Strangest Unsolved Cases, Explained In 9 Minutes".
  * Mejor aun, las dos: "4 Unexplained Internet Mysteries, Explained In 8 Minutes".
  * NUNCA empieces por un nombre propio seguido de dos puntos. "Cicada 3301: the puzzle that..."
    es un encabezado de enciclopedia y no le dice nada a quien no sepa ya lo que es.
  * Si una cifra concreta del material sostiene el titulo, pesa mas que cualquier adjetivo:
    "77,000 Videos" dice mas que "Bizarre".
  Los nombres propios de los casos NO se pierden: van en "tags" y en las primeras frases de
  "description", que es de donde YouTube saca las palabras clave. El titulo esta para que
  alguien haga clic, no para indexar.
- "description": empieza con 1-2 frases que repitan de forma natural la palabra clave principal
  del titulo (esto es lo que se muestra en resultados de busqueda), sigue con 2-3 frases de
  contexto, y termina con 3 a 5 hashtags relevantes (formato #Palabra, sin espacios) mas una
  llamada a suscribirse a {channel_name}.
- "tags": genera entre 10 y 15 palabras clave/frases de busqueda reales que la gente usaria en
  YouTube sobre este tema, mezclando: 2-3 amplias (el tema general, ej. "inteligencia artificial"),
  4-6 especificas (nombres, lugares, entidades concretas de la noticia), y 3-5 relacionadas con el
  tipo de contenido. EN {language}, que
  es donde busca esta audiencia. Sin duplicados,
  sin almohadillas aqui (van solo en la descripcion).
{shorts_seo_hint}

MUY IMPORTANTE - formato del JSON: NUNCA uses comillas dobles (") dentro del texto de ningun campo.
Una sola comilla doble sin escapar rompe el JSON entero y el video no se llega a generar. Si necesitas
entrecomillar algo (el nombre de una ley, una cita, un termino), usa comillas simples ('asi') o
angulares (<<asi>>). Tampoco metas saltos de linea dentro de un valor: cada narracion va en una sola
linea.

Devuelve EXCLUSIVAMENTE un JSON con esta forma exacta, sin texto adicional ni markdown.

Y esto literalmente: el PRIMER caracter de tu respuesta tiene que ser una llave de apertura.
Nada antes. Ni
"Voy a seleccionar los casos...", ni "Escribiendo el guion para...", ni un resumen de lo que
has decidido. Las decisiones que tomas - que casos entran, en que orden - se ven en el JSON,
que para eso esta. Un solo parrafo tuyo por delante y el guion entero se tira a la basura
despues de haberse escrito y pagado.
{{
  "title": "titulo optimizado para SEO, ver requisitos arriba",
  "description": "descripcion con hashtags, ver requisitos arriba",
  "is_sensitive": "true o false - true si la noticia trata sobre una muerte, crimen violento, victima identificable, tragedia personal real, o una acusacion/investigacion no probada sobre una persona identificable (ver AVISO DE SENSIBILIDAD arriba), false en cualquier otro caso",
  "tags": ["tag1", "tag2", "... entre 10 y 15 tags"],
  "scenes": [
    {{
      "narration": "EN {language}, el texto que se narra en esta escena",
      "visual_keywords": "palabras clave en ingles para buscar video de stock",
      "photo_subject": "nombre de una persona publica o de un lugar/institucion con nombre propio si aplica, si no, cadena vacia",
      "photo_subject_role": "cargo de la persona o descriptor corto del lugar si photo_subject no esta vacio, si no, cadena vacia",
      "ai_image_prompt": "descripcion en ingles para ilustracion por IA si aplica, si no, cadena vacia",
      "escena": "{bloque_campo_escena}",
      "sonido": "{bloque_campo_sonido}",
      "on_screen_highlight": "EN {language}, texto corto (3-6 palabras) con el dato clave de esta escena, con CIFRA si la escena tiene alguna, ver instrucciones arriba",
      "slide": "objeto con la diapositiva de datos si esta escena la necesita, o null - ver DIAPOSITIVAS DE DATOS arriba"
    }}
  ]
}}

Genera {scene_count_hint} siguiendo la estructura de arriba (gancho, contexto, hecho, analisis,
cierre - el hecho y el analisis pueden ocupar varias escenas). {scene_length_hint} No inventes
datos que no esten en la noticia original: puedes analizar y contextualizar, pero los hechos deben
ser reales.

{source_block}
Titular: {title}
Resumen: {summary}
"""


def _comprobar_plantilla() -> None:
    """Does PROMPT_TEMPLATE still format?

    A literal brace in the prompt is invisible to anyone reading it and blows
    up .format() with "unexpected '{' in field name". It cost a run: a line
    added to tell the model that its reply must start with an opening brace
    contained one, and the whole generation died before it ever reached the
    API - the prompt could not be built at all.

    Checked once at import with empty values, because a template that cannot
    be formatted cannot make a single video and the right moment to find that
    out is the deploy, not the next time somebody presses generate."""
    campos = set(re.findall(r"(?<!\{)\{(\w+)\}(?!\})", PROMPT_TEMPLATE))
    try:
        PROMPT_TEMPLATE.format(**{c: "" for c in campos})
    except (ValueError, KeyError, IndexError) as exc:
        logger.error(
            "PROMPT_TEMPLATE no se puede formatear (%s). Casi seguro es una llave "
            "literal sin escapar: en esta plantilla se escriben {{ y }}. "
            "Mientras esto no se arregle NO se puede generar ningun video.", exc)


_comprobar_plantilla()

_VARIANT_CONFIG = {
    "short": {
        "format_hint": (
            "YouTube Short vertical (9:16). Autoconclusivo y directo, para verse en el feed sin "
            "contexto previo.\n\n"
            "LOS DOS PRIMEROS SEGUNDOS LO DECIDEN TODO. Es lo unico en lo que coincide todo lo "
            "que se ha medido del formato: quien no se engancha en la primera frase desliza, y "
            "el video se entierra. Asi que la ESCENA 1 no situa, no presenta y no dice de que "
            "vamos a hablar - suelta el golpe.\n\n"
            "Empieza por el dato mas raro, la cifra mas bestia o la frase que obliga a preguntar "
            "'¿como?'. Si la escena 1 se puede resumir como 'hoy os cuento X', esta mal escrita.\n\n"
            "  MAL:  'Hoy vamos a hablar del asedio de Baler, en Filipinas.'\n"
            "  BIEN: 'Siguieron defendiendo una iglesia once meses despues de perder la guerra.'\n\n"
            "  MAL:  'La batalla de Lepanto fue un enfrentamiento naval de 1571.'\n"
            "  BIEN: 'En Lepanto remaban encadenados doce mil hombres que no eran soldados.'\n\n"
            "UN SOLO HECHO POR VIDEO. Un Short no es un resumen: es una cosa contada entera. Si "
            "te sobran datos, guardalos - hay mas videos.\n\n"
            "Y LAS CINCO ESCENAS NO SON CINCO DATOS. Cinco frases con cifras no cuentan nada: "
            "son cinco frases con cifras. Cada escena tiene UN TRABAJO y hay que hacerlo:\n\n"
            "  1. EL GOLPE. El hecho que no se cree nadie. Sin fecha, sin sitio, sin contexto: "
            "eso viene despues. Solo lo que paso, dicho de la forma mas seca posible.\n"
            "  2. QUIEN Y CUANDO. AHORA si: el año, el sitio y quienes eran. Una frase, porque "
            "el espectador ya esta enganchado y solo necesita saber donde esta.\n"
            "  3. EL GIRO. Lo que cambio las cosas, o el detalle que lo vuelve raro. Sin esto "
            "no hay historia, hay una ficha.\n"
            "  4. COMO ACABO. El desenlace, concreto. Nada de 'y asi termino aquella epoca'.\n"
            "  5. EL REMATE. La coletilla que cierra la historia: lo que paso despues y no se "
            "espera nadie, o el dato final que deja al espectador con la cara torcida. NO es una "
            "moraleja, NO es un 'suscribete' y NO es una reflexion sobre el paso del tiempo. Si "
            "suena a final de documental de La 2, esta mal.\n\n"
            "Si al leer las cinco seguidas no se entiende una historia con principio y final, "
            "esta mal escrito aunque cada frase sea correcta. Eso fue lo que paso con los "
            "primeros: datos ciertos, ordenados, y sin nada que contar.\n\n"
            "QUE ALGUIEN HABLE, Y QUE DIGA ALGO BUENO. En dos o tres de las cinco escenas "
            "mete DENTRO de la narracion una frase corta que dijera alguien, entre comillas "
            "angulares: «¡Que ardan con ella!». Va dentro del texto narrado, no aparte, porque "
            "la voz la lee y encima aparece un bocadillo de comic justo cuando se dice.\n\n"
            "EL BOCADILLO ES DONDE MAS SE RIE LA GENTE. Es lo unico del video que no dice la voz "
            "narrando en serio: es el personaje hablando por su cuenta. Asi que que diga lo que "
            "esa persona diria de verdad en ese momento - mezquino, cabezota, harto, muerto de "
            "miedo, indignado por algo pequeño -, no una frase de placa conmemorativa.\n\n"
            "  BIEN: «Pues yo de aqui no me muevo.»\n"
            "  BIEN: «¿Y esto quien lo paga?»\n"
            "  BIEN: «Ya te lo dije.»\n"
            "  MAL:  «Hoy comienza una nueva era para el reino.»\n\n"
            "Maximo SIETE palabras: lo que cabe en un globo y se lee de un vistazo. Y que sea "
            "algo que esa persona pudo decir, no una cita historica textual que te inventes. Si "
            "no sabes que dijo nadie en esa escena, no pongas comillas: un bocadillo inventado "
            "en una frase solemne se nota.\n\n"
            "EL TONO: DIVERTIDO. Esto no es un adorno, es lo que decide si alguien se queda "
            "o desliza, y hasta ahora el prompt pedia justo lo contrario.\n\n"
            "LA GRACIA NO LA PONE LA VOZ. La voz narra en serio, formal, como si estuviera "
            "contando algo importante - y encima pasan cosas ridiculas. ESE CONTRASTE ES EL "
            "CHISTE: dicho en serio, el detalle absurdo hace el doble de gracia que si te pones "
            "a hacer el gracioso. Si la narracion lleva guiños, '¡atencion!', exclamaciones o "
            "coletillas de youtuber, suena a pesado y se cae el video.\n\n"
            "DE DONDE SALE LA GRACIA, por orden:\n"
            "  1. EL DETALLE ABSURDO QUE ADEMAS ES VERDAD. Toda historia tiene uno: la cifra que "
            "no tiene sentido, lo que alguien se llevo al huir, la razon ridicula por la que "
            "empezo todo. Si al leer el dosier levantas una ceja, eso va dentro si o si.\n"
            "  2. LA GENTE PORTANDOSE COMO GENTE. Nadie sabia que estaba dentro de la Historia: "
            "discutian por dinero, por vanidad, por no dar su brazo a torcer, por no madrugar. "
            "Los motivos pequeños son los que hacen gracia y ademas son los ciertos.\n"
            "  3. DECIRLO CORTO Y SECO. 'Tardaron once meses en enterarse de que la guerra habia "
            "terminado' tiene gracia. 'Debido a la incomunicacion, la noticia tardo once meses "
            "en llegar' no tiene ninguna. La misma informacion.\n\n"
            "LO QUE NO SE HACE: inventarse un dato porque queda gracioso, meter chistes de "
            "ahora con calzador, reirse de quien lo paso mal - una epidemia, un naufragio o una "
            "ejecucion se cuentan con interes, no con burla - ni explicar la gracia despues de "
            "hacerla.\n\n"
            "Y NO ES PARA NIÑOS. No se simplifica, no se habla como a un crio y no se ponen "
            "tonterias. Es historia de verdad contada por alguien que se lo esta pasando bien "
            "contandola."
        ),
        "duration_hint": "30-40 segundos",
        "scene_count_hint": (
            "EXACTAMENTE 5 escenas, y el guion ENTERO no puede pasar de 85 PALABRAS "
            "de narracion sumando todas. Cuentalas antes de contestar. El primer Short "
            "de este canal pidio 4 o 5 escenas y devolvio 7, con 66 segundos en vez de "
            "35: el numero de escenas no ata, el presupuesto de palabras si"
        ),
        "scene_length_hint": (
            "LA ESCENA 1 NO PUEDE EMPEZAR POR UNA FECHA NI POR UN LUGAR. El primer Short "
            "de este canal abrio con 'En mayo de 1975, en el Sahara...' - o sea situando, "
            "que es justo lo que se prohibe mas arriba. Nada de 'En [año]', 'El [dia]', "
            "'En [sitio]'. Empieza por lo que hicieron o por lo que paso.\n\n"
            "Cada narracion es UNA frase corta y directa de UNAS 17 PALABRAS - nunca dos frases, "
            "nunca una frase larga con comas encadenadas. Con 5 o 6 escenas asi el Short sale en su "
            "duracion. Si una frase se te va larga, recorta adjetivos y contexto, nunca las cifras "
            "ni la causa tecnica."
        ),
        "shorts_seo_hint": (
            '- Incluye "#Shorts" como uno de los hashtags al final de la descripcion (obligatorio '
            "para que YouTube lo clasifique bien como Short)."
        ),
        # El dibujo es el video, no un recurso para cuando no hay foto. La
        # regla de antes - "la ilustracion es para las escenas ABSTRACTAS, si
        # hay algo real va SIEMPRE en photo_subject" - se escribio para un
        # canal de noticias y aqui deja el guion sin un solo dibujo: en
        # historia TODAS las escenas nombran a alguien o algun sitio.
        "bloque_primera_imagen": """LA PRIMERA IMAGEN ES LA PORTADA DEL VIDEO. No exagero: en un Short la miniatura casi no la ve
nadie - lo que la gente ve es el primer segundo del video reproduciendose. Ese primer plano ES la
portada, y decide si se quedan.

Asi que la imagen de la escena 1 tiene que ser EL GANCHO HECHO IMAGEN, de cerca: un sujeto
llenando el encuadre, cara o accion, con algo raro que se entienda de un vistazo. Nada de planos
generales, ni vistas de una ciudad, ni un edificio entero, ni un paisaje. Un plano general dice
"esto es un documental" y el pulgar sigue.

  Narracion: "Heredo cuarenta y cuatro titulos y no le cabian en el carnet."
    BIEN: una anciana diminuta sepultada bajo una montaña de pergaminos y medallas, mirando a
          camara con cara de circunstancias
    MAL:  un palacio sevillano visto desde la calle

  Narracion: "Siguieron defendiendo una iglesia once meses despues de perder la guerra."
    BIEN: la cara de un soldado demacrado asomando entre las tablas de una ventana, de muy cerca
    MAL:  una iglesia pequeña en un pueblo al amanecer

Habia escrito aqui justo lo contrario - que la escena 1 tenia que SITUAR, "la ciudad, el
edificio, el juzgado" - y encima tres parrafos despues de prohibirle a la narracion que situe. El
video abria contando un golpe sobre un plano general de nada.""",
        # El guion ya no describe una imagen para Gemini: ELIGE de unas
        # listas cerradas y el programa la dibuja. Lo que no esta en la
        # lista no se puede dibujar, asi que no se puede pedir.
        "bloque_campo_escena": "objeto con la escena de monigotes, OBLIGATORIO - ver LA ESCENA arriba",
        "bloque_campo_sonido": "uno de [gentio, campana, fuego, pasos, espada, tormenta, mar, monedas, puerta, caballo] o cadena vacia",
        "bloque_ilustracion": """LA ESCENA ("escena"): OBLIGATORIA EN TODAS Y CADA UNA DE LAS ESCENAS.

Este canal se dibuja con MONIGOTES - palotes con cabeza redonda, como los de un canal de
historia contada con dibujos malos a proposito -, y los dibuja el propio programa. Tu no
describes una imagen: eliges de unas listas cerradas. Lo que no este en las listas no se sabe
dibujar, asi que no te inventes nada: si pides "catedral gotica al atardecer" no sale una
catedral, sale un fondo liso.

  "escena": {
    "interior": uno de [monasterio, taberna, salon_trono] - o quitalo y usa "fondo"
    "fondo":    uno de [campo, calle, salon, noche, liso]
    "habla_x":  0.0 a 1.0, donde esta QUIEN HABLA en esta escena (para el bocadillo)
    "figuras":  de 1 a 4 personajes, cada uno:
       "x":        0.12 a 0.88, de izquierda a derecha
       "alto":     0.18 a 0.46 de la pantalla (0.34 normal; 0.26 si hay cuatro)
       "pose":     [de_pie, sentado, en_mesa, brazos_arriba, señala, corriendo]
       "pose_fin": otra pose de la misma lista: el personaje SE MUEVE de una a otra
       "gesto":    [neutro, sorpresa, contento, enfadado, grito]
       "gorro":    [corona, comandante, tricornio, sombrero, casco, mitra, monje, boina,
                    marinero] - o quitalo si no lleva
       "espejo":   true para que mire hacia la izquierda
    "tachados": hasta 3, cada uno {"x":.., "y":.., "tam":..}: una cruz roja encima de algo,
                para decir "prohibido" o "se acabo" de un vistazo
  }

COSAS QUE HACEN QUE ESTO FUNCIONE:

- PON "pose_fin" CASI SIEMPRE. Es lo que hace que el plano se mueva en vez de ser una foto
  quieta, y es gratis. Un monigote que pasa de "de_pie" a "brazos_arriba" esta celebrando o
  indignandose; de "corriendo" a "de_pie" esta llegando; de "de_pie" a "sentado" se rinde.
- EL GORRO ES QUIEN ES. No hay caras parecidas ni hace falta: la corona es el rey, la mitra el
  obispo, el morrion el conquistador, el tricornio el del XVIII. Si en una escena hay un rey y
  un subdito, ponle corona a uno y al otro nada, y ya se entiende.
- MISMO PERSONAJE, MISMO GORRO Y MISMO SITIO EN TODAS LAS ESCENAS donde salga. Es lo que hace
  que las cinco escenas sean UNA historia y no cinco dibujos sueltos.
- LA CARA CUENTA EL CHISTE. "grito" y "enfadado" valen mas que cualquier adjetivo de la
  narracion. Una escena entera de gente con cara "neutro" no la mira nadie.
- "habla_x" tiene que coincidir con la x del que dice la frase entrecomillada, o el bocadillo
  saldra apuntando a otro.

EJEMPLO, para la frase «El rey prohibio las capas largas y Madrid ardio tres dias»:
  {"interior": "salon_trono", "habla_x": 0.30,
   "figuras": [{"x":0.30,"alto":0.40,"pose":"señala","pose_fin":"brazos_arriba",
                "gesto":"enfadado","gorro":"corona"},
               {"x":0.70,"alto":0.36,"pose":"de_pie","pose_fin":"sentado",
                "gesto":"sorpresa","espejo":true}]}

Y EL SONIDO ("sonido"): uno de [gentio, campana, fuego, pasos, espada, tormenta, mar, monedas,
puerta, caballo], o cadena vacia si ninguno pega. Va MUY por debajo de la voz, solo para que el
plano no este mudo: "gentio" en un motin, "mar" en un naufragio, "campana" en un monasterio. No
lo fuerces - un efecto que no pega distrae mas que el silencio.""",
    },
    "long": {
        "format_hint": "Video horizontal (16:9) extendido para YouTube, no es un Short.",
        # Fifteen minutes because that is where the market study put the
        # cliff, not because longer is better: the channels that clear it have
        # enough material to hold it. Fifteen minutes of narration is about two
        # thousand words, which at forty words a scene is fifty scenes of
        # eighteen seconds - a documentary's pace, not a montage's.
        "duration_hint": "unos 15 minutos",
        "scene_count_hint": "entre 45 y 55 escenas",
        "scene_length_hint": (
            "Cada narracion puede tener hasta 2-3 frases; profundiza mas que en un Short: añade "
            "ejemplos concretos, cifras adicionales, comparaciones, cronologia mas detallada y "
            "matices en el analisis."
        ),
        "shorts_seo_hint": "",
        # En horizontal se queda como estaba: un video largo con foto real de
        # Wikipedia donde la hay es correcto, y dibujarlo entero costaria
        # catorce ilustraciones.
        "bloque_primera_imagen": """LA PRIMERA ESCENA TIENE UN TRABAJO DISTINTO. Su imagen no esta ahi para ilustrar la frase: esta
ahi para que el espectador no se vaya. Asi que en la escena 1 las "visual_keywords" tienen que
SITUAR - la ciudad, el edificio, el juzgado, la casa, una cara - y no el detalle literal del sitio
donde pasaron los hechos. El video del caso Asunta abrio con un camino de tierra en un bosque,
porque ahi aparecio el cuerpo: correcto como dato y pesimo como primer plano, porque quien no
conoce el caso ve un camino cualquiera y se va. Ese detalle es bueno MAS TARDE, cuando ya se ha
contado que paso y el espectador sabe por que esta mirando un camino.""",
        "bloque_campo_escena": "null, este formato no usa monigotes",
        "bloque_campo_sonido": "cadena vacia",
        "bloque_ilustracion": """Ilustracion por IA ("ai_image_prompt"): es para las escenas ABSTRACTAS, las que no tienen nada real
que enseñar. Si la escena nombra una persona, un lugar o una institucion con nombre propio, va
SIEMPRE en "photo_subject" y nunca aqui: una foto real de Wikipedia es gratis y siempre mejor, y una
ilustracion de un sitio real identificable se nota que esta inventada. Pero cuando la frase habla de
una idea, un proceso, una cifra o una consecuencia y no hay nada que fotografiar, una ilustracion
que diga EXACTAMENTE eso vale mucho mas que un clip de archivo generico de gente tecleando: es
precisamente ahi donde el video se llena ahora de imagenes que no pegan, y esto lo arregla.

Lo que escribes es SOLO EL CONTENIDO de la imagen, en ingles, en una frase: que se ve, quien o que
es el sujeto, que esta pasando. NO describas el estilo, ni colores, ni iluminacion, ni "editorial
illustration", ni "news graphic style" - el estilo lo pone el sistema automaticamente e igual para
todas, y si lo describes tu cada escena saldra de su padre y de su madre y el video parecera un
collage.

La ilustracion tiene que representar LO QUE DICE ESA FRASE CONCRETA, no el tema general del video.
Antes de escribirla, pregunta: "si alguien ve esta imagen sin sonido, entiende la frase que estoy
narrando?". Si la respuesta es no, esta mal.
- Narracion: "la banca gano un 30% mas mientras las hipotecas subian" -> "a rising stack of coins
  beside a small house weighed down by an oversized percentage arrow"
- Narracion: "el algoritmo decide quien recibe la ayuda sin que nadie lo revise" -> "a faceless
  automated machine sorting human silhouettes into two separate groups"
- MAL (vago, no dice nada): "technology concept", "economic uncertainty", "political tension"

Nunca pidas personas reales reconocibles, y en este canal eso es literal: nada de caras de
victimas, de desaparecidos ni de acusados, ni siquiera dibujadas. Para representar una
organizacion usa el COLOR o un objeto asociado, nunca su logo: estos modelos los dibujan
deformados y canta muchisimo.

Deja "ai_image_prompt" vacio ("") cuando la escena si tenga algo real que enseñar o cuando un clip
de archivo concreto la represente bien.""",
    },
}


def _solo_el_json(texto: str) -> str:
    """The JSON object out of a reply that may have prose around it.

    The compilation format made the model start thinking out loud before the
    JSON - "Voy a seleccionar 4 casos de este material..." - and json.loads
    fails on the first character. Three attempts died that way, each one
    paying for a full script, and the scripts themselves were fine.

    The usual fix for this is an assistant prefill, which the current models
    reject with a 400, so the parser gives instead: the object runs from the
    first brace to the last, and anything outside it is the model clearing
    its throat. This cannot rescue genuinely broken JSON - a bad quote inside
    a string still fails, as it should - it only stops a preamble from
    throwing away work that was already done and already paid for.
    """
    inicio = texto.find("{")
    final = texto.rfind("}")
    if inicio == -1 or final <= inicio:
        return texto
    if inicio > 0:
        logger.info("La respuesta traia %s caracteres de prologo antes del JSON; recortados.",
                    inicio)
    return texto[inicio:final + 1]


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
    return text.strip()


# Generous headroom: a response that doesn't fit is cut off mid-JSON and
# fails to parse. A long video is 16-24 scenes, each carrying a narration
# plus five other fields, so the old 10000 was not a comfortable margin.
# (This was NOT what broke the CIS story - that one failed at ~800 tokens,
# on an unescaped quote inside a string. See the prompt's quoting rule.)
# Headroom for the model to reason before writing, not a target length: the
# reply itself is a few hundred tokens, and an unused ceiling costs nothing.
# It was 8000 for a Short, and a harder prompt walked straight into it - three
# attempts in a row spent the entire budget thinking and returned no text at
# all, which reads as a broken API rather than as "give me more room". Raised
# to 12000, and a Short over a full dossier hit that too. There is no reason
# for the Short to have the smaller ceiling: the harder the story is to
# compress, the more room the model needs, so a sixty-second video can need
# MORE thinking than a five-minute one, not less. One number for both.
# Raised with the long video's length: fifty scenes of six fields each is
# several thousand tokens of JSON before the model has thought about
# anything, and a reply cut off mid-object does not parse at all. An
# unused ceiling costs nothing.
_MAX_TOKENS = 32000
_MAX_ATTEMPTS = 3

# How much of the dossier each variant is allowed to read.
#
# research.build_dossier is sized for a long narration: thirty thousand
# characters and up, across several sources. A Short is five or six sentences.
# Measured on "Presa de Tous": a 31,566-character dossier sent to the Short
# spent the whole ceiling reasoning on the first attempt and returned nothing,
# then succeeded on the second - $0.33 for a video that costs $0.10. Raising
# the ceiling stops it failing; this stops it paying to read what it cannot
# use.
#
# The trim keeps whole sources instead of cutting at a character count. The
# sources are labelled so the model can cross them, and a source that stops
# mid-sentence is worse than an absent one: it reads as a document that
# contradicts itself rather than as one that ends.
_SOURCE_BUDGET = {"short": 9000, "long": None}

# The header build_dossier writes in front of each source.
_FUENTE = re.compile(r"(?m)^===== FUENTE \d+ · .*? =====$")


def _trim_sources(summary: str, budget: int | None) -> str:
    """The head of the dossier, cut on a source boundary where there is one."""
    if budget is None or len(summary) <= budget:
        return summary
    # Kept for the log: below, `summary` may be narrowed to the main source
    # before it is cut, and reporting that as the original would understate
    # how much was dropped.
    entero = len(summary)
    marcas = [m.start() for m in _FUENTE.finditer(summary)]
    if marcas:
        # Where each source ends: the next one's header, or the end of the text.
        finales = marcas[1:] + [len(summary)]
        caben = [fin for fin in finales if fin <= budget]
        if caben:
            recortado = summary[: max(caben)].rstrip()
            logger.info(
                "Dosier recortado para la variante corta: %s de %s caracteres, "
                "%s fuentes de %s.",
                len(recortado), entero, len(caben), len(marcas),
            )
            return recortado
        # Not even the main article fits. Everything else goes, and the main
        # one is cut below - its opening paragraphs are where a sixty-second
        # story is anyway.
        summary = summary[: finales[0]].rstrip()
        if len(summary) <= budget:
            return summary
    # A single block longer than the budget: cut it between paragraphs, and
    # fall back to the raw count only if that would throw away most of it.
    corte = summary.rfind("\n\n", 0, budget)
    recortado = summary[: corte if corte > budget // 2 else budget].rstrip()
    logger.info(
        "Dosier recortado para la variante corta: %s de %s caracteres (una sola fuente).",
        len(recortado), entero,
    )
    return recortado





# Una escena 1 que empieza situando. Se comprueba en codigo porque pedirlo en
# el prompt no basto: el primer Short del canal abrio con "En mayo de 1975, en
# el Sahara..." teniendo la regla escrita tres veces mas arriba.
#
# Y se comprueba ANTES de narrar, que es donde esta el dinero: un guion malo
# cuesta veinte centimos de reescritura, y uno malo ya narrado cuesta mil
# creditos y un video que nadie va a ver.
_ABRE_SITUANDO = re.compile(
    r"^\s*(en|el|la|los|las|durante|hacia|a\s+finales|a\s+principios|corria)\s+"
    r"(el\s+|la\s+)?(\d{1,4}\b|\w+\s+de\s+\d{3,4}|[A-ZÁÉÍÓÚÑ])",
    re.IGNORECASE,
)


_PALABRAS_MAXIMAS_SHORT = 110


def _que_le_pasa_al_guion(script: dict, variant: str = "long",
                          exigente: bool = True) -> str | None:
    """What is wrong with this script, or None when nothing is.

    Checked before anything expensive runs. Everything downstream reads
    scene["narration"] directly - three separate places do - so a scene
    without it is not a worse video, it is a crash, and the crash lands after
    the narration has been paid for.

    Slides are deliberately NOT checked: slides.py ignores a type it does not
    know and catches its own drawing errors, so a bad slide costs a slide, not
    a video."""
    escenas = script.get("scenes")
    if not isinstance(escenas, list) or not escenas:
        return "no trae ninguna escena"
    for i, escena in enumerate(escenas, 1):
        if not isinstance(escena, dict):
            return f"la escena {i} no es un objeto"
        narracion = escena.get("narration")
        if not isinstance(narracion, str) or not narracion.strip():
            return f"la escena {i} no tiene narracion"
    # Las de mas abajo son de CALIDAD, no de que el video reviente: un Short
    # de sesenta segundos sin bocadillos es peor que uno bueno, pero es
    # infinitamente mejor que ningun video. En el ultimo intento se aceptan.
    #
    # Esto lo aprendi tirando 0,37 $ y una tanda entera: puse la regla de los
    # bocadillos como obligatoria y el tema que toco fue 'Mundo islamico', un
    # articulo enciclopedico donde no habla nadie. Tres guiones pagados,
    # ningun video. Una regla nueva sin pensar que pasa cuando no se puede
    # cumplir.
    if variant == "short" and exigente:
        primera = (escenas[0].get("narration") or "").strip()
        if _ABRE_SITUANDO.match(primera):
            return (f"la escena 1 abre situando ({primera[:40]}...), que es lo que "
                    "mata un Short en los dos primeros segundos")
        palabras = sum(len((e.get("narration") or "").split()) for e in escenas)
        if palabras > _PALABRAS_MAXIMAS_SHORT:
            return (f"{palabras} palabras de narracion para un Short, que son "
                    f"unos {palabras / 2.2:.0f} segundos; el tope son "
                    f"{_PALABRAS_MAXIMAS_SHORT}")
        # Y QUE TODAS LLEVEN DIBUJO. Esto es lo que fallo en el #81: el canal
        # entero se monto para ser dibujado, se subio el cupo a ocho
        # ilustraciones y el video salio con cero, porque el guion no pidio ni
        # una. Una escena sin "ai_image_prompt" no da un video un poco peor:
        # da una foto de stock generica, que es de lo que se queja ella desde
        # el primer dia. Se comprueba AQUI, que es antes de pagar la voz.
        # Y QUE ALGUIEN HABLE DE VERDAD. El #82 salio con sus cinco dibujos y
        # con CERO bocadillos, porque el prompt los pedia y nada comprobaba
        # que estuvieran. Es el mismo fallo que llevo repitiendo todo el dia:
        # escribir una regla en el prompt y no comprobar en codigo que se ha
        # cumplido. Se mira con la MISMA funcion que luego dibuja el globo,
        # asi que lo que pasa aqui es exactamente lo que se vera en pantalla.
        hablan = sum(1 for e in escenas if bocadillos.cita_de(e.get("narration", "")))
        if not hablan:
            return ("no habla nadie: ninguna escena trae una frase entre comillas "
                    "angulares, asi que el video no tendra ni un bocadillo")

        # Y QUE TODAS TRAIGAN SU ESCENA DE MONIGOTES. Una escena sin dibujo
        # no da un video un poco peor: cae en la cadena vieja y acaba en una
        # foto de archivo generica, que es de lo que se queja ella desde el
        # primer dia. Se comprueba con la MISMA funcion que luego dibuja, asi
        # que lo que pasa aqui es exactamente lo que se va a ver.
        sin_dibujo = [i for i, e in enumerate(escenas, 1)
                      if not isinstance(e.get("escena"), dict)
                      or not (e["escena"].get("figuras") or e["escena"].get("interior")
                              or e["escena"].get("fondo"))]
        if sin_dibujo:
            cuales = ", ".join(str(i) for i in sin_dibujo)
            return (f"las escenas {cuales} no traen 'escena'. Este canal se dibuja con "
                    "monigotes: una escena sin dibujo acaba en foto de archivo generica")
        # Y que lo que pidan se sepa dibujar. No se rechaza por esto - el
        # vocabulario se limpia solo -, pero si TODAS las figuras de un guion
        # cayeran al monigote por defecto seria que el modelo no ha entendido
        # el formato, y eso si hay que reintentarlo.
        from . import monigotes
        reconocidas = sum(
            1 for e in escenas
            for f in monigotes.limpia(e["escena"])["figuras"]
            if f["pose"] != "de_pie" or f["gesto"] != "neutro" or f["gorro"])
        if not reconocidas:
            return ("ninguna figura de ninguna escena trae pose, gesto ni gorro que se sepa "
                    "dibujar: saldrian cinco monigotes de pie mirando al frente")
    if not isinstance(script.get("tags"), list):
        return "las etiquetas no son una lista"
    for clave in ("title", "description"):
        if not isinstance(script.get(clave), str) or not script[clave].strip():
            return f"falta {clave}"
    return None


def _log_accent_rate(script: dict, variant: str) -> None:
    """Reports how accented the narration came out.

    The prompt asks for correctly accented Spanish because the speech
    synthesiser pronounces from the spelling, and an unaccented word lands its
    stress on the wrong syllable. Whether the model actually complied is not
    otherwise visible until the video is listened to."""
    if NARRATION_LANG != "es":
        # Not a Spanish script, so there is nothing to measure. Running it
        # anyway would warn on every single generation and train everyone to
        # ignore the one warning that matters.
        return
    text = " ".join(scene.get("narration", "") for scene in script.get("scenes", []))
    acentuadas, palabras, tasa = tasa_de_acentos(text)
    if not palabras:
        return
    message = "Guion: %.1f%% de palabras acentuadas (%s de %s)"
    if tasa < MIN_TASA_ACENTOS:
        logger.warning(
            message + " - demasiado pocas, la voz pronunciara mal. Variante '%s'.",
            tasa * 100, acentuadas, palabras, variant,
        )
    else:
        logger.info(message, tasa * 100, acentuadas, palabras)


# What a script may take from its dossier without padding.
#
# Measured: today's six-and-a-half-minute video used 15% of a 5,629-word
# dossier and did not pad. Fifteen minutes from the same source would need
# 35%. Thirty is the line between them - enough to make a long video where
# the material is there, short of the point where the model starts saying
# the same thing twice because it has been asked for words it does not have.
_FRACCION_APROVECHABLE = 0.30

# The floor is not a target, it is an admission: below this there is not
# enough for a long video at all, and the honest output is a shorter one.
#
# The ceiling came down from fifteen to ten when the compilation format and
# the open-web sources landed together, for two reasons. With five cases at
# twenty-five thousand characters each there is always more material than
# fifteen minutes can hold, so the adaptive sizing was pinned at the ceiling
# and had stopped adapting - every video would come out the same length
# whatever was found. And ten minutes is two minutes a case instead of
# three, which is where this niche's compilations actually sit.
#
# It also costs about 7,500 credits to narrate instead of 11,300, and that
# matters while the chain is still being proved: the first run of something
# new is better discovered cheap.
_MINUTOS_MINIMO, _MINUTOS_MAXIMO = 6, 10
_PALABRAS_POR_MINUTO_HABLADO = 132
_PALABRAS_POR_ESCENA = 40


def _tamano_por_material(summary: str) -> tuple[str, str, float]:
    """How long this case can actually hold, from how much was found on it.

    Fixing the length at fifteen minutes was a mistake I made and caught by
    doing the arithmetic: the market study says fifteen minutes is where the
    audience is, but a case with two thousand words behind it cannot fill
    fifteen minutes with anything but repetition - and a padded fifteen is
    worse than an honest eight, for the viewer and for the channel.

    So the study sets the ceiling and the dossier sets the length."""
    palabras = len(summary.split())
    minutos = palabras * _FRACCION_APROVECHABLE / _PALABRAS_POR_MINUTO_HABLADO
    minutos = max(_MINUTOS_MINIMO, min(_MINUTOS_MAXIMO, minutos))
    escenas = round(minutos * _PALABRAS_POR_MINUTO_HABLADO / _PALABRAS_POR_ESCENA)
    logger.info(
        "Material: %s palabras de dosier -> video de ~%.0f min (%s escenas).",
        palabras, minutos, escenas,
    )
    return (f"unos {minutos:.0f} minutos",
            f"entre {escenas - 3} y {escenas + 3} escenas",
            minutos)


# Lo que un Short de monigotes ya NO usa, y que seguia entrando entero en sus
# instrucciones: como buscar fotos reales, que palabras clave darle al banco
# de video de archivo y como construir una diapositiva de datos. Son casi once
# mil caracteres que el modelo tiene que leer y ponderar para nada.
#
# Y NO ES SOLO EL TAMAÑO DEL PROMPT: el #84 gasto 14.465 tokens de SALIDA
# donde el #81 gasto 7.755. El doble de pensar, 0,36 $ de guion frente a 0,12.
# O sea que el ahorro de quitar las imagenes de IA - 12 centimos - se lo
# comio con creces el guion. Se lo vendi como ahorro sin mirarlo.
#
# Se recorta sobre el prompt YA CONSTRUIDO, no moviendo texto entre
# plantillas: esas secciones llevan {language} y {channel_name} dentro, y
# sacarlas a una variable las dejaria sin sustituir en el video largo.
_CAMPOS_MUERTOS_EN_SHORT = (
    '      "visual_keywords":', '      "photo_subject":',
    '      "photo_subject_role":', '      "ai_image_prompt":', '      "slide":',
)

_FUERA_DEL_SHORT = (
    # La seccion de fotos acaba donde empieza la de monigotes. Puse aqui
    # "Ilustracion por IA", que es como acababa ANTES de cambiar el bloque, y
    # en el Short ya no existe: salto el aviso y se quedaron 4.400 caracteres
    # dentro. Para eso esta el aviso.
    ("Fotos reales de personas y sitios concretos", 'LA ESCENA ("escena")'),
    ("Palabras clave visuales", "DIAPOSITIVAS DE DATOS"),
    ("DIAPOSITIVAS DE DATOS", "Texto destacado en pantalla"),
)


def _sin_lo_que_ya_no_usa(prompt: str) -> str:
    """Las instrucciones de un Short, sin lo que quedo muerto al dibujar.

    Si alguna marca deja de existir se avisa y se sigue: un prompt un poco mas
    largo es un problema de dinero, y quedarse sin guion es un problema de
    verdad.
    """
    fuera = 0
    for desde, hasta in _FUERA_DEL_SHORT:
        i = prompt.find(desde)
        j = prompt.find(hasta, i + 1) if i >= 0 else -1
        if i < 0 or j <= i:
            logger.warning("No encuentro la seccion %r para quitarla del Short.", desde[:40])
            continue
        fuera += j - i
        prompt = prompt[:i] + prompt[j:]
    # Y los campos del esquema que ya nadie lee. Son cinco POR ESCENA que el
    # modelo tiene que decidir y escribir, y la salida es lo caro.
    lineas, campos = [], 0
    for linea in prompt.split("\n"):
        if any(linea.startswith(c) for c in _CAMPOS_MUERTOS_EN_SHORT):
            campos += 1
            continue
        lineas.append(linea)
    prompt = "\n".join(lineas)
    if fuera or campos:
        logger.info("Guion (short): fuera %s caracteres de instrucciones muertas y "
                    "%s campos del esquema que ya no se leen.", fuera, campos)
    return prompt


def generate_script(news_item: dict, variant: str = "long") -> dict:
    if variant not in _VARIANT_CONFIG:
        raise ValueError(f"variant desconocida: {variant!r}")
    variant_config = dict(_VARIANT_CONFIG[variant])
    if variant == "long":
        duracion, escenas, _ = _tamano_por_material(news_item.get("summary", ""))
        variant_config["duration_hint"] = duracion
        variant_config["scene_count_hint"] = escenas

    # The genre blocks carry placeholders of their own ({duration_hint}), and
    # str.format inserts what it substitutes literally - it does not look
    # inside it. Without this pass the words "{duration_hint}" would reach the
    # model verbatim instead of "unos 60 segundos".
    genero = {
        nombre: bloque.format(**variant_config)
        for nombre, bloque in _GENRE_BLOCKS[CONTENT_MODE].items()
    }
    prompt = PROMPT_TEMPLATE.format(
        **genero,
        channel_name=CHANNEL_NAME,
        tone_hint=CHANNEL_TONE_HINT,
        language=NEWS_LANGUAGE_HINT,
        bloque_ortografia=_ORTOGRAFIA.get(NARRATION_LANG, _ORTOGRAFIA['es']),
        title=news_item["title"],
        summary=_trim_sources(news_item["summary"], _SOURCE_BUDGET[variant]),
        **variant_config,
    )
    if variant == "short":
        prompt = _sin_lo_que_ya_no_usa(prompt)

    # Split into the part that never changes and the story of the day, so the
    # instructions can be cached.
    #
    # Caching is a prefix match: everything after the first differing byte is
    # re-read at full price. The story used to sit 15% of the way in, which put
    # the other 85% - about four thousand tokens of instructions, resent on
    # every script of every video - permanently past the point of difference.
    # Moving it to the end and sending the instructions as a cached system
    # prompt means they are written once and then read at a tenth of the price.
    # Que se vea EN EL LOG con que tono se esta escribiendo. CHANNEL_TONE_HINT
    # se puede sobrescribir por variable de entorno, y durante dias estuvo
    # entrando el tono del canal viejo - "casos reales de informatica... el
    # tono es documental, preciso y sobrio" - sin que se notara en ningun
    # sitio, porque el prompt no se imprime en ningun lado. Con esta linea se
    # sabe de un vistazo cual mando en cada video.
    logger.info("Guion (%s): tono del canal -> %s...", variant, CHANNEL_TONE_HINT[:70])

    instrucciones, _, noticia = prompt.partition(_STORY_MARKER)

    last_error: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        # STREAMED, and not for the progress: the SDK refuses a plain request
        # whose max_tokens is high enough that it might run past ten minutes,
        # and raises before sending anything. Raising the ceiling for a
        # fifty-scene script crossed that line and every generation failed
        # instantly. Streaming removes the limit; get_final_message gives back
        # the same Message the non-streaming call returned, so nothing
        # downstream changes.
        try:
            with _client.messages.stream(
                model=CLAUDE_MODEL,
                max_tokens=_MAX_TOKENS,
                system=[
                    {
                        "type": "text",
                        "text": instrucciones,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": _STORY_MARKER + noticia}],
            ) as stream:
                message = stream.get_final_message()
        except anthropic.APIStatusError as exc:
            # El filtro de contenido de la API es un fallo distinto de todos
            # los demas y merece decirse con sus palabras: no es un error de
            # red ni un JSON roto, es que la respuesta se ha bloqueado. Salia
            # como un traceback de doscientas lineas en el que no se entendia
            # nada, y el pipeline moria sin explicar por que.
            if "content filtering" in str(exc).lower():
                logger.warning(
                    "generate_script (%s): la API ha bloqueado la respuesta por su "
                    "filtro de contenido en el intento %s.", variant, attempt)
                last_error = RuntimeError(
                    "La API ha bloqueado la respuesta por su filtro de contenido. "
                    "Suele pasar con casos que mezclan una muerte sin resolver y "
                    "material de primera mano; prueba a generar con otros casos.")
                continue
            raise
        llm_usage.record(f"guion-{variant}", CLAUDE_MODEL, message)
        text_blocks = [block.text for block in message.content if block.type == "text"]
        if not text_blocks:
            last_error = ValueError("Claude no devolvio ningun bloque de texto en la respuesta")
            continue

        raw_text = _solo_el_json(_strip_markdown_fence(text_blocks[0]))
        try:
            script = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            # Log the offending text: a malformed response is otherwise
            # invisible, and the failure mode matters. A truncated response
            # is worth retrying, but a quoting mistake inside a string value
            # is deterministic - it fails identically on all three attempts
            # and loses the story outright, which is what happened before
            # the prompt gained its "no double quotes inside values" rule.
            logger.warning(
                "generate_script (%s): JSON invalido (%s). Respuesta cruda alrededor del fallo: %r",
                variant,
                exc,
                raw_text[max(0, exc.pos - 200) : exc.pos + 200],
            )
            last_error = exc
            continue

        required_keys = {"title", "description", "tags", "scenes"}
        if not required_keys.issubset(script):
            last_error = ValueError(f"Respuesta de Claude incompleta, faltan claves: {required_keys - script.keys()}")
            continue

        # Aqui, y no despues, porque aqui todavia no se ha pagado nada caro.
        #
        # Lo unico que se comprobaba eran las cuatro claves de arriba. Una
        # escena sin "narration" pasaba el filtro y reventaba mucho mas tarde,
        # en el paso 4 o 5 - con la narracion del paso 3 YA PAGADA, que son
        # unos siete mil quinientos creditos. Repetir el guion cuesta treinta
        # centimos; descubrirlo despues cuesta el video entero.
        # En el ultimo intento solo se miran los fallos que revientan el
        # video; lo de calidad se acepta y se avisa. Perder un guion ya
        # pagado por una regla de estilo es el peor cambio posible.
        ultimo = attempt >= _MAX_ATTEMPTS
        problema = _que_le_pasa_al_guion(script, variant, exigente=not ultimo)
        if problema:
            logger.warning("generate_script (%s): guion mal formado (%s). Intento %s.",
                           variant, problema, attempt)
            last_error = ValueError(f"Guion mal formado: {problema}")
            continue
        if ultimo:
            pega = _que_le_pasa_al_guion(script, variant, exigente=True)
            if pega:
                logger.warning(
                    "generate_script (%s): el guion sale con una pega despues de %s "
                    "intentos y se acepta igual - %s.", variant, attempt, pega)

        _log_accent_rate(script, variant)
        return script

    raise RuntimeError(f"generate_script fallo tras {_MAX_ATTEMPTS} intentos: {last_error}") from last_error
