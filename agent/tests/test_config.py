import os
from followup_agent.config import load_settings


def test_load_settings_reads_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setenv("OPENROUTER_MODEL", "m")
    monkeypatch.setenv("JWT_SIGNING_KEY", "secret")
    monkeypatch.setenv("FOLLOWUP_AGE_DAYS", "10")
    s = load_settings()
    assert s.database_url == "postgresql://x"
    assert s.followup_age_days == 10
    assert s.jwt_issuer == "JobApplicationTracker"  # default
    assert s.client_origin == "http://localhost:3000"  # default
