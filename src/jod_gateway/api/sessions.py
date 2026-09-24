from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from jod_gateway.core.session import new
from jod_gateway.core.store import SessionStore

router = APIRouter(prefix="/sessions", tags=["sessions"])

ALLOWED_PROVIDERS = {"chatgpt", "echo"}


class CookieItem(BaseModel):
    name: str
    value: str
    domain: str | None = None
    path: str | None = None
    expires: float | None = None
    http_only: bool | None = None
    secure: bool | None = None


class IngestRequest(BaseModel):
    provider: str
    label: str
    cookies: list[CookieItem]
    derived: dict[str, str] = {}


def _store(request: Request) -> SessionStore:
    return request.app.state.store


@router.post("/ingest")
async def ingest(request: Request, body: IngestRequest):
    if body.provider not in ALLOWED_PROVIDERS:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "message": f"Unsupported provider '{body.provider}'",
                    "code": "unknown_provider",
                }
            },
        )

    cookies = {item.name: item.value for item in body.cookies}
    session = new(body.provider, body.label, cookies, body.derived)
    await _store(request).save(session)
    return session.public_meta()


@router.get("")
async def list_sessions(request: Request):
    return [s.public_meta() for s in await _store(request).list()]


@router.get("/{session_id}")
async def get_session(request: Request, session_id: str):
    session = await _store(request).get(session_id)
    if session is None:
        return JSONResponse(
            status_code=404,
            content={"error": {"message": "Session not found", "code": "session_not_found"}},
        )
    return session.public_meta()


@router.delete("/{session_id}")
async def delete_session(request: Request, session_id: str):
    deleted = await _store(request).delete(session_id)
    return {"deleted": deleted}