from followup_agent import mailer
from followup_agent.config import Settings


def make_settings():
    return Settings(database_url="", openrouter_api_key="", openrouter_model="",
                    jwt_signing_key="", jwt_issuer="", jwt_audience="",
                    smtp_host="smtp.test", smtp_port=587, smtp_user="me@test",
                    smtp_password="pw", smtp_from="me@test", followup_age_days=7,
                    client_origin="http://localhost:3000")


def test_send_email_uses_smtp(monkeypatch):
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port): sent["addr"] = (host, port)
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self): sent["tls"] = True
        def login(self, u, p): sent["login"] = (u, p)
        def send_message(self, msg): sent["msg"] = msg

    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)
    mailer.send_email(make_settings(), to="r@x.com", subject="Hi", body="Body")

    assert sent["addr"] == ("smtp.test", 587)
    assert sent["tls"] is True
    assert sent["login"] == ("me@test", "pw")
    assert sent["msg"]["To"] == "r@x.com"
    assert sent["msg"]["Subject"] == "Hi"
