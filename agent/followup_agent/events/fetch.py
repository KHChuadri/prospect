import time
import urllib.robotparser
from typing import Callable, Optional
from urllib.parse import urlparse

import httpx


class FetchError(Exception):
    """Any reason a page could not be retrieved, including robots.txt refusal."""


class Fetcher:
    """Polite HTTP for the crawler. This is the swap point for Playwright.

    Everything here is about being a guest on someone else's server: honour
    robots.txt, say who we are, one request at a time per host with a pause
    between, and never hang. Three sites twice a day is ~40 requests — these
    rules cost nothing and are the difference between being welcome and being
    IP-blocked.
    """

    def __init__(self, user_agent: str, delay_seconds: float = 2.0,
                 timeout: float = 10.0,
                 sleep_fn: Callable[[float], None] = time.sleep,
                 client: Optional[httpx.Client] = None):
        self.user_agent = user_agent
        self.delay_seconds = delay_seconds
        self._sleep = sleep_fn
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(timeout, connect=timeout),
            follow_redirects=True,
        )
        self._robots: dict[str, Optional[urllib.robotparser.RobotFileParser]] = {}
        self._last_request_at: dict[str, float] = {}

    def _robots_for(self, url: str):
        host = urlparse(url).netloc
        if host in self._robots:
            return self._robots[host]
        parsed = urlparse(url)
        rp = None
        try:
            resp = self._client.get(f"{parsed.scheme}://{host}/robots.txt",
                                    headers={"User-Agent": self.user_agent})
            if resp.status_code == 200:
                rp = urllib.robotparser.RobotFileParser()
                rp.parse(resp.text.splitlines())
        except httpx.HTTPError:
            rp = None          # unreachable robots.txt is not a prohibition
        self._robots[host] = rp
        return rp

    def allowed(self, url: str) -> bool:
        rp = self._robots_for(url)
        return True if rp is None else rp.can_fetch(self.user_agent, url)

    def _wait_turn(self, host: str) -> None:
        last = self._last_request_at.get(host)
        if last is not None:
            remaining = self.delay_seconds - (time.monotonic() - last)
            if remaining > 0:
                self._sleep(remaining)
        self._last_request_at[host] = time.monotonic()

    def get(self, url: str) -> str:
        if not self.allowed(url):
            raise FetchError(f"robots.txt disallows {url}")
        self._wait_turn(urlparse(url).netloc)
        try:
            resp = self._client.get(url, headers={"User-Agent": self.user_agent})
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise FetchError(f"{url}: {e}") from e
        return resp.text
