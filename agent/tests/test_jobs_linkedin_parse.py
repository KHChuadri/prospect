from urllib.parse import parse_qs, urlparse

from followup_agent.jobs.sources import linkedin

# Trimmed to the elements the parser targets. Two well-formed cards plus one
# malformed card, to prove one bad card cannot break the rest.
CARDS = """
<li>
  <div class="base-card" data-entity-urn="urn:li:jobPosting:4426311357">
    <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/senior-frontend-engineer-at-canva-4426311357?refId=abc"></a>
    <h3 class="base-search-card__title">Senior Frontend Engineer</h3>
    <h4 class="base-search-card__subtitle">
      <a href="https://www.linkedin.com/company/canva?trk=x">Canva &amp; Co</a>
    </h4>
    <span class="job-search-card__location">Sydney, New South Wales, Australia</span>
    <time class="job-search-card__listdate" datetime="2026-08-04">3 days ago</time>
  </div>
</li>
<li>
  <div class="base-card" data-entity-urn="urn:li:jobPosting:4426311358">
    <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/ai-engineer-4426311358"></a>
    <h3 class="base-search-card__title">AI Engineer &#8212; Platform</h3>
    <h4 class="base-search-card__subtitle">Atlassian</h4>
    <span class="job-search-card__location">Remote</span>
  </div>
</li>
<li>
  <div class="base-card" data-entity-urn="urn:li:jobPosting:notanumber">
    <h3 class="base-search-card__title">Broken</h3>
  </div>
</li>
"""


def test_parses_every_well_formed_card():
    cards = linkedin.parse_job_cards(CARDS)
    assert len(cards) == 2


def test_extracts_all_fields():
    c = linkedin.parse_job_cards(CARDS)[0]
    assert c["id"] == "4426311357"
    assert c["title"] == "Senior Frontend Engineer"
    assert c["company"] == "Canva & Co"          # entity decoded
    assert c["location"] == "Sydney, New South Wales, Australia"
    assert c["date"] == "2026-08-04"
    assert "?" not in c["url"]                    # tracking params stripped


def test_decodes_numeric_entities():
    c = linkedin.parse_job_cards(CARDS)[1]
    assert c["title"] == "AI Engineer — Platform"


def test_company_without_link_still_parses():
    c = linkedin.parse_job_cards(CARDS)[1]
    assert c["company"] == "Atlassian"


def test_missing_date_is_none():
    assert linkedin.parse_job_cards(CARDS)[1]["date"] is None


def test_malformed_card_is_skipped_not_fatal():
    assert "notanumber" not in {c["id"] for c in linkedin.parse_job_cards(CARDS)}


def test_empty_html_yields_nothing():
    assert linkedin.parse_job_cards("") == []


def test_jobage_to_tpr():
    assert linkedin.jobage_to_tpr(14) == "r1209600"
    assert linkedin.jobage_to_tpr(0) is None
    assert linkedin.jobage_to_tpr(-1) is None


def test_work_type_flag():
    assert linkedin.work_type_flag("remote") == "2"
    assert linkedin.work_type_flag("hybrid") == "3"
    assert linkedin.work_type_flag("onsite") == "1"
    assert linkedin.work_type_flag("on-site") == "1"
    assert linkedin.work_type_flag(None) is None
    assert linkedin.work_type_flag("nonsense") is None


def test_build_search_url_includes_every_filter():
    url = linkedin.build_search_url(
        query="frontend engineer", location="Sydney, New South Wales, Australia",
        jobage=14, remote="hybrid", page=2)
    q = parse_qs(urlparse(url).query)
    assert q["keywords"] == ["frontend engineer"]
    assert q["location"] == ["Sydney, New South Wales, Australia"]
    assert q["f_TPR"] == ["r1209600"]
    assert q["f_WT"] == ["3"]
    assert q["start"] == ["10"]              # page 2, 10 results per page


def test_build_search_url_omits_absent_filters():
    url = linkedin.build_search_url(query=None, location="Remote")
    q = parse_qs(urlparse(url).query)
    assert "keywords" not in q
    assert "f_TPR" not in q
    assert "f_WT" not in q
    assert q["start"] == ["0"]
