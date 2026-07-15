from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sportx.config import DB_PATH
from sportx.models import SportEvent

_SEEN_COLUMNS = {
    "dedupe_key": "TEXT PRIMARY KEY",
    "fingerprint": "TEXT",
    "title": "TEXT",
    "url": "TEXT",
    "deadline": "TEXT",
    "first_seen_at": "TEXT NOT NULL",
    "platform": "TEXT",
    "location": "TEXT",
    "organisation": "TEXT",
    "category": "TEXT",
    "image_url": "TEXT",
    "description": "TEXT",
}


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
                    first_seen_at TEXT NOT NULL,
                    platform TEXT,
                    location TEXT,
                    organisation TEXT,
                    category TEXT,
                    image_url TEXT,
                    description TEXT
                )
                """
            )
            existing = {
                row[1]
                for row in conn.execute("PRAGMA table_info(seen_events)").fetchall()
            }
            for col, decl in _SEEN_COLUMNS.items():
                if col in existing or col == "dedupe_key":
                    continue
                conn.execute(f"ALTER TABLE seen_events ADD COLUMN {col} {decl}")

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
        desc = (event.description or "")[:800] or None
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT first_seen_at FROM seen_events WHERE dedupe_key = ?",
                (event.dedupe_key,),
            ).fetchone()
            first_seen = existing["first_seen_at"] if existing else now
            conn.execute(
                """
                INSERT INTO seen_events (
                    dedupe_key, fingerprint, title, url, deadline, first_seen_at,
                    platform, location, organisation, category, image_url, description
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(dedupe_key) DO UPDATE SET
                    fingerprint = excluded.fingerprint,
                    title = excluded.title,
                    url = excluded.url,
                    deadline = excluded.deadline,
                    platform = excluded.platform,
                    location = excluded.location,
                    organisation = excluded.organisation,
                    category = excluded.category,
                    image_url = excluded.image_url,
                    description = excluded.description
                """,
                (
                    event.dedupe_key,
                    event.fingerprint,
                    event.title,
                    event.registration_url,
                    deadline,
                    first_seen,
                    event.platform,
                    event.location,
                    event.organisation,
                    event.category,
                    event.image_url,
                    desc,
                ),
            )
            conn.commit()

    def mark_many_seen(self, events: list[SportEvent]) -> None:
        for event in events:
            self.mark_seen(event)

    def refresh_seen_metadata(self, events: list[SportEvent]) -> None:
        """Update stored listing details for events we already know about."""
        for event in events:
            if self.has_seen(event):
                self.mark_seen(event)

    def reminder_already_sent(self, fingerprint: str, kind: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM reminders_sent WHERE fingerprint = ? AND kind = ?",
                (fingerprint, kind),
            ).fetchone()
            return row is not None

    def mark_reminder(self, fingerprint: str, kind: str, *, also: str | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        keys = [fingerprint]
        if also and also != fingerprint:
            keys.append(also)
        with self._connect() as conn:
            for key in keys:
                conn.execute(
                    "INSERT OR IGNORE INTO reminders_sent (fingerprint, kind, sent_at) VALUES (?, ?, ?)",
                    (key, kind, now),
                )
            conn.commit()

    def _row_to_event(self, row: sqlite3.Row, deadline: datetime) -> SportEvent:
        platform = row["platform"] or "meetup"
        # Older rows stored dedupe_key as platform:id; recover id
        raw_id = row["dedupe_key"] or ""
        eid = raw_id.split(":", 1)[-1] if ":" in raw_id else raw_id
        return SportEvent(
            id=eid,
            title=row["title"] or "Sports event",
            platform=platform,
            registration_url=row["url"] or "",
            mode="offline",
            location=row["location"] or "Bangalore",
            deadline=deadline,
            organisation=row["organisation"],
            category=row["category"] or "sports",
            image_url=row["image_url"],
            description=row["description"],
        )

    def events_needing_reminders(self) -> list[tuple[SportEvent, str, str]]:
        """Return (event, kind, fingerprint) for exclusive 48h / 24h windows.

        Windows (same as HackathonX):
          - 48h: more than 24h and at most 48h away
          - 24h: at most 24h away
        Older overlapping logic (<=48h AND <=24h) double-fired reminders.
        """
        now = datetime.now(timezone.utc)
        out: list[tuple[SportEvent, str, str]] = []
        seen_keys: set[tuple[str, str]] = set()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT dedupe_key, fingerprint, title, url, deadline,
                       platform, location, organisation, category, image_url, description
                FROM seen_events
                WHERE deadline IS NOT NULL
                """
            ).fetchall()
        for row in rows:
            try:
                deadline = datetime.fromisoformat(row["deadline"])
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
            delta = deadline - now
            if delta <= timedelta(0):
                continue

            hours_left = delta.total_seconds() / 3600
            if hours_left <= 24:
                kind = "24h"
            elif hours_left <= 48:
                kind = "48h"
            else:
                continue

            fingerprint = row["fingerprint"] or row["dedupe_key"]
            dedupe_key = str(row["dedupe_key"] or fingerprint)
            # Claim by both identities so URL/title fingerprint churn can't re-fire.
            if self.reminder_already_sent(fingerprint, kind) or self.reminder_already_sent(
                dedupe_key, kind
            ):
                continue
            key = (fingerprint, kind)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            out.append((self._row_to_event(row, deadline), kind, fingerprint))
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
