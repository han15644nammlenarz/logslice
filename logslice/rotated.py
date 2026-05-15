"""Support for reading rotated log files (e.g. app.log, app.log.1, app.log.2.gz)."""
from __future__ import annotations

import gzip
import bz2
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, List


@dataclass
class RotatedFileSet:
    """An ordered collection of rotated log file paths, oldest-first."""

    base_path: Path
    members: List[Path] = field(default_factory=list)

    @property
    def total_size_bytes(self) -> int:
        return sum(p.stat().st_size for p in self.members if p.exists())


_ROTATION_SUFFIX = re.compile(
    r"^(?P<base>.+?)\.(?P<index>\d+)(\.gz|\.bz2)?$"
)


def _sort_key(path: Path) -> int:
    """Return numeric rotation index; 0 for the live file."""
    m = _ROTATION_SUFFIX.match(path.name)
    if m:
        return int(m.group("index"))
    return 0


def discover_rotated_files(base: str | Path) -> RotatedFileSet:
    """Discover all rotated variants of *base* in the same directory.

    Files are returned oldest-first so callers can iterate chronologically.
    """
    base = Path(base)
    directory = base.parent
    stem = base.name  # e.g. "app.log"

    candidates: List[Path] = []
    for entry in directory.iterdir():
        name = entry.name
        if name == stem or name.startswith(stem + "."):
            candidates.append(entry)

    candidates.sort(key=_sort_key, reverse=True)  # highest index = oldest
    return RotatedFileSet(base_path=base, members=candidates)


def _open_member(path: Path):
    """Open a (possibly compressed) log member for text reading."""
    suffix = path.suffix.lower()
    if suffix == ".gz":
        return gzip.open(path, "rt", errors="replace")
    if suffix == ".bz2":
        return bz2.open(path, "rt", errors="replace")
    return open(path, "r", errors="replace")


def iter_rotated_lines(file_set: RotatedFileSet) -> Iterator[str]:
    """Yield lines from all members in chronological order (oldest first)."""
    for member in file_set.members:
        with _open_member(member) as fh:
            yield from fh
