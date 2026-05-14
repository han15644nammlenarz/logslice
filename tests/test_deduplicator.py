"""Tests for logslice.deduplicator."""

from __future__ import annotations

import pytest

from logslice.deduplicator import (
    DedupeConfig,
    DedupeStats,
    deduplicate_lines,
)


# ---------------------------------------------------------------------------
# DedupeStats
# ---------------------------------------------------------------------------

class TestDedupeStats:
    def test_defaults(self):
        s = DedupeStats()
        assert s.total_lines == 0
        assert s.unique_lines == 0
        assert s.dropped_lines == 0

    def test_drop_rate_zero_when_no_lines(self):
        assert DedupeStats().drop_rate == 0.0

    def test_drop_rate_calculation(self):
        s = DedupeStats(total_lines=10, unique_lines=6, dropped_lines=4)
        assert s.drop_rate == pytest.approx(0.4)

    def test_drop_rate_all_unique(self):
        s = DedupeStats(total_lines=5, unique_lines=5, dropped_lines=0)
        assert s.drop_rate == 0.0


# ---------------------------------------------------------------------------
# deduplicate_lines — consecutive mode (default)
# ---------------------------------------------------------------------------

def _collect(lines, config=None):
    it, stats = deduplicate_lines(lines, config)
    return list(it), stats


def test_no_duplicates_returns_all_lines():
    lines = ["a\n", "b\n", "c\n"]
    result, stats = _collect(lines)
    assert result == lines
    assert stats.total_lines == 3
    assert stats.dropped_lines == 0


def test_consecutive_duplicates_removed():
    lines = ["a\n", "a\n", "b\n", "b\n", "b\n", "c\n"]
    result, stats = _collect(lines)
    assert result == ["a\n", "b\n", "c\n"]
    assert stats.dropped_lines == 3
    assert stats.unique_lines == 3


def test_non_consecutive_duplicates_kept_in_consecutive_mode():
    lines = ["a\n", "b\n", "a\n"]
    result, stats = _collect(lines)
    assert result == ["a\n", "b\n", "a\n"]
    assert stats.dropped_lines == 0


def test_empty_input():
    result, stats = _collect([])
    assert result == []
    assert stats.total_lines == 0


def test_strip_whitespace_normalises_before_compare():
    lines = ["hello\n", "hello  \n", "world\n"]
    result, stats = _collect(lines)
    assert len(result) == 2
    assert stats.dropped_lines == 1


def test_no_strip_whitespace_keeps_differing_trailing():
    cfg = DedupeConfig(strip_whitespace=False)
    lines = ["hello\n", "hello  \n"]
    result, stats = _collect(lines, cfg)
    assert result == lines
    assert stats.dropped_lines == 0


# ---------------------------------------------------------------------------
# deduplicate_lines — global (non-consecutive) mode
# ---------------------------------------------------------------------------

def test_global_dedup_removes_non_consecutive_duplicates():
    cfg = DedupeConfig(consecutive_only=False)
    lines = ["a\n", "b\n", "a\n", "c\n", "b\n"]
    result, stats = _collect(lines, cfg)
    assert result == ["a\n", "b\n", "c\n"]
    assert stats.dropped_lines == 2


def test_stats_updated_incrementally():
    """Stats should reflect consumed portion even if iterator is partial."""
    lines = ["x\n"] * 4
    it, stats = deduplicate_lines(lines)
    first = next(it)
    assert first == "x\n"
    assert stats.total_lines == 1
    assert stats.unique_lines == 1
