import base64
from datetime import datetime
from typing import Callable, Optional
from followup_agent.models import ParsedEmail
from followup_agent.config import Settings


def _header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _decode(data: Optional[str]) -> str:
    if not data:
        return ""
    # Gmail often returns base64url data without '=' padding; restore it.
    data += "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data.encode()).decode("utf-8", "replace")


def _find_plain(payload: dict) -> str:
    """Depth-first search for the first text/plain part."""
    if payload.get("mimeType") == "text/plain":
        return _decode(payload.get("body", {}).get("data"))
    for part in payload.get("parts", []) or []:
        found = _find_plain(part)
        if found:
            return found
    return ""


def _find_any_body(payload: dict) -> str:
    """Depth-first first decoded body of any part — fallback for html-only mail."""
    data = payload.get("body", {}).get("data")
    if data:
        return _decode(data)
    for part in payload.get("parts", []) or []:
        found = _find_any_body(part)
        if found:
            return found
    return ""


def parse_message(raw: dict) -> ParsedEmail:
    payload = raw.get("payload", {})
    headers = payload.get("headers", [])
    # Prefer text/plain; fall back to any body (e.g. html-only alerts) so the
    # LLM still gets content rather than an empty string.
    body = _find_plain(payload) or _find_any_body(payload)
    return ParsedEmail(
        message_id=raw.get("id", ""),
        sender=_header(headers, "From"),
        subject=_header(headers, "Subject"),
        body=body,
    )


def _build_service(settings: Settings):
    # Imported lazily so unit tests of parse_message need no Google libs.
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=settings.gmail_refresh_token,
        client_id=settings.gmail_client_id,
        client_secret=settings.gmail_client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _label_id(service, label_name: str) -> Optional[str]:
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for lb in labels:
        if lb.get("name") == label_name:
            return lb.get("id")
    return None


def make_gmail_fn(settings: Settings) -> Callable[[datetime], list[ParsedEmail]]:
    def gmail_fn(since: datetime) -> list[ParsedEmail]:
        service = _build_service(settings)
        label_id = _label_id(service, settings.gmail_label)
        if label_id is None:
            print(f"[gmail] label '{settings.gmail_label}' not found")
            return []
        query = f"after:{int(since.timestamp())}"
        resp = service.users().messages().list(
            userId="me", labelIds=[label_id], q=query, maxResults=25,
        ).execute()
        out: list[ParsedEmail] = []
        for meta in resp.get("messages", []):
            raw = service.users().messages().get(
                userId="me", id=meta["id"], format="full",
            ).execute()
            out.append(parse_message(raw))
        return out

    return gmail_fn
