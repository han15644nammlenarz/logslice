"""Tests for logslice.compressor."""

from __future__ import annotations

import gzip
import bz2
import os
import pytest

from logslice.compressor import (
    CompressionFormat,
    CompressedWriter,
    format_from_path,
    open_for_reading,
)


def test_format_from_path_gz():
    assert format_from_path("output.log.gz") == CompressionFormat.GZIP


def test_format_from_path_bz2():
    assert format_from_path("output.log.bz2") == CompressionFormat.BZIP2


def test_format_from_path_plain():
    assert format_from_path("output.log") == CompressionFormat.NONE


def test_format_from_path_no_extension():
    assert format_from_path("outputlog") == CompressionFormat.NONE


def test_compressed_writer_defaults():
    cw = CompressedWriter()
    assert cw.format == CompressionFormat.NONE
    assert cw.bytes_written == 0


def test_write_lines_plain(tmp_path):
    out = tmp_path / "out.log"
    cw = CompressedWriter(format=CompressionFormat.NONE)
    with cw.open(str(out)) as fh:
        lines = ["line one\n", "line two\n"]
        total = cw.write_lines(fh, iter(lines))
    assert total == sum(len(l.encode()) for l in lines)
    assert cw.bytes_written == total
    assert out.read_text() == "line one\nline two\n"


def test_write_lines_gzip(tmp_path):
    out = tmp_path / "out.log.gz"
    cw = CompressedWriter(format=CompressionFormat.GZIP)
    lines = ["hello gz\n", "world\n"]
    with cw.open(str(out)) as fh:
        cw.write_lines(fh, iter(lines))
    with gzip.open(str(out), "rb") as fh:
        content = fh.read().decode()
    assert content == "hello gz\nworld\n"


def test_write_lines_bzip2(tmp_path):
    out = tmp_path / "out.log.bz2"
    cw = CompressedWriter(format=CompressionFormat.BZIP2)
    lines = ["bzip2 line\n"]
    with cw.open(str(out)) as fh:
        cw.write_lines(fh, iter(lines))
    with bz2.open(str(out), "rb") as fh:
        content = fh.read().decode()
    assert content == "bzip2 line\n"


def test_open_for_reading_plain(tmp_path):
    p = tmp_path / "plain.log"
    p.write_bytes(b"plain content\n")
    with open_for_reading(str(p)) as fh:
        assert fh.read() == b"plain content\n"


def test_open_for_reading_gz(tmp_path):
    p = tmp_path / "data.log.gz"
    with gzip.open(str(p), "wb") as fh:
        fh.write(b"gzipped\n")
    with open_for_reading(str(p)) as fh:
        assert fh.read() == b"gzipped\n"


def test_open_for_reading_bz2(tmp_path):
    p = tmp_path / "data.log.bz2"
    with bz2.open(str(p), "wb") as fh:
        fh.write(b"bzipped\n")
    with open_for_reading(str(p)) as fh:
        assert fh.read() == b"bzipped\n"
