"""Lyrics stage — transcribe the (isolated) vocal stem to timed words.

Whisper on the Demucs vocal stem gives cleaner, better-aligned lyrics than
running it on the full mix. Returns ``(word, start_seconds)`` pairs, which
drumtab.tab snaps onto the same grid as the drum hits.

Model size via DRUMTAB_WHISPER_MODEL (tiny/base/small/medium/large-v3);
"base" is a fine default for lyrics-as-a-guide.
"""

from __future__ import annotations

import os

from .tab import Word


def transcribe_lyrics(vocals_path: str, language: str | None = None) -> list[Word]:
    try:
        import whisper
    except ImportError as e:
        raise RuntimeError("whisper not installed: pip install '.[lyrics]'") from e

    model = whisper.load_model(os.environ.get("DRUMTAB_WHISPER_MODEL", "base"))
    result = model.transcribe(vocals_path, word_timestamps=True, language=language)

    words: list[Word] = []
    for seg in result.get("segments", []):
        for w in seg.get("words", []):
            text = w.get("word", "").strip()
            if text:
                words.append((text, float(w["start"])))
    return words
