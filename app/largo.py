"""/largo: LA HISTORIA LARGA DEL SHORT DE CADA DIA, CONTADA PARA DORMIR.

Ella: "la idea seria subir la historia larga del short cada dia... si hoy
hablamos de Lepanto, pues seria mas decir como empezo, quien participo y esas
cosas aburridas de fechas y personajes". El Short es el chiste; esto es el
documental tranquilo que lo acompaña, en horizontal, de diez minutos a una
hora.

Lo que lo hace distinto de todo lo demas del canal:

- LA VOZ: la entrada (un minuto) con SU voz clonada, y el resto con la voz de
  Google. Una hora con ElevenLabs son ~55.000 creditos AL DIA; con Google,
  un par de dolares. Asi el canal suena a ella y no cuesta un sueldo.
- EL RITMO: un plano cada 30-40 segundos, fijo, con un zoom lentisimo. Es
  para dormirse: nada salta, nada grita, no hay bocadillos.
- LOS DIBUJOS: los monigotes de siempre (mismo reparto, mismos decorados),
  mapas de verdad (app/mapas.py), lineas de tiempo, listas y cifras.
- EL GUION: Claude con el dosier de Wikipedia delante, capitulo a capitulo,
  con el indice hecho antes para que no se repita.
"""
import io
import json
import logging
import math
import shutil
import subprocess
import time
from pathlib import Path

import anthropic
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from . import llm_usage, mapas, monigotes, slides
from .config import ANTHROPIC_API_KEY, CHANNEL_NAME, CLAUDE_MODEL, DATA_DIR, MUSIC_VOLUME

logger = logging.getLogger(__name__)

ANCHO, ALTO = 1920, 1080
FPS = 25
# Palabras por minuto de la voz de Google contando despacio. Medido por
# encima: sirve para repartir el guion, no para cronometrar - el tiempo de
# verdad sale de medir el audio.
_PALABRAS_MINUTO = 120
# Un plano dura lo que tarda en decirse su texto: 50-85 palabras son 25-40
# segundos. Menos y parece un trailer; mas y el dibujo se queda muerto.
# Ella, viendo el primero de Lepanto: "tarda demasiado en cambiar de escena,
# no puede estar casi un minuto con el mismo mapa... los primeros minutos le
# tienen que enganchar". Eran planos de 50-85 palabras (30-45 segundos). Ahora
# una o dos frases, 10-15 segundos, y el dibujo cambia con cada una.
_PALABRAS_PLANO = (18, 35)
_PAUSA_PLANO = 0.35         # segundos de silencio entre planos
_PAUSA_CAPITULO = 1.2       # y entre capitulos, que se note el cambio
# Los dibujos se pintan a 12,5 por segundo y el video va a 25: cada dibujo
# dura dos fotogramas, como la animacion hecha a mano ("en doses"), y cuesta
# la mitad de montar.
_FPS_DIBUJO = 12.5
# El vaiven de los monigotes, mas lento que en los Shorts: es para dormirse.
_CALMA = 2.4
_ZOOM = 1.07                # el zoom lento de cada plano, de 1 a esto
_MINUTOS_MAX = 75

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


class LargoError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# El guion
# ---------------------------------------------------------------------------

_INSTRUCCIONES = """Eres el guionista de "{canal}", un canal de YouTube de historia de España contada
con monigotes. Ademas de los Shorts graciosos, el canal sube cada dia LA HISTORIA LARGA del tema
del Short, en horizontal, para escuchar tranquilo y DORMIRSE: un documental sereno, con todos los
datos - como empezo, quien participo, las fechas, los personajes, lo que paso despues.

EL TONO. Voz de narrador de documental nocturno: calmada, clara, cercana, sin prisas. Frases
completas y bien hiladas, de longitud media. NADA de gritos, exclamaciones, chistes, cliffhangers
ni "¡no te lo vas a creer!". Si hay algo duro (una matanza, una tortura), se dice con respeto y
sin detalles crueles: es un video para dormir y tiene que poder monetizarse.

LOS DATOS. Usa el DOSIER de abajo como fuente: fechas, nombres, cifras y lugares tienen que ser
verdad. Si dos fuentes no coinciden, di la mas aceptada o "segun algunas fuentes". No inventes
dialogos ni detalles. Escribe los numeros de los reyes y papas EN LETRA ("Felipe segundo", "Pio
quinto"): la voz lee "II" como "i i". Los años y las cifras pueden ir en numero.

ORTOGRAFIA: español de España con TODAS sus tildes y eñes; la voz lee la ortografia tal cual.

{bloque_ilustracion}

===== DOSIER =====
{dosier}
"""

_PIDE_INDICE = """Tema del video: «{tema}». Duracion objetivo: {minutos} minutos de narracion
(unas {palabras} palabras en total).

Haz el INDICE. Devuelve SOLO este JSON:
{{
  "titulo": "titulo corto para la careta (6-9 palabras)",
  "titulo_youtube": "titulo para YouTube, que se busque y se entienda, sin clickbait (max 90 caracteres)",
  "descripcion": "descripcion para YouTube: 3-5 parrafos que resuman la historia con fechas y nombres, y al final: 📜 Historias de España contadas despacio, para escuchar tranquilo o para dormir.",
  "tags": ["15-20 etiquetas"],
  "gancho": "LA APERTURA, antes de la presentadora: el momento mas impactante o curioso de la historia contado en 50-70 palabras, para que quien empieza el video se quede los primeros minutos (sin destripar el final, en presente, muy visual)",
  "entrada": "lo que dice la PRESENTADORA al empezar, con su propia voz: 50-70 palabras. Saluda ('Hola, bienvenido a {canal}'), dice de que va la historia de esta noche en una o dos frases, e invita a ponerse comodo. Calida, tranquila, en segunda persona.",
  "reparto": {{"mandamas": "a quien hace", "soldado": "...", "cronista": "...", "abuela": "...", "chaval": "..."}},
  "capitulos": [
    {{"titulo": "titulo corto del capitulo", "resumen": "que se cuenta, con los datos clave", "palabras": 400}}
  ]
}}

"reparto": a quien da vida cada personaje fijo del canal EN TODO EL VIDEO (solo los que hagan
falta; los que no, ""). El mismo personaje historico siempre con el mismo monigote.
Capitulos: entre 2 y 8, en orden cronologico, que juntos sumen las {palabras} palabras. El
primero pone el contexto; el ultimo cuenta las consecuencias y cierra con calma."""

