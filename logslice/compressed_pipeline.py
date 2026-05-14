"""Pipeline variant that transparently handles compressed input/output."""

from __future__ import annotations

import io
from typing import Iterator, Optional

from logslice.compressor import (
    CompressionFormat,
    CompressedWriter,
    format_from_path,
    open_for_reading,
)
from logslice.filter import FilterConfig
from logslice.pipeline import _iter_lines
from logslice.binary_search import find_start_offset, find_end_offset
from logslice.timestamp_parser import parse_timestamp

import datetime


def run_compressed_pipeline(
    input_path: str,
    output_path: str,
    start: Optional[datetime.datetime] = None,
    end: Optional[datetime.datetime] = None,
    filter_config: Optional[FilterConfig] = None,
) -> int:
    """Slice *input_path* (optionally compressed) and write to *output_path*.

    Compression for both input and output is inferred from file extensions.
    Returns the number of bytes written.
    """
    in_fmt = format_from_path(input_path)
    out_fmt = format_from_path(output_path)

    if in_fmt == CompressionFormat.NONE:
        # Binary-search optimisation is only possible on plain files.
        start_offset, end_offset = _plain_offsets(input_path, start, end)
    else:
        start_offset, end_offset = None, None

    lines = _read_lines(
        input_path, in_fmt, start_offset, end_offset, start, end, filter_config
    )

    writer = CompressedWriter(format=out_fmt)
    with writer.open(output_path) as fh:
        return writer.write_lines(fh, lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _plain_offsets(
    path: str,
    start: Optional[datetime.datetime],
    end: Optional[datetime.datetime],
) -> tuple[Optional[int], Optional[int]]:
    with open(path, "rb") as fh:
        so = find_start_offset(fh, start, parse_timestamp) if start else None
        eo = find_end_offset(fh, end, parse_timestamp) if end else None
    return so, eo


def _read_lines(
    path: str,
    fmt: CompressionFormat,
    start_offset: Optional[int],
    end_offset: Optional[int],
    start: Optional[datetime.datetime],
    end: Optional[datetime.datetime],
    filter_config: Optional[FilterConfig],
) -> Iterator[str]:
    with open_for_reading(path) as raw:
        if start_offset is not None:
            raw.seek(start_offset)  # type: ignore[attr-defined]
        text = io.TextIOWrapper(raw, encoding="utf-8", errors="replace")
        for line in _iter_lines(
            text,
            start=start,
            end=end,
            end_offset=end_offset,
            filter_config=filter_config,
        ):
            yield line
