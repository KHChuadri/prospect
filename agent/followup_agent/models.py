from dataclasses import dataclass
from datetime import datetime
from typing import Optional, TypedDict

from pydantic import BaseModel

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
