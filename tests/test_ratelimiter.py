"""Tests for logslice.ratelimiter."""

from __future__ import annotations

import pytest

from logslice.ratelimiter import (
    RateLimitConfig,
    RateLimitStats,
    rate_limit_lines,
)


# ---------------------------------------------------------------------------
# RateLimitConfig
# ---------------------------------------------------------------------------

class TestRateLimitConfig:
    def test_defaults_not_active(self):
        cfg = RateLimitConfig()
        assert not cfg.is_active

    def test_lines_per_sec_makes_active(self):
        cfg = RateLimitConfig(max_lines_per_sec=100)
        assert cfg.is_active

    def test_bytes_per_sec_makes_active(self):
        cfg = RateLimitConfig(max_bytes_per_sec=1024)
        assert cfg.is_active

    def test_negative_lines_raises(self):
        with pytest.raises(ValueError, match="max_lines_per_sec"):
            RateLimitConfig(max_lines_per_sec=-1)

    def test_zero_bytes_raises(self):
        with pytest.raises(ValueError, match="max_bytes_per_sec"):
            RateLimitConfig(max_bytes_per_sec=0)


# ---------------------------------------------------------------------------
# RateLimitStats
# ---------------------------------------------------------------------------

class TestRateLimitStats:
    def test_defaults(self):
        s = RateLimitStats()
        assert s.lines_emitted == 0
        assert s.bytes_emitted == 0
        assert s.sleep_total_sec == 0.0
        assert s.sleeps == 0

    def test_avg_sleep_ms_zero_when_no_sleeps(self):
        s = RateLimitStats()
        assert s.avg_sleep_ms == 0.0

    def test_avg_sleep_ms_calculated(self):
        s = RateLimitStats(sleep_total_sec=0.3, sleeps=3)
        assert abs(s.avg_sleep_ms - 100.0) < 1e-6


# ---------------------------------------------------------------------------
# rate_limit_lines (no-sleep path — very high limits)
# ---------------------------------------------------------------------------

def test_all_lines_emitted_no_limit():
    lines = ["line one\n", "line two\n", "line three\n"]
    cfg = RateLimitConfig()
    results = list(rate_limit_lines(lines, cfg))
    assert [r[0] for r in results] == lines


def test_stats_count_lines_correctly():
    lines = ["a\n", "b\n", "c\n"]
    cfg = RateLimitConfig(max_lines_per_sec=1_000_000)  # effectively unlimited
    *_, (_, stats) = rate_limit_lines(lines, cfg)
    assert stats.lines_emitted == 3


def test_stats_count_bytes_correctly():
    lines = ["hello\n"]  # 6 bytes UTF-8
    cfg = RateLimitConfig(max_bytes_per_sec=1_000_000)
    _, stats = next(iter(rate_limit_lines(lines, cfg)))
    assert stats.bytes_emitted == len("hello\n".encode())


def test_empty_input_yields_nothing():
    cfg = RateLimitConfig(max_lines_per_sec=10)
    assert list(rate_limit_lines([], cfg)) == []


def test_lines_order_preserved():
    lines = [f"line {i}\n" for i in range(20)]
    cfg = RateLimitConfig(max_lines_per_sec=1_000_000)
    out = [line for line, _ in rate_limit_lines(lines, cfg)]
    assert out == lines
