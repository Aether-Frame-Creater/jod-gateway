import time
import uuid
from dataclasses import dataclass, field

from jod_gateway.core.crypto import decrypt_json, encrypt_json


@dataclass
class Session:
    id: str
    provider: str
    label: str
    cookies: dict[str, str]
    derived: dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_ok_at: float | None = None
    last_error: str | None = None
    healthy: bool = True
    inflight: int = 0
    rate_limited_until: float | None = None

    def to_row(self, key: bytes) -> dict:
        return {
            "id": self.id,
            "provider": self.provider,
            "label": self.label,
            "cookies": encrypt_json(self.cookies, key),
            "derived": encrypt_json(self.derived, key),
            "created_at": self.created_at,
            "last_ok_at": self.last_ok_at,
            "last_error": self.last_error,
            "healthy": int(self.healthy),
            "inflight": self.inflight,
            "rate_limited_until": self.rate_limited_until,
        }

    @classmethod
    def from_row(cls, row, key: bytes) -> "Session":
        return cls(
            id=row["id"],
            provider=row["provider"],
            label=row["label"],
            cookies=decrypt_json(row["cookies"], key),
            derived=decrypt_json(row["derived"], key),
            created_at=row["created_at"],
            last_ok_at=row["last_ok_at"],
            last_error=row["last_error"],
            healthy=bool(row["healthy"]),
            inflight=row["inflight"],
            rate_limited_until=row["rate_limited_until"],
        )

    def public_meta(self) -> dict:
        return {
            "id": self.id,
            "provider": self.provider,
            "label": self.label,
            "created_at": self.created_at,
            "last_ok_at": self.last_ok_at,
            "last_error": self.last_error,
            "healthy": self.healthy,
            "inflight": self.inflight,
            "rate_limited_until": self.rate_limited_until,
            "cookie_count": len(self.cookies),
        }


def new(provider: str, label: str, cookies: dict[str, str], derived: dict[str, str] | None = None) -> Session:
    return Session(
        id=uuid.uuid4().hex,
        provider=provider,
        label=label,
        cookies=cookies,
        derived=derived or {},
    )