import re
from urllib.parse import urljoin, urlparse, urlunparse

from selectolax.parser import HTMLParser

# Chrome, navigation and boilerplate carry no event information and would
# otherwise dominate the text sent to the LLM.
_DROP_TAGS = ("script", "style", "nav", "header", "footer", "noscript",
              "svg", "form", "iframe")


def html_to_text(html: str) -> str:
    """Reduce a page to readable text. ~110KB of markup becomes a few KB."""
    if not html:
        return ""
    tree = HTMLParser(html)
    for tag in _DROP_TAGS:
        for node in tree.css(tag):
            node.decompose()
    body = tree.body or tree.root
    if body is None:
        return ""
    text = body.text(separator="\n", strip=True)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _canonical(url: str) -> str:
    """Drop query strings and fragments so ?utm=... isn't a distinct event."""
    p = urlparse(url)
    return urlunparse((p.scheme, p.netloc, p.path.rstrip("/"), "", "", ""))


def discover_links(html: str, base_url: str, link_pattern: str) -> list[str]:
    """Absolute, deduplicated, same-host links whose path contains link_pattern.

    Same-host only: a link out to another domain is a site nobody vetted, and
    fetching it would put an unreviewed host under our User-Agent and IP.
    Order is preserved so crawls are reproducible.
    """
    if not html:
        return []
    base_host = urlparse(base_url).netloc
    seen: set[str] = set()
    out: list[str] = []
    for node in HTMLParser(html).css("a[href]"):
        href = (node.attributes.get("href") or "").strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        absolute = _canonical(urljoin(base_url, href))
        parsed = urlparse(absolute)
        if parsed.netloc != base_host or link_pattern not in parsed.path:
            continue
        if absolute not in seen:
            seen.add(absolute)
            out.append(absolute)
    return out
