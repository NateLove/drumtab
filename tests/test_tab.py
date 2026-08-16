"""Round-trip test: build a known 1-bar rock beat as MIDI, render, assert."""

import os
import tempfile

import mido

from drumtab.tab import TabConfig, midi_to_tab


def _write_beat(path: str, bpm: int = 120) -> None:
    """One bar, 4/4: kick on 1 & 3, snare on 2 & 4, hi-hat on every 8th."""
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0))

    tpb = mid.ticks_per_beat            # ticks per quarter note
    eighth = tpb // 2

    # (tick_offset_from_bar_start, note, velocity)
    events = []
    for i in range(8):                  # hi-hat, 8th notes
        events.append((i * eighth, 42, 90))
    events += [(0, 36, 100), (2 * tpb, 36, 100)]           # kick beats 1 & 3
    events += [(1 * tpb, 38, 100), (3 * tpb, 38, 100)]     # snare beats 2 & 4

    # Build absolute-tick messages (on + off), then emit sorted deltas.
    abs_msgs: list[tuple[int, int, mido.Message]] = []
    for tick, note, vel in events:
        abs_msgs.append((tick, 1, mido.Message("note_on", note=note, velocity=vel)))
        abs_msgs.append((tick + 10, 0, mido.Message("note_off", note=note, velocity=0)))
    abs_msgs.sort(key=lambda x: (x[0], x[1]))  # offs before ons at equal tick

    prev = 0
    for abs_tick, _, msg in abs_msgs:
        track.append(msg.copy(time=abs_tick - prev))
        prev = abs_tick
    mid.save(path)


def test_rock_beat():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "beat.mid")
        _write_beat(p, bpm=120)
        tab = midi_to_tab(p, TabConfig(bpm=120, grid=16))

    lines = {ln.split("|", 1)[0]: ln for ln in tab.splitlines() if "|" in ln}
    assert lines["HH"] == "HH|x-x-x-x-x-x-x-x-|"
    assert lines["SD"] == "SD|----o-------o---|"
    assert lines["BD"] == "BD|o-------o-------|"
    print(tab)


if __name__ == "__main__":
    test_rock_beat()
    print("\nOK")
