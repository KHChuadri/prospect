from pathlib import Path

import pytest
from followup_agent.jobs.sources import JobPosting, load_search_configs

SHIPPED_YAML = Path(__file__).resolve().parents[1] / "job_sources.yaml"


def _write(tmp_path, body):
    p = tmp_path / "jobs.yaml"
    p.write_text(body)
    return p


def test_loads_linkedin_config(tmp_path):
    p = _write(tmp_path,
        "sources:\n"
        "  - name: linkedin-frontend-syd\n"
        "    type: linkedin\n"
        "    query: frontend engineer\n"
        "    location: Sydney, New South Wales, Australia\n"
        "    jobage: 14\n")
    cfgs = load_search_configs(p)
    assert len(cfgs) == 1
    assert cfgs[0]["name"] == "linkedin-frontend-syd"
    assert cfgs[0]["jobage"] == 14


def test_loads_greenhouse_and_lever_configs(tmp_path):
    p = _write(tmp_path,
        "sources:\n"
        "  - name: greenhouse-stripe\n"
        "    type: greenhouse\n"
        "    slug: stripe\n"
        "  - name: lever-palantir\n"
        "    type: lever\n"
        "    slug: palantir\n")
    cfgs = load_search_configs(p)
    assert [c["type"] for c in cfgs] == ["greenhouse", "lever"]


def test_missing_config_file_returns_empty_list(tmp_path):
    assert load_search_configs(tmp_path / "nope.yaml") == []


def test_linkedin_config_missing_location_raises(tmp_path):
    p = _write(tmp_path,
        "sources:\n"
        "  - name: broken\n"
        "    type: linkedin\n"
        "    query: engineer\n")
    with pytest.raises(ValueError, match="location"):
        load_search_configs(p)


def test_greenhouse_config_missing_slug_raises(tmp_path):
    p = _write(tmp_path,
        "sources:\n"
        "  - name: broken\n"
        "    type: greenhouse\n")
    with pytest.raises(ValueError, match="slug"):
        load_search_configs(p)


def test_unknown_type_raises(tmp_path):
    p = _write(tmp_path,
        "sources:\n"
        "  - name: broken\n"
        "    type: monster\n")
    with pytest.raises(ValueError, match="monster"):
        load_search_configs(p)


def test_disabled_source_is_dropped_and_reported(tmp_path, capsys):
    p = _write(tmp_path,
        "sources:\n"
        "  - name: greenhouse-stripe\n"
        "    type: greenhouse\n"
        "    slug: stripe\n"
        "  - name: lever-palantir\n"
        "    type: lever\n"
        "    slug: palantir\n"
        "    enabled: false\n")
    cfgs = load_search_configs(p)
    assert [c["name"] for c in cfgs] == ["greenhouse-stripe"]
    # A silently skipped source looks identical to one that found nothing.
    assert "lever-palantir" in capsys.readouterr().out


@pytest.mark.parametrize("literal", ['"false"', '"False"', '"NO"', "'off'"])
def test_quoted_enabled_string_still_disables(tmp_path, capsys, literal):
    # YAML hands back the STRING "false" here, which is truthy in Python, so a
    # bare `is False` left the source running. ARCHITECTURE.md names this toggle
    # as the way to switch off the ToS-violating LinkedIn source in a shared
    # deployment — a quoting typo must not silently re-enable it.
    p = _write(tmp_path,
        "sources:\n"
        "  - name: linkedin-syd\n"
        "    type: linkedin\n"
        "    query: engineer\n"
        "    location: Sydney\n"
        f"    enabled: {literal}\n")
    assert load_search_configs(p) == []
    assert "disabled" in capsys.readouterr().out


@pytest.mark.parametrize("literal", ['"true"', "true", '"yes"', '"falsey"'])
def test_values_that_are_not_negatives_stay_enabled(tmp_path, literal):
    # The matching must be narrow. Only the explicit negative words disable, so
    # a truthy or unrelated value can never accidentally switch a source off.
    p = _write(tmp_path,
        "sources:\n"
        "  - name: greenhouse-stripe\n"
        "    type: greenhouse\n"
        "    slug: stripe\n"
        f"    enabled: {literal}\n")
    assert [c["name"] for c in load_search_configs(p)] == ["greenhouse-stripe"]


