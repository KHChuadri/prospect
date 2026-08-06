from datetime import datetime, timezone
from followup_agent.models import AppRow, Draft
from followup_agent import llm


def test_assess_and_draft_maps_structured_output(monkeypatch):
    captured = {}

    class FakeStructured:
        def invoke(self, prompt):
            captured["prompt"] = prompt
            return Draft(warranted=True, reason="10 days, no reply",
                         subject="Following up", body="Hi team, ...")

    class FakeChat:
        def __init__(self, **kw): captured["kw"] = kw
        def with_structured_output(self, schema): return FakeStructured()

    monkeypatch.setattr(llm, "ChatOpenAI", FakeChat)

    from followup_agent.config import Settings
    s = Settings(database_url="", openrouter_api_key="k", openrouter_model="m",
                 jwt_signing_key="", jwt_issuer="", jwt_audience="",
                 smtp_host="", smtp_port=587, smtp_user="", smtp_password="",
                 smtp_from="", followup_age_days=7,
                 client_origin="http://localhost:3000")
    app = AppRow(id=1, user_id=1, company="Acme", role="Engineer",
                 status=0, applied_at=datetime(2026, 6, 16, tzinfo=timezone.utc))

    result = llm.assess_and_draft(app, s)
    assert result.warranted is True
    assert "Acme" in str(captured["prompt"])
    assert captured["kw"]["base_url"] == "https://openrouter.ai/api/v1"


def _ai_settings():
    from followup_agent.config import Settings
    return Settings(database_url="", openrouter_api_key="k", openrouter_model="m",
                    jwt_signing_key="", jwt_issuer="", jwt_audience="",
                    smtp_host="", smtp_port=587, smtp_user="", smtp_password="",
                    smtp_from="", followup_age_days=7,
                    client_origin="http://localhost:3000")


def test_extract_maps_structured_output(monkeypatch):
    from followup_agent.models import Extraction
    captured = {}

    class FakeStructured:
        def invoke(self, prompt):
            captured["prompt"] = prompt
            return Extraction(company="Acme", role="Engineer",
                              requirements=["python"], ok=True)

    class FakeChat:
        def __init__(self, **kw): pass
        def with_structured_output(self, schema): return FakeStructured()

    monkeypatch.setattr(llm, "ChatOpenAI", FakeChat)
    result = llm.extract("Acme is hiring an Engineer ...", _ai_settings())
    assert result.company == "Acme" and result.ok is True
    assert "Acme is hiring" in str(captured["prompt"])


def test_match_maps_structured_output(monkeypatch):
    from followup_agent.models import MatchResult

    class FakeStructured:
        def invoke(self, prompt):
            return MatchResult(score=72, missing=["docker"],
                               matched=["python"], suggestions=["add docker"])

    class FakeChat:
        def __init__(self, **kw): pass
        def with_structured_output(self, schema): return FakeStructured()

    monkeypatch.setattr(llm, "ChatOpenAI", FakeChat)
    result = llm.match("my resume", "the jd", _ai_settings())
    assert result.score == 72 and "docker" in result.missing


def test_parse_resume_maps_structured_output(monkeypatch):
    from followup_agent.models import ResumeEducation, ResumeExperience, ResumeProfile

    captured = {}

    class FakeStructured:
        def invoke(self, prompt):
            captured["prompt"] = prompt
            return ResumeProfile(
                name="Jane Chen",
                email="jane.chen@example.com",
                location="Sydney",
                skills=["Python", "Postgres"],
                experience=[ResumeExperience(
                    company="Acme Corp", title="Senior Engineer",
                    start="2023", end="2026",
                    bullets=["Built the billing pipeline."])],
                education=[ResumeEducation(
                    school="UNSW", degree="BSc Computer Science", year="2022")],
            )

    class FakeChat:
        def __init__(self, **kw): captured["kw"] = kw
        def with_structured_output(self, schema):
            captured["schema"] = schema
            return FakeStructured()

    monkeypatch.setattr(llm, "ChatOpenAI", FakeChat)

    result = llm.parse_resume("Jane Chen\nSenior Engineer at Acme", _ai_settings())

    assert result.name == "Jane Chen"
    assert result.skills == ["Python", "Postgres"]
    assert result.experience[0].company == "Acme Corp"
    assert result.education[0].school == "UNSW"
    assert captured["schema"] is ResumeProfile
    assert "Jane Chen" in str(captured["prompt"])


def test_resume_profile_tolerates_a_sparse_response():
    # Every field defaults, so an LLM that returns almost nothing still
    # validates instead of 500ing the ingest endpoint.
    from followup_agent.models import ResumeProfile

    profile = ResumeProfile()
    assert profile.name == ""
    assert profile.email is None
    assert profile.skills == []
    assert profile.experience == []