_PIDE_CAPITULO = """INDICE DEL VIDEO (ya decidido):
{indice}

Escribe ahora el CAPITULO {n}: «{titulo}» - {resumen}
Unas {palabras} palabras de narracion, partidas en PLANOS de {pmin} a {pmax} palabras cada uno.
{anterior}
Devuelve SOLO este JSON:
{{"planos": [{{"narracion": "...", "visual": {{...}}, "sonido": "", "falta": ""}}]}}

"falta": SOLO si para dibujar bien ese plano necesitarias algo que NO esta en las listas (un
decorado, una bandera, un gorro, un objeto, una postura), dilo aqui en pocas palabras ("el
Senado de Venecia por dentro", "bandera de Genova"); si no falta nada, "". Se dibujara antes de
montar el video, asi que pidelo sin miedo - pero usa entretanto lo mas parecido que exista.

"sonido": un ruido de fondo suave para ese plano, uno de [gentio, campana, fuego, pasos, espada,
tormenta, mar, monedas, puerta, caballo], o "" (lo normal). Solo donde pegue de verdad: "mar" en
el puerto o la galera, "espada" en la batalla, "campana" en la iglesia.

PLANOS CORTOS: una o dos frases cada uno ({pmin}-{pmax} palabras, 10-15 segundos de voz). El
dibujo cambia con CADA plano, asi que pocos planos seguidos con el mismo decorado, y nunca dos
mapas o dos pantallas de datos seguidos.

"visual" es lo que se ve mientras se dice ese plano. Uno de estos tipos:

1. {{"tipo": "escena", "escena": {{...}}}} - monigotes en un decorado, con el formato de LA ESCENA
   de arriba, PERO sin dialogos: "hablan": [], nada de bocadillos. Se ANIMAN como en los Shorts:
   pon "pose" y "pose_fin" (de una postura a otra) y los EFECTOS cuando la narracion los cuente -
   el que cae herido "caida", el que celebra la victoria "salto", el que suda "sudor", el que
   llora "lagrimas", el que tiene una idea "idea", la boda "enamorado", el que se saca la corona
   "corona", el que le da algo a otro "entrega"... Posturas que cuenten lo que se narra (firmando,
   remando, peleando, rezando, mirando...). Usa el reparto del indice y el mismo gorro para el
   mismo personaje en todo el video. Que los decorados VARIEN de un plano a otro, y pon las
   BANDERAS de cada bando y las cosas de las que se habla.
2. {{"tipo": "mapa", "mapa": {{"titulo": "...", "lugares": [{{"nombre": "Mesina", "lat": 38.19, "lon": 15.55, "tipo": "ciudad|capital|batalla"}}],
   "zonas": [{{"nombre": "Imperio otomano", "lat": 39.5, "lon": 32.0, "color": "verde|rojo|azul|negro|oro"}}],
   "flechas": [{{"de": "Mesina", "a": "Lepanto", "color": "rojo"}}]}}}} - cuando importa DONDE: coordenadas
   reales (latitud y longitud con dos decimales), de 2 a 7 lugares; las flechas unen lugares de la lista.
3. {{"tipo": "cronologia", "titulo": "...", "puntos": ["1570 · Los otomanos atacan Chipre", "..."]}} - 3 a 6 fechas.
4. {{"tipo": "lista", "titulo": "...", "puntos": ["Don Juan de Austria · al mando de la flota", "..."]}} - 3 a 6.
5. {{"tipo": "cifra", "valor": "200", "unidad": "galeras", "pie": "frase corta"}}
6. {{"tipo": "comparacion", "titulo": "...", "izquierda": "La Liga Santa: ...", "derecha": "Los otomanos: ..."}}

Mezcla: mas o menos 6 de cada 10 planos son escenas; el resto mapas y datos, donde ayuden de
verdad (un mapa cuando se habla de sitios y rutas, una cronologia cuando se encadenan fechas).
La narracion de cada plano va SIN comillas «» y sin acotaciones: es lo que dice la voz y nada mas.
{cierre}"""


def _json_de(texto: str) -> dict:
    t = texto.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        t = t.rsplit("```", 1)[0]
    ini, fin = t.find("{"), t.rfind("}")
    return json.loads(t[ini:fin + 1])


