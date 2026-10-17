#!/usr/bin/env python3
"""
ver-video: convierte un video (URL de YouTube u otro sitio, o archivo local) en
evidencia que Claude puede "ver" y "oír":

  - Fotogramas densos (por defecto 1 cada 2 s) agrupados en hojas 3x3 con la
    hora impresa en cada recuadro (storyboard).
  - Detección de cambios de escena.
  - Transcripción del audio con Whisper local (faster-whisper) o, si no está
    disponible, con los subtítulos del sitio.
  - Una línea de tiempo (timeline.md) que une cada hoja con lo que se dice en
    ese tramo.

Subcomandos:
  watch  <url|ruta>          Procesa el video completo (o un tramo).
  zoom   <video> --at MM:SS  Extrae fotogramas a resolución completa en un instante.
  gemini <url|ruta>          Envía el video completo a Gemini (necesita GEMINI_API_KEY).
  check                      Verifica dependencias.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ----------------------------------------------------------------- utilidades


def log(msg: str) -> None:
    print(f"[ver-video] {msg}", file=sys.stderr, flush=True)


def fmt_ts(sec: float) -> str:
    sec = max(0, int(math.floor(sec + 1e-6)))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def parse_ts(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    parts = [float(p) for p in str(value).split(":")]
    sec = 0.0
    for p in parts:
        sec = sec * 60 + p
    return sec


def run(cmd: list[str], capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=capture, text=True,
                          encoding="utf-8", errors="replace")


def need(binary: str) -> str:
    path = shutil.which(binary)
    if not path:
        sys.exit(f"Falta '{binary}'. Ejecuta el instalador (install.ps1 / install.sh).")
    return path


def is_url(s: str) -> bool:
    return bool(re.match(r"^https?://", s, re.I))


def ytdlp_cmd() -> list[str]:
    if shutil.which("yt-dlp"):
        return ["yt-dlp"]
    return [sys.executable, "-m", "yt_dlp"]


def default_out(source: str) -> Path:
    base = Path(os.environ.get("VER_VIDEO_HOME", Path.home() / "ver-video-salidas"))
    if is_url(source):
        m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{6,})", source)
        name = m.group(1) if m else re.sub(r"\W+", "_", source)[-40:]
    else:
        name = Path(source).stem
    return base / re.sub(r"[^\w.-]+", "_", name)


# ----------------------------------------------------------------- descarga


def download(url: str, out: Path, lang: str) -> tuple[Path, dict]:
    out.mkdir(parents=True, exist_ok=True)
    existing = sorted(out.glob("video.*"))
    existing = [p for p in existing if p.suffix.lower() in (".mp4", ".mkv", ".webm")]
    info_path = out / "video.info.json"
    if existing and info_path.exists():
        log("Video ya descargado, reutilizando.")
        return existing[0], json.loads(info_path.read_text(encoding="utf-8"))

    log("Descargando video (máx. 720p) y subtítulos disponibles...")
    cmd = ytdlp_cmd() + [
        "-f", "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720]/bv*+ba/b",
        "--merge-output-format", "mp4",
        "--write-info-json", "--write-subs", "--write-auto-subs",
        "--sub-langs", f"{lang}.*,{lang},en.*,en",
        "--sub-format", "vtt", "--convert-subs", "vtt",
        "--no-playlist", "--ignore-errors",
        "-o", str(out / "video.%(ext)s"), url,
    ]
    res = run(cmd, capture=False)
    files = [p for p in out.glob("video.*") if p.suffix.lower() in (".mp4", ".mkv", ".webm")]
    if not files:
        sys.exit(f"No se pudo descargar el video (código {res.returncode}).")
    info = json.loads(info_path.read_text(encoding="utf-8")) if info_path.exists() else {}
    return files[0], info


# ----------------------------------------------------------------- análisis de video


def probe_duration(video: Path) -> float:
    res = run([need("ffprobe"), "-v", "error", "-show_entries", "format=duration",
               "-of", "default=nw=1:nk=1", str(video)])
    try:
        return float(res.stdout.strip())
    except ValueError:
        sys.exit(f"No se pudo leer la duración de {video}")


def extract_frames(video: Path, out: Path, start: float, end: float,
                   interval: float, width: int) -> list[tuple[float, Path]]:
    fdir = out / "frames"
    if fdir.exists():
        shutil.rmtree(fdir)
    fdir.mkdir(parents=True)
    log(f"Extrayendo fotogramas cada {interval:g} s ({fmt_ts(start)}–{fmt_ts(end)})...")
    cmd = [need("ffmpeg"), "-hide_banner", "-loglevel", "error",
           "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(video),
           "-vf", f"fps=1/{interval},scale={width}:-2", "-q:v", "3",
           str(fdir / "f_%05d.jpg")]
    res = run(cmd)
    if res.returncode != 0:
        sys.exit(f"ffmpeg falló: {res.stderr[-500:]}")
    frames = sorted(fdir.glob("f_*.jpg"))
    # El filtro fps toma el primer fotograma en t=start y luego cada 'interval'.
    return [(start + i * interval, p) for i, p in enumerate(frames)]


def detect_scenes(video: Path, start: float, end: float, threshold: float) -> list[float]:
    log("Detectando cambios de escena...")
    cmd = [need("ffmpeg"), "-hide_banner", "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
           "-i", str(video), "-vf", f"scale=320:-2,select='gt(scene,{threshold})',showinfo",
           "-an", "-f", "null", "-"]
    res = run(cmd)
    times = [start + float(m) for m in re.findall(r"pts_time:([\d.]+)", res.stderr)]
    return times


def build_grids(frames: list[tuple[float, Path]], out: Path, cols: int, rows: int,
                scene_times: list[float]) -> list[dict]:
    from PIL import Image, ImageDraw, ImageFont

    gdir = out / "grids"
    if gdir.exists():
        shutil.rmtree(gdir)
    gdir.mkdir(parents=True)
    per = cols * rows
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
        except OSError:
            font = ImageFont.load_default()

    grids = []
    for gi in range(0, len(frames), per):
        chunk = frames[gi:gi + per]
        imgs = [Image.open(p).convert("RGB") for _, p in chunk]
        w, h = imgs[0].size
        pad = 4
        sheet = Image.new("RGB", (cols * w + (cols + 1) * pad, rows * h + (rows + 1) * pad), (20, 20, 20))
        draw = ImageDraw.Draw(sheet)
        for k, ((t, _), im) in enumerate(zip(chunk, imgs)):
            x = pad + (k % cols) * (w + pad)
            y = pad + (k // cols) * (h + pad)
            sheet.paste(im, (x, y))
            label = fmt_ts(t)
            nxt = chunk[k + 1][0] if k + 1 < len(chunk) else t + (t - chunk[k - 1][0] if k else 0)
            if any(t - 0.01 <= s < nxt for s in scene_times):
                label += "  ✂"  # hay un corte de escena en este tramo
            bbox = draw.textbbox((0, 0), label, font=font)
            draw.rectangle([x, y, x + bbox[2] + 12, y + bbox[3] + 10], fill=(0, 0, 0))
            draw.text((x + 6, y + 4), label, fill=(255, 230, 0), font=font)
        path = gdir / f"hoja_{gi // per + 1:03d}.jpg"
        sheet.save(path, quality=85)
        grids.append({"index": gi // per + 1, "path": str(path),
                      "t0": chunk[0][0], "t1": chunk[-1][0],
                      "frame_times": [t for t, _ in chunk]})
    return grids


# ----------------------------------------------------------------- audio


def parse_vtt(path: Path) -> list[dict]:
    segs, seen = [], set()
    text = path.read_text(encoding="utf-8", errors="replace")
    for block in re.split(r"\n\s*\n", text):
        m = re.search(r"(\d+:)?(\d+):(\d+)[.,](\d+)\s*-->\s*(\d+:)?(\d+):(\d+)[.,](\d+)", block)
        if not m:
            continue
        def to_s(h, mi, s, ms):
            return (int(h[:-1]) if h else 0) * 3600 + int(mi) * 60 + int(s) + int(ms) / 1000
        t0 = to_s(m.group(1), m.group(2), m.group(3), m.group(4))
        t1 = to_s(m.group(5), m.group(6), m.group(7), m.group(8))
        lines = block[m.end():].strip().splitlines()
        clean = " ".join(re.sub(r"<[^>]+>", "", l).strip() for l in lines).strip()
        if clean and clean not in seen:
            seen.add(clean)
            segs.append({"start": t0, "end": t1, "text": clean})
    return segs


def transcribe(video: Path, out: Path, start: float, end: float, lang: str,
               model_name: str, mode: str) -> tuple[list[dict], str]:
    """mode: auto | whisper | subs | none"""
    if mode == "none":
        return [], "ninguna"

    subs = sorted(out.glob("video.*.vtt"))
    if mode in ("auto", "subs") and subs:
        # Prioriza el idioma pedido y subtítulos manuales sobre automáticos.
        subs.sort(key=lambda p: (0 if f".{lang}" in p.name else 1, len(p.name)))
        segs = [s for s in parse_vtt(subs[0]) if s["end"] >= start and s["start"] <= end]
        if segs and mode == "subs":
            return segs, f"subtítulos ({subs[0].name})"
        subs_fallback = (segs, f"subtítulos ({subs[0].name})")
    else:
        subs_fallback = ([], "ninguna")
        if mode == "subs":
            log("No hay subtítulos disponibles.")
            return subs_fallback

    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError:
        if subs_fallback[0]:
            log("faster-whisper no instalado: uso los subtítulos del sitio.")
            return subs_fallback
        log("faster-whisper no instalado y no hay subtítulos: sin transcripción.")
        return [], "ninguna"

    wav = out / "audio.wav"
    log("Extrayendo audio...")
    res = run([need("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y",
               "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(video),
               "-vn", "-ac", "1", "-ar", "16000", str(wav)])
    if res.returncode != 0 or not wav.exists():
        log("El video no tiene pista de audio.")
        return subs_fallback

    device = os.environ.get("VER_VIDEO_DEVICE", "auto")
    log(f"Transcribiendo con Whisper '{model_name}' (la primera vez descarga el modelo)...")
    try:
        model = WhisperModel(model_name, device=device,
                             compute_type="int8" if device in ("auto", "cpu") else "float16")
        seg_iter, info = model.transcribe(str(wav), language=None if lang == "auto" else lang,
                                          vad_filter=True, beam_size=5)
        segs = []
        for s in seg_iter:
            segs.append({"start": start + s.start, "end": start + s.end, "text": s.text.strip()})
        return segs, f"Whisper {model_name} (idioma detectado: {info.language})"
    except Exception as exc:  # noqa: BLE001
        log(f"Whisper falló ({exc}).")
        return subs_fallback


# ----------------------------------------------------------------- línea de tiempo


def write_timeline(out: Path, meta: dict, grids: list[dict], segs: list[dict],
                   scenes: list[float], transcript_src: str) -> Path:
    lines = [
        f"# {meta.get('title') or 'Video'}",
        "",
        f"- Fuente: {meta.get('source')}",
    ]
    if meta.get("uploader"):
        lines.append(f"- Canal: {meta['uploader']}")
    lines += [
        f"- Duración total: {fmt_ts(meta['duration'])} · Tramo analizado: "
        f"{fmt_ts(meta['start'])}–{fmt_ts(meta['end'])}",
        f"- Fotograma cada {meta['interval']:g} s · {len(grids)} hojas de "
        f"{meta['cols']}x{meta['rows']} · {len(scenes)} cambios de escena",
        f"- Transcripción: {transcript_src}",
        f"- Video local: {meta['video']}",
        "",
        "Cada hoja se lee de izquierda a derecha y de arriba abajo. La hora de cada "
        "recuadro está en amarillo; ✂ marca un corte de escena en ese tramo.",
        "",
    ]
    if meta.get("description"):
        desc = meta["description"].strip()
        lines += ["## Descripción del video", "", desc[:1500] + ("…" if len(desc) > 1500 else ""), ""]
    if meta.get("chapters"):
        lines += ["## Capítulos", ""]
        lines += [f"- {fmt_ts(c['start_time'])} {c['title']}" for c in meta["chapters"]]
        lines.append("")

    for g in grids:
        t0 = g["t0"]
        t1 = g["t1"] + meta["interval"]
        lines.append(f"## Hoja {g['index']} · {fmt_ts(t0)}–{fmt_ts(t1)}")
        lines.append("")
        lines.append(f"Imagen: `{g['path']}`")
        cuts = [fmt_ts(s) for s in scenes if t0 <= s < t1]
        if cuts:
            lines.append(f"Cortes de escena: {', '.join(cuts)}")
        said = [s for s in segs if s["start"] < t1 and s["end"] > t0]
        lines.append("")
        if said:
            for s in said:
                lines.append(f"> [{fmt_ts(s['start'])}] {s['text']}")
        else:
            lines.append("> (sin habla en este tramo)")
        lines.append("")

    path = out / "timeline.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    if segs:
        (out / "transcripcion.txt").write_text(
            "\n".join(f"[{fmt_ts(s['start'])}] {s['text']}" for s in segs), encoding="utf-8")
    return path


# ----------------------------------------------------------------- comandos


def cmd_watch(a: argparse.Namespace) -> None:
    need("ffmpeg"); need("ffprobe")
    out = Path(a.out) if a.out else default_out(a.source)
    out.mkdir(parents=True, exist_ok=True)

    if is_url(a.source):
        video, info = download(a.source, out, a.lang if a.lang != "auto" else "es")
    else:
        video = Path(a.source).expanduser().resolve()
        if not video.exists():
            sys.exit(f"No existe el archivo: {video}")
        info = {}

    duration = probe_duration(video)
    start = parse_ts(a.start) or 0.0
    end = min(parse_ts(a.end) or duration, duration)
    if end <= start:
        sys.exit("El tramo pedido está vacío (revisa --start/--end).")
    span = end - start

    per = a.cols * a.rows
    interval = a.interval
    if math.ceil(span / interval) > a.max_grids * per:
        interval = math.ceil(span / (a.max_grids * per) * 10) / 10
        log(f"Video largo: subo el intervalo a {interval:g} s para no pasar de "
            f"{a.max_grids} hojas. Usa --start/--end para ver un tramo con más detalle.")

    frames = extract_frames(video, out, start, end, interval, a.width)
    if not frames:
        sys.exit("No se extrajo ningún fotograma.")
    scenes = detect_scenes(video, start, end, a.scene_threshold)
    grids = build_grids(frames, out, a.cols, a.rows, scenes)
    segs, src = transcribe(video, out, start, end, a.lang, a.whisper_model, a.transcript)

    meta = {
        "source": a.source, "video": str(video), "title": info.get("title") or video.stem,
        "uploader": info.get("uploader"), "description": info.get("description"),
        "chapters": info.get("chapters"), "duration": duration, "start": start, "end": end,
        "interval": interval, "cols": a.cols, "rows": a.rows,
    }
    timeline = write_timeline(out, meta, grids, segs, scenes, src)
    report = {**{k: v for k, v in meta.items() if k != "description"},
              "out_dir": str(out), "timeline": str(timeline),
              "grids": [g["path"] for g in grids], "scene_changes": scenes,
              "transcript_source": src, "transcript_segments": len(segs)}
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "timeline": str(timeline), "out_dir": str(out),
                      "grids": len(grids), "interval": interval,
                      "transcript": src, "scene_changes": len(scenes)}, ensure_ascii=False))


def cmd_zoom(a: argparse.Namespace) -> None:
    need("ffmpeg")
    video = Path(a.video).expanduser()
    if video.is_dir():
        cands = [p for p in video.glob("video.*") if p.suffix.lower() in (".mp4", ".mkv", ".webm")]
        if not cands:
            sys.exit("No encuentro video.* en esa carpeta.")
        video = cands[0]
    at = parse_ts(a.at) or 0.0
    zdir = Path(a.out) if a.out else video.parent / "zoom"
    zdir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(a.count):
        t = at + i * a.step
        p = zdir / f"zoom_{fmt_ts(t).replace(':', '-')}.jpg"
        run([need("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.3f}",
             "-i", str(video), "-frames:v", "1", "-q:v", "2", str(p)])
        if p.exists():
            paths.append(str(p))
    print(json.dumps({"ok": bool(paths), "frames": paths}, ensure_ascii=False))


def cmd_gemini(a: argparse.Namespace) -> None:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        env = Path.home() / ".config" / "ver-video" / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    key = line.split("=", 1)[1].strip()
    if not key:
        sys.exit("Falta GEMINI_API_KEY (variable de entorno o ~/.config/ver-video/.env).")
    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore
    except ImportError:
        sys.exit("Instala el SDK: pip install google-genai")

    client = genai.Client(api_key=key)
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    prompt = a.prompt or ("Describe el video con marcas de tiempo [MM:SS]: qué se ve, qué se dice "
                          "y los puntos clave. Responde en español.")
    uploaded = None
    if is_url(a.source) and re.search(r"youtu\.?be", a.source):
        video_part = types.Part(file_data=types.FileData(file_uri=a.source))
    else:
        path = Path(a.source).expanduser()
        if is_url(a.source):
            out = default_out(a.source)
            path, _ = download(a.source, out, "es")
        log("Subiendo video a Google (se borra al terminar)...")
        uploaded = client.files.upload(file=str(path))
        import time
        while getattr(uploaded.state, "name", str(uploaded.state)) == "PROCESSING":
            time.sleep(3)
            uploaded = client.files.get(name=uploaded.name)
        video_part = uploaded
    try:
        resp = client.models.generate_content(model=model, contents=[video_part, prompt])
        print(resp.text)
    finally:
        if uploaded is not None:
            try:
                client.files.delete(name=uploaded.name)
            except Exception:  # noqa: BLE001
                pass


def cmd_check(_: argparse.Namespace) -> None:
    status = {
        "python": sys.version.split()[0],
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "ffprobe": bool(shutil.which("ffprobe")),
    }
    for mod, key in (("yt_dlp", "yt-dlp"), ("PIL", "pillow"),
                     ("faster_whisper", "faster-whisper"), ("google.genai", "google-genai")):
        try:
            __import__(mod)
            status[key] = True
        except ImportError:
            status[key] = bool(shutil.which(key)) if key == "yt-dlp" else False
    status["gemini_key"] = bool(os.environ.get("GEMINI_API_KEY")) or \
        (Path.home() / ".config" / "ver-video" / ".env").exists()
    status["listo_para_watch"] = all(status[k] for k in ("ffmpeg", "ffprobe", "pillow"))
    print(json.dumps(status, indent=2))


def main() -> None:
    p = argparse.ArgumentParser(prog="vervideo", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("watch", help="procesar un video")
    w.add_argument("source", help="URL o ruta al archivo")
    w.add_argument("--out", help="carpeta de salida")
    w.add_argument("--start", help="inicio del tramo (MM:SS o H:MM:SS)")
    w.add_argument("--end", help="fin del tramo")
    w.add_argument("--interval", type=float, default=2.0, help="segundos entre fotogramas (def. 2)")
    w.add_argument("--cols", type=int, default=3)
    w.add_argument("--rows", type=int, default=3)
    w.add_argument("--width", type=int, default=480, help="ancho de cada recuadro en px")
    w.add_argument("--max-grids", type=int, default=40, help="tope de hojas (def. 40 = 360 fotogramas)")
    w.add_argument("--scene-threshold", type=float, default=0.3)
    w.add_argument("--lang", default="es", help="idioma del audio (es, en, auto)")
    w.add_argument("--whisper-model", default=os.environ.get("VER_VIDEO_WHISPER", "small"),
                   help="tiny, base, small, medium, large-v3")
    w.add_argument("--transcript", choices=["auto", "whisper", "subs", "none"], default="auto")
    w.set_defaults(func=cmd_watch)

    z = sub.add_parser("zoom", help="fotogramas a resolución completa")
    z.add_argument("video", help="archivo de video o carpeta de salida de watch")
    z.add_argument("--at", required=True, help="instante MM:SS")
    z.add_argument("--count", type=int, default=1)
    z.add_argument("--step", type=float, default=1.0)
    z.add_argument("--out")
    z.set_defaults(func=cmd_zoom)

    g = sub.add_parser("gemini", help="análisis nativo de video con Gemini")
    g.add_argument("source")
    g.add_argument("--prompt")
    g.set_defaults(func=cmd_gemini)

    c = sub.add_parser("check", help="verificar dependencias")
    c.set_defaults(func=cmd_check)

    a = p.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
