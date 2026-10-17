# ver-video

Plugin para Claude Code que permite a Claude **ver, escuchar y analizar videos**
(YouTube, otros sitios o archivos locales), con marcas de tiempo en cada conclusión.

Pensado para estudiar videos de trading: extraer reglas de entrada y salida,
leer niveles e indicadores en pantalla y separar lo que se **ve** de lo que se **dice**.

## Cómo funciona

| Sentido | Cómo se logra |
|---|---|
| **Ver** | Muestreo adaptativo: el video se analiza 4 veces por segundo y se guarda un fotograma cada vez que la imagen cambia, incluso si cambia una zona pequeña (un texto, una etiqueta de precio, una línea dibujada). En tramos quietos, un fotograma de control cada ≤5 s. |
| **Oír** | Whisper local (`faster-whisper`). Con GPU NVIDIA usa `large-v3-turbo` (más preciso); sin GPU, `small` en CPU. Si no hay Whisper, usa los subtítulos del sitio. |
| **Ordenar** | Hojas 3×3 con la hora de cada fotograma en una franja propia (no tapa la imagen), cortes de escena marcados con ✂ y `timeline.md`, que une cada hoja con lo que se dice en ese tramo. |
| **Mirar de cerca** | `zoom`: fotogramas a resolución completa en cualquier instante. |
| **Segunda opinión** | `gemini` (opcional): envía el video a Gemini, que procesa video y audio de forma nativa. |

### Por qué es distinto a otras herramientas

La mayoría de herramientas que "le dan video" a un modelo hacen una de dos cosas:
leer solo la transcripción, o extraer fotogramas cada N segundos o en los cortes de
escena. Ambas fallan justo en los videos que más interesan para aprender trading,
donde la cámara no se mueve y la información está en detalles pequeños.

| | Transcripción sola | Fotogramas fijos / por escena | **ver-video** |
|---|---|---|---|
| Ve lo que se dibuja en el gráfico | No | Solo si coincide con el muestreo | **Sí: detecta cambios por zonas** (una línea de 4 px, una etiqueta de precio) |
| Desperdicia imágenes cuando no pasa nada | — | Sí (o se salta cosas si el intervalo es largo) | **No: fotos de control solo cada ≤5 s** |
| Sabe *cuándo* aparece cada cosa | No | Aproximado | **Sí: hora exacta, con décimas** |
| Une lo que se ve con lo que se dice | No | Por separado | **Sí: `timeline.md` alinea cada hoja con su tramo de audio** |
| Lee números pequeños en pantalla | No | Con la resolución de la hoja | **Sí: `zoom` a resolución completa** |
| Funciona sin subtítulos y sin enviar audio a terceros | Depende | Depende | **Sí: Whisper local, en GPU si la hay** |
| Instalación en Windows | Manual | Manual | **Un doble clic** |
| Verificado | — | — | **Prueba automática + CI en cada cambio** |

La clave técnica es la detección **por zonas**: la imagen se divide en 144 zonas y
basta con que cambie el 4 % de una de ellas (una línea de tendencia, un nivel, un
texto) para guardar ese instante, aunque el resto de la pantalla siga igual. Una
detección de escenas global no lo ve, porque ese cambio es menos del 1 % de la imagen.

¿Cuándo usar otra cosa? Si solo necesitas un resumen de lo que se *dice*, basta con
la transcripción. Si quieres que un modelo procese el video de forma nativa,
`ver-video gemini` te da esa segunda opinión.

### Qué no hace

Claude no percibe video continuo: ve fotogramas. El muestreo adaptativo hace que
no se pierda ningún cambio visual que dure más de ~0.25 s, pero el movimiento
continuo (gestos, scroll) se resume en un fotograma cada ~0.5 s. Videos con
mucho movimiento se acotan a 360 fotogramas por pasada; usa `--start/--end`
para más detalle en un tramo.

## Instalación

### Windows

1. Descarga o clona este repositorio.
2. Doble clic en **`instalar_todo.bat`**. Instala, sin preguntas:
   - Python 3.12 (Whisper aún no funciona con 3.14), ffmpeg y Deno (yt-dlp lo necesita para YouTube), con `winget`.
   - `yt-dlp`, `pillow`, `numpy` y `faster-whisper`.
   - Si hay tarjeta NVIDIA: las librerías CUDA para Whisper (cuBLAS y cuDNN, ~1 GB).
   - La skill en `%USERPROFILE%\.claude\skills\ver-video`.

   Al final muestra una verificación y deja el registro en `install_log.txt`.
3. Opcional: `probar.bat` hace una prueba completa con un video de YouTube y compara GPU y CPU.

