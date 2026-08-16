"""drumtab CLI:  drumtab <youtube-url|audio|drums.mid> [options]

A .mid input skips straight to rendering (great for e-kit captures off your
TD-17 — exact ground truth, no transcription guesswork). --lyrics needs
audio (it transcribes the vocal stem), so it's ignored for .mid input.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .pipeline import Pipeline
from .stages import render
from .tab import TabConfig


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="drumtab", description="Drum tabs from YouTube.")
    p.add_argument("source", help="YouTube URL, audio file, or drum .mid")
    p.add_argument("-o", "--out", default="out", help="output directory")
    p.add_argument("--bpm", type=float, default=None,
                   help="tempo; auto-detected from the drum stem if omitted")
    p.add_argument("--grid", type=int, default=16, help="grid (16 = 16th notes)")
    p.add_argument("--bars", type=int, default=None, help="limit to N bars")
    p.add_argument("--bars-per-line", type=int, default=None, help="wrap width (systems)")
    p.add_argument("--time-sig", default="4/4", help="e.g. 4/4, 6/8, 7/8")
    p.add_argument("--device", default=None, help="cpu | cuda | mps")
    p.add_argument("--lyrics", action="store_true", help="overlay timed lyrics (needs audio)")
    p.add_argument("--musicxml", action="store_true", help="also emit MusicXML")
    p.add_argument("--pdf", action="store_true", help="also emit engraved PDF (needs MuseScore)")
    p.add_argument("--tab-pdf", action="store_true",
                   help="also emit the ASCII tab as a printable PDF (keeps lyrics)")
    p.add_argument("--no-reuse", action="store_true", help="ignore cached stages")
    return p


def _tab_cfg(args) -> TabConfig:
    num, den = (int(x) for x in args.time_sig.split("/"))
    return TabConfig(bpm=args.bpm, grid=args.grid, beats_per_bar=num, beat_unit=den,
                     max_bars=args.bars, bars_per_line=args.bars_per_line)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = _tab_cfg(args)

    # Fast path: a MIDI file only needs rendering (+ optional notation/PDF).
    if args.source.lower().endswith((".mid", ".midi")):
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        if args.lyrics:
            print("note: --lyrics needs audio; ignored for MIDI input.", file=sys.stderr)
        tab = render.render_ascii(args.source, cfg)
        (out / "tab.txt").write_text(tab)
        print(tab)
        if args.tab_pdf:
            p = render.render_tab_pdf(tab, str(out / "tab.pdf"))
            print(f"-> {p}", file=sys.stderr)
        if args.musicxml or args.pdf:
            xml = render.render_musicxml(args.source, str(out / "score.musicxml"))
            if args.pdf:
                pdf = render.render_pdf(xml, str(out / "score.pdf"))
                print(f"-> {pdf}", file=sys.stderr)
        return 0

    pipe = Pipeline(device=args.device, tab_cfg=cfg, reuse=not args.no_reuse)
    result = pipe.run(args.source, args.out, musicxml=args.musicxml,
                      pdf=args.pdf, lyrics=args.lyrics, tab_pdf=args.tab_pdf)
    print(Path(result.tab).read_text())
    print(f"\n-> {result.tab}", file=sys.stderr)
    for extra in (result.tab_pdf, result.musicxml, result.pdf):
        if extra:
            print(f"-> {extra}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
