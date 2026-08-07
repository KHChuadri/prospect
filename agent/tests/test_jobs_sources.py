import pytest
from followup_agent.jobs.sources import JobPosting, load_search_configs


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