def _pregunta(sistema: str, pedido: str, paso: str, max_tokens: int = 16000) -> dict:
    ultimo = None
    for intento in range(1, 4):
        with _client.messages.stream(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            output_config={"effort": "low"},
            system=[{"type": "text", "text": sistema, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": pedido}],
        ) as stream:
            mensaje = stream.get_final_message()
        llm_usage.record(paso, CLAUDE_MODEL, mensaje)
        texto = "".join(b.text for b in mensaje.content if b.type == "text")
        try:
            return _json_de(texto)
        except (ValueError, json.JSONDecodeError) as exc:
            ultimo = exc
            logger.warning("largo: %s devolvio JSON roto (intento %s): %s", paso, intento, exc)
    raise LargoError(f"{paso}: Claude no devolvio un JSON valido ({ultimo})")


def _dosier(tema: str) -> str:
    from . import research
    try:
        encontrados = research.buscar("es", tema, 1)
        if not encontrados:
            return ""
        return research.build_dossier(encontrados[0])[:60000]
    except Exception:
        logger.warning("largo: no se ha podido hacer el dosier de %r", tema, exc_info=True)
        return ""


def _bloque_ilustracion() -> str:
    from .script_generator import _VARIANT_CONFIG
    return _VARIANT_CONFIG["short"]["bloque_ilustracion"]


def escribe_guion(tema: str, minutos: int, parar=None) -> dict:
    minutos = max(3, min(_MINUTOS_MAX, int(minutos)))
    palabras = minutos*_PALABRAS_MINUTO
    dosier = _dosier(tema)
    if len(dosier) < 2000:
        logger.warning("largo: dosier corto para %r (%s caracteres); Claude tirara de lo que sabe.",
                       tema, len(dosier))
    sistema = _INSTRUCCIONES.format(canal=CHANNEL_NAME, bloque_ilustracion=_bloque_ilustracion(),
                                    dosier=dosier or "(sin dosier: usa solo datos de los que estes seguro)")
    plan = _pregunta(sistema, _PIDE_INDICE.format(tema=tema, minutos=minutos, palabras=palabras,
                                                  canal=CHANNEL_NAME), "largo-indice", 8000)
    capitulos = [c for c in plan.get("capitulos") or [] if isinstance(c, dict)]
    if not capitulos:
        raise LargoError("el indice no trae capitulos")
    indice = "\n".join(f"{i + 1}. {c.get('titulo')}: {c.get('resumen')}" for i, c in enumerate(capitulos))
    indice += "\nReparto: " + json.dumps(plan.get("reparto") or {}, ensure_ascii=False)
    hechos = []
    for i, c in enumerate(capitulos):
        if parar is not None and parar():
            from .pipeline import GenerationStopped
            raise GenerationStopped("parada pedida mientras se escribia el largo")
        anterior = ""
        if hechos:
            ultimo = " ".join(p.get("narracion", "") for p in hechos[-1]["planos"][-2:])
            anterior = ("\nEl capitulo anterior acababa asi (sigue desde ahi, sin repetir lo ya "
                        f"contado): «{ultimo[-600:]}»\n")
        cierre = ("\nEs el ULTIMO capitulo: termina el video con dos o tres frases tranquilas de "
                  "despedida (buenas noches, hasta la proxima historia)." if i == len(capitulos) - 1 else "")
        cap = _pregunta(sistema, _PIDE_CAPITULO.format(
            indice=indice, n=i + 1, titulo=c.get("titulo", ""), resumen=c.get("resumen", ""),
            palabras=int(c.get("palabras") or palabras/len(capitulos)), pmin=_PALABRAS_PLANO[0],
            pmax=_PALABRAS_PLANO[1], anterior=anterior, cierre=cierre), f"largo-capitulo-{i + 1}")
        planos = [p for p in cap.get("planos") or []
                  if isinstance(p, dict) and str(p.get("narracion", "")).strip()]
        if not planos:
            raise LargoError(f"el capitulo {i + 1} ha salido vacio")
        hechos.append({"titulo": c.get("titulo", ""), "planos": planos})
    plan["capitulos"] = hechos
    # LA APERTURA: el gancho, en planos aun mas cortos, que va antes de la
    # presentadora. Si falla, el video sale sin ella: no vale un video.
    if plan.get("gancho"):
        try:
            ap = _pregunta(sistema, _PIDE_CAPITULO.format(
                indice=indice, n="0 - LA APERTURA (va antes de todo, sin cartel de capitulo)",
                titulo="Apertura", resumen=plan["gancho"], palabras=70, pmin=10, pmax=22,
                anterior="\nEs lo PRIMERO que ve quien abre el video: lo mas visual y emocionante, "
                         "planos muy cortos, y que acabe dejando ganas de saber como paso.\n",
                cierre=""), "largo-apertura")
            planos = [p for p in ap.get("planos") or []
                      if isinstance(p, dict) and str(p.get("narracion", "")).strip()]
            if planos:
                plan["apertura"] = {"titulo": "Apertura", "planos": planos}
        except Exception:
            logger.warning("largo: sin apertura.", exc_info=True)
    return plan


def _secciones(guion: dict) -> list[dict]:
    """La apertura (si hay) y los capitulos, en orden."""
    return ([guion["apertura"]] if guion.get("apertura") else []) + list(guion.get("capitulos") or [])


# ---------------------------------------------------------------------------
# La voz
# ---------------------------------------------------------------------------

def _voz_google(texto: str, destino: Path, ritmo_pedido: float | None = 0.92):
    """Un plano con la voz de Google, mas despacio que la de los Shorts."""
    from google.cloud import texttospeech
    from pydub import AudioSegment
    from .config import TTS_LANGUAGE_CODE, TTS_VOICE_NAME
    from .tts import _get_client
    cliente = _get_client()
    voz = texttospeech.VoiceSelectionParams(language_code=TTS_LANGUAGE_CODE, name=TTS_VOICE_NAME)
    for ritmo in ((ritmo_pedido, None) if ritmo_pedido else (None,)):
        cfg = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                                       **({"speaking_rate": ritmo} if ritmo else {}))
        try:
            r = cliente.synthesize_speech(input=texttospeech.SynthesisInput(text=texto),
                                          voice=voz, audio_config=cfg)
            break
        except Exception:
            if ritmo is None:
                raise
            logger.info("largo: esta voz no acepta cambiar el ritmo; va a velocidad normal.")
    audio = AudioSegment.from_wav(io.BytesIO(r.audio_content))
    audio.export(destino, format="wav")
    return audio


def _voz_suya(texto: str, destino: Path):
    """La entrada con su voz clonada. Si no hay voz clonada, la de Google:
    una entrada con otra voz es mejor que un video que no sale."""
    from pydub import AudioSegment
    from . import voice_clone
    voice_id, modelo, ajustes = voice_clone.ajustes_elegidos()
    if not voice_id:
        logger.warning("largo: no hay voz clonada; la entrada va con la de Google.")
        return _voz_google(texto, destino)
    mp3 = destino.with_suffix(".mp3")
    voice_clone.sintetizar(voice_id, texto, mp3, model=modelo, ajustes=ajustes)
    audio = AudioSegment.from_file(mp3)
    audio.export(destino, format="wav")
    return audio


# ---------------------------------------------------------------------------
# Los dibujos
# ---------------------------------------------------------------------------

def _fuente(px):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", int(px))
    except OSError:
        return ImageFont.load_default()


_FONDO = (26, 24, 30)
_CREMA = (238, 228, 206)
_ROJO = (198, 40, 40)


def _cartel(arriba: str, grande: str, abajo: str = "") -> Image.Image:
    """La entrada y los capitulos: fondo oscuro, letras crema, la raya roja
    del canal. Lo mismo que la careta de los Shorts, en horizontal."""
    img = Image.new("RGB", (ANCHO, ALTO), _FONDO)
    d = ImageDraw.Draw(img)
    medio = ALTO*0.47
    d.rectangle([ANCHO*0.30, medio, ANCHO*0.70, medio + 5], fill=_ROJO)
    d.text((ANCHO/2, medio - ALTO*0.06), arriba.upper(), font=_fuente(ALTO*0.045),
           fill=(170, 160, 146), anchor="mm")
    f = _fuente(ALTO*0.075)
    lineas, linea = [], ""
    for palabra in grande.upper().split():
        prueba = (linea + " " + palabra).strip()
        if d.textlength(prueba, font=f) > ANCHO*0.80 and linea:
            lineas.append(linea)
            linea = palabra
        else:
            linea = prueba
    lineas.append(linea)
    y = medio + ALTO*0.07
    for l in lineas[:3]:
        d.text((ANCHO/2, y), l, font=f, fill=_CREMA, anchor="mt")
        y += f.size*1.2
    if abajo:
        d.text((ANCHO/2, ALTO*0.88), abajo, font=_fuente(ALTO*0.032), fill=(150, 140, 128), anchor="mm")
    return img


def _spec_escena(spec: dict) -> dict:
    e = monigotes.limpia(spec if isinstance(spec, dict) else {})
    e["hablan"], e["a_quien"] = [], []
    for f in e.get("figuras", []):
        # En horizontal los monigotes se quedaban diminutos: su estatura va
        # por la altura de la pantalla, y en vertical esa altura es el doble.
        f["alto"] = f.get("alto", 0.34)*1.3
    return e


def _escena(spec: dict, semilla: int) -> Image.Image:
    e = _spec_escena(spec)
    img = monigotes.montar(e, ANCHO, ALTO, semilla).convert("RGB")
    if e.get("noche"):
        img = monigotes._de_noche(img)
    return img


def _ultimo(fotogramas) -> Image.Image | None:
    return fotogramas[-1].convert("RGB") if fotogramas else None


def dibuja(visual: dict, semilla: int) -> Image.Image:
    """El dibujo de un plano. Lo que no se sepa dibujar cae en una escena
    con el cronista: un plano nunca se queda en negro."""
    v = visual if isinstance(visual, dict) else {}
    tipo = str(v.get("tipo") or "escena").lower()
    img = None
    try:
        if tipo == "mapa":
            img = mapas.mapa(v.get("mapa") or v, ANCHO, ALTO)
        elif tipo == "cronologia":
            img = _ultimo(slides.cronologia([str(p) for p in v.get("puntos") or []][:6],
                                            str(v.get("titulo") or ""), ANCHO, ALTO))
        elif tipo == "lista":
            img = _ultimo(slides.lista([str(p) for p in v.get("puntos") or []][:6],
                                       str(v.get("titulo") or ""), ANCHO, ALTO))
        elif tipo == "cifra":
            img = _ultimo(slides.cifra(str(v.get("valor") or ""), str(v.get("unidad") or ""),
                                       str(v.get("pie") or ""), ANCHO, ALTO))
        elif tipo == "comparacion":
            img = _ultimo(slides.comparacion(str(v.get("izquierda") or ""), str(v.get("derecha") or ""),
                                             str(v.get("titulo") or ""), ANCHO, ALTO))
        else:
            img = _escena(v.get("escena") or v, semilla)
    except Exception:
        logger.warning("largo: no se ha podido dibujar un plano %s; va una escena.", tipo, exc_info=True)
    if img is None:
        img = _escena({"interior": "despacho", "figuras": [{"quien": "cronista", "x": 0.5}]}, semilla)
    if img.size != (ANCHO, ALTO):
        img = img.resize((ANCHO, ALTO))
    # Un poco mas apagado que en los Shorts: es para la noche.
    return ImageEnhance.Brightness(img).enhance(0.9)


# ---------------------------------------------------------------------------
# El montaje
# ---------------------------------------------------------------------------

def _ffmpeg(args: list[str], paso: str, timeout: int = 1800) -> None:
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], capture_output=True,
                       text=True, timeout=timeout)
    if r.returncode != 0:
        raise LargoError(f"ffmpeg ({paso}): {r.stderr[-800:]}")


