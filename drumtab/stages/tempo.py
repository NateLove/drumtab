"""Tempo estimation — recover BPM from the drum stem.

ADTOF's MIDI carries no tempo, so without this the renderer falls back to a
fixed 120 BPM and the barlines drift against the actual groove. We estimate
tempo from the isolated drum stem (cleaner than the full mix) with librosa's
beat tracker and use it as the default when the user doesn't pass --bpm.

Returns None if librosa is unavailable or detection fails, so callers can
fall back gracefully rather than crash.
"""

from __future__ import annotations


def estimate_bpm(drums_wav: str) -> float | None:
    try:
        import librosa
        import numpy as np
    except ImportError:
        return None
    try:
        y, sr = librosa.load(drums_wav)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(np.asarray(tempo).reshape(-1)[0])
        return round(bpm, 1) if bpm and bpm > 0 else None
    except Exception:
        return None
