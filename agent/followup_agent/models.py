from dataclasses import dataclass
from datetime import datetime
from typing import Optional, TypedDict

from pydantic import BaseModel, field_validator

ELIGIBLE_STATUSES = {0, 1}  # Applied, Screening


@dataclass(frozen=True)
class AppRow:
    id: int
    user_id: int
    company: str
    role: str
    status: int
    applied_at: datetime


class Draft(BaseModel):
    warranted: bool
    reason: str
    subject: str
    body: str


class Extraction(BaseModel):
    company: str = ""
    role: str = ""
    location: Optional[str] = None
    salary: Optional[str] = None
    requirements: list[str] = []
    ok: bool = True


class MatchResult(BaseModel):
    score: int
    missing: list[str] = []
    matched: list[str] = []
    suggestions: list[str] = []


class OptimizedResume(BaseModel):
    optimized_resume: str


class FollowUpState(TypedDict, total=False):
    app: dict          # AppRow as dict (LangGraph state must be serializable)
    warranted: bool
    reason: str
    draft_subject: str
    draft_body: str
    decision: Optional[str]        # "approve" | "reject"
    recipient_email: Optional[str]


@dataclass(frozen=True)
class ParsedEmail:
    message_id: str
    sender: str
    subject: str
    body: str


class RecommendationExtract(BaseModel):
    is_job: bool = False
    company: str = ""
    role: str = ""
    location: Optional[str] = None
    url: Optional[str] = None


EVENT_TYPES = {"networking", "panel", "career_fair", "workshop", "talk", "other"}


class EventExtract(BaseModel):
    """The only interface between LLM output and the events pipeline.

    Note the absence of `url`: it always comes from the crawler, never the
    model. A crawled page is text a stranger wrote, so a page instructing the
    model to emit a phishing link must have no field to put it in.

    Times are LOCAL, exactly as printed on the page. Conversion to UTC happens
    in the pipeline using the source's declared timezone — the page itself
    rarely states one.
    """
    is_career_event: bool = False
    title: str = ""
    description: str = ""
    starts_at_local: Optional[str] = None
    ends_at_local: Optional[str] = None
    location: Optional[str] = None
    is_online: bool = False
    organizations: list[str] = []
    topics: list[str] = []
    event_type: str = "other"

    @field_validator("event_type", mode="before")
    @classmethod
    def _coerce_event_type(cls, v):
        # The model will occasionally invent a category. An event with an odd
        # label is still a real event, so coerce rather than reject.
        if not isinstance(v, str):
            return "other"
        v = v.strip().lower()
        return v if v in EVENT_TYPES else "other"

    @field_validator("title", "description", mode="before")
    @classmethod
    def _strip_text(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("organizations", "topics", mode="before")
    @classmethod
    def _clean_list(cls, v):
        if not isinstance(v, list):
            return []
        return [s.strip() for s in v if isinstance(s, str) and s.strip()]
