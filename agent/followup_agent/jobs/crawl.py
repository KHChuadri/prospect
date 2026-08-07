from followup_agent import db


def _snippet(posting) -> str:
    """The card renders raw_snippet, and there is no column for posted_at.

    Folding location and date into it keeps the design at zero migrations
    while still showing both on the Recommendations page.
    """
    parts = []
    if posting.location:
        parts.append(posting.location)
    if posting.posted_at:
        parts.append(f"posted {posting.posted_at}")
    return " · ".join(parts)


def run_jobs_batch(conn, *, sources, user_id: int) -> list[int]:
    """Crawl every source and store the postings that pass four gates.

    Mirrors events/crawl.py. There is deliberately no sync cursor: search
    results show what is current, so the crawler re-reads them every run and
    Gate 1 absorbs the repeats. A source that failed at 09:00 is retried at
    21:00 — failure recovery is a property of the design rather than code.
    """
    seen_ids = db.existing_source_message_ids(conn)
    job_keys = db.existing_job_keys(conn, user_id)
    created: list[int] = []

    for source in sources:
        try:
            postings = source.discover()
        except Exception as e:
            # One dead source must not stop the others.
            print(f"[jobs] {source.name}: discover failed: {e}")
            continue

        print(f"[jobs] {source.name}: {len(postings)} posting(s)")
        for posting in postings:
            # GATE 1 — already stored. First, before any per-posting work,
            # which is what makes re-reading the same search nearly free.
            if posting.uid in seen_ids:
                continue

            try:
                # GATE 2 — usable identity.
                company = (posting.company or "").strip()
                role = (posting.role or "").strip()
                if not company or not role:
                    continue

                # GATE 3 — already on the board, or already awaiting a decision.
                key = (company.lower(), role.lower())
                if key in job_keys:
                    print(f"[jobs] {source.name}/{posting.uid}: already tracked {key}")
                    continue

                snippet = _snippet(posting)
            except Exception as e:
                # A malformed posting must not abort its source.
                print(f"[jobs] {source.name}/{posting.uid}: {e}")
                continue

            rid = db.create_recommendation(
                conn,
                user_id=user_id,
                source_message_id=posting.uid,
                source_sender=source.name,
                company=company,
                role=role,
                location=posting.location,
                url=posting.url,          # always the source's — never composed
                raw_snippet=snippet,
            )
            if rid is None:               # UNIQUE race — inserted elsewhere
                continue

            seen_ids.add(posting.uid)
            # GATE 4 — the same role listed by two sources. Adding the key here
            # rather than checking a separate set means one pass covers both
            # cross-source duplicates and repeats within a single source.
            job_keys.add(key)
            created.append(rid)
            print(f"[jobs] {source.name}/{posting.uid}: stored "
                  f"{company} / {role} -> {rid}")

    return created
