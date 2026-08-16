"""Verify timed words snap to the correct bar/column above the tab."""

from drumtab.tab import TabConfig, compute_grid, lyrics_to_bars


def test_word_placement():
    cfg = TabConfig(bpm=120, grid=16)          # cell = 0.125s, bar = 16 cells = 2.0s
    grid = compute_grid(cfg, 120)
    words = [("hello", 0.0), ("world", 1.0), ("again", 2.0)]
    bars = lyrics_to_bars(words, grid, n_bars=2)

    assert bars[0] == "hello   world   "        # col 0 and col 8
    assert bars[1] == "again           "        # start of bar 2
    assert all(len(b) == 16 for b in bars)


def test_collision_slides_right():
    cfg = TabConfig(bpm=120, grid=16)
    grid = compute_grid(cfg, 120)
    # two words land on the same cell; second slides past the first
    bars = lyrics_to_bars([("dont", 0.0), ("stop", 0.0)], grid, n_bars=1)
    assert bars[0].startswith("dontstop")


if __name__ == "__main__":
    test_word_placement()
    test_collision_slides_right()
    print("OK")