def _tuberia(fotos, fotogramas: int, destino: Path, zoom: bool, hacia_dentro: bool = True,
             brillo: float = -0.035, desliza: float = 0.0, fps_entrada: float = None) -> None:
    """Los dibujos, uno detras de otro y sin pasar por disco, a un trozo de
    video de `fotogramas` a 25 por segundo. Se pintan a 12,5: ffmpeg repite
    cada uno. Si se acaban antes, se repite el ultimo. Con `zoom`, el
    acercamiento lentisimo (para lo que no se mueve solo: mapas, datos,
    carteles); se agranda antes al doble porque zoompan avanza de pixel en
    pixel y, a esta velocidad, el dibujo temblaria."""
    # fps_entrada: a cuantos se pintan (12,5 por defecto; la mascota de Why
    # Though, a 25, que se mueve mucho y a 12,5 daba tirones).
    fps_entrada = fps_entrada or _FPS_DIBUJO
    entrada = int(math.ceil(fotogramas/(FPS/fps_entrada))) + 2
    filtro = f"fps={FPS}"
    if zoom:
        paso = (_ZOOM - 1)/max(1, fotogramas)
        z = (f"min(1+{paso:.7f}*on,{_ZOOM})" if hacia_dentro else f"max({_ZOOM}-{paso:.7f}*on,1)")
        filtro += (f",scale={ANCHO*2}:{ALTO*2}:flags=bilinear,zoompan=z='{z}':x='iw/2-(iw/zoom/2)'"
                   f":y='ih/2-(ih/zoom/2)':d=1:s={ANCHO}x{ALTO}:fps={FPS}")
    # desliza: el plano ENTRA de lado en esos segundos, frenando, sobre el
    # folio en blanco (Why Though). A 25 por segundo, no a los 12,5 del dibujo.
    if desliza:
        hueco = int(ANCHO*0.4)
        filtro += (f",pad={ANCHO + hueco}:{ALTO}:{hueco}:0:color=0xFCFCFA"
                   f",crop={ANCHO}:{ALTO}:x='{hueco}-{hueco}*pow(1-min(1,t/{desliza}),3)':y=0")
    # Un poco mas apagado que en los Shorts: es para la noche.
    if brillo:
        filtro += f",eq=brightness={brillo}"
    filtro += ",setsar=1,format=yuv420p"
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{ANCHO}x{ALTO}", "-r", str(fps_entrada), "-i", "-", "-vf", filtro,
         "-frames:v", str(fotogramas), "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
         "-r", str(FPS), "-g", str(FPS*10), str(destino)],
        stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    ultimo = None
    try:
        n = 0
        for img in fotos:
            if n >= entrada:
                break
            img = img.convert("RGB")
            if img.size != (ANCHO, ALTO):
                img = img.resize((ANCHO, ALTO))
            ultimo = img.tobytes()
            proc.stdin.write(ultimo)
            n += 1
        while n < entrada and ultimo is not None:
            proc.stdin.write(ultimo)
            n += 1
        proc.stdin.close()
    except BrokenPipeError:
        pass
    error = proc.stderr.read().decode(errors="replace")
    if proc.wait() != 0:
        raise LargoError(f"ffmpeg (plano): {error[-800:]}")


