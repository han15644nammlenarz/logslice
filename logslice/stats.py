"""Collect and report statistics about a log slice operation."""

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SliceStats:
    """Mutable statistics accumulated during a slice run."""
    file_size_bytes: int = 0
    lines_written: int = 0
    bytes_written: int = 0
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    detected_format: Optional[str] = None
    elapsed_seconds: float = 0.0
    _start_time: float = field(default_factory=time.monotonic, repr=False, compare=False)

    def start_timer(self) -> None:
        self._start_time = time.monotonic()

    def stop_timer(self) -> None:
        self.elapsed_seconds = time.monotonic() - self._start_time

    @property
    def slice_size_bytes(self) -> int:
        if self.start_offset is None or self.end_offset is None:
            return 0
        return max(0, self.end_offset - self.start_offset)

    @property
    def throughput_mb_per_sec(self) -> float:
        if self.elapsed_seconds <= 0:
            return 0.0
        return (self.bytes_written / 1_048_576) / self.elapsed_seconds

    def summary(self) -> str:
        lines = [
            f"Lines written : {self.lines_written:,}",
            f"Bytes written : {self.bytes_written:,}",
            f"Elapsed       : {self.elapsed_seconds:.3f}s",
            f"Throughput    : {self.throughput_mb_per_sec:.2f} MB/s",
        ]
        if self.detected_format:
            lines.insert(0, f"Format        : {self.detected_format}")
        return "\n".join(lines)


class StatsCollector:
    """Context manager that times a block and stores results in a SliceStats."""

    def __init__(self, stats: SliceStats):
        self.stats = stats

    def __enter__(self) -> "StatsCollector":
        self.stats.start_timer()
        return self

    def __exit__(self, *_) -> None:
        self.stats.stop_timer()
