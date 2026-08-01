from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import yaml

from followup_agent.models import EventExtract

_REQUIRED = {
    "generic": ("name", "type", "url", "link_pattern", "timezone"),
    "eventbrite": ("name", "type", "timezone"),
}


@dataclass(frozen=True)
class Candidate:
    """One possible event, before the gates decide whether to keep it.

    prefetched carries a fully-formed event when the source already has
    structured data (the Eventbrite API). Generic pages leave it None and the
    pipeline runs fetch -> clean -> LLM. That single field is the whole hybrid.
    """
    uid: str
    url: str
    timezone: str
    prefetched: Optional[EventExtract] = None


def load_source_configs(path: Union[str, Path]) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text()) or {}
    cfgs = data.get("sources") or []
    for cfg in cfgs:
        required = _REQUIRED.get(cfg.get("type"), _REQUIRED["generic"])
        missing = [k for k in required if not cfg.get(k)]
        if missing:
            raise ValueError(
                f"source {cfg.get('name', '<unnamed>')} is missing: {', '.join(missing)}")
    return cfgs


def build_sources(settings, fetcher) -> list:
    """Construct source objects from events_sources.yaml.

    Lives here rather than in main.py so crawl_now.py can call it without
    importing main — importing main would start the scheduler and the API.
    Source classes are imported lazily to avoid a circular import back into
    this module.
    """
    from followup_agent.events.sources.generic import GenericSource
    from followup_agent.events.sources.eventbrite import EventbriteSource

    out = []
    for cfg in load_source_configs(settings.events_sources_path):
        if cfg["type"] == "eventbrite":
            out.append(EventbriteSource(cfg, token=settings.eventbrite_token,
                                        location=settings.events_location))
        else:
            out.append(GenericSource(cfg, fetcher))
    return out
