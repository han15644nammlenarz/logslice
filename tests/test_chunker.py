"""Tests for logslice.chunker."""

from __future__ import annotations

import os
import tempfile
from typing import Generator

import pytest

from logslice.chunker import ChunkResult, iter_chunks, DEFAULT_CHUNK_SIZE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_log(lines: list[str]) -> str:
    """Write *lines* to a temp file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".log")
    with os.fdopen(fd, "wb") as fh:
        for line in lines:
            fh.write((line + "\n").encode())
    return path


@pytest.fixture()
def small_log(tmp_path):
    path = tmp_path / "small.log"
    path.write_bytes(b"line1\nline2\nline3\nline4\nline5\n")
    return str(path)


# ---------------------------------------------------------------------------
# ChunkResult
# ---------------------------------------------------------------------------

class TestChunkResult:
    def test_size_bytes_matches_data_length(self):
        cr = ChunkResult(data=b"hello\n", chunk_index=0, byte_offset=0)
        assert cr.size_bytes == 6

    def test_defaults(self):
        cr = ChunkResult(data=b"", chunk_index=0, byte_offset=0)
        assert cr.lines_in_chunk == 0
        assert cr.is_last is False


# ---------------------------------------------------------------------------
# iter_chunks
# ---------------------------------------------------------------------------

def test_invalid_chunk_size_raises(small_log):
    with pytest.raises(ValueError):
        list(iter_chunks(small_log, chunk_size=0))


def test_all_content_returned_no_bounds(small_log):
    chunks = list(iter_chunks(small_log))
    combined = b"".join(c.data for c in chunks)
    assert combined == b"line1\nline2\nline3\nline4\nline5\n"


def test_chunk_indices_are_sequential(small_log):
    chunks = list(iter_chunks(small_log, chunk_size=8))
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_byte_offsets_are_contiguous(small_log):
    chunks = list(iter_chunks(small_log, chunk_size=8))
    for i in range(1, len(chunks)):
        assert chunks[i].byte_offset == chunks[i - 1].byte_offset + chunks[i - 1].size_bytes


def test_start_offset_respected(small_log):
    # Skip first line "line1\n" (6 bytes)
    chunks = list(iter_chunks(small_log, start_offset=6))
    combined = b"".join(c.data for c in chunks)
    assert combined.startswith(b"line2")


def test_end_offset_respected(small_log):
    # Only read first two lines: "line1\n" + "line2\n" = 12 bytes
    chunks = list(iter_chunks(small_log, end_offset=12))
    combined = b"".join(c.data for c in chunks)
    assert b"line3" not in combined
    assert b"line1" in combined


def test_lines_in_chunk_counted(small_log):
    chunks = list(iter_chunks(small_log))
    total_lines = sum(c.lines_in_chunk for c in chunks)
    assert total_lines == 5


def test_empty_file_yields_no_chunks(tmp_path):
    path = tmp_path / "empty.log"
    path.write_bytes(b"")
    chunks = list(iter_chunks(str(path)))
    assert chunks == []


def test_no_partial_lines_across_chunks(tmp_path):
    """Every chunk must end with a newline when more chunks follow."""
    path = tmp_path / "multi.log"
    path.write_bytes(b"aaaa\nbbbb\ncccc\ndddd\neeee\n")
    chunks = list(iter_chunks(str(path), chunk_size=7))
    for chunk in chunks[:-1]:
        assert chunk.data.endswith(b"\n"), f"Chunk did not end with newline: {chunk.data!r}"
