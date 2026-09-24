import os
import time

import httpx
import structlog

from jod_gateway.core.session import Session
from jod_gateway.providers.chatgpt.config import (
    BASE_URL,
    DEFAULT_TIMEOUT,
    OAI_CLIENT_VERSION,
    SENTINEL_CACHE_TTL_SEC,
    SENTINEL_FINALIZE_PATH,
    SENTINEL_PREPARE_PATH,
)
from jod_gateway.providers.chatgpt.headers import browser_headers
from jod_gateway.providers.chatgpt.pow import build_pow_config, solve_pow
from jod_gateway.providers.chatgpt.prepare_p import build_requirements_token

log = structlog.get_logger("jod.sentinel")

_REDACT_KEYS = {
    "token",
    "access_token",
    "accessToken",
    "prepare_token",
    "proof_token",
    "conduit_token",
    "authorization",
    "cookie",
    "cookies",
    "proof",
}


def _redact(obj):
    if isinstance(obj, dict):
        return {k: "***" if k in _REDACT_KEYS else _redact(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact(item) for item in obj]
    return obj


class SentinelError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class SentinelManager:
    def __init__(self, session: Session):
        self.session = session
        self.chat_req_token: str | None = None
        self.proof_token: str | None = None
        self.expires_at: float = 0.0

    async def ensure_tokens(self) -> None:
        if self.chat_req_token and time.time() < self.expires_at - 60:
            return
        await self._refresh()

    def _headers(self) -> dict:
        return browser_headers(
            {
                "authorization": f"Bearer {self.session.derived.get('access_token', '')}",
                "oai-device-id": self.session.derived.get("device_id", ""),
                "oai-client-version": OAI_CLIENT_VERSION,
                "content-type": "application/json",
            }
        )

    async def _post(self, path: str, json_body: dict) -> httpx.Response:
        try:
            async with httpx.AsyncClient(
                headers=self._headers(), timeout=DEFAULT_TIMEOUT, follow_redirects=False
            ) as client:
                return await client.post(BASE_URL + path, json=json_body)
        except httpx.HTTPError as exc:
            raise SentinelError(f"network error: {exc.__class__.__name__}") from exc

    async def _refresh(self) -> None:
        p = build_requirements_token(self.session)

        prepare_resp = await self._post(
            SENTINEL_PREPARE_PATH, {"p": p, "conduit_token": ""}
        )
        if os.environ.get("JOD_ENV") == "dev":
            log.info("sentinel prepare", status=prepare_resp.status_code)
        if prepare_resp.status_code != 200:
            raise SentinelError(f"prepare failed: HTTP {prepare_resp.status_code}")

        prep = self._parse_json(prepare_resp, "prepare")
        if not isinstance(prep, dict) or "prepare_token" not in prep:
            if os.environ.get("JOD_ENV") == "dev":
                log.info("prepare shape unexpected", response=_redact(prep))
            raise SentinelError("prepare response missing 'prepare_token'")

        proof = None
        pow_cfg = prep.get("proofofwork") or {}
        if pow_cfg.get("required", True):
            if "seed" not in pow_cfg or "difficulty" not in pow_cfg:
                if os.environ.get("JOD_ENV") == "dev":
                    log.info("proofofwork incomplete", response=_redact(prep))
                raise SentinelError("proofofwork response missing 'seed' or 'difficulty'")
            proof = solve_pow(pow_cfg["seed"], pow_cfg["difficulty"], build_pow_config(self.session))
            if proof is None:
                raise SentinelError("pow_exhausted")

        finalize_body: dict = {"prepare_token": prep["prepare_token"]}
        if proof is not None:
            finalize_body["proofofwork"] = proof

        finalize_resp = await self._post(SENTINEL_FINALIZE_PATH, finalize_body)
        if os.environ.get("JOD_ENV") == "dev":
            log.info("sentinel finalize", status=finalize_resp.status_code)
        if finalize_resp.status_code != 200:
            raise SentinelError(f"finalize failed: HTTP {finalize_resp.status_code}")

        fin = self._parse_json(finalize_resp, "finalize")
        if not isinstance(fin, dict) or "token" not in fin:
            if os.environ.get("JOD_ENV") == "dev":
                log.info("finalize shape unexpected", response=_redact(fin))
            raise SentinelError("finalize response missing 'token'")

        self.chat_req_token = fin["token"]
        self.proof_token = proof
        self.expires_at = time.time() + SENTINEL_CACHE_TTL_SEC

    async def invalidate(self) -> None:
        self.chat_req_token = None
        self.proof_token = None
        self.expires_at = 0.0

    @staticmethod
    def _parse_json(resp: httpx.Response, stage: str) -> dict:
        try:
            data = resp.json()
        except ValueError as exc:
            raise SentinelError(f"{stage} returned non-JSON response") from exc
        if not isinstance(data, dict):
            raise SentinelError(f"{stage} response is not a JSON object")
        return data