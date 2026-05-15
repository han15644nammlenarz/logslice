"""Tests for logslice.truncator."""
from __future__ import annotations

import pytest

from logslice.truncator import (
    TruncateConfig,
    TruncateResult,
    truncate_lines,
    iter_truncated,
)


LINES = [
    "2024-01-01T00:00:01Z INFO  alpha\n",
    "2024-01-01T00:00:02Z INFO  bravo\n",
    "2024-01-01T00:00:03Z INFO  charlie\n",
    "2024-01-01T00:00:04Z INFO  delta\n",
    "2024-01-01T00:00:05Z INFO  echo\n",
]


# ---------------------------------------------------------------------------
# TruncateConfig
# ---------------------------------------------------------------------------

class TestTruncateConfig:
    def test_is_active_false_when_no_limits(self):
        assert TruncateConfig().is_active is False

    def test_is_active_true_with_max_lines(self):
        assert TruncateConfig(max_lines=10).is_active is True

    def test_is_active_true_with_max_bytes(self):
        assert TruncateConfig(max_bytes=1024).is_active is True

    def test_negative_max_lines_raises(self):
        with pytest.raises(ValueError, match="max_lines"):
            TruncateConfig(max_lines=-1)

    def test_negative_max_bytes_raises(self):
        with pytest.raises(ValueError, match="max_bytes"):
            TruncateConfig(max_bytes=-1)

    def test_zero_max_lines_is_valid(self):
        cfg = TruncateConfig(max_lines=0)
        assert cfg.max_lines == 0


# ---------------------------------------------------------------------------
# truncate_lines
# ---------------------------------------------------------------------------

def test_no_limits_returns_all_lines():
    result = truncate_lines(LINES, TruncateConfig())
    assert result.lines == LINES
    assert result.truncated is False


def test_max_lines_limits_output():
    result = truncate_lines(LINES, TruncateConfig(max_lines=3))
    assert result.lines == LINES[:3]
    assert result.lines_read == 3
    assert result.truncated is True


def test_max_lines_zero_returns_empty():
    result = truncate_lines(LINES, TruncateConfig(max_lines=0))
    assert result.lines == []
    assert result.truncated is True


def test_max_lines_larger_than_source_not_truncated():
    result = truncate_lines(LINES, TruncateConfig(max_lines=100))
    assert result.lines == LINES
    assert result.truncated is False


def test_max_bytes_limits_output():
    # Each line is ~34 bytes; limit to first two lines worth
    two_line_bytes = sum(len(l.encode()) for l in LINES[:2])
    result = truncate_lines(LINES, TruncateConfig(max_bytes=two_line_bytes))
    assert result.lines == LINES[:2]
    assert result.truncated is True


def test_bytes_read_accumulates_correctly():
    result = truncate_lines(LINES[:3], TruncateConfig())
    expected = sum(len(l.encode()) for l in LINES[:3])
    assert result.bytes_read == expected


def test_max_lines_and_max_bytes_both_respected():
    # max_lines kicks in first
    result = truncate_lines(LINES, TruncateConfig(max_lines=2, max_bytes=99999))
    assert len(result.lines) == 2


# ---------------------------------------------------------------------------
# iter_truncated
# ---------------------------------------------------------------------------

def test_iter_truncated_yields_correct_lines():
    result = list(iter_truncated(LINES, TruncateConfig(max_lines=2)))
    assert result == LINES[:2]


def test_iter_truncated_no_limits_yields_all():
    result = list(iter_truncated(LINES, TruncateConfig()))
    assert result == LINES
