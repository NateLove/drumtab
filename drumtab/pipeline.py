"""Orchestrates fetch -> separate -> transcribe -> render.

Stages write into a per-run workdir and are reused when their artifact
already exists, so re-running to tweak tempo/grid doesn't re-download or
re-separate (the slow parts). Lyrics add a vocal-stem + Whisper path; PDF
adds a MusicXML -> MuseScore conversion.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .backends import adtof
from .stages import fetch, render, separate
from .tab import TabConfig, Word


@dataclass
class PipelineResult:
    source_audio: str
    drums_stem: str
    midi: str
    tab: str
    musicxml: str | None = None
    pdf: str | None = None
    lyrics: list[Word] | None = None


@dataclass
class Pipeline:
    workdir: str = "runs"
    demucs_model: str = "htdemucs"
    device: str | None = None
    tab_cfg: TabConfig = field(default_factory=TabConfig)
    reuse: bool = True

    def run(self, url_or_path: str, out_dir: str, musicxml: bool = False,
            pdf: bool = False, lyrics: bool = False) -> PipelineResult:
        os.makedirs(out_dir, exist_ok=True)
        work = os.path.join(self.workdir, Path(out_dir).name)
        os.makedirs(work, exist_ok=True)

        audio = fetch.fetch_audio(url_or_path, work)

        stems = ("drums", "vocals") if lyrics else ("drums",)
        seps = separate.separate(audio, work, stems, self.demucs_model, self.device)
        drums = seps["drums"]

        midi = adtof.transcribe_to_midi(drums, os.path.join(work, "midi"))

        words: list[Word] | None = None
        if lyrics:
            from .lyrics import transcribe_lyrics
            words = transcribe_lyrics(seps["vocals"])

        tab_text = render.render_ascii(midi, self.tab_cfg, words=words)
        tab_path = os.path.join(out_dir, "tab.txt")
        Path(tab_path).write_text(tab_text)

        xml_path = None
        pdf_path = None
        if musicxml or pdf:
            xml_path = render.render_musicxml(midi, os.path.join(out_dir, "score.musicxml"))
        if pdf:
            pdf_path = render.render_pdf(xml_path, os.path.join(out_dir, "score.pdf"))

        return PipelineResult(audio, drums, midi, tab_path, xml_path, pdf_path, words)
