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


def load_search_configs(path: Union[str, Path]) -> list[dict]:
    """Read job_sources.yaml, validate, and drop disabled sources.

    A source is enabled unless it sets `enabled: false` — a missing key means
    enabled. Disabled sources are printed rather than silently dropped: a
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
        if cfg.get("enabled", True) is False:
            print(f"[jobs] {cfg['name']}: disabled — skipping")
            continue
        out.append(cfg)
    return out
