from datetime import datetime, timezone
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from followup_agent.models import AppRow, Draft
from followup_agent import graph as graph_mod

APP = AppRow(id=1, user_id=1, company="Acme", role="Eng", status=0,
             applied_at=datetime(2026, 6, 10, tzinfo=timezone.utc))


def build(send_calls, warranted=True):
    def assess_fn(app):
        return Draft(warranted=warranted, reason="stale", subject="Hi", body="Body")

    def send_fn(*, to, subject, body):
        send_calls.append((to, subject, body))

    return graph_mod.build_graph(MemorySaver(), assess_fn=assess_fn, send_fn=send_fn)


def run_to_interrupt(g, app):
    cfg = {"configurable": {"thread_id": f"t-{app.id}"}}
    state = g.invoke({"app": app.__dict__}, cfg)
    return state, cfg


def test_not_warranted_ends_without_interrupt():
    sends = []
    g = build(sends, warranted=False)
    state, _ = run_to_interrupt(g, APP)
    assert state.get("warranted") is False
    assert sends == []


def test_warranted_interrupts_then_approve_sends():
    sends = []
    g = build(sends)
    _, cfg = run_to_interrupt(g, APP)
    # graph is paused at human_review; resume with approval
    g.invoke(Command(resume={"decision": "approve", "recipient_email": "r@x.com",
                             "subject": "Hi", "body": "Body"}), cfg)
    assert sends == [("r@x.com", "Hi", "Body")]


def test_warranted_interrupts_then_reject_does_not_send():
    sends = []
    g = build(sends)
    _, cfg = run_to_interrupt(g, APP)
    g.invoke(Command(resume={"decision": "reject"}), cfg)
    assert sends == []
