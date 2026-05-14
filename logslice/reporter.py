"""Human-readable reporting helpers for logslice CLI output."""

import sys
from typing import Optional, TextIO

from logslice.stats import SliceStats


_RESET = "\033[0m"
_BOLD = "\033[1m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"


def _supports_color(stream: TextIO) -> bool:
    return hasattr(stream, "isatty") and stream.isatty()


def _fmt(text: str, code: str, stream: TextIO) -> str:
    if _supports_color(stream):
        return f"{code}{text}{_RESET}"
    return text


def print_stats(stats: SliceStats, stream: TextIO = sys.stderr) -> None:
    """Print a formatted statistics block to *stream* (default stderr)."""
    sep = "-" * 40
    stream.write(sep + "\n")
    stream.write(_fmt("logslice stats\n", _BOLD, stream))
    stream.write(sep + "\n")

    if stats.detected_format:
        stream.write(
            f"  Format    : {_fmt(stats.detected_format, _CYAN, stream)}\n"
        )
    stream.write(f"  Lines     : {_fmt(str(stats.lines_written), _GREEN, stream)}\n")
    stream.write(f"  Bytes out : {stats.bytes_written:,}\n")
    stream.write(
        f"  Elapsed   : {_fmt(f'{stats.elapsed_seconds:.3f}s', _YELLOW, stream)}\n"
    )
    stream.write(f"  Throughput: {stats.throughput_mb_per_sec:.2f} MB/s\n")
    stream.write(sep + "\n")


def print_warning(message: str, stream: TextIO = sys.stderr) -> None:
    """Emit a warning line to *stream*."""
    prefix = _fmt("WARNING", _YELLOW, stream)
    stream.write(f"[{prefix}] {message}\n")


def print_error(message: str, stream: TextIO = sys.stderr) -> None:
    """Emit an error line to *stream*."""
    prefix = _fmt("ERROR", "\033[31m", stream)
    stream.write(f"[{prefix}] {message}\n")


def low_confidence_warning(
    result_format: str,
    confidence: float,
    threshold: float = 0.5,
    stream: TextIO = sys.stderr,
) -> None:
    """Warn the user when format-detection confidence is below *threshold*."""
    if confidence < threshold:
        print_warning(
            f"Low confidence ({confidence:.0%}) detecting format '{result_format}'. "
            "Consider specifying --format explicitly.",
            stream=stream,
        )
