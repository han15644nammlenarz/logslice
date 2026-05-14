"""Command-line interface for logslice."""

import argparse
import sys
from pathlib import Path

from logslice.timestamp_parser import parse_user_datetime
from logslice.slicer import slice_log


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logslice",
        description="Extract time-bounded slices from large log files.",
    )
    parser.add_argument(
        "logfile",
        type=Path,
        help="Path to the log file to slice.",
    )
    parser.add_argument(
        "-s", "--start",
        metavar="DATETIME",
        default=None,
        help="Start of the time range (inclusive). E.g. '2024-01-15 08:00:00'.",
    )
    parser.add_argument(
        "-e", "--end",
        metavar="DATETIME",
        default=None,
        help="End of the time range (inclusive). E.g. '2024-01-15 09:00:00'.",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        type=Path,
        default=None,
        help="Write output to FILE instead of stdout.",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="File encoding (default: utf-8).",
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.logfile.exists():
        print(f"logslice: error: file not found: {args.logfile}", file=sys.stderr)
        return 2

    start_dt = None
    end_dt = None

    try:
        if args.start:
            start_dt = parse_user_datetime(args.start)
        if args.end:
            end_dt = parse_user_datetime(args.end)
    except ValueError as exc:
        print(f"logslice: error: {exc}", file=sys.stderr)
        return 2

    if start_dt and end_dt and start_dt > end_dt:
        print("logslice: error: --start must not be later than --end.", file=sys.stderr)
        return 2

    try:
        lines = slice_log(args.logfile, start=start_dt, end=end_dt, encoding=args.encoding)
        if args.output:
            with args.output.open("w", encoding=args.encoding) as fh:
                fh.writelines(lines)
        else:
            for line in lines:
                sys.stdout.write(line)
    except OSError as exc:
        print(f"logslice: error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
