"""Tests for logslice.redactor and logslice.redact_pipeline."""
from __future__ import annotations

import textwrap
from datetime import datetime, timezone
from pathlib import Path

import pytest

from logslice.redactor import RedactConfig, RedactStats, redact_lines
from logslice.redact_pipeline import RedactPipelineResult, run_redact_pipeline


# ---------------------------------------------------------------------------
# RedactConfig
# ---------------------------------------------------------------------------

class TestRedactConfig:
    def test_defaults_not_active(self):
        cfg = RedactConfig()
        assert not cfg.is_active()

    def test_builtin_pattern_makes_active(self):
        cfg = RedactConfig(builtin=["ipv4"])
        assert cfg.is_active()

    def test_custom_pattern_makes_active(self):
        cfg = RedactConfig(patterns=[r"\d{4}"])
        assert cfg.is_active()

    def test_unknown_builtin_raises(self):
        with pytest.raises(ValueError, match="Unknown built-in"):
            RedactConfig(builtin=["ssn"])

    def test_compiled_returns_none_when_inactive(self):
        cfg = RedactConfig()
        assert cfg.compiled() is None

    def test_compiled_returns_pattern_when_active(self):
        import re
        cfg = RedactConfig(builtin=["email"])
        assert isinstance(cfg.compiled(), re.Pattern)


# ---------------------------------------------------------------------------
# redact_lines
# ---------------------------------------------------------------------------

def test_redact_ipv4():
    lines = ["Connection from 192.168.1.1 rejected", "No address here"]
    cfg = RedactConfig(builtin=["ipv4"])
    out, stats = redact_lines(iter(lines), cfg)
    result = list(out)
    assert "[REDACTED]" in result[0]
    assert "192.168.1.1" not in result[0]
    assert result[1] == "No address here"
    assert stats.lines_redacted == 1
    assert stats.total_replacements == 1


def test_redact_email():
    lines = ["User user@example.com logged in"]
    cfg = RedactConfig(builtin=["email"])
    out, stats = redact_lines(iter(lines), cfg)
    result = list(out)
    assert "user@example.com" not in result[0]
    assert stats.total_replacements == 1


def test_redact_custom_pattern():
    lines = ["Order ID: 1234", "No digits"]
    cfg = RedactConfig(patterns=[r"\b\d{4}\b"])
    out, stats = redact_lines(iter(lines), cfg)
    result = list(out)
    assert "1234" not in result[0]
    assert stats.lines_redacted == 1


def test_no_redaction_when_inactive():
    lines = ["plain log line"]
    cfg = RedactConfig()
    out, stats = redact_lines(iter(lines), cfg)
    assert list(out) == lines
    assert stats.lines_redacted == 0


def test_redact_rate_calculation():
    stats = RedactStats(lines_processed=10, lines_redacted=4)
    assert stats.redact_rate == pytest.approx(0.4)


def test_redact_rate_zero_when_no_lines():
    stats = RedactStats()
    assert stats.redact_rate == 0.0


# ---------------------------------------------------------------------------
# run_redact_pipeline
# ---------------------------------------------------------------------------

@pytest.fixture()
def log_file(tmp_path: Path) -> Path:
    p = tmp_path / "app.log"
    p.write_text(
        textwrap.dedent("""\
            2024-01-01T00:00:01Z INFO  login from 10.0.0.1 user@test.com
            2024-01-01T00:00:02Z INFO  request ok
            2024-01-01T00:00:03Z WARN  failed from 10.0.0.2
        """)
    )
    return p


def test_pipeline_redacts_ips(log_file: Path):
    cfg = RedactConfig(builtin=["ipv4", "email"])
    result = run_redact_pipeline(log_file, cfg)
    assert all("10.0." not in ln for ln in result.lines)
    assert all("@test.com" not in ln for ln in result.lines)
    assert result.redact_stats.lines_redacted >= 2


def test_pipeline_inactive_config_passes_through(log_file: Path):
    cfg = RedactConfig()
    result = run_redact_pipeline(log_file, cfg)
    assert result.line_count == 3
    assert result.redact_stats.lines_redacted == 0


def test_pipeline_with_time_bounds(log_file: Path):
    cfg = RedactConfig(builtin=["ipv4"])
    start = datetime(2024, 1, 1, 0, 0, 2, tzinfo=timezone.utc)
    result = run_redact_pipeline(log_file, cfg, start=start)
    assert result.line_count == 2
