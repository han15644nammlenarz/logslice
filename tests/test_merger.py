"""Tests for logslice.merger."""

from __future__ import annotations

from io import StringIO
from typing import List

import pytest

from logslice.merger import MergeStats, merge_log_sources


def _lines(text: str) -> StringIO:
    return StringIO(text)


SRC_A = (
    "2024-01-01T10:00:00 alpha first\n"
    "2024-01-01T10:00:02 alpha third\n"
    "2024-01-01T10:00:04 alpha fifth\n"
)

SRC_B = (
    "2024-01-01T10:00:01 beta second\n"
    "2024-01-01T10:00:03 beta fourth\n"
    "2024-01-01T10:00:05 beta sixth\n"
)


def test_merge_two_sources_produces_sorted_output() -> None:
    result = list(merge_log_sources([_lines(SRC_A), _lines(SRC_B)]))
    timestamps = [line.split()[0] for line in result]
    assert timestamps == sorted(timestamps)


def test_merge_two_sources_contains_all_lines() -> None:
    result = list(merge_log_sources([_lines(SRC_A), _lines(SRC_B)]))
    assert len(result) == 6


def test_merge_single_source_returns_same_lines() -> None:
    result = list(merge_log_sources([_lines(SRC_A)]))
    assert result == [line + "\n" if not line.endswith("\n") else line
                      for line in SRC_A.splitlines(keepends=True)]


def test_merge_empty_sources_returns_nothing() -> None:
    result = list(merge_log_sources([_lines(""), _lines("")]))
    assert result == []


def test_stats_sources_count() -> None:
    stats = MergeStats()
    list(merge_log_sources([_lines(SRC_A), _lines(SRC_B)], stats=stats))
    assert stats.sources == 2


def test_stats_lines_written() -> None:
    stats = MergeStats()
    list(merge_log_sources([_lines(SRC_A), _lines(SRC_B)], stats=stats))
    assert stats.lines_written == 6


def test_stats_lines_read_equals_written_when_no_errors() -> None:
    stats = MergeStats()
    list(merge_log_sources([_lines(SRC_A), _lines(SRC_B)], stats=stats))
    assert stats.lines_read == stats.lines_written


def test_unparseable_lines_are_skipped_and_counted() -> None:
    bad_src = "not a timestamp at all\n" + SRC_A
    stats = MergeStats()
    result = list(merge_log_sources([_lines(bad_src)], stats=stats))
    assert stats.parse_errors == 1
    assert len(result) == 3  # only the valid lines from SRC_A


def test_merge_stats_defaults() -> None:
    s = MergeStats()
    assert s.sources == 0
    assert s.lines_read == 0
    assert s.lines_written == 0
    assert s.parse_errors == 0