def _plano_en_video(png: Path, fotogramas: int, hacia_dentro: bool, destino: Path) -> None:
    _tuberia([Image.open(png)], fotogramas, destino, zoom=True, hacia_dentro=hacia_dentro)


def _fotos_de_escena(visual: dict, segundos: float, guarda: list):
    """LOS MONIGOTES SE MUEVEN TODO EL PLANO, no seis segundos: "a partir de
    X segundos se quedan paradas y al final eso queda rarisimo". Respiran,
    van de una postura a otra (mas despacio que en los Shorts) y les pasan
    sus efectos, con su sonido."""
    e = _spec_escena((visual or {}).get("escena") or visual or {})
    for f in e.get("figuras", []):
        efecto = f.get("efecto")
        if efecto in monigotes.SONIDO_DEL_EFECTO:
            nombre, dura = monigotes.SONIDO_DEL_EFECTO[efecto]
            t0 = f.get("efecto_desde")
            t0 = monigotes.momento_del_efecto(efecto, segundos) if t0 is None else float(t0)
            if t0 < segundos:
                guarda.append((nombre, t0, dura))
    return monigotes.animar(e, segundos=segundos, fps=_FPS_DIBUJO, tam=(ANCHO, ALTO), calma=_CALMA)


_MAX_ESCENA = 15.0            # segundos como mucho con el mismo dibujo
_POSES_DE_RELEVO = ("señala", "mirando", "brazos_arriba", "andando", "de_pie")


def _relevo_de_escena(visual: dict, k: int) -> dict:
    """La misma escena para el trozo k de un plano demasiado largo: en los
    impares en espejo (lo de la izquierda a la derecha), y siempre con los
    monigotes en otra postura. Sin repetir el efecto ni su sonido."""
    v = json.loads(json.dumps(visual or {}))
    escena = v["escena"] if isinstance(v.get("escena"), dict) else v
    espejo = k % 2 == 1
    for f in escena.get("figuras") or []:
        if not isinstance(f, dict):
            continue
        if espejo:
            f["x"] = 1 - float(f.get("x", 0.5))
            f["espejo"] = not f.get("espejo")
        f["pose"] = _POSES_DE_RELEVO[(k + len(str(f.get("quien", "")))) % len(_POSES_DE_RELEVO)]
        for campo in ("pose_fin", "efecto", "efecto_desde"):
            f.pop(campo, None)
    for c in escena.get("cosas") or []:
        if espejo and isinstance(c, dict):
            c["x"] = 1 - float(c.get("x", 0.5))
    return v


def _fotos_de_mapa(visual: dict, segundos: float):
    """Las rutas del mapa se dibujan solas, una detras de otra, en la primera
    mitad del plano; luego el mapa se queda y sigue el zoom."""
    spec = visual.get("mapa") or visual
    crece = max(1, int(segundos*_FPS_DIBUJO*0.5))
    if not spec.get("flechas"):
        yield mapas.mapa(spec, ANCHO, ALTO)
        return
    yield from mapas.mapa_animado(spec, ANCHO, ALTO, crece)


