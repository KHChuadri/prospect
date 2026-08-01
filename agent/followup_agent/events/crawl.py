from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from followup_agent import db
from followup_agent.events import timeparse
from followup_agent.models import EventExtract


def run_events_batch(
    conn,
    *,
    sources,
    fetch_fn: Callable[[str], str],
    extract_fn: Callable[[str, str], EventExtract],
    now: Optional[datetime] = None,
    max_future_days: int = 548,          # ~18 months
) -> list[int]:
    """Crawl every configured source and store the events that pass four gates.

    There is deliberately no sync cursor. Listing pages show what is current, so
    the crawler re-reads them every run and Gate 1 absorbs the repeats. An event
    that failed at 09:00 is simply retried at 21:00 — failure recovery is a
    property of the design rather than code.
    """
    now = now or datetime.now(timezone.utc)
    horizon = now + timedelta(days=max_future_days)
    seen_uids = db.existing_source_uids(conn)
    seen_keys: set[tuple[str, str]] = set()
    created: list[int] = []

    for source in sources:
        try:
            candidates = source.discover()
        except Exception as e:
            # One site being down must not stop the others.
            print(f"[events] {source.name}: discover failed: {e}")
            db.record_crawl_state(conn, source.name, error=str(e))
            continue

        print(f"[events] {source.name}: {len(candidates)} candidate(s)")
        for cand in candidates:
            # GATE 1 — already stored. Runs before any network or LLM cost,
            # which is what makes re-crawling the same listing nearly free.
            if (source.name, cand.uid) in seen_uids:
                continue

            try:
                ev = cand.prefetched
                if ev is None:
                    ev = extract_fn(fetch_fn(cand.url), cand.url)
            except Exception as e:
                # A flaky fetch or LLM call must not abort the source.
                print(f"[events] {source.name}/{cand.uid}: {e}")
                continue

            # GATE 2 — is this actually a career event with a usable title?
            if not ev.is_career_event or not ev.title.strip():
                continue

            starts_at = timeparse.to_utc(ev.starts_at_local, cand.timezone)

            # GATE 3 — plausible date. Null is allowed (renders as Date TBC);
            # past and hallucinated-far-future are not.
            if starts_at is not None and not (now <= starts_at <= horizon):
                continue

            # GATE 4 — the same event listed by two sources.
            key = timeparse.dedup_key(ev.title, starts_at)
            if key is not None and key in seen_keys:
                print(f"[events] {source.name}/{cand.uid}: duplicate of {key[0]}")
                continue

            eid = db.create_event(
                conn,
                source_name=source.name,
                source_uid=cand.uid,
                url=cand.url,                  # never ev — see EventExtract
                title=ev.title.strip(),
                description=ev.description,
                starts_at=starts_at,
                ends_at=timeparse.to_utc(ev.ends_at_local, cand.timezone),
                location=ev.location,
                is_online=ev.is_online,
                organizations=ev.organizations,
                topics=ev.topics,
                event_type=ev.event_type,
                raw_snippet=ev.description[:280],
            )
            if eid is None:                    # UNIQUE race — stored elsewhere
                continue
            seen_uids.add((source.name, cand.uid))
            if key is not None:
                seen_keys.add(key)
            created.append(eid)
            print(f"[events] {source.name}/{cand.uid}: stored {ev.title!r} -> {eid}")

        db.record_crawl_state(conn, source.name, error=None)

    return created
