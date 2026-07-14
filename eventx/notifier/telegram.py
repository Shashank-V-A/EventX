import httpx

from eventx.category import category_label
from eventx.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from eventx.models import HackathonEvent

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

PLATFORM_LABELS = {
    "unstop": "Unstop",
    "devfolio": "Devfolio",
    "devpost": "Devpost",
    "hackerearth": "HackerEarth",
    "hack2skill": "Hack2Skill",
    "dorahacks": "DoraHacks",
    "mlh": "MLH",
    "luma": "Luma",
    "meetup": "Meetup",
    "allevents": "AllEvents",
}


def _format_deadline(event: HackathonEvent) -> str:
    if not event.deadline:
        return "Not specified"
    try:
        return event.deadline.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return str(event.deadline)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def format_message(event: HackathonEvent, *, kind: str = "new") -> str:
    location = _escape(event.location or "Not specified")
    org = _escape(event.organisation or "Unknown")
    platforms = ", ".join(
        PLATFORM_LABELS.get(p, p.title()) for p in (event.platforms or [event.platform])
    )
    category = category_label(event.category or "event")

    if kind == "24h":
        header = "⏰ <b>Starting / closing in 24 hours — Bangalore</b>"
    elif kind == "48h":
        header = "⏰ <b>Starting / closing in 48 hours — Bangalore</b>"
    else:
        header = f"✨ <b>New {category} — Bangalore</b>"

    lines = [
        header,
        "",
        f"<b>{_escape(event.title)}</b>",
        "",
        f"🏷️ Type: {_escape(category)}",
        f"📍 Location: {location}",
        f"🌐 Mode: {_escape(event.mode)}",
        f"🏢 Host: {org}",
        f"📱 Source: {_escape(platforms)}",
    ]

    if event.prize_pool:
        lines.append(f"🏆 Prize: {_escape(event.prize_pool)}")
    if event.team_size:
        lines.append(f"👥 Team size: {_escape(event.team_size)}")
    if event.eligibility:
        lines.append(f"✅ Eligibility: {_escape(event.eligibility)}")

    lines.extend(
        [
            f"⏰ Date / deadline: {_escape(_format_deadline(event))}",
            f'🔗 <a href="{event.registration_url}">Register / details</a>',
        ]
    )
    return "\n".join(lines)


def format_health_alert(platform: str, failures: int, error: str) -> str:
    label = PLATFORM_LABELS.get(platform, platform.title())
    return (
        f"⚠️ <b>EventX health check</b>\n\n"
        f"Source <b>{_escape(label)}</b> failed {failures} runs in a row.\n"
        f"Last error: {_escape(error[:300]) or 'unknown'}\n\n"
        f"New alerts from this source may be missing until it recovers."
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


def notify_events(events: list[HackathonEvent], *, kind: str = "new") -> int:
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
