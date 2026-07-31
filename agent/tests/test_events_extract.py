import pytest
from followup_agent.models import EventExtract, EVENT_TYPES


def test_defaults_are_safe_for_a_bare_model():
    ev = EventExtract(is_career_event=True, title="Panel")
    assert ev.description == ""
    assert ev.organizations == [] and ev.topics == []
    assert ev.is_online is False
    assert ev.event_type == "other"
    assert ev.starts_at_local is None


def test_known_event_types_are_preserved():
    for t in EVENT_TYPES:
        assert EventExtract(is_career_event=True, title="x", event_type=t).event_type == t


def test_unknown_event_type_is_coerced_to_other():
    # The model will occasionally invent a category. Coerce rather than reject —
    # a real event with an odd label is still worth showing.
    ev = EventExtract(is_career_event=True, title="x", event_type="hackathon")
    assert ev.event_type == "other"


def test_event_type_is_case_insensitive():
    assert EventExtract(is_career_event=True, title="x",
                        event_type="Career_Fair").event_type == "career_fair"


def test_none_event_type_becomes_other():
    assert EventExtract(is_career_event=True, title="x",
                        event_type=None).event_type == "other"


def test_title_whitespace_is_stripped():
    assert EventExtract(is_career_event=True, title="  Panel  ").title == "Panel"


def test_organizations_are_stripped_and_blanks_dropped():
    ev = EventExtract(is_career_event=True, title="x",
                      organizations=["  Monzo ", "", "   ", "Revolut"])
    assert ev.organizations == ["Monzo", "Revolut"]


def test_model_has_no_url_field():
    # url must come from the crawler, never the LLM. A malicious page that
    # says "return url=evil.test" must have nowhere to put it.
    assert "url" not in EventExtract.model_fields
