from followup_agent.events import clean
from followup_agent.events.sources import Candidate


class GenericSource:
    """A listing page whose event links are followed one hop.

    Listing pages carry title, date and venue but almost never speakers —
    and speakers are what fill organizations[], which company matching needs.
    So the detail page is fetched rather than extracting from the listing.
    The cost is front-loaded: Gate 1 skips known URLs on every later crawl.
    """

    def __init__(self, cfg: dict, fetcher, max_pages: int = 25):
        self.name = cfg["name"]
        self.url = cfg["url"]
        self.link_pattern = cfg["link_pattern"]
        self.timezone = cfg["timezone"]
        self._fetcher = fetcher
        self._max_pages = max_pages

    def discover(self) -> list[Candidate]:
        html = self._fetcher.get(self.url)
        links = clean.discover_links(html, self.url, self.link_pattern)
        if len(links) > self._max_pages:
            # Never truncate silently — a capped crawl must not look complete.
            print(f"[events] {self.name}: {len(links)} links, "
                  f"cap of {self._max_pages} applied — {len(links) - self._max_pages} skipped")
            links = links[:self._max_pages]
        return [Candidate(uid=u, url=u, timezone=self.timezone) for u in links]
