"""Deduplication support for log slices — removes consecutive duplicate lines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator


@dataclass
class DedupeStats:
    """Tracks deduplication statistics."""

    total_lines: int = 0
    unique_lines: int = 0
    dropped_lines: int = 0

    @property
    def drop_rate(self) -> float:
        """Fraction of lines dropped (0.0 – 1.0)."""
        if self.total_lines == 0:
            return 0.0
        return self.dropped_lines / self.total_lines


@dataclass
class DedupeConfig:
    """Configuration for the deduplicator."""

    consecutive_only: bool = True
    """When True only adjacent duplicates are removed (memory-efficient).
    When False all seen lines are tracked (uses more memory)."""
    strip_whitespace: bool = True
    """Normalise lines before comparison."""


def deduplicate_lines(
    lines: Iterable[str],
    config: DedupeConfig | None = None,
) -> tuple[Iterator[str], DedupeStats]:
    """Return a lazy iterator of deduplicated lines and accumulated stats.

    Args:
        lines: Source iterable of log lines.
        config: Deduplication configuration.  Defaults to consecutive-only.

    Returns:
        A ``(iterator, stats)`` tuple.  *stats* is updated in-place as the
        iterator is consumed.
    """
    if config is None:
        config = DedupeConfig()

    stats = DedupeStats()

    def _iter() -> Iterator[str]:
        prev: str | None = None
        seen: set[str] = set()

        for raw_line in lines:
            stats.total_lines += 1
            key = raw_line.strip() if config.strip_whitespace else raw_line

            if config.consecutive_only:
                if key == prev:
                    stats.dropped_lines += 1
                    continue
                prev = key
            else:
                if key in seen:
                    stats.dropped_lines += 1
                    continue
                seen.add(key)

            stats.unique_lines += 1
            yield raw_line

    return _iter(), stats
