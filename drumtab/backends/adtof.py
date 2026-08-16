"""Automatic Drum Transcription backend: ADTOF (drums stem -> MIDI).

Two flavours of the same model exist and both ship a ``drumTranscriptor``
entry point that writes a General-MIDI drum file:

  * MZehren/ADTOF          — original, TensorFlow + madmom (heavier install)
  * xavriley/ADTOF-pytorch — PyTorch only, ~0.2% F-measure lower, far easier
                             to install (recommended, esp. on Apple Silicon)

Both are wrapped here as a subprocess so the model's own environment stays
isolated from this package. Set DRUMTAB_ADT_CMD if your entry point differs
or lives in another venv, e.g.

    export DRUMTAB_ADT_CMD="/opt/adtof/.venv/bin/drumTranscriptor"

The output note numbers follow the GM percussion map, which is exactly what
drumtab.tab expects — no remapping needed.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def _resolve_cmd() -> list[str]:
    override = os.environ.get("DRUMTAB_ADT_CMD")
    if override:
        return override.split()
    exe = shutil.which("drumTranscriptor")
    if exe:
        return [exe]
    raise RuntimeError(
        "No ADT backend found. Install one of:\n"
        "  pip install 'adtof @ git+https://github.com/xavriley/ADTOF-pytorch'\n"
        "  (or MZehren/ADTOF), or set DRUMTAB_ADT_CMD to its entry point."
    )


def transcribe_to_midi(drums_wav: str, out_dir: str) -> str:
    """Transcribe an isolated drum stem to a GM drum MIDI file."""
    os.makedirs(out_dir, exist_ok=True)
    cmd = _resolve_cmd() + [drums_wav, out_dir]
    subprocess.run(cmd, check=True)

    stem = Path(drums_wav).stem
    # ADTOF writes "<stem>.mid" into out_dir; fall back to any new .mid found.
    expected = Path(out_dir) / f"{stem}.mid"
    if expected.exists():
        return str(expected)
    mids = sorted(Path(out_dir).glob("*.mid"), key=lambda p: p.stat().st_mtime)
    if mids:
        return str(mids[-1])
    raise FileNotFoundError(f"ADT backend produced no .mid in {out_dir}")
