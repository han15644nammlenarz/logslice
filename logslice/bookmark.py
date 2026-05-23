"""Bookmark support: save and restore byte-offset positions in log files."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Bookmark:
    """Persisted position within a log file."""

    path: str
    offset: int
    timestamp: Optional[str] = None
    saved_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "offset": self.offset,
            "timestamp": self.timestamp,
            "saved_at": self.saved_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Bookmark":
        return Bookmark(
            path=data["path"],
            offset=data["offset"],
            timestamp=data.get("timestamp"),
            saved_at=data.get("saved_at", ""),
        )


def bookmark_path(log_path: str, store_dir: Optional[str] = None) -> Path:
    """Return the path where a bookmark for *log_path* is stored."""
    store = Path(store_dir) if store_dir else Path.home() / ".logslice" / "bookmarks"
    store.mkdir(parents=True, exist_ok=True)
    safe_name = Path(log_path).name + ".bookmark.json"
    return store / safe_name


def save_bookmark(bookmark: Bookmark, store_dir: Optional[str] = None) -> Path:
    """Persist *bookmark* to disk and return the file path."""
    dest = bookmark_path(bookmark.path, store_dir)
    dest.write_text(json.dumps(bookmark.as_dict(), indent=2))
    return dest


def load_bookmark(log_path: str, store_dir: Optional[str] = None) -> Optional[Bookmark]:
    """Load a previously saved bookmark for *log_path*, or return None."""
    dest = bookmark_path(log_path, store_dir)
    if not dest.exists():
        return None
    data = json.loads(dest.read_text())
    return Bookmark.from_dict(data)


def delete_bookmark(log_path: str, store_dir: Optional[str] = None) -> bool:
    """Remove the bookmark for *log_path*. Returns True if it existed."""
    dest = bookmark_path(log_path, store_dir)
    if dest.exists():
        dest.unlink()
        return True
    return False
