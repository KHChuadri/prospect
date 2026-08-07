import pytest

from followup_agent import db
from followup_agent.jobs import crawl
from followup_agent.jobs.sources import JobPosting


class FakeSource:
    def __init__(self, name, postings, raises=None):
        self.name = name
        self._postings = postings
        self._raises = raises

    def discover(self):
        if self._raises:
            raise self._raises
        return self._postings


def _jp(uid, company="Canva", role="Frontend Engineer", **kw):
    return JobPosting(uid=uid, company=company, role=role,
                      url=f"https://ex.test/{uid}", **kw)


def _setup(monkeypatch, *, seen_ids=None, job_keys=None):
    monkeypatch.setattr(db, "existing_source_message_ids",
                        lambda conn: set(seen_ids or set()))
    monkeypatch.setattr(db, "existing_job_keys",
                        lambda conn, uid: set(job_keys or set()))
    created = []

    def fake_create(conn, **kw):
        created.append(kw)
        return len(created)

    monkeypatch.setattr(db, "create_recommendation", fake_create)
    return created


def test_stores_a_new_posting(monkeypatch):
    created = _setup(monkeypatch)
    src = FakeSource("linkedin-syd", [_jp("linkedin:1", location="Sydney NSW",
                                          posted_at="2026-08-04")])
    ids = crawl.run_jobs_batch(None, sources=[src], user_id=1)
    assert ids == [1]
    assert created[0]["source_message_id"] == "linkedin:1"
    assert created[0]["company"] == "Canva"
    assert created[0]["source_sender"] == "linkedin-syd"
    assert created[0]["url"] == "https://ex.test/linkedin:1"


def test_raw_snippet_carries_location_and_date(monkeypatch):
    created = _setup(monkeypatch)
    src = FakeSource("linkedin-syd", [_jp("linkedin:1", location="Sydney NSW",
                                          posted_at="2026-08-04")])
    crawl.run_jobs_batch(None, sources=[src], user_id=1)
    assert created[0]["raw_snippet"] == "Sydney NSW · posted 2026-08-04"


def test_raw_snippet_omits_missing_parts(monkeypatch):
    created = _setup(monkeypatch)
    src = FakeSource("gh", [_jp("greenhouse:s:1")])
    crawl.run_jobs_batch(None, sources=[src], user_id=1)
    assert created[0]["raw_snippet"] == ""


def test_gate1_skips_already_stored_uid(monkeypatch):
    created = _setup(monkeypatch, seen_ids={"linkedin:1"})
    src = FakeSource("linkedin-syd", [_jp("linkedin:1")])
    assert crawl.run_jobs_batch(None, sources=[src], user_id=1) == []
    assert created == []


def test_gate2_skips_empty_company(monkeypatch):
    created = _setup(monkeypatch)
    src = FakeSource("s", [_jp("linkedin:1", company="   ")])
    assert crawl.run_jobs_batch(None, sources=[src], user_id=1) == []
    assert created == []


def test_gate2_skips_empty_role(monkeypatch):
    created = _setup(monkeypatch)
    src = FakeSource("s", [_jp("linkedin:1", role="")])
    assert crawl.run_jobs_batch(None, sources=[src], user_id=1) == []
    assert created == []


def test_gate3_skips_already_tracked_company_role(monkeypatch):
    created = _setup(monkeypatch, job_keys={("canva", "frontend engineer")})
    src = FakeSource("s", [_jp("linkedin:1")])
    assert crawl.run_jobs_batch(None, sources=[src], user_id=1) == []
    assert created == []


def test_gate4_skips_cross_source_duplicate(monkeypatch):
    created = _setup(monkeypatch)
    a = FakeSource("linkedin-syd", [_jp("linkedin:1")])
    b = FakeSource("greenhouse-canva", [_jp("greenhouse:canva:9")])
    ids = crawl.run_jobs_batch(None, sources=[a, b], user_id=1)
    assert ids == [1]                       # same company+role, second dropped
    assert len(created) == 1


def test_failing_source_does_not_stop_the_others(monkeypatch):
    created = _setup(monkeypatch)
    bad = FakeSource("dead", [], raises=RuntimeError("boom"))
    good = FakeSource("alive", [_jp("linkedin:2")])
    ids = crawl.run_jobs_batch(None, sources=[bad, good], user_id=1)
    assert ids == [1]
    assert len(created) == 1


def test_insert_race_returning_none_is_skipped(monkeypatch):
    _setup(monkeypatch)
    monkeypatch.setattr(db, "create_recommendation", lambda conn, **kw: None)
    src = FakeSource("s", [_jp("linkedin:1")])
    assert crawl.run_jobs_batch(None, sources=[src], user_id=1) == []


def test_same_uid_twice_in_one_run_stores_once(monkeypatch):
    created = _setup(monkeypatch)
    src = FakeSource("s", [_jp("linkedin:1"), _jp("linkedin:1")])
    assert crawl.run_jobs_batch(None, sources=[src], user_id=1) == [1]
    assert len(created) == 1


def test_malformed_posting_does_not_stop_its_source(monkeypatch):
    created = _setup(monkeypatch)
    bad = JobPosting(uid="linkedin:bad", company=123, role="Frontend Engineer",
                      url="https://ex.test/bad")
    good = _jp("linkedin:2")
    src = FakeSource("linkedin-syd", [bad, good])
    ids = crawl.run_jobs_batch(None, sources=[src], user_id=1)
    assert ids == [1]
    assert len(created) == 1
    assert created[0]["source_message_id"] == "linkedin:2"


def test_malformed_posting_does_not_stop_the_run(monkeypatch):
    created = _setup(monkeypatch)
    bad = JobPosting(uid="linkedin:bad", company=123, role="Frontend Engineer",
                      url="https://ex.test/bad")
    a = FakeSource("linkedin-syd", [bad])
    b = FakeSource("greenhouse-canva", [_jp("greenhouse:canva:9")])
    ids = crawl.run_jobs_batch(None, sources=[a, b], user_id=1)
    assert ids == [1]
    assert len(created) == 1
    assert created[0]["source_message_id"] == "greenhouse:canva:9"


def test_malformed_posting_failure_is_reported(monkeypatch, capsys):
    _setup(monkeypatch)
    bad = JobPosting(uid="linkedin:bad", company=123, role="Frontend Engineer",
                      url="https://ex.test/bad")
    src = FakeSource("linkedin-syd", [bad])
    crawl.run_jobs_batch(None, sources=[src], user_id=1)
    out = capsys.readouterr().out
    assert "linkedin-syd" in out
    assert "linkedin:bad" in out


def test_db_error_on_create_propagates(monkeypatch):
    _setup(monkeypatch)

    def raising_create(conn, **kw):
        raise RuntimeError("db exploded")

    monkeypatch.setattr(db, "create_recommendation", raising_create)
    src = FakeSource("s", [_jp("linkedin:1")])
    with pytest.raises(RuntimeError, match="db exploded"):
        crawl.run_jobs_batch(None, sources=[src], user_id=1)
