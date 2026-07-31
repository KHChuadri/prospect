from datetime import datetime, timezone
from followup_agent import recommend_batch, db
from followup_agent.models import ParsedEmail, RecommendationExtract

NOW = datetime(2026, 7, 7, tzinfo=timezone.utc)


def _email(mid, subject="Backend Engineer at Acme"):
    return ParsedEmail(message_id=mid, sender="jobs@acme.com",
                       subject=subject, body="body text")


def _setup(monkeypatch, *, seen=None, job_keys=None):
    monkeypatch.setattr(db, "get_sync_state", lambda conn, uid: None)
    monkeypatch.setattr(db, "existing_message_ids", lambda conn: set(seen or set()))
    monkeypatch.setattr(db, "existing_job_keys", lambda conn, uid: set(job_keys or set()))
    monkeypatch.setattr(db, "set_sync_state", lambda conn, uid, ts: None)
    created = []
    def fake_create(conn, **kw):
        created.append(kw)
        return len(created)
    monkeypatch.setattr(db, "create_recommendation", fake_create)
    return created


def test_creates_pending_for_new_job(monkeypatch):
    created = _setup(monkeypatch)
    gmail_fn = lambda since: [_email("m1")]
    extract_fn = lambda em: RecommendationExtract(
        is_job=True, company="Acme", role="Backend Engineer",
        location="Remote", url="https://x")
    ids = recommend_batch.run_reco_batch(
        conn=None, gmail_fn=gmail_fn, extract_fn=extract_fn, user_id=1, now=NOW)
    assert ids == [1]
    assert created[0]["company"] == "Acme"
    assert created[0]["source_message_id"] == "m1"


def test_skips_seen_message_id(monkeypatch):
    created = _setup(monkeypatch, seen={"m1"})
    gmail_fn = lambda since: [_email("m1")]
    extract_fn = lambda em: (_ for _ in ()).throw(AssertionError("should not extract"))
    ids = recommend_batch.run_reco_batch(
        conn=None, gmail_fn=gmail_fn, extract_fn=extract_fn, user_id=1, now=NOW)
    assert ids == [] and created == []


def _record_sync(monkeypatch):
    calls = []
    monkeypatch.setattr(db, "set_sync_state", lambda conn, uid, ts: calls.append(ts))
    return calls


def test_advances_sync_state_when_all_ok(monkeypatch):
    _setup(monkeypatch)
    calls = _record_sync(monkeypatch)   # override the no-op recorder
    gmail_fn = lambda since: [_email("m1")]
    extract_fn = lambda em: RecommendationExtract(is_job=True, company="Acme", role="Eng")
    recommend_batch.run_reco_batch(
        conn=None, gmail_fn=gmail_fn, extract_fn=extract_fn, user_id=1, now=NOW)
    assert calls == [NOW]


def test_does_not_advance_sync_state_on_extract_failure(monkeypatch):
    _setup(monkeypatch)
    calls = _record_sync(monkeypatch)
    gmail_fn = lambda since: [_email("m4"), _email("m5")]
    def extract_fn(em):
        if em.message_id == "m4":
            raise RuntimeError("LLM 429")
        return RecommendationExtract(is_job=True, company="Beta", role="PM")
    recommend_batch.run_reco_batch(
        conn=None, gmail_fn=gmail_fn, extract_fn=extract_fn, user_id=1, now=NOW)
    # a message failed extraction → cursor must NOT advance, so it retries next poll
    assert calls == []


def test_skips_existing_job_key(monkeypatch):
    created = _setup(monkeypatch, job_keys={("acme", "backend engineer")})
    gmail_fn = lambda since: [_email("m2")]
    extract_fn = lambda em: RecommendationExtract(
        is_job=True, company="Acme", role="Backend Engineer")
    ids = recommend_batch.run_reco_batch(
        conn=None, gmail_fn=gmail_fn, extract_fn=extract_fn, user_id=1, now=NOW)
    assert ids == [] and created == []


def test_skips_non_job(monkeypatch):
    _setup(monkeypatch)
    gmail_fn = lambda since: [_email("m3")]
    extract_fn = lambda em: RecommendationExtract(is_job=False)
    ids = recommend_batch.run_reco_batch(
        conn=None, gmail_fn=gmail_fn, extract_fn=extract_fn, user_id=1, now=NOW)
    assert ids == []


def test_one_extract_failure_does_not_abort_batch(monkeypatch):
    created = _setup(monkeypatch)
    gmail_fn = lambda since: [_email("m4"), _email("m5")]
    def extract_fn(em):
        if em.message_id == "m4":
            raise RuntimeError("LLM 429")
        return RecommendationExtract(is_job=True, company="Beta", role="PM")
    ids = recommend_batch.run_reco_batch(
        conn=None, gmail_fn=gmail_fn, extract_fn=extract_fn, user_id=1, now=NOW)
    assert ids == [1] and created[0]["company"] == "Beta"
