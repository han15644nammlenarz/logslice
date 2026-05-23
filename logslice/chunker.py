"""Chunked reading support for streaming large log file slices."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Optional

DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1 MB


@dataclass
class ChunkResult:
    """Holds metadata about a single chunk read from a log file."""

    data: bytes
    chunk_index: int
    byte_offset: int
    lines_in_chunk: int = 0
    is_last: bool = False

    @property
    def size_bytes(self) -> int:
        return len(self.data)


def iter_chunks(
    path: str,
    start_offset: int = 0,
    end_offset: Optional[int] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> Iterator[ChunkResult]:
    """Yield successive byte chunks from *path* between *start_offset* and
    *end_offset* (exclusive).  Each chunk is aligned to a newline boundary so
    that callers never receive a partial line at a chunk boundary.

    Args:
        path: Path to the log file to read.
        start_offset: Byte offset at which to begin reading. Defaults to 0.
        end_offset: Byte offset at which to stop reading (exclusive). If
            ``None``, reads until end of file.
        chunk_size: Maximum number of bytes to read per chunk before aligning
            to a newline boundary. Defaults to ``DEFAULT_CHUNK_SIZE`` (1 MB).

    Raises:
        ValueError: If *chunk_size* is not a positive integer.
        FileNotFoundError: If *path* does not exist.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")

    with open(path, "rb") as fh:
        fh.seek(start_offset)
        position = start_offset
        index = 0

        while True:
            if end_offset is not None:
                remaining = end_offset - position
                if remaining <= 0:
                    break
                read_size = min(chunk_size, remaining)
            else:
                read_size = chunk_size

            raw = fh.read(read_size)
            if not raw:
                break

            # Align to the last newline so we never split a line across chunks.
            if end_offset is None or (position + len(raw)) < end_offset:
                last_nl = raw.rfind(b"\n")
                if last_nl != -1 and last_nl < len(raw) - 1:
                    # Rewind file pointer to just after the last newline.
                    rewind = len(raw) - last_nl - 1
                    fh.seek(-rewind, 1)
                    raw = raw[: last_nl + 1]

            lines = raw.count(b"\n")
            next_position = position + len(raw)
            is_last = end_offset is not None and next_position >= end_offset

            yield ChunkResult(
                data=raw,
                chunk_index=index,
                byte_offset=position,
                lines_in_chunk=lines,
                is_last=is_last,
            )

            position = next_position
            index += 1

            if is_last:
                break
