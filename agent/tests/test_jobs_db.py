from followup_agent import db


def _mk(conn, source_message_id, status="pending"):
    rid = db.create_recommendation(
        conn, user_id=1, source_message_id=source_message_id,
        source_sender="LinkedIn", company="Canva", role="Engineer",
        location="Sydney NSW", url="https://ex.test/1", raw_snippet="")
    if status != "pending":
        with conn.cursor() as cur:
            cur.execute("UPDATE recommendations SET status = %s WHERE id = %s",
                        (status, rid))
    return rid


def test_returns_stored_source_message_ids(conn):
    _mk(conn, "linkedin:111")
    _mk(conn, "greenhouse:stripe:222")
    ids = db.existing_source_message_ids(conn)
    assert "linkedin:111" in ids
    assert "greenhouse:stripe:222" in ids


def test_includes_dismissed_ids(conn):
    # A dismissed posting must stay dismissed. Filtering by status here would
    # resurrect every rejected posting on the next crawl.
    _mk(conn, "linkedin:333", status="dismissed")
    assert "linkedin:333" in db.existing_source_message_ids(conn)


def test_includes_accepted_ids(conn):
    _mk(conn, "linkedin:444", status="accepted")
    assert "linkedin:444" in db.existing_source_message_ids(conn)
