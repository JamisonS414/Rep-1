"""Loudness-based highlight detection.

We never decode audio in Python. ffmpeg's `ebur128` filter prints a momentary
loudness reading (400ms window) roughly every 100ms to stderr; we parse that
text stream and look for sustained peaks. On a livestream VOD those peaks line
up with reactions -- shouting, fight audio, chat-raiding hype -- which is a good
enough shortlist for a human to skim.
"""

from __future__ import annotations

import re
import subprocess

from clipper.util import Candidate, require_tool

# e.g. "[Parsed_ebur128_0 @ 0x..] t: 12.3  TARGET:-23 LUFS  M: -18.4 S: -21.0 ..."
_LINE = re.compile(r"t:\s*(?P<t>[\d.]+).*?M:\s*(?P<m>-?[\d.inf]+)")

SILENCE_FLOOR = -70.0  # LUFS; ebur128 reports -120 or -inf for digital silence


def loudness_series(path: str) -> list[tuple[float, float]]:
    """Return [(timestamp_seconds, momentary_LUFS)] for the whole file."""
    ffmpeg = require_tool("ffmpeg", "https://ffmpeg.org/download.html")
    proc = subprocess.Popen(
        [ffmpeg, "-nostats", "-i", path, "-map", "a:0",
         "-filter_complex", "ebur128=metadata=1", "-f", "null", "-"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    series: list[tuple[float, float]] = []
    assert proc.stderr is not None
    for line in proc.stderr:
        match = _LINE.search(line)
        if not match:
            continue
        try:
            value = float(match.group("m"))
        except ValueError:  # "-inf"
            value = SILENCE_FLOOR
        series.append((float(match.group("t")), max(value, SILENCE_FLOOR)))
    proc.wait()
    if not series:
        raise RuntimeError(
            f"no loudness samples from {path!r} -- does it have an audio track?"
        )
    return series


def _smooth(values: list[float], window: int) -> list[float]:
    """Moving average, so one transient bang doesn't outrank a sustained moment."""
    if window <= 1:
        return list(values)
    out: list[float] = []
    total = 0.0
    for i, v in enumerate(values):
        total += v
        if i >= window:
            total -= values[i - window]
        out.append(total / min(i + 1, window))
    return out


def _percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    idx = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return ordered[idx]


def find_candidates(
    path: str,
    *,
    percentile: float = 97.0,
    smooth_seconds: float = 3.0,
    min_gap: float = 60.0,
    limit: int = 10,
) -> list[Candidate]:
    """Shortlist the loudest sustained stretches of a VOD.

    `percentile` sets how selective we are; `min_gap` keeps the results spread
    across the stream instead of clustering inside one long fight.
    """
    series = loudness_series(path)
    times = [t for t, _ in series]
    levels = [m for _, m in series]

    step = (times[-1] - times[0]) / max(1, len(times) - 1) or 0.1
    smoothed = _smooth(levels, max(1, int(smooth_seconds / step)))

    # Only consider non-silent samples when picking the threshold, otherwise long
    # quiet stretches drag it down and everything looks like a peak.
    voiced = [v for v in smoothed if v > SILENCE_FLOOR + 1]
    if not voiced:
        return []
    threshold = _percentile(voiced, percentile)

    ranked = sorted(
        (i for i, v in enumerate(smoothed) if v >= threshold),
        key=lambda i: smoothed[i],
        reverse=True,
    )

    picked: list[Candidate] = []
    for i in ranked:
        t = times[i]
        if any(abs(t - c.start) < min_gap for c in picked):
            continue
        picked.append(
            Candidate(
                start=t,
                end=t,
                score=smoothed[i],
                reason=f"loudness peak {smoothed[i]:.1f} LUFS",
            )
        )
        if len(picked) >= limit:
            break

    picked.sort(key=lambda c: c.start)
    return picked
