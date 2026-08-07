import json

import pytest

from followup_agent.events.fetch import FetchError
from followup_agent.jobs.sources import greenhouse, lever

GH_PAYLOAD = {
    "jobs": [
        {"id": 8023928,
         "title": "Backend Engineer",
         "absolute_url": "https://stripe.com/jobs/search?gh_jid=8023928",
         "location": {"name": "Sydney, Australia"},
         "updated_at": "2026-08-04T09:12:00-04:00"},
        {"id": 8023929,
         "title": "  ",
         "absolute_url": "https://stripe.com/jobs/8023929",
         "location": {"name": "Remote"}},
    ]
}

LEVER_PAYLOAD = [
    {"id": "abc-123",
     "text": "Forward Deployed Engineer",
     "hostedUrl": "https://jobs.lever.co/palantir/abc-123",
     "categories": {"location": "Sydney"},
     "createdAt": 1785000000000},
    {"id": "def-456",
     "text": "Data Scientist",
     "hostedUrl": "https://jobs.lever.co/palantir/def-456",
     "categories": {}},
]


class FakeFetcher:
    def __init__(self, body="", raises=None):
        self.body = body
        self.raises = raises
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        if self.raises:
            raise self.raises
        return self.body


GH_CFG = {"name": "greenhouse-stripe", "type": "greenhouse", "slug": "stripe"}
LEVER_CFG = {"name": "lever-palantir", "type": "lever", "slug": "palantir"}


# --- Greenhouse ---------------------------------------------------------

def test_greenhouse_parses_a_posting():
    out = greenhouse.parse_jobs(GH_PAYLOAD, "stripe", "Stripe")
    assert out[0].uid == "greenhouse:stripe:8023928"
    assert out[0].company == "Stripe"
    assert out[0].role == "Backend Engineer"
    assert out[0].url == "https://stripe.com/jobs/search?gh_jid=8023928"
    assert out[0].location == "Sydney, Australia"
    assert out[0].posted_at == "2026-08-04"


def test_greenhouse_drops_titleless_postings():
    assert len(greenhouse.parse_jobs(GH_PAYLOAD, "stripe", "Stripe")) == 1


def test_greenhouse_handles_missing_date():
    payload = {"jobs": [{"id": 1, "title": "Eng",
                         "absolute_url": "https://ex.test/1"}]}
    assert greenhouse.parse_jobs(payload, "s", "S")[0].posted_at is None


def test_greenhouse_empty_payload():
    assert greenhouse.parse_jobs({}, "s", "S") == []


def test_greenhouse_source_builds_the_board_url():
    f = FakeFetcher(json.dumps(GH_PAYLOAD))
    greenhouse.GreenhouseSource(GH_CFG, f).discover()
    assert f.urls == ["https://boards-api.greenhouse.io/v1/boards/stripe/jobs"]


def test_greenhouse_company_defaults_to_titlecased_slug():
    f = FakeFetcher(json.dumps(GH_PAYLOAD))
    out = greenhouse.GreenhouseSource(GH_CFG, f).discover()
    assert out[0].company == "Stripe"


def test_greenhouse_company_override_from_config():
    cfg = dict(GH_CFG, company="Stripe Inc")
    f = FakeFetcher(json.dumps(GH_PAYLOAD))
    assert greenhouse.GreenhouseSource(cfg, f).discover()[0].company == "Stripe Inc"


def test_greenhouse_fetch_error_propagates():
    src = greenhouse.GreenhouseSource(GH_CFG, FakeFetcher(raises=FetchError("nope")))
    with pytest.raises(FetchError):
        src.discover()


def test_greenhouse_cap_is_reported(capsys):
    payload = {"jobs": [{"id": i, "title": f"Eng {i}",
                         "absolute_url": f"https://ex.test/{i}"}
                        for i in range(30)]}
    f = FakeFetcher(json.dumps(payload))
    out = greenhouse.GreenhouseSource(GH_CFG, f, max_results=25).discover()
    assert len(out) == 25
    assert "5 skipped" in capsys.readouterr().out


# --- Lever --------------------------------------------------------------

def test_lever_parses_a_posting():
    out = lever.parse_jobs(LEVER_PAYLOAD, "palantir", "Palantir")
    assert out[0].uid == "lever:palantir:abc-123"
    assert out[0].company == "Palantir"
    assert out[0].role == "Forward Deployed Engineer"
    assert out[0].url == "https://jobs.lever.co/palantir/abc-123"
    assert out[0].location == "Sydney"
    assert out[0].posted_at == "2026-07-25"        # ms epoch -> ISO date (UTC)


def test_lever_handles_missing_location_and_date():
    out = lever.parse_jobs(LEVER_PAYLOAD, "palantir", "Palantir")
    assert out[1].location is None
    assert out[1].posted_at is None


def test_lever_empty_payload():
    assert lever.parse_jobs([], "p", "P") == []


def test_lever_source_builds_the_postings_url():
    f = FakeFetcher(json.dumps(LEVER_PAYLOAD))
    lever.LeverSource(LEVER_CFG, f).discover()
    assert f.urls == ["https://api.lever.co/v0/postings/palantir?mode=json"]


def test_lever_fetch_error_propagates():
    src = lever.LeverSource(LEVER_CFG, FakeFetcher(raises=FetchError("nope")))
    with pytest.raises(FetchError):
        src.discover()
