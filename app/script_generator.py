import json
import logging
import re
import unicodedata

import anthropic

from . import llm_usage
from .config import CONTENT_MODE, ANTHROPIC_API_KEY, CHANNEL_NAME, CHANNEL_TONE_HINT, CLAUDE_MODEL, NEWS_LANGUAGE_HINT

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
        "structure_block": """Este video cuenta UN caso real de informatica o tecnologia - una intrusion, un fraude,
una filtracion, un software que fallo, una empresa que se cayo - A TRAVES DE UNA PERSONA.

LO PRIMERO QUE DECIDES, antes de escribir una sola frase: quien es el protagonista. Busca en el
material a la persona que tomo la decision que lo desencadeno todo, o la que tuvo que cargar con
las consecuencias. El chaval que escribio el gusano. El ingeniero que aviso y al que no hicieron
caso. El directivo que decidio que parchear salia caro. El investigador que lo destapo. Tiene nombre y apellidos en el articulo, y
es el video entero: no aparece en una escena, esta en todas.

POR QUE ESTO IMPORTA MAS QUE NINGUNA OTRA INSTRUCCION: "el ataque de Mirai" es un tema; "el
universitario que tumbo media internet para hacer trampas en Minecraft" es una historia. Un tema se
explica y se olvida a los diez segundos. Una historia tiene a alguien que quiere algo, se
equivoca, y paga - y saber como acaba esa persona es lo unico que hace que alguien se quede.

CUANDO NO HAY PROTAGONISTA: si el material no da ninguna persona con nombre, o si la unica
identificable esta acusada de algo TODAVIA NO RESUELTO, no fuerces uno y no lo inventes. Entonces
el protagonista es el sistema: el gusano, la plataforma, la empresa. Misma estructura, pero
el "quien" es eso y el "que queria" es para lo que se creo. Nunca montes el relato sobre la
culpa de alguien cuyo caso siga abierto.

Estructura obligatoria del guion ({duration_hint}, en este orden):

1. LA DECISION. Abre en el segundo exacto en que el protagonista hace lo que lo desencadena todo,
   con su nombre en la primera frase. Y CORTA antes de decir en que acabo. Nunca empieces situando
   ("en septiembre de 2016, una red de camaras conectadas a internet...").
   Ejemplo: "Paras Jha escribio un programa para que su servidor de Minecraft ganara jugadores.
   Tres meses despues, medio internet estaba caido. ¿Que hacia exactamente ese programa?" -> el
   espectador ya sabe que algo va a pasar, y no sabe el que.

2. QUIEN ERA Y QUE QUERIA. Muy corto. Su cargo, su experiencia, y las dos o tres cifras que dicen
   lo que tenia entre manos: cuanta gente, cuanto pesaba, cuanto valia. Nada de inventario.

3. LO QUE SE LE VINO ENCIMA. La cronologia, en orden, con horas y datos concretos. Sobria, sin
   dramatizar. AQUI TODAVIA NO SE EXPLICA POR QUE FUE TAN GRAVE.

4. POR QUE AQUELLO FUE CATASTROFICO. El pago de todo lo anterior, y lo que separa este canal de
   quien solo cuenta la tragedia: la causa tecnica explicada para cualquiera. Que fallo, por que
   esa decision concreta tuvo ese efecto concreto, que margen no existia. Si hay informe oficial,
   citalo. No puede llegar antes de la mitad del video.

5. QUE FUE DE EL. El desenlace de la PERSONA, no solo del sitio: juicio, condena y cuantos años,
   absolucion, ruina, olvido, o que siguio trabajando como si nada. Esto no es un epilogo, es la
   razon por la que alguien aguanta hasta el final. Si ademas cambiaron normas o diseños por el
   caso, va aqui en una frase. Cierra con la llamada a suscribirse.

TONO: documental, sobrio y preciso. El drama lo ponen los hechos y las cifras, no los adjetivos.
Tener un protagonista NO es licencia para novelar: no le atribuyas pensamientos, miedos ni
intenciones que no esten en la fuente. Puedes contar lo que hizo y lo que dijo; no lo que sentia.
Si hubo victimas, se mencionan con respeto y sin detalles morbosos: nunca describas agonias,
heridas ni el sufrimiento de personas concretas. No especules sobre causas que la investigacion no
haya establecido - si algo esta en disputa, di que esta en disputa.""",
        "source_block": """===== MATERIAL DE PARTIDA =====
VARIAS fuentes sobre el mismo caso, cada una con su cabecera: el articulo principal, el mismo
articulo en otros idiomas - escritos por separado, no son traducciones - y los articulos de las
personas, los sitios y las maquinas que salen en la historia.

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
- Punto para el golpe. Una frase corta y un punto pesan mas que una coma. "España le dijo que no."
  suena; "España le dijo que no y seis dias despues..." se diluye.
- Coma antes del dato que quieres que se oiga: "El casco se abrio, a treinta millas de la costa."
- Si algo es una PREGUNTA, escribela como pregunta de verdad, con ¿ y ? - asi la voz sube al final
  y suena a pregunta. Una pregunta escrita como afirmacion se lee plana y pierde todo el efecto.
  Esto importa especialmente en el gancho, que muchas veces es la pregunta del video.
- Nada de frases largas encadenadas con comas: la voz las lee de corrido, sin aire, y cansa.
- Nunca uses puntos suspensivos ni guiones para marcar una pausa: no los respeta. Usa punto.

ORTOGRAFIA, MUY IMPORTANTE: el campo "narration" lo lee en voz alta un sintetizador de voz, y ese
sintetizador pronuncia SEGUN COMO ESTE ESCRITA la palabra. Una palabra sin su tilde se pronuncia
con el acento en la silaba equivocada y suena a robot. Escribe la narracion en español
PERFECTAMENTE acentuado, con todas las tildes, eñes y signos de apertura: "investigación" y no
"investigacion", "según" y no "segun", "murió" y no "murio", "más" y no "mas", "año" y no "ano",
"España" y no "Espana", "análisis", "policía", "también", "qué", "cómo", "aquí". Lo mismo para
"title", "description" y "on_screen_highlight", que se leen en pantalla. Fijate en que estas
instrucciones estan escritas sin tildes por motivos tecnicos: NO imites ese estilo, tu texto debe
ir correctamente acentuado.

Recuerda: SIEMPRE anclado en los hechos de la noticia original. Nunca inventes conspiraciones ni
afirmes cosas que no esten respaldadas por la fuente.

Fotos reales de personas y lugares/instituciones concretas: para cada escena, si esa narracion
concreta nombra directamente (a) una persona publica real identificable por su cargo o su nombre
(un ministro, un politico, un CEO, un famoso), O (b) un lugar, edificio o institucion especifico y
con nombre propio que casi seguro tenga su propio articulo en Wikipedia con foto (una universidad
concreta, un ministerio, un monumento, la sede de una empresa conocida, un estadio, un hospital
concreto, UN PARTIDO POLITICO por su nombre - PSOE, PP, Vox, Sumar, etc. -, un sindicato, una
organizacion internacional como la ONU o la Union Europea, y TAMBIEN CUALQUIER PUEBLO, MUNICIPIO,
CIUDAD, COMARCA, ISLA O PROVINCIA con nombre propio - Alozaina, Ronda, Teruel, El Hierro, etc.,
por pequeño que sea, casi todos tienen articulo en Wikipedia con foto del sitio real), rellena
"photo_subject" con su
nombre completo tal cual aparece en Wikipedia, para mostrar su foto/logo REAL en vez de video
generico o una ilustracion inventada. Nunca sustituyas un lugar, institucion o partido con nombre
propio conocido por una escena generica ni por una ilustracion de IA - si tiene nombre propio y es
real, casi siempre existe una foto real de el, usa "photo_subject" primero. Ejemplos concretos: si
la narracion menciona "la Universidad de Las Palmas de Gran Canaria", el campo debe ser exactamente
"photo_subject": "Universidad de Las Palmas de Gran Canaria"; si menciona "el PSOE" o "el partido
socialista", debe ser "photo_subject": "Partido Socialista Obrero Español" - NUNCA lo dejes vacio
ni uses "visual_keywords" o "ai_image_prompt" para estos casos, por muy comun o generico que
parezca el nombre. Si el nombre es generico y existe igual en varios paises (ej. "Partido Popular"
existe en España, Portugal y otros paises), añade el pais entre parentesis: "photo_subject":
"Partido Popular (España)" - si no, la busqueda de la foto puede acabar cogiendo el articulo o la
imagen equivocada de otro pais.
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

Ilustracion por IA ("ai_image_prompt"): es para las escenas ABSTRACTAS, las que no tienen nada real
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

Nunca pidas personas reales reconocibles. Para representar partidos o bandos usa el COLOR, que en
España se entiende solo (azul el PP, rojo el PSOE), nunca sus logos: estos modelos los dibujan
deformados y canta muchisimo.

Deja "ai_image_prompt" vacio ("") cuando la escena si tenga algo real que enseñar o cuando un clip
de archivo concreto la represente bien.

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
MUY IMPORTANTE - pais correcto: cuando la escena sea de gobierno, politica, justicia, policia,
banca central, parlamento o cualquier otra imagen institucional generica, especifica SIEMPRE el
pais/region real de la noticia dentro de las palabras clave (ej. para una noticia de España:
"spanish parliament exterior", "madrid courthouse", "spain police officer", "european union flag
brussels" - NUNCA dejes terminos ambiguos sin pais como "government building", "senate", "capitol",
"courtroom" o "police car", porque los bancos de stock genericos devuelven mayoritariamente
imagenes de Estados Unidos (banderas americanas, el Capitolio, coches de policia americanos) para
esos terminos, y eso queda visualmente incorrecto y confunde al espectador en una noticia de otro
pais. Si la noticia es de España usa "spain"/"spanish"/"madrid"/etc.; si es de otro pais, usa ese
pais en su lugar.

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
- "title": es LO QUE HIZO EL PROTAGONISTA, no el nombre del sitio ni la matricula del aparato.
  Maximo 90 caracteres, con gancho pero sin exagerar (nada de MAYUSCULAS sostenidas ni "no vas a
  creer..."). Tres reglas duras, porque los titulos de este canal venian saliendo mal:
  * NUNCA empieces por un nombre propio seguido de dos puntos. "M/S Estonia: que fallo en el
    ataque" y "Stuxnet: el fallo tecnico que permitio..." no le dicen nada a nadie que no sepa
    ya lo que es un M/S Estonia, y son literalmente encabezados de enciclopedia.
  * Empieza por la PERSONA definida por su acto: "El universitario que tumbo medio internet por
    un servidor de Minecraft", "La mujer que estafo cuatro mil millones con una moneda que no
    existia". Si el protagonista es la
    obra y no una persona, entonces por lo que la obra hizo o le hicieron, nunca por su nombre a
    secas.
  * Si tienes una cifra o un superlativo que sostenga el titulo, usalo: "cuatro mil personas",
    "el mayor robo bancario de la historia". Un numero concreto pesa mas que un adjetivo.
  El nombre propio del caso NO se pierde: va en "tags" y en la primera frase de "description", que
  es de donde YouTube saca las palabras clave para el buscador. El titulo esta para que alguien
  haga clic, no para indexar.
- "description": empieza con 1-2 frases que repitan de forma natural la palabra clave principal
  del titulo (esto es lo que se muestra en resultados de busqueda), sigue con 2-3 frases de
  contexto, y termina con 3 a 5 hashtags relevantes (formato #Palabra, sin espacios) mas una
  llamada a suscribirse a {channel_name}.
- "tags": genera entre 10 y 15 palabras clave/frases de busqueda reales que la gente usaria en
  YouTube sobre este tema, mezclando: 2-3 amplias (el tema general, ej. "inteligencia artificial"),
  4-6 especificas (nombres, lugares, entidades concretas de la noticia), y 3-5 relacionadas con el
  tipo de contenido (ej. "noticias de actualidad", "analisis noticias españa"). Sin duplicados,
  sin almohadillas aqui (van solo en la descripcion).
{shorts_seo_hint}

MUY IMPORTANTE - formato del JSON: NUNCA uses comillas dobles (") dentro del texto de ningun campo.
Una sola comilla doble sin escapar rompe el JSON entero y el video no se llega a generar. Si necesitas
entrecomillar algo (el nombre de una ley, una cita, un termino), usa comillas simples ('asi') o
angulares (<<asi>>). Tampoco metas saltos de linea dentro de un valor: cada narracion va en una sola
linea.

Devuelve EXCLUSIVAMENTE un JSON con esta forma exacta, sin texto adicional ni markdown:
{{
  "title": "titulo optimizado para SEO, ver requisitos arriba",
  "description": "descripcion con hashtags, ver requisitos arriba",
  "is_sensitive": "true o false - true si la noticia trata sobre una muerte, crimen violento, victima identificable, tragedia personal real, o una acusacion/investigacion no probada sobre una persona identificable (ver AVISO DE SENSIBILIDAD arriba), false en cualquier otro caso",
  "tags": ["tag1", "tag2", "... entre 10 y 15 tags"],
  "scenes": [
    {{
      "narration": "texto que se narrara en esta escena, en español con TODAS las tildes correctas",
      "visual_keywords": "palabras clave en ingles para buscar video de stock",
      "photo_subject": "nombre de una persona publica o de un lugar/institucion con nombre propio si aplica, si no, cadena vacia",
      "photo_subject_role": "cargo de la persona o descriptor corto del lugar si photo_subject no esta vacio, si no, cadena vacia",
      "ai_image_prompt": "descripcion en ingles para ilustracion por IA si aplica, si no, cadena vacia",
      "on_screen_highlight": "texto corto en español (3-6 palabras) con el dato clave de esta escena, con CIFRA si la escena tiene alguna, ver instrucciones arriba"
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

_VARIANT_CONFIG = {
    "short": {
        "format_hint": (
            "YouTube Short vertical (9:16). Debe ser autoconclusivo, directo al grano, pensado "
            "para verse en el feed de Shorts sin contexto previo."
        ),
        "duration_hint": "40-50 segundos",
        "scene_count_hint": "entre 5 y 6 escenas",
        "scene_length_hint": (
            "Cada narracion es UNA frase corta y directa de UNAS 20 PALABRAS - nunca dos frases, "
            "nunca una frase larga con comas encadenadas. Con 5 o 6 escenas asi el Short sale en su "
            "duracion. Si una frase se te va larga, recorta adjetivos y contexto, nunca las cifras "
            "ni la causa tecnica."
        ),
        "shorts_seo_hint": (
            '- Incluye "#Shorts" como uno de los hashtags al final de la descripcion (obligatorio '
            "para que YouTube lo clasifique bien como Short)."
        ),
    },
    "long": {
        "format_hint": "Video horizontal (16:9) extendido para YouTube, no es un Short.",
        "duration_hint": "3 a 5 minutos",
        "scene_count_hint": "entre 16 y 24 escenas",
        "scene_length_hint": (
            "Cada narracion puede tener hasta 2-3 frases; profundiza mas que en un Short: añade "
            "ejemplos concretos, cifras adicionales, comparaciones, cronologia mas detallada y "
            "matices en el analisis."
        ),
        "shorts_seo_hint": "",
    },
}


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
# reply itself is a few hundred tokens. The Short's ceiling was 8000 and a
# harder prompt walked straight into it - three attempts in a row spent the
# entire budget thinking and returned no text at all, which reads as a broken
# API rather than as "give me more room".
_MAX_TOKENS = {"short": 12000, "long": 20000}
_MAX_ATTEMPTS = 3



# Written Spanish carries an accent or an ene on roughly one word in twenty.
# Well under that means the narration came back effectively unaccented, which
# the voice then mispronounces - it stresses whatever the spelling says.
_MIN_ACCENT_RATE = 0.02


def _log_accent_rate(script: dict, variant: str) -> None:
    """Reports how accented the narration came out.

    The prompt asks for correctly accented Spanish because the speech
    synthesiser pronounces from the spelling, and an unaccented word lands its
    stress on the wrong syllable. Whether the model actually complied is not
    otherwise visible until the video is listened to."""
    text = " ".join(scene.get("narration", "") for scene in script.get("scenes", []))
    words = re.findall(r"[^\W\d_]{3,}", text, re.UNICODE)
    if not words:
        return
    accented = sum(
        1 for w in words if any(unicodedata.combining(c) for c in unicodedata.normalize("NFD", w)) or "ñ" in w.lower()
    )
    rate = accented / len(words)
    message = "Guion: %.1f%% de palabras acentuadas (%s de %s)"
    if rate < _MIN_ACCENT_RATE:
        logger.warning(
            message + " - demasiado pocas, la voz pronunciara mal. Variante '%s'.",
            rate * 100, accented, len(words), variant,
        )
    else:
        logger.info(message, rate * 100, accented, len(words))


def generate_script(news_item: dict, variant: str = "long") -> dict:
    if variant not in _VARIANT_CONFIG:
        raise ValueError(f"variant desconocida: {variant!r}")
    variant_config = _VARIANT_CONFIG[variant]

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
        title=news_item["title"],
        summary=news_item["summary"],
        **variant_config,
    )
    # Split into the part that never changes and the story of the day, so the
    # instructions can be cached.
    #
    # Caching is a prefix match: everything after the first differing byte is
    # re-read at full price. The story used to sit 15% of the way in, which put
    # the other 85% - about four thousand tokens of instructions, resent on
    # every script of every video - permanently past the point of difference.
    # Moving it to the end and sending the instructions as a cached system
    # prompt means they are written once and then read at a tenth of the price.
    instrucciones, _, noticia = prompt.partition(_STORY_MARKER)

    last_error: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        message = _client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=_MAX_TOKENS[variant],
            system=[
                {
                    "type": "text",
                    "text": instrucciones,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": _STORY_MARKER + noticia}],
        )
        llm_usage.record(f"guion-{variant}", CLAUDE_MODEL, message)
        text_blocks = [block.text for block in message.content if block.type == "text"]
        if not text_blocks:
            last_error = ValueError("Claude no devolvio ningun bloque de texto en la respuesta")
            continue

        raw_text = _strip_markdown_fence(text_blocks[0])
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

        _log_accent_rate(script, variant)
        return script

    raise RuntimeError(f"generate_script fallo tras {_MAX_ATTEMPTS} intentos: {last_error}") from last_error
