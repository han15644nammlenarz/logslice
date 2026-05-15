"""Pipeline that slices a log file and optionally truncates the output."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from logslice.pipeline import run_pipeline
from logslice.truncator import TruncateConfig, TruncateResult, truncate_lines


@dataclass
class TruncatePipelineResult:
    """Combined result from slicing + truncation."""
    lines: list[str] = field(default_factory=list)
    lines_read: int = 0
    bytes_read: int = 0
    truncated: bool = False


def run_truncate_pipeline(
    path: Path,
    *,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    max_lines: Optional[int] = None,
    max_bytes: Optional[int] = None,
) -> TruncatePipelineResult:
    """Slice *path* between *start* / *end* then apply truncation limits.

    Parameters
    ----------
    path:
        Path to the log file.
    start:
        Inclusive lower bound on timestamps.  ``None`` means no lower bound.
    end:
        Inclusive upper bound on timestamps.  ``None`` means no upper bound.
    max_lines:
        Stop after this many output lines.  ``None`` disables the limit.
    max_bytes:
        Stop once accumulated output bytes would exceed this value.
        ``None`` disables the limit.

    Returns
    -------
    TruncatePipelineResult
        The collected lines together with read statistics and a flag that
        indicates whether the output was cut short by a truncation limit.
    """
    pipeline_result = run_pipeline(path, start=start, end=end)
    config = TruncateConfig(max_lines=max_lines, max_bytes=max_bytes)
    trunc: TruncateResult = truncate_lines(pipeline_result.lines, config)

    return TruncatePipelineResult(
        lines=trunc.lines,
        lines_read=trunc.lines_read,
        bytes_read=trunc.bytes_read,
        truncated=trunc.truncated,
    )
