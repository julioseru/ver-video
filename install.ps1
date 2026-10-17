# Instalador de ver-video para Windows (PowerShell, sin administrador)
$ErrorActionPreference = "Stop"
Write-Host "== ver-video: instalando dependencias ==" -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Instalando Python 3.12..." ; winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    Write-Host "Cierra y vuelve a abrir PowerShell y ejecuta este script otra vez." ; exit 1
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "Instalando ffmpeg..." ; winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
}
python -m pip install --upgrade pip
python -m pip install -r "$PSScriptRoot\requirements.txt"

$resp = Read-Host "Instalar soporte Gemini (opcional, analiza el video completo con Google)? [s/N]"
if ($resp -match '^[sS]') { python -m pip install google-genai }

Write-Host "`nVerificando..." -ForegroundColor Cyan
python "$PSScriptRoot\skills\ver-video\scripts\vervideo.py" check
Write-Host "`nSi ffmpeg aparece en false, cierra y abre de nuevo la terminal (winget actualiza el PATH)." -ForegroundColor Yellow
