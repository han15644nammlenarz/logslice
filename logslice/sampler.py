"""Line sampler for probing log files to estimate timestamp density."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from logslice.timestamp_parser import parse_timestamp
from logslice.format_detector import detect_format


@dataclass
class SampleResult:
    """Result of sampling a log file."""
    total_size: int = 0
    lines_sampled: int = 0
    lines_parsed: int = 0
    first_timestamp: Optional[object] = None
    last_timestamp: Optional[object] = None
    detected_format: Optional[str] = None
    offsets: list = field(default_factory=list)

    @property
    def parse_rate(self) -> float:
        """Fraction of sampled lines that yielded a timestamp."""
        if self.lines_sampled == 0:
            return 0.0
        return self.lines_parsed / self.lines_sampled


def sample_log_file(
    file_path: str,
    num_samples: int = 8,
) -> SampleResult:
    """Sample evenly-spaced offsets in *file_path* and parse timestamps.

    Parameters
    ----------
    file_path:
        Path to the log file.
    num_samples:
        How many positions to probe (including start and end).

    Returns
    -------
    SampleResult
        Aggregated information about the sampled lines.
    """
    result = SampleResult()
    result.total_size = os.path.getsize(file_path)

    if result.total_size == 0:
        return result

    # Detect format from the first readable line.
    with open(file_path, "rb") as fh:
        first_line = fh.readline().decode("utf-8", errors="replace").rstrip()
    fmt_result = detect_format(first_line)
    result.detected_format = fmt_result.format_name if fmt_result else None

    step = max(result.total_size // max(num_samples - 1, 1), 1)
    probe_offsets = sorted(
        set(min(i * step, result.total_size - 1) for i in range(num_samples))
    )

    with open(file_path, "rb") as fh:
        for offset in probe_offsets:
            fh.seek(offset)
            if offset != 0:
                fh.readline()  # skip partial line
            line_bytes = fh.readline()
            if not line_bytes:
                continue
            line = line_bytes.decode("utf-8", errors="replace").rstrip()
            result.lines_sampled += 1
            result.offsets.append(fh.tell())
            ts = parse_timestamp(line)
            if ts is not None:
                result.lines_parsed += 1
                if result.first_timestamp is None:
                    result.first_timestamp = ts
                result.last_timestamp = ts

    return result
