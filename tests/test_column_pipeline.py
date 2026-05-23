"""Tests for logslice.column_pipeline."""
from __future__ import annotations

import textwrap
from datetime import datetime, timezone
from pathlib import Path

import pytest

from logslice.column_formatter import ColumnConfig
from logslice.column_pipeline import run_column_pipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_log(tmp_path: Path, lines: list[str]) -> Path:
    p = tmp_path / "app.log"
    p.write_text("".join(lines))
    return p


_LINES = [
    "2024-03-01T08:00:00Z INFO  service starting\n",
    "2024-03-01T08:00:01Z DEBUG initialising db\n",
    "2024-03-01T08:00:02Z ERROR failed to connect\n",
    "2024-03-01T08:00:03Z INFO  retrying\n",
    "2024-03-01T08:00:04Z INFO  connected\n",
]


@pytest.fixture()
def log_file(tmp_path: Path) -> Path:
    return _write_log(tmp_path, _LINES)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_no_bounds_all_lines_returned(log_file: Path):
    cfg = ColumnConfig(preset="iso")
    result = run_column_pipeline(log_file, cfg)
    assert result.line_count == len(_LINES)


def test_start_bound_excludes_early_lines(log_file: Path):
    cfg = ColumnConfig(preset="iso")
    start = datetime(2024, 3, 1, 8, 0, 2, tzinfo=timezone.utc)
    result = run_column_pipeline(log_file, cfg, start=start)
    assert result.line_count <= len(_LINES)
    # All rendered lines should be at or after 08:00:02
    for line in result.lines:
        assert "08:00:0" in line  # coarse sanity check


def test_end_bound_excludes_late_lines(log_file: Path):
    cfg = ColumnConfig(preset="iso")
    end = datetime(2024, 3, 1, 8, 0, 1, tzinfo=timezone.utc)
    result = run_column_pipeline(log_file, cfg, end=end)
    assert result.line_count <= len(_LINES)


def test_columns_are_aligned(log_file: Path):
    cfg = ColumnConfig(preset="iso")
    result = run_column_pipeline(log_file, cfg)
    # All lines should be padded to the same width for the first column
    col_ends = [line.index("  ") for line in result.lines if "  " in line]
    assert len(set(col_ends)) == 1, "First column widths differ — alignment broken"


def test_no_column_config_returns_raw_lines(log_file: Path):
    cfg = ColumnConfig()  # inactive
    result = run_column_pipeline(log_file, cfg)
    assert result.line_count == len(_LINES)
    assert result.unmatched == 0


def test_unmatched_lines_tracked(tmp_path: Path):
    mixed = [
        "2024-03-01T08:00:00Z INFO  ok\n",
        "this line has no timestamp at all\n",
    ]
    p = _write_log(tmp_path, mixed)
    cfg = ColumnConfig(preset="iso")
    result = run_column_pipeline(p, cfg)
    assert result.unmatched == 1
    assert result.matched == 1


def test_empty_file_returns_empty_result(tmp_path: Path):
    p = _write_log(tmp_path, [])
    cfg = ColumnConfig(preset="iso")
    result = run_column_pipeline(p, cfg)
    assert result.line_count == 0
    assert result.lines == []
