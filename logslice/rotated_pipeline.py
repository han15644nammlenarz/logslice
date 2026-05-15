"""Pipeline for processing rotated log file sets as a unified stream.

Combines rotated file discovery with time-bounded slicing so callers
can treat a directory of rotated logs (e.g. syslog, syslog.1,
syslog.2.gz) as a single continuous source.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from logslice.rotated import RotatedFileSet, discover_rotated_files, _open_member
from logslice.timestamp_parser import parse_timestamp
from logslice.filter import FilterConfig, apply_filter


@dataclass
class RotatedPipelineResult:
    """Summary of a rotated-log pipeline run."""

    lines_written: int = 0
    files_read: int = 0
    bytes_read: int = 0
    skipped_lines: int = 0  # lines outside the time window
    errors: list[str] = field(default_factory=list)


def _iter_lines_from_set(
    file_set: RotatedFileSet,
    start: Optional[datetime],
    end: Optional[datetime],
) -> Iterator[tuple[str, str]]:
    """Yield (member_path, line) pairs from all members of *file_set*.

    Members are iterated oldest-first (ascending by sort key).  Each
    line is decoded as UTF-8 with replacement so binary noise in old
    compressed archives does not abort the pipeline.

    Only lines whose parsed timestamp falls within [start, end] are
    yielded.  Lines whose timestamp cannot be parsed are always yielded
    so that non-timestamped continuation lines are preserved.
    """
    for member in file_set.members:
        path_str = str(member)
        try:
            fh = _open_member(member)
        except OSError as exc:
            # Caller collects errors via the result object; skip silently here.
            yield (path_str, f"__ERROR__: {exc}")
            continue

        with fh:
            for raw in fh:
                if isinstance(raw, bytes):
                    line = raw.decode("utf-8", errors="replace")
                else:
                    line = raw
                line = line.rstrip("\n")

                ts = parse_timestamp(line)
                if ts is not None:
                    if start is not None and ts < start:
                        continue
                    if end is not None and ts > end:
                        # Rotated files are sorted oldest-first; once we
                        # exceed *end* inside a file we can break early.
                        break
                yield (path_str, line)


def run_rotated_pipeline(
    base_path: Path,
    *,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    filter_cfg: Optional[FilterConfig] = None,
    output_path: Optional[Path] = None,
    encoding: str = "utf-8",
) -> RotatedPipelineResult:
    """Slice across all rotated members of *base_path* and write results.

    Parameters
    ----------
    base_path:
        Path to the *live* log file (e.g. ``/var/log/syslog``).  Rotated
        siblings are discovered automatically via
        :func:`~logslice.rotated.discover_rotated_files`.
    start:
        Inclusive lower bound on log timestamps.  ``None`` means no lower
        bound.
    end:
        Inclusive upper bound on log timestamps.  ``None`` means no upper
        bound.
    filter_cfg:
        Optional :class:`~logslice.filter.FilterConfig` for include/exclude
        pattern filtering applied *after* the time window check.
    output_path:
        If given, matched lines are written to this file.  Otherwise they
        are written to *stdout* via ``print``.
    encoding:
        Encoding used when writing to *output_path*.

    Returns
    -------
    RotatedPipelineResult
        Counters and any non-fatal error messages collected during the run.
    """
    result = RotatedPipelineResult()

    file_set = discover_rotated_files(base_path)
    result.files_read = len(file_set.members)

    out_fh: Optional[io.TextIOWrapper] = None
    if output_path is not None:
        out_fh = open(output_path, "w", encoding=encoding)  # noqa: SIM115

    try:
        for member_path, line in _iter_lines_from_set(file_set, start, end):
            if line.startswith("__ERROR__: "):
                result.errors.append(f"{member_path}: {line[len('__ERROR__: '):]}")
                continue

            result.bytes_read += len(line.encode("utf-8", errors="replace"))

            if filter_cfg is not None and filter_cfg.is_active():
                if not filter_cfg.accepts(line):
                    result.skipped_lines += 1
                    continue

            if out_fh is not None:
                out_fh.write(line + "\n")
            else:
                print(line)

            result.lines_written += 1
    finally:
        if out_fh is not None:
            out_fh.close()

    return result