def _fotos_de_datos(visual: dict, segundos: float):
    """Las listas, fechas y cifras van apareciendo punto a punto en el
    primer 60% del plano, que es como se leen."""
    fotos = None
    tipo = str(visual.get("tipo") or "").lower()
    puntos = [str(p) for p in visual.get("puntos") or []][:6]
    titulo = str(visual.get("titulo") or "")
    if tipo == "cronologia":
        fotos = slides.cronologia(puntos, titulo, ANCHO, ALTO)
    elif tipo == "lista":
        fotos = slides.lista(puntos, titulo, ANCHO, ALTO)
    elif tipo == "cifra":
        fotos = slides.cifra(str(visual.get("valor") or ""), str(visual.get("unidad") or ""),
                             str(visual.get("pie") or ""), ANCHO, ALTO)
    elif tipo == "comparacion":
        fotos = slides.comparacion(str(visual.get("izquierda") or ""), str(visual.get("derecha") or ""),
                                   titulo, ANCHO, ALTO)
    if not fotos:
        yield dibuja(visual, 0)
        return
    total = max(1, int(segundos*_FPS_DIBUJO))
    reparto = max(1, int(total*0.6))
    for k in range(total):
        yield fotos[min(len(fotos) - 1, int(k/reparto*len(fotos)))]


class _guarda_una:
    """Deja pasar los dibujos y se queda con uno (el de la mitad del plano):
    de ahi sale la miniatura."""
    def __init__(self, fotos, cual: int, _cb=None):
        self.fotos, self.cual, self.foto = fotos, cual, None

    def __iter__(self):
        for n, img in enumerate(self.fotos):
            if n == self.cual or self.foto is None:
                self.foto = img.convert("RGB").copy()
            yield img


def _mismo_monigote(guion: dict) -> list[str]:
    """EL MISMO PERSONAJE, EL MISMO MONIGOTE. En el guion de Lepanto, don Juan
    de Austria era Don Severo en tres planos y Perico en otro. Cada papel se
    queda con el monigote que mas veces lleva - salvo en una escena donde ese
    monigote ya lo usa otro, que ahi no se toca."""
    from collections import Counter, defaultdict
    escenas = []
    for cap in _secciones(guion):
        for p in cap.get("planos") or []:
            v = p.get("visual") or {}
            if str(v.get("tipo") or "escena") == "escena":
                escenas.append(v.get("escena") or v)
    votos = defaultdict(Counter)
    for e in escenas:
        for f in e.get("figuras") or []:
            if f.get("papel") and f.get("quien"):
                votos[monigotes.clave_de_papel(f["papel"])][f["quien"]] += 1
    cambios = []
    for e in escenas:
        figs = e.get("figuras") or []
        for f in figs:
            clave = monigotes.clave_de_papel(f.get("papel"))
            if not clave or clave not in votos or not f.get("quien"):
                continue
            mejor = votos[clave].most_common(1)[0][0]
            if mejor != f["quien"] and not any(o is not f and o.get("quien") == mejor for o in figs):
                cambios.append(f"{f.get('papel')}: {f['quien']} -> {mejor}")
                f["quien"] = mejor
    return cambios


