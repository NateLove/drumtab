"""MIDI (drum) -> quantized ASCII drum tab, with optional lyric overlay.

This is the deterministic, testable heart of the pipeline. It has no ML in
it: it takes a drum MIDI file (from ADTOF, a DAW, or an e-kit) and lays the
onsets onto a fixed subdivision grid, then prints lanes. Lyrics, when
supplied as (word, start_seconds) pairs, are snapped onto the *same* grid so
they line up column-for-column above the tab.

The default grid is sixteenth notes, enough for most grooves and fills
without exploding into tuplets. Tempo comes from the MIDI ``set_tempo`` meta
event unless the caller overrides it.
"""

from __future__ import annotations

from dataclasses import dataclass

import mido

from .gm_map import LANES, lane_for, symbol_for

# A timed word: (text, start_seconds). Kept as a plain tuple so this module
# has no dependency on the lyrics/Whisper stage.
Word = tuple[str, float]


@dataclass
class Hit:
    time_s: float
    note: int
    velocity: int


@dataclass
class TabConfig:
    bpm: float | None = None       # None -> read from MIDI (fallback 120)
    grid: int = 16                 # subdivisions per whole note (16 = 16th notes)
    beats_per_bar: int = 4         # numerator of the time signature
    beat_unit: int = 4             # denominator (4 = quarter-note beat)
    max_bars: int | None = None    # cap output length; None = all
    bars_per_line: int | None = None  # wrap into systems; None = auto


@dataclass
class Grid:
    cell_s: float
    cells_per_bar: int


def read_hits(path: str) -> list[Hit]:
    """Extract drum onsets (note_on with velocity > 0) with absolute seconds."""
    mid = mido.MidiFile(path)
    hits: list[Hit] = []
    t = 0.0
    for msg in mid:                # iterating a MidiFile yields delta time in seconds
        t += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            if lane_for(msg.note) is not None:
                hits.append(Hit(t, msg.note, msg.velocity))
    return hits


def read_bpm(path: str, fallback: float = 120.0) -> float:
    for track in mido.MidiFile(path).tracks:
        for msg in track:
            if msg.type == "set_tempo":
                return round(mido.tempo2bpm(msg.tempo), 3)
    return fallback


def compute_grid(cfg: TabConfig, bpm: float) -> Grid:
    cells_per_beat = cfg.grid // cfg.beat_unit          # 16 // 4 = 4 cells per beat
    cells_per_bar = cells_per_beat * cfg.beats_per_bar  # 4 * 4 = 16 cells per bar
    beat_s = 60.0 / bpm
    return Grid(cell_s=beat_s / cells_per_beat, cells_per_bar=cells_per_bar)


def quantize(hits: list[Hit], cfg: TabConfig, bpm: float) -> tuple[dict[str, list[str]], Grid]:
    """Snap hits to the grid and build per-lane glyph rows (one entry per cell)."""
    grid = compute_grid(cfg, bpm)
    if not hits:
        return ({lane.key: [] for lane in LANES}, grid)

    total_cells = int(round(hits[-1].time_s / grid.cell_s)) + 1
    if cfg.max_bars is not None:
        total_cells = min(total_cells, cfg.max_bars * grid.cells_per_bar)
    if total_cells % grid.cells_per_bar:                # pad to whole bars
        total_cells += grid.cells_per_bar - (total_cells % grid.cells_per_bar)

    rows: dict[str, list[str]] = {lane.key: ["-"] * total_cells for lane in LANES}
    for h in hits:
        cell = int(round(h.time_s / grid.cell_s))
        if cell >= total_cells:
            continue
        lane = lane_for(h.note)
        if lane is None:
            continue
        glyph = symbol_for(h.note, h.velocity)
        cur = rows[lane.key][cell]
        rows[lane.key][cell] = glyph if cur == "-" else _louder(cur, glyph)
    return rows, grid


def _louder(a: str, b: str) -> str:
    # uppercase (accent/open/crash) wins over lowercase (ghost) / normal
    return a if a.isupper() and not b.isupper() else b


def lyrics_to_bars(words: list[Word], grid: Grid, n_bars: int) -> list[str]:
    """Place timed words onto the grid, one fixed-width string per bar.

    A word starts at the column of its onset; if that column is taken, it
    slides right to the next free space. Words are clipped at the bar edge
    (a practice chart, not a typesetter)."""
    cpb = grid.cells_per_bar
    bars = [[" "] * cpb for _ in range(n_bars)]
    for text, start_s in sorted(words, key=lambda w: w[1]):
        cell = int(round(start_s / grid.cell_s))
        b, col = divmod(cell, cpb)
        if b >= n_bars:
            continue
        row = bars[b]
        while col < cpb and row[col] != " ":
            col += 1
        for i, ch in enumerate(text.strip()):
            if col + i >= cpb:
                break
            row[col + i] = ch
    return ["".join(r) for r in bars]


def render(rows: dict[str, list[str]], grid: Grid, lyric_bars: list[str] | None = None,
           bars_per_line: int | None = None, drop_empty: bool = True) -> str:
    """Render lanes into bar-delimited ASCII, wrapped into systems.

    When ``lyric_bars`` is given, a lyric line is printed above each system,
    aligned column-for-column with the tab (label width + '|' = 3 chars)."""
    cpb = grid.cells_per_bar
    total = max((len(r) for r in rows.values()), default=0)
    n_bars = total // cpb if cpb else 0
    active = [l for l in LANES
              if not (drop_empty and (not rows[l.key] or all(c == "-" for c in rows[l.key])))]

    if not bars_per_line or bars_per_line <= 0:
        bars_per_line = n_bars or 1
    prefix = "   "                                       # aligns over "XX|"
    single_system = bars_per_line >= n_bars and lyric_bars is None

    lines: list[str] = []
    for start in range(0, n_bars, bars_per_line):
        end = min(start + bars_per_line, n_bars)
        if lyric_bars is not None:
            seg = [lyric_bars[b] if b < len(lyric_bars) else " " * cpb for b in range(start, end)]
            lines.append((prefix + " ".join(seg)).rstrip())
        for lane in active:
            chunks = ["".join(rows[lane.key][b * cpb:(b + 1) * cpb]) for b in range(start, end)]
            lines.append(f"{lane.label}|" + "|".join(chunks) + "|")
        if not single_system:
            lines.append("")
    return "\n".join(lines).rstrip()


def midi_to_tab(path: str, cfg: TabConfig | None = None,
                words: list[Word] | None = None) -> str:
    cfg = cfg or TabConfig()
    bpm = cfg.bpm or read_bpm(path)
    hits = read_hits(path)
    rows, grid = quantize(hits, cfg, bpm)
    total = max((len(r) for r in rows.values()), default=0)
    n_bars = total // grid.cells_per_bar if grid.cells_per_bar else 0

    lyric_bars = lyrics_to_bars(words, grid, n_bars) if words else None
    bpl = cfg.bars_per_line
    if bpl is None and words:                            # wrap for readability when lyrics present
        bpl = 4

    header = f"# {path}\n# {bpm:g} BPM, {cfg.beats_per_bar}/{cfg.beat_unit}, 1/{cfg.grid} grid\n"
    return header + render(rows, grid, lyric_bars=lyric_bars, bars_per_line=bpl)
