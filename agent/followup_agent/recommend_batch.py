from datetime import datetime, timezone, timedelta
from typing import Callable, Optional
from followup_agent import db
from followup_agent.models import ParsedEmail, RecommendationExtract


def run_reco_batch(
    conn,
    *,
    gmail_fn: Callable[[datetime], list[ParsedEmail]],
    extract_fn: Callable[[ParsedEmail], RecommendationExtract],
    user_id: int,
    now: Optional[datetime] = None,
) -> list[int]:
    now = now or datetime.now(timezone.utc)
    since = db.get_sync_state(conn, user_id) or (now - timedelta(days=1))
    emails = gmail_fn(since)

    seen = db.existing_message_ids(conn)
    job_keys = db.existing_job_keys(conn, user_id)
    created: list[int] = []
    extract_failed = False
    print(f"[reco] {len(emails)} email(s) since {since:%Y-%m-%d %H:%M}")

    for em in emails:
        if em.message_id in seen:
            continue
        # A flaky LLM call must not abort the batch — log and continue.
        try:
            ex = extract_fn(em)
        except Exception as e:
            print(f"[reco] skip {em.message_id}: {e}")
            extract_failed = True
            continue
        if not ex.is_job or not ex.company.strip() or not ex.role.strip():
            continue
        key = (ex.company.strip().lower(), ex.role.strip().lower())
        if key in job_keys:
            print(f"[reco] skip {em.message_id}: already tracked {key}")
            continue
        rid = db.create_recommendation(
            conn, user_id=user_id, source_message_id=em.message_id,
            source_sender=em.sender, company=ex.company.strip(),
            role=ex.role.strip(), location=ex.location, url=ex.url,
            raw_snippet=em.body[:280],
        )
        if rid is None:            # UNIQUE race — inserted elsewhere
            continue
        job_keys.add(key)          # prevent duplicate within this same batch
        created.append(rid)
        print(f"[reco] {em.message_id}: recommended {ex.company} / {ex.role} -> {rid}")

    # Only advance the sync cursor if every message extracted cleanly. A
    # transient LLM failure leaves `since` unchanged so the next poll re-fetches
    # that window; already-inserted messages are skipped by message-id dedup, so
    # only the failed ones get retried.
    if not extract_failed:
        db.set_sync_state(conn, user_id, now)
    return created
