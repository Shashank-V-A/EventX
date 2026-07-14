"""Shared Telegram command handling for polling or Vercel webhooks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def parse_command(text: str) -> str:
    return text.split()[0].split("@")[0].lower()


def handle_command_update(
    update: dict[str, Any],
    *,
    subscribe: Callable[..., bool],
    unsubscribe: Callable[[str], bool],
    send: Callable[[str, str], bool],
    welcome: str,
    already: str,
    goodbye: str,
    help_text: str,
) -> bool:
    """Handle one Telegram update. Returns True if a command was processed."""
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id") or "")
    if not chat_id:
        return False
    text = (message.get("text") or "").strip()
    if not text:
        return False
    cmd = parse_command(text)
    username = (message.get("from") or {}).get("username")
    first_name = (message.get("from") or {}).get("first_name")

    if cmd in {"/start", "/subscribe"}:
        is_new = subscribe(chat_id, username=username, first_name=first_name)
        send(chat_id, welcome if is_new else already)
        return True
    if cmd in {"/stop", "/unsubscribe"}:
        unsubscribe(chat_id)
        send(chat_id, goodbye)
        return True
    if cmd == "/help":
        send(chat_id, help_text)
        return True
    return False
