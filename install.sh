#!/usr/bin/env bash
# Instalador de ver-video para macOS / Linux
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
PIP="python3 -m pip install --user"

if ! command -v ffmpeg >/dev/null; then
  if command -v brew >/dev/null; then brew install ffmpeg
  else echo "Instala ffmpeg con tu gestor de paquetes (ej. sudo apt install ffmpeg)"; exit 1; fi
fi
if ! command -v deno >/dev/null; then
  if command -v brew >/dev/null; then brew install deno
  else echo "Aviso: instala Deno (https://deno.com) para que yt-dlp funcione bien con YouTube."; fi
fi

$PIP -r "$DIR/requirements.txt" || $PIP --break-system-packages -r "$DIR/requirements.txt"
if command -v nvidia-smi >/dev/null; then
  $PIP -r "$DIR/requirements-gpu.txt" || $PIP --break-system-packages -r "$DIR/requirements-gpu.txt"
fi

DEST="$HOME/.claude/skills/ver-video"
mkdir -p "$DEST"
cp -R "$DIR/skills/ver-video/." "$DEST/"
echo "Skill copiada a $DEST"
python3 "$DEST/scripts/vervideo.py" check
