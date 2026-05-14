"""Integration tests for logslice.pipeline."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from pathlib import Path

import pytest

from logslice.filter import FilterConfig
from logslice.pipeline import run_pipeline


LOG_LINES = [
    b"2024-03-01T08:00:00Z INFO  server started\n",
    b"2024-03-01T08:01:00Z DEBUG request received id=1\n",
    b"2024-03-01T08:02:00Z ERROR disk full\n",
    b"2024-03-01T08:03:00Z INFO  request id=1 done\n",
    b"2024-03-01T08:04:00Z WARN  memory high\n",
]


@pytest.fixture()
def log_file(tmp_path: Path) -> Path:
    p = tmp_path / "app.log"
    p.write_bytes(b"".join(LOG_LINES))
    return p


def _dt(hour: int, minute: int) -> datetime:
    return datetime(2024, 3, 1, hour, minute, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------

def test_no_bounds_returns_all_lines(log_file: Path):
    out = io.BytesIO()
    stats = run_pipeline(log_file, out)
    result = out.getvalue()
    assert result == b"".join(LOG_LINES)
    assert stats.lines_written == len(LOG_LINES)


def test_start_bound_excludes_early_lines(log_file: Path):
    out = io.BytesIO()
    run_pipeline(log_file, out, start=_dt(8, 2))
    lines = out.getvalue().splitlines(keepends=True)
    assert all(b"08:0" + bytes([str(m).encode()[0]]) not in line
               or int(line[14:16]) >= 2
               for line in lines)


def test_end_bound_excludes_late_lines(log_file: Path):
    out = io.BytesIO()
    run_pipeline(log_file, out, end=_dt(8, 2))
    content = out.getvalue().decode()
    assert "08:03" not in content
    assert "08:04" not in content


def test_filter_include_only_error(log_file: Path):
    out = io.BytesIO()
    cfg = FilterConfig(include_pattern="ERROR")
    stats = run_pipeline(log_file, out, filter_config=cfg)
    content = out.getvalue().decode()
    assert "ERROR" in content
    assert "INFO" not in content
    assert "DEBUG" not in content
    assert stats.lines_written == 1


def test_filter_exclude_debug(log_file: Path):
    out = io.BytesIO()
    cfg = FilterConfig(exclude_pattern="DEBUG")
    stats = run_pipeline(log_file, out, filter_config=cfg)
    content = out.getvalue().decode()
    assert "DEBUG" not in content
    assert stats.lines_written == len(LOG_LINES) - 1


def test_stats_populated(log_file: Path):
    out = io.BytesIO()
    stats = run_pipeline(log_file, out)
    assert stats.start_offset == 0
    assert stats.end_offset == log_file.stat().st_size
    assert stats.elapsed_seconds is not None
    assert stats.elapsed_seconds >= 0


def test_empty_file_returns_zero_lines(tmp_path: Path):
    empty = tmp_path / "empty.log"
    empty.write_bytes(b"")
    out = io.BytesIO()
    stats = run_pipeline(empty, out)
    assert out.getvalue() == b""
    assert stats.lines_written == 0
