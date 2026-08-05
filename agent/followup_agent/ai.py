import uuid
from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from followup_agent import auth, db, llm, pdf, storage
from followup_agent.config import Settings

MAX_RESUME_BYTES = 5 * 1024 * 1024
PDF_CONTENT_TYPE = "application/pdf"


class TextBody(BaseModel):
    text: str


class UploadUrlBody(BaseModel):
    filename: str
    content_type: str
    size: int


class IngestBody(BaseModel):
    key: str
    filename: str


def _key_prefix(user_id: int) -> str:
    return f"resumes/{user_id}/"


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
            previous = db.get_resume_row(conn, uid)
            db.upsert_resume(conn, uid, body.text)
            conn.commit()
        finally:
            conn.close()
        _discard_stored_file((previous or {}).get("file_key"))
        return {"ok": True}

    @router.get("/resume")
    def get_resume(authorization: Optional[str] = Header(default=None)):
        uid = require_user(authorization)
        conn = conn_factory()
        try:
            row = db.get_resume_row(conn, uid)
        finally:
            conn.close()
        if row is None:
            return {"text": "", "profile": None,
                    "file_name": None, "updated_at": None}
        return {"text": row["text"] or "", "profile": row["parsed_json"],
                "file_name": row["file_name"], "updated_at": row["updated_at"]}

    def _discard_stored_file(key: Optional[str]) -> None:
        """Best-effort delete of a superseded PDF.

        Deliberately swallows failures: the database is already consistent by
        this point, and an object left in a bucket with 10 GB of headroom is
        not worth failing the user's request over.
        """
        if not key or not storage.is_configured(settings):
            return
        try:
            storage.delete_object(settings, key)
        except Exception:
            pass

    @router.post("/resume/upload-url")
    def resume_upload_url(body: UploadUrlBody,
                          authorization: Optional[str] = Header(default=None)):
        uid = require_user(authorization)
        if body.content_type != PDF_CONTENT_TYPE:
            raise HTTPException(400, "only PDF files are accepted")
        if body.size <= 0 or body.size > MAX_RESUME_BYTES:
            raise HTTPException(400, "PDF must be no larger than 5 MB")
        if not storage.is_configured(settings):
            raise HTTPException(503, "résumé upload is not configured")
        # The user id in the key is what makes the ingest check below
        # meaningful — a presigned URL cannot be redirected at someone else.
        key = f"{_key_prefix(uid)}{uuid.uuid4().hex}.pdf"
        try:
            url = storage.presign_put(settings, key, PDF_CONTENT_TYPE)
        except Exception:
            raise HTTPException(502, "storage unavailable")
        return {"key": key, "url": url}

    @router.post("/resume/ingest")
    def resume_ingest(body: IngestBody,
                      authorization: Optional[str] = Header(default=None)):
        uid = require_user(authorization)
        if not body.key.startswith(_key_prefix(uid)):
            raise HTTPException(403, "that file does not belong to you")
        if not storage.is_configured(settings):
            raise HTTPException(503, "résumé upload is not configured")

        try:
            data = storage.get_object(settings, body.key)
        except storage.ObjectNotFound:
            raise HTTPException(404, "uploaded file not found")
        except Exception:
            raise HTTPException(502, "storage unavailable")

        try:
            text = pdf.extract_text(data)
        except pdf.EncryptedPdfError:
            raise HTTPException(422, "this PDF is password-protected")
        except pdf.NoTextLayerError:
            raise HTTPException(
                422, "this looks like a scanned image — paste the text instead")
        except pdf.PdfError:
            raise HTTPException(422, "could not read this PDF")

        profile, warning = None, None
        try:
            profile = llm.parse_resume(text, settings).model_dump()
        except Exception:
            # A flaky LLM should not cost the user a successful upload.
            warning = "text extracted, but automatic parsing failed"

        conn = conn_factory()
        try:
            previous = db.get_resume_row(conn, uid)
            db.upsert_resume_file(conn, uid, text=text, parsed=profile,
                                  file_key=body.key, file_name=body.filename)
            conn.commit()
        finally:
            conn.close()

        old_key = (previous or {}).get("file_key")
        if old_key != body.key:
            _discard_stored_file(old_key)
        return {"text": text, "profile": profile, "warning": warning}

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
