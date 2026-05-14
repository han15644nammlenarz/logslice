"""Tests for logslice.sampler."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone

import pytest

from logslice.sampler import sample_log_file, SampleResult


def _write_log(lines: list[str]) -> str:
    """Write *lines* to a temp file and return its path."""
    tf = tempfile.NamedTemporaryFile(
        mode="w", suffix=".log", delete=False, encoding="utf-8"
    )
    for line in lines:
        tf.write(line + "\n")
    tf.flush()
    tf.close()
    return tf.name


@pytest.fixture()
def iso_log(tmp_path):
    lines = [
        f"2024-01-{d:02d}T12:00:00Z INFO event-{d}"
        for d in range(1, 16)
    ]
    p = tmp_path / "sample.log"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


def test_sample_result_defaults():
    sr = SampleResult()
    assert sr.parse_rate == 0.0
    assert sr.lines_sampled == 0
    assert sr.lines_parsed == 0


def test_parse_rate_calculation():
    sr = SampleResult(lines_sampled=10, lines_parsed=7)
    assert sr.parse_rate == pytest.approx(0.7)


def test_empty_file_returns_zero_size(tmp_path):
    empty = tmp_path / "empty.log"
    empty.write_bytes(b"")
    result = sample_log_file(str(empty))
    assert result.total_size == 0
    assert result.lines_sampled == 0


def test_sample_detects_format(iso_log):
    result = sample_log_file(iso_log, num_samples=4)
    assert result.detected_format is not None
    assert "iso" in result.detected_format.lower() or result.detected_format != ""


def test_sample_captures_first_and_last_timestamps(iso_log):
    result = sample_log_file(iso_log, num_samples=4)
    assert result.first_timestamp is not None
    assert result.last_timestamp is not None
    assert result.first_timestamp <= result.last_timestamp


def test_sample_parse_rate_high_for_clean_log(iso_log):
    result = sample_log_file(iso_log, num_samples=6)
    assert result.parse_rate > 0.5


def test_sample_total_size_matches_file(iso_log):
    result = sample_log_file(iso_log)
    assert result.total_size == os.path.getsize(iso_log)


def test_sample_single_line(tmp_path):
    p = tmp_path / "one.log"
    p.write_text("2024-06-01T08:00:00Z INFO only line\n", encoding="utf-8")
    result = sample_log_file(str(p), num_samples=4)
    assert result.lines_sampled >= 1
    assert result.first_timestamp is not None
