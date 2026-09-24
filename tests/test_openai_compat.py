import json

from fastapi.testclient import TestClient

from jod_gateway.main import app


def test_models_list() -> None:
    with TestClient(app) as client:
        resp = client.get("/v1/models")
    assert resp.status_code == 200
    assert resp.json()["object"] == "list"
    ids = {m["id"] for m in resp.json()["data"]}
    assert "echo" in ids
    assert "echo-mini" in ids


def test_non_stream_completion() -> None:
    with TestClient(app) as client:
        resp = client.post(
            "/v1/chat/completions",
            json={"model": "echo", "messages": [{"role": "user", "content": "hello jod"}]},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["object"] == "chat.completion"
    assert body["model"] == "echo"
    assert body["choices"][0]["message"]["content"] == "hello jod"
    assert body["choices"][0]["finish_reason"] == "stop"


def test_stream_completion() -> None:
    with TestClient(app) as client:
        resp = client.post(
            "/v1/chat/completions",
            json={"model": "echo", "stream": True, "messages": [{"role": "user", "content": "hello jod"}]},
        )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    assert resp.headers["cache-control"] == "no-cache"

    lines = [l for l in resp.text.splitlines() if l.startswith("data: ")]
    assert len(lines) >= 3
    assert lines[-1] == "data: [DONE]"

    chunks = [json.loads(l[6:]) for l in lines[:-1]]
    assert all(c["object"] == "chat.completion.chunk" for c in chunks)
    text = "".join(c["choices"][0]["delta"].get("content", "") for c in chunks)
    assert text == "hello jod"


def test_unknown_model_404() -> None:
    with TestClient(app) as client:
        resp = client.post(
            "/v1/chat/completions",
            json={"model": "nope", "messages": [{"role": "user", "content": "x"}]},
        )
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == "model_not_found"
    assert body["error"]["param"] is None
    assert body["error"]["message"]