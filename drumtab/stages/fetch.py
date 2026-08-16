"""Stage 1 — pull audio from a YouTube URL (or accept a local file)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def fetch_audio(url_or_path: str, workdir: str) -> str:
    """Return a path to a WAV. Local files are passed through untouched."""
    if os.path.exists(url_or_path):
        return url_or_path

    os.makedirs(workdir, exist_ok=True)
    out_tmpl = os.path.join(workdir, "source.%(ext)s")
    cmd = [
        "yt-dlp",
        "-x", "--audio-format", "wav",
        "--audio-quality", "0",
        "-o", out_tmpl,
        url_or_path,
    ]
    subprocess.run(cmd, check=True)
    wav = Path(workdir) / "source.wav"
    if not wav.exists():
        raise FileNotFoundError(f"yt-dlp did not produce {wav}")
    return str(wav)
