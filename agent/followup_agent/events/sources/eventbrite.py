from typing import Optional

import httpx

from followup_agent.models import EventExtract
from followup_agent.events.sources import Candidate

API = "https://www.eventbriteapi.com/v3/events/search/"


def _text(node, key="text") -> str:
    return (node or {}).get(key) or ""


def parse_event(raw: dict) -> tuple[str, str, EventExtract]:
    """Map one Eventbrite API event onto EventExtract.

    The API already returns structured fields, so this source spends zero LLM
    calls — that is the point of the prefetched branch in Candidate.
    """
    venue = raw.get("venue") or {}
    address = (venue.get("address") or {}).get("localized_address_display") or ""
    venue_name = venue.get("name") or ""
    location = ", ".join(p for p in (venue_name, address) if p) or None

    organizer = (raw.get("organizer") or {}).get("name")

    ev = EventExtract(
        is_career_event=True,      # the query already filters by category
        title=_text(raw.get("name")),
        description=_text(raw.get("description")),
        starts_at_local=(raw.get("start") or {}).get("local"),
        ends_at_local=(raw.get("end") or {}).get("local"),
        location=location,
        is_online=bool(raw.get("online_event")),
        organizations=[organizer] if organizer else [],
        topics=[],
        event_type="networking",
    )
    return str(raw.get("id") or ""), raw.get("url") or "", ev


class EventbriteSource:
    def __init__(self, cfg: dict, token: str, location: str,
                 client: Optional[httpx.Client] = None, max_pages: int = 25):
        self.name = cfg["name"]
        self.timezone = cfg["timezone"]
        self._token = token
        self._location = location
        self._client = client or httpx.Client(timeout=httpx.Timeout(10.0, connect=10.0))
        self._max_pages = max_pages

    def discover(self) -> list[Candidate]:
        if not self._token:
            print(f"[events] {self.name}: no EVENTBRITE_TOKEN set — skipping")
            return []
        resp = self._client.get(
            API,
            headers={"Authorization": f"Bearer {self._token}"},
            params={
                "location.address": self._location,
                "categories": "101",          # Business & Professional
                "start_date.keyword": "this_month",
                "expand": "venue,organizer",
            },
        )
        resp.raise_for_status()
        events = (resp.json() or {}).get("events") or []
        if len(events) > self._max_pages:
            print(f"[events] {self.name}: {len(events)} events, "
                  f"cap of {self._max_pages} applied — {len(events) - self._max_pages} skipped")
            events = events[:self._max_pages]

        out: list[Candidate] = []
        for raw in events:
            uid, url, ev = parse_event(raw)
            if uid and url:
                out.append(Candidate(uid=uid, url=url, timezone=self.timezone,
                                     prefetched=ev))
        return out
