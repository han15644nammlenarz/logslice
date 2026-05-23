"""Line transformer: apply simple text transformations to log lines."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Iterator, List, Optional


_BUILTIN_TRANSFORMS = {
    "upper": str.upper,
    "lower": str.lower,
    "strip": str.strip,
    "lstrip": str.lstrip,
    "rstrip": str.rstrip,
}


@dataclass
class TransformConfig:
    """Configuration for line transformations."""

    transforms: List[str] = field(default_factory=list)
    prefix: str = ""
    suffix: str = ""
    replace_pattern: Optional[str] = None
    replace_with: str = ""

    def __post_init__(self) -> None:
        for t in self.transforms:
            if t not in _BUILTIN_TRANSFORMS:
                raise ValueError(
                    f"Unknown transform {t!r}. "
                    f"Valid options: {sorted(_BUILTIN_TRANSFORMS)}"
                )
        if self.replace_pattern is not None:
            re.compile(self.replace_pattern)  # validate early

    def is_active(self) -> bool:
        return bool(
            self.transforms
            or self.prefix
            or self.suffix
            or self.replace_pattern is not None
        )


@dataclass
class TransformStats:
    lines_in: int = 0
    lines_out: int = 0
    replacements_made: int = 0

    @property
    def replacement_rate(self) -> float:
        if self.lines_in == 0:
            return 0.0
        return self.replacements_made / self.lines_in


def transform_lines(
    lines: Iterable[str],
    config: TransformConfig,
    stats: Optional[TransformStats] = None,
) -> Iterator[str]:
    """Apply *config* transformations to each line, yielding results."""
    if stats is None:
        stats = TransformStats()

    _pattern = re.compile(config.replace_pattern) if config.replace_pattern else None

    for line in lines:
        stats.lines_in += 1
        result = line

        for t in config.transforms:
            result = _BUILTIN_TRANSFORMS[t](result)

        if _pattern is not None:
            new_result, n = _pattern.subn(config.replace_with, result)
            if n:
                stats.replacements_made += n
            result = new_result

        if config.prefix:
            result = config.prefix + result
        if config.suffix:
            result = result + config.suffix

        stats.lines_out += 1
        yield result
