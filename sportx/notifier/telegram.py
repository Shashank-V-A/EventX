from __future__ import annotations

import httpx

from sportx.category import category_label
from sportx.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from sportx.models import SportEvent

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

PLATFORM_LABELS = {
    "allevents": "AllEvents",
    "meetup": "Meetup",
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


def format_message(event: SportEvent, *, kind: str = "new") -> str:
    location = _escape(event.location or "Bangalore")
    org = _escape(event.organisation or "See listing")
    platforms = ", ".join(
        PLATFORM_LABELS.get(p, p.title()) for p in (event.platforms or [event.platform])
    )
    subtype = category_label(event.category or "sports")

    if kind == "24h":
        header = "⏰ <b>SportX · starts / closes within 24 hours</b>"
    elif kind == "48h":
        header = "⏰ <b>SportX · starts / closes within 48 hours</b>"
    else:
        header = f"🏅 <b>SportX · New {subtype}</b>"

    lines = [
        header,
        "",
        f"<b>{_escape(event.title)}</b>",
        "",
        f"🏷️ Sport: {_escape(subtype)}",
        f"📍 Location: {location}",
        f"🏢 Host: {org}",
        f"📱 Listed on: {_escape(platforms)}",
        f"📅 When: {_escape(_format_when(event))}",
        f'🔗 <a href="{_escape(event.registration_url)}">Open listing</a>',
    ]
    return "\n".join(lines)


def format_health_alert(platform: str, failures: int, error: str) -> str:
    label = PLATFORM_LABELS.get(platform, platform.title())
    return (
        f"⚠️ <b>SportX health check</b>\n\n"
        f"Source <b>{_escape(label)}</b> failed {failures} runs in a row.\n"
        f"Last error: {_escape(error[:300]) or 'unknown'}\n\n"
        f"Sports alerts from this source may be missing until it recovers."
    )


def send_telegram_message(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError(
            "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in your .env file"
        )

    url = TELEGRAM_API.format(token=TELEGRAM_BOT_TOKEN)
    response = httpx.post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=30.0,
    )
    response.raise_for_status()


def notify_events(events: list[SportEvent], *, kind: str = "new") -> int:
    sent = 0
    for event in events:
        send_telegram_message(format_message(event, kind=kind))
        sent += 1
    return sent


def notify_health_alerts(alerts: list[tuple[str, int, str]]) -> int:
    sent = 0
    for platform, failures, error in alerts:
        send_telegram_message(format_health_alert(platform, failures, error))
        sent += 1
    return sent
