"""Tests for logslice.format_detector."""

import io
import pytest
from logslice.format_detector import detect_format, detect_format_from_line, DetectionResult


# ---------------------------------------------------------------------------
# detect_format_from_line
# ---------------------------------------------------------------------------

class TestDetectFormatFromLine:
    def test_iso8601_basic(self):
        assert detect_format_from_line("2024-01-15T12:34:56 INFO starting") == "iso8601"

    def test_iso8601_with_ms(self):
        assert detect_format_from_line("2024-01-15T12:34:56.789Z ERROR boom") == "iso8601"

    def test_syslog(self):
        assert detect_format_from_line("Jan  5 12:34:56 host sshd[123]: msg") == "syslog"

    def test_apache(self):
        line = "[15/Jan/2024:12:34:56 +0000] GET /index.html 200"
        assert detect_format_from_line(line) == "apache"

    def test_nginx(self):
        assert detect_format_from_line("2024/01/15 12:34:56 [error] 1#1: msg") == "nginx"

    def test_epoch(self):
        assert detect_format_from_line("1705318496 INFO event") == "epoch"

    def test_unknown_returns_none(self):
        assert detect_format_from_line("no timestamp here at all") is None


# ---------------------------------------------------------------------------
# detect_format
# ---------------------------------------------------------------------------

def _make_stream(lines):
    content = "\n".join(lines) + "\n"
    return io.BytesIO(content.encode())


class TestDetectFormat:
    def test_iso8601_file(self):
        lines = [f"2024-01-15T12:34:{i:02d} INFO msg" for i in range(15)]
        result = detect_format(_make_stream(lines))
        assert result.format_name == "iso8601"
        assert result.confidence > 0.9

    def test_syslog_file(self):
        lines = [f"Jan {i+1:2d} 08:00:00 host daemon: msg" for i in range(10)]
        result = detect_format(_make_stream(lines))
        assert result.format_name == "syslog"

    def test_mixed_returns_dominant(self):
        iso_lines = [f"2024-01-15T12:34:{i:02d} INFO msg" for i in range(14)]
        other_lines = ["no timestamp here"]
        result = detect_format(_make_stream(iso_lines + other_lines))
        assert result.format_name == "iso8601"

    def test_empty_file_returns_unknown(self):
        result = detect_format(io.BytesIO(b""))
        assert result.format_name == "unknown"
        assert result.confidence == 0.0

    def test_file_position_restored(self):
        stream = _make_stream(["2024-01-15T00:00:00 INFO line"] * 5)
        stream.seek(0)
        detect_format(stream)
        assert stream.tell() == 0

    def test_sample_lines_limit(self):
        lines = [f"2024-01-15T12:34:{i:02d} INFO msg" for i in range(50)]
        result = detect_format(_make_stream(lines), sample_lines=10)
        assert result.sample_count == 10
