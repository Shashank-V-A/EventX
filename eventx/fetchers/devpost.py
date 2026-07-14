from datetime import datetime

import httpx

from eventx.category import with_category
from eventx.fetchers._common import USER_AGENT, strip_html
from eventx.models import HackathonEvent

DEVPOST_API = "https://devpost.com/api/hackathons"
MAX_PAGES = 5


def _parse_end_date(date_str: str | None) -> datetime | None:
    if not date_str or " - " not in date_str:
        return None

    try:
        _, end_str = date_str.split(" - ", 1)
        end_str = end_str.strip()
        month_names = (
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        )
        if not any(month in end_str for month in month_names):
            start_str = date_str.split(" - ", 1)[0].strip()
            start_month = start_str.split(" ")[0]
            end_str = f"{start_month} {end_str}"
        return datetime.strptime(end_str, "%b %d, %Y")
    except ValueError:
        return None


def _format_prize(item: dict) -> str | None:
    amount = strip_html(item.get("prize_amount"))
    counts = item.get("prizes_counts") or {}
    parts = []
    if amount:
        parts.append(amount)
    cash = counts.get("cash")
    other = counts.get("other")
    extras = []
    if cash:
        extras.append(f"{cash} cash")
    if other:
        extras.append(f"{other} other")
    if extras:
        parts.append("(" + ", ".join(extras) + ")")
    return " ".join(parts) if parts else None


def _normalize_item(item: dict) -> HackathonEvent | None:
    if item.get("open_state") == "ended":
        return None

    event_id = item.get("id")
    title = item.get("title")
    url = item.get("url")
    if not event_id or not title or not url:
        return None

    displayed = item.get("displayed_location") or {}
    location = displayed.get("location") or "Online"
    mode = "online" if location.lower() in ("online", "everywhere") else "offline"
    themes = item.get("themes") or []
    theme_names = ", ".join(t.get("name") for t in themes[:3] if t.get("name"))

    return with_category(
        HackathonEvent(
            id=str(event_id),
            title=title,
            platform="devpost",
            registration_url=url,
            mode=mode,
            location=location,
            deadline=_parse_end_date(item.get("submission_period_dates")),
            organisation=item.get("organization_name"),
            prize_pool=_format_prize(item),
            eligibility=theme_names or None,
            category="hackathon",
        )
    )


def fetch_devpost_hackathons() -> list[HackathonEvent]:
    events: list[HackathonEvent] = []

    with httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT}) as client:
        for page in range(1, MAX_PAGES + 1):
            response = client.get(DEVPOST_API, params={"page": page})
            response.raise_for_status()
            batch = response.json().get("hackathons", [])
            if not batch:
                break

            ended = False
            for item in batch:
                if item.get("open_state") == "ended":
                    ended = True
                    break
                event = _normalize_item(item)
                if event:
                    events.append(event)

            if ended:
                break

    return events
