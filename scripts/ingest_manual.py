"""Ingest a cookie jar from a JSON file into the running gateway.

Usage:
    uv run python scripts/ingest_manual.py /path/to/cookies.json
"""

import json
import sys

import httpx

INGEST_URL = "http://localhost:8080/sessions/ingest"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/ingest_manual.py <cookies.json>")
        return 2

    with open(sys.argv[1]) as fh:
        payload = json.load(fh)

    resp = httpx.post(INGEST_URL, json=payload)
    resp.raise_for_status()
    data = resp.json()
    print(f"session {data['id']} for provider {data['provider']} ({data['label']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())