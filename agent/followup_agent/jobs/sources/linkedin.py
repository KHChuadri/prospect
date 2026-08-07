"""LinkedIn public jobs-guest endpoints.

Ported from .agents/skills/linkedin-search/cli/src/helpers.ts in the
ai-job-search repo. Parsed with regex rather than a DOM library because the
markup is shallow and stable, and splitting on the job-posting URN lets one
malformed card fail without taking the rest of the page with it.

READ THIS BEFORE EDITING: LinkedIn's robots.txt is `Disallow: /` for all
user-agents. This module is the ONLY place in the codebase that bypasses the
robots check enforced by events/fetch.py. That exception is confined here on
purpose — one file to audit, one file to delete. See docs/ARCHITECTURE.md.
"""
import random
import re
import time
from typing import Optional
from urllib.parse import urlencode

import httpx

from followup_agent.jobs.sources import JobPosting

SEARCH_URL = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
)

_PAGE_SIZE = 10


def jobage_to_tpr(days: int) -> Optional[str]:
    """Convert a job age in days to LinkedIn's f_TPR seconds value."""
    if not days or days <= 0 or days >= 9999:
        return None
    return f"r{days * 86400}"


def work_type_flag(mode: Optional[str]) -> Optional[str]:
    """Workplace-type filter: on-site=1, remote=2, hybrid=3.

    Deliberate deviation from the ported TS (`workTypeFlag` in helpers.ts),
    which only lowercases: here `mode` comes from a hand-edited
    job_sources.yaml rather than a CLI flag, so `.strip()` treats stray
    whitespace as user intent instead of silently dropping the filter.
    """
    return {"remote": "2", "hybrid": "3",
            "onsite": "1", "on-site": "1"}.get((mode or "").strip().lower())


def build_search_url(*, query: Optional[str], location: str, jobage: int = 0,
                     remote: Optional[str] = None, page: int = 1) -> str:
    params = {}
    if query:
        params["keywords"] = query
    if location:
        params["location"] = location
    tpr = jobage_to_tpr(jobage)
    if tpr:
        params["f_TPR"] = tpr
    wt = work_type_flag(remote)
    if wt:
        params["f_WT"] = wt
    params["start"] = str((page - 1) * _PAGE_SIZE)
    return f"{SEARCH_URL}?{urlencode(params)}"


def _numeric_entity(cp: int) -> str:
    # Use chr() over the full range so supplementary-plane code points (emoji)
    # decode, and drop out-of-range values instead of raising.
    return chr(cp) if 0 <= cp <= 0x10FFFF else ""


def _decode_entities(text: str) -> str:
    for entity, char in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                         ("&quot;", '"'), ("&#39;", "'"), ("&apos;", "'"),
                         ("&nbsp;", " ")):
        text = text.replace(entity, char)
    text = re.sub(r"&#(\d+);", lambda m: _numeric_entity(int(m.group(1))), text)
    text = re.sub(r"&#[xX]([0-9a-fA-F]+);",
                  lambda m: _numeric_entity(int(m.group(1), 16)), text)
    return text


def _clean(html: str) -> str:
    return _decode_entities(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip())


