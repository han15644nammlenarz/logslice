"""Tests for logslice.filter."""

from __future__ import annotations

import pytest

from logslice.filter import FilterConfig, apply_filter


LINES = [
    "2024-01-01T00:00:00 INFO  service started\n",
    "2024-01-01T00:01:00 DEBUG received request id=42\n",
    "2024-01-01T00:02:00 ERROR connection refused\n",
    "2024-01-01T00:03:00 INFO  request id=42 completed\n",
    "2024-01-01T00:04:00 WARN  disk usage above 80%\n",
]


# ---------------------------------------------------------------------------
# FilterConfig unit tests
# ---------------------------------------------------------------------------

class TestFilterConfig:
    def test_no_patterns_is_not_active(self):
        cfg = FilterConfig()
        assert not cfg.is_active

    def test_include_pattern_makes_active(self):
        cfg = FilterConfig(include_pattern="ERROR")
        assert cfg.is_active

    def test_exclude_pattern_makes_active(self):
        cfg = FilterConfig(exclude_pattern="DEBUG")
        assert cfg.is_active

    def test_accepts_include_match(self):
        cfg = FilterConfig(include_pattern="ERROR")
        assert cfg.accepts("2024-01-01 ERROR something bad")

    def test_rejects_include_no_match(self):
        cfg = FilterConfig(include_pattern="ERROR")
        assert not cfg.accepts("2024-01-01 INFO all good")

    def test_rejects_exclude_match(self):
        cfg = FilterConfig(exclude_pattern="DEBUG")
        assert not cfg.accepts("2024-01-01 DEBUG noisy line")

    def test_accepts_exclude_no_match(self):
        cfg = FilterConfig(exclude_pattern="DEBUG")
        assert cfg.accepts("2024-01-01 INFO useful line")

    def test_case_insensitive_include(self):
        cfg = FilterConfig(include_pattern="error", case_sensitive=False)
        assert cfg.accepts("2024-01-01 ERROR boom")

    def test_case_sensitive_include_rejects(self):
        cfg = FilterConfig(include_pattern="error", case_sensitive=True)
        assert not cfg.accepts("2024-01-01 ERROR boom")

    def test_include_and_exclude_combined(self):
        cfg = FilterConfig(include_pattern=r"id=\d+", exclude_pattern="ERROR")
        assert cfg.accepts(LINES[1])      # DEBUG with id=42 — passes
        assert not cfg.accepts(LINES[2]) # ERROR, no id — fails include
        assert cfg.accepts(LINES[3])     # INFO with id=42 — passes


# ---------------------------------------------------------------------------
# apply_filter integration tests
# ---------------------------------------------------------------------------

def test_no_filter_yields_all_lines():
    cfg = FilterConfig()
    result = list(apply_filter(LINES, cfg))
    assert result == LINES


def test_include_only_error_lines():
    cfg = FilterConfig(include_pattern="ERROR")
    result = list(apply_filter(LINES, cfg))
    assert len(result) == 1
    assert "ERROR" in result[0]


def test_exclude_debug_lines():
    cfg = FilterConfig(exclude_pattern="DEBUG")
    result = list(apply_filter(LINES, cfg))
    assert all("DEBUG" not in line for line in result)
    assert len(result) == len(LINES) - 1


def test_empty_input_yields_nothing():
    cfg = FilterConfig(include_pattern="ERROR")
    result = list(apply_filter([], cfg))
    assert result == []
