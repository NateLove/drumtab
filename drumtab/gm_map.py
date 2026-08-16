"""General MIDI (channel 10) percussion mapping to drum-tab lanes.

The lanes are ordered top-to-bottom the way drummers read a chart:
cymbals up high, kick down low. Each lane declares the GM note numbers
that land in it and the glyph used for a normal hit. A couple of notes
are special-cased in ``symbol_for`` (open hi-hat, accents, ghosts).

ADTOF emits standard GM notes for its 5 classes (kick/snare/hi-hat/
toms/cymbals), so the same table covers both a full 8-piece transcription
and the reduced 5-class model output without special handling.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Lane:
    key: str                       # stable id, e.g. "HH"
    label: str                     # 2-char left-margin label
    notes: frozenset[int]          # GM note numbers routed here
    glyph: str = "x"               # default hit glyph


# Order matters: this is the vertical order of the printed tab.
LANES: list[Lane] = [
    Lane("CC", "CC", frozenset({49, 52, 55, 57}), "X"),   # crash / china / splash
    Lane("RD", "RD", frozenset({51, 53, 59}), "x"),        # ride (+ bell)
    Lane("HH", "HH", frozenset({42, 44, 46}), "x"),        # hi-hat (46 = open, handled below)
    Lane("T1", "T1", frozenset({48, 50}), "o"),            # high tom
    Lane("T2", "T2", frozenset({45, 47}), "o"),            # mid tom
    Lane("FT", "FT", frozenset({41, 43}), "o"),            # floor tom
    Lane("SD", "SD", frozenset({38, 40, 37}), "o"),        # snare (37 = side stick)
    Lane("BD", "BD", frozenset({35, 36}), "o"),            # kick
]

_NOTE_TO_LANE: dict[int, Lane] = {n: lane for lane in LANES for n in lane.notes}

OPEN_HH = 46
SIDE_STICK = 37


def lane_for(note: int) -> Lane | None:
    """Return the lane a GM note belongs to, or None if unmapped."""
    return _NOTE_TO_LANE.get(note)


def symbol_for(note: int, velocity: int) -> str:
    """Pick the glyph for a hit, encoding a few standard articulations.

    - open hi-hat (46)      -> ``O``
    - snare side stick (37) -> ``X`` (cross-stick)
    - ghost note (vel < 40) -> lowercase glyph
    - accent   (vel > 104)  -> uppercase glyph
    """
    lane = lane_for(note)
    if lane is None:
        return "-"
    if note == OPEN_HH:
        return "O"
    if note == SIDE_STICK:
        return "X"
    glyph = lane.glyph
    if velocity and velocity < 40:
        return glyph.lower()
    if velocity and velocity > 104:
        return glyph.upper()
    return glyph