def parse_job_cards(html: str) -> list[dict]:
    """Parse the search response into raw card dicts.

    Split on the job-posting URN so each card is parsed independently — one
    malformed card cannot break the rest of the page.
    """
    results: list[dict] = []
    for chunk in html.split('data-entity-urn="urn:li:jobPosting:')[1:]:
        id_match = re.match(r"^(\d+)", chunk)
        if not id_match:
            continue
        job_id = id_match.group(1)

        link = re.search(r'class="base-card__full-link[^"]*"[^>]*href="([^"]+)"',
                         chunk, re.I)
        url = _decode_entities(link.group(1)).split("?")[0] if link else ""

        title = None
        h3 = re.search(r'class="base-search-card__title"[^>]*>(.*?)</h3>',
                       chunk, re.I | re.S)
        if h3:
            title = _clean(h3.group(1))
        if not title:
            sr = re.search(r'class="sr-only"[^>]*>(.*?)</span>', chunk, re.I | re.S)
            if sr:
                title = _clean(sr.group(1))
        if not title:
            continue

        company = None
        sub = re.search(r'class="base-search-card__subtitle"[^>]*>(.*?)</h4>',
                        chunk, re.I | re.S)
        if sub:
            company = _clean(sub.group(1)) or None

        loc = re.search(r'class="job-search-card__location"[^>]*>(.*?)</span>',
                        chunk, re.I | re.S)
        location = (_clean(loc.group(1)) or None) if loc else None

        dt = re.search(
            r'class="job-search-card__listdate[^"]*"[^>]*datetime="([^"]+)"',
            chunk, re.I)

        results.append({
            "id": job_id,
            "title": title,
            "company": company,
            "location": location,
            "date": dt.group(1) if dt else None,
            "url": url or f"https://www.linkedin.com/jobs/view/{job_id}",
        })
    return results


_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

_MAX_RETRIES = 6
_INITIAL_DELAY = 0.5
_MAX_DELAY = 8.0


class LinkedInRefused(Exception):
    """LinkedIn declined, or we declined to ask.

    Raised for an exhausted retry budget, an open circuit breaker, or a
    per-run request budget that is spent. All three are the same thing from
    the crawler's point of view: this source contributes nothing this run.
    """


class LinkedInClient:
    """HTTP for the LinkedIn guest endpoints, with the rails a scheduler needs.

    The reference CLI has none of the budget, spacing or breaker logic below,
    because a human types one command and reads the error. Unattended, a bare
    retry loop would hammer a refused endpoint every 12 hours forever.

    Deliberately NOT an events/fetch.py Fetcher: that class enforces
    robots.txt, and LinkedIn's is `Disallow: /`. Confining the exception to
    this class is the point.

    State lives on the instance, so main.py constructs exactly one long-lived
    client. An agent restart clears the cooldown — accepted, and consistent
    with the single-worker in-process scheduler documented in ARCHITECTURE.md.
    """

    def __init__(self, *, max_requests: int = 10, delay_seconds: float = 2.0,
                 timeout: float = 10.0, sleep_fn=time.sleep,
                 client: Optional[httpx.Client] = None):
        self._max_requests = max_requests
        self._delay_seconds = delay_seconds
        self._sleep = sleep_fn
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(timeout, connect=timeout),
            follow_redirects=True, cookies={})
        self._requests_made = 0
        self._last_request_at: Optional[float] = None
        self._cooldown_runs = 0        # runs still to skip
        self._cooldown_next = 1        # length of the next cooldown, in runs
        self._skip_this_run = False    # was a cooldown active as this run began?

    def begin_run(self) -> None:
        """Reset the per-run budget and spend one run of any active cooldown.

        The cooldown must still bite on the run in which it is spent — decide
        `_skip_this_run` from the pre-decrement value so `get()` below sees a
        run that started under cooldown as skipped, even though this call
        immediately decrements the counter towards the cooldown's end.
        """
        self._requests_made = 0
        self._skip_this_run = self._cooldown_runs > 0
        if self._cooldown_runs > 0:
            self._cooldown_runs -= 1

    def _open_breaker(self) -> None:
        self._cooldown_runs = self._cooldown_next
        self._cooldown_next = min(self._cooldown_next * 2, 16)
        print(f"[jobs] linkedin: refused — skipping the next "
              f"{self._cooldown_runs} run(s)")

    def _close_breaker(self) -> None:
        self._cooldown_runs = 0
        self._cooldown_next = 1

    def _wait_turn(self) -> None:
        """Space distinct get() calls apart. Retries are spaced by backoff."""
        if self._last_request_at is not None:
            remaining = self._delay_seconds - (time.monotonic() - self._last_request_at)
            if remaining > 0:
                self._sleep(remaining)

    def get(self, url: str) -> str:
        # `_skip_this_run` alone only catches a cooldown that was already open
        # when the run began. A breaker opened by an earlier get() call in
        # THIS run (e.g. its retries were exhausted moments ago) leaves
        # `_skip_this_run` False but `_cooldown_runs` freshly positive — check
        # both, or a second get() in the same run walks straight past a
        # breaker that just opened.
        if self._skip_this_run or self._cooldown_runs > 0:
            raise LinkedInRefused(
                # `_cooldown_runs` is the post-decrement remainder; +1 counts
                # this run too, so the first skipped run doesn't misreport
                # "0 run(s) remaining" while it is actively being skipped.
                f"cooling down — {self._cooldown_runs + 1} run(s) remaining")
        if self._requests_made >= self._max_requests:
            raise LinkedInRefused(
                f"per-run request budget of {self._max_requests} is spent")

        # Once, before the first attempt. Calling this inside the retry loop
        # would stack spacing sleeps on top of backoff sleeps.
        self._wait_turn()

        delay = _INITIAL_DELAY
        for attempt in range(_MAX_RETRIES + 1):
            self._requests_made += 1
            response = self._client.get(url, headers={
                "User-Agent": _UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "X-Requested-With": "XMLHttpRequest",
            })
            self._last_request_at = time.monotonic()
            # httpx stores Set-Cookie in the client's jar and replays it on the
            # next request — `cookies={}` only seeds an empty jar, it does not
            # disable one. Clearing after every response is what actually keeps
            # this client anonymous, and anonymity is the whole safety property.
            self._client.cookies.clear()

            if response.status_code == 429 or response.status_code >= 500:
                if attempt == _MAX_RETRIES:
                    self._open_breaker()
                    raise LinkedInRefused(
                        f"{response.status_code} after {_MAX_RETRIES} retries")
                self._sleep(delay + random.uniform(0, 0.5))
                delay = min(delay * 2, _MAX_DELAY)
                continue

            if response.status_code == 404:
                self._close_breaker()
                return ""
            if response.status_code >= 400:
                raise LinkedInRefused(
                    f"{response.status_code} {response.reason_phrase}")

            self._close_breaker()
            return response.text

        raise LinkedInRefused("request failed after max retries")


