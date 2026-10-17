# Instalacion desatendida de ver-video. Deja el registro en install_log.txt
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$log  = Join-Path $root "install_log.txt"
Start-Transcript -Path $log -Force | Out-Null
$env:PYTHONUTF8 = "1"

function Refresh-Path {
  $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
}
function Find-Python {
  foreach ($c in @("py","python")) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -notlike "*WindowsApps*") {
      $v = & $c --version 2>&1
      if ($v -match "Python 3\.(\d+)" -and [int]$Matches[1] -ge 10) { return $c }
    }
  }
  return $null
}

Write-Host "== 1/5 Python =="
$py = Find-Python
if (-not $py) {
  winget install -e --id Python.Python.3.12 --scope user --silent --accept-source-agreements --accept-package-agreements
  Refresh-Path
  $py = Find-Python
}
if (-not $py) { Write-Host "ERROR: no se pudo instalar Python"; Stop-Transcript; exit 1 }
Write-Host "Python OK: $py ($(& $py --version 2>&1))"

Write-Host "== 2/5 ffmpeg =="
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
  winget install -e --id Gyan.FFmpeg --silent --accept-source-agreements --accept-package-agreements
  Refresh-Path
}
$ff = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($ff) { Write-Host "ffmpeg OK: $($ff.Source)" } else { Write-Host "AVISO: ffmpeg no aparece en PATH todavia (reinicia la terminal)" }

Write-Host "== 3/5 Paquetes de Python =="
& $py -m pip install --upgrade pip --quiet
& $py -m pip install -r (Join-Path $root "requirements.txt")

Write-Host "== 4/5 Instalar skill para Claude =="
$dest = Join-Path $HOME ".claude\skills\ver-video"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Recurse -Force (Join-Path $root "skills\ver-video\*") $dest
Write-Host "Skill copiada a $dest"

Write-Host "== 5/5 Verificacion =="
& $py (Join-Path $dest "scripts\vervideo.py") check
Write-Host "FIN_INSTALACION"
Stop-Transcript | Out-Null
