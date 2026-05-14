"""Tests for logslice.binary_search offset-finding utilities."""

import io
import os
import tempfile
from datetime import datetime, timezone

import pytest

from logslice.binary_search import (
    find_end_offset,
    find_line_start,
    find_start_offset,
    read_line_at,
)


LOG_LINES = [
    "2024-01-01T00:00:00Z INFO  startup complete",
    "2024-01-01T01:00:00Z DEBUG connection accepted",
    "2024-01-01T02:00:00Z INFO  processing request",
    "2024-01-01T03:00:00Z WARN  high memory usage",
    "2024-01-01T04:00:00Z ERROR disk full",
]


def make_log_file(lines):
    """Write lines to a temp file and return (path, file_size)."""
    content = '\n'.join(lines) + '\n'
    f = tempfile.NamedTemporaryFile(delete=False, suffix='.log')
    f.write(content.encode('utf-8'))
    f.close()
    return f.name, os.path.getsize(f.name)


@pytest.fixture
def log_file():
    path, size = make_log_file(LOG_LINES)
    yield path, size
    os.unlink(path)


def dt(hour):
    return datetime(2024, 1, 1, hour, 0, 0, tzinfo=timezone.utc)


class TestFindLineStart:
    def test_start_of_file_returns_zero(self, log_file):
        path, _ = log_file
        with open(path, 'rb') as f:
            assert find_line_start(f, 0) == 0

    def test_mid_line_returns_line_start(self, log_file):
        path, _ = log_file
        with open(path, 'rb') as f:
            first_line_len = len(LOG_LINES[0].encode('utf-8')) + 1  # +1 for \n
            mid = first_line_len + 5  # somewhere inside second line
            start = find_line_start(f, mid)
            assert start == first_line_len


class TestReadLineAt:
    def test_reads_first_line(self, log_file):
        path, _ = log_file
        with open(path, 'rb') as f:
            line = read_line_at(f, 0)
        assert line == LOG_LINES[0]


class TestFindStartOffset:
    def test_before_all_entries_returns_zero(self, log_file):
        path, size = log_file
        with open(path, 'rb') as f:
            offset = find_start_offset(f, size, dt(0))
        assert offset == 0

    def test_after_all_entries_returns_file_size(self, log_file):
        path, size = log_file
        with open(path, 'rb') as f:
            offset = find_start_offset(f, size, dt(10))
        assert offset == size

    def test_mid_range(self, log_file):
        path, size = log_file
        with open(path, 'rb') as f:
            offset = find_start_offset(f, size, dt(2))
            f.seek(offset)
            line = f.readline().decode('utf-8').strip()
        assert '02:00:00' in line


class TestFindEndOffset:
    def test_after_all_entries_returns_file_size(self, log_file):
        path, size = log_file
        with open(path, 'rb') as f:
            offset = find_end_offset(f, size, dt(23))
        assert offset == size

    def test_mid_range_excludes_later_entries(self, log_file):
        path, size = log_file
        with open(path, 'rb') as f:
            offset = find_end_offset(f, size, dt(2))
            f.seek(offset)
            line = f.readline().decode('utf-8').strip()
        assert '03:00:00' in line
