"""Automatic log format detection for logslice."""

import re
from dataclasses import dataclass
from typing import Optional


# Ordered list of (format_name, regex_pattern) pairs used for detection
FORMAT_PATTERNS = [
    ("iso8601", re.compile(
        r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?"
    )),
    ("syslog", re.compile(
        r"^[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}"
    )),
    ("apache", re.compile(
        r"^\[\d{2}/[A-Z][a-z]{2}/\d{4}:\d{2}:\d{2}:\d{2}\s[+-]\d{4}\]"
    )),
    ("nginx", re.compile(
        r"^\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}"
    )),
    ("epoch", re.compile(
        r"^\d{10}(?:\.\d+)?\s"
    )),
]


@dataclass
class DetectionResult:
    format_name: str
    confidence: float  # 0.0 – 1.0
    sample_count: int


def detect_format_from_line(line: str) -> Optional[str]:
    """Return the format name that matches *line*, or None."""
    for name, pattern in FORMAT_PATTERNS:
        if pattern.search(line):
            return name
    return None


def detect_format(file_obj, sample_lines: int = 20) -> DetectionResult:
    """Detect the timestamp format used in *file_obj* by sampling lines.

    The file position is restored after sampling.
    """
    original_pos = file_obj.tell()
    votes: dict[str, int] = {}
    lines_read = 0

    try:
        for raw in file_obj:
            line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            fmt = detect_format_from_line(line.rstrip("\n"))
            if fmt:
                votes[fmt] = votes.get(fmt, 0) + 1
            lines_read += 1
            if lines_read >= sample_lines:
                break
    finally:
        file_obj.seek(original_pos)

    if not votes:
        return DetectionResult(format_name="unknown", confidence=0.0, sample_count=lines_read)

    best_fmt = max(votes, key=lambda k: votes[k])
    confidence = votes[best_fmt] / max(lines_read, 1)
    return DetectionResult(format_name=best_fmt, confidence=confidence, sample_count=lines_read)
