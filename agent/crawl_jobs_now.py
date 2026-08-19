"""Run one job crawl against the live internet and print what came back.

Source quality is judged, not asserted — this is the tool for judging it.
Automated tests use fixtures and fakes (see tests/test_jobs_crawl.py).

    python crawl_jobs_now.py                     # every enabled source
    python crawl_jobs_now.py linkedin-ai-syd     # just one
"""
import sys

import psycopg

from followup_agent import db
from followup_agent.config import load_settings
from followup_agent.events.fetch import Fetcher
from followup_agent.jobs import crawl
from followup_agent.jobs.sources import build_job_sources
from followup_agent.jobs.sources.linkedin import LinkedInClient

settings = load_settings()
only = sys.argv[1] if len(sys.argv) > 1 else None

fetcher = Fetcher(settings.jobs_user_agent)
client = LinkedInClient(max_requests=settings.jobs_max_requests_per_run)
client.begin_run()

sources = [s for s in build_job_sources(settings, fetcher, client)
           if only is None or s.name == only]
if not sources:
    print(f"no enabled source named {only!r} in {settings.jobs_sources_path}")
    raise SystemExit(1)

conn = psycopg.connect(settings.database_url)
try:
    # Tables come from the backend's EF migrations; nothing to create here.
    ids = crawl.run_jobs_batch(conn, sources=sources, user_id=settings.reco_user_id)
    conn.commit()
    print(f"\n=== stored {len(ids)} recommendation(s) ===")
    for rid in ids:
        row = db.get_recommendation(conn, rid, settings.reco_user_id)
        print(f"\n{row['role']} · {row['company']}")
        print(f"  where: {row['location'] or '?'}")
        print(f"  from:  {row['source_sender']}")
        print(f"  url:   {row['url']}")
finally:
    conn.close()
