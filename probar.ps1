# Prueba completa en este PC: CUDA, Whisper GPU vs CPU y muestreo adaptativo.
# Registro: prueba_log.txt
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONUTF8 = "1"
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
$s   = Join-Path $root "skills\ver-video\scripts\vervideo.py"
$url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
$filtro = "symlink|warnings.warn|HF_TOKEN|developer|Cache entry"

function Correr($etiqueta, $device, $carpeta) {
  "== $etiqueta =="
  $env:VER_VIDEO_DEVICE = $device
  $sw = [Diagnostics.Stopwatch]::StartNew()
  py -3.12 $s watch $url --transcript whisper --lang en --out (Join-Path $HOME "ver-video-salidas\$carpeta") 2>&1 |
    ForEach-Object { "$_" } | Where-Object { $_ -notmatch $filtro }
  $sw.Stop()
  "Tiempo total: {0:N1} s" -f $sw.Elapsed.TotalSeconds
  Get-Content (Join-Path $HOME "ver-video-salidas\$carpeta\transcripcion.txt") -Encoding utf8 -ErrorAction SilentlyContinue
}

& {
  "== GPU =="
  if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
    "Instalando cuBLAS + cuDNN (puede tardar, ~1 GB)..."
    py -3.12 -m pip install --quiet -r (Join-Path $root "requirements-gpu.txt") 2>&1 | ForEach-Object { "$_" } | Where-Object { $_ -notmatch $filtro }
  } else { "Sin tarjeta NVIDIA." }

  "== Actualizar skill =="
  Copy-Item -Recurse -Force (Join-Path $root "skills\ver-video\*") (Join-Path $HOME ".claude\skills\ver-video")
  "copiado"

  "== check =="
  py -3.12 $s check

  if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) { Correr "Whisper en GPU (large-v3-turbo)" "cuda" "prueba_gpu" }
  Correr "Whisper en CPU (small)" "cpu" "prueba_cpu"
  "FIN_PRUEBA"
} *>&1 | Tee-Object -FilePath (Join-Path $root "prueba_log.txt")
