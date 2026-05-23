"""Pipeline that combines log slicing with optional rate-limited output."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

from logslice.pipeline import _iter_lines
from logslice.ratelimiter import RateLimitConfig, RateLimitStats, rate_limit_lines
from logslice.binary_search import find_start_offset, find_end_offset
from logslice.timestamp_parser import parse_timestamp
from logslice.format_detector import detect_format


@dataclass
class RateLimitPipelineResult:
    lines: list[str]
    stats: RateLimitStats
    start_offset: int | None = None
    end_offset: int | None = None


def run_ratelimit_pipeline(
    path: Path,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    config: RateLimitConfig | None = None,
) -> RateLimitPipelineResult:
    """Slice *path* between *start* / *end* and stream output with rate limiting.

    Parameters
    ----------
    path:
        Log file to read.
    start:
        Inclusive lower bound on timestamps.  ``None`` means beginning of file.
    end:
        Inclusive upper bound on timestamps.  ``None`` means end of file.
    config:
        Rate-limit settings.  ``None`` or an inactive config disables throttling.
    """
    if config is None:
        config = RateLimitConfig()

    fmt = detect_format(path)
    parser = (lambda line: parse_timestamp(line, fmt=fmt.format)) if fmt else parse_timestamp

    start_offset: int | None = None
    end_offset: int | None = None

    with path.open("rb") as fh:
        file_size = path.stat().st_size

        if start is not None:
            start_offset = find_start_offset(fh, file_size, start, parser)
        if end is not None:
            end_offset = find_end_offset(fh, file_size, end, parser)

    raw: Iterator[str] = _iter_lines(path, start_offset, end_offset)

    collected: list[str] = []
    last_stats = RateLimitStats()

    if config.is_active:
        for line, last_stats in rate_limit_lines(raw, config):
            collected.append(line)
    else:
        for line in raw:
            collected.append(line)
            last_stats.lines_emitted += 1
            last_stats.bytes_emitted += len(line.encode())

    return RateLimitPipelineResult(
        lines=collected,
        stats=last_stats,
        start_offset=start_offset,
        end_offset=end_offset,
    )
