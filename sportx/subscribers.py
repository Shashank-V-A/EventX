"""SportX open subscription store + Telegram command helpers."""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

import httpx

from eventx.commands import handle_command_update
from eventx.blob_store import (
    add_active,
    blob_configured,
    is_active,
    list_active,
    remove_active,
)
from sportx.config import BASE_DIR, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

BOT = "sportx"
DB_PATH = BASE_DIR / "data" / "sportx_subscribers.db"

WELCOME = (
    "🏅 <b>Welcome to SportX</b>\n\n"
    "You're subscribed to Bangalore sports alerts "
    "(marathons, cricket, pickleball, badminton, and more).\n\n"
    "You'll get a Telegram message when something new is listed.\n\n"
    "Commands:\n"
    "/start — subscribe\n"
    "/stop — unsubscribe\n"
    "/help — show this message"
)

ALREADY = (
    "✅ You're already subscribed to <b>SportX</b>.\n"
    "New Bangalore sports events will appear here automatically."
)

GOODBYE = (
    "👋 Unsubscribed from <b>SportX</b>.\n"
    "Send /start anytime to subscribe again."
)

HELP = WELCOME


class SubscriberStore:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.use_blob = blob_configured()
        if os.getenv("VERCEL") and not self.use_blob:
            raise RuntimeError(
                "BLOB_READ_WRITE_TOKEN is required on Vercel "
                "(SQLite is ephemeral there)"
            )
        if not self.use_blob:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_sqlite()
        self.ensure_admin()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS subscribers (
                    chat_id TEXT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    joined_at TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bot_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def ensure_admin(self) -> None:
        if not TELEGRAM_CHAT_ID:
            return
        chat_id = str(TELEGRAM_CHAT_ID)
        if self.use_blob:
            if not is_active(BOT, chat_id):
                add_active(BOT, chat_id)
            return
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM subscribers WHERE chat_id = ?", (chat_id,)
            ).fetchone()
        if not row:
            self.subscribe(chat_id, username="admin", first_name="Admin")

    def get_offset(self) -> int:
        if self.use_blob:
            return 0
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM bot_state WHERE key = 'update_offset'"
            ).fetchone()
        return int(row["value"]) if row else 0

    def set_offset(self, offset: int) -> None:
        if self.use_blob:
            return
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO bot_state (key, value) VALUES ('update_offset', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (str(offset),),
            )
            conn.commit()

    def subscribe(
        self,
        chat_id: str,
        *,
        username: str | None = None,
        first_name: str | None = None,
    ) -> bool:
        chat_id = str(chat_id)
        if self.use_blob:
            return add_active(BOT, chat_id)

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT active FROM subscribers WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            conn.execute(
                """
                INSERT INTO subscribers (chat_id, username, first_name, joined_at, active)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(chat_id) DO UPDATE SET
                    username = COALESCE(excluded.username, subscribers.username),
                    first_name = COALESCE(excluded.first_name, subscribers.first_name),
                    active = 1
                """,
                (chat_id, username, first_name, now),
            )
            conn.commit()
        if not existing:
            return True
        return int(existing["active"] or 0) == 0

    def unsubscribe(self, chat_id: str) -> bool:
        chat_id = str(chat_id)
        if self.use_blob:
            return remove_active(BOT, chat_id)

        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE subscribers SET active = 0 WHERE chat_id = ? AND active = 1",
                (chat_id,),
            )
            conn.commit()
            return cur.rowcount > 0

    def list_active_chat_ids(self) -> list[str]:
        self.ensure_admin()
        if self.use_blob:
            return list_active(BOT)

        with self._connect() as conn:
            rows = conn.execute(
                "SELECT chat_id FROM subscribers WHERE active = 1 ORDER BY joined_at"
            ).fetchall()
        ids = [str(r["chat_id"]) for r in rows]
        seen: set[str] = set()
        out: list[str] = []
        for cid in ids:
            if cid not in seen:
                seen.add(cid)
                out.append(cid)
        return out

    def count_active(self) -> int:
        return len(self.list_active_chat_ids())


def _api(method: str) -> str:
    return f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"


def send_to_chat(
    chat_id: str,
    text: str,
    *,
    disable_preview: bool = True,
) -> bool:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("SPORTX_TELEGRAM_BOT_TOKEN is not set")
    response = httpx.post(
        _api("sendMessage"),
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": disable_preview,
        },
        timeout=30.0,
    )
    if response.status_code == 403:
        SubscriberStore().unsubscribe(str(chat_id))
        return False
    response.raise_for_status()
    return True


def send_photo_to_chat(chat_id: str, photo_url: str, caption: str) -> bool:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("SPORTX_TELEGRAM_BOT_TOKEN is not set")
    if len(caption) > 1024:
        caption = caption[:1021] + "…"
    response = httpx.post(
        _api("sendPhoto"),
        json={
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": "HTML",
        },
        timeout=30.0,
    )
    if response.status_code == 403:
        SubscriberStore().unsubscribe(str(chat_id))
        return False
    response.raise_for_status()
    return True


def handle_update(update: dict) -> bool:
    store = SubscriberStore()
    return handle_command_update(
        update,
        subscribe=store.subscribe,
        unsubscribe=store.unsubscribe,
        send=lambda cid, text: send_to_chat(cid, text),
        welcome=WELCOME,
        already=ALREADY,
        goodbye=GOODBYE,
        help_text=HELP,
    )


def process_commands(*, store: SubscriberStore | None = None) -> int:
    if not TELEGRAM_BOT_TOKEN:
        return 0
    if blob_configured():
        print(
            "  Skipping SportX getUpdates (Blob/webhook mode). "
            "Commands are handled by the Vercel webhook."
        )
        return 0
    store = store or SubscriberStore()
    store.ensure_admin()
    offset = store.get_offset()
    handled = 0

    try:
        response = httpx.get(
            _api("getUpdates"),
            params={"offset": offset, "timeout": 0, "allowed_updates": '["message"]'},
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        print(f"  Warning: SportX getUpdates failed: {exc}")
        return 0

    for update in payload.get("result") or []:
        update_id = int(update["update_id"])
        store.set_offset(update_id + 1)
        if handle_update(update):
            handled += 1

    return handled
