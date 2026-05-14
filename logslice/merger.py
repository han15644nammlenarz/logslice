"""Merge multiple sorted log slices into a single time-ordered output."""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Iterable, Iterator, List, Optional, Tuple

from logslice.timestamp_parser import parse_timestamp


@dataclass
class MergeStats:
    """Statistics collected during a merge operation."""

    sources: int = 0
    lines_read: int = 0
    lines_written: int = 0
    parse_errors: int = 0


def _timestamped_lines(
    source_id: int,
    lines: Iterable[str],
    stats: MergeStats,
) -> Iterator[Tuple[object, int, str]]:
    """Yield (timestamp, source_id, line) tuples for heap ordering."""
    for line in lines:
        stats.lines_read += 1
        stripped = line.rstrip("\n")
        ts = parse_timestamp(stripped)
        if ts is None:
            stats.parse_errors += 1
            # Emit with a sentinel so unparseable lines sort last per source.
            continue
        yield (ts, source_id, stripped)


def merge_log_sources(
    sources: List[Iterable[str]],
    stats: Optional[MergeStats] = None,
) -> Iterator[str]:
    """Merge multiple iterables of log lines into time-sorted order.

    Lines whose timestamps cannot be parsed are silently skipped and
    counted in ``stats.parse_errors``.

    Args:
        sources: Ordered iterables of log lines (one per file/stream).
        stats:   Optional :class:`MergeStats` instance updated in place.

    Yields:
        Log lines in ascending timestamp order.
    """
    if stats is None:
        stats = MergeStats()

    stats.sources = len(sources)

    iterators = [
        _timestamped_lines(idx, src, stats)
        for idx, src in enumerate(sources)
    ]

    for _ts, _src_id, line in heapq.merge(*iterators, key=lambda t: (t[0], t[1])):
        stats.lines_written += 1
        yield line + "\n"