### macOS / Linux

```bash
./install.sh
```

### Como plugin de Claude Code (opcional)

Si prefieres instalarlo como plugin en vez de skill personal:

```text
/plugin marketplace add <tu-usuario>/ver-video
/plugin install ver-video@ver-video
```

En Claude Desktop: Customize → Plugins → Add → Add marketplace → Add from a repository → URL del repositorio.

## Uso

En una sesión **Code** de Claude, en lenguaje natural:

> Mira este video y extrae las reglas de la estrategia con marcas de tiempo: https://www.youtube.com/watch?v=...

> Analiza del minuto 12 al 18 de este video y dime qué indicadores usa y con qué parámetros.

Desde la terminal:

```bash
py -3.12 skills/ver-video/scripts/vervideo.py watch "https://youtu.be/XXXX"
py -3.12 skills/ver-video/scripts/vervideo.py watch video.mp4 --start 12:00 --end 18:00 --sensitivity 1
py -3.12 skills/ver-video/scripts/vervideo.py zoom ~/ver-video-salidas/XXXX --at 14:32 --count 3
py -3.12 skills/ver-video/scripts/vervideo.py gemini "https://youtu.be/XXXX" --prompt "¿Qué reglas de entrada usa?"
py -3.12 skills/ver-video/scripts/vervideo.py check
```

(En macOS/Linux usa `python3` en lugar de `py -3.12`.)

Las salidas quedan en `~/ver-video-salidas/<id>/`: `timeline.md`, `grids/`,
`transcripcion.txt` y `report.json` (incluye los instantes de cambio visual).
Cambia la carpeta con la variable `VER_VIDEO_HOME`.

### Opciones principales de `watch`

| Opción | Por defecto | Qué hace |
|---|---|---|
| `--mode` | `smart` | `smart` (adaptativo) o `fixed` (una foto cada `--interval` s) |
| `--sensitivity` | `2` | % de la imagen que debe cambiar; menor = más fotos |
| `--max-gap` | `5` | segundos máximos sin fotograma en tramos quietos |
| `--min-gap` | `0.5` | segundos mínimos entre fotos (salvo cortes/destellos) |
| `--sample-fps` | `4` | instantes analizados por segundo |
| `--start` / `--end` | todo | tramo a analizar (`MM:SS` o `H:MM:SS`) |
| `--lang` | `es` | idioma del audio (`es`, `en`, `auto`) |
| `--whisper-model` | `auto` | `large-v3-turbo` con GPU, `small` sin GPU |
| `--transcript` | `auto` | `auto`, `whisper`, `subs`, `none` |

Variables de entorno: `VER_VIDEO_DEVICE` (`cuda`/`cpu`), `VER_VIDEO_WHISPER`
(modelo fijo), `VER_VIDEO_HOME`, `GEMINI_API_KEY`, `GEMINI_MODEL`.

## GPU (CUDA)

Con una tarjeta NVIDIA, Whisper transcribe de 5 a 10 veces más rápido, lo que
permite usar el modelo grande (`large-v3-turbo`): menos errores en español y en
jerga técnica. No hace falta instalar el CUDA Toolkit; basta el controlador
NVIDIA y `pip install -r requirements-gpu.txt` (lo hace el instalador). Si la
GPU falla, Whisper pasa solo a la CPU.

## Gemini (opcional)

1. Clave gratuita en https://aistudio.google.com/apikey
2. Guárdala en `~/.config/ver-video/.env` como `GEMINI_API_KEY=...`
3. `pip install google-genai`

Los videos de YouTube se envían por URL; los locales se suben a Google y se
borran al terminar.

## Estructura

```
.claude-plugin/          manifiestos del plugin y del marketplace
skills/ver-video/        SKILL.md (instrucciones para Claude) y scripts/vervideo.py
instalar_todo.bat/.ps1   instalador de Windows
probar.bat/.ps1          prueba completa en tu PC (YouTube real, GPU vs CPU)
install.sh               instalador de macOS/Linux
requirements*.txt        dependencias (base y GPU)
tests/smoke_test.py      prueba automática (sin red ni Whisper); la corre el CI
```

## Pruebas

```bash
python tests/smoke_test.py
```

Genera un video sintético tipo gráfico de trading y comprueba que se detectan una
etiqueta pequeña que aparece, una línea fina de 4 px que se dibuja y un corte de
escena, y que el ruido de compresión no genera falsos cambios. GitHub Actions la
ejecuta en cada cambio.

## Licencia

[MIT](LICENSE): libre para descargar, usar, modificar y redistribuir, también con fines comerciales.
Contribuciones bienvenidas: abre un *issue* o un *pull request*.
