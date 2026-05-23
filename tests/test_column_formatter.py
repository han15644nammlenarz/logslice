"""Tests for logslice.column_formatter."""
from __future__ import annotations

import pytest

from logslice.column_formatter import (
    ColumnConfig,
    FormatResult,
    format_columns,
)


# ---------------------------------------------------------------------------
# ColumnConfig
# ---------------------------------------------------------------------------

class TestColumnConfig:
    def test_defaults_not_active(self):
        cfg = ColumnConfig()
        assert not cfg.is_active()

    def test_columns_makes_active(self):
        cfg = ColumnConfig(columns=[r"(?P<ts>\S+)", r"(?P<msg>.+)"])
        assert cfg.is_active()

    def test_preset_iso_loads_columns(self):
        cfg = ColumnConfig(preset="iso")
        assert cfg.is_active()
        assert len(cfg.columns) == 3

    def test_preset_syslog_loads_columns(self):
        cfg = ColumnConfig(preset="syslog")
        assert cfg.is_active()

    def test_unknown_preset_raises(self):
        with pytest.raises(ValueError, match="Unknown preset"):
            ColumnConfig(preset="nonexistent")

    def test_explicit_columns_override_preset_ignored_when_both(self):
        # explicit columns take precedence; preset only fills when columns empty
        explicit = [r"(?P<x>\S+)"]
        cfg = ColumnConfig(columns=explicit, preset="iso")
        assert cfg.columns == explicit


# ---------------------------------------------------------------------------
# FormatResult
# ---------------------------------------------------------------------------

class TestFormatResult:
    def test_matched_property(self):
        r = FormatResult(rows=[["a", "b"], ["c"]], unmatched=1, total=2)
        assert r.matched == 1

    def test_render_pads_columns(self):
        r = FormatResult(rows=[["short", "x"], ["longervalue", "y"]], total=2)
        rendered = list(r.render())
        assert len(rendered) == 2
        # first row timestamp column should be padded to width of second row
        assert rendered[0].startswith("short      ")

    def test_render_empty_yields_nothing(self):
        r = FormatResult()
        assert list(r.render()) == []


# ---------------------------------------------------------------------------
# format_columns
# ---------------------------------------------------------------------------

def test_no_config_returns_lines_as_single_column():
    lines = ["hello world\n", "foo bar\n"]
    result = format_columns(lines, ColumnConfig())
    assert result.total == 2
    assert result.unmatched == 0
    assert result.rows[0] == ["hello world"]


def test_iso_preset_extracts_timestamp_and_level():
    lines = [
        "2024-01-15T10:00:00Z INFO  server started\n",
        "2024-01-15T10:00:01Z ERROR connection refused\n",
    ]
    cfg = ColumnConfig(preset="iso")
    result = format_columns(lines, cfg)
    assert result.total == 2
    assert result.unmatched == 0
    assert result.rows[0][0] == "2024-01-15T10:00:00Z"
    assert result.rows[0][1] == "INFO"


def test_unmatched_lines_counted():
    lines = ["no timestamp here\n", "2024-01-15T10:00:00Z INFO ok\n"]
    cfg = ColumnConfig(preset="iso")
    result = format_columns(lines, cfg)
    assert result.unmatched == 1
    assert result.matched == 1


def test_render_separator_used():
    lines = ["2024-01-15T10:00:00Z INFO msg\n"]
    cfg = ColumnConfig(preset="iso")
    result = format_columns(lines, cfg)
    rendered = list(result.render(separator=" | "))
    assert " | " in rendered[0]
