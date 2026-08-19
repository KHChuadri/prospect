from followup_agent.config import load_settings

REQUIRED_ENV = {
    "DATABASE_URL": "postgresql://x/y",
    "JWT_SIGNING_KEY": "k" * 32,
}


def _load(monkeypatch, **overrides):
    for k, v in {**REQUIRED_ENV, **overrides}.items():
        monkeypatch.setenv(k, v)
    return load_settings()


def test_jobs_defaults(monkeypatch):
    for k in ("JOBS_POLL_HOURS", "JOBS_MAX_PER_SOURCE",
              "JOBS_MAX_REQUESTS_PER_RUN", "JOBS_USER_AGENT",
              "JOBS_SOURCES_PATH"):
        monkeypatch.delenv(k, raising=False)
    s = _load(monkeypatch)
    assert s.jobs_poll_hours == 12
    assert s.jobs_max_per_source == 25
    assert s.jobs_max_requests_per_run == 10
    assert s.jobs_sources_path.endswith("job_sources.yaml")
    assert "Prospect-JobCrawler" in s.jobs_user_agent


def test_jobs_overrides(monkeypatch):
    s = _load(monkeypatch, JOBS_POLL_HOURS="6", JOBS_MAX_REQUESTS_PER_RUN="3")
    assert s.jobs_poll_hours == 6
    assert s.jobs_max_requests_per_run == 3


def test_jobs_user_agent_is_distinct_from_events(monkeypatch):
    # An honest UA that misdescribes what it is doing is not an honest UA.
    s = _load(monkeypatch)
    assert s.jobs_user_agent != s.events_user_agent
