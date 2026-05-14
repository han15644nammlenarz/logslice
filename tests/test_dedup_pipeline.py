"""Integration tests for logslice.dedup_pipeline."""

from __future__ import annotations

import textwrap
from datetime import datetime, timezone
from pathlib import Path

import pytest

from logslice.dedup_pipeline import run_dedup_pipeline
from logslice.deduplicator import DedupeConfig


UTC = timezone.utc


@pytest.fixture()
def log_file(tmp_path: Path) -> Path:
    content = textwrap.dedent("""\
        2024-01-01T10:00:00Z INFO  starting up
        2024-01-01T10:00:01Z DEBUG heartbeat
        2024-01-01T10:00:01Z DEBUG heartbeat
        2024-01-01T10:00:02Z INFO  request received
        2024-01-01T10:00:02Z INFO  request received
        2024-01-01T10:00:03Z INFO  shutting down
    """)
    p = tmp_path / "app.log"
    p.write_text(content)
    return p


def test_dedup_removes_consecutive_duplicates(log_file: Path):
    result = run_dedup_pipeline(log_file)
    assert result.dedup_stats.dropped_lines == 2
    assert result.dedup_stats.unique_lines == 4


def test_dedup_result_lines_have_no_consecutive_duplicates(log_file: Path):
    result = run_dedup_pipeline(log_file)
    for a, b in zip(result.lines, result.lines[1:]):
        assert a.strip() != b.strip(), "Consecutive duplicate found in output"


def test_dedup_with_start_bound(log_file: Path):
    start = datetime(2024, 1, 1, 10, 0, 2, tzinfo=UTC)
    result = run_dedup_pipeline(log_file, start=start)
    assert all("10:00:02" in ln or "10:00:03" in ln for ln in result.lines)


def test_dedup_with_end_bound(log_file: Path):
    end = datetime(2024, 1, 1, 10, 0, 1, tzinfo=UTC)
    result = run_dedup_pipeline(log_file, end=end)
    assert all("10:00:03" not in ln for ln in result.lines)


def test_global_dedup_removes_all_duplicates(log_file: Path):
    cfg = DedupeConfig(consecutive_only=False)
    result = run_dedup_pipeline(log_file, dedup_config=cfg)
    seen = set()
    for line in result.lines:
        key = line.strip()
        assert key not in seen, f"Duplicate found: {key!r}"
        seen.add(key)


def test_empty_log_file(tmp_path: Path):
    p = tmp_path / "empty.log"
    p.write_text("")
    result = run_dedup_pipeline(p)
    assert result.lines == []
    assert result.dedup_stats.total_lines == 0
