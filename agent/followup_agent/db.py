from datetime import datetime
from typing import Optional
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json
from followup_agent.models import AppRow, ELIGIBLE_STATUSES

SCHEMA = """
CREATE TABLE IF NOT EXISTS follow_ups (
    id              SERIAL PRIMARY KEY,
    app_id          INTEGER NOT NULL,
    user_id         INTEGER NOT NULL,
    thread_id       TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    draft_subject   TEXT NOT NULL,
    draft_body      TEXT NOT NULL,
    recipient_email TEXT,
    reason          TEXT NOT NULL DEFAULT '',
    error           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at      TIMESTAMPTZ,
    sent_at         TIMESTAMPTZ
);
"""

AI_SCHEMA = """
CREATE TABLE IF NOT EXISTS resumes (
    user_id     INTEGER PRIMARY KEY,
    text        TEXT NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app_ai (
    app_id            INTEGER PRIMARY KEY,
    user_id           INTEGER NOT NULL,
    jd_text           TEXT NOT NULL,
    match_json        JSONB,
    optimized_resume  TEXT,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

RECO_SCHEMA = """
CREATE TABLE IF NOT EXISTS recommendations (
    id                      SERIAL PRIMARY KEY,
    user_id                 INTEGER NOT NULL,
    source_message_id       TEXT NOT NULL UNIQUE,
    source_sender           TEXT NOT NULL DEFAULT '',
    company                 TEXT NOT NULL,
    role                    TEXT NOT NULL,
    location                TEXT,
    url                     TEXT,
    raw_snippet             TEXT NOT NULL DEFAULT '',
    status                  TEXT NOT NULL DEFAULT 'pending',
    accepted_application_id INTEGER,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at              TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS gmail_sync_state (
    user_id        INTEGER PRIMARY KEY,
    last_polled_at TIMESTAMPTZ NOT NULL
);
"""

_ALLOWED_UPDATE = {"status", "recipient_email", "draft_subject", "draft_body",
                   "error", "decided_at", "sent_at"}

_ALLOWED_RECO_UPDATE = {"status", "accepted_application_id", "decided_at"}


def init_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(SCHEMA)


def fetch_candidate_apps(conn: psycopg.Connection) -> list[AppRow]:
    statuses = tuple(ELIGIBLE_STATUSES)
    with conn.cursor() as cur:
        cur.execute(
            'SELECT "Id", "UserId", "Company", "Role", "Status", "AppliedAt" '
            'FROM "JobApplications" WHERE "Status" = ANY(%s)',
            (list(statuses),),
        )
        return [
            AppRow(id=r[0], user_id=r[1], company=r[2], role=r[3],
                   status=r[4], applied_at=r[5])
            for r in cur.fetchall()
        ]


def existing_followup_app_ids(conn: psycopg.Connection) -> set[int]:
    with conn.cursor() as cur:
        cur.execute("SELECT app_id FROM follow_ups WHERE status <> 'rejected'")
        return {r[0] for r in cur.fetchall()}


def create_follow_up(conn, *, app_id, user_id, thread_id, subject, body, reason) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO follow_ups "
            "(app_id, user_id, thread_id, draft_subject, draft_body, reason) "
            "VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
            (app_id, user_id, thread_id, subject, body, reason),
        )
        return cur.fetchone()[0]


def list_follow_ups(conn, user_id, status) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM follow_ups WHERE user_id = %s AND status = %s "
            "ORDER BY created_at DESC",
            (user_id, status),
        )
        return cur.fetchall()


def get_follow_up(conn, follow_up_id, user_id, *, for_update=False) -> Optional[dict]:
    # for_update locks the row until the transaction commits, so two concurrent
    # approve requests can't both read 'pending' and both send.
    sql = "SELECT * FROM follow_ups WHERE id = %s AND user_id = %s"
    if for_update:
        sql += " FOR UPDATE"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, (follow_up_id, user_id))
        return cur.fetchone()


def update_follow_up(conn, follow_up_id, **fields) -> None:
    cols = [c for c in fields if c in _ALLOWED_UPDATE]
    if not cols:
        return
    sets = ", ".join(f"{c} = %s" for c in cols)
    values = [fields[c] for c in cols] + [follow_up_id]
    with conn.cursor() as cur:
        cur.execute(f"UPDATE follow_ups SET {sets} WHERE id = %s", values)


def init_ai_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(AI_SCHEMA)


def upsert_resume(conn, user_id: int, text: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO resumes (user_id, text) VALUES (%s, %s) "
            "ON CONFLICT (user_id) DO UPDATE "
            "SET text = EXCLUDED.text, updated_at = now()",
            (user_id, text),
        )


def get_resume(conn, user_id: int) -> Optional[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT text FROM resumes WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        return row[0] if row else None


def upsert_jd(conn, app_id: int, user_id: int, text: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO app_ai (app_id, user_id, jd_text) VALUES (%s, %s, %s) "
            "ON CONFLICT (app_id) DO UPDATE "
            "SET jd_text = EXCLUDED.jd_text, updated_at = now() "
            "WHERE app_ai.user_id = EXCLUDED.user_id",
            (app_id, user_id, text),
        )


def get_app_ai(conn, app_id: int, user_id: int) -> Optional[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM app_ai WHERE app_id = %s AND user_id = %s",
            (app_id, user_id),
        )
        return cur.fetchone()


def save_match(conn, app_id: int, user_id: int, match_json: dict) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE app_ai SET match_json = %s, updated_at = now() "
            "WHERE app_id = %s AND user_id = %s",
            (Json(match_json), app_id, user_id),
        )


def save_optimized(conn, app_id: int, user_id: int, text: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE app_ai SET optimized_resume = %s, updated_at = now() "
            "WHERE app_id = %s AND user_id = %s",
            (text, app_id, user_id),
        )


def init_reco_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(RECO_SCHEMA)


def existing_message_ids(conn) -> set[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT source_message_id FROM recommendations")
        return {r[0] for r in cur.fetchall()}


def existing_job_keys(conn, user_id: int) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    with conn.cursor() as cur:
        cur.execute(
            'SELECT LOWER(TRIM("Company")), LOWER(TRIM("Role")) '
            'FROM "JobApplications" WHERE "UserId" = %s',
            (user_id,),
        )
        keys.update((r[0], r[1]) for r in cur.fetchall())
        cur.execute(
            "SELECT LOWER(TRIM(company)), LOWER(TRIM(role)) FROM recommendations "
            "WHERE user_id = %s AND status = 'pending'",
            (user_id,),
        )
        keys.update((r[0], r[1]) for r in cur.fetchall())
    return keys


def create_recommendation(conn, *, user_id, source_message_id, source_sender,
                          company, role, location, url, raw_snippet) -> Optional[int]:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO recommendations "
            "(user_id, source_message_id, source_sender, company, role, "
            " location, url, raw_snippet) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (source_message_id) DO NOTHING RETURNING id",
            (user_id, source_message_id, source_sender, company, role,
             location, url, raw_snippet),
        )
        row = cur.fetchone()
        return row[0] if row else None


def list_recommendations(conn, user_id, status) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM recommendations WHERE user_id = %s AND status = %s "
            "ORDER BY created_at DESC",
            (user_id, status),
        )
        return cur.fetchall()


def get_recommendation(conn, rec_id, user_id, *, for_update=False) -> Optional[dict]:
    sql = "SELECT * FROM recommendations WHERE id = %s AND user_id = %s"
    if for_update:
        sql += " FOR UPDATE"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, (rec_id, user_id))
        return cur.fetchone()


def update_recommendation(conn, rec_id, **fields) -> None:
    cols = [c for c in fields if c in _ALLOWED_RECO_UPDATE]
    if not cols:
        return
    sets = ", ".join(f"{c} = %s" for c in cols)
    values = [fields[c] for c in cols] + [rec_id]
    with conn.cursor() as cur:
        cur.execute(f"UPDATE recommendations SET {sets} WHERE id = %s", values)


def get_sync_state(conn, user_id) -> Optional[datetime]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT last_polled_at FROM gmail_sync_state WHERE user_id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        return row[0] if row else None


def set_sync_state(conn, user_id, ts) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO gmail_sync_state (user_id, last_polled_at) "
            "VALUES (%s, %s) ON CONFLICT (user_id) DO UPDATE "
            "SET last_polled_at = EXCLUDED.last_polled_at",
            (user_id, ts),
        )
