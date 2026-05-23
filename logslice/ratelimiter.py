"""Rate limiting for log output — caps lines or bytes emitted per second."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterable, Iterator


@dataclass
class RateLimitConfig:
    """Configuration for rate-limited output."""

    max_lines_per_sec: float | None = None
    max_bytes_per_sec: float | None = None

    def __post_init__(self) -> None:
        if self.max_lines_per_sec is not None and self.max_lines_per_sec <= 0:
            raise ValueError("max_lines_per_sec must be positive")
        if self.max_bytes_per_sec is not None and self.max_bytes_per_sec <= 0:
            raise ValueError("max_bytes_per_sec must be positive")

    @property
    def is_active(self) -> bool:
        return self.max_lines_per_sec is not None or self.max_bytes_per_sec is not None


@dataclass
class RateLimitStats:
    """Counters collected during a rate-limited pass."""

    lines_emitted: int = 0
    bytes_emitted: int = 0
    sleep_total_sec: float = 0.0
    sleeps: int = 0

    @property
    def avg_sleep_ms(self) -> float:
        if self.sleeps == 0:
            return 0.0
        return (self.sleep_total_sec / self.sleeps) * 1000


def _sleep(duration: float, stats: RateLimitStats) -> None:
    if duration > 0:
        time.sleep(duration)
        stats.sleep_total_sec += duration
        stats.sleeps += 1


def rate_limit_lines(
    lines: Iterable[str],
    config: RateLimitConfig,
) -> Iterator[tuple[str, RateLimitStats]]:
    """Yield (line, running_stats) pairs, sleeping as needed to honour limits."""
    stats = RateLimitStats()
    start = time.monotonic()

    for line in lines:
        stats.lines_emitted += 1
        stats.bytes_emitted += len(line.encode())

        elapsed = time.monotonic() - start

        if config.max_lines_per_sec is not None and elapsed > 0:
            expected = stats.lines_emitted / config.max_lines_per_sec
            _sleep(expected - elapsed, stats)

        if config.max_bytes_per_sec is not None:
            elapsed = time.monotonic() - start
            if elapsed > 0:
                expected = stats.bytes_emitted / config.max_bytes_per_sec
                _sleep(expected - elapsed, stats)

        yield line, stats
