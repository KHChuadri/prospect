import pytest
from followup_agent.config import load_settings


@pytest.fixture(autouse=True)
def base_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x/y")
    monkeypatch.setenv("JWT_SIGNING_KEY", "k" * 32)


def test_event_settings_have_sensible_defaults(monkeypatch):
    for key in ("EVENTS_LOCATION", "EVENTS_POLL_HOURS", "EVENTBRITE_TOKEN",
                "EVENTS_USER_AGENT", "EVENTS_SOURCES_PATH"):
        monkeypatch.delenv(key, raising=False)
    s = load_settings()
    assert s.events_location == "Sydney"
    assert s.events_poll_hours == 12
    assert s.eventbrite_token == ""
    assert "Prospect-EventCrawler" in s.events_user_agent
    assert s.events_sources_path.endswith("events_sources.yaml")


def test_event_settings_read_from_the_environment(monkeypatch):
    monkeypatch.setenv("EVENTS_LOCATION", "Melbourne")
    monkeypatch.setenv("EVENTS_POLL_HOURS", "6")
    monkeypatch.setenv("EVENTBRITE_TOKEN", "tok")
    s = load_settings()
    assert s.events_location == "Melbourne"
    assert s.events_poll_hours == 6
    assert s.eventbrite_token == "tok"


def test_user_agent_carries_a_contact_url(monkeypatch):
    # An anonymous or spoofed UA is what gets a crawler blanket-blocked.
    monkeypatch.delenv("EVENTS_USER_AGENT", raising=False)
    assert "http" in load_settings().events_user_agent
