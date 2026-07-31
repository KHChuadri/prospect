from followup_agent import llm
from followup_agent.models import ParsedEmail, RecommendationExtract


class _FakeStructured:
    def __init__(self, result):
        self._result = result
    def invoke(self, messages):
        # capture what the prompt contained for assertion
        _FakeStructured.last_messages = messages
        return self._result


def test_extract_recommendation_passes_email_to_llm(monkeypatch):
    expected = RecommendationExtract(
        is_job=True, company="Acme", role="Backend Engineer",
        location="Remote", url="https://jobs.acme.com/123",
    )

    class _FakeChat:
        def with_structured_output(self, model):
            assert model is RecommendationExtract
            return _FakeStructured(expected)

    monkeypatch.setattr(llm, "_chat", lambda settings: _FakeChat())

    email = ParsedEmail(
        message_id="m1", sender="jobs@acme.com",
        subject="New role: Backend Engineer",
        body="Acme is hiring a Backend Engineer in Remote. Apply: https://jobs.acme.com/123",
    )
    result = llm.extract_recommendation(email, settings=None)

    assert result == expected
    blob = " ".join(m["content"] for m in _FakeStructured.last_messages)
    assert "Backend Engineer" in blob and "jobs@acme.com" in blob
