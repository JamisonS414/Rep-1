"""Download, cut and reframe -- the ffmpeg/yt-dlp side of the pipeline."""

from __future__ import annotations

import json
import os

from clipper.util import Candidate, require_tool, run, slug, timecode

YTDLP_HINT = "pip install -U yt-dlp"
FFMPEG_HINT = "https://ffmpeg.org/download.html"

SHORTS_W, SHORTS_H = 1080, 1920
SHORTS_MAX_SECONDS = 180  # YouTube raised the Shorts ceiling to 3 minutes


def download(url: str, dest_dir: str, *, max_height: int = 1080) -> str:
    """Fetch a VOD/clip with yt-dlp. Returns the downloaded file path."""
    ytdlp = require_tool("yt-dlp", YTDLP_HINT)
    os.makedirs(dest_dir, exist_ok=True)
    template = os.path.join(dest_dir, "%(id)s.%(ext)s")
    # --print after_move:filepath reports the final path, so we don't have to
    # guess which container yt-dlp settled on.
    proc = run([
        ytdlp,
        "-f", f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]/best",
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--no-simulate", "--print", "after_move:filepath",
        "-o", template,
        url,
    ])
    paths = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if not paths or not os.path.exists(paths[-1]):
        raise RuntimeError(f"yt-dlp did not report a downloaded file for {url!r}")
    return paths[-1]


def probe_duration(path: str) -> float:
    ffprobe = require_tool("ffprobe", FFMPEG_HINT)
    proc = run([
        ffprobe, "-v", "error", "-show_entries", "format=duration",
        "-of", "json", path,
    ])
    return float(json.loads(proc.stdout)["format"]["duration"])


def _vertical_filter(mode: str, blur: int = 20) -> str:
    """Build the filtergraph that turns landscape gameplay into 1080x1920."""
    if mode == "crop":
        # Fills the frame, but shaves the sides -- loses hotbar/health edges.
        return (
            f"scale={SHORTS_W}:{SHORTS_H}:force_original_aspect_ratio=increase,"
            f"crop={SHORTS_W}:{SHORTS_H},setsar=1"
        )
    if mode == "blur":
        # Keeps the whole 16:9 frame, pads with a blurred blow-up of itself.
        return (
            f"[0:v]split=2[bg][fg];"
            f"[bg]scale={SHORTS_W}:{SHORTS_H}:force_original_aspect_ratio=increase,"
            f"crop={SHORTS_W}:{SHORTS_H},gblur=sigma={blur}[bgb];"
            f"[fg]scale={SHORTS_W}:-2[fgs];"
            f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2,setsar=1[v]"
        )
    raise ValueError(f"unknown reframe mode {mode!r} (use 'blur' or 'crop')")


def cut(
    source: str,
    candidate: Candidate,
    out_dir: str,
    *,
    index: int,
    label: str = "clip",
    mode: str = "blur",
    crf: int = 20,
) -> str:
    """Cut one candidate out of `source` and render it vertical."""
    ffmpeg = require_tool("ffmpeg", FFMPEG_HINT)
    os.makedirs(out_dir, exist_ok=True)

    name = f"{index:02d}-{slug(label)}-{timecode(candidate.start).replace(':', 'h', 1).replace(':', 'm')}s.mp4"
    out = os.path.join(out_dir, name)

    cmd = [
        ffmpeg, "-y",
        # -ss before -i seeks fast; re-encoding below keeps the cut frame-accurate.
        "-ss", f"{candidate.start:.3f}",
        "-t", f"{candidate.duration:.3f}",
        "-i", source,
    ]
    graph = _vertical_filter(mode)
    if mode == "blur":
        cmd += ["-filter_complex", graph, "-map", "[v]", "-map", "0:a:0?"]
    else:
        cmd += ["-vf", graph, "-map", "0:v:0", "-map", "0:a:0?"]
    cmd += [
        "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
        "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-r", "30", "-g", "60",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart",
        out,
    ]
    run(cmd)
    return out
