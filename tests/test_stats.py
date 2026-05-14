"""Tests for logslice.stats."""

import time
import pytest
from logslice.stats import SliceStats, StatsCollector


class TestSliceStats:
    def test_defaults(self):
        s = SliceStats()
        assert s.lines_written == 0
        assert s.bytes_written == 0
        assert s.elapsed_seconds == 0.0
        assert s.detected_format is None

    def test_slice_size_bytes_both_offsets(self):
        s = SliceStats(start_offset=100, end_offset=500)
        assert s.slice_size_bytes == 400

    def test_slice_size_bytes_missing_offset(self):
        s = SliceStats(start_offset=100)
        assert s.slice_size_bytes == 0

    def test_slice_size_bytes_inverted(self):
        s = SliceStats(start_offset=500, end_offset=100)
        assert s.slice_size_bytes == 0

    def test_throughput_zero_elapsed(self):
        s = SliceStats(bytes_written=1_000_000, elapsed_seconds=0.0)
        assert s.throughput_mb_per_sec == 0.0

    def test_throughput_calculation(self):
        s = SliceStats(bytes_written=2_097_152, elapsed_seconds=2.0)
        assert s.throughput_mb_per_sec == pytest.approx(1.0)

    def test_summary_contains_lines_and_bytes(self):
        s = SliceStats(lines_written=42, bytes_written=1024, elapsed_seconds=0.5)
        summary = s.summary()
        assert "42" in summary
        assert "1,024" in summary

    def test_summary_includes_format_when_set(self):
        s = SliceStats(detected_format="iso8601")
        assert "iso8601" in s.summary()

    def test_timer_records_elapsed(self):
        s = SliceStats()
        s.start_timer()
        time.sleep(0.05)
        s.stop_timer()
        assert s.elapsed_seconds >= 0.04


class TestStatsCollector:
    def test_context_manager_sets_elapsed(self):
        s = SliceStats()
        with StatsCollector(s):
            time.sleep(0.05)
        assert s.elapsed_seconds >= 0.04

    def test_context_manager_returns_collector(self):
        s = SliceStats()
        with StatsCollector(s) as sc:
            assert sc.stats is s

    def test_exception_still_stops_timer(self):
        s = SliceStats()
        try:
            with StatsCollector(s):
                raise ValueError("oops")
        except ValueError:
            pass
        assert s.elapsed_seconds >= 0.0
