"""Automatic Drum Transcription backend: ADTOF (drums stem -> MIDI).

Wraps the ADTOF-pytorch CLI (xavriley/ADTOF-pytorch), whose entry point is
``adtof`` and which takes flags, not positionals:

    adtof --audio drums.wav --out OUTDIR [--device mps] [--threshold ...]

Set DRUMTAB_ADT_CMD to override the executable (e.g. a different venv), and
DRUMTAB_ADT_DEVICE to run transcription on mps/cuda instead of cpu.
The output notes follow the GM percussion map, which is what drumtab.tab
expects — no remapping needed.
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
    exe = shutil.which("adtof") or shutil.which("drumTranscriptor")
    if exe:
        return [exe]
    raise RuntimeError(
        "No ADT backend found. Install one of:\n"
        "  pip install 'adtof-pytorch @ git+https://github.com/xavriley/ADTOF-pytorch'\n"
        "  (or MZehren/ADTOF), or set DRUMTAB_ADT_CMD to its entry point."
    )


def transcribe_to_midi(drums_wav: str, out_dir: str) -> str:
    """Transcribe an isolated drum stem to a GM drum MIDI file."""
    os.makedirs(out_dir, exist_ok=True)

    before = {p.resolve() for p in Path(out_dir).glob("**/*.mid")}

    cmd = _resolve_cmd() + ["--audio", drums_wav, "--out", out_dir]
    device = os.environ.get("DRUMTAB_ADT_DEVICE")
    if device:
        cmd += ["--device", device]
    subprocess.run(cmd, check=True)

    # ADTOF may write next to the input or into --out; search both.
    candidates = set(Path(out_dir).glob("**/*.mid"))
    candidates |= set(Path(drums_wav).parent.glob("*.mid"))
    new = [p for p in candidates if p.resolve() not in before]
    pool = new or list(candidates)
    if not pool:
        raise FileNotFoundError(
            f"ADT backend produced no .mid in {out_dir} or beside {drums_wav}"
        )
    newest = max(pool, key=lambda p: p.stat().st_mtime)

    # normalise location so the rest of the pipeline finds it predictably
    dest = Path(out_dir) / "drums.mid"
    if newest.resolve() != dest.resolve():
        shutil.copy(newest, dest)
    return str(dest)
