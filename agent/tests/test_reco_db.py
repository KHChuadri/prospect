from datetime import datetime, timezone
from followup_agent import db


def test_create_list_and_dedup_message_id(conn):
    rid = db.create_recommendation(
        conn, user_id=1, source_message_id="m1", source_sender="jobs@acme.com",
        company="Acme", role="Backend Engineer", location="Remote",
        url="https://x", raw_snippet="snippet",
    )
    assert rid is not None

    # same message id -> conflict -> None
    dup = db.create_recommendation(
        conn, user_id=1, source_message_id="m1", source_sender="jobs@acme.com",
        company="Acme", role="Backend Engineer", location=None, url=None,
        raw_snippet="",
    )
    assert dup is None

    rows = db.list_recommendations(conn, 1, "pending")
    assert len(rows) == 1 and rows[0]["company"] == "Acme"
    assert db.existing_message_ids(conn) == {"m1"}


def test_existing_job_keys_includes_pending_recs(conn):
    db.create_recommendation(
        conn, user_id=1, source_message_id="m2", source_sender="s",
        company="Beta Co", role="PM", location=None, url=None, raw_snippet="",
    )
    keys = db.existing_job_keys(conn, 1)
    assert ("beta co", "pm") in keys


def test_update_and_sync_state(conn):
    rid = db.create_recommendation(
        conn, user_id=1, source_message_id="m3", source_sender="s",
        company="Gamma", role="SRE", location=None, url=None, raw_snippet="",
    )
    db.update_recommendation(conn, rid, status="accepted",
                             accepted_application_id=99,
                             decided_at=datetime.now(timezone.utc))
    row = db.get_recommendation(conn, rid, 1)
    assert row["status"] == "accepted" and row["accepted_application_id"] == 99

    ts = datetime(2026, 7, 7, tzinfo=timezone.utc)
    db.set_sync_state(conn, 1, ts)
    assert db.get_sync_state(conn, 1) == ts
