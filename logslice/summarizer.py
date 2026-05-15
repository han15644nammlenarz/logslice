"""Summarize a log slice: line count, time span, byte size, and rate."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta
from typing import Iterable, Optional

from logslice.timestamp_parser import parse_timestamp


@dataclasses.dataclass
class SummaryResult:
    """Aggregated summary of a processed log slice."""

    line_count: int = 0
    byte_count: int = 0
    first_timestamp: Optional[datetime] = None
    last_timestamp: Optional[datetime] = None
    parse_errors: int = 0

    @property
    def time_span(self) -> Optional[timedelta]:
        """Duration between first and last parsed timestamps."""
        if self.first_timestamp is None or self.last_timestamp is None:
            return None
        return self.last_timestamp - self.first_timestamp

    @property
    def avg_line_bytes(self) -> float:
        """Average bytes per line, or 0 if no lines."""
        if self.line_count == 0:
            return 0.0
        return self.byte_count / self.line_count

    @property
    def lines_per_second(self) -> Optional[float]:
        """Average lines per second over the time span."""
        span = self.time_span
        if span is None:
            return None
        seconds = span.total_seconds()
        if seconds <= 0:
            return None
        return self.line_count / seconds


def summarize_lines(lines: Iterable[str]) -> SummaryResult:
    """Consume *lines* and return a :class:`SummaryResult`.

    Each line is decoded as UTF-8 for byte counting purposes.
    Timestamp parsing failures are counted but do not abort the summary.
    """
    result = SummaryResult()

    for line in lines:
        result.line_count += 1
        result.byte_count += len(line.encode("utf-8", errors="replace"))

        ts = parse_timestamp(line)
        if ts is None:
            result.parse_errors += 1
        else:
            if result.first_timestamp is None:
                result.first_timestamp = ts
            result.last_timestamp = ts

    return result
