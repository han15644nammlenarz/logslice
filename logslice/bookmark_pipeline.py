"""Pipeline that resumes reading a log file from a saved bookmark."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, List, Optional

from logslice.bookmark import Bookmark, load_bookmark, save_bookmark
from logslice.slicer import slice_log
from logslice.timestamp_parser import parse_timestamp


@dataclass
class BookmarkPipelineResult:
    lines: List[str] = field(default_factory=list)
    start_offset: int = 0
    end_offset: int = 0
    bookmark_used: bool = False
    bookmark_saved: bool = False

    @property
    def line_count(self) -> int:
        return len(self.lines)


def run_bookmark_pipeline(
    log_path: str,
    *,
    store_dir: Optional[str] = None,
    start=None,
    end=None,
    update_bookmark: bool = True,
) -> BookmarkPipelineResult:
    """Slice *log_path* starting from any saved bookmark offset.

    Parameters
    ----------
    log_path:
        Path to the log file to read.
    store_dir:
        Directory where bookmarks are persisted (default: ``~/.logslice/bookmarks``).
    start:
        Optional lower-bound datetime (passed through to :func:`slice_log`).
    end:
        Optional upper-bound datetime (passed through to :func:`slice_log`).
    update_bookmark:
        When *True* (default) a new bookmark is saved pointing just past the
        last byte that was read so the next call continues from there.
    """
    result = BookmarkPipelineResult()

    existing = load_bookmark(log_path, store_dir=store_dir)
    resume_offset: int = 0
    if existing is not None:
        resume_offset = existing.offset
        result.bookmark_used = True

    result.start_offset = resume_offset

    lines: List[str] = list(
        slice_log(log_path, start=start, end=end, start_offset=resume_offset)
    )
    result.lines = lines

    # Determine the new end offset by summing byte lengths of consumed lines.
    new_offset = resume_offset + sum(len(line.encode()) for line in lines)
    result.end_offset = new_offset

    if update_bookmark and lines:
        last_ts: Optional[str] = None
        try:
            last_ts_dt = parse_timestamp(lines[-1])
            last_ts = last_ts_dt.isoformat() if last_ts_dt else None
        except Exception:
            last_ts = None

        bm = Bookmark(path=log_path, offset=new_offset, timestamp=last_ts)
        save_bookmark(bm, store_dir=store_dir)
        result.bookmark_saved = True

    return result
