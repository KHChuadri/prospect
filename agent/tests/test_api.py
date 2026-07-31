import datetime as dt
import jwt
from fastapi.testclient import TestClient
from langgraph.types import Command
from followup_agent import api, db
from followup_agent.config import Settings

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


class FakeGraph:
    def __init__(self): self.resumes = []
    def invoke(self, command, cfg): self.resumes.append((command, cfg))


def client(monkeypatch, row):
    s = settings()
    fake_graph = FakeGraph()

    monkeypatch.setattr(db, "list_follow_ups", lambda conn, user_id, status: [row])
    monkeypatch.setattr(db, "get_follow_up",
                        lambda conn, fid, user_id, **kw: row if user_id == row["user_id"] else None)
    updates = []
    monkeypatch.setattr(db, "update_follow_up",
                        lambda conn, fid, **kw: updates.append(kw))

    class FakeConn:
        def commit(self): pass
        def close(self): pass
    app = api.create_app(s, conn_factory=lambda: FakeConn(), graph=fake_graph)
    return TestClient(app), s, fake_graph, updates


ROW = {"id": 1, "app_id": 5, "user_id": 42, "thread_id": "t-1",
       "status": "pending", "draft_subject": "Hi", "draft_body": "Body",
       "recipient_email": None, "reason": "stale"}


def test_list_requires_auth(monkeypatch):
    c, *_ = client(monkeypatch, ROW)
    assert c.get("/follow-ups?status=pending").status_code == 401


def test_list_returns_rows(monkeypatch):
    c, s, *_ = client(monkeypatch, ROW)
    r = c.get("/follow-ups?status=pending",
              headers={"Authorization": f"Bearer {token(s)}"})
    assert r.status_code == 200
    assert r.json()[0]["id"] == 1


def test_approve_resumes_graph_and_marks_sent(monkeypatch):
    c, s, g, updates = client(monkeypatch, ROW)
    r = c.post("/follow-ups/1/approve",
               headers={"Authorization": f"Bearer {token(s)}"},
               json={"recipient_email": "r@x.com"})
    assert r.status_code == 200
    assert isinstance(g.resumes[0][0], Command)          # resumed with Command
    assert any(u.get("status") == "sent" for u in updates)


def test_reject_marks_rejected(monkeypatch):
    c, s, g, updates = client(monkeypatch, ROW)
    r = c.post("/follow-ups/1/reject",
               headers={"Authorization": f"Bearer {token(s)}"})
    assert r.status_code == 200
    assert any(u.get("status") == "rejected" for u in updates)


def test_approve_rejects_non_pending(monkeypatch):
    sent_row = {**ROW, "status": "sent"}
    c, s, g, updates = client(monkeypatch, sent_row)
    r = c.post("/follow-ups/1/approve",
               headers={"Authorization": f"Bearer {token(s)}"},
               json={"recipient_email": "r@x.com"})
    assert r.status_code == 409
    assert g.resumes == []  # graph was NOT resumed
