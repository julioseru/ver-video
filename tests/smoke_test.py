#!/usr/bin/env python3
"""Prueba rápida de ver-video sin red ni Whisper.

Genera un video sintético tipo gráfico de trading (fondo quieto, un texto pequeño
que aparece, una línea fina que se dibuja y un corte de escena) y comprueba que el
muestreo adaptativo detecta los tres cambios, que el ruido no dispara falsos
cambios y que se generan hojas, línea de tiempo y zoom.

Uso:  python tests/smoke_test.py      (necesita ffmpeg, pillow y numpy)
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "ver-video" / "scripts" / "vervideo.py"


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def watch(video: Path, out: Path, *extra: str) -> dict:
    res = subprocess.run([sys.executable, str(SCRIPT), "watch", str(video), "--out", str(out),
                          "--transcript", "none", *extra],
                         capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, res.stderr
    return json.loads((out / "report.json").read_text(encoding="utf-8"))


def near(times: list[float], target: float, tol: float = 0.3) -> bool:
    return any(abs(t - target) <= tol for t in times)


def main() -> int:
    if not shutil.which("ffmpeg"):
        print("SKIP: falta ffmpeg")
        return 0
    tmp = Path(tempfile.mkdtemp(prefix="vervideo_test_"))
    try:
        # 1) cambios pequeños y corte
        trading = tmp / "trading.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=0x101820:s=1280x720:d=20,format=yuv420p", "-vf",
               "drawbox=x=1040:y=36:w=180:h=30:color=white@1:t=fill:enable='gte(t,7)',"
               "drawbox=x=100:y=300:w=1080:h=4:color=red@1:t=fill:enable='gte(t,11)',"
               "drawbox=x=0:y=0:w=1280:h=720:color=0x204060@1:t=fill:enable='gte(t,15)'",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", str(trading))
        rep = watch(trading, tmp / "o")
        ev = [e["t"] for e in rep["visual_events"]]
        assert near(ev, 7), f"no detectó la etiqueta en 00:07: {ev}"
        assert near(ev, 11), f"no detectó la línea fina en 00:11: {ev}"
        assert near(ev, 15), f"no detectó el corte en 00:15: {ev}"
        assert len(ev) <= 5, f"demasiados eventos falsos: {ev}"
        assert rep["grids"] and Path(rep["grids"][0]).exists(), "no se generó la hoja"
        assert (tmp / "o" / "timeline.md").exists(), "no se generó timeline.md"
        print(f"OK cambios: {ev}")

        # 2) ruido de compresión: no debe disparar
        ruido = tmp / "ruido.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=gray:s=1280x720:d=12", "-vf",
               "noise=alls=8:allf=t,format=yuv420p", "-c:v", "libx264", "-crf", "32", str(ruido))
        rep = watch(ruido, tmp / "r")
        assert not rep["visual_events"], f"el ruido disparó cambios: {rep['visual_events']}"
        assert rep["frames"] >= 3, "faltan fotogramas de control"
        print(f"OK ruido: 0 eventos, {rep['frames']} fotogramas de control")

        # 3) modo fijo y zoom
        rep = watch(trading, tmp / "f", "--mode", "fixed", "--interval", "2")
        assert rep["frames"] == 10, f"modo fijo: esperaba 10 fotogramas, hay {rep['frames']}"
        z = subprocess.run([sys.executable, str(SCRIPT), "zoom", str(tmp / "o"), "--at", "00:12",
                            "--count", "2"], capture_output=True, text=True, encoding="utf-8")
        assert z.returncode == 0 and len(json.loads(z.stdout)["frames"]) == 2, z.stderr
        print("OK modo fijo y zoom")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("TODO OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
