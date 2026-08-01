import pytest
import httpx
from followup_agent.events.fetch import Fetcher, FetchError

UA = "Prospect-EventCrawler/1.0 (+https://example.test)"
ROBOTS_OPEN = "User-agent: *\nDisallow: /admin/\n"
ROBOTS_CLOSED = "User-agent: *\nDisallow: /\n"


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def _serve(pages):
    def handler(request):
        key = str(request.url)
        if key not in pages:
            return httpx.Response(404)
        status, body = pages[key]
        return httpx.Response(status, text=body)
    return handler


def test_fetches_a_permitted_page():
    pages = {
        "https://ex.test/robots.txt": (200, ROBOTS_OPEN),
        "https://ex.test/event/x": (200, "<p>hello</p>"),
    }
    f = Fetcher(UA, sleep_fn=lambda s: None, client=_client(_serve(pages)))
    assert f.get("https://ex.test/event/x") == "<p>hello</p>"


def test_robots_disallow_blocks_the_fetch():
    pages = {"https://ex.test/robots.txt": (200, ROBOTS_CLOSED)}
    f = Fetcher(UA, sleep_fn=lambda s: None, client=_client(_serve(pages)))
    assert f.allowed("https://ex.test/event/x") is False


def test_missing_robots_txt_is_treated_as_permitted():
    pages = {"https://ex.test/event/x": (200, "ok")}
    f = Fetcher(UA, sleep_fn=lambda s: None, client=_client(_serve(pages)))
    assert f.allowed("https://ex.test/event/x") is True


def test_robots_is_fetched_once_per_host():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=ROBOTS_OPEN)
        return httpx.Response(200, text="ok")

    f = Fetcher(UA, sleep_fn=lambda s: None, client=_client(handler))
    f.get("https://ex.test/event/a")
    f.get("https://ex.test/event/b")
    assert calls.count("https://ex.test/robots.txt") == 1


def test_sends_the_configured_user_agent():
    seen = {}

    def handler(request):
        seen["ua"] = request.headers.get("user-agent")
        return httpx.Response(200, text="ok")

    f = Fetcher(UA, sleep_fn=lambda s: None, client=_client(handler))
    f.get("https://ex.test/event/x")
    assert seen["ua"] == UA


def test_sleeps_between_requests_to_the_same_host():
    slept = []
    pages = {
        "https://ex.test/robots.txt": (200, ROBOTS_OPEN),
        "https://ex.test/event/a": (200, "a"),
        "https://ex.test/event/b": (200, "b"),
    }
    f = Fetcher(UA, delay_seconds=2.0, sleep_fn=slept.append,
                client=_client(_serve(pages)))
    f.get("https://ex.test/event/a")
    f.get("https://ex.test/event/b")
    assert any(s > 0 for s in slept)


def test_disallowed_url_raises_rather_than_silently_returning_empty():
    pages = {"https://ex.test/robots.txt": (200, ROBOTS_CLOSED)}
    f = Fetcher(UA, sleep_fn=lambda s: None, client=_client(_serve(pages)))
    with pytest.raises(FetchError, match="robots"):
        f.get("https://ex.test/event/x")


def test_http_error_raises_fetch_error():
    pages = {"https://ex.test/robots.txt": (200, ROBOTS_OPEN)}
    f = Fetcher(UA, sleep_fn=lambda s: None, client=_client(_serve(pages)))
    with pytest.raises(FetchError):
        f.get("https://ex.test/event/missing")


def test_network_failure_raises_fetch_error():
    def handler(request):
        raise httpx.ConnectError("refused")

    f = Fetcher(UA, sleep_fn=lambda s: None, client=_client(handler))
    with pytest.raises(FetchError):
        f.get("https://ex.test/event/x")
