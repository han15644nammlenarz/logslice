"""Tests for logslice.progress."""

from __future__ import annotations

import io
import time

import pytest

from logslice.progress import (
    ProgressState,
    render_progress,
    update_progress,
    finish_progress,
)


def test_percent_zero_when_no_total():
    state = ProgressState(total_bytes=0, bytes_processed=0)
    assert state.percent == 0.0


def test_percent_capped_at_100():
    state = ProgressState(total_bytes=100, bytes_processed=200)
    assert state.percent == 100.0


def test_percent_midpoint():
    state = ProgressState(total_bytes=1000, bytes_processed=500)
    assert state.percent == pytest.approx(50.0)


def test_mb_per_sec_zero_when_no_elapsed(monkeypatch):
    fixed = 1_000_000.0
    monkeypatch.setattr("time.monotonic", lambda: fixed)
    state = ProgressState(total_bytes=1024 * 1024, bytes_processed=1024 * 1024)
    state.start_time = fixed  # elapsed == 0
    assert state.mb_per_sec == 0.0


def test_render_progress_contains_percent():
    state = ProgressState(total_bytes=1000, bytes_processed=250)
    rendered = render_progress(state)
    assert "25.0%" in rendered


def test_render_progress_contains_bar_chars():
    state = ProgressState(total_bytes=100, bytes_processed=50)
    rendered = render_progress(state)
    assert "#" in rendered
    assert "-" in rendered


def test_update_progress_increments_bytes():
    stream = io.StringIO()
    state = ProgressState(total_bytes=1000, bytes_processed=0, report_interval=0.0)
    update_progress(state, 400, stream=stream, force=True)
    assert state.bytes_processed == 400


def test_update_progress_writes_to_stream():
    stream = io.StringIO()
    state = ProgressState(total_bytes=1000, bytes_processed=0, report_interval=0.0)
    update_progress(state, 100, stream=stream, force=True)
    assert len(stream.getvalue()) > 0


def test_finish_progress_writes_newline():
    stream = io.StringIO()
    state = ProgressState(total_bytes=500, bytes_processed=300, report_interval=0.0)
    finish_progress(state, stream=stream)
    assert stream.getvalue().endswith("\n")


def test_finish_progress_sets_bytes_to_total():
    stream = io.StringIO()
    state = ProgressState(total_bytes=800, bytes_processed=400)
    finish_progress(state, stream=stream)
    assert state.bytes_processed == 800
