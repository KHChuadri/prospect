"""main.py's job-crawler wiring, which nothing else in CI exercises.

Every assertion here is a safety property that would otherwise fail silently:

  * reusing `_fetcher` for the job crawler would send the EventCrawler UA to
    Greenhouse and Lever — a UA that misdescribes what it is doing is not an
    honest UA, and honest UAs are what buys the robots.txt exception next door;
  * constructing a LinkedInClient per run would destroy the circuit breaker,
    whose cooldown lives on the instance — the crawler would go back to hitting
    a refused endpoint every 12 hours forever;
  * dropping `begin_run()` would leave the per-run request budget spent after
    the first run and never spend a cooldown;
  * moving `begin_run()` outside the try would leak the database connection on
    the run it raised, because the `finally: conn.close()` belongs to that try.

main.py opens a PostgresSaver and starts a scheduler at import, so it has to be
imported under patched module attributes and dropped from sys.modules after.
The patches go on the modules main imports FROM, before main is imported, so
its own `from x import y` picks up the fakes.
"""
import importlib
import sys
from unittest.mock import MagicMock

import pytest

MODULE = "followup_agent.main"


class _FakeConn:
    def __init__(self):
        self.closed = False
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class _FakeSaver:
    def setup(self):
        pass


class _FakeSaverCM:
    def __enter__(self):
        return _FakeSaver()

    def __exit__(self, *exc):
        return False


class _FakePostgresSaver:
    @staticmethod
    def from_conn_string(url):
        return _FakeSaverCM()


@pytest.fixture
def main_mod(monkeypatch):
    import apscheduler.schedulers.background as apsbg
    import langgraph.checkpoint.postgres as lgpg
    import psycopg

    from followup_agent import api, gmail, graph

    monkeypatch.setenv("DATABASE_URL", "postgresql://unused/unused")
    monkeypatch.setenv("JWT_SIGNING_KEY", "test-signing-key")
    monkeypatch.setenv("EVENTS_USER_AGENT", "Prospect-EventCrawler/test")
    monkeypatch.setenv("JOBS_USER_AGENT", "Prospect-JobCrawler/test")

    monkeypatch.setattr(lgpg, "PostgresSaver", _FakePostgresSaver)
    monkeypatch.setattr(apsbg, "BackgroundScheduler",
                        lambda *a, **k: MagicMock())
    monkeypatch.setattr(graph, "build_graph", lambda *a, **k: MagicMock())
    monkeypatch.setattr(api, "create_app", lambda *a, **k: MagicMock())
    monkeypatch.setattr(gmail, "make_gmail_fn", lambda settings: (lambda: []))

    conns = []

    def fake_connect(url):
        conns.append(_FakeConn())
        return conns[-1]

    monkeypatch.setattr(psycopg, "connect", fake_connect)

    sys.modules.pop(MODULE, None)
    try:
        m = importlib.import_module(MODULE)
        m.conns = conns          # handed to the test, not used by main
        yield m
    finally:
        # main is a module-level side-effect factory; leaving a mocked copy in
        # sys.modules would silently change what a later test imports.
        sys.modules.pop(MODULE, None)


def _spy_crawl(monkeypatch, m):
    """Record the sources kwarg of every run_jobs_batch call, run nothing."""
    seen = []

    def fake_run(conn, *, sources, user_id):
        seen.append(sources)
        return []

    monkeypatch.setattr(m.jobs_crawl, "run_jobs_batch", fake_run)

    built = []

    def fake_build(settings, fetcher, linkedin_client):
        built.append((fetcher, linkedin_client))
        return []

    monkeypatch.setattr(m, "build_job_sources", fake_build)
    return built


def test_jobs_fetcher_is_distinct_and_carries_the_jobs_user_agent(main_mod):
    assert main_mod._jobs_fetcher is not main_mod._fetcher
    assert main_mod._jobs_fetcher.user_agent == "Prospect-JobCrawler/test"
    # Not merely "not None": the whole point is that it differs from the events
    # UA, which a reuse-_fetcher regression would make equal.
    assert main_mod._jobs_fetcher.user_agent != main_mod._fetcher.user_agent


def test_jobs_job_passes_the_jobs_fetcher_not_the_events_one(monkeypatch, main_mod):
    built = _spy_crawl(monkeypatch, main_mod)
    main_mod._jobs_job()
    fetcher, _ = built[0]
    assert fetcher is main_mod._jobs_fetcher
    assert fetcher is not main_mod._fetcher


def test_linkedin_client_is_module_level_and_survives_between_runs(
        monkeypatch, main_mod):
    built = _spy_crawl(monkeypatch, main_mod)
    main_mod._jobs_job()
    main_mod._jobs_job()
    first, second = built[0][1], built[1][1]
    # A per-run client would be a fresh object here, and its cooldown — which
    # lives on the instance — would reset every run.
    assert first is second
    assert first is main_mod._linkedin_client


def test_begin_run_is_called_once_per_jobs_job(monkeypatch, main_mod):
    _spy_crawl(monkeypatch, main_mod)
    calls = []
    monkeypatch.setattr(main_mod._linkedin_client, "begin_run",
                        lambda: calls.append(1))
    main_mod._jobs_job()
    assert len(calls) == 1
    main_mod._jobs_job()
    assert len(calls) == 2


def test_begin_run_failing_still_closes_the_connection(monkeypatch, main_mod):
    _spy_crawl(monkeypatch, main_mod)

    def boom():
        raise RuntimeError("begin_run exploded")

    monkeypatch.setattr(main_mod._linkedin_client, "begin_run", boom)
    # begin_run() sits inside the try, so a failure is caught and logged and the
    # finally still runs. Outside it, the connection opened one line earlier
    # would leak on every failing run.
    main_mod._jobs_job()
    assert main_mod.conns[-1].closed is True
    assert main_mod.conns[-1].rollbacks == 1
