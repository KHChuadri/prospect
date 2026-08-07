"""Greenhouse job board API — public, structured, and robots-clean.

boards-api.greenhouse.io/robots.txt disallows only /embed/, so this goes
through the ordinary Fetcher with its robots check and honest UA. No LLM: the
payload is already structured, which is the same reason EventbriteSource
spends zero LLM calls.
"""
import json
from typing import Optional

from followup_agent.jobs.sources import JobPosting

API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


def parse_jobs(payload: dict, slug: str, company: str) -> list[JobPosting]:
    out: list[JobPosting] = []
    for raw in (payload or {}).get("jobs") or []:
        title = (raw.get("title") or "").strip()
        url = raw.get("absolute_url") or ""
        job_id = raw.get("id")
        if not title or not url or job_id is None:
            continue
        updated: Optional[str] = raw.get("updated_at")
        out.append(JobPosting(
            uid=f"greenhouse:{slug}:{job_id}",
            company=company,
            role=title,
            url=url,                                  # always the board's own
            location=((raw.get("location") or {}).get("name") or "").strip() or None,
            posted_at=updated[:10] if updated else None,
        ))
    return out


class GreenhouseSource:
    def __init__(self, cfg: dict, fetcher, max_results: int = 25):
        self.name = cfg["name"]
        self._slug = cfg["slug"]
        # Greenhouse does not return the company name, only the board slug.
        self._company = cfg.get("company") or self._slug.replace("-", " ").title()
        # Board name, not the YAML key: this is copied into
        # JobApplication.source, so renaming a search must not orphan history.
        self.display_name = f"Greenhouse · {self._company}"
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
