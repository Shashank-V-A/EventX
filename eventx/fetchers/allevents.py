"""AllEvents.in Bangalore listings — concerts, sports, festivals, local events."""

from __future__ import annotations

import json
import re

import httpx

from eventx.category import with_category
from eventx.fetchers._common import USER_AGENT, parse_datetime
from eventx.models import HackathonEvent

ALLEVENTS_URL = "https://allevents.in/bangalore"
PAGE_URLS = [
    ALLEVENTS_URL,
    "https://allevents.in/bangalore/business",
    "https://allevents.in/bangalore/sports-fitness",
    "https://allevents.in/bangalore/workshops",
    "https://allevents.in/bangalore/music",
]


def _extract_ld_events(html: str) -> list[dict]:
    events: list[dict] = []
    for match in re.finditer(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S
    ):
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "Event":
                events.append(item)
    return events


def _location_from_item(item: dict) -> str | None:
    loc = item.get("location")
    if isinstance(loc, dict):
        name = loc.get("name")
        address = loc.get("address")
        if isinstance(address, dict):
            city = address.get("addressLocality") or "Bengaluru"
            return ", ".join(p for p in (name, city) if p)
        if name:
            return name
        if isinstance(address, str):
            return address
    if isinstance(loc, str):
        return loc
    return "Bengaluru"


def _normalize_item(item: dict) -> HackathonEvent | None:
    title = item.get("name")
    url = item.get("url")
    if not title or not url:
        return None

    event_id = str(url).rstrip("/").split("/")[-1]
    deadline = parse_datetime(item.get("endDate") or item.get("startDate"))
    # AllEvents often gives date-only strings
    if deadline is None and item.get("startDate"):
        try:
            from datetime import datetime

            deadline = datetime.fromisoformat(str(item["startDate"]))
        except ValueError:
            deadline = None

    event = HackathonEvent(
        id=event_id,
        title=title,
        platform="allevents",
        registration_url=url,
        mode="offline",
        location=_location_from_item(item),
        deadline=deadline,
        organisation=None,
        category="event",
    )
    return with_category(event)


def fetch_allevents_events() -> list[HackathonEvent]:
    events: list[HackathonEvent] = []
    seen: set[str] = set()

    with httpx.Client(timeout=40.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        for url in PAGE_URLS:
            try:
                response = client.get(url)
                response.raise_for_status()
            except Exception as exc:
                print(f"  Warning: allevents page failed ({url}): {exc}")
                continue

            for item in _extract_ld_events(response.text):
                event = _normalize_item(item)
                if not event or event.id in seen:
                    continue
                seen.add(event.id)
                events.append(event)

    return events
