import base64
import json
import time

from jod_gateway.core.session import Session
from jod_gateway.providers.chatgpt.config import (
    POW_FNV_MODULO,
    POW_FNV_OFFSET,
    POW_FNV_PRIME,
    POW_MAX_ITERATIONS,
)


def fnv1a_mod(data: bytes) -> int:
    h = POW_FNV_OFFSET
    for byte in data:
        h = (h * POW_FNV_PRIME) % POW_FNV_MODULO
        h = (h ^ byte) % POW_FNV_MODULO
        h = (h * POW_FNV_PRIME) % POW_FNV_MODULO
    return h


def parse_difficulty(difficulty: str) -> tuple[int, bool]:
    if difficulty.startswith("~"):
        return (int(difficulty[1:], 16), True)
    return (int(difficulty, 16), False)


def solve_pow(
    seed_b64: str,
    difficulty: str,
    config: dict,
    max_iterations: int = POW_MAX_ITERATIONS,
) -> str | None:
    seed = base64.b64decode(seed_b64)
    threshold, inverted = parse_difficulty(difficulty)

    for nonce in range(max_iterations):
        cfg = config.copy()
        cfg["n"] = nonce
        payload = json.dumps(cfg, separators=(",", ":")).encode()
        h = fnv1a_mod(seed + payload)
        if (h >= threshold) if inverted else (h <= threshold):
            return f"gAAAAAB{nonce}"
    return None


# SHAPE UNSTABLE — verify against live /prepare response if PoW is rejected.
def build_pow_config(session: Session) -> dict:
    return {
        "s": "1920x1080",
        "t": int(time.time() * 1000),
        "c": "0",
        "d": session.derived.get("device_id", ""),
        "l": "en-US",
        "i": "0",
        "n": 0,
        "m": "0",
        "u": "0",
        "e": "0",
        "o": "0",
        "p": "0",
        "q": "0",
        "r": "0",
        "v": "0",
        "w": "0",
        "x": "0",
        "y": "0",
        "z": "0",
    }