"""MLH season events — parses embedded event JSON from mlh.io seasons pages."""

import json

import httpx

from eventx.category import with_category
from eventx.fetchers._common import USER_AGENT, parse_datetime
from eventx.models import HackathonEvent

SEASON_YEARS = (2025, 2026, 2027)


def _extract_events_json(html: str) -> list[dict]:
    # Embedded event objects contain "venueAddress" / "formatType"
    marker = '"formatType":'
    idx = html.find(marker)
    if idx == -1:
        return []

    start = html.rfind("[", 0, idx)
    if start == -1:
        return []

    # Expanding window until JSON array parses
    for end in range(idx + 200, min(len(html), start + 800_000), 8_000):
        chunk = html[start:end]
        last = chunk.rfind("}]")
        if last == -1:
            continue
        try:
            data = json.loads(chunk[: last + 2])
            if isinstance(data, list) and data and isinstance(data[0], dict) and "slug" in data[0]:
                return data
        except json.JSONDecodeError:
            continue
    return []


def _normalize_item(item: dict) -> HackathonEvent | None:
    status = (item.get("status") or "").lower()
    if status in {"ended", "cancelled", "canceled"}:
        return None

    event_id = item.get("id") or item.get("slug")
    title = (item.get("name") or "").strip()
    if not event_id or not title:
        return None

    venue = item.get("venueAddress") or {}
    city = venue.get("city")
    state = venue.get("state")
    country = venue.get("country")
    location = item.get("location")
    if city or state:
        location = ", ".join(p for p in (city, state, country) if p)

    format_type = (item.get("formatType") or "").lower()
    if format_type in {"virtual", "online"}:
        mode = "online"
    elif format_type in {"hybrid"}:
        mode = "hybrid"
    else:
        mode = "offline"

    website = item.get("websiteUrl") or item.get("website_url")
    slug = item.get("slug")
    registration_url = website or (f"https://mlh.io/events/{slug}" if slug else None)
    if not registration_url:
        return None

    return with_category(
        HackathonEvent(
            id=str(event_id),
            title=title,
            platform="mlh",
            registration_url=registration_url,
            mode=mode,
            location=location,
            deadline=parse_datetime(item.get("endsAt") or item.get("ends_at")),
            organisation="Major League Hacking",
            eligibility="Students (MLH)",
            prize_pool=None,
            team_size=None,
            category="hackathon",
        )
    )


def fetch_mlh_hackathons() -> list[HackathonEvent]:
    events: list[HackathonEvent] = []
    seen: set[str] = set()

    with httpx.Client(timeout=45.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        for year in SEASON_YEARS:
            response = client.get(f"https://mlh.io/seasons/{year}/events")
            if response.status_code != 200:
                continue
            for item in _extract_events_json(response.text):
                event = _normalize_item(item)
                if not event or event.id in seen:
                    continue
                seen.add(event.id)
                events.append(event)

    return events
