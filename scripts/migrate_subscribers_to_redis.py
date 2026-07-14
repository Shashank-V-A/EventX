"""One-shot: copy local SQLite active subscribers into Upstash Redis."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from eventx.redis_store import redis_configured, sadd_active  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def migrate(db_path: Path, bot: str) -> int:
    if not db_path.exists():
        print(f"{bot}: no local DB at {db_path}")
        return 0
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT chat_id FROM subscribers WHERE active = 1"
    ).fetchall()
    conn.close()
    for (chat_id,) in rows:
        sadd_active(bot, str(chat_id))
    print(f"{bot}: migrated {len(rows)} active subscriber(s)")
    return len(rows)


def main() -> None:
    if not redis_configured():
        print(
            "Set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN first.",
            file=sys.stderr,
        )
        sys.exit(1)
    total = 0
    total += migrate(ROOT / "data" / "hackathonx_subscribers.db", "hackathonx")
    total += migrate(ROOT / "data" / "sportx_subscribers.db", "sportx")
    print(f"Done. {total} chat id(s) in Redis.")


if __name__ == "__main__":
    main()
