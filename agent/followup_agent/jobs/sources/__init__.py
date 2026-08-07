from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import yaml

# Required keys per source type. Validated at load so a typo fails at startup
# with the key name in the message, rather than as an AttributeError mid-crawl.
_REQUIRED = {
    "linkedin": ("name", "type", "query", "location"),
    "greenhouse": ("name", "type", "slug"),
    "lever": ("name", "type", "slug"),
}


@dataclass(frozen=True)
class JobPosting:
    """One posting, as a source returned it.

    A plain dataclass rather than a pydantic model because no LLM touches this
    path — all three sources return structured data, so there is nothing to
    validate against a hallucination and no injection surface. `url` always
    comes from the source; it is never composed from an id.
    """
    uid: str                        # "linkedin:4426311357"
    company: str
    role: str
    url: str
    location: Optional[str] = None
    posted_at: Optional[str] = None


_DISABLED_WORDS = frozenset({"false", "no", "off"})


def _is_disabled(value) -> bool:
    """Is this `enabled:` value a request to sit the source out?

    A bare `is False` would miss the quoted forms. YAML gives `enabled: "false"`
    as the STRING "false", which is truthy in Python — so a stray pair of quotes
    used to leave the source running and print no "disabled" line. That matters
    beyond tidiness: ARCHITECTURE.md names this toggle as the way to switch off
    the ToS-violating LinkedIn source in a shared deployment, so a quoting typo
    silently re-enabled it with nothing in the log to reveal the mistake.

    Only the explicit negative words disable. Anything else — including a
    missing key, a truthy string, or a number — leaves the source enabled, so
    this cannot accidentally switch a source off.
    """
    if isinstance(value, bool):
        return value is False
    if isinstance(value, str):
        return value.strip().lower() in _DISABLED_WORDS
    return False


def load_search_configs(path: Union[str, Path]) -> list[dict]:
    """Read job_sources.yaml, validate, and drop disabled sources.

    A source is enabled unless it sets `enabled: false` — a missing key means
    enabled, and the quoted string forms ("false"/"no"/"off", any case) count as
    disabled too. Disabled sources are printed rather than silently dropped: a
    skipped source and a source that found nothing look identical in the log
    otherwise.
    """
    path = Path(path)
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text()) or {}
    cfgs = data.get("sources") or []

    out = []
    for cfg in cfgs:
        stype = cfg.get("type")
        required = _REQUIRED.get(stype)
        if required is None:
            raise ValueError(
                f"source {cfg.get('name', '<unnamed>')} has unknown type {stype!r}")
        missing = [k for k in required if not cfg.get(k)]
        if missing:
            raise ValueError(
                f"source {cfg.get('name', '<unnamed>')} is missing: {', '.join(missing)}")
        if _is_disabled(cfg.get("enabled", True)):
            print(f"[jobs] {cfg['name']}: disabled — skipping")
            continue
        out.append(cfg)
    return out


def build_job_sources(settings, fetcher, linkedin_client) -> list:
    """Construct source objects from job_sources.yaml.

    Lives here rather than in main.py so crawl_jobs_now.py can call it without
    importing main — importing main would start the scheduler and the API.
    Source classes are imported lazily to avoid a circular import back into
    this module.
    """
    from followup_agent.jobs.sources.greenhouse import GreenhouseSource
    from followup_agent.jobs.sources.lever import LeverSource
    from followup_agent.jobs.sources.linkedin import LinkedInSource

    cap = settings.jobs_max_per_source
    out = []
    for cfg in load_search_configs(settings.jobs_sources_path):
        if cfg["type"] == "linkedin":
            out.append(LinkedInSource(cfg, linkedin_client, max_results=cap))
        elif cfg["type"] == "greenhouse":
            out.append(GreenhouseSource(cfg, fetcher, max_results=cap))
        else:
            out.append(LeverSource(cfg, fetcher, max_results=cap))
    return out
