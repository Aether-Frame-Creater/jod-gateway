from pathlib import Path

import aiosqlite

from jod_gateway.core.session import Session

_SELECT_ALL = (
    "SELECT id, provider, label, cookies, derived, created_at, last_ok_at, last_error, "
    "healthy, inflight, rate_limited_until FROM sessions"
)


class SessionStore:
    def __init__(self, db_path: str, key: bytes):
        self._db_path = db_path
        self._key = key
        self._conn: aiosqlite.Connection | None = None

    async def init(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                label TEXT NOT NULL,
                cookies BLOB NOT NULL,
                derived BLOB NOT NULL,
                created_at REAL NOT NULL,
                last_ok_at REAL,
                last_error TEXT,
                healthy INTEGER NOT NULL DEFAULT 1,
                inflight INTEGER NOT NULL DEFAULT 0,
                rate_limited_until REAL
            )
            """
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_provider ON sessions(provider)"
        )
        await self._conn.commit()

    async def save(self, s: Session) -> None:
        assert self._conn is not None
        row = s.to_row(self._key)
        await self._conn.execute(
            """
            INSERT OR REPLACE INTO sessions (
                id, provider, label, cookies, derived, created_at, last_ok_at,
                last_error, healthy, inflight, rate_limited_until
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                row["provider"],
                row["label"],
                row["cookies"],
                row["derived"],
                row["created_at"],
                row["last_ok_at"],
                row["last_error"],
                row["healthy"],
                row["inflight"],
                row["rate_limited_until"],
            ),
        )
        await self._conn.commit()

    async def get(self, session_id: str) -> Session | None:
        assert self._conn is not None
        cursor = await self._conn.execute(_SELECT_ALL + " WHERE id = ?", (session_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return Session.from_row(row, self._key)

    async def list(self, provider: str | None = None) -> list[Session]:
        assert self._conn is not None
        if provider is None:
            cursor = await self._conn.execute(_SELECT_ALL + " ORDER BY created_at")
        else:
            cursor = await self._conn.execute(
                _SELECT_ALL + " WHERE provider = ? ORDER BY created_at", (provider,)
            )
        rows = await cursor.fetchall()
        return [Session.from_row(row, self._key) for row in rows]

    async def delete(self, session_id: str) -> bool:
        assert self._conn is not None
        cursor = await self._conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await self._conn.commit()
        return cursor.rowcount > 0

    async def update_health(
        self,
        session_id: str,
        *,
        healthy: bool,
        last_error: str | None = None,
        last_ok_at: float | None = None,
    ) -> None:
        assert self._conn is not None
        await self._conn.execute(
            "UPDATE sessions SET healthy = ?, last_error = ?, last_ok_at = ? WHERE id = ?",
            (int(healthy), last_error, last_ok_at, session_id),
        )
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None