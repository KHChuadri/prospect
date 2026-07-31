from datetime import datetime, timezone, timedelta
import pytest
from followup_agent import db

SOON = datetime.now(timezone.utc) + timedelta(days=7)


@pytest.fixture
def schema(conn):
    db.init_events_schema(conn)
    return conn


def _mk(conn, *, uid="u1", title="Fintech Panel", starts_at=SOON,
        orgs=None, source="unsw-events"):
    return db.create_event(
        conn, source_name=source, source_uid=uid,
        url=f"https://example.test/{uid}", title=title,
        description="desc", starts_at=starts_at, ends_at=None,
        location="Level39", is_online=False,
        organizations=orgs if orgs is not None else ["Monzo"],
        topics=["fintech"], event_type="panel", raw_snippet="snip",
    )


def test_creates_and_reads_back_an_event(schema):
    eid = _mk(schema)
    assert eid is not None
    row = db.get_event(schema, eid)
    assert row["title"] == "Fintech Panel"
    assert row["organizations"] == ["Monzo"]


def test_duplicate_source_uid_returns_none_not_an_error(schema):
    # Gate 1 normally prevents this, but a concurrent crawl could race.
    assert _mk(schema, uid="dup") is not None
    assert _mk(schema, uid="dup") is None


def test_same_uid_from_a_different_source_is_a_separate_event(schema):
    assert _mk(schema, uid="x", source="unsw-events") is not None
    assert _mk(schema, uid="x", source="eventbrite") is not None


def test_existing_source_uids_returns_source_scoped_pairs(schema):
    _mk(schema, uid="a", source="unsw-events")
    _mk(schema, uid="b", source="eventbrite")
    uids = db.existing_source_uids(schema)
    assert ("unsw-events", "a") in uids
    assert ("eventbrite", "b") in uids
    assert ("eventbrite", "a") not in uids


def test_undecided_event_appears_in_the_feed_with_no_status(schema):
    _mk(schema, uid="new1")
    rows = db.list_events(schema, user_id=1)
    assert len(rows) == 1
    assert rows[0]["status"] is None      # no user_events row means undecided


def test_dismissed_event_leaves_the_feed(schema):
    eid = _mk(schema, uid="d1")
    db.set_event_decision(schema, user_id=1, event_id=eid, status="dismissed")
    assert db.list_events(schema, user_id=1) == []


def test_dismissal_is_per_user(schema):
    eid = _mk(schema, uid="d2")
    db.set_event_decision(schema, user_id=1, event_id=eid, status="dismissed")
    assert len(db.list_events(schema, user_id=2)) == 1   # user 2 unaffected


def test_interested_event_stays_in_feed_and_appears_in_saved(schema):
    eid = _mk(schema, uid="i1")
    db.set_event_decision(schema, user_id=1, event_id=eid, status="interested")
    assert db.list_events(schema, user_id=1)[0]["status"] == "interested"
    assert len(db.list_events(schema, user_id=1, saved=True)) == 1


def test_saved_view_excludes_undecided(schema):
    _mk(schema, uid="i2")
    assert db.list_events(schema, user_id=1, saved=True) == []


def test_decision_is_idempotent(schema):
    eid = _mk(schema, uid="i3")
    db.set_event_decision(schema, user_id=1, event_id=eid, status="interested")
    db.set_event_decision(schema, user_id=1, event_id=eid, status="dismissed")
    assert db.list_events(schema, user_id=1) == []


def test_clearing_a_decision_returns_the_event_to_undecided(schema):
    eid = _mk(schema, uid="i4")
    db.set_event_decision(schema, user_id=1, event_id=eid, status="dismissed")
    db.clear_event_decision(schema, user_id=1, event_id=eid)
    assert db.list_events(schema, user_id=1)[0]["status"] is None


def test_past_events_are_excluded(schema):
    _mk(schema, uid="old", starts_at=datetime.now(timezone.utc) - timedelta(days=1))
    assert db.list_events(schema, user_id=1) == []


def test_null_date_events_are_included_and_sort_last(schema):
    _mk(schema, uid="tbc", title="Autumn Fair", starts_at=None)
    _mk(schema, uid="dated", title="Panel", starts_at=SOON)
    rows = db.list_events(schema, user_id=1)
    assert [r["title"] for r in rows] == ["Panel", "Autumn Fair"]


def test_crawl_state_records_success_then_error(schema):
    db.record_crawl_state(schema, "unsw-events")
    db.record_crawl_state(schema, "unsw-events", error="boom")
    with schema.cursor() as cur:
        cur.execute("SELECT last_error FROM events_crawl_state WHERE source_name = %s",
                    ("unsw-events",))
        assert cur.fetchone()[0] == "boom"


def test_successful_crawl_clears_a_previous_error(schema):
    db.record_crawl_state(schema, "unsw-events", error="boom")
    db.record_crawl_state(schema, "unsw-events")
    with schema.cursor() as cur:
        cur.execute("SELECT last_error FROM events_crawl_state WHERE source_name = %s",
                    ("unsw-events",))
        assert cur.fetchone()[0] is None


def test_company_match_fires_on_exact_name(schema):
    _mk(schema, uid="cm1", orgs=["Monzo"])
    schema.execute(
        'INSERT INTO "JobApplications" ("UserId","Company","Role","Status","AppliedAt") '
        "VALUES (1,'Monzo','Engineer',0,now())")
    assert db.list_events(schema, user_id=1)[0]["company_match"] is True


def test_company_match_survives_a_legal_suffix(schema):
    # The page says "Monzo Bank Ltd"; the user tracks "Monzo". Exact
    # comparison would miss this and the feature would silently under-fire.
    _mk(schema, uid="cm2", orgs=["Monzo Bank Ltd"])
    schema.execute(
        'INSERT INTO "JobApplications" ("UserId","Company","Role","Status","AppliedAt") '
        "VALUES (1,'Monzo Bank','Engineer',0,now())")
    assert db.list_events(schema, user_id=1)[0]["company_match"] is True


def test_company_match_is_false_for_untracked_companies(schema):
    _mk(schema, uid="cm3", orgs=["Atlassian"])
    assert db.list_events(schema, user_id=1)[0]["company_match"] is False


def test_company_match_is_per_user(schema):
    _mk(schema, uid="cm4", orgs=["Monzo"])
    schema.execute(
        'INSERT INTO "JobApplications" ("UserId","Company","Role","Status","AppliedAt") '
        "VALUES (1,'Monzo','Engineer',0,now())")
    assert db.list_events(schema, user_id=2)[0]["company_match"] is False


def test_company_match_needs_no_recrawl_to_start_firing(schema):
    # The whole point of deriving it: an event crawled before the
    # application existed lights up as soon as the application is added.
    _mk(schema, uid="cm5", orgs=["Monzo"])
    assert db.list_events(schema, user_id=1)[0]["company_match"] is False
    schema.execute(
        'INSERT INTO "JobApplications" ("UserId","Company","Role","Status","AppliedAt") '
        "VALUES (1,'Monzo','Engineer',0,now())")
    assert db.list_events(schema, user_id=1)[0]["company_match"] is True
