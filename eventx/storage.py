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
                notified_at TEXT NOT NULL,
                fingerprint TEXT,
                deadline TEXT,
                reminder_48h_sent INTEGER NOT NULL DEFAULT 0,
                reminder_24h_sent INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fetch_failures (
                platform TEXT PRIMARY KEY,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                last_failed_at TEXT,
                alerted INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        _ensure_column(conn, "seen_events", "fingerprint", "TEXT")
        _ensure_column(conn, "seen_events", "deadline", "TEXT")
        _ensure_column(conn, "seen_events", "reminder_48h_sent", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "seen_events", "reminder_24h_sent", "INTEGER NOT NULL DEFAULT 0")
        conn.commit()


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, typedef: str) -> None:
    cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {typedef}")


def count_seen() -> int:
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM seen_events").fetchone()
        return int(row["n"]) if row else 0


def get_new_events(events: list[HackathonEvent]) -> list[HackathonEvent]:
    if not events:
        return []

    with _connect() as conn:
        keys = [e.dedupe_key for e in events]
        fps = [e.fingerprint for e in events]

        placeholders = ",".join("?" * len(keys))
        seen_keys = {
            row["dedupe_key"]
            for row in conn.execute(
                f"SELECT dedupe_key FROM seen_events WHERE dedupe_key IN ({placeholders})",
                keys,
            ).fetchall()
        }

        seen_fps: set[str] = set()
        if fps:
            fp_placeholders = ",".join("?" * len(fps))
            seen_fps = {
                row["fingerprint"]
                for row in conn.execute(
                    f"SELECT fingerprint FROM seen_events WHERE fingerprint IN ({fp_placeholders})",
                    fps,
                ).fetchall()
                if row["fingerprint"]
            }

    return [
        e
        for e in events
        if e.dedupe_key not in seen_keys and e.fingerprint not in seen_fps
    ]


def mark_notified(events: list[HackathonEvent]) -> None:
    if not events:
        return

    now = datetime.now().isoformat()
    with _connect() as conn:
        conn.executemany(
            """
            INSERT INTO seen_events
                (dedupe_key, title, platform, registration_url, notified_at,
                 fingerprint, deadline, reminder_48h_sent, reminder_24h_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0)
            ON CONFLICT(dedupe_key) DO UPDATE SET
                title=excluded.title,
                platform=excluded.platform,
                registration_url=excluded.registration_url,
                fingerprint=excluded.fingerprint,
                deadline=excluded.deadline
            """,
            [
                (
                    e.dedupe_key,
                    e.title,
                    e.platform,
                    e.registration_url,
                    now,
                    e.fingerprint,
                    e.deadline.isoformat() if e.deadline else None,
                )
                for e in events
            ],
        )
        conn.commit()


def get_due_reminders(events_by_key: dict[str, HackathonEvent]) -> list[tuple[HackathonEvent, str]]:
    """Return (event, kind) where kind is '48h' or '24h'."""
    now = datetime.now()
    due: list[tuple[HackathonEvent, str]] = []

    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT dedupe_key, fingerprint, deadline, reminder_48h_sent, reminder_24h_sent,
                   title, platform, registration_url
            FROM seen_events
            WHERE deadline IS NOT NULL
            """
        ).fetchall()

    for row in rows:
        try:
            deadline = datetime.fromisoformat(row["deadline"])
        except ValueError:
            continue

        if deadline.tzinfo is not None:
            deadline = deadline.replace(tzinfo=None)

        if deadline <= now:
            continue

        hours_left = (deadline - now).total_seconds() / 3600
        event = events_by_key.get(row["dedupe_key"])
        if event is None and row["fingerprint"]:
            for candidate in events_by_key.values():
                if candidate.fingerprint == row["fingerprint"]:
                    event = candidate
                    break

        # Only remind for events still present in the current filtered scan.
        # Avoids re-alerting on old /false-positive rows left in seen_events.
        if event is None:
            continue
        if event.deadline is None:
            event.deadline = deadline

        if 0 < hours_left <= 24 and not row["reminder_24h_sent"]:
            due.append((event, "24h"))
        elif 24 < hours_left <= 48 and not row["reminder_48h_sent"]:
            due.append((event, "48h"))

    return due


def mark_reminder_sent(event: HackathonEvent, kind: str) -> None:
    column = "reminder_24h_sent" if kind == "24h" else "reminder_48h_sent"
    with _connect() as conn:
        conn.execute(
            f"UPDATE seen_events SET {column}=1 WHERE dedupe_key=? OR fingerprint=?",
            (event.dedupe_key, event.fingerprint),
        )
        conn.commit()


def record_fetch_success(platform: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM fetch_failures WHERE platform=?", (platform,))
        conn.commit()


def record_fetch_failure(platform: str, error: str) -> int:
    """Record a failure and return the new consecutive failure count."""
    now = datetime.now().isoformat()
    with _connect() as conn:
        row = conn.execute(
            "SELECT consecutive_failures FROM fetch_failures WHERE platform=?",
            (platform,),
        ).fetchone()
        count = (row["consecutive_failures"] + 1) if row else 1
        conn.execute(
            """
            INSERT INTO fetch_failures (platform, consecutive_failures, last_error, last_failed_at, alerted)
            VALUES (?, ?, ?, ?, 0)
            ON CONFLICT(platform) DO UPDATE SET
                consecutive_failures=excluded.consecutive_failures,
                last_error=excluded.last_error,
                last_failed_at=excluded.last_failed_at
            """,
            (platform, count, error[:500], now),
        )
        conn.commit()
        return count


def get_health_alerts(threshold: int = 2) -> list[tuple[str, int, str]]:
    """Platforms that have failed `threshold` times and not yet alerted."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT platform, consecutive_failures, last_error
            FROM fetch_failures
            WHERE consecutive_failures >= ? AND alerted = 0
            """,
            (threshold,),
        ).fetchall()
    return [(r["platform"], r["consecutive_failures"], r["last_error"] or "") for r in rows]


def mark_health_alerted(platforms: list[str]) -> None:
    if not platforms:
        return
    with _connect() as conn:
        conn.executemany(
            "UPDATE fetch_failures SET alerted=1 WHERE platform=?",
            [(p,) for p in platforms],
        )
        conn.commit()
