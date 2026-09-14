# youtube-news-automation

Canal de YouTube de noticias completamente automatizado. El sistema:

1. Busca noticias nuevas en feeds RSS.
2. Genera un guion (titulo, descripcion, tags y escenas) con Claude.
3. Sintetiza la narracion en voz con Google Cloud Text-to-Speech.
4. Descarga video de stock (Pexels) para cada escena y monta el video final con FFmpeg.
5. Genera subtitulos automaticos (faster-whisper) y una miniatura.
6. Te envia el video por Telegram con botones **Aprobar** / **Rechazar**.
7. Si apruebas, lo sube automaticamente a YouTube con la Data API v3.

Todo corre como un unico proceso (bot de Telegram + tarea periodica) pensado para desplegarse en Railway.

## 1. Requisitos y cuentas a crear

| Servicio | Para que | Donde |
|---|---|---|
| Anthropic API key | Generar guion/titulo/descripcion | https://console.anthropic.com |
| Pexels API key | Video de stock | https://www.pexels.com/api/ |
| Google Cloud project + Service Account | Texto a voz | https://console.cloud.google.com (habilita "Cloud Text-to-Speech API", crea una cuenta de servicio y descarga el JSON) |
| Google Cloud OAuth Client (Desktop app) | Subida a YouTube (Data API v3) | Mismo proyecto de Google Cloud, habilita "YouTube Data API v3" y crea credenciales OAuth de tipo "Desktop app" |
| Bot de Telegram | Aprobar/rechazar videos | Habla con @BotFather en Telegram, `/newbot` |
| Railway | Hosting 24/7 | https://railway.app |

## 2. Configuracion local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Rellena `.env` con tus claves. Coloca los archivos de credenciales de Google en `credentials/`:

- `credentials/google-tts.json` -> JSON de la cuenta de servicio de Text-to-Speech.
- `credentials/youtube_client_secret.json` -> JSON del cliente OAuth de escritorio para YouTube.

Para obtener tu `TELEGRAM_CHAT_ID`, escribe cualquier mensaje a tu bot y visita:
`https://api.telegram.org/bot<TU_TOKEN>/getUpdates` (ahi aparece `chat.id`).

## 3. Autorizar YouTube (una sola vez, en tu ordenador)

La subida a YouTube usa OAuth y necesita que abras un navegador para dar permiso la primera vez,
algo que no se puede hacer en un servidor sin pantalla. Hazlo en local:

```bash
python -m scripts.authorize_youtube
```

Se abrira el navegador, inicias sesion con la cuenta de YouTube del canal y aceptas. Esto genera
`credentials/youtube_token.json`, que ya se reutiliza (y se refresca solo) en cada subida.
Copia ese archivo al servidor de Railway (o su contenido como variable de entorno, ver mas abajo).

## 4. Probar el pipeline en local

```bash
python -m app.main
```

Esto arranca el bot de Telegram y, a los 15 segundos, la primera ejecucion del pipeline. Cada
video generado te llega por Telegram con los botones de aprobacion.

Para forzar una ejecucion manual sin esperar al scheduler:

```bash
python -c "from app.pipeline import run_once; print(run_once())"
```

## 5. Despliegue en Railway

1. Crea un nuevo proyecto en Railway y conectalo a este repositorio (Railway detecta el `Dockerfile` automaticamente).
2. Define las variables de entorno del `.env.example` en la pestana "Variables" del servicio.
3. En vez de subir un volumen, pega el contenido completo de cada archivo JSON de `credentials/`
   en estas 3 variables de entorno adicionales (la app los escribe a disco sola al arrancar):
   - `GOOGLE_TTS_CREDENTIALS_JSON` -> contenido de `credentials/google-tts.json`
   - `YOUTUBE_CLIENT_SECRET_JSON` -> contenido de `credentials/youtube_client_secret.json`
   - `YOUTUBE_TOKEN_JSON` -> contenido de `credentials/youtube_token.json`
4. Despliega. El servicio queda corriendo 24/7: cada `PIPELINE_INTERVAL_SECONDS` genera un video
   nuevo y te avisa por Telegram.

## Estructura del proyecto

```
app/
  config.py            variables de entorno y rutas
  storage.py            estado en SQLite (noticias procesadas, videos, status)
  news_source.py         lectura de feeds RSS
  script_generator.py    guion via Claude
  tts.py                  locucion via Google Cloud TTS
  visuals.py              video de stock via Pexels
  video_builder.py        montaje con FFmpeg
  subtitles.py            subtitulos via faster-whisper
  thumbnail.py            miniatura con Pillow
  youtube_uploader.py     subida via YouTube Data API v3
  telegram_bot.py         bot de aprobacion + scheduler
  main.py                 punto de entrada
scripts/
  authorize_youtube.py    autorizacion OAuth (ejecutar en local, una vez)
```

## Costes

- **Anthropic API**: uso muy bajo por video (unos pocos miles de tokens).
- **Railway**: servicio pequeno 24/7, del orden de unos pocos dolares al mes.
- Todo lo demas (YouTube Data API, Google Cloud TTS, Pexels, Telegram, faster-whisper, FFmpeg)
  se mantiene dentro de sus capas gratuitas para un volumen de 1 video/dia.
