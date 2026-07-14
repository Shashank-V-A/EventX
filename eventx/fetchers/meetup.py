"""Meetup Bengaluru upcoming in-person events (via Meetup find page Apollo state)."""

from __future__ import annotations

import json
import re

import httpx

from eventx.category import with_category
from eventx.fetchers._common import USER_AGENT, parse_datetime
from eventx.models import HackathonEvent

MEETUP_FIND_URL = (
    "https://www.meetup.com/find/"
    "?location=in--Bengaluru&source=EVENTS&eventType=inPerson"
)


def _resolve_ref(apollo: dict, value):
    if isinstance(value, dict) and "__ref" in value:
        return apollo.get(value["__ref"])
    return value


def _normalize_event(node: dict, apollo: dict) -> HackathonEvent | None:
    event_id = node.get("id")
    title = node.get("title")
    url = node.get("eventUrl")
    if not event_id or not title or not url:
        return None

    venue = _resolve_ref(apollo, node.get("venue")) or {}
    location_parts = []
    if isinstance(venue, dict):
        for key in ("name", "address", "city"):
            if venue.get(key):
                location_parts.append(venue[key])
    location = ", ".join(location_parts) if location_parts else "Bengaluru"

    group = _resolve_ref(apollo, node.get("group")) or {}
    organisation = group.get("name") if isinstance(group, dict) else None

    event = HackathonEvent(
        id=str(event_id),
        title=title,
        platform="meetup",
        registration_url=url,
        mode="offline" if node.get("eventType") != "ONLINE" else "online",
        location=location,
        deadline=parse_datetime(node.get("dateTime")),
        organisation=organisation,
        category="meetup",
    )
    return with_category(event, hints=node.get("description") or "")


def fetch_meetup_events() -> list[HackathonEvent]:
    with httpx.Client(timeout=40.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        response = client.get(MEETUP_FIND_URL)
        response.raise_for_status()

    match = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', response.text, re.S
    )
    if not match:
        return []

    payload = json.loads(match.group(1))
    apollo = payload.get("props", {}).get("pageProps", {}).get("__APOLLO_STATE__", {})
    events: list[HackathonEvent] = []
    seen: set[str] = set()

    for node in apollo.values():
        if not isinstance(node, dict) or node.get("__typename") != "Event":
            continue
        event = _normalize_event(node, apollo)
        if not event or event.id in seen:
            continue
        seen.add(event.id)
        events.append(event)

    return events
