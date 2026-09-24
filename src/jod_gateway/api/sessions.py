import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from jod_gateway.core.errors import GatewayError
from jod_gateway.core.router import _registry, resolve
from jod_gateway.core.session import new
from jod_gateway.core.store import SessionStore

router = APIRouter(prefix="/sessions", tags=["sessions"])

ALLOWED_PROVIDERS = {"chatgpt", "echo"}
_CHATGPT_PROBE_MODEL = "gpt-4o"


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


def _adapter_for(provider: str):
    if provider == "chatgpt":
        return resolve(_CHATGPT_PROBE_MODEL)
    for adapter in _registry.values():
        if adapter.name == provider:
            return adapter
    return None


def _not_found(session_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": {"message": "Session not found", "code": "session_not_found"}},
    )


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

    if body.provider == "chatgpt":
        try:
            adapter = _adapter_for("chatgpt")
        except GatewayError as exc:
            return JSONResponse(status_code=exc.status_code, content=exc.to_response())

        healthy, derived_updates, reason = await adapter.validate_session(session)
        if not healthy:
            return JSONResponse(
                status_code=400,
                content={"error": {"message": reason, "code": "session_invalid"}},
            )
        if derived_updates:
            session.derived.update(derived_updates)
        session.healthy = True
        session.last_ok_at = time.time()

    await _store(request).save(session)
    return session.public_meta()


@router.post("/{session_id}/validate")
async def validate_session(request: Request, session_id: str):
    store = _store(request)
    session = await store.get(session_id)
    if session is None:
        return _not_found(session_id)

    adapter = _adapter_for(session.provider)
    if adapter is None:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": f"No adapter registered for provider '{session.provider}'",
                    "code": "unknown_provider",
                }
            },
        )

    healthy, derived_updates, reason = await adapter.validate_session(session)
    session.healthy = healthy
    if derived_updates:
        session.derived.update(derived_updates)
    if healthy:
        session.last_ok_at = time.time()
        session.last_error = None
    else:
        session.last_error = reason
    await store.save(session)

    meta = session.public_meta()
    meta["validated"] = healthy
    meta["reason"] = reason
    return meta


@router.get("")
async def list_sessions(request: Request):
    return [s.public_meta() for s in await _store(request).list()]


@router.get("/{session_id}")
async def get_session(request: Request, session_id: str):
    session = await _store(request).get(session_id)
    if session is None:
        return _not_found(session_id)
    return session.public_meta()


@router.delete("/{session_id}")
async def delete_session(request: Request, session_id: str):
    deleted = await _store(request).delete(session_id)
    return {"deleted": deleted}