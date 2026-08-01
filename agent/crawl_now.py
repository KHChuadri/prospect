"""Run one crawl against the live internet and print what came back.

Extraction quality is judged, not asserted — this is the tool for judging it.
Automated tests use fixtures and fakes (see tests/test_events_crawl.py).

    python crawl_now.py                # every configured source
    python crawl_now.py unsw-events    # just one
"""
import sys

import psycopg

from followup_agent import db, llm
from followup_agent.config import load_settings
from followup_agent.events import crawl
from followup_agent.events.clean import html_to_text
from followup_agent.events.fetch import Fetcher
from followup_agent.events.sources import build_sources

settings = load_settings()
only = sys.argv[1] if len(sys.argv) > 1 else None

fetcher = Fetcher(settings.events_user_agent)
sources = [s for s in build_sources(settings, fetcher)
           if only is None or s.name == only]
if not sources:
    print(f"no source named {only!r} in {settings.events_sources_path}")
    raise SystemExit(1)

conn = psycopg.connect(settings.database_url)
try:
    db.init_events_schema(conn)
    conn.commit()
    ids = crawl.run_events_batch(
        conn, sources=sources, fetch_fn=fetcher.get,
        extract_fn=lambda text, url: llm.extract_event(html_to_text(text), settings),
    )
    conn.commit()
    print(f"\n=== stored {len(ids)} event(s) ===")
    for eid in ids:
        row = db.get_event(conn, eid)
        print(f"\n[{row['event_type']}] {row['title']}")
        print(f"  when:  {row['starts_at'] or 'TBC'}")
        print(f"  where: {row['location'] or ('Online' if row['is_online'] else '?')}")
        print(f"  orgs:  {row['organizations']}")
        print(f"  url:   {row['url']}")
finally:
    conn.close()
