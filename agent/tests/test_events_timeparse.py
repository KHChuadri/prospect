from datetime import datetime, timezone
import pytest
from followup_agent.events import timeparse


def test_converts_sydney_local_time_to_utc():
    # 6:30pm AEST (UTC+10) on 13 Aug is 08:30 UTC the same day.
    got = timeparse.to_utc("2026-08-13T18:30:00", "Australia/Sydney")
    assert got == datetime(2026, 8, 13, 8, 30, tzinfo=timezone.utc)


def test_handles_daylight_saving():
    # 6:30pm AEDT (UTC+11) on 13 Jan is 07:30 UTC — one hour different
    # from the winter case above. Hardcoding +10 would get this wrong.
    got = timeparse.to_utc("2026-01-13T18:30:00", "Australia/Sydney")
    assert got == datetime(2026, 1, 13, 7, 30, tzinfo=timezone.utc)


def test_date_only_input_becomes_midnight_local():
    got = timeparse.to_utc("2026-08-13", "Australia/Sydney")
    assert got == datetime(2026, 8, 12, 14, 0, tzinfo=timezone.utc)


def test_none_passes_through():
    assert timeparse.to_utc(None, "Australia/Sydney") is None


def test_unparseable_string_returns_none():
    # A page saying "early autumn" must yield null, never a guessed date.
    assert timeparse.to_utc("early autumn", "Australia/Sydney") is None


def test_already_aware_input_is_respected_not_relabelled():
    got = timeparse.to_utc("2026-08-13T18:30:00+00:00", "Australia/Sydney")
    assert got == datetime(2026, 8, 13, 18, 30, tzinfo=timezone.utc)


def test_unknown_timezone_returns_none():
    assert timeparse.to_utc("2026-08-13T18:30:00", "Mars/Olympus") is None


def test_normalize_title_lowercases_and_collapses_whitespace():
    assert timeparse.normalize_title("  Fintech   Careers  PANEL ") == "fintech careers panel"


def test_dedup_key_matches_across_whitespace_and_case():
    d = datetime(2026, 8, 13, 8, 30, tzinfo=timezone.utc)
    assert timeparse.dedup_key("Fintech Panel", d) == timeparse.dedup_key("  fintech   panel ", d)


def test_dedup_key_differs_on_different_dates():
    a = datetime(2026, 8, 13, 8, 30, tzinfo=timezone.utc)
    b = datetime(2026, 8, 14, 8, 30, tzinfo=timezone.utc)
    assert timeparse.dedup_key("Fintech Panel", a) != timeparse.dedup_key("Fintech Panel", b)


def test_dedup_key_is_none_when_date_unknown():
    # Null-date events can't collide on a date, so deduping them would be guessing.
    assert timeparse.dedup_key("Autumn Careers Fair", None) is None
