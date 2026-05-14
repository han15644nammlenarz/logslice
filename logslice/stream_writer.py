"""Write sliced log output using chunked streaming to avoid high memory usage."""

from __future__ import annotations

import sys
from typing import Optional, TextIO

from logslice.chunker import iter_chunks, DEFAULT_CHUNK_SIZE


def stream_to_output(
    path: str,
    start_offset: int = 0,
    end_offset: Optional[int] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    output: TextIO = sys.stdout,
) -> int:
    """Stream bytes from *path* between *start_offset* and *end_offset* to
    *output*, decoding each chunk as UTF-8 (with replacement for bad bytes).

    Returns the total number of lines written.
    """
    total_lines = 0

    for chunk in iter_chunks(
        path,
        start_offset=start_offset,
        end_offset=end_offset,
        chunk_size=chunk_size,
    ):
        text = chunk.data.decode("utf-8", errors="replace")
        output.write(text)
        total_lines += chunk.lines_in_chunk

    return total_lines


def stream_to_file(
    source_path: str,
    dest_path: str,
    start_offset: int = 0,
    end_offset: Optional[int] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> int:
    """Write the slice from *source_path* directly to *dest_path* in binary
    mode, avoiding any encoding overhead.

    Returns the total number of bytes written.
    """
    total_bytes = 0

    with open(dest_path, "wb") as dest_fh:
        for chunk in iter_chunks(
            source_path,
            start_offset=start_offset,
            end_offset=end_offset,
            chunk_size=chunk_size,
        ):
            dest_fh.write(chunk.data)
            total_bytes += chunk.size_bytes

    return total_bytes
