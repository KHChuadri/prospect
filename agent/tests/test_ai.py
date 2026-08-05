import datetime as dt
import pytest
import jwt
from fastapi import FastAPI
from fastapi.testclient import TestClient
from followup_agent import ai, db, llm, pdf, storage
from followup_agent.config import Settings
from followup_agent.models import Extraction, MatchResult, ResumeProfile

NAMEID = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier"


def settings():
    return Settings(database_url="", openrouter_api_key="", openrouter_model="",
                    jwt_signing_key="super-secret-key-at-least-32-chars!!",
                    jwt_issuer="JobApplicationTracker",
                    jwt_audience="JobApplicationTrackerUsers",
                    smtp_host="", smtp_port=587, smtp_user="", smtp_password="",
                    smtp_from="", followup_age_days=7,
                    client_origin="http://localhost:3000")


def token(s, uid=42):
    return jwt.encode(
        {NAMEID: str(uid), "iss": s.jwt_issuer, "aud": s.jwt_audience,
         "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5)},
        s.jwt_signing_key, algorithm="HS256")


class FakeConn:
    def commit(self): pass
    def close(self): pass


def make_client():
    s = settings()
    app = FastAPI()
    app.include_router(ai.create_ai_router(s, conn_factory=lambda: FakeConn()))
    return TestClient(app), s


def test_extract_requires_auth():
    c, s = make_client()
    assert c.post("/ai/extract", json={"text": "x"}).status_code == 401


def test_extract_returns_fields(monkeypatch):
    monkeypatch.setattr(llm, "extract",
        lambda text, settings: Extraction(company="Acme", role="Eng", ok=True))
    c, s = make_client()
    r = c.post("/ai/extract", json={"text": "Acme hiring"},
               headers={"Authorization": f"Bearer {token(s)}"})
    assert r.status_code == 200 and r.json()["company"] == "Acme"


def test_extract_llm_error_returns_502(monkeypatch):
    def boom(text, settings): raise RuntimeError("llm down")
    monkeypatch.setattr(llm, "extract", boom)
    c, s = make_client()
    r = c.post("/ai/extract", json={"text": "x"},
               headers={"Authorization": f"Bearer {token(s)}"})
    assert r.status_code == 502


def test_match_needs_resume(monkeypatch):
    monkeypatch.setattr(db, "get_resume", lambda conn, uid: None)
    c, s = make_client()
    r = c.post("/ai/match/5", headers={"Authorization": f"Bearer {token(s)}"})
    assert r.status_code == 409


def test_match_needs_jd(monkeypatch):
    monkeypatch.setattr(db, "get_resume", lambda conn, uid: "resume")
    monkeypatch.setattr(db, "get_app_ai", lambda conn, app_id, uid: None)
    c, s = make_client()
    r = c.post("/ai/match/5", headers={"Authorization": f"Bearer {token(s)}"})
    assert r.status_code == 409


def test_match_computes_and_caches(monkeypatch):
    monkeypatch.setattr(db, "get_resume", lambda conn, uid: "resume")
    monkeypatch.setattr(db, "get_app_ai",
        lambda conn, app_id, uid: {"jd_text": "jd", "match_json": None,
                                   "optimized_resume": None})
    saved = {}
    monkeypatch.setattr(db, "save_match",
        lambda conn, app_id, uid, mj: saved.update(mj))
    monkeypatch.setattr(llm, "match",
        lambda r, j, settings: MatchResult(score=70, missing=["docker"],
                                           matched=["python"], suggestions=["x"]))
    c, s = make_client()
    r = c.post("/ai/match/5", headers={"Authorization": f"Bearer {token(s)}"})
    assert r.status_code == 200 and r.json()["score"] == 70
    assert saved["score"] == 70                      # cached


def test_match_returns_cache_without_calling_llm(monkeypatch):
    monkeypatch.setattr(db, "get_resume", lambda conn, uid: "resume")
    monkeypatch.setattr(db, "get_app_ai",
        lambda conn, app_id, uid: {"jd_text": "jd",
                                   "match_json": {"score": 88},
                                   "optimized_resume": None})
    def boom(*a, **k): raise AssertionError("llm.match must not be called")
    monkeypatch.setattr(llm, "match", boom)
    c, s = make_client()
    r = c.post("/ai/match/5", headers={"Authorization": f"Bearer {token(s)}"})
    assert r.status_code == 200 and r.json()["score"] == 88


# ---------------------------------------------------------------- upload-url

def _configure_storage(monkeypatch, configured=True):
    monkeypatch.setattr(storage, "is_configured", lambda s: configured)


def test_upload_url_requires_auth():
    c, s = make_client()
    r = c.post("/ai/resume/upload-url",
               json={"filename": "cv.pdf", "content_type": "application/pdf", "size": 1000})
    assert r.status_code == 401


def test_upload_url_rejects_non_pdf(monkeypatch):
    _configure_storage(monkeypatch)
    c, s = make_client()
    r = c.post("/ai/resume/upload-url",
               json={"filename": "cv.docx", "size": 1000,
                     "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
               headers={"Authorization": f"Bearer {token(s)}"})
    assert r.status_code == 400


def test_upload_url_rejects_oversized_file(monkeypatch):
    _configure_storage(monkeypatch)
    c, s = make_client()
    r = c.post("/ai/resume/upload-url",
               json={"filename": "cv.pdf", "content_type": "application/pdf",
                     "size": 6 * 1024 * 1024},
               headers={"Authorization": f"Bearer {token(s)}"})
    assert r.status_code == 400


def test_upload_url_returns_503_when_storage_unconfigured(monkeypatch):
    _configure_storage(monkeypatch, configured=False)
    c, s = make_client()
    r = c.post("/ai/resume/upload-url",
               json={"filename": "cv.pdf", "content_type": "application/pdf", "size": 1000},
               headers={"Authorization": f"Bearer {token(s)}"})
    assert r.status_code == 503


def test_upload_url_scopes_the_key_to_the_caller(monkeypatch):
    _configure_storage(monkeypatch)
    monkeypatch.setattr(storage, "presign_put",
                        lambda s, key, ct, **kw: f"https://bucket.example/{key}?sig=x")
    c, s = make_client()
    r = c.post("/ai/resume/upload-url",
               json={"filename": "cv.pdf", "content_type": "application/pdf", "size": 1000},
               headers={"Authorization": f"Bearer {token(s, uid=42)}"})
    assert r.status_code == 200
    body = r.json()
    assert body["key"].startswith("resumes/42/")
    assert body["key"].endswith(".pdf")
    assert body["key"] in body["url"]


# ------------------------------------------------------------------- ingest

RESUME_TEXT = "Jane Chen\nSenior Engineer at Acme Corp\nPython, Postgres"


def _ingest_happy_path(monkeypatch, saved):
    _configure_storage(monkeypatch)
    monkeypatch.setattr(storage, "get_object", lambda s, key: b"%PDF-1.4 fake")
    monkeypatch.setattr(pdf, "extract_text", lambda data: RESUME_TEXT)
    monkeypatch.setattr(llm, "parse_resume",
                        lambda text, s: ResumeProfile(name="Jane Chen",
                                                      skills=["Python"]))
    monkeypatch.setattr(db, "get_resume_row", lambda conn, uid: None)
    monkeypatch.setattr(db, "upsert_resume_file",
                        lambda conn, uid, **kw: saved.update(kw))


def test_ingest_stores_text_and_profile(monkeypatch):
    saved = {}
    _ingest_happy_path(monkeypatch, saved)
    c, s = make_client()
    r = c.post("/ai/resume/ingest",
               json={"key": "resumes/42/abc.pdf", "filename": "cv.pdf"},
               headers={"Authorization": f"Bearer {token(s, uid=42)}"})
    assert r.status_code == 200
    body = r.json()
    assert body["text"] == RESUME_TEXT
    assert body["profile"]["name"] == "Jane Chen"
    assert body["warning"] is None
    assert saved["text"] == RESUME_TEXT
    assert saved["file_key"] == "resumes/42/abc.pdf"
    assert saved["file_name"] == "cv.pdf"
    assert saved["parsed"]["skills"] == ["Python"]


def test_ingest_rejects_another_users_key(monkeypatch):
    saved = {}
    _ingest_happy_path(monkeypatch, saved)
    c, s = make_client()
    r = c.post("/ai/resume/ingest",
               json={"key": "resumes/99/abc.pdf", "filename": "cv.pdf"},
               headers={"Authorization": f"Bearer {token(s, uid=42)}"})
    assert r.status_code == 403
    assert saved == {}


def test_ingest_returns_404_for_a_missing_object(monkeypatch):
    _configure_storage(monkeypatch)

    def missing(s, key): raise storage.ObjectNotFound(key)
    monkeypatch.setattr(storage, "get_object", missing)
    c, s = make_client()
    r = c.post("/ai/resume/ingest",
               json={"key": "resumes/42/gone.pdf", "filename": "cv.pdf"},
               headers={"Authorization": f"Bearer {token(s, uid=42)}"})
    assert r.status_code == 404


@pytest.mark.parametrize("error", [
    pdf.EncryptedPdfError, pdf.NoTextLayerError, pdf.UnreadablePdfError,
])
def test_ingest_returns_422_for_unreadable_pdfs(monkeypatch, error):
    _configure_storage(monkeypatch)
    monkeypatch.setattr(storage, "get_object", lambda s, key: b"bytes")

    def boom(data): raise error("nope")
    monkeypatch.setattr(pdf, "extract_text", boom)
    c, s = make_client()
    r = c.post("/ai/resume/ingest",
               json={"key": "resumes/42/a.pdf", "filename": "cv.pdf"},
               headers={"Authorization": f"Bearer {token(s, uid=42)}"})
    assert r.status_code == 422
    assert r.json()["detail"]


def test_ingest_saves_text_even_when_the_llm_fails(monkeypatch):
    saved = {}
    _ingest_happy_path(monkeypatch, saved)

    def boom(text, s): raise RuntimeError("llm down")
    monkeypatch.setattr(llm, "parse_resume", boom)
    c, s = make_client()
    r = c.post("/ai/resume/ingest",
               json={"key": "resumes/42/a.pdf", "filename": "cv.pdf"},
               headers={"Authorization": f"Bearer {token(s, uid=42)}"})
    assert r.status_code == 200
    assert r.json()["text"] == RESUME_TEXT
    assert r.json()["profile"] is None
    assert r.json()["warning"]
    assert saved["parsed"] is None      # still persisted


def test_ingest_deletes_the_previously_stored_file(monkeypatch):
    saved = {}
    _ingest_happy_path(monkeypatch, saved)
    monkeypatch.setattr(db, "get_resume_row",
                        lambda conn, uid: {"file_key": "resumes/42/old.pdf"})
    deleted = []
    monkeypatch.setattr(storage, "delete_object",
                        lambda s, key: deleted.append(key))
    c, s = make_client()
    c.post("/ai/resume/ingest",
           json={"key": "resumes/42/new.pdf", "filename": "cv.pdf"},
           headers={"Authorization": f"Bearer {token(s, uid=42)}"})
    assert deleted == ["resumes/42/old.pdf"]


# --------------------------------------------------------------- get résumé

def test_get_resume_returns_profile_and_filename(monkeypatch):
    monkeypatch.setattr(db, "get_resume_row", lambda conn, uid: {
        "text": RESUME_TEXT, "parsed_json": {"name": "Jane Chen"},
        "file_key": "resumes/42/a.pdf", "file_name": "cv.pdf",
        "updated_at": None,
    })
    c, s = make_client()
    r = c.get("/ai/resume", headers={"Authorization": f"Bearer {token(s)}"})
    assert r.status_code == 200
    assert r.json() == {"text": RESUME_TEXT, "profile": {"name": "Jane Chen"},
                        "file_name": "cv.pdf", "updated_at": None}


def test_get_resume_when_nothing_stored(monkeypatch):
    monkeypatch.setattr(db, "get_resume_row", lambda conn, uid: None)
    c, s = make_client()
    r = c.get("/ai/resume", headers={"Authorization": f"Bearer {token(s)}"})
    assert r.json() == {"text": "", "profile": None,
                        "file_name": None, "updated_at": None}


def test_pasting_text_clears_the_stored_file(monkeypatch):
    monkeypatch.setattr(db, "get_resume_row",
                        lambda conn, uid: {"file_key": "resumes/42/old.pdf"})
    monkeypatch.setattr(db, "upsert_resume", lambda conn, uid, text: None)
    deleted = []
    monkeypatch.setattr(storage, "is_configured", lambda s: True)
    monkeypatch.setattr(storage, "delete_object",
                        lambda s, key: deleted.append(key))
    c, s = make_client()
    r = c.put("/ai/resume", json={"text": "pasted over the top"},
              headers={"Authorization": f"Bearer {token(s, uid=42)}"})
    assert r.status_code == 200
    assert deleted == ["resumes/42/old.pdf"]
