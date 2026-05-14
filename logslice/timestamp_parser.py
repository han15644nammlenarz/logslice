"""Timestamp parsing utilities for logslice.

Supports common log timestamp formats and returns
normalized datetime objects for comparison.
"""

import re
from datetime import datetime
from typing import Optional

# Ordered list of (regex_pattern, strptime_format) tuples
TIMESTAMP_FORMATS = [
    # ISO 8601: 2024-01-15T13:45:00 or 2024-01-15T13:45:00.123
    (
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?",
        "%Y-%m-%dT%H:%M:%S",
    ),
    # Common syslog: Jan 15 13:45:00
    (
        r"[A-Z][a-z]{2} [ \d]\d \d{2}:\d{2}:\d{2}",
        "%b %d %H:%M:%S",
    ),
    # Apache/nginx: 15/Jan/2024:13:45:00
    (
        r"\d{2}/[A-Z][a-z]{2}/\d{4}:\d{2}:\d{2}:\d{2}",
        "%d/%b/%Y:%H:%M:%S",
    ),
    # Simple date-time: 2024-01-15 13:45:00
    (
        r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",
        "%Y-%m-%d %H:%M:%S",
    ),
]


def parse_timestamp(line: str) -> Optional[datetime]:
    """Extract and parse the first timestamp found in a log line.

    Args:
        line: A single log line string.

    Returns:
        A datetime object if a timestamp is found, otherwise None.
    """
    for pattern, fmt in TIMESTAMP_FORMATS:
        match = re.search(pattern, line)
        if match:
            raw = match.group(0)
            # Strip sub-second precision for strptime compatibility
            raw_clean = raw.split(".")[0] if "." in raw else raw
            try:
                return datetime.strptime(raw_clean, fmt)
            except ValueError:
                continue
    return None


def parse_user_datetime(value: str) -> datetime:
    """Parse a user-supplied datetime string from the CLI.

    Accepts ISO 8601 or 'YYYY-MM-DD HH:MM:SS' formats.

    Args:
        value: Datetime string from the user.

    Returns:
        A datetime object.

    Raises:
        ValueError: If the string cannot be parsed.
    """
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(
        f"Unrecognized datetime format: '{value}'. "
        "Use YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, or 'YYYY-MM-DD HH:MM:SS'."
    )
