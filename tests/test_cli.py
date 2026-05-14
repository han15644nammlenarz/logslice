"""Tests for the logslice CLI entry point."""

import textwrap
from pathlib import Path

import pytest

from logslice.cli import main


LOG_CONTENT = textwrap.dedent("""\
    2024-01-15T07:55:00 startup complete
    2024-01-15T08:00:00 request received
    2024-01-15T08:30:00 processing done
    2024-01-15T09:00:00 request received
    2024-01-15T09:30:00 shutdown initiated
""").encode()


@pytest.fixture()
def log_file(tmp_path: Path) -> Path:
    p = tmp_path / "app.log"
    p.write_bytes(LOG_CONTENT)
    return p


def test_no_bounds_prints_all_lines(log_file, capsys):
    rc = main([str(log_file)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "startup complete" in out
    assert "shutdown initiated" in out


def test_start_bound_filters_early_lines(log_file, capsys):
    rc = main([str(log_file), "--start", "2024-01-15 08:00:00"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "startup complete" not in out
    assert "request received" in out


def test_end_bound_filters_late_lines(log_file, capsys):
    rc = main([str(log_file), "--end", "2024-01-15 08:30:00"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "shutdown initiated" not in out
    assert "startup complete" in out


def test_start_and_end_bound(log_file, capsys):
    rc = main([str(log_file), "-s", "2024-01-15 08:00:00", "-e", "2024-01-15 09:00:00"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "startup complete" not in out
    assert "shutdown initiated" not in out
    assert "request received" in out


def test_output_file_written(log_file, tmp_path, capsys):
    out_file = tmp_path / "out.log"
    rc = main([str(log_file), "-o", str(out_file)])
    assert rc == 0
    assert out_file.exists()
    content = out_file.read_text()
    assert "startup complete" in content
    assert capsys.readouterr().out == ""


def test_missing_file_returns_exit_code_2(capsys):
    rc = main(["/nonexistent/path/app.log"])
    assert rc == 2
    assert "not found" in capsys.readouterr().err


def test_invalid_start_datetime_returns_exit_code_2(log_file, capsys):
    rc = main([str(log_file), "--start", "not-a-date"])
    assert rc == 2
    assert "error" in capsys.readouterr().err.lower()


def test_start_after_end_returns_exit_code_2(log_file, capsys):
    rc = main([str(log_file), "-s", "2024-01-15 10:00:00", "-e", "2024-01-15 08:00:00"])
    assert rc == 2
    assert "error" in capsys.readouterr().err.lower()
