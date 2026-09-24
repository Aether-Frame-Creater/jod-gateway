import httpx

from jod_gateway.core.session import Session
from jod_gateway.providers.chatgpt.config import (
    BASE_URL,
    DEFAULT_TIMEOUT,
    OAI_CLIENT_VERSION,
    SENTINEL_PREPARE_PATH,
)
from jod_gateway.providers.chatgpt.headers import browser_headers
from jod_gateway.providers.chatgpt.prepare_p import build_requirements_token


async def probe(session: Session) -> dict:
    headers = browser_headers(
        {
            "authorization": f"Bearer {session.derived.get('access_token', '')}",
            "oai-device-id": session.derived.get("device_id", ""),
            "oai-client-version": OAI_CLIENT_VERSION,
            "content-type": "application/json",
        }
    )
    p = build_requirements_token(session)
    async with httpx.AsyncClient(headers=headers, timeout=DEFAULT_TIMEOUT) as client:
        resp = await client.post(
            BASE_URL + SENTINEL_PREPARE_PATH, json={"p": p, "conduit_token": ""}
        )
    try:
        return resp.json()
    except ValueError:
        return {"http_status": resp.status_code, "body": resp.text[:2000]}