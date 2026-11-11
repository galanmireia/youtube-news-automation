# Notas para Claude

Proyecto: dos bots de Telegram en Railway que generan vídeos.
- **España Contada** (youtube-bot): historia de España en monigotes, en español.
- **STILL BURNING** (why-though-bot): canal en inglés.

Railway: proyecto `137a5ff0-c0bb-441c-aaa6-4ac85c501f79`
- youtube-bot: `db48b9f3-2074-4649-878d-53367b15824d`
- why-though-bot: `9390831a-9a02-4108-b16e-661d537952d7`

Rama de trabajo y de despliegue: `claude/youtube-automation-channel-mybp8t`. Railway
despliega solo al hacer push a esa rama.

## Normas fijas de la dueña

- Responder siempre en **español**.
- **Nunca hacer push mientras un bot está generando**: antes, mirar los logs de Railway de
  LOS DOS servicios. Después del push, decirle que espere a SUCCESS antes de lanzar nada.
- No leer variables ni secretos de Railway. No clonar repos de terceros sin preguntar.
- Preguntar antes de pruebas de pago de más de unos céntimos (ElevenLabs ≈ 1 crédito por carácter).
- **Probar antes de proponer**: hojas de escenas o fotogramas para revisar antes del vídeo.
- Contenido: exactitud ante todo, sin inventar datos; nada de anacronismos (ropa de época:
  `sayo` para los cristianos del norte en la Alta Edad Media, `tunica` + `turbante` para
  Al-Andalus); sin caras IA de personas reales; nunca dibujar a Mahoma; **sin humor sobre la
  Guerra Civil ni el terrorismo**; nada de vivienda; no copiar mascotas de otros canales.
- Ideas originales, no las típicas. Pocos personajes. Más gracioso.

## España Contada

- Público real: sobre todo **2º de Bachillerato** que prepara la **PAU** (Historia de España).
  Los vídeos que más funcionan los encuentran buscando (p. ej. el de Isabel II, la reina de
  tres años). Pensar títulos y etiquetas para el buscador: «2º Bachillerato», «PAU»,
  «selectividad», «resumen».
- Guiones hechos a mano: `app/guiones_espana/<nombre>.json`, se lanzan con `/hecho <nombre>`.
  El bot los lee TAL CUAL (solo arreglos automáticos de bocadillos/anacronismos).
- Validar en local antes de subir (con variables falsas solo para importar):
  `ANTHROPIC_API_KEY=x PEXELS_API_KEY=x TELEGRAM_BOT_TOKEN=x TELEGRAM_CHAT_ID=1` y
  `_que_le_pasa_al_guion(script, "short", exigente=_SOLO_LO_ROTO)` de `app.script_generator`.
- Un Short debe durar ~1 minuto: ~2,2 palabras por segundo de narración (237 palabras dieron 1:48).
- Bocadillos: máximo 10 palabras por frase y 8 frases por escena; lo del narrador va sin «».

## Estado (4-nov-2026)

- **Covadonga**: terminado (14 escenas, ~67 s, título y etiquetas para la PAU).
- **Amadeo de Saboya** (`/hecho amadeo`): 13 escenas (versión mejorada con ChatGPT, datos corregidos), ~167 palabras, siglo XIX con ropa de
  1870 (uniforme y banda, peinetas). Hecho el 4-nov; pendiente de revisar el vídeo generado.
- Siguiente línea propuesta: saga del siglo XIX para 2º Bachillerato (Primera República,
  Restauración, Constitución de 1876...). Ficha «Para la PAU» al final: pendiente de decidir.
- Otros proyectos en `prototipos/`: reels de gatos (`michi/`), zoom de fractal (`fractal/`).
- **Canal nuevo «Lo he simulado»** (`prototipos/simulado/`): preguntas de la vida real respondidas con
  simulaciones programadas, videos largos horizontales. Video 1: atascos fantasma (`atascos.py`,
  simulacion en `trafico.py`), narrado con su voz clonada via `/narra atascos si` en el bot de
  España Contada (textos en `app/narraciones/`). Montaje: `atascos.py salida.mp4 --audio X.mp3
  --duraciones X.json`. Marca y miniaturas en `prototipos/simulado/marca/` (le gusto la miniatura C,
  sin el letrero «TÚ»). Shorts del canal: de momento NO.
