---
name: ver-video
description: Ver, escuchar y analizar un video (URL de YouTube u otro sitio, o archivo local). Úsalo siempre que el usuario pida ver, resumir, analizar o extraer información de un video, por ejemplo una estrategia de trading explicada en YouTube. Convierte el video en hojas de fotogramas con hora, transcripción del audio y cortes de escena alineados en una línea de tiempo.
allowed-tools: Bash, Read
---

# ver-video

`SKILL_DIR` es la carpeta que contiene este archivo. El script está en
`SKILL_DIR/scripts/vervideo.py`. En Windows usa `py -3.12` (Whisper no es compatible aún con Python 3.14); en macOS/Linux `python3`.

## 1. Verificar (solo la primera vez en la sesión)

```bash
py -3.12 "SKILL_DIR/scripts/vervideo.py" check
```

Si `listo_para_watch` es false, dile al usuario que ejecute `instalar_todo.bat`
(Windows) o `install.sh` (macOS/Linux) de este repositorio. No instales nada
con permisos de administrador sin preguntar.

## 2. Procesar el video

```bash
py -3.12 "SKILL_DIR/scripts/vervideo.py" watch "<URL o ruta>"
```

Por defecto usa **muestreo adaptativo**: analiza el video 4 veces por segundo
y guarda un fotograma cada vez que la imagen cambia (también si cambia una zona
pequeña: un texto, una etiqueta de precio, una línea dibujada), más uno de
control cada ≤5 s si nada cambia. `report.json` lista los instantes de cambio
(`visual_events`).

Opciones útiles:
- `--start 12:00 --end 18:30` para un tramo. Úsalo en videos largos: primero
  una pasada general y luego tramos con más detalle.
- `--sensitivity 1` para captar cambios más sutiles (por defecto 2 %);
  `--max-gap 3` para más fotos de control en tramos quietos.
- `--mode fixed --interval 2` para el modo antiguo (una foto cada N segundos).
- `--lang en` si el audio está en inglés (`auto` para detectar).
- `--transcript subs` para usar solo los subtítulos del sitio (más rápido);
  `whisper` para forzar la transcripción local.
- Whisper usa la GPU NVIDIA si está disponible (modelo `large-v3-turbo`, más
  preciso) y si no, la CPU (modelo `small`). Fuerza con `--whisper-model`.

El comando imprime un JSON con la ruta de `timeline.md` y la carpeta de salida.

## 3. Ver el video (obligatorio, no te saltes este paso)

1. Lee `timeline.md` completo.
2. Para **cada** hoja, en orden, abre la imagen con Read y léela junto con lo
   que se dice en ese tramo. Cada hoja tiene 9 fotogramas (izquierda→derecha,
   arriba→abajo) con la hora en amarillo en una franja encima de cada uno
   (con décimas si no cae en segundo exacto); `✂` marca un corte de escena.
   Los fotogramas NO están equiespaciados: dos seguidos muy próximos indican
   que en ese momento algo cambió en pantalla.
3. Lleva notas mentales de lo que cambia entre recuadros: movimiento, texto
   en pantalla, gráficos, niveles de precio, indicadores, gestos.
4. Cuando algo importante se vea pequeño (un número, un nivel, el nombre de
   un indicador, parámetros), haz zoom a resolución completa:

```bash
py -3.12 "SKILL_DIR/scripts/vervideo.py" zoom "<carpeta de salida>" --at 14:32 --count 3 --step 1
```

   y abre las imágenes que devuelve.

## 4. Responder

- Cita marcas de tiempo `[MM:SS]` para cada afirmación.
- Separa lo que **se ve** (fotogramas) de lo que **se dice** (transcripción).
  No afirmes hechos visuales a partir solo del audio, ni al revés.
- Si una parte no quedó clara (por ejemplo, un movimiento rápido entre dos
  fotogramas), dilo y revisa ese tramo con más detalle:
  `watch ... --start MM:SS --end MM:SS --sensitivity 1 --min-gap 0.25`.
- Para videos de trading: extrae reglas de entrada, salida, stop, gestión,
  marco temporal, instrumento e indicadores con sus parámetros, y señala lo
  que el autor no especifica.

## 5. Opcional: Gemini

Si hay `GEMINI_API_KEY`, se puede pedir una segunda opinión con un modelo que
procesa video y audio de forma nativa. Avisa antes al usuario: el video se
envía a Google (los locales se suben y se borran al terminar).

```bash
py -3.12 "SKILL_DIR/scripts/vervideo.py" gemini "<URL o ruta>" --prompt "pregunta concreta"
```

Contrasta su respuesta con tus propias hojas; no la copies sin verificar.
