"""Tests for logslice.tail."""

from __future__ import annotations

import os
import pytest

from logslice.tail import TailResult, tail_log_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_log(tmp_path, lines):
    p = tmp_path / "sample.log"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


@pytest.fixture()
def log_file(tmp_path):
    lines = [f"2024-01-01T00:00:{i:02d}Z INFO line {i}" for i in range(20)]
    return _write_log(tmp_path, lines), lines


# ---------------------------------------------------------------------------
# TailResult unit tests
# ---------------------------------------------------------------------------

def test_tail_result_defaults():
    r = TailResult()
    assert r.lines == []
    assert r.bytes_read == 0
    assert r.total_size == 0
    assert r.lines_found == 0


def test_tail_result_lines_found():
    r = TailResult(lines=["a", "b", "c"])
    assert r.lines_found == 3


# ---------------------------------------------------------------------------
# tail_log_file tests
# ---------------------------------------------------------------------------

def test_tail_returns_last_n_lines(log_file):
    path, lines = log_file
    result = tail_log_file(path, n=5)
    assert result.lines == lines[-5:]


def test_tail_default_n_is_ten(log_file):
    path, lines = log_file
    result = tail_log_file(path)
    assert len(result.lines) == 10
    assert result.lines == lines[-10:]


def test_tail_n_larger_than_file(log_file):
    path, lines = log_file
    result = tail_log_file(path, n=100)
    assert result.lines == lines


def test_tail_empty_file(tmp_path):
    p = tmp_path / "empty.log"
    p.write_text("", encoding="utf-8")
    result = tail_log_file(str(p), n=5)
    assert result.lines == []
    assert result.bytes_read == 0
    assert result.total_size == 0


def test_tail_small_block_size(log_file):
    """Force multiple backward seeks to exercise the chunking loop."""
    path, lines = log_file
    result = tail_log_file(path, n=5, block_size=32)
    assert result.lines == lines[-5:]


def test_tail_records_total_size(log_file):
    path, _ = log_file
    result = tail_log_file(path, n=3)
    assert result.total_size == os.path.getsize(path)


def test_tail_invalid_n_raises(log_file):
    path, _ = log_file
    with pytest.raises(ValueError):
        tail_log_file(path, n=0)
