"""Tests for logslice.bookmark."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from logslice.bookmark import (
    Bookmark,
    bookmark_path,
    delete_bookmark,
    load_bookmark,
    save_bookmark,
)


# ---------------------------------------------------------------------------
# Bookmark dataclass
# ---------------------------------------------------------------------------

class TestBookmark:
    def test_defaults_populate_saved_at(self):
        bm = Bookmark(path="/var/log/app.log", offset=1024)
        assert bm.saved_at  # non-empty ISO string

    def test_as_dict_round_trip(self):
        bm = Bookmark(path="/var/log/app.log", offset=512, timestamp="2024-01-01T00:00:00")
        restored = Bookmark.from_dict(bm.as_dict())
        assert restored.path == bm.path
        assert restored.offset == bm.offset
        assert restored.timestamp == bm.timestamp

    def test_from_dict_missing_timestamp_is_none(self):
        data = {"path": "/tmp/x.log", "offset": 0, "saved_at": "2024-01-01T00:00:00"}
        bm = Bookmark.from_dict(data)
        assert bm.timestamp is None

    def test_from_dict_missing_saved_at_defaults_empty(self):
        data = {"path": "/tmp/x.log", "offset": 0}
        bm = Bookmark.from_dict(data)
        assert bm.saved_at == ""


# ---------------------------------------------------------------------------
# save / load / delete
# ---------------------------------------------------------------------------

def test_save_creates_file(tmp_path):
    bm = Bookmark(path="/var/log/app.log", offset=256)
    dest = save_bookmark(bm, store_dir=str(tmp_path))
    assert dest.exists()


def test_save_writes_valid_json(tmp_path):
    bm = Bookmark(path="/var/log/app.log", offset=256, timestamp="2024-06-01T12:00:00")
    dest = save_bookmark(bm, store_dir=str(tmp_path))
    data = json.loads(dest.read_text())
    assert data["offset"] == 256
    assert data["timestamp"] == "2024-06-01T12:00:00"


def test_load_returns_none_when_missing(tmp_path):
    result = load_bookmark("/var/log/missing.log", store_dir=str(tmp_path))
    assert result is None


def test_load_returns_bookmark_after_save(tmp_path):
    bm = Bookmark(path="/var/log/app.log", offset=1024)
    save_bookmark(bm, store_dir=str(tmp_path))
    loaded = load_bookmark("/var/log/app.log", store_dir=str(tmp_path))
    assert loaded is not None
    assert loaded.offset == 1024


def test_delete_returns_true_when_exists(tmp_path):
    bm = Bookmark(path="/var/log/app.log", offset=0)
    save_bookmark(bm, store_dir=str(tmp_path))
    assert delete_bookmark("/var/log/app.log", store_dir=str(tmp_path)) is True


def test_delete_returns_false_when_missing(tmp_path):
    assert delete_bookmark("/var/log/nope.log", store_dir=str(tmp_path)) is False


def test_delete_removes_file(tmp_path):
    bm = Bookmark(path="/var/log/app.log", offset=0)
    dest = save_bookmark(bm, store_dir=str(tmp_path))
    delete_bookmark("/var/log/app.log", store_dir=str(tmp_path))
    assert not dest.exists()


def test_bookmark_path_uses_log_filename(tmp_path):
    p = bookmark_path("/some/deep/path/service.log", store_dir=str(tmp_path))
    assert p.name == "service.log.bookmark.json"
