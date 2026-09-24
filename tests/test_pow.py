from jod_gateway.core.session import Session
from jod_gateway.providers.chatgpt.pow import (
    build_pow_config,
    fnv1a_mod,
    parse_difficulty,
    solve_pow,
)


def test_fnv1a_mod_known_vectors() -> None:
    cases = [
        (b"", 0x811C9DC5),
        (b"a", 0x70772D5A),
        (b"ab", 0xC132AD24),
        (b"hello", 0x1507EF4F),
    ]
    for data, expected in cases:
        assert fnv1a_mod(data) == expected


def test_parse_difficulty_plain() -> None:
    assert parse_difficulty("0000ffff") == (0x0000FFFF, False)


def test_parse_difficulty_inverted() -> None:
    assert parse_difficulty("~0000ffff") == (0x0000FFFF, True)


def test_solve_pow_trivial() -> None:
    proof = solve_pow("AA==", "~0", {"a": "b"}, max_iterations=10)
    assert proof == "gAAAAAB0"


def test_solve_pow_impossible() -> None:
    proof = solve_pow("AA==", "0", {"a": "b"}, max_iterations=100)
    assert proof is None


def test_solve_pow_uses_nonce_in_json() -> None:
    session = Session(
        id="s1",
        provider="chatgpt",
        label="t",
        cookies={"oai-did": "dev-1"},
        derived={"device_id": "dev-1"},
    )
    cfg = build_pow_config(session)
    assert cfg["d"] == "dev-1"
    assert cfg["s"] == "1920x1080"
    assert "n" in cfg