import pytest
import pytest_asyncio

from jod_gateway.core.session import new
from jod_gateway.core.store import SessionStore


@pytest_asyncio.fixture
async def store(tmp_path):
    s = SessionStore(str(tmp_path / "test.db"), b"k" * 32)
    await s.init()
    yield s
    await s.close()


def _make_session(provider="chatgpt", label="main", value="a"):
    return new(
        provider,
        label,
        {"session-token": value, "oai-did": "dev-" + value},
        {"access_token": "tok-" + value},
    )


@pytest.mark.asyncio
async def test_save_and_get(store) -> None:
    session = _make_session()
    await store.save(session)

    fetched = await store.get(session.id)
    assert fetched is not None
    assert fetched.cookies == session.cookies
    assert fetched.derived == session.derived
    assert fetched.provider == "chatgpt"
    assert fetched.label == "main"


@pytest.mark.asyncio
async def test_get_missing(store) -> None:
    assert await store.get("nope") is None


@pytest.mark.asyncio
async def test_list_filters_by_provider(store) -> None:
    a = _make_session(provider="chatgpt", label="a")
    b = _make_session(provider="chatgpt", label="b")
    c = _make_session(provider="echo", label="c")
    for s in (a, b, c):
        await store.save(s)

    all_sessions = await store.list()
    assert {s.id for s in all_sessions} == {a.id, b.id, c.id}

    chatgpt = await store.list(provider="chatgpt")
    assert {s.id for s in chatgpt} == {a.id, b.id}


@pytest.mark.asyncio
async def test_delete(store) -> None:
    session = _make_session()
    await store.save(session)

    assert await store.delete(session.id) is True
    assert await store.delete(session.id) is False
    assert await store.get(session.id) is None


@pytest.mark.asyncio
async def test_update_health_keeps_cookies(store) -> None:
    session = _make_session()
    await store.save(session)

    await store.update_health(session.id, healthy=False, last_error="waf", last_ok_at=None)

    fetched = await store.get(session.id)
    assert fetched is not None
    assert fetched.healthy is False
    assert fetched.last_error == "waf"
    assert fetched.cookies == session.cookies
    assert fetched.derived == session.derived