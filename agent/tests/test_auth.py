import datetime as dt
import jwt
import pytest
from followup_agent import auth
from followup_agent.config import Settings

NAMEID = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier"


def settings():
    return Settings(database_url="", openrouter_api_key="", openrouter_model="",
                    jwt_signing_key="super-secret-key-at-least-32-chars!!",
                    jwt_issuer="JobApplicationTracker",
                    jwt_audience="JobApplicationTrackerUsers",
                    smtp_host="", smtp_port=587, smtp_user="", smtp_password="",
                    smtp_from="", followup_age_days=7,
                    client_origin="http://localhost:3000")


def make_token(s, **over):
    payload = {
        NAMEID: "42",
        "iss": s.jwt_issuer,
        "aud": s.jwt_audience,
        "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5),
        **over,
    }
    return jwt.encode(payload, s.jwt_signing_key, algorithm="HS256")


def test_valid_token_returns_user_id():
    s = settings()
    assert auth.user_id_from_token(make_token(s), s) == 42


def test_wrong_signature_rejected():
    s = settings()
    bad = jwt.encode({NAMEID: "1", "iss": s.jwt_issuer, "aud": s.jwt_audience,
                      "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5)},
                     "different-key", algorithm="HS256")
    with pytest.raises(auth.AuthError):
        auth.user_id_from_token(bad, s)


def test_wrong_audience_rejected():
    s = settings()
    with pytest.raises(auth.AuthError):
        auth.user_id_from_token(make_token(s, aud="someone-else"), s)


def test_wrong_issuer_rejected():
    s = settings()
    with pytest.raises(auth.AuthError):
        auth.user_id_from_token(make_token(s, iss="untrusted-issuer"), s)


def test_missing_nameid_claim_rejected():
    s = settings()
    token = jwt.encode({"iss": s.jwt_issuer, "aud": s.jwt_audience,
                        "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5)},
                       s.jwt_signing_key, algorithm="HS256")
    with pytest.raises(auth.AuthError):
        auth.user_id_from_token(token, s)
