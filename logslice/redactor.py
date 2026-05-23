"""Redact sensitive patterns from log lines before output."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Iterator, List, Optional

_BUILTIN_PATTERNS: dict[str, str] = {
    "ipv4": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "email": r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    "token": r"(?i)(?:bearer|token|api[_-]?key)[=:\s]+[\w\-\.]{8,}",
    "credit_card": r"\b(?:\d[ \-]?){13,16}\b",
}


@dataclass
class RedactConfig:
    """Configuration for the redactor."""

    patterns: List[str] = field(default_factory=list)
    """Extra regex patterns to redact."""

    builtin: List[str] = field(default_factory=list)
    """Names of built-in patterns to enable (e.g. 'ipv4', 'email')."""

    replacement: str = "[REDACTED]"
    """String to substitute for each match."""

    def __post_init__(self) -> None:
        for name in self.builtin:
            if name not in _BUILTIN_PATTERNS:
                raise ValueError(
                    f"Unknown built-in redaction pattern: {name!r}. "
                    f"Available: {list(_BUILTIN_PATTERNS)}"
                )

    def is_active(self) -> bool:
        return bool(self.patterns or self.builtin)

    def compiled(self) -> Optional[re.Pattern[str]]:
        """Return a single compiled pattern combining all active rules."""
        parts: List[str] = []
        for name in self.builtin:
            parts.append(_BUILTIN_PATTERNS[name])
        parts.extend(self.patterns)
        if not parts:
            return None
        return re.compile("|".join(f"(?:{p})" for p in parts))


@dataclass
class RedactStats:
    lines_processed: int = 0
    lines_redacted: int = 0
    total_replacements: int = 0

    @property
    def redact_rate(self) -> float:
        if self.lines_processed == 0:
            return 0.0
        return self.lines_redacted / self.lines_processed


def redact_lines(
    lines: Iterable[str],
    config: RedactConfig,
) -> tuple[Iterator[str], RedactStats]:
    """Yield lines with sensitive data replaced; also return stats."""
    stats = RedactStats()
    pattern = config.compiled()

    def _iter() -> Iterator[str]:
        for line in lines:
            stats.lines_processed += 1
            if pattern is None:
                yield line
                continue
            new_line, n = pattern.subn(config.replacement, line)
            if n:
                stats.lines_redacted += 1
                stats.total_replacements += n
            yield new_line

    return _iter(), stats
