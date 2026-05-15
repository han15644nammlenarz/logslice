"""Anomaly detection for log streams.

Detects lines that deviate significantly from the expected timestamp
progression — e.g. out-of-order entries, large time gaps, or lines
where no timestamp could be parsed.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta
from typing import Iterable, Iterator, List, Optional

from logslice.timestamp_parser import parse_timestamp


@dataclasses.dataclass
class AnomalyEvent:
    """A single detected anomaly in the log stream."""

    line_number: int
    line: str
    kind: str          # 'out_of_order' | 'large_gap' | 'unparseable'
    detail: str        # human-readable description
    gap_seconds: Optional[float] = None   # set for 'large_gap' events


@dataclasses.dataclass
class AnomalyReport:
    """Aggregated results from an anomaly-detection pass."""

    total_lines: int = 0
    unparseable: int = 0
    out_of_order: int = 0
    large_gaps: int = 0
    events: dataclasses.field(default_factory=list) = dataclasses.field(
        default_factory=list
    )

    @property
    def anomaly_count(self) -> int:
        """Total number of anomalies detected."""
        return self.unparseable + self.out_of_order + self.large_gaps

    @property
    def clean(self) -> bool:
        """True when no anomalies were found."""
        return self.anomaly_count == 0


def _record(
    report: AnomalyReport,
    event: AnomalyEvent,
) -> None:
    """Append an event and increment the appropriate counter."""
    report.events.append(event)
    if event.kind == "unparseable":
        report.unparseable += 1
    elif event.kind == "out_of_order":
        report.out_of_order += 1
    elif event.kind == "large_gap":
        report.large_gaps += 1


def detect_anomalies(
    lines: Iterable[str],
    *,
    gap_threshold: timedelta = timedelta(hours=1),
    max_events: int = 1000,
) -> AnomalyReport:
    """Scan *lines* and return an :class:`AnomalyReport`.

    Parameters
    ----------
    lines:
        Iterable of raw log lines (newlines are stripped automatically).
    gap_threshold:
        A forward jump larger than this value is flagged as a ``large_gap``.
        Defaults to one hour.
    max_events:
        Cap on the number of individual :class:`AnomalyEvent` objects stored
        in the report.  Counting continues even after the cap is reached so
        the summary statistics remain accurate.
    """
    report = AnomalyReport()
    prev_ts: Optional[datetime] = None

    for lineno, raw in enumerate(lines, start=1):
        report.total_lines += 1
        line = raw.rstrip("\n")

        ts = parse_timestamp(line)

        if ts is None:
            if len(report.events) < max_events:
                _record(
                    report,
                    AnomalyEvent(
                        line_number=lineno,
                        line=line,
                        kind="unparseable",
                        detail="No recognisable timestamp found in line.",
                    ),
                )
            else:
                report.unparseable += 1
            continue

        if prev_ts is not None:
            delta = (ts - prev_ts).total_seconds()

            if delta < 0:
                if len(report.events) < max_events:
                    _record(
                        report,
                        AnomalyEvent(
                            line_number=lineno,
                            line=line,
                            kind="out_of_order",
                            detail=(
                                f"Timestamp {ts.isoformat()} precedes "
                                f"previous timestamp {prev_ts.isoformat()} "
                                f"by {abs(delta):.1f}s."
                            ),
                        ),
                    )
                else:
                    report.out_of_order += 1

            elif delta > gap_threshold.total_seconds():
                if len(report.events) < max_events:
                    _record(
                        report,
                        AnomalyEvent(
                            line_number=lineno,
                            line=line,
                            kind="large_gap",
                            detail=(
                                f"Gap of {delta:.1f}s between "
                                f"{prev_ts.isoformat()} and "
                                f"{ts.isoformat()}."
                            ),
                            gap_seconds=delta,
                        ),
                    )
                else:
                    report.large_gaps += 1

        prev_ts = ts

    return report


def iter_anomalous_lines(
    lines: Iterable[str],
    *,
    gap_threshold: timedelta = timedelta(hours=1),
) -> Iterator[AnomalyEvent]:
    """Yield :class:`AnomalyEvent` objects as they are discovered.

    This is a streaming alternative to :func:`detect_anomalies` that avoids
    buffering all events in memory — useful when piping very large files.
    """
    prev_ts: Optional[datetime] = None

    for lineno, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n")
        ts = parse_timestamp(line)

        if ts is None:
            yield AnomalyEvent(
                line_number=lineno,
                line=line,
                kind="unparseable",
                detail="No recognisable timestamp found in line.",
            )
            continue

        if prev_ts is not None:
            delta = (ts - prev_ts).total_seconds()

            if delta < 0:
                yield AnomalyEvent(
                    line_number=lineno,
                    line=line,
                    kind="out_of_order",
                    detail=(
                        f"Timestamp {ts.isoformat()} precedes "
                        f"previous timestamp {prev_ts.isoformat()} "
                        f"by {abs(delta):.1f}s."
                    ),
                )
            elif delta > gap_threshold.total_seconds():
                yield AnomalyEvent(
                    line_number=lineno,
                    line=line,
                    kind="large_gap",
                    detail=(
                        f"Gap of {delta:.1f}s between "
                        f"{prev_ts.isoformat()} and "
                        f"{ts.isoformat()}."
                    ),
                    gap_seconds=delta,
                )

        prev_ts = ts
