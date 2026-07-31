import base64
from followup_agent import gmail


def _b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode()


def test_parse_message_plain_body():
    raw = {
        "id": "m1",
        "payload": {
            "headers": [
                {"name": "From", "value": "Jobs <jobs@acme.com>"},
                {"name": "Subject", "value": "Backend Engineer"},
            ],
            "mimeType": "text/plain",
            "body": {"data": _b64("Apply now at https://acme.com/1")},
        },
    }
    email = gmail.parse_message(raw)
    assert email.message_id == "m1"
    assert email.sender == "Jobs <jobs@acme.com>"
    assert email.subject == "Backend Engineer"
    assert "Apply now" in email.body


def test_parse_message_multipart_prefers_text_plain():
    raw = {
        "id": "m2",
        "payload": {
            "headers": [
                {"name": "From", "value": "a@b.com"},
                {"name": "Subject", "value": "Role"},
            ],
            "mimeType": "multipart/alternative",
            "parts": [
                {"mimeType": "text/html", "body": {"data": _b64("<b>hi</b>")}},
                {"mimeType": "text/plain", "body": {"data": _b64("plain wins")}},
            ],
        },
    }
    email = gmail.parse_message(raw)
    assert email.body == "plain wins"


def test_parse_message_missing_headers_defaults_empty():
    raw = {"id": "m3", "payload": {"headers": [], "body": {}}}
    email = gmail.parse_message(raw)
    assert email.message_id == "m3"
    assert email.sender == "" and email.subject == "" and email.body == ""


def test_parse_message_html_only_falls_back_to_body():
    raw = {
        "id": "m4",
        "payload": {
            "headers": [{"name": "From", "value": "ats@x.com"}],
            "mimeType": "text/html",
            "body": {"data": _b64("<p>Backend Engineer role</p>")},
        },
    }
    email = gmail.parse_message(raw)
    assert "Backend Engineer role" in email.body


def test_decode_handles_unpadded_base64():
    # Gmail may omit '=' padding; parse must not raise.
    raw_b64 = base64.urlsafe_b64encode(b"hello world").decode().rstrip("=")
    raw = {
        "id": "m5",
        "payload": {"headers": [], "mimeType": "text/plain",
                    "body": {"data": raw_b64}},
    }
    email = gmail.parse_message(raw)
    assert email.body == "hello world"
