from datetime import datetime
from followup_agent.models import AppRow, ELIGIBLE_STATUSES


def eligible_apps(
    apps: list[AppRow],
    existing_followup_app_ids: set[int],
    now: datetime,
    age_days: int,
) -> list[AppRow]:
    out = []
    for a in apps:
        if a.status not in ELIGIBLE_STATUSES:
            continue
        if a.id in existing_followup_app_ids:
            continue
        if (now - a.applied_at).days < age_days:
            continue
        out.append(a)
    return out
