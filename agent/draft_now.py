"""Trigger the follow-up batch immediately (instead of waiting for the 09:00 cron).

Drafts follow-ups for every application older than FOLLOWUP_AGE_DAYS in an
eligible status, leaving each one 'pending' for approval in the web UI.

Run from the agent/ directory:  python draft_now.py
Env is auto-loaded from agent/.env (no `source .env` needed).
"""
from followup_agent.main import graph, settings, _conn_factory
from followup_agent import batch


def main() -> None:
    conn = _conn_factory()
    try:
        ids = batch.run_batch(conn, graph, age_days=settings.followup_age_days)
        conn.commit()
        print(f"done. created {len(ids)} follow-up(s): {ids}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
