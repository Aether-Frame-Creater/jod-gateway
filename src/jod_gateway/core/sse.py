import json
import time
import uuid


def new_completion_id() -> str:
    return "chatcmpl-" + uuid.uuid4().hex[:24]


def openai_chunk(
    completion_id: str,
    model: str,
    delta_text: str = "",
    finish_reason: str | None = None,
    tool_calls: list | None = None,
) -> str:
    delta: dict = {}
    if tool_calls is not None:
        delta["tool_calls"] = tool_calls
    elif delta_text:
        delta["content"] = delta_text

    chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason or None}],
    }
    return "data: " + json.dumps(chunk) + "\n\n"


def openai_done() -> str:
    return "data: [DONE]\n\n"