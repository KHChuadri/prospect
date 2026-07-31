from datetime import datetime, timezone, timedelta
import pytest
from followup_agent import db
from followup_agent.events import crawl
from followup_agent.events.sources import Candidate
from followup_agent.models import EventExtract

NOW = datetime(2026, 7, 31, tzinfo=timezone.utc)
TZ = "Australia/Sydney"


class FakeSource:
    def __init__(self, name, candidates, raises=None):
        self.name = name
        self._candidates = candidates
        self._raises = raises

    def discover(self):
        if self._raises:
            raise self._raises
        return self._candidates


def _cand(uid, url=None, prefetched=None):
    return Candidate(uid=uid, url=url or f"https://ex.test/{uid}",
                     timezone=TZ, prefetched=prefetched)


def _ev(title="Fintech Panel", start="2026-08-13T18:30:00", **kw):
    return EventExtract(is_career_event=True, title=title,
                        starts_at_local=start, **kw)


def _setup(monkeypatch, *, seen=None):
    monkeypatch.setattr(db, "existing_source_uids", lambda conn: set(seen or set()))
    monkeypatch.setattr(db, "record_crawl_state", lambda conn, name, **kw: None)
    created = []

    def fake_create(conn, **kw):
        created.append(kw)
        return len(created)

    monkeypatch.setattr(db, "create_event", fake_create)
    return created


def _run(sources, *, fetch_fn=None, extract_fn=None, **kw):
    return crawl.run_events_batch(
        conn=None, sources=sources,
        fetch_fn=fetch_fn or (lambda url: "<p>page</p>"),
        extract_fn=extract_fn or (lambda text, url: _ev()),
        now=NOW, **kw)


def test_creates_an_event_from_a_generic_candidate(monkeypatch):
    created = _setup(monkeypatch)
    ids = _run([FakeSource("unsw", [_cand("e1")])])
    assert ids == [1]
    assert created[0]["title"] == "Fintech Panel"
    assert created[0]["source_name"] == "unsw"


def test_url_comes_from_the_crawler_not_the_extractor(monkeypatch):
    # Injection defence: whatever the page says, the stored url is the one
    # we actually fetched.
    created = _setup(monkeypatch)
    _run([FakeSource("unsw", [_cand("e1", url="https://ex.test/real")])])
    assert created[0]["url"] == "https://ex.test/real"


def test_local_time_is_converted_to_utc(monkeypatch):
    created = _setup(monkeypatch)
    _run([FakeSource("unsw", [_cand("e1")])])
    assert created[0]["starts_at"] == datetime(2026, 8, 13, 8, 30, tzinfo=timezone.utc)


def test_gate1_skips_already_stored_uids_without_fetching(monkeypatch):
    created = _setup(monkeypatch, seen={("unsw", "e1")})

    def boom(url):
        raise AssertionError("must not fetch a known uid")

    ids = _run([FakeSource("unsw", [_cand("e1")])], fetch_fn=boom)
    assert ids == [] and created == []


def test_gate1_is_scoped_per_source(monkeypatch):
    created = _setup(monkeypatch, seen={("eventbrite", "e1")})
    ids = _run([FakeSource("unsw", [_cand("e1")])])
    assert ids == [1]


def test_gate2_skips_non_career_events(monkeypatch):
    created = _setup(monkeypatch)
    ids = _run([FakeSource("unsw", [_cand("e1")])],
               extract_fn=lambda t, u: EventExtract(is_career_event=False, title="Choir"))
    assert ids == [] and created == []


def test_gate2_skips_empty_titles(monkeypatch):
    created = _setup(monkeypatch)
    ids = _run([FakeSource("unsw", [_cand("e1")])],
               extract_fn=lambda t, u: _ev(title="   "))
    assert ids == []


def test_gate3_skips_past_events(monkeypatch):
    created = _setup(monkeypatch)
    ids = _run([FakeSource("unsw", [_cand("e1")])],
               extract_fn=lambda t, u: _ev(start="2020-01-01T10:00:00"))
    assert ids == []


def test_gate3_skips_implausibly_distant_events(monkeypatch):
    # A hallucinated year must not sit at the bottom of the feed forever.
    created = _setup(monkeypatch)
    ids = _run([FakeSource("unsw", [_cand("e1")])],
               extract_fn=lambda t, u: _ev(start="2099-01-01T10:00:00"))
    assert ids == []


