import httpx

from eventx.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from eventx.models import HackathonEvent

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def _format_deadline(event: HackathonEvent) -> str:
    if not event.deadline:
        return "Not specified"
    return event.deadline.strftime("%d %b %Y, %I:%M %p IST")


def format_message(event: HackathonEvent) -> str:
    location = event.location or "Not specified"
    org = event.organisation or "Unknown"

    return (
        f"🚀 <b>New Hackathon — Bangalore</b>\n\n"
        f"<b>{event.title}</b>\n\n"
        f"📍 Location: {location}\n"
        f"🌐 Mode: {event.mode}\n"
        f"🏢 Host: {org}\n"
        f"⏰ Registration closes: {_format_deadline(event)}\n"
        f"🔗 <a href=\"{event.registration_url}\">Register on Unstop</a>"
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


def notify_events(events: list[HackathonEvent]) -> int:
    sent = 0
    for event in events:
        send_telegram_message(format_message(event))
        sent += 1
    return sent
