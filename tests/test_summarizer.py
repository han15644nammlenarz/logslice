"""Tests for logslice.summarizer."""

from datetime import datetime, timedelta, timezone

import pytest

from logslice.summarizer import SummaryResult, summarize_lines


UTC = timezone.utc


# ---------------------------------------------------------------------------
# SummaryResult unit tests
# ---------------------------------------------------------------------------

class TestSummaryResult:
    def test_defaults(self):
        r = SummaryResult()
        assert r.line_count == 0
        assert r.byte_count == 0
        assert r.first_timestamp is None
        assert r.last_timestamp is None
        assert r.parse_errors == 0

    def test_time_span_none_when_missing_timestamps(self):
        r = SummaryResult()
        assert r.time_span is None

    def test_time_span_calculated(self):
        r = SummaryResult(
            first_timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
            last_timestamp=datetime(2024, 1, 1, 0, 1, 0, tzinfo=UTC),
        )
        assert r.time_span == timedelta(seconds=60)

    def test_avg_line_bytes_zero_when_no_lines(self):
        r = SummaryResult()
        assert r.avg_line_bytes == 0.0

    def test_avg_line_bytes(self):
        r = SummaryResult(line_count=4, byte_count=100)
        assert r.avg_line_bytes == 25.0

    def test_lines_per_second_none_when_no_span(self):
        r = SummaryResult(line_count=10)
        assert r.lines_per_second is None

    def test_lines_per_second_calculated(self):
        r = SummaryResult(
            line_count=120,
            first_timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
            last_timestamp=datetime(2024, 1, 1, 0, 2, 0, tzinfo=UTC),
        )
        assert r.lines_per_second == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# summarize_lines integration tests
# ---------------------------------------------------------------------------

def test_empty_iterable_returns_zero_counts():
    result = summarize_lines([])
    assert result.line_count == 0
    assert result.byte_count == 0
    assert result.parse_errors == 0


def test_counts_lines_and_bytes():
    lines = [
        "2024-01-01T00:00:01Z INFO starting up\n",
        "2024-01-01T00:00:02Z INFO ready\n",
    ]
    result = summarize_lines(lines)
    assert result.line_count == 2
    assert result.byte_count == sum(len(l.encode()) for l in lines)


def test_timestamps_captured():
    lines = [
        "2024-01-01T00:00:01Z INFO first\n",
        "2024-01-01T00:00:05Z INFO last\n",
    ]
    result = summarize_lines(lines)
    assert result.first_timestamp is not None
    assert result.last_timestamp is not None
    assert result.last_timestamp > result.first_timestamp


def test_parse_errors_incremented_for_unparseable_lines():
    lines = ["no timestamp here\n", "also no timestamp\n"]
    result = summarize_lines(lines)
    assert result.parse_errors == 2
    assert result.first_timestamp is None


def test_mixed_lines_count_errors_only_for_bad():
    lines = [
        "2024-01-01T00:00:01Z INFO ok\n",
        "garbage line\n",
        "2024-01-01T00:00:03Z INFO also ok\n",
    ]
    result = summarize_lines(lines)
    assert result.line_count == 3
    assert result.parse_errors == 1
