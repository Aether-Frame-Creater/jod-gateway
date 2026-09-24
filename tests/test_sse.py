import json

from jod_gateway.core.sse import new_completion_id, openai_chunk, openai_done


def test_new_completion_id() -> None:
    cid = new_completion_id()
    assert cid.startswith("chatcmpl-")
    assert len(cid) == len("chatcmpl-") + 24


def test_openai_chunk_shape() -> None:
    line = openai_chunk("chatcmpl-test", "echo", delta_text="hel")
    assert line.startswith("data: ")
    assert line.endswith("\n\n")

    payload = json.loads(line[6:])
    assert payload["id"] == "chatcmpl-test"
    assert payload["object"] == "chat.completion.chunk"
    assert isinstance(payload["created"], int)
    assert payload["model"] == "echo"

    choice = payload["choices"][0]
    assert choice["index"] == 0
    assert choice["delta"]["content"] == "hel"
    assert choice["finish_reason"] is None


def test_openai_chunk_finish() -> None:
    line = openai_chunk("chatcmpl-test", "echo", finish_reason="stop")
    payload = json.loads(line[6:])
    assert payload["choices"][0]["delta"] == {}
    assert payload["choices"][0]["finish_reason"] == "stop"


def test_openai_done() -> None:
    assert openai_done() == "data: [DONE]\n\n"