def test_gate3_admits_events_with_no_date(monkeypatch):
    # "early autumn" is real and worth showing as Date TBC.
    created = _setup(monkeypatch)
    ids = _run([FakeSource("unsw", [_cand("e1")])],
               extract_fn=lambda t, u: _ev(title="Autumn Fair", start=None))
    assert ids == [1]
    assert created[0]["starts_at"] is None


def test_gate4_collapses_the_same_event_across_sources(monkeypatch):
    created = _setup(monkeypatch)
    ids = _run([
        FakeSource("unsw", [_cand("a")]),
        FakeSource("eventbrite", [_cand("b")]),
    ])
    assert ids == [1]          # same title + date, second one dropped


def test_gate4_keeps_distinct_events(monkeypatch):
    created = _setup(monkeypatch)
    titles = iter(["Panel One", "Panel Two"])
    ids = _run([FakeSource("unsw", [_cand("a"), _cand("b")])],
               extract_fn=lambda t, u: _ev(title=next(titles)))
    assert ids == [1, 2]


def test_gate4_does_not_collapse_undated_events(monkeypatch):
    created = _setup(monkeypatch)
    ids = _run([FakeSource("unsw", [_cand("a"), _cand("b")])],
               extract_fn=lambda t, u: _ev(title="Autumn Fair", start=None))
    assert ids == [1, 2]


def test_prefetched_candidates_skip_fetch_and_extract(monkeypatch):
    created = _setup(monkeypatch)

    def boom(*a, **k):
        raise AssertionError("prefetched candidates must not fetch or extract")

    ids = _run([FakeSource("eventbrite", [_cand("e1", prefetched=_ev())])],
               fetch_fn=boom, extract_fn=boom)
    assert ids == [1]


def test_one_failing_source_does_not_stop_the_others(monkeypatch):
    created = _setup(monkeypatch)
    ids = _run([
        FakeSource("broken", [], raises=RuntimeError("site down")),
        FakeSource("unsw", [_cand("e1")]),
    ])
    assert ids == [1]


def test_source_failure_is_recorded_not_swallowed(monkeypatch):
    _setup(monkeypatch)
    errors = []
    monkeypatch.setattr(db, "record_crawl_state",
                        lambda conn, name, **kw: errors.append((name, kw.get("error"))))
    _run([FakeSource("broken", [], raises=RuntimeError("site down"))])
    assert errors[0][0] == "broken"
    assert "site down" in errors[0][1]


def test_successful_source_records_a_clear_state(monkeypatch):
    _setup(monkeypatch)
    states = []
    monkeypatch.setattr(db, "record_crawl_state",
                        lambda conn, name, **kw: states.append(kw.get("error")))
    _run([FakeSource("unsw", [_cand("e1")])])
    assert states == [None]


def test_one_failing_event_does_not_stop_the_rest(monkeypatch):
    created = _setup(monkeypatch)
    titles = iter(["Panel One", "Panel Two"])

    def extract_fn(text, url):
        if url.endswith("bad"):
            raise RuntimeError("LLM 429")
        return _ev(title=next(titles))

    ids = _run([FakeSource("unsw", [_cand("bad"), _cand("good")])],
               extract_fn=extract_fn)
    assert ids == [1]


def test_fetch_failure_on_one_page_does_not_stop_the_rest(monkeypatch):
    created = _setup(monkeypatch)
    titles = iter(["Panel One", "Panel Two"])

    def fetch_fn(url):
        if url.endswith("bad"):
            raise RuntimeError("connection refused")
        return "<p>ok</p>"

    ids = _run([FakeSource("unsw", [_cand("bad"), _cand("good")])],
               fetch_fn=fetch_fn, extract_fn=lambda t, u: _ev(title=next(titles)))
    assert ids == [1]


def test_no_sync_cursor_is_written(monkeypatch):
    # The stateless design is what makes retries free. Nothing must be
    # holding a cursor here.
    _setup(monkeypatch)
    monkeypatch.setattr(db, "set_sync_state",
                        lambda *a, **k: pytest.fail("crawler must not use a cursor"))
    _run([FakeSource("unsw", [_cand("e1")])])
