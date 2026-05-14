"""Binary search utilities for locating timestamp boundaries in log files."""

import os
from datetime import datetime
from typing import Optional

from logslice.timestamp_parser import parse_timestamp


def find_line_start(f, pos: int) -> int:
    """Given a file position, seek backward to the start of the current line."""
    if pos == 0:
        return 0
    f.seek(pos - 1)
    while f.tell() > 0:
        char = f.read(1)
        if char == b'\n':
            return f.tell()
        f.seek(f.tell() - 2)
    f.seek(0)
    return 0


def read_line_at(f, pos: int) -> Optional[str]:
    """Seek to pos (start of a line) and return the decoded line, or None."""
    f.seek(pos)
    raw = f.readline()
    if not raw:
        return None
    try:
        return raw.decode('utf-8', errors='replace').rstrip('\n')
    except Exception:
        return None


def get_timestamp_at(f, pos: int) -> Optional[datetime]:
    """Return the parsed timestamp of the line at pos, or None if unparseable."""
    line = read_line_at(f, pos)
    if line is None:
        return None
    return parse_timestamp(line)


def find_start_offset(f, file_size: int, start_dt: datetime) -> int:
    """Binary search for the first byte offset whose line timestamp >= start_dt.

    Returns 0 if all lines are >= start_dt, or file_size if none qualify.
    """
    lo, hi = 0, file_size
    result = file_size

    while lo < hi:
        mid = (lo + hi) // 2
        line_start = find_line_start(f, mid)
        ts = get_timestamp_at(f, line_start)

        if ts is None:
            # Skip unparseable lines by nudging hi down
            hi = mid if mid > lo else lo + 1
            continue

        if ts < start_dt:
            lo = line_start + 1
        else:
            result = line_start
            hi = mid

    return result


def find_end_offset(f, file_size: int, end_dt: datetime) -> int:
    """Binary search for the first byte offset whose line timestamp > end_dt.

    Returns file_size if all lines are <= end_dt.
    """
    lo, hi = 0, file_size
    result = file_size

    while lo < hi:
        mid = (lo + hi) // 2
        line_start = find_line_start(f, mid)
        ts = get_timestamp_at(f, line_start)

        if ts is None:
            hi = mid if mid > lo else lo + 1
            continue

        if ts <= end_dt:
            lo = line_start + 1
        else:
            result = line_start
            hi = mid

    return result
