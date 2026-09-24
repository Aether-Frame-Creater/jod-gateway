import httpx
import pytest
import respx

from jod_gateway.core.session import Session
from jod_gateway.providers.chatgpt.config import BASE_URL
from jod_gateway.providers.chatgpt.sentinel_probe import probe

PREPARE_URL = BASE_URL + "/backend-api/sentinel/chat-requirements/prepare"


@pytest.mark.asyncio
async def test_probe_returns_raw_dict() -> None:
    session = Session(
        id="s1",
        provider="chatgpt",
        label="test",
        cookies={"oai-did": "dev-1"},
        derived={"access_token": "at-1", "device_id": "dev-1"},
    )
    raw = {
        "prepare_token": "prep-1",
        "proofofwork": {"required": True, "seed": "AQ==", "difficulty": "0000ffff"},
    }
    with respx.mock:
        respx.post(PREPARE_URL).mock(return_value=httpx.Response(200, json=raw))
        result = await probe(session)

    assert result == raw


@pytest.mark.asyncio
async def test_probe_non_json_body() -> None:
    session = Session(
        id="s1",
        provider="chatgpt",
        label="test",
        cookies={},
        derived={"access_token": "at-1", "device_id": "dev-1"},
    )
    with respx.mock:
        respx.post(PREPARE_URL).mock(
            return_value=httpx.Response(502, content=b"<html>bad gateway</html>")
        )
        result = await probe(session)

    assert result["http_status"] == 502
    assert "html" in result["body"]