def test_missing_enabled_key_means_enabled(tmp_path):
    p = _write(tmp_path,
        "sources:\n"
        "  - name: greenhouse-stripe\n"
        "    type: greenhouse\n"
        "    slug: stripe\n")
    assert len(load_search_configs(p)) == 1


def test_job_posting_defaults():
    jp = JobPosting(uid="linkedin:1", company="Canva", role="Engineer",
                    url="https://ex.test/1")
    assert jp.location is None
    assert jp.posted_at is None


from dataclasses import dataclass

from followup_agent.jobs.sources import build_job_sources
from followup_agent.jobs.sources.greenhouse import GreenhouseSource
from followup_agent.jobs.sources.lever import LeverSource
from followup_agent.jobs.sources.linkedin import LinkedInSource


@dataclass
class FakeSettings:
    jobs_sources_path: str
    jobs_max_per_source: int = 25


def test_build_job_sources_constructs_one_object_per_config(tmp_path):
    p = _write(tmp_path,
        "sources:\n"
        "  - name: linkedin-syd\n"
        "    type: linkedin\n"
        "    query: engineer\n"
        "    location: Sydney\n"
        "  - name: greenhouse-stripe\n"
        "    type: greenhouse\n"
        "    slug: stripe\n"
        "  - name: lever-palantir\n"
        "    type: lever\n"
        "    slug: palantir\n")
    sources = build_job_sources(FakeSettings(str(p)), fetcher=object(),
                                linkedin_client=object())
    assert [s.name for s in sources] == [
        "linkedin-syd", "greenhouse-stripe", "lever-palantir"]


def test_build_job_sources_skips_disabled(tmp_path):
    p = _write(tmp_path,
        "sources:\n"
        "  - name: greenhouse-stripe\n"
        "    type: greenhouse\n"
        "    slug: stripe\n"
        "  - name: lever-palantir\n"
        "    type: lever\n"
        "    slug: palantir\n"
        "    enabled: false\n")
    sources = build_job_sources(FakeSettings(str(p)), fetcher=object(),
                                linkedin_client=object())
    assert [s.name for s in sources] == ["greenhouse-stripe"]


def test_build_job_sources_missing_file_is_empty(tmp_path):
    assert build_job_sources(FakeSettings(str(tmp_path / "nope.yaml")),
                             fetcher=object(), linkedin_client=object()) == []


def test_build_job_sources_uses_correct_class_per_type(tmp_path):
    # Names alone don't prove dispatch: all three classes set
    # self.name = cfg["name"] identically, so a name-only assertion passes
    # even if the type -> class mapping is completely broken.
    p = _write(tmp_path,
        "sources:\n"
        "  - name: linkedin-syd\n"
        "    type: linkedin\n"
        "    query: engineer\n"
        "    location: Sydney\n"
        "  - name: greenhouse-stripe\n"
        "    type: greenhouse\n"
        "    slug: stripe\n"
        "  - name: lever-palantir\n"
        "    type: lever\n"
        "    slug: palantir\n")
    sources = build_job_sources(FakeSettings(str(p)), fetcher=object(),
                                linkedin_client=object())
    assert [type(s) for s in sources] == [
        LinkedInSource, GreenhouseSource, LeverSource]


def test_build_job_sources_propagates_max_results_cap(tmp_path):
    # 7 is deliberately non-default: each source class's own default is 25,
    # so asserting 25 here would pass even if the setting were ignored.
    p = _write(tmp_path,
        "sources:\n"
        "  - name: linkedin-syd\n"
        "    type: linkedin\n"
        "    query: engineer\n"
        "    location: Sydney\n"
        "  - name: greenhouse-stripe\n"
        "    type: greenhouse\n"
        "    slug: stripe\n"
        "  - name: lever-palantir\n"
        "    type: lever\n"
        "    slug: palantir\n")
    sources = build_job_sources(FakeSettings(str(p), jobs_max_per_source=7),
                                fetcher=object(), linkedin_client=object())
    assert [s._max_results for s in sources] == [7, 7, 7]


def test_shipped_yaml_enables_a_robots_clean_source():
    # The first real run of a fresh checkout must not exercise the
    # ToS-violating LinkedIn source alone. This is a property of the shipped
    # config, so it is asserted against the shipped file, not a fixture.
    cfgs = load_search_configs(SHIPPED_YAML)
    types = {c["type"] for c in cfgs}
    assert "greenhouse" in types
    assert "lever" in types
