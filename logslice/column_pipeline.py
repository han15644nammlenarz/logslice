"""column_pipeline.py — Pipeline that slices a log and renders columnar output."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator, List, Optional

from logslice.column_formatter import ColumnConfig, FormatResult, format_columns
from logslice.pipeline import run_pipeline


@dataclass
class ColumnPipelineResult:
    lines: List[str] = field(default_factory=list)
    format_result: Optional[FormatResult] = None
    line_count: int = 0
    unmatched: int = 0

    @property
    def matched(self) -> int:
        return self.line_count - self.unmatched


def _render(result: FormatResult, separator: str, pad_char: str) -> List[str]:
    return list(result.render(separator=separator, pad_char=pad_char))


def run_column_pipeline(
    path: Path,
    column_config: ColumnConfig,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> ColumnPipelineResult:
    """Slice *path* between *start* / *end* then format as aligned columns.

    Parameters
    ----------
    path:
        Log file to process.
    column_config:
        Column extraction and formatting settings.
    start:
        Inclusive lower bound for timestamps.  ``None`` means no lower bound.
    end:
        Inclusive upper bound for timestamps.  ``None`` means no upper bound.

    Returns
    -------
    ColumnPipelineResult
        Contains the rendered lines and formatting statistics.
    """
    raw_lines = run_pipeline(path, start=start, end=end)

    fmt_result = format_columns(raw_lines, column_config)

    rendered = _render(
        fmt_result,
        separator=column_config.separator,
        pad_char=column_config.pad_char,
    )

    return ColumnPipelineResult(
        lines=rendered,
        format_result=fmt_result,
        line_count=fmt_result.total,
        unmatched=fmt_result.unmatched,
    )
