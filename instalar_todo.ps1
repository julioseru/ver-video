# Instalacion desatendida de ver-video (Windows). Registro: install_log.txt
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$log  = Join-Path $root "install_log.txt"
$env:PYTHONUTF8 = "1"

function Refresh-Path {
  $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
}
function Winget-Install($id) {
  winget install -e --id $id --silent --accept-source-agreements --accept-package-agreements 2>&1 |
    Where-Object { $_ -notmatch '^\s*[-\\|/]?\s*$' -and $_ -notmatch '█|▒' }
  Refresh-Path
}

& {
  "== 1/6 Python 3.12 (Whisper aun no funciona con 3.14) =="
  $ok = $false
  try { $v = & py -3.12 --version 2>&1; if ($v -match "3\.12") { $ok = $true } } catch {}
  if (-not $ok) { Winget-Install "Python.Python.3.12"; $v = & py -3.12 --version 2>&1 }
  "Python: $v"

  "== 2/6 ffmpeg =="
  if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { Winget-Install "Gyan.FFmpeg" }
  (Get-Command ffmpeg -ErrorAction SilentlyContinue).Source

  "== 3/6 Deno (lo necesita yt-dlp para YouTube) =="
  if (-not (Get-Command deno -ErrorAction SilentlyContinue)) { Winget-Install "DenoLand.Deno" }
  (Get-Command deno -ErrorAction SilentlyContinue).Source

  "== 4/6 Paquetes de Python =="
  py -3.12 -m pip install --quiet --upgrade pip 2>&1 | Where-Object { $_ -notmatch "Cache entry" }
  py -3.12 -m pip install --quiet -r (Join-Path $root "requirements.txt") 2>&1 | Where-Object { $_ -notmatch "Cache entry" }

  "== 5/6 CUDA para Whisper (solo si hay tarjeta NVIDIA) =="
  if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
    py -3.12 -m pip install --quiet -r (Join-Path $root "requirements-gpu.txt") 2>&1 | Where-Object { $_ -notmatch "Cache entry" }
  } else { "Sin tarjeta NVIDIA: Whisper usara la CPU." }

  "== 6/6 Instalar la skill para Claude =="
  $dest = Join-Path $HOME ".claude\skills\ver-video"
  New-Item -ItemType Directory -Force -Path $dest | Out-Null
  Copy-Item -Recurse -Force (Join-Path $root "skills\ver-video\*") $dest
  "Skill copiada a $dest"

  "== Verificacion =="
  py -3.12 (Join-Path $dest "scripts\vervideo.py") check
  "FIN_INSTALACION"
} *>&1 | Tee-Object -FilePath $log
