from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from followup_agent import auth, db, llm
from followup_agent.config import Settings


class TextBody(BaseModel):
    text: str


def create_ai_router(settings: Settings, conn_factory) -> APIRouter:
    router = APIRouter(prefix="/ai")

    def require_user(authorization: Optional[str]) -> int:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "missing bearer token")
        try:
            return auth.user_id_from_token(authorization[7:], settings)
        except auth.AuthError:
            raise HTTPException(401, "invalid token")

    @router.post("/extract")
    def extract(body: TextBody,
                authorization: Optional[str] = Header(default=None)):
        require_user(authorization)
        try:
            return llm.extract(body.text, settings)
        except Exception:
            raise HTTPException(502, "AI unavailable")

    @router.put("/resume")
    def put_resume(body: TextBody,
                   authorization: Optional[str] = Header(default=None)):
        uid = require_user(authorization)
        conn = conn_factory()
        try:
            db.upsert_resume(conn, uid, body.text)
            conn.commit()
            return {"ok": True}
        finally:
            conn.close()

    @router.get("/resume")
    def get_resume(authorization: Optional[str] = Header(default=None)):
        uid = require_user(authorization)
        conn = conn_factory()
        try:
            return {"text": db.get_resume(conn, uid) or ""}
        finally:
            conn.close()

    @router.put("/apps/{app_id}/jd")
    def put_jd(app_id: int, body: TextBody,
               authorization: Optional[str] = Header(default=None)):
        uid = require_user(authorization)
        conn = conn_factory()
        try:
            db.upsert_jd(conn, app_id, uid, body.text)
            conn.commit()
            return {"ok": True}
        finally:
            conn.close()

    def _load_resume_and_jd(conn, app_id: int, uid: int):
        resume = db.get_resume(conn, uid)
        if not resume:
            raise HTTPException(409, "no résumé on file")
        row = db.get_app_ai(conn, app_id, uid)
        if row is None:
            raise HTTPException(409, "no job description stored for this application")
        return resume, row

    @router.post("/match/{app_id}")
    def match(app_id: int, refresh: bool = False,
              authorization: Optional[str] = Header(default=None)):
        uid = require_user(authorization)
        conn = conn_factory()
        try:
            resume, row = _load_resume_and_jd(conn, app_id, uid)
            if row["match_json"] and not refresh:
                return row["match_json"]
            try:
                result = llm.match(resume, row["jd_text"], settings)
            except Exception:
                raise HTTPException(502, "AI unavailable")
            db.save_match(conn, app_id, uid, result.model_dump())
            conn.commit()
            return result
        finally:
            conn.close()

    @router.post("/optimize/{app_id}")
    def optimize(app_id: int, refresh: bool = False,
                 authorization: Optional[str] = Header(default=None)):
        uid = require_user(authorization)
        conn = conn_factory()
        try:
            resume, row = _load_resume_and_jd(conn, app_id, uid)
            if row["optimized_resume"] and not refresh:
                return {"optimized_resume": row["optimized_resume"]}
            try:
                result = llm.optimize(resume, row["jd_text"], settings)
            except Exception:
                raise HTTPException(502, "AI unavailable")
            db.save_optimized(conn, app_id, uid, result.optimized_resume)
            conn.commit()
            return {"optimized_resume": result.optimized_resume}
        finally:
            conn.close()

    return router
