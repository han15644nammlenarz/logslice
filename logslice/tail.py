"""Tail utility: read the last N lines from a large log file efficiently."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

_DEFAULT_BLOCK = 1 << 14  # 16 KB


@dataclass
class TailResult:
    lines: List[str] = field(default_factory=list)
    bytes_read: int = 0
    total_size: int = 0

    @property
    def lines_found(self) -> int:
        return len(self.lines)


def tail_log_file(
    path: str,
    n: int = 10,
    block_size: int = _DEFAULT_BLOCK,
) -> TailResult:
    """Return the last *n* lines of *path* without loading the whole file.

    The algorithm seeks backwards in chunks so memory usage stays bounded
    regardless of file size.
    """
    if n <= 0:
        raise ValueError(f"n must be a positive integer, got {n}")

    total_size = os.path.getsize(path)
    if total_size == 0:
        return TailResult(lines=[], bytes_read=0, total_size=0)

    collected: List[bytes] = []
    bytes_read = 0
    lines_needed = n + 1  # +1 because splitting always produces an extra empty token

    with open(path, "rb") as fh:
        offset = total_size

        while offset > 0 and len(collected) < lines_needed:
            read_size = min(block_size, offset)
            offset -= read_size
            fh.seek(offset)
            block = fh.read(read_size)
            bytes_read += len(block)
            collected.insert(0, block)

        raw = b"".join(collected)
        all_lines = raw.splitlines()

    # Drop the leading partial line only when we did NOT reach the file start
    if offset > 0 and all_lines:
        all_lines = all_lines[1:]

    result_lines = [
        ln.decode("utf-8", errors="replace") for ln in all_lines[-n:]
    ]
    return TailResult(
        lines=result_lines,
        bytes_read=bytes_read,
        total_size=total_size,
    )
