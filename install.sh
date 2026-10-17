#!/usr/bin/env bash
# Instalador de ver-video para macOS / Linux
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
if ! command -v ffmpeg >/dev/null; then
  if command -v brew >/dev/null; then brew install ffmpeg
  else echo "Instala ffmpeg con tu gestor de paquetes (ej. sudo apt install ffmpeg)"; exit 1; fi
fi
python3 -m pip install --user -r "$DIR/requirements.txt" || python3 -m pip install --user --break-system-packages -r "$DIR/requirements.txt"
python3 "$DIR/skills/ver-video/scripts/vervideo.py" check
