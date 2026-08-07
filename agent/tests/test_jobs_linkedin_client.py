import httpx
import pytest

from followup_agent.jobs.sources.linkedin import LinkedInClient, LinkedInRefused


def _client(handler, **kw):
    sleeps = []
    c = LinkedInClient(
        sleep_fn=sleeps.append,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        **kw)
    c.begin_run()
    return c, sleeps


URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?x=1"


def test_returns_body_on_200():
    c, _ = _client(lambda r: httpx.Response(200, text="<li>ok</li>"))
    assert c.get(URL) == "<li>ok</li>"


def test_sends_browser_headers():
    seen = {}

    def handler(request):
        seen.update(request.headers)
        return httpx.Response(200, text="ok")

    c, _ = _client(handler)
    c.get(URL)
    assert "Mozilla/5.0" in seen["user-agent"]
    # The guest endpoint is an XHR endpoint; without this it answers differently.
    assert seen["x-requested-with"] == "XMLHttpRequest"


def test_never_sends_cookies():
    seen = {}

    def handler(request):
        seen["cookie"] = request.headers.get("cookie")
        return httpx.Response(200, text="ok", headers={"set-cookie": "li_at=xyz"})

    c, _ = _client(handler)
    c.get(URL)
    c.get(URL)
    # The absence of an account is the entire safety property. A Set-Cookie the
    # client honours would start building one.
    assert seen["cookie"] is None


def test_404_returns_empty_string():
    c, _ = _client(lambda r: httpx.Response(404))
    assert c.get(URL) == ""


def test_retries_429_then_succeeds():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return (httpx.Response(429) if calls["n"] < 3
                else httpx.Response(200, text="ok"))

    c, sleeps = _client(handler)
    assert c.get(URL) == "ok"
    assert calls["n"] == 3
    assert len(sleeps) == 2


def test_backoff_doubles_and_caps():
    c, sleeps = _client(lambda r: httpx.Response(429))
    with pytest.raises(LinkedInRefused):
        c.get(URL)
    # 0.5, 1, 2, 4, 8, 8 — doubling, capped at 8s. Jitter adds up to 0.5s.
    assert [int(s) for s in sleeps] == [0, 1, 2, 4, 8, 8]


def test_exhausted_429_raises_and_opens_the_breaker():
    c, _ = _client(lambda r: httpx.Response(429))
    with pytest.raises(LinkedInRefused):
        c.get(URL)
    # Next run must be skipped entirely rather than retried.
    c.begin_run()
    with pytest.raises(LinkedInRefused, match="cooling down"):
        c.get(URL)


def test_cooldown_backs_off_then_clears_on_success():
    state = {"fail": True}

    def handler(request):
        return httpx.Response(429) if state["fail"] else httpx.Response(200, text="ok")

    c, _ = _client(handler)
    with pytest.raises(LinkedInRefused):
        c.get(URL)                       # opens breaker, cooldown = 1 run

    c.begin_run()                        # run 2: skipped, cooldown spent
    with pytest.raises(LinkedInRefused, match="cooling down"):
        c.get(URL)

    state["fail"] = False
    c.begin_run()                        # run 3: allowed through
    assert c.get(URL) == "ok"

    c.begin_run()                        # success cleared the breaker
    assert c.get(URL) == "ok"


def test_cooldown_grows_on_repeated_refusal():
    c, _ = _client(lambda r: httpx.Response(429))
    with pytest.raises(LinkedInRefused):
        c.get(URL)                       # cooldown = 1
    c.begin_run()
    with pytest.raises(LinkedInRefused, match="cooling down"):
        c.get(URL)                       # spends it
    c.begin_run()
    with pytest.raises(LinkedInRefused):
        c.get(URL)                       # refused again -> cooldown = 2
    c.begin_run()
    with pytest.raises(LinkedInRefused, match="cooling down"):
        c.get(URL)
    c.begin_run()
    with pytest.raises(LinkedInRefused, match="cooling down"):
        c.get(URL)


def test_request_budget_is_enforced_per_run():
    c, _ = _client(lambda r: httpx.Response(200, text="ok"), max_requests=2)
    c.get(URL)
    c.get(URL)
    with pytest.raises(LinkedInRefused, match="budget"):
        c.get(URL)


def test_begin_run_resets_the_budget():
    c, _ = _client(lambda r: httpx.Response(200, text="ok"), max_requests=1)
    c.get(URL)
    with pytest.raises(LinkedInRefused, match="budget"):
        c.get(URL)
    c.begin_run()
    assert c.get(URL) == "ok"


def test_requests_are_spaced_apart():
    c, sleeps = _client(lambda r: httpx.Response(200, text="ok"),
                        delay_seconds=2.0)
    c.get(URL)
    c.get(URL)
    # First request is free; the second waits its turn.
    assert len(sleeps) == 1
    assert 0 < sleeps[0] <= 2.0


def test_5xx_is_retried_like_429():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return (httpx.Response(503) if calls["n"] < 2
                else httpx.Response(200, text="ok"))

    c, _ = _client(handler)
    assert c.get(URL) == "ok"


def test_other_4xx_raises_without_retrying():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(403)

    c, _ = _client(handler)
    with pytest.raises(LinkedInRefused):
        c.get(URL)
    assert calls["n"] == 1
