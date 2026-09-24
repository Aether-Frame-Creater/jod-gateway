import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from jod_gateway.core.adapter import ChatRequest, ProviderAdapter
from jod_gateway.core.errors import GatewayError
from jod_gateway.core.router import all_models, resolve
from jod_gateway.core.sse import new_completion_id, openai_chunk, openai_done

router = APIRouter(prefix="/v1", tags=["openai"])


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[dict]
    stream: bool = False
    temperature: float = 1.0
    max_tokens: int | None = None
    tools: list[dict] | None = None


def _internal_error_response() -> dict:
    return {
        "error": {
            "message": "Internal server error",
            "type": "server_error",
            "code": "internal_error",
            "param": None,
        }
    }


def _make_stream(adapter: ProviderAdapter, req: ChatRequest, model: str, completion_id: str):
    async def gen():
        async for chunk in adapter.chat(req):
            if chunk.tool_calls:
                yield openai_chunk(
                    completion_id, model, finish_reason=chunk.finish_reason, tool_calls=chunk.tool_calls
                )
            else:
                yield openai_chunk(completion_id, model, delta_text=chunk.delta, finish_reason=chunk.finish_reason)
        yield openai_done()

    return gen()


async def _non_stream(adapter: ProviderAdapter, req: ChatRequest, model: str) -> dict:
    completion_id = new_completion_id()
    content: list[str] = []
    finish_reason = "stop"
    async for chunk in adapter.chat(req):
        if chunk.delta:
            content.append(chunk.delta)
        if chunk.finish_reason:
            finish_reason = chunk.finish_reason
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "".join(content)},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


@router.get("/models")
async def models():
    return {"object": "list", "data": all_models()}


@router.post("/chat/completions")
async def chat_completions(body: ChatCompletionRequest):
    try:
        adapter = resolve(body.model)
    except GatewayError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.to_response())

    req = ChatRequest(**body.model_dump())

    if body.stream:
        return StreamingResponse(
            _make_stream(adapter, req, body.model, new_completion_id()),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    try:
        payload = await _non_stream(adapter, req, body.model)
    except GatewayError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.to_response())
    except Exception:  # noqa: BLE001
        return JSONResponse(status_code=500, content=_internal_error_response())
    return JSONResponse(payload)