from datetime import datetime, timedelta, timezone
from followup_agent.models import AppRow
from followup_agent.rules import eligible_apps

NOW = datetime(2026, 6, 26, tzinfo=timezone.utc)


def app(id, status, days_ago):
    return AppRow(
        id=id, user_id=1, company="Acme", role="Eng",
        status=status, applied_at=NOW - timedelta(days=days_ago),
    )


def test_includes_stale_applied_and_screening():
    apps = [app(1, 0, 10), app(2, 1, 8)]
    assert {a.id for a in eligible_apps(apps, set(), NOW, 7)} == {1, 2}


def test_excludes_recent():
    assert eligible_apps([app(1, 0, 3)], set(), NOW, 7) == []


def test_excludes_ineligible_status():
    # 2=Interviewing 3=Offer 4=Rejected 5=Withdrawn
    apps = [app(1, 2, 30), app(2, 3, 30), app(3, 4, 30), app(4, 5, 30)]
    assert eligible_apps(apps, set(), NOW, 7) == []


def test_excludes_apps_with_existing_followup():
    assert eligible_apps([app(1, 0, 30)], {1}, NOW, 7) == []


def test_boundary_exactly_threshold_is_eligible():
    assert len(eligible_apps([app(1, 0, 7)], set(), NOW, 7)) == 1
