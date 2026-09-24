import httpx
import pytest
import respx

from jod_gateway.core.session import Session
from jod_gateway.providers.chatgpt.config import BASE_URL
from jod_gateway.providers.chatgpt.sentinel import SentinelError, SentinelManager

PREPARE_URL = BASE_URL + "/backend-api/sentinel/chat-requirements/prepare"
FINALIZE_URL = BASE_URL + "/backend-api/sentinel/chat-requirements/finalize"


def _session() -> Session:
    return Session(
        id="s1",
        provider="chatgpt",
        label="test",
        cookies={
            "__Secure-next-auth.session-token.0": "tok-0",
            "oai-did": "dev-1",
        },
        derived={"access_token": "at-1", "device_id": "dev-1"},
    )


def _body_bytes(call) -> dict:
    import json

    return json.loads(call.request.content)


@pytest.mark.asyncio
async def test_flow_and_cache_hit() -> None:
    manager = SentinelManager(_session())
    with respx.mock as mock:
        prepare = mock.post(PREPARE_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "prepare_token": "prep-1",
                    "proofofwork": {"required": True, "seed": "AA==", "difficulty": "~0"},
                },
            )
        )
        finalize = mock.post(FINALIZE_URL).mock(
            return_value=httpx.Response(200, json={"token": "chat-req-1"})
        )

        await manager.ensure_tokens()
        await manager.ensure_tokens()

        assert manager.chat_req_token == "chat-req-1"
        assert manager.proof_token == "gAAAAAB0"
        assert manager.expires_at > 0
        assert len(prepare.calls) == 1
        assert len(finalize.calls) == 1

        body = _body_bytes(finalize.calls[0])
        assert body["prepare_token"] == "prep-1"
        assert body["proofofwork"] == "gAAAAAB0"


@pytest.mark.asyncio
async def test_no_pow_when_not_required() -> None:
    manager = SentinelManager(_session())
    with respx.mock as mock:
        mock.post(PREPARE_URL).mock(
            return_value=httpx.Response(
                200,
                json={"prepare_token": "prep-2", "proofofwork": {"required": False}},
            )
        )
        finalize = mock.post(FINALIZE_URL).mock(
            return_value=httpx.Response(200, json={"token": "chat-req-2"})
        )

        await manager.ensure_tokens()

        assert manager.chat_req_token == "chat-req-2"
        assert manager.proof_token is None
        body = _body_bytes(finalize.calls[0])
        assert body["prepare_token"] == "prep-2"
        assert "proofofwork" not in body


@pytest.mark.asyncio
async def test_malformed_prepare() -> None:
    manager = SentinelManager(_session())
    with respx.mock:
        respx.post(PREPARE_URL).mock(return_value=httpx.Response(200, json={"foo": 1}))
        with pytest.raises(SentinelError) as exc_info:
            await manager.ensure_tokens()
    assert "prepare_token" in exc_info.value.reason


@pytest.mark.asyncio
async def test_finalize_401() -> None:
    manager = SentinelManager(_session())
    with respx.mock:
        respx.post(PREPARE_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "prepare_token": "prep-3",
                    "proofofwork": {"required": True, "seed": "AA==", "difficulty": "~0"},
                },
            )
        )
        respx.post(FINALIZE_URL).mock(return_value=httpx.Response(401, json={}))
        with pytest.raises(SentinelError) as exc_info:
            await manager.ensure_tokens()
    assert "finalize failed" in exc_info.value.reason


@pytest.mark.asyncio
async def test_network_error() -> None:
    manager = SentinelManager(_session())
    with respx.mock:
        def _boom(request):
            raise httpx.ConnectError("connection refused")

        respx.post(PREPARE_URL).mock(side_effect=_boom)
        with pytest.raises(SentinelError) as exc_info:
            await manager.ensure_tokens()
    assert exc_info.value.reason == "network error: ConnectError"