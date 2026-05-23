"""Extract specific fields from structured log lines (key=value, JSON, etc.)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


_KV_RE = re.compile(r'(\w[\w.\-]*)\s*=\s*(?:"([^"]*)"|(\'[^\']*\')|([\S]*))')


@dataclass
class ExtractionResult:
    """Holds fields extracted from a single log line."""

    raw: str
    fields: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def found(self) -> List[str]:
        """Return the list of field names that were extracted."""
        return list(self.fields.keys())

    def get(self, key: str, default: str = "") -> str:
        """Return the value for *key*, or *default* if not present."""
        return self.fields.get(key, default)


def _extract_json(line: str) -> Optional[Dict[str, str]]:
    """Try to parse the line (or the first JSON object found in it) as JSON."""
    start = line.find("{")
    if start == -1:
        return None
    try:
        obj = json.loads(line[start:])
        if isinstance(obj, dict):
            return {k: str(v) for k, v in obj.items()}
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def _extract_kv(line: str) -> Dict[str, str]:
    """Extract key=value pairs from a log line."""
    result: Dict[str, str] = {}
    for m in _KV_RE.finditer(line):
        key = m.group(1)
        value = m.group(2) or m.group(3) or m.group(4) or ""
        # Strip surrounding quotes from single-quoted values
        if value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        result[key] = value
    return result


def extract_fields(
    line: str,
    keys: Optional[List[str]] = None,
    prefer_json: bool = True,
) -> ExtractionResult:
    """Extract fields from *line*.

    Parameters
    ----------
    line:
        A single log line (with or without trailing newline).
    keys:
        If provided, only these field names are retained in the result.
    prefer_json:
        When ``True`` (default), attempt JSON parsing before falling back to
        key=value extraction.
    """
    stripped = line.rstrip("\n")
    fields: Dict[str, str] = {}
    error: Optional[str] = None

    if prefer_json:
        parsed = _extract_json(stripped)
        if parsed is not None:
            fields = parsed
        else:
            fields = _extract_kv(stripped)
    else:
        fields = _extract_kv(stripped)
        if not fields:
            parsed = _extract_json(stripped)
            if parsed is not None:
                fields = parsed

    if keys:
        fields = {k: v for k, v in fields.items() if k in keys}

    return ExtractionResult(raw=stripped, fields=fields, error=error)


def extract_fields_from_lines(
    lines: List[str],
    keys: Optional[List[str]] = None,
    prefer_json: bool = True,
) -> List[ExtractionResult]:
    """Convenience wrapper: extract fields from every line in *lines*."""
    return [extract_fields(ln, keys=keys, prefer_json=prefer_json) for ln in lines]
