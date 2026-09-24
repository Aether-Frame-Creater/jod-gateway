from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from jod_gateway.api.sessions import router as sessions_router
from jod_gateway.core.crypto import load_or_create_master_key
from jod_gateway.core.store import SessionStore


@pytest.fixture
def client(tmp_path):
    app = FastAPI()
    key = load_or_create_master_key(str(tmp_path / "master.key"))
    store = SessionStore(str(tmp_path / "test.db"), key)

    @asynccontextmanager
    async def lifespan(app):
        await store.init()
        app.state.store = store
        yield
        await store.close()

    app.include_router(sessions_router)
    app.router.lifespan_context = lifespan

    with TestClient(app) as c:
        yield c


def _ingest_payload():
    return {
        "provider": "chatgpt",
        "label": "smoke-test",
        "cookies": [
            {"name": "__Secure-next-auth.session-token.0", "value": "secret-cookie-value", "domain": ".chatgpt.com"},
            {"name": "oai-did", "value": "fake-device-uuid", "domain": ".chatgpt.com"},
        ],
        "derived": {"access_token": "secret-derived-token"},
    }


def test_ingest(client) -> None:
    resp = client.post("/sessions/ingest", json=_ingest_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"]
    assert body["provider"] == "chatgpt"
    assert body["healthy"] is True
    assert body["cookie_count"] == 2


def test_get_session_no_cookies_leak(client) -> None:
    created = client.post("/sessions/ingest", json=_ingest_payload()).json()
    resp = client.get(f"/sessions/{created['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == created["id"]
    assert "secret-cookie-value" not in resp.text
    assert "secret-derived-token" not in resp.text
    assert "cookies" not in body


def test_delete_session(client) -> None:
    created = client.post("/sessions/ingest", json=_ingest_payload()).json()
    resp = client.delete(f"/sessions/{created['id']}")
    assert resp.status_code == 200
    assert resp.json() == {"deleted": True}
    assert client.get(f"/sessions/{created['id']}").status_code == 404


def test_delete_missing_session(client) -> None:
    resp = client.delete("/sessions/does-not-exist")
    assert resp.status_code == 200
    assert resp.json() == {"deleted": False}


def test_ingest_missing_fields_422(client) -> None:
    resp = client.post("/sessions/ingest", json={})
    assert resp.status_code == 422


def test_ingest_unknown_provider(client) -> None:
    payload = _ingest_payload()
    payload["provider"] = "skynet"
    resp = client.post("/sessions/ingest", json=payload)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "unknown_provider"