from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator


# Exponential backoff schedule (seconds) for retryable jobs; index == attempts.
JOB_BACKOFF_SECONDS = [0, 30, 120, 600, 1800, 7200]
DEFAULT_MAX_ATTEMPTS = 6
_LOCK_RETRIES = 5
_LOCK_SLEEP_SECONDS = 0.2


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _trunc(value: Any, limit: int = 120) -> str | None:
    if value is None:
        return None
    return str(value)[:limit]


class Store:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        # Retry briefly on "database is locked" so concurrent webhook delivery +
        # the background job drainer don't fail a write under contention.
        last_exc: sqlite3.OperationalError | None = None
        for attempt in range(_LOCK_RETRIES):
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            conn.row_factory = sqlite3.Row
            try:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=5000")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA foreign_keys=ON")
                yield conn
                conn.commit()
                return
            except sqlite3.OperationalError as exc:
                conn.rollback()
                if "locked" in str(exc).lower() and attempt < _LOCK_RETRIES - 1:
                    last_exc = exc
                    time.sleep(_LOCK_SLEEP_SECONDS * (attempt + 1))
                    continue
                raise
            finally:
                conn.close()
        if last_exc:
            raise last_exc

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS kv (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at TEXT
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 6,
                    dedupe_key TEXT,
                    next_attempt_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_error TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status, created_at);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_dedupe ON jobs(dedupe_key)
                    WHERE dedupe_key IS NOT NULL;

                -- Durable record of every Stripe event we accept, so re-delivery
                -- of the same event is idempotent even across restarts.
                CREATE TABLE IF NOT EXISTS stripe_events (
                    event_id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    payload TEXT,
                    status TEXT NOT NULL DEFAULT 'received'
                );

                -- One row per paid Checkout Session. payment_intent + PR linkage
                -- powers the refund guarantee.
                CREATE TABLE IF NOT EXISTS purchases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL UNIQUE,
                    payment_intent TEXT,
                    sku TEXT,
                    email TEXT,
                    price_id TEXT,
                    amount INTEGER,
                    currency TEXT,
                    livemode INTEGER,
                    status TEXT NOT NULL DEFAULT 'paid',
                    repo TEXT,
                    pr_url TEXT,
                    pr_number INTEGER,
                    deadline TEXT,
                    refunded INTEGER NOT NULL DEFAULT 0,
                    refund_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_purchases_pi ON purchases(payment_intent);
                CREATE INDEX IF NOT EXISTS idx_purchases_repo_pr ON purchases(repo, pr_number);

                -- First-party funnel analytics. No third-party tracker; this is
                -- the source of truth for source/utm/kit/deadline/sku/outcome so
                -- conversion drop-offs are visible and attributable.
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    name TEXT NOT NULL,
                    source TEXT,
                    utm_source TEXT,
                    utm_medium TEXT,
                    utm_campaign TEXT,
                    kit TEXT,
                    deadline TEXT,
                    sku TEXT,
                    path TEXT,
                    meta TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
                CREATE INDEX IF NOT EXISTS idx_events_name ON events(name);
                """
            )
            self._migrate_jobs_columns(conn)

    def _migrate_jobs_columns(self, conn: sqlite3.Connection) -> None:
        # Older databases created before durability work may miss columns.
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)")}
        for column, ddl in (
            ("max_attempts", "ALTER TABLE jobs ADD COLUMN max_attempts INTEGER NOT NULL DEFAULT 6"),
            ("dedupe_key", "ALTER TABLE jobs ADD COLUMN dedupe_key TEXT"),
            ("next_attempt_at", "ALTER TABLE jobs ADD COLUMN next_attempt_at TEXT"),
        ):
            if column not in existing:
                conn.execute(ddl)

    # ---- kv ---------------------------------------------------------------- #

    def put_json(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        expires_at = None
        if ttl_seconds:
            expires_at = (datetime.now(UTC) + timedelta(seconds=ttl_seconds)).isoformat()
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO kv(key, value, expires_at) VALUES (?, ?, ?)",
                (key, json.dumps(value), expires_at),
            )

    def get_json(self, key: str) -> Any | None:
        with self.connect() as conn:
            row = conn.execute("SELECT value, expires_at FROM kv WHERE key = ?", (key,)).fetchone()
            if not row:
                return None
            if row["expires_at"] and datetime.fromisoformat(row["expires_at"]) < datetime.now(UTC):
                conn.execute("DELETE FROM kv WHERE key = ?", (key,))
                return None
            return json.loads(row["value"])

    def delete(self, key: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM kv WHERE key = ?", (key,))

    # ---- stripe events (idempotency) -------------------------------------- #

    def record_stripe_event(self, event_id: str, event_type: str, payload: Any) -> bool:
        """Atomically record an event. Returns True if newly recorded, False if
        it was already seen (duplicate delivery)."""
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT OR IGNORE INTO stripe_events(event_id, type, received_at, payload) "
                "VALUES (?, ?, ?, ?)",
                (event_id, event_type, _now(), json.dumps(payload)),
            )
            return cur.rowcount > 0

    def mark_stripe_event(self, event_id: str, status: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE stripe_events SET status = ? WHERE event_id = ?",
                (status, event_id),
            )

    # ---- purchases -------------------------------------------------------- #

    def record_purchase(
        self,
        *,
        session_id: str,
        payment_intent: str | None,
        sku: str | None,
        email: str | None,
        price_id: str | None,
        amount: int | None,
        currency: str | None,
        livemode: bool | None,
        repo: str | None = None,
        deadline: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Insert a purchase row. Returns True if newly inserted, False if the
        session was already recorded (idempotent)."""
        now = _now()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO purchases(
                    session_id, payment_intent, sku, email, price_id, amount,
                    currency, livemode, status, repo, deadline, created_at,
                    updated_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'paid', ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    payment_intent,
                    sku,
                    email,
                    price_id,
                    amount,
                    currency,
                    1 if livemode else 0,
                    repo,
                    deadline,
                    now,
                    now,
                    json.dumps(metadata or {}),
                ),
            )
            return cur.rowcount > 0

    def link_purchase_pr(self, session_id: str, *, pr_url: str, pr_number: int, repo: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE purchases SET pr_url = ?, pr_number = ?, repo = ?, updated_at = ? "
                "WHERE session_id = ?",
                (pr_url, pr_number, repo, _now(), session_id),
            )

    def get_purchase_by_session(self, session_id: str) -> dict[str, Any] | None:
        return self._purchase_query("SELECT * FROM purchases WHERE session_id = ?", (session_id,))

    def get_purchase_by_pr(self, repo: str, pr_number: int) -> dict[str, Any] | None:
        return self._purchase_query(
            "SELECT * FROM purchases WHERE repo = ? AND pr_number = ?", (repo, pr_number)
        )

    def get_purchase_by_payment_intent(self, payment_intent: str) -> dict[str, Any] | None:
        return self._purchase_query(
            "SELECT * FROM purchases WHERE payment_intent = ?", (payment_intent,)
        )

    def _purchase_query(self, sql: str, params: tuple) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None

    # ---- funnel analytics ------------------------------------------------- #

    def record_event(self, name: str, fields: dict[str, Any]) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO events(ts, name, source, utm_source, utm_medium,
                                   utm_campaign, kit, deadline, sku, path, meta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _now(),
                    name[:64],
                    _trunc(fields.get("source")),
                    _trunc(fields.get("utm_source")),
                    _trunc(fields.get("utm_medium")),
                    _trunc(fields.get("utm_campaign")),
                    _trunc(fields.get("kit")),
                    _trunc(fields.get("deadline")),
                    _trunc(fields.get("sku")),
                    _trunc(fields.get("path"), 256),
                    json.dumps(fields.get("meta") or {})[:2000],
                ),
            )
            return int(cur.lastrowid)

    def event_counts(self, since_days: int = 7) -> dict[str, int]:
        cutoff = (datetime.now(UTC) - timedelta(days=since_days)).isoformat()
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT name, COUNT(*) AS n FROM events WHERE ts >= ? GROUP BY name",
                (cutoff,),
            ).fetchall()
            return {row["name"]: int(row["n"]) for row in rows}

    def mark_refunded(self, session_id: str, refund_id: str) -> bool:
        """Mark a purchase refunded. Returns True if this call performed the
        refund transition (i.e. it was not already refunded)."""
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE purchases SET refunded = 1, refund_id = ?, status = 'refunded', "
                "updated_at = ? WHERE session_id = ? AND refunded = 0",
                (refund_id, _now(), session_id),
            )
            return cur.rowcount > 0

    # ---- jobs ------------------------------------------------------------- #

    def enqueue(
        self,
        job_type: str,
        payload: dict[str, Any],
        status: str = "pending",
        dedupe_key: str | None = None,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> int:
        """Enqueue a job. If dedupe_key collides with an existing job, returns
        the existing job id instead of inserting a duplicate."""
        now = _now()
        with self.connect() as conn:
            if dedupe_key:
                existing = conn.execute(
                    "SELECT id FROM jobs WHERE dedupe_key = ?", (dedupe_key,)
                ).fetchone()
                if existing:
                    return int(existing["id"])
            cur = conn.execute(
                """
                INSERT INTO jobs(type, payload, status, max_attempts, dedupe_key,
                                 next_attempt_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (job_type, json.dumps(payload), status, max_attempts, dedupe_key, now, now, now),
            )
            return int(cur.lastrowid)

    def try_claim(self, job_id: int) -> bool:
        """Atomically transition a job pending -> running. Returns True only for
        the caller that won the claim, so the inline background task and the
        startup drainer never process the same job twice."""
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE jobs SET status = 'running', updated_at = ? "
                "WHERE id = ? AND status = 'pending'",
                (_now(), job_id),
            )
            return cur.rowcount > 0

    def mark_job(self, job_id: int, status: str, error: str | None = None) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, updated_at = ?, last_error = COALESCE(?, last_error),
                    attempts = attempts + CASE WHEN ? IS NOT NULL THEN 1 ELSE 0 END
                WHERE id = ?
                """,
                (status, _now(), error, error, job_id),
            )

    def schedule_retry_or_deadletter(self, job_id: int, error: str) -> str:
        """Increment attempts; reschedule with backoff or move to dead_letter
        when max_attempts is exhausted. Returns the resulting status."""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT attempts, max_attempts FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
            if not row:
                return "missing"
            attempts = int(row["attempts"]) + 1
            max_attempts = int(row["max_attempts"] or DEFAULT_MAX_ATTEMPTS)
            if attempts >= max_attempts:
                status = "dead_letter"
                next_attempt_at = None
            else:
                status = "pending"
                idx = min(attempts, len(JOB_BACKOFF_SECONDS) - 1)
                delay = JOB_BACKOFF_SECONDS[idx]
                next_attempt_at = (datetime.now(UTC) + timedelta(seconds=delay)).isoformat()
            conn.execute(
                "UPDATE jobs SET status = ?, attempts = ?, next_attempt_at = ?, "
                "last_error = ?, updated_at = ? WHERE id = ?",
                (status, attempts, next_attempt_at, error[:2000], _now(), job_id),
            )
            return status

    def claim_pending_jobs(self, limit: int = 25) -> list[dict[str, Any]]:
        """Return jobs that are pending and due (next_attempt_at <= now)."""
        now = _now()
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM jobs
                WHERE status = 'pending'
                  AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
                ORDER BY id ASC LIMIT ?
                """,
                (now, limit),
            ).fetchall()
            return [self._job_row(row) for row in rows]

    def recent_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._job_row(row) for row in rows]

    @staticmethod
    def _job_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "type": row["type"],
            "payload": json.loads(row["payload"]),
            "status": row["status"],
            "attempts": row["attempts"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "last_error": row["last_error"],
        }
