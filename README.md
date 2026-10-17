# ver-video

Plugin para Claude Code que le permite a Claude **ver, escuchar y analizar videos**
(YouTube, otros sitios o archivos locales).

## Qué hace (y qué no)

Claude no percibe video continuo como una persona. Este plugin le da lo más
cercano posible:

| Sentido | Cómo se logra |
|---|---|
| **Ver** | Un fotograma cada 2 s (ajustable a 0.5 s), agrupados en hojas 3×3 con la hora impresa. Claude revisa 9 momentos por imagen, en orden. |
| **Oír** | Transcripción local con Whisper (`faster-whisper`), sin depender de subtítulos. Si Whisper no está, usa los subtítulos del sitio. |
| **Notar cambios** | Detección de cortes de escena con ffmpeg, marcados con ✂ en las hojas. |
| **Mirar de cerca** | `zoom`: fotogramas a resolución completa en el instante que interese (niveles, números, parámetros de un indicador). |
| **Segunda opinión** | `gemini` (opcional): envía el video completo a Gemini, que procesa video y audio nativamente. |

Todo se une en `timeline.md`: cada hoja de fotogramas junto a lo que se dice en ese tramo.

Limitaciones: entre un fotograma y otro hay huecos (2 s por defecto); el
movimiento rápido puede perderse si no bajas el intervalo. Videos de más de
~12 minutos suben el intervalo automáticamente; para detalle usa `--start/--end`.

## Instalación

### 1. Dependencias (una vez)

**Windows:**

Doble clic en **`instalar_todo.bat`** (instala Python, ffmpeg, paquetes y copia
la skill a `%USERPROFILE%\.claude\skills\ver-video`; deja el registro en
`install_log.txt`). Alternativa: `powershell -ExecutionPolicy Bypass -File .\install.ps1`.

Notas de Windows:
- Usa **Python 3.12** (`py -3.12`): Whisper aún no funciona con Python 3.14.
- Si tienes GPU NVIDIA sin CUDA instalado, Whisper pasa solo a CPU.
- Instala Deno (`winget install DenoLand.Deno`) para que yt-dlp funcione bien con YouTube.


**macOS / Linux:** `./install.sh`

La primera transcripción descarga el modelo Whisper `small` (~500 MB).
Con tarjeta NVIDIA es mucho más rápido; en CPU, un video de 20 min tarda
unos minutos. Cambia el modelo con `--whisper-model base` (más rápido) o
`medium` (más preciso).

### 2. Instalar el plugin en Claude

**Claude Desktop (sesión Code):** Customize → Plugins → Add → Add marketplace →
Add from a repository → pega la URL de tu repositorio en GitHub → Sync →
instala **ver-video**.

**Claude Code en terminal:**

```text
/plugin marketplace add <tu-usuario>/ver-video
/plugin install ver-video@ver-video
```

**Sin GitHub (carpeta local):** `/plugin marketplace add C:\ruta\a\ver-video`

## Uso

En una sesión **Code**, pide en lenguaje natural:

> Mira este video y extrae las reglas de la estrategia con marcas de tiempo: https://www.youtube.com/watch?v=...

> Analiza del minuto 12 al 18 de este video con un fotograma por segundo y dime qué indicadores usa y con qué parámetros.

O directamente desde la terminal:

```bash
python skills/ver-video/scripts/vervideo.py watch "https://youtu.be/XXXX"
python skills/ver-video/scripts/vervideo.py watch video.mp4 --start 12:00 --end 18:00 --interval 1
python skills/ver-video/scripts/vervideo.py zoom ~/ver-video-salidas/XXXX --at 14:32 --count 3
python skills/ver-video/scripts/vervideo.py gemini "https://youtu.be/XXXX" --prompt "¿Qué reglas de entrada usa?"
python skills/ver-video/scripts/vervideo.py check
```

Las salidas quedan en `~/ver-video-salidas/<id>/` (cámbialo con `VER_VIDEO_HOME`).

## Gemini (opcional)

1. Clave gratuita en https://aistudio.google.com/apikey
2. Guárdala en `~/.config/ver-video/.env` como `GEMINI_API_KEY=...`
   (o como variable de entorno).
3. Modelo por defecto `gemini-2.5-flash`; cámbialo con `GEMINI_MODEL`.

Los videos de YouTube se envían por URL; los locales se suben a Google y se
borran al terminar.

## Estructura

```
.claude-plugin/        manifiestos del plugin y del marketplace
skills/ver-video/      SKILL.md (instrucciones para Claude) y scripts/vervideo.py
install.ps1 / .sh      instaladores de dependencias
```

## Licencia

MIT
