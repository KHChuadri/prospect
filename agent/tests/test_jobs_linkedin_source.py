import httpx
import pytest

from followup_agent.jobs.sources import JobPosting
from followup_agent.jobs.sources.linkedin import LinkedInRefused, LinkedInSource

CFG = {
    "name": "linkedin-frontend-syd",
    "type": "linkedin",
    "query": "frontend engineer",
    "location": "Sydney, New South Wales, Australia",
    "jobage": 14,
}

CARD = """
<div data-entity-urn="urn:li:jobPosting:{id}">
  <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/{id}"></a>
  <h3 class="base-search-card__title">Frontend Engineer</h3>
  <h4 class="base-search-card__subtitle">Canva</h4>
  <span class="job-search-card__location">Sydney, New South Wales, Australia</span>
  <time class="job-search-card__listdate" datetime="2026-08-04">3 days ago</time>
</div>
"""


class FakeClient:
    def __init__(self, body="", raises=None):
        self.body = body
        self.raises = raises
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        if self.raises:
            raise self.raises
        return self.body


def test_discover_returns_job_postings():
    c = FakeClient(CARD.format(id="4426311357"))
    postings = LinkedInSource(CFG, c).discover()
    assert postings == [JobPosting(
        uid="linkedin:4426311357",
        company="Canva",
        role="Frontend Engineer",
        url="https://www.linkedin.com/jobs/view/4426311357",
        location="Sydney, New South Wales, Australia",
        posted_at="2026-08-04")]


def test_uid_is_namespaced():
    c = FakeClient(CARD.format(id="999"))
    assert LinkedInSource(CFG, c).discover()[0].uid == "linkedin:999"


def test_config_drives_the_request_url():
    c = FakeClient("")
    LinkedInSource(CFG, c).discover()
    assert "keywords=frontend+engineer" in c.urls[0]
    assert "f_TPR=r1209600" in c.urls[0]


def test_cards_without_a_company_are_dropped():
    body = """
    <div data-entity-urn="urn:li:jobPosting:1">
      <h3 class="base-search-card__title">Ghost Role</h3>
    </div>"""
    assert LinkedInSource(CFG, FakeClient(body)).discover() == []


def test_empty_body_yields_nothing_and_does_not_warn(capsys):
    assert LinkedInSource(CFG, FakeClient("")).discover() == []
    assert "parse failure" not in capsys.readouterr().out


def test_non_trivial_body_yielding_zero_cards_is_a_parse_failure(capsys):
    # Markup changed. Without this the feed just goes quiet and nothing says why.
    body = "<html><body>" + ("<div class='new-markup'>x</div>" * 200) + "</body></html>"
    assert LinkedInSource(CFG, FakeClient(body)).discover() == []
    assert "parse failure" in capsys.readouterr().out


def test_refusal_propagates_for_crawl_to_isolate():
    src = LinkedInSource(CFG, FakeClient(raises=LinkedInRefused("cooling down")))
    with pytest.raises(LinkedInRefused):
        src.discover()


def test_results_are_capped_and_the_cap_is_reported(capsys):
    body = "".join(CARD.format(id=str(i)) for i in range(1000, 1030))
    postings = LinkedInSource(CFG, FakeClient(body), max_results=25).discover()
    assert len(postings) == 25
    assert "5 skipped" in capsys.readouterr().out


def test_transport_error_propagates_uncaught():
    # Task 5's review flagged that LinkedInClient.get does not wrap transport
    # failures — an httpx.ConnectError escapes raw, bypassing LinkedInRefused
    # entirely. discover() must not assume LinkedInRefused is the only thing
    # that can come out of get(); run_jobs_batch already isolates whatever
    # a source raises, so the right behaviour here is to let it propagate.
    src = LinkedInSource(CFG, FakeClient(raises=httpx.ConnectError("boom")))
    with pytest.raises(httpx.ConnectError):
        src.discover()
