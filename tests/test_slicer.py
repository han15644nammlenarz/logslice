"""Tests for logslice.slicer — the core log-slicing interface."""

import os
import pytest
from datetime import datetime, timezone

from logslice.slicer import slice_log


LOG_LINES = [
    "2024-01-15T10:00:00Z INFO  starting service",
    "2024-01-15T10:01:00Z DEBUG received request",
    "2024-01-15T10:02:00Z INFO  processed request",
    "2024-01-15T10:03:00Z WARN  slow response detected",
    "2024-01-15T10:04:00Z ERROR connection timeout",
    "2024-01-15T10:05:00Z INFO  shutting down",
]


@pytest.fixture
def log_file(tmp_path):
    """Write sample log lines to a temporary file and return its path."""
    path = tmp_path / "test.log"
    path.write_text("\n".join(LOG_LINES) + "\n", encoding="utf-8")
    return str(path)


@pytest.fixture
def empty_log_file(tmp_path):
    path = tmp_path / "empty.log"
    path.write_text("", encoding="utf-8")
    return str(path)


def test_slice_all_lines_no_bounds(log_file):
    result = list(slice_log(log_file))
    assert len(result) == len(LOG_LINES)
    assert result[0].startswith("2024-01-15T10:00:00Z")


def test_slice_with_start_only(log_file):
    result = list(slice_log(log_file, start="2024-01-15T10:03:00Z"))
    assert all("10:03" in r or "10:04" in r or "10:05" in r for r in result)
    assert not any("10:00" in r or "10:01" in r or "10:02" in r for r in result)


def test_slice_with_end_only(log_file):
    result = list(slice_log(log_file, end="2024-01-15T10:01:00Z"))
    assert all("10:00" in r or "10:01" in r for r in result)
    assert not any("10:02" in r for r in result)


def test_slice_with_start_and_end(log_file):
    result = list(slice_log(log_file, start="2024-01-15T10:01:00Z", end="2024-01-15T10:03:00Z"))
    assert len(result) == 3
    assert "10:01" in result[0]
    assert "10:03" in result[-1]


def test_slice_range_outside_log_returns_empty(log_file):
    result = list(slice_log(log_file, start="2025-01-01T00:00:00Z", end="2025-01-01T01:00:00Z"))
    assert result == []


def test_slice_empty_file_returns_empty(empty_log_file):
    result = list(slice_log(empty_log_file))
    assert result == []


def test_slice_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        list(slice_log("/nonexistent/path/to/file.log"))


def test_slice_invalid_start_raises(log_file):
    with pytest.raises(ValueError):
        list(slice_log(log_file, start="not-a-date"))


def test_slice_yields_strings_not_bytes(log_file):
    for line in slice_log(log_file):
        assert isinstance(line, str)
