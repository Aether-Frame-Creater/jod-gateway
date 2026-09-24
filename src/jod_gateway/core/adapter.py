from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class ChatRequest:
    model: str
    messages: list[dict]
    stream: bool = True
    temperature: float = 1.0
    max_tokens: int | None = None
    tools: list[dict] | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class ChatChunk:
    delta: str = ""
    finish_reason: str | None = None
    tool_calls: list | None = None


class ProviderAdapter(ABC):
    name: str = ""
    base_url: str = ""
    models: ClassVar[list[str]] = []

    @abstractmethod
    async def chat(self, req: ChatRequest, session=None) -> AsyncIterator[ChatChunk]:
        raise NotImplementedError

    async def validate_session(self, session) -> bool:
        return True

    async def refresh_session(self, session):
        return session

    def list_models(self) -> list[dict]:
        return [{"id": m, "object": "model", "owned_by": self.name} for m in self.models]