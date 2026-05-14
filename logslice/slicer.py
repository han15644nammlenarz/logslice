"""Core log slicing functionality using binary search to extract time-bounded log segments."""

import os
from datetime import datetime
from typing import Iterator, Optional

from .binary_search import find_start_offset, find_end_offset
from .timestamp_parser import parse_timestamp, parse_user_datetime


DEFAULT_CHUNK_SIZE = 65536  # 64 KB


def slice_log(
    filepath: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> Iterator[str]:
    """Yield log lines from filepath within the given time range.

    Args:
        filepath: Path to the log file.
        start: Start datetime string (inclusive). If None, read from beginning.
        end: End datetime string (inclusive). If None, read until end of file.
        chunk_size: Number of bytes to read per chunk when streaming.

    Yields:
        Log lines (with newline stripped) within the specified time range.

    Raises:
        FileNotFoundError: If filepath does not exist.
        ValueError: If start or end cannot be parsed as a datetime.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Log file not found: {filepath}")

    start_dt: Optional[datetime] = parse_user_datetime(start) if start else None
    end_dt: Optional[datetime] = parse_user_datetime(end) if end else None

    file_size = os.path.getsize(filepath)
    if file_size == 0:
        return

    with open(filepath, "rb") as fh:
        start_offset = 0
        if start_dt is not None:
            start_offset = find_start_offset(fh, file_size, start_dt)

        end_offset = file_size
        if end_dt is not None:
            end_offset = find_end_offset(fh, file_size, end_dt)

        if start_offset >= end_offset:
            return

        fh.seek(start_offset)
        remaining = end_offset - start_offset

        while remaining > 0:
            to_read = min(chunk_size, remaining)
            chunk = fh.read(to_read)
            if not chunk:
                break
            remaining -= len(chunk)
            lines = chunk.split(b"\n")
            # If chunk doesn't end on a newline boundary, the last element is
            # a partial line — peek ahead and complete it.
            if remaining > 0 and not chunk.endswith(b"\n"):
                rest = fh.readline()
                remaining -= len(rest)
                lines[-1] += rest
            for line in lines:
                decoded = line.decode("utf-8", errors="replace").rstrip("\r\n")
                if decoded:
                    yield decoded
