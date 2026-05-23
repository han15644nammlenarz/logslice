"""Tests for logslice.field_extractor."""

import pytest

from logslice.field_extractor import (
    ExtractionResult,
    extract_fields,
    extract_fields_from_lines,
)


# ---------------------------------------------------------------------------
# ExtractionResult helpers
# ---------------------------------------------------------------------------


class TestExtractionResult:
    def test_found_returns_field_names(self):
        r = ExtractionResult(raw="x", fields={"a": "1", "b": "2"})
        assert set(r.found) == {"a", "b"}

    def test_get_existing_key(self):
        r = ExtractionResult(raw="x", fields={"level": "INFO"})
        assert r.get("level") == "INFO"

    def test_get_missing_key_returns_default(self):
        r = ExtractionResult(raw="x", fields={})
        assert r.get("missing") == ""
        assert r.get("missing", "N/A") == "N/A"

    def test_defaults_empty_fields(self):
        r = ExtractionResult(raw="plain line")
        assert r.fields == {}
        assert r.error is None


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------


def test_json_line_extracts_all_fields():
    line = '{"level": "ERROR", "msg": "disk full", "code": 42}'
    r = extract_fields(line)
    assert r.get("level") == "ERROR"
    assert r.get("msg") == "disk full"
    assert r.get("code") == "42"


def test_json_embedded_in_prefix():
    line = '2024-01-01T00:00:00Z {"service": "api", "status": "ok"}'
    r = extract_fields(line)
    assert r.get("service") == "api"
    assert r.get("status") == "ok"


def test_json_keys_filter():
    line = '{"a": "1", "b": "2", "c": "3"}'
    r = extract_fields(line, keys=["a", "c"])
    assert "a" in r.fields
    assert "c" in r.fields
    assert "b" not in r.fields


# ---------------------------------------------------------------------------
# Key=value extraction
# ---------------------------------------------------------------------------


def test_kv_basic():
    line = "level=INFO msg=started host=web01"
    r = extract_fields(line)
    assert r.get("level") == "INFO"
    assert r.get("msg") == "started"
    assert r.get("host") == "web01"


def test_kv_quoted_values():
    line = 'level=WARN msg="disk usage high" threshold=90'
    r = extract_fields(line)
    assert r.get("msg") == "disk usage high"
    assert r.get("threshold") == "90"


def test_kv_keys_filter():
    line = "a=1 b=2 c=3"
    r = extract_fields(line, keys=["b"])
    assert r.fields == {"b": "2"}


def test_kv_no_pairs_returns_empty():
    line = "plain log line with no structure"
    r = extract_fields(line)
    assert r.fields == {}


def test_prefer_json_false_uses_kv_first():
    # Line has both kv pairs AND a json blob; prefer_json=False should still
    # find kv pairs first.
    line = 'status=ok {"status": "bad"}'
    r = extract_fields(line, prefer_json=False)
    assert r.get("status") == "ok"


# ---------------------------------------------------------------------------
# Batch helper
# ---------------------------------------------------------------------------


def test_extract_fields_from_lines_batch():
    lines = [
        "level=INFO msg=boot",
        "level=ERROR msg=crash",
    ]
    results = extract_fields_from_lines(lines, keys=["level"])
    assert len(results) == 2
    assert results[0].get("level") == "INFO"
    assert results[1].get("level") == "ERROR"
    # 'msg' was filtered out
    assert "msg" not in results[0].fields


def test_extract_fields_from_lines_empty():
    assert extract_fields_from_lines([]) == []
