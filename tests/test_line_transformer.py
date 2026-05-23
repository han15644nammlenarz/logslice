"""Tests for logslice.line_transformer."""
import pytest

from logslice.line_transformer import (
    TransformConfig,
    TransformStats,
    transform_lines,
)


# ---------------------------------------------------------------------------
# TransformConfig
# ---------------------------------------------------------------------------

class TestTransformConfig:
    def test_defaults_not_active(self):
        cfg = TransformConfig()
        assert cfg.is_active() is False

    def test_transform_makes_active(self):
        cfg = TransformConfig(transforms=["upper"])
        assert cfg.is_active() is True

    def test_prefix_makes_active(self):
        assert TransformConfig(prefix=">> ").is_active() is True

    def test_suffix_makes_active(self):
        assert TransformConfig(suffix=" <<").is_active() is True

    def test_replace_pattern_makes_active(self):
        assert TransformConfig(replace_pattern=r"\d+").is_active() is True

    def test_unknown_transform_raises(self):
        with pytest.raises(ValueError, match="Unknown transform"):
            TransformConfig(transforms=["rot13"])

    def test_invalid_regex_raises(self):
        with pytest.raises(re.error if False else Exception):
            TransformConfig(replace_pattern="[unclosed")


import re  # noqa: E402 — needed after class definition above


# ---------------------------------------------------------------------------
# TransformStats
# ---------------------------------------------------------------------------

def test_stats_defaults():
    s = TransformStats()
    assert s.lines_in == 0
    assert s.lines_out == 0
    assert s.replacements_made == 0


def test_replacement_rate_zero_when_no_lines():
    assert TransformStats().replacement_rate == 0.0


def test_replacement_rate_calculation():
    s = TransformStats(lines_in=10, replacements_made=4)
    assert s.replacement_rate == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# transform_lines
# ---------------------------------------------------------------------------

def test_upper_transform():
    cfg = TransformConfig(transforms=["upper"])
    result = list(transform_lines(["hello", "world"], cfg))
    assert result == ["HELLO", "WORLD"]


def test_strip_transform():
    cfg = TransformConfig(transforms=["strip"])
    result = list(transform_lines(["  hello  ", "\tworld\n"], cfg))
    assert result == ["hello", "world"]


def test_prefix_and_suffix():
    cfg = TransformConfig(prefix="[", suffix="]")
    result = list(transform_lines(["ok"], cfg))
    assert result == ["[ok]"]


def test_replace_pattern():
    cfg = TransformConfig(replace_pattern=r"\d+", replace_with="NUM")
    result = list(transform_lines(["error 404 on line 12"], cfg))
    assert result == ["error NUM on line NUM"]


def test_stats_are_updated():
    cfg = TransformConfig(replace_pattern=r"\d+", replace_with="X")
    stats = TransformStats()
    lines = ["a1b2", "no digits here", "3"]
    list(transform_lines(lines, cfg, stats=stats))
    assert stats.lines_in == 3
    assert stats.lines_out == 3
    assert stats.replacements_made == 3  # 2 in first line + 1 in third


def test_chained_transforms():
    cfg = TransformConfig(transforms=["strip", "upper"])
    result = list(transform_lines(["  hello  "], cfg))
    assert result == ["HELLO"]


def test_inactive_config_passes_lines_unchanged():
    cfg = TransformConfig()
    lines = ["line one", "line two"]
    assert list(transform_lines(lines, cfg)) == lines
