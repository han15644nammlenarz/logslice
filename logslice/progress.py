"""Simple progress reporting for logslice CLI operations."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProgressState:
    """Mutable state tracked during a slice operation."""
    total_bytes: int = 0
    bytes_processed: int = 0
    start_time: float = field(default_factory=time.monotonic)
    last_report_time: float = field(default_factory=time.monotonic)
    report_interval: float = 1.0  # seconds between updates

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.start_time

    @property
    def percent(self) -> float:
        if self.total_bytes == 0:
            return 0.0
        return min(100.0, self.bytes_processed / self.total_bytes * 100.0)

    @property
    def mb_per_sec(self) -> float:
        elapsed = self.elapsed
        if elapsed == 0:
            return 0.0
        return (self.bytes_processed / (1024 * 1024)) / elapsed


def _erase_line(stream) -> None:
    stream.write("\r\033[K")


def render_progress(state: ProgressState) -> str:
    """Return a single-line progress string."""
    bar_width = 20
    filled = int(bar_width * state.percent / 100)
    bar = "#" * filled + "-" * (bar_width - filled)
    return (
        f"[{bar}] {state.percent:5.1f}%  "
        f"{state.bytes_processed / (1024*1024):.1f} MB  "
        f"{state.mb_per_sec:.1f} MB/s"
    )


def update_progress(
    state: ProgressState,
    new_bytes: int,
    stream=None,
    force: bool = False,
) -> None:
    """Advance *state* by *new_bytes* and maybe print to *stream*."""
    if stream is None:
        stream = sys.stderr
    state.bytes_processed += new_bytes
    now = time.monotonic()
    if force or (now - state.last_report_time) >= state.report_interval:
        state.last_report_time = now
        _erase_line(stream)
        stream.write(render_progress(state))
        stream.flush()


def finish_progress(state: ProgressState, stream=None) -> None:
    """Print the final 100 % line and move to a new line."""
    if stream is None:
        stream = sys.stderr
    state.bytes_processed = state.total_bytes
    _erase_line(stream)
    stream.write(render_progress(state) + "\n")
    stream.flush()
