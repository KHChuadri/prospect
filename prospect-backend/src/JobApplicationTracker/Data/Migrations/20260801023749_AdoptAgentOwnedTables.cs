using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace JobApplicationTracker.Data.Migrations
{
    /// <summary>
    /// Brings the Python agent's tables under EF Core's ownership.
    ///
    /// This is a BASELINE migration, so Up() is hand-written idempotent SQL
    /// rather than the CreateTable calls EF scaffolded. Every deployment that
    /// has ever run the agent already has these tables — the agent used to
    /// create them itself with CREATE TABLE IF NOT EXISTS at startup — and a
    /// plain CreateTable would fail there with "relation already exists".
    ///
    /// The statements below are copied verbatim from the DDL the agent used to
    /// execute (followup_agent/db.py, removed in the same commit), so the
    /// result is identical whether this runs against a fresh database or one
    /// that has been live since day one:
    ///
    ///   fresh database    -> tables are created here for the first time
    ///   existing database -> every statement is a no-op, and the migration is
    ///                        recorded so later migrations apply normally
    ///
    /// From the NEXT migration onward, use ordinary EF operations. This is the
    /// only migration in the project that should contain raw idempotent DDL;
    /// the migration ledger makes IF NOT EXISTS unnecessary from here on.
    /// </summary>
    public partial class AdoptAgentOwnedTables : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql(@"
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

CREATE TABLE IF NOT EXISTS events (
    id            SERIAL PRIMARY KEY,
    source_name   TEXT NOT NULL,
    source_uid    TEXT NOT NULL,
    url           TEXT NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    starts_at     TIMESTAMPTZ,
    ends_at       TIMESTAMPTZ,
    location      TEXT,
    is_online     BOOLEAN NOT NULL DEFAULT false,
    organizations TEXT[] NOT NULL DEFAULT '{}',
    topics        TEXT[] NOT NULL DEFAULT '{}',
    event_type    TEXT,
    raw_snippet   TEXT NOT NULL DEFAULT '',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_name, source_uid)
);

CREATE INDEX IF NOT EXISTS events_starts_idx ON events (starts_at);

-- Events are public, so the event row is global. Only the user's opinion is
-- per-user, and only once they have one — no row means undecided.
CREATE TABLE IF NOT EXISTS user_events (
    user_id    INTEGER NOT NULL,
    event_id   INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    status     TEXT NOT NULL,
    decided_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, event_id)
);

-- EF indexes foreign key columns by convention; the agent's original DDL did
-- not. Created here so a database that predates this migration ends up
-- matching a freshly created one exactly.
CREATE INDEX IF NOT EXISTS ""IX_user_events_event_id"" ON user_events (event_id);

CREATE TABLE IF NOT EXISTS events_crawl_state (
    source_name     TEXT PRIMARY KEY,
    last_crawled_at TIMESTAMPTZ NOT NULL,
    last_error      TEXT
);

-- In SQL rather than application code so the company match runs inside the
-- query instead of pulling both lists into the API process.
CREATE OR REPLACE FUNCTION normalize_company(name TEXT)
RETURNS TEXT LANGUAGE sql IMMUTABLE AS $$
    SELECT btrim(regexp_replace(
        regexp_replace(lower(coalesce(name, '')),
            '\s+(ltd|limited|inc|incorporated|plc|corp|corporation|pty|llc)\.?$',
            '', 'g'),
        '\s+', ' ', 'g'));
$$;
");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql(@"
DROP FUNCTION IF EXISTS normalize_company(TEXT);
DROP TABLE IF EXISTS user_events;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS events_crawl_state;
DROP TABLE IF EXISTS gmail_sync_state;
DROP TABLE IF EXISTS recommendations;
DROP TABLE IF EXISTS app_ai;
DROP TABLE IF EXISTS resumes;
DROP TABLE IF EXISTS follow_ups;
");
        }
    }
}
