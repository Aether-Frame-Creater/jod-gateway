import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

from jod_gateway.api import sessions as sessions_mod
from jod_gateway.api.sessions import router as sessions_router
from jod_gateway.core.crypto import load_or_create_master_key
from jod_gateway.core.store import SessionStore


class _StubAdapter:
    name = "chatgpt"

    def __init__(self, healthy: bool = True):
        self.healthy = healthy

    async def validate_session(self, session):
        if self.healthy:
            return (
                True,
                {
                    "access_token": "stubbed-token",
                    "device_id": session.cookies.get("oai-did", ""),
                },
                None,
            )
        return (False, None, "cookie expired (stub)")


@pytest_asyncio.fixture
async def client(tmp_path):
    app = FastAPI()
    key = load_or_create_master_key(str(tmp_path / "master.key"))
    store = SessionStore(str(tmp_path / "test.db"), key)
    await store.init()
    app.state.store = store
    app.include_router(sessions_router)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await store.close()


def _chatgpt_payload(label="real-account"):
    return {
        "provider": "chatgpt",
        "label": label,
        "cookies": [
            {"name": "__Secure-next-auth.session-token.0", "value": "tok-0"},
            {"name": "oai-did", "value": "dev-abc"},
        ],
    }


@pytest.mark.asyncio
async def test_ingest_valid_stores_derived(client, monkeypatch) -> None:
    monkeypatch.setattr(sessions_mod, "resolve", lambda model: _StubAdapter(healthy=True))
    resp = await client.post("/sessions/ingest", json=_chatgpt_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["healthy"] is True
    assert body["cookie_count"] == 2
    assert "reason" not in body

    listed = (await client.get("/sessions")).json()
    assert any(s["id"] == body["id"] for s in listed)


@pytest.mark.asyncio
async def test_ingest_invalid_not_stored(client, monkeypatch) -> None:
    monkeypatch.setattr(sessions_mod, "resolve", lambda model: _StubAdapter(healthy=False))
    resp = await client.post("/sessions/ingest", json=_chatgpt_payload())
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "session_invalid"

    listed = (await client.get("/sessions")).json()
    assert listed == []


@pytest.mark.asyncio
async def test_validate_updates_last_ok(client, monkeypatch) -> None:
    monkeypatch.setattr(sessions_mod, "resolve", lambda model: _StubAdapter(healthy=True))
    created = (await client.post("/sessions/ingest", json=_chatgpt_payload())).json()

    resp = await client.post(f"/sessions/{created['id']}/validate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["validated"] is True
    assert body["reason"] is None
    assert body["healthy"] is True
    assert body["last_ok_at"] is not None


@pytest.mark.asyncio
async def test_validate_invalid_marks_unhealthy(client, monkeypatch) -> None:
    monkeypatch.setattr(sessions_mod, "resolve", lambda model: _StubAdapter(healthy=True))
    created = (await client.post("/sessions/ingest", json=_chatgpt_payload())).json()

    monkeypatch.setattr(sessions_mod, "resolve", lambda model: _StubAdapter(healthy=False))
    resp = await client.post(f"/sessions/{created['id']}/validate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["validated"] is False
    assert body["reason"] == "cookie expired (stub)"
    assert body["healthy"] is False


@pytest.mark.asyncio
async def test_validate_missing_session_404(client) -> None:
    resp = await client.post("/sessions/nope/validate")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_echo_bypasses_validation(client, monkeypatch) -> None:
    def _boom(*args, **kwargs):
        raise AssertionError("resolve must not be called for echo")

    monkeypatch.setattr(sessions_mod, "resolve", _boom)
    payload = {
        "provider": "echo",
        "label": "local",
        "cookies": [{"name": "anything", "value": "whatever"}],
    }
    resp = await client.post("/sessions/ingest", json=payload)
    assert resp.status_code == 200
    assert resp.json()["provider"] == "echo"