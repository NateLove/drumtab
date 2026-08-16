"""Stage 2 — isolate stems with Demucs v4.

"Separate then detect": transcription is markedly more accurate on an
isolated drum stem than on the full mix, so this step is load-bearing. When
lyrics are requested we do one full 4-stem pass and reuse both the drums and
vocals stems, rather than running Demucs twice.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def separate(audio_path: str, workdir: str, stems: tuple[str, ...] = ("drums",),
             model: str = "htdemucs", device: str | None = None) -> dict[str, str]:
    """Return {stem_name: wav_path}. A single common stem uses the faster
    ``--two-stems`` mode; multiple stems trigger a full separation."""
    os.makedirs(workdir, exist_ok=True)
    two_stem = len(stems) == 1 and stems[0] in {"drums", "bass", "other", "vocals"}

    cmd = ["demucs", "-n", model, "-o", workdir]
    if two_stem:
        cmd += ["--two-stems", stems[0]]
    if device:                                   # cpu | cuda | mps (Apple Silicon)
        cmd += ["-d", device]
    cmd.append(audio_path)
    subprocess.run(cmd, check=True)

    base = Path(workdir) / model / Path(audio_path).stem
    out: dict[str, str] = {}
    for s in stems:
        p = base / f"{s}.wav"
        if not p.exists():
            raise FileNotFoundError(f"Demucs did not produce {p}")
        out[s] = str(p)
    return out


def separate_drums(audio_path: str, workdir: str, model: str = "htdemucs",
                   device: str | None = None) -> str:
    """Back-compat helper returning just the drums stem path."""
    return separate(audio_path, workdir, ("drums",), model, device)["drums"]
