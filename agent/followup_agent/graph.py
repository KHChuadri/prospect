from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from followup_agent.models import AppRow, FollowUpState


def build_graph(checkpointer, *, assess_fn, send_fn):
    def assess(state: FollowUpState) -> FollowUpState:
        app_data = state.get("app")
        assert app_data is not None, "assess reached without app in state"
        app = AppRow(**app_data)
        draft = assess_fn(app)
        return {
            "warranted": draft.warranted,
            "reason": draft.reason,
            "draft_subject": draft.subject,
            "draft_body": draft.body,
        }

    def route_after_assess(state: FollowUpState) -> str:
        return "human_review" if state.get("warranted") else END

    def human_review(state: FollowUpState) -> FollowUpState:
        decision = interrupt({
            "subject": state.get("draft_subject"),
            "body": state.get("draft_body"),
            "reason": state.get("reason"),
        })
        return {
            "decision": decision.get("decision"),
            "recipient_email": decision.get("recipient_email"),
            "draft_subject": decision.get("subject", state.get("draft_subject")),
            "draft_body": decision.get("body", state.get("draft_body")),
        }

    def route_after_review(state: FollowUpState) -> str:
        return "send" if state.get("decision") == "approve" else END

    def send(state: FollowUpState) -> FollowUpState:
        to = state.get("recipient_email")
        subject = state.get("draft_subject")
        body = state.get("draft_body")
        assert to and subject and body, "send reached without approved draft fields"
        send_fn(to=to, subject=subject, body=body)
        return {}

    builder = StateGraph(FollowUpState)
    builder.add_node("assess", assess)
    builder.add_node("human_review", human_review)
    builder.add_node("send", send)
    builder.add_edge(START, "assess")
    builder.add_conditional_edges("assess", route_after_assess,
                                  {"human_review": "human_review", END: END})
    builder.add_conditional_edges("human_review", route_after_review,
                                  {"send": "send", END: END})
    builder.add_edge("send", END)
    return builder.compile(checkpointer=checkpointer)
