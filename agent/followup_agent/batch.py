from datetime import datetime, timezone
from typing import Optional
from followup_agent import db, rules


def run_batch(conn, graph, *, age_days: int, now: Optional[datetime] = None) -> list[int]:
    now = now or datetime.now(timezone.utc)
    candidates = db.fetch_candidate_apps(conn)
    existing = db.existing_followup_app_ids(conn)
    eligible = rules.eligible_apps(candidates, existing, now, age_days)

    created: list[int] = []
    print(f"[batch] {len(eligible)} eligible application(s)")
    for app in eligible:
        thread_id = f"followup-{app.id}-{now:%Y%m%d}"
        cfg = {"configurable": {"thread_id": thread_id}}
        # One flaky LLM call (e.g. a free-provider 429) must not abort the
        # whole batch — log and move on so the rest still get drafted.
        try:
            state = graph.invoke({"app": app.__dict__}, cfg)
        except Exception as e:
            print(f"[batch] skip app {app.id} ({app.company}): {e}")
            continue
        if not state.get("warranted"):
            print(f"[batch] app {app.id} ({app.company}): not warranted")
            continue
        fid = db.create_follow_up(
            conn, app_id=app.id, user_id=app.user_id, thread_id=thread_id,
            subject=state["draft_subject"], body=state["draft_body"],
            reason=state.get("reason", ""),
        )
        print(f"[batch] app {app.id} ({app.company}): drafted -> follow_up {fid}")
        created.append(fid)
    return created
