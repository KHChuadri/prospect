from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langgraph.types import Command
from followup_agent import auth, db, ai
from followup_agent.config import Settings


class ApproveBody(BaseModel):
    recipient_email: str
    subject: Optional[str] = None
    body: Optional[str] = None


class AcceptRecommendationBody(BaseModel):
    application_id: int


def create_app(settings: Settings, conn_factory, graph) -> FastAPI:
    app = FastAPI(title="Follow-up Agent")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.client_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(ai.create_ai_router(settings, conn_factory))

    def require_user(authorization: Optional[str]) -> int:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "missing bearer token")
        try:
            return auth.user_id_from_token(authorization[7:], settings)
        except auth.AuthError:
            raise HTTPException(401, "invalid token")

    @app.get("/follow-ups")
    def list_follow_ups(status: str = "pending",
                        authorization: Optional[str] = Header(default=None)):
        uid = require_user(authorization)
        conn = conn_factory()
        try:
            return db.list_follow_ups(conn, uid, status)
        finally:
            conn.close()

    @app.post("/follow-ups/{follow_up_id}/approve")
    def approve(follow_up_id: int, body: ApproveBody,
                authorization: Optional[str] = Header(default=None)):
        uid = require_user(authorization)
        conn = conn_factory()
        try:
            # FOR UPDATE: hold a row lock for the whole transaction so a second
            # concurrent approve blocks here, then reads status='sent' -> 409.
            row = db.get_follow_up(conn, follow_up_id, uid, for_update=True)
            if row is None:
                raise HTTPException(404, "not found")
            if row["status"] != "pending":
                raise HTTPException(409, "follow-up is not pending")
            cfg = {"configurable": {"thread_id": row["thread_id"]}}
            subject = body.subject or row["draft_subject"]
            text = body.body or row["draft_body"]
            try:
                graph.invoke(Command(resume={
                    "decision": "approve",
                    "recipient_email": body.recipient_email,
                    "subject": subject, "body": text,
                }), cfg)
            except Exception as e:  # send failed inside the graph
                db.update_follow_up(conn, follow_up_id, error=str(e))
                conn.commit()
                raise HTTPException(502, "send failed")
            db.update_follow_up(
                conn, follow_up_id, status="sent",
                recipient_email=body.recipient_email,
                draft_subject=subject, draft_body=text,
                decided_at=datetime.now(timezone.utc),
                sent_at=datetime.now(timezone.utc), error=None,
            )
            conn.commit()
            return db.get_follow_up(conn, follow_up_id, uid)
        finally:
            conn.close()

    @app.post("/follow-ups/{follow_up_id}/reject")
    def reject(follow_up_id: int,
               authorization: Optional[str] = Header(default=None)):
        uid = require_user(authorization)
        conn = conn_factory()
        try:
            row = db.get_follow_up(conn, follow_up_id, uid)
            if row is None:
                raise HTTPException(404, "not found")
            cfg = {"configurable": {"thread_id": row["thread_id"]}}
            graph.invoke(Command(resume={"decision": "reject"}), cfg)
            db.update_follow_up(conn, follow_up_id, status="rejected",
                                decided_at=datetime.now(timezone.utc))
            conn.commit()
            return db.get_follow_up(conn, follow_up_id, uid)
        finally:
            conn.close()

    @app.get("/recommendations")
    def list_recommendations(status: str = "pending",
                             authorization: Optional[str] = Header(default=None)):
        uid = require_user(authorization)
        conn = conn_factory()
        try:
            return db.list_recommendations(conn, uid, status)
        finally:
            conn.close()

    @app.post("/recommendations/{rec_id}/accept")
    def accept_recommendation(rec_id: int, body: AcceptRecommendationBody,
                              authorization: Optional[str] = Header(default=None)):
        uid = require_user(authorization)
        conn = conn_factory()
        try:
            row = db.get_recommendation(conn, rec_id, uid, for_update=True)
            if row is None:
                raise HTTPException(404, "not found")
            if row["status"] == "accepted":
                return row                      # idempotent
            if row["status"] != "pending":
                raise HTTPException(409, "recommendation is not pending")
            db.update_recommendation(
                conn, rec_id, status="accepted",
                accepted_application_id=body.application_id,
                decided_at=datetime.now(timezone.utc))
            conn.commit()
            return db.get_recommendation(conn, rec_id, uid)
        finally:
            conn.close()

    @app.post("/recommendations/{rec_id}/dismiss")
    def dismiss_recommendation(rec_id: int,
                               authorization: Optional[str] = Header(default=None)):
        uid = require_user(authorization)
        conn = conn_factory()
        try:
            row = db.get_recommendation(conn, rec_id, uid, for_update=True)
            if row is None:
                raise HTTPException(404, "not found")
            db.update_recommendation(conn, rec_id, status="dismissed",
                                     decided_at=datetime.now(timezone.utc))
            conn.commit()
            return db.get_recommendation(conn, rec_id, uid)
        finally:
            conn.close()

    def _decide(event_id: int, status: str, authorization: Optional[str]):
        uid = require_user(authorization)
        conn = conn_factory()
        try:
            if db.get_event(conn, event_id) is None:
                raise HTTPException(404, "not found")
            db.set_event_decision(conn, uid, event_id, status)
            conn.commit()
            return db.get_event(conn, event_id)
        finally:
            conn.close()

    @app.get("/events")
    def list_events(saved: bool = False,
                    authorization: Optional[str] = Header(default=None)):
        uid = require_user(authorization)
        conn = conn_factory()
        try:
            return db.list_events(conn, uid, saved=saved)
        finally:
            conn.close()

    @app.post("/events/{event_id}/interested")
    def mark_interested(event_id: int,
                        authorization: Optional[str] = Header(default=None)):
        return _decide(event_id, "interested", authorization)

    @app.post("/events/{event_id}/dismiss")
    def dismiss_event(event_id: int,
                      authorization: Optional[str] = Header(default=None)):
        return _decide(event_id, "dismissed", authorization)

    @app.delete("/events/{event_id}/decision")
    def undo_event_decision(event_id: int,
                            authorization: Optional[str] = Header(default=None)):
        uid = require_user(authorization)
        conn = conn_factory()
        try:
            if db.get_event(conn, event_id) is None:
                raise HTTPException(404, "not found")
            db.clear_event_decision(conn, uid, event_id)
            conn.commit()
            return db.get_event(conn, event_id)
        finally:
            conn.close()

    return app
