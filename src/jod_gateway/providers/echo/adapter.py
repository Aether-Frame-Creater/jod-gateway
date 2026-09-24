import asyncio
from typing import ClassVar

from jod_gateway.core.adapter import ChatChunk, ChatRequest, ProviderAdapter


def _content_to_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts)
    return ""


class EchoAdapter(ProviderAdapter):
    name = "echo"
    base_url = "local://echo"
    models: ClassVar[list[str]] = ["echo", "echo-mini"]

    async def chat(self, req: ChatRequest, session=None):
        parts = [m["content"] for m in req.messages if m.get("role") == "user"]
        text = "\n".join(_content_to_text(c) for c in parts)

        step = 4
        for i in range(0, len(text), step):
            await asyncio.sleep(0.02)
            yield ChatChunk(delta=text[i : i + step])
        yield ChatChunk(finish_reason="stop")

    async def validate_session(self, session) -> tuple[bool, dict | None, str | None]:
        return (True, {}, None)