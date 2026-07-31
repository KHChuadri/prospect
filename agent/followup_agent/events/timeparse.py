import re
from datetime import datetime, timezone
from typing import Optional, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def to_utc(local_iso: Optional[str], tz_name: str) -> Optional[datetime]:
    """Convert an ISO-8601 time as printed on a page into an absolute UTC instant.

    Source pages print local times with no offset ("Wednesday 13 August, 6:30pm").
    starts_at is TIMESTAMPTZ — an absolute instant — so a naive Sydney time stored
    as-is would display 10-11 hours out. zoneinfo also handles the AEST/AEDT switch,
    which a hardcoded offset would not.

    Returns None for anything unparseable ("early autumn"), never a guess.
    """
    if not local_iso:
        return None
    try:
        parsed = datetime.fromisoformat(local_iso.strip())
    except (ValueError, AttributeError):
        return None
    if parsed.tzinfo is not None:
        # Already absolute — respect it rather than relabelling its offset.
        return parsed.astimezone(timezone.utc)
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        return None
    return parsed.replace(tzinfo=tz).astimezone(timezone.utc)


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").strip().lower())


def dedup_key(title: str, starts_at: Optional[datetime]) -> Optional[Tuple[str, str]]:
    """Cross-source duplicate key (Gate 4).

    The same meetup listed on both Eventbrite and a university page should
    collapse to one row. Events with no known date are exempt — they cannot
    collide on a date, so deduping them would be guessing.
    """
    if starts_at is None:
        return None
    return (normalize_title(title), starts_at.date().isoformat())
