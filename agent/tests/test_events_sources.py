from pathlib import Path
import pytest
from followup_agent.events.sources import Candidate, load_source_configs
from followup_agent.events.sources.generic import GenericSource

LISTING = """
<html><body><nav><a href="/about">About</a></nav>
<a href="/event/a">A</a><a href="/event/b">B</a><a href="/event/a">A dup</a>
</body></html>
"""

CFG = {
    "name": "unsw-events",
    "type": "generic",
    "url": "https://ex.test/events",
    "link_pattern": "/event/",
    "timezone": "Australia/Sydney",
}


class FakeFetcher:
    def __init__(self, pages, fail_on=()):
        self.pages = pages
        self.fail_on = set(fail_on)
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        if url in self.fail_on:
            raise RuntimeError("boom")
        return self.pages[url]


def test_loads_config_from_yaml(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text(
        "sources:\n"
        "  - name: unsw-events\n"
        "    type: generic\n"
        "    url: https://ex.test/events\n"
        "    link_pattern: /event/\n"
        "    timezone: Australia/Sydney\n"
    )
    cfgs = load_source_configs(p)
    assert cfgs[0]["name"] == "unsw-events"
    assert cfgs[0]["timezone"] == "Australia/Sydney"


def test_missing_config_file_returns_empty_list(tmp_path):
    assert load_source_configs(tmp_path / "nope.yaml") == []


def test_config_missing_required_key_raises(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text("sources:\n  - name: broken\n    type: generic\n")
    with pytest.raises(ValueError, match="url"):
        load_source_configs(p)


def test_discovers_one_candidate_per_unique_event_link():
    f = FakeFetcher({"https://ex.test/events": LISTING})
    cands = GenericSource(CFG, f).discover()
    assert [c.url for c in cands] == ["https://ex.test/event/a", "https://ex.test/event/b"]


def test_candidate_uid_is_the_canonical_url():
    f = FakeFetcher({"https://ex.test/events": LISTING})
    cands = GenericSource(CFG, f).discover()
    assert cands[0].uid == "https://ex.test/event/a"


def test_candidates_carry_the_source_timezone():
    f = FakeFetcher({"https://ex.test/events": LISTING})
    assert GenericSource(CFG, f).discover()[0].timezone == "Australia/Sydney"


def test_generic_candidates_are_never_prefetched():
    # Generic pages need the LLM; only the Eventbrite API can prefetch.
    f = FakeFetcher({"https://ex.test/events": LISTING})
    assert all(c.prefetched is None for c in GenericSource(CFG, f).discover())


def test_listing_fetch_failure_propagates_to_the_caller():
    # crawl.py records this against the source and moves to the next one.
    f = FakeFetcher({}, fail_on=["https://ex.test/events"])
    with pytest.raises(RuntimeError):
        GenericSource(CFG, f).discover()


def test_page_cap_truncates_and_is_not_silent(capsys):
    many = "".join(f'<a href="/event/{i}">e</a>' for i in range(50))
    f = FakeFetcher({"https://ex.test/events": f"<body>{many}</body>"})
    cands = GenericSource(CFG, f, max_pages=25).discover()
    assert len(cands) == 25
    assert "cap" in capsys.readouterr().out.lower()


def test_source_name_is_exposed():
    f = FakeFetcher({"https://ex.test/events": LISTING})
    assert GenericSource(CFG, f).name == "unsw-events"
