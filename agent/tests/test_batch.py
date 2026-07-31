from datetime import datetime, timezone, timedelta
from followup_agent.models import AppRow
from followup_agent import batch, db, rules

NOW = datetime(2026, 6, 26, tzinfo=timezone.utc)


class FakeGraph:
    """Returns a warranted draft for app id 1, not warranted for id 2."""
    def invoke(self, state, cfg):
        app = state["app"]
        if app["id"] == 1:
            return {**state, "warranted": True, "reason": "stale",
                    "draft_subject": "Hi", "draft_body": "Body"}
        return {**state, "warranted": False}


def test_run_batch_creates_rows_for_warranted(monkeypatch):
    apps = [
        AppRow(1, 1, "Acme", "Eng", 0, NOW - timedelta(days=30)),
        AppRow(2, 1, "Beta", "PM", 1, NOW - timedelta(days=30)),
    ]
    monkeypatch.setattr(db, "fetch_candidate_apps", lambda conn: apps)
    monkeypatch.setattr(db, "existing_followup_app_ids", lambda conn: set())

    created = []
    def fake_create(conn, **kw):
        created.append(kw)
        return len(created)
    monkeypatch.setattr(db, "create_follow_up", fake_create)

    ids = batch.run_batch(conn=None, graph=FakeGraph(), age_days=7, now=NOW)

    assert ids == [1]                          # only app 1 warranted
    assert created[0]["app_id"] == 1
    assert created[0]["thread_id"] == "followup-1-20260626"
    assert created[0]["subject"] == "Hi"