# Below this, an empty body is genuinely empty rather than markup we stopped
# recognising. LinkedIn's zero-result response is a near-empty fragment.
_PARSE_FAILURE_THRESHOLD = 500


class LinkedInSource:
    """One saved search against the LinkedIn guest job board."""

    def __init__(self, cfg: dict, client: "LinkedInClient", max_results: int = 25):
        self.name = cfg["name"]
        self._query = cfg.get("query")
        self._location = cfg["location"]
        self._jobage = int(cfg.get("jobage") or 0)
        self._remote = cfg.get("remote")
        self._client = client
        self._max_results = max_results

    def discover(self) -> list[JobPosting]:
        html = self._client.get(build_search_url(
            query=self._query, location=self._location,
            jobage=self._jobage, remote=self._remote))

        cards = parse_job_cards(html)

        # A real body that yields nothing means the markup moved, not that the
        # search was empty. Without this the feed goes quiet and never says why.
        if not cards and len(html) > _PARSE_FAILURE_THRESHOLD:
            print(f"[jobs] {self.name}: parse failure — {len(html)} bytes, "
                  f"0 cards recognised. LinkedIn markup has probably changed.")
            return []

        if len(cards) > self._max_results:
            # Never truncate silently — a capped crawl must not look complete.
            print(f"[jobs] {self.name}: {len(cards)} cards, cap of "
                  f"{self._max_results} applied — "
                  f"{len(cards) - self._max_results} skipped")
            cards = cards[:self._max_results]

        out: list[JobPosting] = []
        for c in cards:
            if not c["company"]:
                continue
            out.append(JobPosting(
                uid=f"linkedin:{c['id']}",
                company=c["company"],
                role=c["title"],
                url=c["url"],
                location=c["location"],
                posted_at=c["date"],
            ))
        return out
