from __future__ import annotations

import html
import re

from sportx.category import category_label
from sportx.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from sportx.models import SportEvent
from sportx.subscribers import (
    SubscriberStore,
    send_photo_to_chat,
    send_to_chat,
)

PLATFORM_LABELS = {
    "allevents": "AllEvents",
    "meetup": "Meetup",
    "luma": "Luma",
    "eventbrite": "Eventbrite",
}


def _format_when(event: SportEvent) -> str:
    if not event.deadline:
        return "See listing"
    try:
        return event.deadline.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return str(event.deadline)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _clean_description(text: str | None, limit: int = 280) -> str | None:
    if not text:
        return None
    plain = re.sub(r"<[^>]+>", " ", text)
    plain = html.unescape(plain)
    plain = re.sub(r"\s+", " ", plain).strip()
    if not plain:
        return None
    if len(plain) > limit:
        plain = plain[: limit - 1].rstrip() + "…"
    return plain


def format_message(event: SportEvent, *, kind: str = "new") -> str:
    location = _escape(event.location or "Bangalore")
    org = _escape(event.organisation) if event.organisation else None
    platforms = ", ".join(
        PLATFORM_LABELS.get(p, p.title())
        for p in (event.platforms or [event.platform])
        if p and p != "reminder"
    ) or "See listing"
    subtype = category_label(event.category or "sports")
    description = _clean_description(event.description)

    if kind == "24h":
        header = "⏰ <b>SportX · starts within 24 hours</b>"
    elif kind == "48h":
        header = "⏰ <b>SportX · starts within 48 hours</b>"
    else:
        header = f"🏅 <b>SportX · New {subtype}</b>"

    lines = [
        header,
        "",
        f"<b>{_escape(event.title)}</b>",
        "",
    ]
    if description:
        lines.extend([_escape(description), ""])

    lines.extend(
        [
            f"🏷️ Sport: {_escape(subtype)}",
            f"📍 Location: {location}",
        ]
    )
    if org:
        lines.append(f"🏢 Host: {org}")
    lines.extend(
        [
            f"📱 Listed on: {_escape(platforms)}",
            f"📅 When: {_escape(_format_when(event))}",
            f'🔗 <a href="{_escape(event.registration_url)}">Open listing</a>',
        ]
    )
    return "\n".join(lines)


def format_health_alert(platform: str, failures: int, error: str) -> str:
    label = PLATFORM_LABELS.get(platform, platform.title())
    return (
        f"⚠️ <b>SportX health check</b>\n\n"
        f"Source <b>{_escape(label)}</b> failed {failures} runs in a row.\n"
        f"Last error: {_escape(error[:300]) or 'unknown'}\n\n"
        f"Sports alerts from this source may be missing until it recovers."
    )


def send_telegram_message(text: str, *, disable_preview: bool = True) -> None:
    """Admin-only message (idle heartbeat / health)."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError(
            "Set SPORTX_TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in your .env file"
        )
    send_to_chat(str(TELEGRAM_CHAT_ID), text, disable_preview=disable_preview)


def notify_events(events: list[SportEvent], *, kind: str = "new") -> int:
    """Broadcast real event alerts to every active subscriber."""
    store = SubscriberStore()
    recipients = store.list_active_chat_ids()
    sent = 0
    for event in events:
        caption = format_message(event, kind=kind)
        for chat_id in recipients:
            try:
                ok = False
                if event.image_url:
                    try:
                        ok = send_photo_to_chat(chat_id, event.image_url, caption)
                    except Exception:
                        ok = False
                if not ok:
                    ok = send_to_chat(chat_id, caption, disable_preview=True)
                if ok:
                    sent += 1
            except Exception as exc:
                print(f"  Warning: SportX send failed ({chat_id}): {exc}")
    return sent


def notify_health_alerts(alerts: list[tuple[str, int, str]]) -> int:
    sent = 0
    for platform, failures, error in alerts:
        send_telegram_message(format_health_alert(platform, failures, error))
        sent += 1
    return sent


def notify_scan_idle() -> None:
    """Idle heartbeat — admin only."""
    send_telegram_message(
        "✅ <b>SportX</b>\nScan done — no new events found."
    )
