"""Pipeline that runs anomaly detection over a log slice.

Combines the binary-search-based slicer with the anomaly detector so callers
can get both the filtered lines *and* a populated AnomalyReport in a single
pass without buffering the whole file in memory.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, Optional

from .anomaly import AnomalyReport, AnomalyEvent
from .pipeline import _iter_lines
from .slicer import slice_log
from .timestamp_parser import parse_timestamp


@dataclass
class AnomalyPipelineResult:
    """Aggregated output from :func:`run_anomaly_pipeline`."""

    lines: list[str] = field(default_factory=list)
    report: AnomalyReport = field(default_factory=AnomalyReport)

    # ------------------------------------------------------------------ #
    # Convenience helpers
    # ------------------------------------------------------------------ #

    @property
    def anomaly_count(self) -> int:
        """Total number of anomalous events detected."""
        return self.report.anomaly_count()

    @property
    def has_anomalies(self) -> bool:
        """``True`` when at least one anomaly was found."""
        return self.anomaly_count > 0


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #

def _feed_lines(
    lines: Iterable[str],
    report: AnomalyReport,
    gap_threshold_seconds: float,
    burst_window_seconds: float,
    burst_max_lines: int,
) -> Iterator[str]:
    """Yield each line while feeding it into *report* for anomaly tracking."""
    prev_ts: Optional[datetime] = None
    window_lines: list[datetime] = []

    for line in lines:
        ts = parse_timestamp(line)

        if ts is not None:
            # --- gap detection -------------------------------------------
            if prev_ts is not None:
                delta = (ts - prev_ts).total_seconds()
                if delta > gap_threshold_seconds:
                    report._record(  # type: ignore[attr-defined]
                        AnomalyEvent(
                            kind="gap",
                            timestamp=ts,
                            detail=(
                                f"Gap of {delta:.1f}s detected "
                                f"(threshold {gap_threshold_seconds}s)"
                            ),
                            line=line.rstrip("\n"),
                        )
                    )
            prev_ts = ts

            # --- burst detection -----------------------------------------
            cutoff = ts.timestamp() - burst_window_seconds
            window_lines = [t for t in window_lines if t.timestamp() >= cutoff]
            window_lines.append(ts)
            if len(window_lines) > burst_max_lines:
                report._record(  # type: ignore[attr-defined]
                    AnomalyEvent(
                        kind="burst",
                        timestamp=ts,
                        detail=(
                            f"{len(window_lines)} lines in {burst_window_seconds}s "
                            f"(max {burst_max_lines})"
                        ),
                        line=line.rstrip("\n"),
                    )
                )

        yield line


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def run_anomaly_pipeline(
    path: Path,
    *,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    gap_threshold_seconds: float = 300.0,
    burst_window_seconds: float = 1.0,
    burst_max_lines: int = 100,
) -> AnomalyPipelineResult:
    """Slice *path* between *start* / *end* and detect anomalies in one pass.

    Parameters
    ----------
    path:
        Log file to process.
    start:
        Inclusive lower bound for timestamps (``None`` = no lower bound).
    end:
        Inclusive upper bound for timestamps (``None`` = no upper bound).
    gap_threshold_seconds:
        A silence gap longer than this many seconds is flagged as an anomaly.
    burst_window_seconds:
        Rolling window width used for burst detection.
    burst_max_lines:
        Maximum lines allowed inside *burst_window_seconds* before a burst
        event is recorded.

    Returns
    -------
    AnomalyPipelineResult
        Contains all matched lines and the populated :class:`AnomalyReport`.
    """
    report = AnomalyReport()
    result = AnomalyPipelineResult(report=report)

    raw_lines: Iterable[str] = slice_log(path, start=start, end=end)

    for line in _feed_lines(
        raw_lines,
        report,
        gap_threshold_seconds=gap_threshold_seconds,
        burst_window_seconds=burst_window_seconds,
        burst_max_lines=burst_max_lines,
    ):
        result.lines.append(line)

    return result
