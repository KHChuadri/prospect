from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from followup_agent import api, db, auth
from followup_agent.config import Settings

SOON = datetime.now(timezone.utc) + timedelta(days=7)


@pytest.fixture
def settings():
    return Settings(
        database_url="", openrouter_api_key="", openrouter_model="",
        jwt_signing_key="k" * 32, jwt_issuer="i", jwt_audience="a",
        smtp_host="", smtp_port=587, smtp_user="", smtp_password="",
        smtp_from="", followup_age_days=7, client_origin="http://localhost:3000",
    )


@pytest.fixture
def client(settings, monkeypatch):
    monkeypatch.setattr(auth, "user_id_from_token", lambda tok, s: 1)
    app = api.create_app(settings, conn_factory=lambda: _FakeConn(), graph=None)
    return TestClient(app)


class _FakeConn:
    rows = []
    decisions = []

    def close(self):
        pass

    def commit(self):
        pass


HDR = {"Authorization": "Bearer anything"}


def test_list_requires_a_bearer_token(client):
    assert client.get("/events").status_code == 401


def test_list_returns_events(client, monkeypatch):
    monkeypatch.setattr(db, "list_events",
                        lambda conn, uid, **kw: [{"id": 1, "title": "Panel"}])
    r = client.get("/events", headers=HDR)
    assert r.status_code == 200
    assert r.json()[0]["title"] == "Panel"


def test_saved_query_param_reaches_the_db_layer(client, monkeypatch):
    seen = {}

    def fake_list(conn, uid, **kw):
        seen.update(kw)
        return []

    monkeypatch.setattr(db, "list_events", fake_list)
    client.get("/events", params={"saved": "true"}, headers=HDR)
    assert seen["saved"] is True


def test_interested_records_the_decision(client, monkeypatch):
    calls = []
    monkeypatch.setattr(db, "get_event", lambda conn, eid: {"id": eid, "title": "P"})
    monkeypatch.setattr(db, "set_event_decision",
                        lambda conn, uid, eid, status: calls.append((uid, eid, status)))
    r = client.post("/events/7/interested", headers=HDR)
    assert r.status_code == 200
    assert calls == [(1, 7, "interested")]


def test_dismiss_records_the_decision(client, monkeypatch):
    calls = []
    monkeypatch.setattr(db, "get_event", lambda conn, eid: {"id": eid, "title": "P"})
    monkeypatch.setattr(db, "set_event_decision",
                        lambda conn, uid, eid, status: calls.append(status))
    client.post("/events/7/dismiss", headers=HDR)
    assert calls == ["dismissed"]


def test_decision_on_a_missing_event_is_404(client, monkeypatch):
    monkeypatch.setattr(db, "get_event", lambda conn, eid: None)
    assert client.post("/events/999/interested", headers=HDR).status_code == 404


def test_undo_clears_the_decision(client, monkeypatch):
    calls = []
    monkeypatch.setattr(db, "get_event", lambda conn, eid: {"id": eid, "title": "P"})
    monkeypatch.setattr(db, "clear_event_decision",
                        lambda conn, uid, eid: calls.append((uid, eid)))
    r = client.delete("/events/7/decision", headers=HDR)
    assert r.status_code == 200
    assert calls == [(1, 7)]


def test_repeated_interested_is_idempotent(client, monkeypatch):
    monkeypatch.setattr(db, "get_event", lambda conn, eid: {"id": eid, "title": "P"})
    monkeypatch.setattr(db, "set_event_decision", lambda *a, **k: None)
    assert client.post("/events/7/interested", headers=HDR).status_code == 200
    assert client.post("/events/7/interested", headers=HDR).status_code == 200


def test_only_local_defaults_to_true(client, monkeypatch):
    seen = {}

    def fake_list(conn, uid, **kw):
        seen.update(kw)
        return []

    monkeypatch.setattr(db, "list_events", fake_list)
    client.get("/events", headers=HDR)
    assert seen["only_local"] is True


def test_only_local_query_param_reaches_the_db_layer(client, monkeypatch):
    seen = {}

    def fake_list(conn, uid, **kw):
        seen.update(kw)
        return []

    monkeypatch.setattr(db, "list_events", fake_list)
    client.get("/events", params={"only_local": "false"}, headers=HDR)
    assert seen["only_local"] is False
