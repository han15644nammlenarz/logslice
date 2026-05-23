"""Counts lines in a log file or slice, optionally within time bounds."""

from __future__ import annotations

import dataclasses
import io
from pathlib import Path
from typing import Optional

from logslice.binary_search import find_start_offset, find_end_offset
from logslice.timestamp_parser import parse_user_datetime
from logslice.format_detector import detect_format


@dataclasses.dataclass
class CountResult:
    """Result of a line-count operation."""

    total_lines: int = 0
    file_size_bytes: int = 0
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None

    @property
    def slice_bytes(self) -> int:
        """Byte span of the counted region."""
        if self.start_offset is None or self.end_offset is None:
            return self.file_size_bytes
        return max(0, self.end_offset - self.start_offset)

    @property
    def avg_line_bytes(self) -> float:
        """Average bytes per line, or 0.0 if no lines."""
        if self.total_lines == 0:
            return 0.0
        return self.slice_bytes / self.total_lines


def count_lines(
    path: Path,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> CountResult:
    """Count lines in *path* between optional *start* and *end* timestamps.

    Parameters
    ----------
    path:
        Path to the log file.
    start:
        Human-readable start datetime string (inclusive).  ``None`` means
        beginning of file.
    end:
        Human-readable end datetime string (inclusive).  ``None`` means end
        of file.

    Returns
    -------
    CountResult
        Populated with line count and byte-range information.
    """
    file_size = path.stat().st_size
    result = CountResult(file_size_bytes=file_size)

    with path.open("rb") as fh:
        fmt = detect_format(fh)
        if fmt is None:
            return result

        dt_start = parse_user_datetime(start) if start else None
        dt_end = parse_user_datetime(end) if end else None

        start_offset = find_start_offset(fh, dt_start, fmt) if dt_start else 0
        end_offset = find_end_offset(fh, dt_end, fmt) if dt_end else file_size

        result.start_offset = start_offset
        result.end_offset = end_offset

        fh.seek(start_offset)
        count = 0
        while fh.tell() < end_offset:
            chunk = fh.read(min(65536, end_offset - fh.tell()))
            if not chunk:
                break
            count += chunk.count(b"\n")
        result.total_lines = count

    return result
