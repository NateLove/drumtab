# drumtab

Turn a YouTube drum video (or any audio) into a drum tab.

```
YouTube URL ──▶ yt-dlp ──▶ Demucs (isolate drums) ──▶ ADTOF (drums→MIDI) ──▶ tab.py ──▶ ASCII tab
                 fetch        separate                  transcribe            render     (+ MusicXML)
```

Each arrow is one swappable stage. Only the transcription stage is ML you
don't control; the rest — including the MIDI→tab renderer, which is the part
most likely to be wrong if hand-waved — is deterministic and unit-tested.

## Why this shape

Transcribing drums straight off a full mix is noticeably worse than
transcribing an isolated stem. Recent ADT work confirms a "separate then
detect" pipeline (Demucs first, transcribe second) beats end-to-end
transcription, so the Demucs step is load-bearing, not polish. ADTOF is the
current open-source SOTA (CRNN, 5 classes: kick, snare, hi-hat, toms,
cymbals) and emits standard General-MIDI notes, which is exactly what the
renderer reads.

## Install

```bash
# base pipeline + pytorch ADT backend + notation + lyrics
pip install ".[adt,notation,lyrics]"
# ffmpeg must be on PATH (brew install ffmpeg / dnf install ffmpeg-free)
# PDF export also needs the MuseScore app/CLI:
#   brew install --cask musescore   (mac)   |   dnf install musescore   (fedora)
```

The ADT backend defaults to **ADTOF-pytorch** (PyTorch only — no TensorFlow
or madmom, which is the sane choice on Apple Silicon). Point `DRUMTAB_ADT_CMD`
at a different entry point if you install it in its own venv.

## Use

```bash
drumtab "https://youtu.be/VIDEO" -o out/song            # full pipeline
drumtab "https://youtu.be/VIDEO" --bpm 96 --bars 8       # hint tempo, first 8 bars
drumtab drums.wav --time-sig 6/8 --grid 24               # local audio, compound meter
drumtab groove.mid                                       # MIDI only → straight to tab
drumtab "https://youtu.be/VIDEO" --lyrics                # overlay timed lyrics
drumtab "https://youtu.be/VIDEO" --pdf                   # engraved PDF via MuseScore
drumtab "https://youtu.be/VIDEO" --lyrics --pdf --bars-per-line 4
```

Output lands in `out/song/tab.txt` (plus `score.musicxml` / `score.pdf` when
asked). Slow stages (download, separation, transcription) are cached per run,
so re-running with a different `--bpm`/`--grid` is instant.

## Lyrics overlay

`--lyrics` does one full Demucs pass, keeps the **vocal** stem alongside the
drum stem, runs Whisper on it with word timestamps, and snaps each word onto
the same grid as the drum hits — so the words line up column-for-column above
the bars:

```
   Is  thisthe real     lifeor  fan-
HH|x-x-x-x-x-x-x-x-|x-x-x-x-x-x-x-x-|
SD|----o-------o---|----o-------o---|
BD|o-------o-------|o-------o-------|
```

It's a practice guide, not a typesetter: words start at their onset column,
collisions slide right, and anything past the bar edge is clipped. Whisper
model size is set by `DRUMTAB_WHISPER_MODEL` (default `base`). Lyrics only
land in the ASCII tab; the MusicXML/PDF staff stays notation-only.

### TD-17 shortcut

For a part you actually play, capture MIDI off the kit and skip transcription
entirely — `drumtab yourtake.mid` gives an exact tab, no ML guesswork. The
audio route only earns its keep for parts you're *not* playing.

## As an agent (MCP)

```bash
pip install ".[agent]"
claude mcp add drumtab -- python -m agent.mcp_server
```

Then ask Claude "tab this drum video: <url>" and it drives the stages itself.
Tools: `transcribe_youtube`, `render_midi`, `requantize` (re-grid an existing
transcription without re-running the slow stages).

## Reading the tab

Lanes top-to-bottom: `CC` crash · `RD` ride · `HH` hi-hat · `T1/T2/FT` toms ·
`SD` snare · `BD` kick. Glyphs: `x`/`o` hit · `O` open hi-hat · `X` accent or
cross-stick · lowercase = ghost note · `-` rest. Bars split by `|`; empty
lanes are hidden.

## Honest limits

Automatic drum transcription is genuinely hard. Expect a solid draft on
steady grooves and clean recordings, and expect to fix ghost notes, fast
fills, ride-vs-crash calls, and dynamics by ear — treat the output as a
starting chart, not a finished one. This is a personal-practice tool; respect
the rights of whatever you transcribe.

## Layout

```
drumtab/
  cli.py            argparse CLI + MIDI fast-path
  pipeline.py       orchestration (cached, resumable)
  tab.py            MIDI → quantized ASCII tab + lyric overlay  (unit-tested core)
  gm_map.py         General MIDI → lane/glyph mapping
  lyrics.py         Whisper vocal-stem → timed words
  stages/           fetch · separate (multi-stem) · render (ascii/musicxml/pdf)
  backends/adtof.py ADT subprocess adapter (ADTOF / ADTOF-pytorch)
agent/mcp_server.py MCP tools for Claude Desktop/Code/Cowork
tests/              test_tab.py (beat→tab) · test_lyrics.py (word alignment)
```
