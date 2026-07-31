from langchain_openai import ChatOpenAI
from followup_agent.models import (
    AppRow, Draft, Extraction, MatchResult, OptimizedResume,
    ParsedEmail, RecommendationExtract,
)
from followup_agent.config import Settings

SYSTEM = (
    "You are an assistant that helps a job seeker decide whether to send a "
    "polite follow-up email about a pending job application, and drafts it. "
    "Only mark it warranted if a brief, professional nudge is appropriate. "
    "Keep the body under 150 words, courteous, specific to the role/company. "
    "Do not invent facts (interview dates, names) that were not provided."
)


def _prompt(app: AppRow) -> str:
    return (
        f"Company: {app.company}\nRole: {app.role}\n"
        f"Applied on: {app.applied_at.date().isoformat()}\n"
        f"Current status: {'Applied' if app.status == 0 else 'Screening'}\n\n"
        "Decide if a follow-up is warranted and draft subject + body."
    )


def _chat(settings: Settings) -> ChatOpenAI:
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=0.4,
        timeout=60,
        max_retries=2,
    )


def assess_and_draft(app: AppRow, settings: Settings) -> Draft:
    structured = _chat(settings).with_structured_output(Draft)
    return structured.invoke(
        [{"role": "system", "content": SYSTEM},
         {"role": "user", "content": _prompt(app)}]
    )


EXTRACT_SYSTEM = (
    "You extract structured fields from a pasted job posting. Return the "
    "company, role/title, location and salary if present (else null), and a "
    "short list of key requirements. Set ok=false ONLY if the text is not a "
    "job posting at all. Do not invent details that are not in the text."
)

MATCH_SYSTEM = (
    "You compare a candidate's résumé against a job description. Return a fit "
    "score from 0 to 100, the important skills/keywords the JD wants that are "
    "missing from the résumé, the ones already matched, and up to three "
    "concrete tailoring suggestions. Judge only on the text provided."
)

# Fixed résumé optimization instruction — not user-editable (see spec).
OPTIMIZE_PROMPT = (
    "Rewrite the candidate's résumé so it is tailored to the job description. "
    "Reorder and rephrase real experience to surface what the JD values, weave "
    "in the JD's language where it genuinely applies, and keep it truthful — "
    "never fabricate employers, dates, titles, or skills the résumé lacks. "
    "Return the full rewritten résumé as plain text."
)


def extract(text: str, settings: Settings) -> Extraction:
    structured = _chat(settings).with_structured_output(Extraction)
    return structured.invoke(
        [{"role": "system", "content": EXTRACT_SYSTEM},
         {"role": "user", "content": text}]
    )


def match(resume_text: str, jd_text: str, settings: Settings) -> MatchResult:
    structured = _chat(settings).with_structured_output(MatchResult)
    return structured.invoke(
        [{"role": "system", "content": MATCH_SYSTEM},
         {"role": "user", "content": f"RÉSUMÉ:\n{resume_text}\n\nJOB DESCRIPTION:\n{jd_text}"}]
    )


def optimize(resume_text: str, jd_text: str, settings: Settings) -> OptimizedResume:
    structured = _chat(settings).with_structured_output(OptimizedResume)
    return structured.invoke(
        [{"role": "system", "content": OPTIMIZE_PROMPT},
         {"role": "user", "content": f"RÉSUMÉ:\n{resume_text}\n\nJOB DESCRIPTION:\n{jd_text}"}]
    )


RECO_SYSTEM = (
    "You read a single email that may be a job alert / posting and extract one "
    "job opportunity. Set is_job=true ONLY if the email advertises a specific "
    "job to apply to. Return the hiring company, the role/title, the location "
    "if present (else null), and the direct application/posting URL if present "
    "(else null). If it is not a job posting (newsletter, personal mail, "
    "receipt), set is_job=false and leave the other fields empty. Do NOT invent "
    "a company, role, or URL that is not in the email."
)


def extract_recommendation(email: ParsedEmail, settings: Settings) -> RecommendationExtract:
    structured = _chat(settings).with_structured_output(RecommendationExtract)
    content = (
        f"From: {email.sender}\nSubject: {email.subject}\n\n{email.body}"
    )
    return structured.invoke(
        [{"role": "system", "content": RECO_SYSTEM},
         {"role": "user", "content": content}]
    )