def monta(guion: dict, carpeta: Path, parar=None) -> tuple[Path, Path]:
    """De guion a video: voces, dibujos, planos y musica. Devuelve el video y
    la miniatura."""
    from pydub import AudioSegment
    carpeta.mkdir(parents=True, exist_ok=True)
    cambios = _mismo_monigote(guion)
    if cambios:
        logger.info("largo: mismo personaje, mismo monigote: %s", "; ".join(cambios))
    planos = []   # (texto, visual, pausa_despues, es_suya)

    def suma_planos(seccion):
        for k, p in enumerate(seccion["planos"]):
            ultimo = k == len(seccion["planos"]) - 1
            visual = dict(p.get("visual") or {})
            visual["_sonido"] = str(p.get("sonido") or "").strip().lower()
            planos.append((str(p["narracion"]).replace("«", "").replace("»", ""), visual,
                           _PAUSA_CAPITULO if ultimo else _PAUSA_PLANO, False))

    # Primero el gancho, luego ella presentando, luego los capitulos.
    if guion.get("apertura"):
        suma_planos(guion["apertura"])
    titulo = guion.get("titulo") or guion.get("titulo_youtube") or ""
    planos.append((guion.get("entrada") or f"Hola, bienvenido a {CHANNEL_NAME}.",
                   {"tipo": "_cartel", "arriba": f"{CHANNEL_NAME} · para dormir", "grande": titulo},
                   _PAUSA_CAPITULO, True))
    numeros = ["uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez"]
    for n, cap in enumerate(guion["capitulos"]):
        nombre = numeros[n] if n < len(numeros) else str(n + 1)
        planos.append((f"Capítulo {nombre}. {cap['titulo']}.",
                       {"tipo": "_cartel", "arriba": f"Capítulo {n + 1}", "grande": cap["titulo"]},
                       0.8, False))
        suma_planos(cap)

    voz = AudioSegment.empty()
    duraciones = []
    caracteres_google = 0
    for i, (texto, _v, pausa, suya) in enumerate(planos):
        if parar is not None and parar():
            from .pipeline import GenerationStopped
            raise GenerationStopped("parada pedida mientras se narraba el largo")
        wav = carpeta / f"voz_{i:03d}.wav"
        audio = (_voz_suya if suya else _voz_google)(texto, wav)
        if not suya:
            caracteres_google += len(texto)
        audio = audio.set_frame_rate(44100).set_channels(1) + AudioSegment.silent(duration=int(pausa*1000),
                                                                                    frame_rate=44100)
        voz += audio
        duraciones.append(len(audio)/1000.0)
    logger.info("largo: narracion de %.1f minutos (%s planos; %s caracteres con la voz de Google).",
                len(voz)/60000.0, len(planos), caracteres_google)
    narracion = carpeta / "narracion.m4a"
    voz.export(narracion, format="ipod", bitrate="128k")

    # Los fotogramas de cada plano salen de las fronteras acumuladas, no de
    # redondear cada duracion: redondeando plano a plano, en una hora la
    # imagen se iria segundos por detras de la voz.
    fronteras = [0]
    t = 0.0
    for d in duraciones:
        t += d
        fronteras.append(round(t*FPS))
    from . import sonidos
    trozos = []
    ruidos = []           # (sonido, segundo, duracion) para la pista de efectos
    miniatura = None
    for i, (_texto, visual, _p, _s) in enumerate(planos):
        if parar is not None and parar():
            from .pipeline import GenerationStopped
            raise GenerationStopped("parada pedida mientras se dibujaba el largo")
        fotogramas = max(1, fronteras[i + 1] - fronteras[i])
        inicio = fronteras[i]/FPS
        ambiente = visual.get("_sonido") or ""
        if ambiente in sonidos.EFECTOS_VALIDOS:
            ruidos.append((ambiente, inicio + 0.3, min(6.0, fotogramas/FPS)))
        tipo = str(visual.get("tipo") or "escena").lower()
        segundos = fotogramas/FPS
        mp4 = carpeta / f"plano_{i:03d}.mp4"
        try:
            if tipo == "_cartel":
                _tuberia([_cartel(visual["arriba"], visual["grande"])], fotogramas, mp4, zoom=True)
            elif tipo == "mapa":
                _tuberia(_fotos_de_mapa(visual, segundos), fotogramas, mp4, zoom=True,
                         hacia_dentro=i % 2 == 0)
            elif tipo in ("cronologia", "lista", "cifra", "comparacion"):
                _tuberia(_fotos_de_datos(visual, segundos), fotogramas, mp4, zoom=True,
                         hacia_dentro=i % 2 == 0)
            else:
                # Ninguna escena mas de _MAX_ESCENA: la que se pasa se parte
                # y cada trozo es otro dibujo (en espejo, otra postura).
                n = max(1, math.ceil(fotogramas/(_MAX_ESCENA*FPS)))
                cortes = [round(fotogramas*j/n) for j in range(n + 1)]
                piezas = []
                for j in range(n):
                    trozo = cortes[j + 1] - cortes[j]
                    fx = []
                    fotos = _fotos_de_escena(visual if j == 0 else _relevo_de_escena(visual, j), trozo/FPS, fx)
                    if miniatura is None:
                        fotos = _guarda_una(fotos, int(trozo/FPS*_FPS_DIBUJO*0.5), lambda img: None)
                        miniatura_de = fotos
                    pieza = mp4 if n == 1 else carpeta / f"plano_{i:03d}_{j}.mp4"
                    _tuberia(fotos, trozo, pieza, zoom=False)
                    if miniatura is None:
                        miniatura = miniatura_de.foto
                    ruidos += [(nombre, inicio + cortes[j]/FPS + t, d) for nombre, t, d in fx]
                    piezas.append(pieza)
                if n > 1:
                    (carpeta / f"plano_{i:03d}.txt").write_text(
                        "\n".join(f"file '{p.resolve()}'" for p in piezas))
                    _ffmpeg(["-f", "concat", "-safe", "0", "-i", str(carpeta / f"plano_{i:03d}.txt"),
                             "-c", "copy", str(mp4)], "trozos")
                    for p in piezas:
                        p.unlink(missing_ok=True)
        except Exception:
            logger.warning("largo: el plano %s (%s) ha fallado; va un dibujo quieto.", i, tipo,
                           exc_info=True)
            _tuberia([dibuja(visual, semilla=i)], fotogramas, mp4, zoom=True)
        trozos.append(mp4)
        if i % 20 == 0:
            logger.info("largo: %s de %s planos montados.", i + 1, len(planos))

    lista = carpeta / "planos.txt"
    lista.write_text("\n".join(f"file '{p.resolve()}'" for p in trozos))
    mudo = carpeta / "mudo.mp4"
    _ffmpeg(["-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(mudo)], "union")
    con_voz = carpeta / "con_voz.mp4"
    _ffmpeg(["-i", str(mudo), "-i", str(narracion), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
             "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(con_voz)], "voz")
    final = con_voz
    if ruidos:
        try:
            from .video_builder import mezclar_efectos
            pista = sonidos.pista(ruidos, fronteras[-1]/FPS, carpeta / "efectos.wav", volumen=0.10)
            if pista is not None:
                final = mezclar_efectos(con_voz, pista, carpeta / "con_efectos.mp4")
        except Exception:
            logger.warning("largo: sin efectos de sonido.", exc_info=True)
    try:
        from .pipeline import _pick_music_track
        from .video_builder import mix_background_music
        musica = _pick_music_track()
        if musica is not None:
            final = mix_background_music(final, musica, carpeta / "final.mp4", MUSIC_VOLUME*0.6)
    except Exception:
        logger.warning("largo: sin musica de fondo.", exc_info=True)

    jpg = carpeta / "miniatura.jpg"
    (miniatura or _cartel(CHANNEL_NAME, titulo)).convert("RGB").resize((1280, 720)).save(jpg, quality=90)
    # Solo se quedan el video y la miniatura: un largo de una hora deja
    # cientos de megas de andamios, y el disco es de 5 GB.
    for p in list(carpeta.glob("plano_*")) + list(carpeta.glob("voz_*")):
        p.unlink(missing_ok=True)
    for p in (mudo, narracion, con_voz, carpeta / "con_efectos.mp4", carpeta / "efectos.wav"):
        if p != final:
            p.unlink(missing_ok=True)
    return final, jpg


_PENDIENTE = Path(DATA_DIR) / "largo_pendiente.json"


def revisa(guion: dict) -> tuple[str, list[str]]:
    """Lo que el guion pide dibujar, y lo que pide y NO existe.

    Ella: "¿estas seguro que has hecho todos? Yo creo que no". No se podia
    estar seguro: limpia() cambia en silencio lo que no existe por algo que
    si, y el video sale con un fondo cualquiera sin que nadie se entere.
    Esto lo dice antes de gastar en voces y dibujos."""
    from collections import Counter
    llevables = set(monigotes.LLEVABLES_EXPLICADOS)
    validos = {"interior": set(monigotes.DECORADOS_VALIDOS), "gorro": set(monigotes.GORROS_VALIDOS),
               "objeto": set(monigotes.OBJETOS_VALIDOS), "pose": set(monigotes.POSES_VALIDAS),
               "efecto": set(monigotes.EFECTOS_VALIDOS), "lleva": llevables,
               "cosa": set(monigotes.COSAS_VALIDAS)}
    usados, inexistentes, pedidos, tipos = Counter(), Counter(), [], Counter()
    for n, cap in enumerate(_secciones(guion), start=0 if guion.get("apertura") else 1):
        for k, p in enumerate(cap.get("planos") or [], start=1):
            v = p.get("visual") or {}
            tipos[str(v.get("tipo") or "escena")] += 1
            if p.get("falta"):
                pedidos.append(f"cap. {n}, plano {k}: {p['falta']}")
            if str(v.get("tipo") or "escena") != "escena":
                continue
            # A veces la escena viene suelta en el visual, sin su "escena":
            # se dibuja igual, y tiene que revisarse igual.
            e = v.get("escena") or v
            dentro = str(e.get("interior") or "").strip().lower()
            if dentro:
                (usados if dentro in validos["interior"] else inexistentes)[f"decorado {dentro}"] += 1
            for c in e.get("cosas") or []:
                que = str((c or {}).get("que") or "").strip().lower()
                if que and que not in validos["cosa"]:
                    inexistentes[f"cosa {que}"] += 1
            for f in e.get("figuras") or []:
                for campo in ("gorro", "objeto", "pose", "pose_fin", "efecto", "lleva"):
                    val = str((f or {}).get(campo) or "").strip().lower()
                    clave = "pose" if campo == "pose_fin" else campo
                    if val and val not in validos[clave]:
                        inexistentes[f"{clave} {val}"] += 1
    lineas = [f"«{guion.get('titulo_youtube') or guion.get('titulo')}»", ""]
    for n, cap in enumerate(_secciones(guion), start=0 if guion.get("apertura") else 1):
        lineas.append(f"{n}. {cap.get('titulo')} ({len(cap.get('planos') or [])} planos)")
    lineas += ["", "Planos: " + ", ".join(f"{t} {c}" for t, c in tipos.most_common()),
               "Decorados: " + ", ".join(f"{u.split(' ', 1)[1]} {c}" for u, c in usados.most_common())]
    faltan = [f"{x} (x{c})" for x, c in inexistentes.most_common()] + pedidos
    if faltan:
        lineas += ["", "⚠️ PIDE COSAS QUE NO ESTAN DIBUJADAS:"] + [f"- {x}" for x in faltan]
    else:
        lineas += ["", "✅ Todo lo que pide esta dibujado."]
    return "\n".join(lineas), faltan


def run_largo_guion(tema: str, minutos: int) -> str:
    """PASO 1 de /largo: solo el guion (unos centimos). Se guarda y se dice
    que pide dibujar, para dibujar lo que falte ANTES de montar."""
    from .pipeline import _stop_requested
    _stop_requested.clear()
    logger.info("[largo] Escribiendo el guion de %r (%s minutos)...", tema, minutos)
    guion = escribe_guion(tema, minutos, parar=_stop_requested.is_set)
    guion["_tema"], guion["_minutos"] = tema, minutos
    _PENDIENTE.write_text(json.dumps(guion, ensure_ascii=False, indent=1))
    texto, faltan = revisa(guion)
    logger.info("[largo] Guion guardado. %s", texto.replace("\n", " | "))
    for i, cap in enumerate(_secciones(guion), start=0 if guion.get("apertura") else 1):
        for k, p in enumerate(cap["planos"], start=1):
            logger.info("[largo] %s.%s %s", i, k, json.dumps(p.get("visual"), ensure_ascii=False)[:400])
    coste = llm_usage.report_and_reset()
    if coste:
        logger.info("[largo] %s", coste)
    return texto


def hay_pendiente() -> bool:
    return _PENDIENTE.exists()


def run_largo(on_done, tema: str | None = None, minutos: int | None = None) -> list[int]:
    """PASO 2 de /largo (/montar): voces, dibujos, montaje y a Telegram, con
    el guion que dejo el paso 1. Con tema, escribe el guion antes."""
    from . import storage
    from .pipeline import GenerationStopped, _stop_requested, cleanup_finished_video_files
    _stop_requested.clear()
    cleanup_finished_video_files()
    carpeta = Path(DATA_DIR) / f"largo_{int(time.time())}"
    try:
        if tema:
            guion = escribe_guion(tema, minutos or 10, parar=_stop_requested.is_set)
        else:
            guion = json.loads(_PENDIENTE.read_text())
            tema = guion.get("_tema", "")
        carpeta.mkdir(parents=True, exist_ok=True)
        logger.info("[largo] Voces y dibujos de %r (%s capitulos)...", tema, len(guion["capitulos"]))
        video, miniatura = monta(guion, carpeta, parar=_stop_requested.is_set)
    except GenerationStopped as exc:
        logger.info("Generacion del largo detenida: %s", exc)
        shutil.rmtree(carpeta, ignore_errors=True)
        return []
    except Exception:
        shutil.rmtree(carpeta, ignore_errors=True)
        raise
    _PENDIENTE.unlink(missing_ok=True)
    logger.info("[largo] Listo: %s", video)
    coste = llm_usage.report_and_reset()
    if coste:
        logger.info("[largo] %s", coste)
    tags = [str(t) for t in guion.get("tags") or []][:25]
    video_id = storage.create_video_record(
        source_url="", variant="long",
        title=str(guion.get("titulo_youtube") or guion.get("titulo") or tema)[:100],
        description=str(guion.get("descripcion") or ""),
        tags=tags, video_path=str(video), thumbnail_path=str(miniatura), subtitle_path="",
    )
    logger.info("Video #%s (largo) generado y pendiente de aprobacion.", video_id)
    if on_done is not None:
        on_done(video_id)
    return [video_id]
