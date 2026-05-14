"""High-level file inspector: combines sampling + progress + stats."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Optional

from logslice.sampler import SampleResult, sample_log_file
from logslice.reporter import print_warning


_LOW_PARSE_RATE_THRESHOLD = 0.5
_MIN_SAMPLE_SIZE = 4


@dataclass
class InspectionReport:
    """Summary returned by :func:`inspect_log_file`."""
    file_path: str
    sample: SampleResult
    warnings: list[str]

    @property
    def is_usable(self) -> bool:
        """True when enough lines could be parsed to attempt slicing."""
        return (
            self.sample.total_size > 0
            and self.sample.lines_sampled > 0
            and self.sample.parse_rate >= _LOW_PARSE_RATE_THRESHOLD
        )

    @property
    def detected_format(self) -> Optional[str]:
        return self.sample.detected_format


def inspect_log_file(
    file_path: str,
    num_samples: int = 8,
    emit_warnings: bool = True,
    stream=None,
) -> InspectionReport:
    """Sample *file_path* and return an :class:`InspectionReport`.

    Parameters
    ----------
    file_path:
        Path to the log file to inspect.
    num_samples:
        Number of evenly-spaced positions to probe.
    emit_warnings:
        When *True*, detected issues are printed via :func:`print_warning`.
    stream:
        Output stream for warnings (defaults to *stderr*).

    Returns
    -------
    InspectionReport
    """
    if stream is None:
        stream = sys.stderr

    sample = sample_log_file(file_path, num_samples=num_samples)
    warnings: list[str] = []

    if sample.total_size == 0:
        warnings.append(f"{file_path}: file is empty.")
    elif sample.lines_sampled == 0:
        warnings.append(f"{file_path}: no lines could be read.")
    elif sample.parse_rate < _LOW_PARSE_RATE_THRESHOLD:
        warnings.append(
            f"{file_path}: only {sample.parse_rate:.0%} of sampled lines "
            "contained a recognisable timestamp — results may be inaccurate."
        )

    if sample.detected_format is None and sample.total_size > 0:
        warnings.append(
            f"{file_path}: could not detect a timestamp format from the first line."
        )

    if emit_warnings:
        for w in warnings:
            print_warning(w, file=stream)

    return InspectionReport(
        file_path=file_path,
        sample=sample,
        warnings=warnings,
    )
