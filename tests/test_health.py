from fastapi.testclient import TestClient

from jod_gateway import __version__
from jod_gateway.main import app


def test_health() -> None:
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__