import httpx
import pytest
import respx

from jod_gateway.core.adapter import ChatRequest
from jod_gateway.core.session import Session
from jod_gateway.providers.chatgpt.adapter import ChatGPTAdapter
from jod_gateway.providers.chatgpt.config import BASE_URL, OAUTH_SESSION_PATH

URL = BASE_URL + OAUTH_SESSION_PATH


def _session(cookies=None) -> Session:
    return Session(
        id="s1",
        provider="chatgpt",
        label="test",
        cookies=cookies
        or {
            "__Secure-next-auth.session-token.0": "real-ish-token",
            "__Secure-next-auth.session-token.1": "real-ish-token-2",
            "oai-did": "dev-abc-123",
        },
    )


@pytest.mark.asyncio
async def test_valid_cookie_extracts_derived() -> None:
    adapter = ChatGPTAdapter()
    with respx.mock:
        respx.get(URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "accessToken": "at-xyz",
                    "user": {"id": "u-42", "email": "me@example.com"},
                },
            )
        )
        healthy, derived, reason = await adapter.validate_session(_session())

    assert healthy is True
    assert reason is None
    assert derived == {
        "access_token": "at-xyz",
        "device_id": "dev-abc-123",
        "account_id": "u-42",
        "account_email": "me@example.com",
    }


@pytest.mark.asyncio
async def test_missing_access_token() -> None:
    adapter = ChatGPTAdapter()
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, json={"user": {}}))
        healthy, derived, reason = await adapter.validate_session(_session())

    assert healthy is False
    assert derived is None
    assert reason == "no accessToken in response — cookie expired"


@pytest.mark.asyncio
async def test_auth_rejected() -> None:
    adapter = ChatGPTAdapter()
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(401))
        healthy, _, reason = await adapter.validate_session(_session())

    assert healthy is False
    assert reason == "auth rejected: HTTP 401"


@pytest.mark.asyncio
async def test_redirect_to_login() -> None:
    adapter = ChatGPTAdapter()
    with respx.mock:
        respx.get(URL).mock(
            return_value=httpx.Response(302, headers={"location": "/auth/login"})
        )
        healthy, _, reason = await adapter.validate_session(_session())

    assert healthy is False
    assert reason == "redirected to login — cookie invalid"


@pytest.mark.asyncio
async def test_network_error() -> None:
    adapter = ChatGPTAdapter()
    with respx.mock:
        def _boom(request):
            raise httpx.ConnectError("connection refused")

        respx.get(URL).mock(side_effect=_boom)
        healthy, _, reason = await adapter.validate_session(_session())

    assert healthy is False
    assert reason == "network error: ConnectError"


@pytest.mark.asyncio
async def test_chat_not_implemented() -> None:
    adapter = ChatGPTAdapter()
    req = ChatRequest(model="gpt-4o", messages=[{"role": "user", "content": "hi"}])
    with pytest.raises(NotImplementedError):
        await adapter.chat(req)