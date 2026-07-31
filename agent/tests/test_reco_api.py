from fastapi.testclient import TestClient
from followup_agent import api, auth, db
from followup_agent.config import Settings


def _settings():
    return Settings(
        database_url="x", openrouter_api_key="", openrouter_model="",
        jwt_signing_key="k", jwt_issuer="i", jwt_audience="a",
        smtp_host="", smtp_port=587, smtp_user="", smtp_password="",
        smtp_from="", followup_age_days=7, client_origin="http://localhost:3000",
    )


class _FakeConn:
    def close(self): pass
    def commit(self): pass


def _client(monkeypatch, store):
    monkeypatch.setattr(auth, "user_id_from_token", lambda tok, s: 1)
    monkeypatch.setattr(db, "list_recommendations",
                        lambda conn, uid, status: [r for r in store if r["status"] == status])

    def get_rec(conn, rec_id, uid, *, for_update=False):
        return next((r for r in store if r["id"] == rec_id), None)
    monkeypatch.setattr(db, "get_recommendation", get_rec)

    def update_rec(conn, rec_id, **fields):
        for r in store:
            if r["id"] == rec_id:
                r.update(fields)
    monkeypatch.setattr(db, "update_recommendation", update_rec)

    app = api.create_app(_settings(), conn_factory=lambda: _FakeConn(), graph=None)
    return TestClient(app)


HDR = {"Authorization": "Bearer t"}


def test_list_scopes_by_status(monkeypatch):
    store = [{"id": 1, "status": "pending", "company": "Acme"}]
    client = _client(monkeypatch, store)
    r = client.get("/recommendations", headers=HDR)
    assert r.status_code == 200 and r.json()[0]["company"] == "Acme"


def test_accept_sets_fields_and_is_idempotent(monkeypatch):
    store = [{"id": 1, "status": "pending", "accepted_application_id": None}]
    client = _client(monkeypatch, store)
    r = client.post("/recommendations/1/accept", json={"application_id": 42}, headers=HDR)
    assert r.status_code == 200
    assert store[0]["status"] == "accepted" and store[0]["accepted_application_id"] == 42
    # second call: already accepted -> no error, still accepted
    r2 = client.post("/recommendations/1/accept", json={"application_id": 99}, headers=HDR)
    assert r2.status_code == 200 and store[0]["accepted_application_id"] == 42


def test_accept_missing_returns_404(monkeypatch):
    client = _client(monkeypatch, [])
    r = client.post("/recommendations/9/accept", json={"application_id": 1}, headers=HDR)
    assert r.status_code == 404


def test_dismiss_sets_status(monkeypatch):
    store = [{"id": 1, "status": "pending"}]
    client = _client(monkeypatch, store)
    r = client.post("/recommendations/1/dismiss", headers=HDR)
    assert r.status_code == 200 and store[0]["status"] == "dismissed"
