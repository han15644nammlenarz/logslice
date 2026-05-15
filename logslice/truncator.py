"""Truncate log output to a maximum number of lines or bytes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator


@dataclass
class TruncateConfig:
    """Configuration for truncation behaviour."""
    max_lines: int | None = None
    max_bytes: int | None = None

    def __post_init__(self) -> None:
        if self.max_lines is not None and self.max_lines < 0:
            raise ValueError("max_lines must be non-negative")
        if self.max_bytes is not None and self.max_bytes < 0:
            raise ValueError("max_bytes must be non-negative")

    @property
    def is_active(self) -> bool:
        """Return True when at least one limit is set."""
        return self.max_lines is not None or self.max_bytes is not None


@dataclass
class TruncateResult:
    """Outcome of a truncation pass."""
    lines: list[str] = field(default_factory=list)
    lines_read: int = 0
    bytes_read: int = 0
    truncated: bool = False


def truncate_lines(
    source: Iterable[str],
    config: TruncateConfig,
) -> TruncateResult:
    """Consume *source* and stop once any limit in *config* is reached.

    Parameters
    ----------
    source:
        An iterable of log lines (newline included or not).
    config:
        Limits to enforce.  If ``is_active`` is False every line is kept.

    Returns
    -------
    TruncateResult
        Collected lines together with read statistics.
    """
    result = TruncateResult()

    for line in source:
        line_bytes = len(line.encode())

        if config.max_lines is not None and result.lines_read >= config.max_lines:
            result.truncated = True
            break

        if config.max_bytes is not None and result.bytes_read + line_bytes > config.max_bytes:
            result.truncated = True
            break

        result.lines.append(line)
        result.lines_read += 1
        result.bytes_read += line_bytes

    return result


def iter_truncated(
    source: Iterable[str],
    config: TruncateConfig,
) -> Iterator[str]:
    """Yield lines from *source* up to the limits defined in *config*."""
    lines_read = 0
    bytes_read = 0

    for line in source:
        if config.max_lines is not None and lines_read >= config.max_lines:
            break
        line_bytes = len(line.encode())
        if config.max_bytes is not None and bytes_read + line_bytes > config.max_bytes:
            break
        yield line
        lines_read += 1
        bytes_read += line_bytes
