from followup_agent import db


def test_followup_roundtrip(conn):

    fid = db.create_follow_up(
        conn, app_id=999999, user_id=42, thread_id="t-1",
        subject="Checking in", body="Hello", reason="stale 10d",
    )
    assert isinstance(fid, int)

    rows = db.list_follow_ups(conn, user_id=42, status="pending")
    assert any(r["id"] == fid for r in rows)

    one = db.get_follow_up(conn, fid, user_id=42)
    assert one["draft_subject"] == "Checking in"
    assert one["status"] == "pending"

    # scoping: other user cannot see it
    assert db.get_follow_up(conn, fid, user_id=43) is None

    db.update_follow_up(conn, fid, status="sent", recipient_email="r@x.com")
    assert db.get_follow_up(conn, fid, user_id=42)["status"] == "sent"


def test_existing_followup_app_ids_excludes_rejected(conn):
    a = db.create_follow_up(conn, app_id=111111, user_id=1, thread_id="a",
                            subject="s", body="b", reason="r")
    db.create_follow_up(conn, app_id=222222, user_id=1, thread_id="b",
                        subject="s", body="b", reason="r")
    db.update_follow_up(conn, a, status="rejected")
    ids = db.existing_followup_app_ids(conn)
    assert 222222 in ids and 111111 not in ids


def test_resume_roundtrip(conn):
    assert db.get_resume(conn, 42) is None
    db.upsert_resume(conn, 42, "resume v1")
    assert db.get_resume(conn, 42) == "resume v1"
    db.upsert_resume(conn, 42, "resume v2")          # upsert overwrites
    assert db.get_resume(conn, 42) == "resume v2"
    assert db.get_resume(conn, 99) is None            # scoped by user_id


def test_app_ai_jd_match_optimize(conn):
    db.upsert_jd(conn, 5, 42, "job description text")
    row = db.get_app_ai(conn, 5, 42)
    assert row["jd_text"] == "job description text"
    assert row["match_json"] is None
    assert db.get_app_ai(conn, 5, 99) is None         # scoped by user_id

    db.save_match(conn, 5, 42, {"score": 80, "missing": ["docker"]})
    assert db.get_app_ai(conn, 5, 42)["match_json"]["score"] == 80

    db.save_optimized(conn, 5, 42, "tailored resume")
    assert db.get_app_ai(conn, 5, 42)["optimized_resume"] == "tailored resume"


def test_upsert_jd_does_not_clobber_other_users_app(conn):
    db.upsert_jd(conn, 7, 42, "owner jd")
    db.upsert_jd(conn, 7, 99, "attacker jd")     # foreign user, same app_id
    assert db.get_app_ai(conn, 7, 42)["jd_text"] == "owner jd"   # unchanged
    assert db.get_app_ai(conn, 7, 99) is None                    # not visible to attacker
