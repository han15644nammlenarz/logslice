"""Tests for logslice.timestamp_parser module."""

import pytest
from datetime import datetime
from logslice.timestamp_parser import parse_timestamp, parse_user_datetime


class TestParseTimestamp:
    def test_iso8601_format(self):
        line = "2024-01-15T13:45:00 INFO server started"
        result = parse_timestamp(line)
        assert result == datetime(2024, 1, 15, 13, 45, 0)

    def test_iso8601_with_milliseconds(self):
        line = "2024-03-22T08:01:55.123 DEBUG request received"
        result = parse_timestamp(line)
        assert result == datetime(2024, 3, 22, 8, 1, 55)

    def test_syslog_format(self):
        line = "Jan 15 13:45:00 hostname process[123]: message"
        result = parse_timestamp(line)
        assert result is not None
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 13

    def test_apache_format(self):
        line = '192.168.1.1 - - [15/Jan/2024:13:45:00 +0000] "GET / HTTP/1.1" 200'
        result = parse_timestamp(line)
        assert result == datetime(2024, 1, 15, 13, 45, 0)

    def test_simple_datetime_format(self):
        line = "2024-01-15 13:45:00 ERROR disk full"
        result = parse_timestamp(line)
        assert result == datetime(2024, 1, 15, 13, 45, 0)

    def test_no_timestamp_returns_none(self):
        line = "This line has no timestamp at all."
        result = parse_timestamp(line)
        assert result is None

    def test_empty_line_returns_none(self):
        assert parse_timestamp("") is None


class TestParseUserDatetime:
    def test_iso8601(self):
        result = parse_user_datetime("2024-01-15T13:45:00")
        assert result == datetime(2024, 1, 15, 13, 45, 0)

    def test_space_separated(self):
        result = parse_user_datetime("2024-01-15 13:45:00")
        assert result == datetime(2024, 1, 15, 13, 45, 0)

    def test_date_only(self):
        result = parse_user_datetime("2024-01-15")
        assert result == datetime(2024, 1, 15, 0, 0, 0)

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Unrecognized datetime format"):
            parse_user_datetime("15-01-2024")

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            parse_user_datetime("not-a-date")
