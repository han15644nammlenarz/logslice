"""Pipeline that slices a log file and redacts sensitive data from output."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from logslice.pipeline import run_pipeline
from logslice.redactor import RedactConfig, RedactStats, redact_lines


@dataclass
class RedactPipelineResult:
    lines: List[str] = field(default_factory=list)
    redact_stats: RedactStats = field(default_factory=RedactStats)

    @property
    def line_count(self) -> int:
        return len(self.lines)

    def write_to_file(self, path: Path) -> None:
        """Write the redacted lines to *path*, one line per entry.

        Parameters
        ----------
        path:
            Destination file.  Parent directories must already exist.
        """
        with path.open("w", encoding="utf-8") as fh:
            fh.writelines(self.lines)


def run_redact_pipeline(
    path: Path,
    config: RedactConfig,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> RedactPipelineResult:
    """Slice *path* between *start* and *end*, then redact each output line.

    Parameters
    ----------
    path:
        Log file to read.
    config:
        Redaction rules to apply.
    start:
        Inclusive lower bound for log timestamps.
    end:
        Inclusive upper bound for log timestamps.

    Returns
    -------
    RedactPipelineResult
        Redacted lines plus statistics about what was replaced.
    """
    raw_lines = run_pipeline(path, start=start, end=end)

    result = RedactPipelineResult()

    if not config.is_active():
        result.lines = raw_lines
        result.redact_stats.lines_processed = len(raw_lines)
        return result

    line_iter, stats = redact_lines(iter(raw_lines), config)
    result.lines = list(line_iter)
    result.redact_stats = stats
    return result
