import sqlite3
from datetime import datetime

from eventx.config import DB_PATH, DATA_DIR
from eventx.models import HackathonEvent


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_events (
                dedupe_key TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                platform TEXT NOT NULL,
                registration_url TEXT NOT NULL,
                notified_at TEXT NOT NULL
            )
            """
        )


def count_seen() -> int:
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM seen_events").fetchone()
        return int(row["n"]) if row else 0


def get_new_events(events: list[HackathonEvent]) -> list[HackathonEvent]:
    if not events:
        return []

    with _connect() as conn:
        keys = [e.dedupe_key for e in events]
        placeholders = ",".join("?" * len(keys))
        rows = conn.execute(
            f"SELECT dedupe_key FROM seen_events WHERE dedupe_key IN ({placeholders})",
            keys,
        ).fetchall()
        seen = {row["dedupe_key"] for row in rows}

    return [e for e in events if e.dedupe_key not in seen]


def mark_notified(events: list[HackathonEvent]) -> None:
    if not events:
        return

    now = datetime.now().isoformat()
    with _connect() as conn:
        conn.executemany(
            """
            INSERT OR IGNORE INTO seen_events
                (dedupe_key, title, platform, registration_url, notified_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (e.dedupe_key, e.title, e.platform, e.registration_url, now)
                for e in events
            ],
        )
        conn.commit()
