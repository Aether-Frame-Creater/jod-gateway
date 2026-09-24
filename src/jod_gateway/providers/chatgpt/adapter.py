from collections.abc import AsyncIterator
from typing import ClassVar

import httpx

from jod_gateway.core.adapter import ChatChunk, ChatRequest, ProviderAdapter
from jod_gateway.core.session import Session
from jod_gateway.providers.chatgpt.config import (
    BASE_URL,
    DEFAULT_TIMEOUT,
    OAUTH_SESSION_PATH,
)
from jod_gateway.providers.chatgpt.headers import browser_headers


class ChatGPTAdapter(ProviderAdapter):
    name = "chatgpt"
    base_url = BASE_URL
    models: ClassVar[list[str]] = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1", "o3-mini"]

    async def validate_session(self, session: Session) -> tuple[bool, dict | None, str | None]:
        async with httpx.AsyncClient(
            cookies=session.cookies,
            headers=browser_headers(),
            follow_redirects=False,
            timeout=DEFAULT_TIMEOUT,
        ) as client:
            try:
                resp = await client.get(BASE_URL + OAUTH_SESSION_PATH)
            except httpx.HTTPError as exc:
                return (False, None, f"network error: {exc.__class__.__name__}")

        status = resp.status_code
        if status in (401, 403):
            return (False, None, f"auth rejected: HTTP {status}")
        if 300 <= status < 400:
            return (False, None, "redirected to login — cookie invalid")
        if status != 200:
            return (False, None, f"unexpected status: HTTP {status}")

        try:
            data = resp.json()
        except ValueError:
            return (False, None, "no accessToken in response — cookie expired")

        if not data.get("accessToken"):
            return (False, None, "no accessToken in response — cookie expired")

        user = data.get("user") or {}
        derived = {
            "access_token": data["accessToken"],
            "device_id": session.cookies.get("oai-did", ""),
            "account_id": str(user.get("id", "")),
            "account_email": user.get("email", ""),
        }
        return (True, derived, None)

    async def chat(self, req: ChatRequest, session=None) -> AsyncIterator[ChatChunk]:
        raise NotImplementedError("Chat completions land in Part 4")