"""Shared helpers: process execution, tool discovery, timecode formatting."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


class MissingToolError(RuntimeError):
    """Raised when a required external binary is not on PATH."""


def require_tool(name: str, install_hint: str) -> str:
    path = shutil.which(name)
    if not path:
        raise MissingToolError(f"{name!r} not found on PATH. Install it: {install_hint}")
    return path


def run(cmd: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a command, raising with the tail of stderr if it fails."""
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        text=True,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()[-15:]
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(cmd[:3])}...\n" + "\n".join(tail)
        )
    return proc


def timecode(seconds: float) -> str:
    """Seconds -> H:MM:SS, for naming files and printing source offsets."""
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"


def slug(text: str, limit: int = 60) -> str:
    keep = [c if c.isalnum() else "-" for c in text.lower()]
    out = "".join(keep)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")[:limit] or "clip"


@dataclass(frozen=True)
class Candidate:
    """A moment worth cutting, in source-video seconds."""

    start: float
    end: float
    score: float
    reason: str

    @property
    def duration(self) -> float:
        return self.end - self.start

    def padded(self, lead: float, tail: float, ceiling: float | None = None) -> "Candidate":
        start = max(0.0, self.start - lead)
        end = self.end + tail
        if ceiling is not None:
            end = min(end, ceiling)
        return Candidate(start, end, self.score, self.reason)
