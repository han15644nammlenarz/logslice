"""CLI entry-point for merging multiple log files into one sorted stream."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from logslice.merger import MergeStats, merge_log_sources
from logslice.reporter import print_error, print_stats, print_warning
from logslice.stats import SliceStats


def build_merge_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logslice-merge",
        description="Merge multiple sorted log files into a single time-ordered stream.",
    )
    parser.add_argument(
        "files",
        nargs="+",
        metavar="FILE",
        help="Log files to merge (at least two).",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="OUTPUT",
        default="-",
        help="Destination file path, or '-' for stdout (default).",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print merge statistics to stderr after completion.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:  # pragma: no cover
    parser = build_merge_parser()
    args = parser.parse_args(argv)

    if len(args.files) < 2:
        print_error("At least two input files are required for merging.")
        return 1

    handles = []
    try:
        for path in args.files:
            try:
                handles.append(open(path, "r", encoding="utf-8", errors="replace"))
            except OSError as exc:
                print_error(f"Cannot open '{path}': {exc}")
                return 1

        merge_stats = MergeStats()
        merged = merge_log_sources(handles, stats=merge_stats)

        if args.output == "-":
            for line in merged:
                sys.stdout.write(line)
        else:
            with open(args.output, "w", encoding="utf-8") as out:
                for line in merged:
                    out.write(line)

        if merge_stats.parse_errors:
            print_warning(
                f"{merge_stats.parse_errors} line(s) skipped due to parse errors."
            )

        if args.stats:
            s = SliceStats()
            s.lines_written = merge_stats.lines_written
            print_stats(s)

    finally:
        for fh in handles:
            fh.close()

    return 0
