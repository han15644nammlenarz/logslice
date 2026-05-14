"""Pipeline integration: slice a log file and deduplicate the output."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

from logslice.deduplicator import DedupeConfig, DedupeStats, deduplicate_lines
from logslice.pipeline import run_pipeline
from logslice.filter import FilterConfig


@dataclass
class DedupPipelineResult:
    """Result returned by :func:`run_dedup_pipeline`."""

    lines: list[str]
    dedup_stats: DedupeStats


def run_dedup_pipeline(
    path: Path | str,
    start: datetime | None = None,
    end: datetime | None = None,
    filter_config: FilterConfig | None = None,
    dedup_config: DedupeConfig | None = None,
) -> DedupPipelineResult:
    """Run the standard log-slice pipeline and deduplicate the result.

    Args:
        path: Path to the log file.
        start: Inclusive lower-bound timestamp.
        end: Inclusive upper-bound timestamp.
        filter_config: Optional include/exclude pattern filter.
        dedup_config: Deduplication settings.  Defaults to consecutive-only.

    Returns:
        A :class:`DedupPipelineResult` with the deduplicated lines and stats.
    """
    path = Path(path)

    raw_lines: list[str] = run_pipeline(
        path,
        start=start,
        end=end,
        filter_config=filter_config,
    )

    dedup_iter, stats = deduplicate_lines(iter(raw_lines), dedup_config)
    return DedupPipelineResult(lines=list(dedup_iter), dedup_stats=stats)
