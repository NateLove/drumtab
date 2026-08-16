"""Orchestrates fetch -> separate -> (detect tempo) -> transcribe -> render.

Stages write into a per-run workdir and are reused when their artifact
already exists, so re-running to tweak grid/tempo doesn't re-download or
re-separate (the slow parts). When the user doesn't pass a tempo, we estimate
it from the drum stem rather than falling back to a fixed 120 BPM.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path

from .backends import adtof
from .stages import fetch, render, separate, tempo
from .tab import TabConfig, Word


@dataclass
class PipelineResult:
    source_audio: str
    drums_stem: str
    midi: str
    tab: str
    bpm: float | None = None
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

        # Fill in tempo from the drum stem unless the user pinned it.
        cfg = self.tab_cfg
        if cfg.bpm is None:
            detected = tempo.estimate_bpm(drums)
            if detected:
                cfg = replace(cfg, bpm=detected)
                print(f"[tempo] detected {detected:g} BPM "
                      f"(pass --bpm to override, or try {detected/2:g}/{detected*2:g} "
                      f"if the groove looks half/double time)", file=sys.stderr)
            else:
                print("[tempo] auto-detect unavailable; using 120 BPM fallback "
                      "(pass --bpm to set it)", file=sys.stderr)

        midi = adtof.transcribe_to_midi(drums, os.path.join(work, "midi"))

        words: list[Word] | None = None
        if lyrics:
            from .lyrics import transcribe_lyrics
            words = transcribe_lyrics(seps["vocals"])

        tab_text = render.render_ascii(midi, cfg, words=words)
        tab_path = os.path.join(out_dir, "tab.txt")
        Path(tab_path).write_text(tab_text)

        xml_path = None
        pdf_path = None
        if musicxml or pdf:
            xml_path = render.render_musicxml(midi, os.path.join(out_dir, "score.musicxml"))
        if pdf:
            pdf_path = render.render_pdf(xml_path, os.path.join(out_dir, "score.pdf"))

        return PipelineResult(audio, drums, midi, tab_path, cfg.bpm,
                              xml_path, pdf_path, words)
