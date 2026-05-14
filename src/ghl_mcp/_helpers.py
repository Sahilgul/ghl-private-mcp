"""Shared date/timezone utilities for GHL tool modules.

Used by the calendars surface; other surfaces work with ISO strings
directly (GHL accepts both epoch-ms and ISO for most endpoints).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo  # type: ignore[no-redef]


def normalize_iana_tz(tz_str: str | None) -> Any | None:
    """Return a ``zoneinfo.ZoneInfo`` object or ``None`` on failure."""
    if not tz_str:
        return None
    try:
        return zoneinfo.ZoneInfo(tz_str)
    except (zoneinfo.ZoneInfoNotFoundError, KeyError):
        return None


def to_epoch_ms(dt: datetime, *, field: str = "datetime", iana_tz: str | None = None) -> int:
    """Convert a datetime to epoch milliseconds.

    If ``dt`` is naive and ``iana_tz`` is provided, it is localised to
    that timezone before conversion.  A naive datetime with no fallback
    is localised to UTC with a warning embedded in the field name.
    """
    if dt.tzinfo is None:
        zone = normalize_iana_tz(iana_tz)
        if zone is not None:
            dt = dt.replace(tzinfo=zone)
        else:
            dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)
