"""Line-level filtering utilities for logslice."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Iterator, Optional


@dataclass
class FilterConfig:
    """Configuration for line-level filtering."""

    include_pattern: Optional[str] = None
    exclude_pattern: Optional[str] = None
    case_sensitive: bool = True

    # Compiled patterns (populated lazily)
    _include_re: Optional[re.Pattern] = field(default=None, init=False, repr=False)
    _exclude_re: Optional[re.Pattern] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        flags = 0 if self.case_sensitive else re.IGNORECASE
        if self.include_pattern:
            self._include_re = re.compile(self.include_pattern, flags)
        if self.exclude_pattern:
            self._exclude_re = re.compile(self.exclude_pattern, flags)

    @property
    def is_active(self) -> bool:
        """Return True if at least one filter is configured."""
        return self._include_re is not None or self._exclude_re is not None

    def accepts(self, line: str) -> bool:
        """Return True if *line* passes all configured filters."""
        if self._include_re is not None and not self._include_re.search(line):
            return False
        if self._exclude_re is not None and self._exclude_re.search(line):
            return False
        return True


def apply_filter(
    lines: Iterable[str],
    config: FilterConfig,
) -> Iterator[str]:
    """Yield only lines that satisfy *config*.

    If the filter is not active every line is yielded unchanged.
    """
    if not config.is_active:
        yield from lines
        return

    for line in lines:
        if config.accepts(line):
            yield line
