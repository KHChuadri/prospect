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
import re
from typing import Optional
from urllib.parse import urlencode

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
