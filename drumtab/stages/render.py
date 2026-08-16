"""Stage 4 — render the drum MIDI into readable output.

- ASCII tab (+ optional lyric overlay): always available, pure-python.
- MusicXML: needs music21. Open in MuseScore for engraved notation.
- PDF: needs the MuseScore CLI (mscore / musescore). Converts the MusicXML.
"""

from __future__ import annotations

import os
import shutil
import subprocess

from ..tab import TabConfig, Word, midi_to_tab


def render_ascii(midi_path: str, cfg: TabConfig | None = None,
                 words: list[Word] | None = None) -> str:
    return midi_to_tab(midi_path, cfg, words=words)


def render_musicxml(midi_path: str, out_path: str) -> str:
    try:
        from music21 import converter
    except ImportError as e:
        raise RuntimeError("music21 not installed: pip install '.[notation]'") from e
    converter.parse(midi_path).write("musicxml", fp=out_path)
    return out_path


def _find_musescore() -> str:
    override = os.environ.get("DRUMTAB_MSCORE")
    if override:
        return override
    for name in ("mscore", "musescore", "MuseScore4", "mscore4portable", "MuseScore3"):
        exe = shutil.which(name)
        if exe:
            return exe
    mac = "/Applications/MuseScore 4.app/Contents/MacOS/mscore"
    if os.path.exists(mac):
        return mac
    raise RuntimeError(
        "MuseScore CLI not found. Install MuseScore (brew install --cask musescore, "
        "or dnf/apt install musescore), or set DRUMTAB_MSCORE to the binary."
    )


def render_pdf(musicxml_path: str, out_pdf: str) -> str:
    """Convert MusicXML to PDF headlessly via the MuseScore CLI."""
    exe = _find_musescore()
    subprocess.run([exe, "-o", out_pdf, musicxml_path], check=True)
    return out_pdf


def render_tab_pdf(tab_text: str, out_pdf: str, font_size: int = 9) -> str:
    """Typeset the ASCII tab (including any lyric overlay) as a monospaced PDF.

    Uses a fixed-width font so the column alignment between the lyric line and
    the bars is preserved exactly as it appears in tab.txt. This is the
    "PDF with words" path — unlike the engraved score, it keeps the lyrics."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas
    except ImportError as e:
        raise RuntimeError("reportlab not installed: pip install '.[notation]'") from e

    width, height = letter
    left, bottom, top = 0.5 * inch, 0.6 * inch, height - 0.6 * inch
    leading = font_size + 2

    c = canvas.Canvas(out_pdf, pagesize=letter)
    c.setFont("Courier", font_size)
    y = top
    for line in tab_text.split("\n"):
        if y < bottom:
            c.showPage()
            c.setFont("Courier", font_size)
            y = top
        c.drawString(left, y, line)
        y -= leading
    c.save()
    return out_pdf
