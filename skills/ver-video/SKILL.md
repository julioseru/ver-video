---
name: ver-video
description: Ver, escuchar y analizar un video (URL de YouTube u otro sitio, o archivo local). Úsalo siempre que el usuario pida ver, resumir, analizar o extraer información de un video, por ejemplo una estrategia de trading explicada en YouTube. Convierte el video en hojas de fotogramas con hora, transcripción del audio y cortes de escena alineados en una línea de tiempo.
allowed-tools: Bash, Read
---

# ver-video

`SKILL_DIR` es la carpeta que contiene este archivo. El script está en
`SKILL_DIR/scripts/vervideo.py`. En Windows usa `python`; en macOS/Linux `python3`.

## 1. Verificar (solo la primera vez en la sesión)

```bash
python "SKILL_DIR/scripts/vervideo.py" check
```

Si `listo_para_watch` es false, dile al usuario que ejecute `install.ps1`
(Windows) o `install.sh` (macOS/Linux) de este repositorio. No instales nada
con permisos de administrador sin preguntar.

## 2. Procesar el video

```bash
python "SKILL_DIR/scripts/vervideo.py" watch "<URL o ruta>"
```

Opciones útiles:
- `--start 12:00 --end 18:30` para un tramo. Úsalo en videos largos: primero
  una pasada general y luego tramos con más detalle.
- `--interval 1` para más densidad (por defecto 2 s). Para gráficos de trading
  que cambian lento, `--interval 3` o `5` basta.
- `--lang en` si el audio está en inglés (`auto` para detectar).
- `--transcript subs` para usar solo los subtítulos del sitio (más rápido);
  `whisper` para forzar la transcripción local.

El comando imprime un JSON con la ruta de `timeline.md` y la carpeta de salida.

## 3. Ver el video (obligatorio, no te saltes este paso)

1. Lee `timeline.md` completo.
2. Para **cada** hoja, en orden, abre la imagen con Read y léela junto con lo
   que se dice en ese tramo. Cada hoja tiene 9 fotogramas (izquierda→derecha,
   arriba→abajo) con la hora en amarillo; `✂` marca un corte de escena.
3. Lleva notas mentales de lo que cambia entre recuadros: movimiento, texto
   en pantalla, gráficos, niveles de precio, indicadores, gestos.
4. Cuando algo importante se vea pequeño (un número, un nivel, el nombre de
   un indicador, parámetros), haz zoom a resolución completa:

```bash
python "SKILL_DIR/scripts/vervideo.py" zoom "<carpeta de salida>" --at 14:32 --count 3 --step 1
```

   y abre las imágenes que devuelve.

## 4. Responder

- Cita marcas de tiempo `[MM:SS]` para cada afirmación.
- Separa lo que **se ve** (fotogramas) de lo que **se dice** (transcripción).
  No afirmes hechos visuales a partir solo del audio, ni al revés.
- Si una parte no quedó clara (por ejemplo, hubo un salto entre fotogramas),
  dilo y ofrece revisar ese tramo con `--interval 0.5`.
- Para videos de trading: extrae reglas de entrada, salida, stop, gestión,
  marco temporal, instrumento e indicadores con sus parámetros, y señala lo
  que el autor no especifica.

## 5. Opcional: Gemini

Si hay `GEMINI_API_KEY`, se puede pedir una segunda opinión con un modelo que
procesa video y audio de forma nativa. Avisa antes al usuario: el video se
envía a Google (los locales se suben y se borran al terminar).

```bash
python "SKILL_DIR/scripts/vervideo.py" gemini "<URL o ruta>" --prompt "pregunta concreta"
```

Contrasta su respuesta con tus propias hojas; no la copies sin verificar.
