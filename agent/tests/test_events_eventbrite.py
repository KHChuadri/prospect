import httpx
import pytest
from followup_agent.events.sources.eventbrite import EventbriteSource, parse_event

RAW = {
    "id": "9988776655",
    "url": "https://www.eventbrite.com.au/e/fintech-panel-9988776655",
    "name": {"text": "Fintech Careers Panel"},
    "description": {"text": "Engineers from three fintechs discuss hiring."},
    "start": {"local": "2026-08-13T18:30:00", "timezone": "Australia/Sydney"},
    "end": {"local": "2026-08-13T20:30:00"},
    "online_event": False,
    "venue": {"name": "Level39", "address": {"localized_address_display": "1 Canada Sq"}},
    "organizer": {"name": "Monzo"},
}

CFG = {"name": "eventbrite", "type": "eventbrite", "timezone": "Australia/Sydney",
       "city": "Sydney"}


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_parses_core_fields():
    uid, url, ev = parse_event(RAW)
    assert uid == "9988776655"
    assert url == "https://www.eventbrite.com.au/e/fintech-panel-9988776655"
    assert ev.title == "Fintech Careers Panel"
    assert ev.starts_at_local == "2026-08-13T18:30:00"
    assert ev.ends_at_local == "2026-08-13T20:30:00"


def test_marks_api_results_as_career_events():
    # The query already filters by category; the gate stays satisfiable
    # without spending an LLM call to re-confirm.
    assert parse_event(RAW)[2].is_career_event is True


def test_organizer_becomes_an_organization():
    assert parse_event(RAW)[2].organizations == ["Monzo"]


def test_venue_becomes_location():
    assert "Level39" in parse_event(RAW)[2].location


def test_online_event_sets_the_flag_and_tolerates_no_venue():
    raw = {**RAW, "online_event": True, "venue": None}
    ev = parse_event(raw)[2]
    assert ev.is_online is True
    assert ev.location is None


def test_missing_optional_fields_do_not_raise():
    minimal = {"id": "1", "url": "https://e.test/1", "name": {"text": "X"}}
    uid, url, ev = parse_event(minimal)
    assert uid == "1" and ev.title == "X"
    assert ev.starts_at_local is None and ev.organizations == []


def test_discover_returns_prefetched_candidates():
    def handler(request):
        return httpx.Response(200, json={"events": [RAW], "pagination": {"has_more_items": False}})

    src = EventbriteSource(CFG, token="tok", location="Sydney", client=_client(handler))
    cands = src.discover()
    assert len(cands) == 1
    assert cands[0].uid == "9988776655"
    assert cands[0].prefetched is not None       # no LLM call needed downstream
    assert cands[0].timezone == "Australia/Sydney"


def test_missing_token_yields_no_candidates_rather_than_crashing():
    src = EventbriteSource(CFG, token="", location="Sydney")
    assert src.discover() == []


def test_api_error_propagates_to_the_caller():
    def handler(request):
        return httpx.Response(401, json={"error": "unauthorized"})

    src = EventbriteSource(CFG, token="bad", location="Sydney", client=_client(handler))
    with pytest.raises(httpx.HTTPError):
        src.discover()


def test_sends_the_bearer_token_and_location():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("authorization")
        seen["query"] = str(request.url)
        return httpx.Response(200, json={"events": [], "pagination": {"has_more_items": False}})

    EventbriteSource(CFG, token="tok", location="Sydney",
                     client=_client(handler)).discover()
    assert seen["auth"] == "Bearer tok"
    assert "Sydney" in seen["query"]
