import datetime as dt
import jwt
from fastapi import FastAPI
from fastapi.testclient import TestClient
from followup_agent import ai, db, llm
from followup_agent.config import Settings
from followup_agent.models import Extraction, MatchResult

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
