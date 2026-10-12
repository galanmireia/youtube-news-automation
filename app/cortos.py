"""LOS SHORTS DEL VIDEO LARGO ("¿luego vamos a poder hacer shorts para
TikTok a partir de los videos?"): de cada video de Why Though salen unos
cuantos verticales de 30-58 segundos, sin dibujar nada nuevo.

- Se eligen los trozos con mas gags (planos seguidos, de principio a fin de
  frase, que se entienden solos).
- Del video largo se recorta un cuadrado que sigue a Mokordo plano a plano,
  y va en el centro de un vertical 1080x1920: arriba el titulo del trozo
  ("DAY 3 WITHOUT SLEEP"), abajo los subtitulos grandes, de 3 en 3 palabras
  (en TikTok casi todo se ve sin sonido), y al final "full video on the
  channel".
- El monta (porque.monta) deja apuntado en planos_cortos.json donde empieza
  cada plano, que se dice, donde esta lo importante y si tiene gag.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

ANCHO, ALTO = 1080, 1920
LADO = 1080                # el cuadrado que se recorta del video (1920x1080)
ARRIBA = 330               # donde empieza el cuadrado en el vertical
MIN_S, MAX_S = 30.0, 58.0
FONDO = "0xF4EDE1"         # el papel del canal
_FUENTE = "DejaVu Sans"


def apunta(planos: list, fronteras: list, fps: float, guion: dict, carpeta: Path) -> None:
    """Lo que necesitan los shorts, al acabar el monta. planos =
    [(texto, visual, pausa, capitulo)]."""
    caps = guion.get("capitulos") or []
    filas = []
    for i, (texto, visual, pausa, cap) in enumerate(planos):
        ini, fin = fronteras[i]/fps, fronteras[i + 1]/fps
        ma = visual.get("mascota") if isinstance(visual.get("mascota"), dict) else None
        filas.append({
            "ini": round(ini, 3), "fin": round(fin, 3), "texto": texto, "pausa": pausa,
            "centro": _centro(visual), "gag": bool(ma and ma.get("gag")), "cifra": bool(visual.get("cifra")),
            "hace": bool(ma and ma.get("hace")), "careta": bool(visual.get("_careta") or visual.get("_antes_despues")),
            "cap": cap, "dia": str((caps[cap] if cap < len(caps) else {}).get("dia") or ""),
            "titulo_cap": str((caps[cap] if cap < len(caps) else {}).get("titulo") or ""),
        })
    (carpeta / "planos_cortos.json").write_text(json.dumps(
        {"titulo": guion.get("titulo"), "miniatura": guion.get("miniatura"), "planos": filas}, ensure_ascii=False))


def _centro(visual: dict) -> float:
    """Donde mirar en este plano (0-1 del ancho): entre Mokordo y lo que
    acompaña, sin salirse."""
    if visual.get("cifra"):
        return 0.45
    xs = []
    ma = visual.get("mascota")
    if isinstance(ma, dict):
        xs += [float(ma.get("x", 0.5))]*2          # Mokordo pesa doble
    for campo in ("figuras", "cosas"):
        for x in visual.get(campo) or []:
            if isinstance(x, dict):
                try:
                    xs.append(float(x.get("x", 0.5)))
                except (TypeError, ValueError):
                    pass
    c = sum(xs)/len(xs) if xs else 0.5
    return round(min(0.71, max(0.29, c)), 3)


def elige(planos: list, cuantos: int = 3) -> list[tuple[int, int]]:
    """Los mejores trozos [(primero, ultimo)]: los que mas gags y cifras
    tienen por segundo, sin pisarse, de MIN_S a MAX_S."""
    candidatos = []
    n = len(planos)
    for a in range(n):
        if planos[a]["careta"] or not planos[a]["texto"]:
            continue
        for b in range(a, n):
            if planos[b]["careta"]:
                break
            dur = planos[b]["fin"] - planos[a]["ini"]
            if dur > MAX_S:
                break
            if dur < MIN_S:
                continue
            trozo = planos[a:b + 1]
            puntos = sum(3*p["gag"] + 2*p["cifra"] + 1*p["hace"] for p in trozo)/dur
            # mejor si empieza un capitulo (la frase de arranque se entiende sola)
            if a == 0 or planos[a - 1]["cap"] != planos[a]["cap"]:
                puntos *= 1.25
            candidatos.append((puntos, a, b))
    elegidos = []
    for puntos, a, b in sorted(candidatos, reverse=True):
        if all(b < a2 or a > b2 for a2, b2 in elegidos):
            elegidos.append((a, b))
        if len(elegidos) >= cuantos:
            break
    return sorted(elegidos)


def _titulo_del_trozo(trozo: list, titulo: str) -> str:
    dia = trozo[0]["dia"]
    corto = re.sub(r"\(.*?\)", "", str(titulo or "")).strip()
    if dia:
        # "DAY 3" + de que va el video ("WITHOUT SLEEP", del titulo)
        m = re.search(r"(without \w+|no \w+|every day|for \d+ \w+)", corto, re.I)
        coletilla = m.group(1) if m else ""
        if re.search(r"don'?t sleep|didn'?t sleep|no sleep|without sleep", corto, re.I):
            coletilla = "without sleep"
        return f"{dia} {coletilla}".strip().upper()
    return (trozo[0]["titulo_cap"] or corto).upper()


def _tiempo(s: float) -> str:
    s = max(0.0, s)
    h, m = int(s//3600), int(s % 3600//60)
    return f"{h}:{m:02d}:{s % 60:05.2f}"


def _ass(trozo: list, titulo: str, dur: float) -> str:
    """Los subtitulos (de 3 en 3 palabras, con el ritmo de la frase), el
    titulo de arriba y el final."""
    cab = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {ANCHO}
PlayResY: {ALTO}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{_FUENTE},92,&H00FFFFFF,&H00FFFFFF,&H00161616,&H00000000,-1,0,0,0,100,100,0,0,1,7,0,8,60,60,{ARRIBA + LADO + 70},1
Style: Titulo,{_FUENTE},84,&H0032D6FF,&H0032D6FF,&H00161616,&H00000000,-1,0,0,0,100,100,0,0,1,7,0,8,50,50,110,1
Style: Fin,{_FUENTE},70,&H00FFFFFF,&H00FFFFFF,&H00161616,&H00000000,-1,0,0,0,100,100,0,0,1,6,0,8,60,60,{ARRIBA + LADO + 60},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lineas = [f"Dialogue: 0,{_tiempo(0)},{_tiempo(dur)},Titulo,,0,0,0,,{titulo}"]
    t0 = trozo[0]["ini"]
    for p in trozo:
        palabras = str(p["texto"]).split()
        if not palabras:
            continue
        hablado = max(0.5, (p["fin"] - p["ini"]) - float(p.get("pausa") or 0))
        total = sum(len(w) + 1 for w in palabras)
        t = p["ini"] - t0
        for k in range(0, len(palabras), 3):
            grupo = palabras[k:k + 3]
            d = hablado*sum(len(w) + 1 for w in grupo)/total
            texto = " ".join(grupo).upper().replace("{", "(").replace("}", ")")
            lineas.append(f"Dialogue: 1,{_tiempo(t)},{_tiempo(min(dur, t + d))},Sub,,0,0,0,,{texto}")
            t += d
    lineas.append(f"Dialogue: 2,{_tiempo(max(0.0, dur - 2.2))},{_tiempo(dur)},Fin,,0,0,0,,"
                  "FULL VIDEO ON THE CHANNEL")
    return cab + "\n".join(lineas) + "\n"


def _recorte_x(trozo: list) -> str:
    """La x del cuadrado plano a plano (en una expresion de ffmpeg, t desde
    el principio del trozo)."""
    t0 = trozo[0]["ini"]
    x = lambda p: int(round(min(1920 - LADO, max(0, p["centro"]*1920 - LADO/2))))
    expr = str(x(trozo[-1]))
    for p in reversed(trozo[:-1]):
        expr = f"if(lt(t\\,{p['fin'] - t0:.3f})\\,{x(p)}\\,{expr})"
    return expr


def monta_uno(video: Path, trozo: list, titulo: str, salida: Path) -> Path:
    from .largo import _ffmpeg
    ini = trozo[0]["ini"]
    dur = trozo[-1]["fin"] - ini
    ass = salida.with_suffix(".ass")
    ass.write_text(_ass(trozo, titulo, dur), encoding="utf-8")
    # LAS CIFRAS ENTERAS: en un cuadrado no caben la cifra y Mokordo a la
    # vez ("17 H" salia cortado); en esos planos va el fotograma entero.
    enteros = [(p["ini"] - ini, p["fin"] - ini) for p in trozo if p.get("cifra")]
    if enteros:
        cuando = "+".join(f"between(t\\,{a:.3f}\\,{b:.3f})" for a, b in enteros)
        alto_entero = int(LADO*1080/1920)//2*2
        filtro = (f"[0:v]split[a][b];[a]crop={LADO}:{LADO}:'{_recorte_x(trozo)}':0,setsar=1[cuadro];"
                  f"[b]scale={LADO}:{alto_entero},pad={LADO}:{LADO}:0:{(LADO - alto_entero)//2}:color={FONDO},"
                  f"setsar=1[entero];[cuadro][entero]overlay=0:0:enable='{cuando}'[mezcla];")
    else:
        filtro = f"[0:v]crop={LADO}:{LADO}:'{_recorte_x(trozo)}':0,setsar=1[mezcla];"
    filtro += (f"color=c={FONDO}:s={ANCHO}x{ALTO}:r=25:d={dur:.3f}[papel];"
               f"[papel][mezcla]overlay=0:{ARRIBA}:shortest=1,"
               f"subtitles='{ass.as_posix()}'[v]")
    _ffmpeg(["-ss", f"{ini:.3f}", "-t", f"{dur:.3f}", "-i", str(video), "-filter_complex", filtro,
             "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(salida)],
            "short")
    ass.unlink(missing_ok=True)
    return salida


def saca(video: Path, carpeta: Path, cuantos: int = 3) -> list[tuple[Path, str]]:
    """[(short.mp4, de que va)] del video largo montado en `carpeta`."""
    datos = json.loads((carpeta / "planos_cortos.json").read_text())
    planos = datos["planos"]
    salida = []
    for n, (a, b) in enumerate(elige(planos, cuantos), start=1):
        trozo = planos[a:b + 1]
        titulo = _titulo_del_trozo(trozo, datos.get("titulo") or "")
        mp4 = carpeta / f"short_{n}.mp4"
        try:
            monta_uno(video, trozo, titulo, mp4)
            salida.append((mp4, f"{titulo} · {trozo[-1]['fin'] - trozo[0]['ini']:.0f}s · «{trozo[0]['texto'][:80]}»"))
        except Exception:
            logger.warning("short %s: no ha salido.", n, exc_info=True)
    return salida


def ultimo() -> tuple[Path, Path] | None:
    """(video, carpeta) del ultimo video de Why Though que se puede cortar."""
    from .config import DATA_DIR
    for carpeta in sorted(Path(DATA_DIR).glob("why_*"), key=lambda c: c.stat().st_mtime, reverse=True):
        if not (carpeta / "planos_cortos.json").exists():
            continue
        for nombre in ("final.mp4", "con_efectos.mp4", "con_voz.mp4"):
            if (carpeta / nombre).exists():
                return carpeta / nombre, carpeta
    return None
