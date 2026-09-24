"""Fetch OpenAI sentinel tokens for a stored session.

Usage:
    uv run python scripts/sentinel_cli.py <session_id> [--probe]

Normal mode prints the chat-requirements token and PoW proof token.
Probe mode only calls /prepare and dumps the raw JSON response.
"""

import asyncio
import json
import sys
from datetime import UTC, datetime

from jod_gateway.config import settings
from jod_gateway.core.crypto import load_or_create_master_key
from jod_gateway.core.store import SessionStore
from jod_gateway.providers.chatgpt.sentinel import SentinelError, SentinelManager
from jod_gateway.providers.chatgpt.sentinel_probe import probe


async def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/sentinel_cli.py <session_id> [--probe]")
        return 2

    session_id = sys.argv[1]
    probe_mode = "--probe" in sys.argv[2:]

    key = load_or_create_master_key(settings.master_key_path)
    store = SessionStore(settings.db_path, key)
    await store.init()
    try:
        session = await store.get(session_id)
        if session is None:
            print(f"session '{session_id}' not found in {settings.db_path}")
            return 1

        if probe_mode:
            raw = await probe(session)
            print(json.dumps(raw, indent=2, default=str))
            return 0

        manager = SentinelManager(session)
        await manager.ensure_tokens()
        print(f"chat_req_token: {manager.chat_req_token[:12]}... ")
        print(f"proof_token:    {manager.proof_token}")
        print(
            "expires_at:     "
            + datetime.fromtimestamp(manager.expires_at, tz=UTC).isoformat()
        )
        return 0
    finally:
        await store.close()


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except SentinelError as exc:
        print(f"sentinel error: {exc.reason}")
        sys.exit(1)