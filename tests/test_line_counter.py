"""Tests for logslice.line_counter."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from logslice.line_counter import CountResult, count_lines


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_log(tmp_path: Path, lines: list[str]) -> Path:
    p = tmp_path / "test.log"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


@pytest.fixture()
def iso_log(tmp_path: Path) -> Path:
    lines = [
        "2024-01-01T10:00:00 INFO  startup",
        "2024-01-01T10:01:00 INFO  ready",
        "2024-01-01T10:02:00 WARN  slow query",
        "2024-01-01T10:03:00 ERROR disk full",
        "2024-01-01T10:04:00 INFO  shutdown",
    ]
    return _write_log(tmp_path, lines)


# ---------------------------------------------------------------------------
# CountResult unit tests
# ---------------------------------------------------------------------------


class TestCountResult:
    def test_defaults(self):
        r = CountResult()
        assert r.total_lines == 0
        assert r.file_size_bytes == 0
        assert r.start_offset is None
        assert r.end_offset is None

    def test_slice_bytes_no_offsets_returns_file_size(self):
        r = CountResult(file_size_bytes=500)
        assert r.slice_bytes == 500

    def test_slice_bytes_with_offsets(self):
        r = CountResult(file_size_bytes=500, start_offset=100, end_offset=300)
        assert r.slice_bytes == 200

    def test_slice_bytes_inverted_offsets_returns_zero(self):
        r = CountResult(file_size_bytes=500, start_offset=300, end_offset=100)
        assert r.slice_bytes == 0

    def test_avg_line_bytes_zero_when_no_lines(self):
        r = CountResult(total_lines=0, file_size_bytes=200)
        assert r.avg_line_bytes == 0.0

    def test_avg_line_bytes_calculated(self):
        r = CountResult(
            total_lines=4,
            file_size_bytes=200,
            start_offset=0,
            end_offset=200,
        )
        assert r.avg_line_bytes == 50.0


# ---------------------------------------------------------------------------
# count_lines integration tests
# ---------------------------------------------------------------------------


def test_count_all_lines(iso_log: Path):
    result = count_lines(iso_log)
    assert result.total_lines == 5


def test_count_with_start_bound(iso_log: Path):
    result = count_lines(iso_log, start="2024-01-01T10:02:00")
    assert result.total_lines >= 1
    assert result.total_lines <= 5


def test_count_with_end_bound(iso_log: Path):
    result = count_lines(iso_log, end="2024-01-01T10:01:00")
    assert result.total_lines >= 1
    assert result.total_lines <= 5


def test_count_file_size_populated(iso_log: Path):
    result = count_lines(iso_log)
    assert result.file_size_bytes == iso_log.stat().st_size


def test_empty_file_returns_zero(tmp_path: Path):
    p = tmp_path / "empty.log"
    p.write_bytes(b"")
    result = count_lines(p)
    assert result.total_lines == 0
