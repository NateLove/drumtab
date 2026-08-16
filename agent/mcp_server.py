"""MCP server exposing drumtab as tools for Claude Desktop / Code / Cowork.

Run it:
    pip install "mcp[cli]"
    python -m agent.mcp_server          # stdio transport

Register it with Claude Code:
    claude mcp add drumtab -- python -m agent.mcp_server

Then just ask: "tab this drum video: <url>" and the agent orchestrates
fetch -> separate -> transcribe -> render itself.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from drumtab.pipeline import Pipeline
from drumtab.stages import render
from drumtab.tab import TabConfig

mcp = FastMCP("drumtab")


def _cfg(bpm: float | None, grid: int, time_sig: str, bars: int | None) -> TabConfig:
    num, den = (int(x) for x in time_sig.split("/"))
    return TabConfig(bpm=bpm, grid=grid, beats_per_bar=num, beat_unit=den, max_bars=bars)


@mcp.tool()
def transcribe_youtube(url: str, out_dir: str = "out", bpm: float | None = None,
                       grid: int = 16, time_sig: str = "4/4", bars: int | None = None,
                       device: str | None = None, lyrics: bool = False,
                       pdf: bool = False) -> str:
    """Fetch a YouTube video (or local audio), isolate drums, transcribe, and
    return an ASCII drum tab. `lyrics` overlays timed words from the vocal
    stem; `pdf` also writes score.pdf (needs MuseScore). `bars` limits length;
    `grid` 16 = 16th notes."""
    pipe = Pipeline(device=device, tab_cfg=_cfg(bpm, grid, time_sig, bars))
    result = pipe.run(url, out_dir, pdf=pdf, lyrics=lyrics)
    from pathlib import Path
    text = Path(result.tab).read_text()
    if result.pdf:
        text += f"\n\n(PDF: {result.pdf})"
    return text


@mcp.tool()
def render_midi(midi_path: str, bpm: float | None = None, grid: int = 16,
                time_sig: str = "4/4", bars: int | None = None) -> str:
    """Render an existing drum MIDI file (e.g. an e-kit capture) to ASCII tab
    without any transcription — exact, not estimated."""
    return render.render_ascii(midi_path, _cfg(bpm, grid, time_sig, bars))


@mcp.tool()
def requantize(midi_path: str, bpm: float, grid: int = 16, time_sig: str = "4/4",
               bars: int | None = None) -> str:
    """Re-render an already-transcribed MIDI at a new tempo/grid/time signature
    to fix alignment, without re-running the slow fetch/separate/ADT stages."""
    return render.render_ascii(midi_path, _cfg(bpm, grid, time_sig, bars))


if __name__ == "__main__":
    mcp.run()
