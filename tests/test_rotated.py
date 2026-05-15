"""Tests for logslice.rotated — rotated log file discovery and reading."""
from __future__ import annotations

import gzip
from pathlib import Path

import pytest

from logslice.rotated import (
    RotatedFileSet,
    discover_rotated_files,
    iter_rotated_lines,
    _sort_key,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, lines: list[str]) -> Path:
    path.write_text("".join(f"{l}\n" for l in lines))
    return path


def _write_gz(path: Path, lines: list[str]) -> Path:
    with gzip.open(path, "wt") as fh:
        fh.write("".join(f"{l}\n" for l in lines))
    return path


# ---------------------------------------------------------------------------
# _sort_key
# ---------------------------------------------------------------------------

def test_sort_key_live_file_is_zero(tmp_path):
    assert _sort_key(tmp_path / "app.log") == 0


def test_sort_key_rotated_index(tmp_path):
    assert _sort_key(tmp_path / "app.log.3") == 3


def test_sort_key_compressed_rotated(tmp_path):
    assert _sort_key(tmp_path / "app.log.2.gz") == 2


# ---------------------------------------------------------------------------
# discover_rotated_files
# ---------------------------------------------------------------------------

def test_discover_finds_live_and_rotated(tmp_path):
    _write(tmp_path / "app.log", ["live"])
    _write(tmp_path / "app.log.1", ["rotated1"])
    _write(tmp_path / "app.log.2", ["rotated2"])

    result = discover_rotated_files(tmp_path / "app.log")

    assert isinstance(result, RotatedFileSet)
    assert len(result.members) == 3


def test_discover_orders_oldest_first(tmp_path):
    _write(tmp_path / "app.log", ["live"])
    _write(tmp_path / "app.log.1", ["r1"])
    _write(tmp_path / "app.log.2", ["r2"])

    result = discover_rotated_files(tmp_path / "app.log")
    names = [p.name for p in result.members]

    assert names.index("app.log.2") < names.index("app.log.1")
    assert names.index("app.log.1") < names.index("app.log")


def test_discover_ignores_unrelated_files(tmp_path):
    _write(tmp_path / "app.log", ["live"])
    _write(tmp_path / "other.log", ["other"])

    result = discover_rotated_files(tmp_path / "app.log")
    assert all("app.log" in p.name for p in result.members)


def test_total_size_bytes(tmp_path):
    _write(tmp_path / "app.log", ["hello"])
    result = discover_rotated_files(tmp_path / "app.log")
    assert result.total_size_bytes > 0


# ---------------------------------------------------------------------------
# iter_rotated_lines
# ---------------------------------------------------------------------------

def test_iter_rotated_lines_plain(tmp_path):
    _write(tmp_path / "app.log.1", ["old line"])
    _write(tmp_path / "app.log", ["new line"])

    fs = discover_rotated_files(tmp_path / "app.log")
    lines = [l.strip() for l in iter_rotated_lines(fs)]

    assert lines[0] == "old line"
    assert lines[-1] == "new line"


def test_iter_rotated_lines_with_gz(tmp_path):
    _write_gz(tmp_path / "app.log.1.gz", ["compressed old"])
    _write(tmp_path / "app.log", ["plain new"])

    fs = discover_rotated_files(tmp_path / "app.log")
    lines = [l.strip() for l in iter_rotated_lines(fs)]

    assert "compressed old" in lines
    assert "plain new" in lines
