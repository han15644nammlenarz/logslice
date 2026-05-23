"""splitter.py — Split a log file into multiple output files by time window.

Each output file receives lines whose timestamps fall within a fixed-width
time bucket (e.g. one file per hour, one file per day).  Lines that cannot
be parsed are forwarded to the *current* bucket so they stay adjacent to
their context.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, Iterable, Iterator, Optional, Tuple

from logslice.timestamp_parser import parse_timestamp


# ---------------------------------------------------------------------------
# Public data structures
# ---------------------------------------------------------------------------

@dataclass
class SplitResult:
    """Summary returned by :func:`split_log_file`."""

    files_created: int = 0
    total_lines: int = 0
    unparsed_lines: int = 0
    output_paths: list = field(default_factory=list)

    @property
    def parsed_lines(self) -> int:
        """Number of lines whose timestamp was successfully parsed."""
        return self.total_lines - self.unparsed_lines


# ---------------------------------------------------------------------------
# Bucket helpers
# ---------------------------------------------------------------------------

def _bucket_for(ts: datetime, window: timedelta) -> datetime:
    """Return the UTC bucket start that *ts* belongs to.

    Buckets are aligned to the Unix epoch so that, for example, hourly
    buckets always start on the hour regardless of when the file begins.
    """
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    ts_utc = ts.astimezone(timezone.utc)
    seconds_since_epoch = (ts_utc - epoch).total_seconds()
    window_secs = window.total_seconds()
    bucket_start_secs = (seconds_since_epoch // window_secs) * window_secs
    return epoch + timedelta(seconds=bucket_start_secs)


def _default_namer(bucket: datetime, output_dir: Path, stem: str, suffix: str) -> Path:
    """Build an output path from the bucket timestamp."""
    tag = bucket.strftime("%Y%m%dT%H%M%SZ")
    return output_dir / f"{stem}_{tag}{suffix}"


# ---------------------------------------------------------------------------
# Core split logic
# ---------------------------------------------------------------------------

def split_log_file(
    source: Path,
    output_dir: Path,
    window: timedelta = timedelta(hours=1),
    namer: Optional[Callable[[datetime, Path, str, str], Path]] = None,
) -> SplitResult:
    """Split *source* into per-bucket files inside *output_dir*.

    Parameters
    ----------
    source:
        Path to the input log file.
    output_dir:
        Directory where output files are written.  Created if absent.
    window:
        Width of each time bucket.  Defaults to one hour.
    namer:
        Optional callable ``(bucket, output_dir, stem, suffix) -> Path``
        used to derive output file names.  Defaults to
        ``<stem>_<YYYYMMDDTHHMMSSz><suffix>``.

    Returns
    -------
    SplitResult
        Aggregated statistics about the split operation.
    """
    if window.total_seconds() <= 0:
        raise ValueError("window must be a positive timedelta")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(source).stem
    suffix = "".join(Path(source).suffixes[-1:])  # keep e.g. ".log"

    _namer = namer or _default_namer

    result = SplitResult()
    handles: Dict[datetime, object] = {}
    current_bucket: Optional[datetime] = None

    try:
        with open(source, "r", errors="replace") as fh:
            for raw in fh:
                result.total_lines += 1
                line = raw if raw.endswith("\n") else raw + "\n"

                ts = parse_timestamp(line)
                if ts is not None:
                    current_bucket = _bucket_for(ts, window)
                else:
                    result.unparsed_lines += 1
                    # Attach unparsed line to the last known bucket; if none
                    # yet, skip until we have at least one anchor.
                    if current_bucket is None:
                        continue

                if current_bucket not in handles:
                    out_path = _namer(current_bucket, output_dir, stem, suffix)
                    handles[current_bucket] = open(out_path, "w", errors="replace")  # noqa: SIM115
                    result.files_created += 1
                    result.output_paths.append(str(out_path))

                handles[current_bucket].write(line)  # type: ignore[union-attr]
    finally:
        for fh in handles.values():
            fh.close()  # type: ignore[union-attr]

    result.output_paths.sort()
    return result
