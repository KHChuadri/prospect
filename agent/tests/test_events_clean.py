from pathlib import Path
import pytest
from followup_agent.events import clean

FIXTURE = Path(__file__).parent / "fixtures" / "unsw-events.html"


@pytest.fixture(scope="module")
def unsw_html():
    if not FIXTURE.exists():
        pytest.skip("fixture not captured — see Task 3 Step 2")
    return FIXTURE.read_text(encoding="utf-8", errors="replace")


def test_strips_script_and_style_content():
    html = "<html><head><style>.a{color:red}</style>" \
           "<script>var x=1;</script></head><body><p>Real text</p></body></html>"
    text = clean.html_to_text(html)
    assert "Real text" in text
    assert "color:red" not in text
    assert "var x" not in text


def test_strips_nav_header_and_footer():
    html = ("<body><nav>Home About Contact</nav><header>Logo</header>"
            "<main><p>Event description</p></main>"
            "<footer>Copyright 2026</footer></body>")
    text = clean.html_to_text(html)
    assert "Event description" in text
    assert "Home About Contact" not in text
    assert "Copyright 2026" not in text


def test_collapses_whitespace():
    text = clean.html_to_text("<p>a</p>\n\n\n   <p>b</p>")
    assert "\n\n\n" not in text
    assert "a" in text and "b" in text


def test_handles_empty_and_malformed_html():
    assert clean.html_to_text("") == ""
    assert "hi" in clean.html_to_text("<p>hi</p><div><span>")


def test_real_page_shrinks_substantially(unsw_html):
    # 110KB of markup should reduce to a few KB of readable text — this is
    # what keeps the LLM call cheap.
    text = clean.html_to_text(unsw_html)
    assert len(text) < len(unsw_html) / 5
    assert len(text) > 200


def test_discovers_event_links_from_the_real_page(unsw_html):
    links = clean.discover_links(unsw_html, "https://www.events.unsw.edu.au/", "/event/")
    assert len(links) >= 10
    assert all(l.startswith("https://www.events.unsw.edu.au/event/") for l in links)


def test_discovered_links_are_deduplicated(unsw_html):
    links = clean.discover_links(unsw_html, "https://www.events.unsw.edu.au/", "/event/")
    assert len(links) == len(set(links))


def test_non_matching_links_are_excluded(unsw_html):
    links = clean.discover_links(unsw_html, "https://www.events.unsw.edu.au/", "/event/")
    assert not any("/about" in l or "/study" in l for l in links)


def test_relative_links_become_absolute():
    html = '<a href="/event/x">X</a><a href="event/y">Y</a>'
    links = clean.discover_links(html, "https://ex.test/events", "/event/")
    assert "https://ex.test/event/x" in links


def test_offsite_links_are_excluded():
    # Only the configured host is crawled — a link out to another domain is
    # a site we never vetted and must not be fetched.
    html = '<a href="https://evil.test/event/x">X</a><a href="/event/y">Y</a>'
    links = clean.discover_links(html, "https://ex.test/events", "/event/")
    assert links == ["https://ex.test/event/y"]


def test_query_strings_and_fragments_are_stripped():
    html = '<a href="/event/x?utm=a#top">X</a><a href="/event/x">X again</a>'
    links = clean.discover_links(html, "https://ex.test/events", "/event/")
    assert links == ["https://ex.test/event/x"]
