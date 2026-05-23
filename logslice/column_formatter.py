"""column_formatter.py — Format log lines into aligned columnar output."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Iterator, List, Optional


# Built-in column presets
_PRESETS: dict[str, list[str]] = {
    "iso": [r"(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^\s]*)",
            r"(?P<level>DEBUG|INFO|WARNING|ERROR|CRITICAL)",
            r"(?P<message>.*)"],
    "syslog": [r"(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})",
               r"(?P<host>\S+)",
               r"(?P<process>\S+):",
               r"(?P<message>.*)"],
}


@dataclass
class ColumnConfig:
    columns: List[str] = field(default_factory=list)
    separator: str = "  "
    preset: Optional[str] = None
    pad_char: str = " "

    def __post_init__(self) -> None:
        if self.preset is not None and self.preset not in _PRESETS:
            raise ValueError(f"Unknown preset '{self.preset}'. Choose from: {list(_PRESETS)}")
        if self.preset and not self.columns:
            self.columns = _PRESETS[self.preset]

    def is_active(self) -> bool:
        return bool(self.columns)


@dataclass
class FormatResult:
    rows: List[List[str]] = field(default_factory=list)
    unmatched: int = 0
    total: int = 0

    @property
    def matched(self) -> int:
        return self.total - self.unmatched

    def render(self, separator: str = "  ", pad_char: str = " ") -> Iterator[str]:
        if not self.rows:
            return
        widths = [max(len(row[i]) for row in self.rows if i < len(row))
                  for i in range(max(len(r) for r in self.rows))]
        for row in self.rows:
            padded = [cell.ljust(widths[i], pad_char) for i, cell in enumerate(row)]
            yield separator.join(padded).rstrip()


def _extract_columns(line: str, patterns: list[str]) -> Optional[list[str]]:
    """Try to extract named groups from *line* using each pattern in order."""
    remaining = line
    cells: list[str] = []
    for pat in patterns:
        m = re.search(pat, remaining)
        if not m:
            return None
        named = list(m.groupdict().values()) if m.groupdict() else [m.group(0)]
        cells.extend(v for v in named if v is not None)
        remaining = remaining[m.end():].lstrip()
    return cells


def format_columns(lines: Iterable[str], config: ColumnConfig) -> FormatResult:
    """Parse *lines* into columnar rows according to *config*."""
    result = FormatResult()
    if not config.is_active():
        result.rows = [[line.rstrip()] for line in lines]
        result.total = len(result.rows)
        return result

    for raw in lines:
        line = raw.rstrip()
        result.total += 1
        cells = _extract_columns(line, config.columns)
        if cells is None:
            result.rows.append([line])
            result.unmatched += 1
        else:
            result.rows.append(cells)
    return result
