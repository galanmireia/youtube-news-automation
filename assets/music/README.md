# Música de fondo

Deja aquí las pistas que quieras usar como música de fondo (`.mp3`, `.m4a`,
`.wav`, `.aac`, `.ogg`). Se elige una al azar por vídeo, se pone a volumen
bajo por debajo de la narración y se le hace fundido de entrada y de salida.

Si esta carpeta está vacía, los vídeos se generan sin música, sin dar error.

## De dónde sacar pistas

Lo más seguro para que el canal siga siendo monetizable es la **Biblioteca de
audio de YouTube** (YouTube Studio → Herramientas → Biblioteca de audio),
filtrando por pistas **sin atribución requerida**: son gratuitas, y al ser de
la propia YouTube no generan reclamaciones de Content ID en el canal.

Si usas una pista que exige atribución, hay que incluir el crédito en la
descripción del vídeo.

No metas aquí música comercial (Spotify, discos, etc.) aunque parezca que
"no pasa nada": una sola reclamación puede desmonetizar el vídeo.

## Ajustes

- `MUSIC_DIR`: carpeta donde buscar las pistas (por defecto, esta).
- `MUSIC_VOLUME`: volumen de la música, 0.08 por defecto. Subirlo a 0.12 se
  nota bastante; por encima de 0.2 empieza a competir con la voz.
