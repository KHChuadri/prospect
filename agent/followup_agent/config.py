import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load agent/.env once at import so callers never need to `source .env`.
# override=False: real environment vars and test monkeypatches still win.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    database_url: str
    openrouter_api_key: str
    openrouter_model: str
    jwt_signing_key: str
    jwt_issuer: str
    jwt_audience: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_from: str
    followup_age_days: int
    client_origin: str
    # Provider-agnostic LLM endpoint (OpenAI-compatible). Defaults keep
    # OpenRouter working; override LLM_BASE_URL/LLM_API_KEY/LLM_MODEL in .env
    # to point at Groq, Gemini, etc. without code changes.
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""
    llm_model: str = ""
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_refresh_token: str = ""
    gmail_label: str = "job-alerts"
    reco_user_id: int = 0
    reco_poll_minutes: int = 15


def load_settings() -> Settings:
    return Settings(
        database_url=os.environ["DATABASE_URL"],
        openrouter_api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        openrouter_model=os.environ.get("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet"),
        jwt_signing_key=os.environ["JWT_SIGNING_KEY"],
        jwt_issuer=os.environ.get("JWT_ISSUER", "JobApplicationTracker"),
        jwt_audience=os.environ.get("JWT_AUDIENCE", "JobApplicationTrackerUsers"),
        smtp_host=os.environ.get("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.environ.get("SMTP_PORT", "587")),
        smtp_user=os.environ.get("SMTP_USER", ""),
        smtp_password=os.environ.get("SMTP_PASSWORD", ""),
        smtp_from=os.environ.get("SMTP_FROM", ""),
        followup_age_days=int(os.environ.get("FOLLOWUP_AGE_DAYS", "7")),
        client_origin=os.environ.get("CLIENT_ORIGIN", "http://localhost:3000"),
        llm_base_url=os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1"),
        llm_api_key=os.environ.get("LLM_API_KEY") or os.environ.get("OPENROUTER_API_KEY", ""),
        llm_model=os.environ.get("LLM_MODEL") or os.environ.get("OPENROUTER_MODEL", "anthropic/claude-haiku-4.5"),
        gmail_client_id=os.environ.get("GMAIL_CLIENT_ID", ""),
        gmail_client_secret=os.environ.get("GMAIL_CLIENT_SECRET", ""),
        gmail_refresh_token=os.environ.get("GMAIL_REFRESH_TOKEN", ""),
        gmail_label=os.environ.get("GMAIL_LABEL", "job-alerts"),
        reco_user_id=int(os.environ.get("RECO_USER_ID", "0")),
        reco_poll_minutes=int(os.environ.get("RECO_POLL_MINUTES", "15")),
    )
