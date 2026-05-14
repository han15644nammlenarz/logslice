"""High-level slicing pipeline that wires together binary search, filtering,
chunking, and stream writing."""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Optional

from logslice.binary_search import find_start_offset, find_end_offset
from logslice.filter import FilterConfig, apply_filter
from logslice.stats import SliceStats, start_timer, stop_timer, slice_size_bytes
from logslice.timestamp_parser import parse_timestamp


def run_pipeline(
    log_path: Path,
    output: io.IOBase,
    *,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    filter_config: Optional[FilterConfig] = None,
    chunk_size: int = 64 * 1024,
) -> SliceStats:
    """Extract a time-bounded, optionally filtered slice from *log_path*.

    Parameters
    ----------
    log_path:
        Path to the log file to read.
    output:
        Writable binary stream that receives matching lines.
    start:
        Inclusive lower bound; ``None`` means beginning of file.
    end:
        Inclusive upper bound; ``None`` means end of file.
    filter_config:
        Optional regex-based line filter applied after time slicing.
    chunk_size:
        Read buffer size in bytes.

    Returns
    -------
    SliceStats
        Populated statistics object for the completed run.
    """
    if filter_config is None:
        filter_config = FilterConfig()

    stats = SliceStats()
    start_timer(stats)

    file_size = log_path.stat().st_size

    with log_path.open("rb") as fh:
        start_offset = find_start_offset(fh, file_size, start, parse_timestamp) if start else 0
        end_offset = find_end_offset(fh, file_size, end, parse_timestamp) if end else file_size

        stats.start_offset = start_offset
        stats.end_offset = end_offset

        fh.seek(start_offset)
        remaining = end_offset - start_offset
        lines_written = 0

        def _iter_lines() -> object:
            nonlocal remaining
            buf = b""
            while remaining > 0:
                chunk = fh.read(min(chunk_size, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    yield (line + b"\n").decode(errors="replace")
            if buf:
                yield buf.decode(errors="replace")

        for line in apply_filter(_iter_lines(), filter_config):
            encoded = line.encode()
            output.write(encoded)
            lines_written += 1

    stats.lines_written = lines_written
    stop_timer(stats)
    return stats
