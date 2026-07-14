from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sportx.config import DB_PATH
from sportx.models import SportEvent


class EventStore:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS seen_events (
                    dedupe_key TEXT PRIMARY KEY,
                    fingerprint TEXT,
                    title TEXT,
                    url TEXT,
                    deadline TEXT,
                    first_seen_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders_sent (
                    fingerprint TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    sent_at TEXT NOT NULL,
                    PRIMARY KEY (fingerprint, kind)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS fetch_failures (
                    platform TEXT PRIMARY KEY,
                    consecutive INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def has_seen(self, event: SportEvent) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM seen_events WHERE dedupe_key = ? OR fingerprint = ?",
                (event.dedupe_key, event.fingerprint),
            ).fetchone()
            return row is not None

    def mark_seen(self, event: SportEvent) -> None:
        now = datetime.now(timezone.utc).isoformat()
        deadline = event.deadline.isoformat() if event.deadline else None
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO seen_events
                (dedupe_key, fingerprint, title, url, deadline, first_seen_at)
                VALUES (?, ?, ?, ?, ?, COALESCE(
                    (SELECT first_seen_at FROM seen_events WHERE dedupe_key = ?),
                    ?
                ))
                """,
                (
                    event.dedupe_key,
                    event.fingerprint,
                    event.title,
                    event.registration_url,
                    deadline,
                    event.dedupe_key,
                    now,
                ),
            )
            conn.commit()

    def mark_many_seen(self, events: list[SportEvent]) -> None:
        for event in events:
            self.mark_seen(event)

    def reminder_already_sent(self, fingerprint: str, kind: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM reminders_sent WHERE fingerprint = ? AND kind = ?",
                (fingerprint, kind),
            ).fetchone()
            return row is not None

    def mark_reminder(self, fingerprint: str, kind: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO reminders_sent (fingerprint, kind, sent_at) VALUES (?, ?, ?)",
                (fingerprint, kind, now),
            )
            conn.commit()

    def events_needing_reminders(self) -> list[tuple[SportEvent, str, str]]:
        """Return (event-like, kind, fingerprint) for 48h and 24h windows."""
        now = datetime.now(timezone.utc)
        windows = [("48h", timedelta(hours=48)), ("24h", timedelta(hours=24))]
        out: list[tuple[SportEvent, str, str]] = []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT dedupe_key, fingerprint, title, url, deadline FROM seen_events WHERE deadline IS NOT NULL"
            ).fetchall()
        for row in rows:
            try:
                deadline = datetime.fromisoformat(row["deadline"])
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
            fingerprint = row["fingerprint"] or row["dedupe_key"]
            for kind, window in windows:
                delta = deadline - now
                if timedelta(0) < delta <= window:
                    if self.reminder_already_sent(fingerprint, kind):
                        continue
                    event = SportEvent(
                        id=row["dedupe_key"],
                        title=row["title"] or "Sports event",
                        platform="reminder",
                        registration_url=row["url"] or "",
                        mode="offline",
                        location="Bangalore",
                        deadline=deadline,
                        organisation=None,
                    )
                    out.append((event, kind, fingerprint))
        return out

    def record_fetch_result(self, platform: str, ok: bool, error: str | None = None) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            if ok:
                conn.execute(
                    """
                    INSERT INTO fetch_failures (platform, consecutive, last_error, updated_at)
                    VALUES (?, 0, NULL, ?)
                    ON CONFLICT(platform) DO UPDATE SET
                        consecutive = 0, last_error = NULL, updated_at = excluded.updated_at
                    """,
                    (platform, now),
                )
                conn.commit()
                return 0
            row = conn.execute(
                "SELECT consecutive FROM fetch_failures WHERE platform = ?", (platform,)
            ).fetchone()
            consecutive = (row["consecutive"] if row else 0) + 1
            conn.execute(
                """
                INSERT INTO fetch_failures (platform, consecutive, last_error, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(platform) DO UPDATE SET
                    consecutive = excluded.consecutive,
                    last_error = excluded.last_error,
                    updated_at = excluded.updated_at
                """,
                (platform, consecutive, error, now),
            )
            conn.commit()
            return consecutive
