"""Lever postings API — public, structured, and robots-clean.

Same posture as greenhouse.py: ordinary Fetcher, robots check intact, no LLM.
"""
import json
from datetime import datetime, timezone
from typing import Optional

from followup_agent.jobs.sources import JobPosting

API = "https://api.lever.co/v0/postings/{slug}?mode=json"


def _iso_date(created_at) -> Optional[str]:
    """Lever's createdAt is epoch milliseconds."""
    # bool is a subclass of int (isinstance(True, int) is True), so it must be
    # excluded explicitly or a stray True/False would silently parse as an
    # epoch timestamp instead of being rejected as non-numeric.
    if isinstance(created_at, bool) or not isinstance(created_at, (int, float)):
        return None
    return datetime.fromtimestamp(created_at / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def parse_jobs(payload: list, slug: str, company: str) -> list[JobPosting]:
    out: list[JobPosting] = []
    for raw in payload or []:
        title = (raw.get("text") or "").strip()
        url = raw.get("hostedUrl") or ""
        job_id = raw.get("id")
        if not title or not url or not job_id:
            continue
        out.append(JobPosting(
            uid=f"lever:{slug}:{job_id}",
            company=company,
            role=title,
            url=url,
            location=((raw.get("categories") or {}).get("location") or "").strip() or None,
            posted_at=_iso_date(raw.get("createdAt")),
        ))
    return out


class LeverSource:
    def __init__(self, cfg: dict, fetcher, max_results: int = 25):
        self.name = cfg["name"]
        self._slug = cfg["slug"]
        self._company = cfg.get("company") or self._slug.replace("-", " ").title()
        self._fetcher = fetcher
        self._max_results = max_results

    def discover(self) -> list[JobPosting]:
        payload = json.loads(self._fetcher.get(API.format(slug=self._slug)))
        jobs = parse_jobs(payload, self._slug, self._company)
        if len(jobs) > self._max_results:
            print(f"[jobs] {self.name}: {len(jobs)} postings, cap of "
                  f"{self._max_results} applied — "
                  f"{len(jobs) - self._max_results} skipped")
            jobs = jobs[:self._max_results]
        return jobs
