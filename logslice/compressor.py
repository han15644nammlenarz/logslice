"""Optional gzip/bzip2 compression support for output streams."""

from __future__ import annotations

import gzip
import bz2
import io
from dataclasses import dataclass, field
from enum import Enum
from typing import IO, Iterator


class CompressionFormat(str, Enum):
    NONE = "none"
    GZIP = "gzip"
    BZIP2 = "bzip2"


_EXTENSION_MAP: dict[str, CompressionFormat] = {
    ".gz": CompressionFormat.GZIP,
    ".bz2": CompressionFormat.BZIP2,
}


@dataclass
class CompressedWriter:
    format: CompressionFormat = CompressionFormat.NONE
    bytes_written: int = field(default=0, init=False)

    def open(self, path: str) -> IO[bytes]:
        """Open *path* for writing with the appropriate compression."""
        if self.format == CompressionFormat.GZIP:
            return gzip.open(path, "wb")
        if self.format == CompressionFormat.BZIP2:
            return bz2.open(path, "wb")
        return open(path, "wb")

    def write_lines(self, dest: IO[bytes], lines: Iterator[str]) -> int:
        """Write *lines* to *dest*, returning total bytes written."""
        total = 0
        for line in lines:
            data = line.encode() if not line.endswith("\n") else line.encode()
            dest.write(data)
            total += len(data)
        self.bytes_written = total
        return total


def format_from_path(path: str) -> CompressionFormat:
    """Infer :class:`CompressionFormat` from a file extension."""
    for ext, fmt in _EXTENSION_MAP.items():
        if path.endswith(ext):
            return fmt
    return CompressionFormat.NONE


def open_for_reading(path: str) -> IO[bytes]:
    """Open *path* for reading, decompressing transparently if needed."""
    fmt = format_from_path(path)
    if fmt == CompressionFormat.GZIP:
        return gzip.open(path, "rb")
    if fmt == CompressionFormat.BZIP2:
        return bz2.open(path, "rb")
    return open(path, "rb")
