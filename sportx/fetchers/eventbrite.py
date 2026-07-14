"""Eventbrite Bangalore sports & fitness listings (when available)."""

from __future__ import annotations

import json

import httpx

from sportx.category import with_category
from sportx.fetchers._common import USER_AGENT, parse_datetime
from sportx.filter import is_sports_event
from sportx.models import SportEvent

_PAGES = (
    "https://www.eventbrite.com/b/india--bangalore/sports-and-fitness/",
    "https://www.eventbrite.com/d/india--bangalore/pickleball/",
    "https://www.eventbrite.com/d/india--bangalore/marathon/",
    "https://www.eventbrite.com/d/india--bangalore/cricket/",
    "https://www.eventbrite.com/d/india--bangalore/badminton/",
    "https://www.eventbrite.com/d/india--bangalore/running/",
    "https://www.eventbrite.com/d/india--bangalore/football/",
)


def _extract_server_data(html: str) -> dict | None:
    marker = "window.__SERVER_DATA__ = "
    i = html.find(marker)
    if i < 0:
        return None
    i += len(marker)
    depth = 0
    in_str = False
    esc = False
    for j in range(i, len(html)):
        ch = html[j]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(html[i : j + 1])
                except json.JSONDecodeError:
                    return None
    return None


def _parse_result(item: dict) -> SportEvent | None:
    name = item.get("name") or item.get("title") or ""
    if isinstance(name, dict):
        name = name.get("text") or name.get("html") or ""
    title = str(name).strip()
    if not title:
        return None

    url = item.get("url") or item.get("shareable") or ""
    if isinstance(url, dict):
        url = url.get("url") or ""
    url = str(url).strip()
    if not url.startswith("http"):
        eid = item.get("id") or item.get("eventbrite_event_id")
        if eid:
            url = f"https://www.eventbrite.com/e/{eid}"
        else:
            return None

    venue = item.get("venue") or item.get("primary_venue") or {}
    if isinstance(venue, dict):
        location = (
            venue.get("name")
            or (venue.get("address") or {}).get("localized_area_display")
            or (venue.get("address") or {}).get("city")
            or "Bangalore"
        )
    else:
        location = "Bangalore"

    start = None
    start_obj = item.get("start") or item.get("start_date") or {}
    if isinstance(start_obj, dict):
        start = start_obj.get("utc") or start_obj.get("local")
    elif isinstance(start_obj, str):
        start = start_obj

    image = None
    logo = item.get("logo") or item.get("image") or {}
    if isinstance(logo, dict):
        image = logo.get("url") or logo.get("original") or logo.get("url_path")
    elif isinstance(logo, str):
        image = logo

    org = None
    organizer = item.get("organizer") or {}
    if isinstance(organizer, dict):
        org = organizer.get("name")

    if not is_sports_event(title, str(location)):
        return None

    eid = str(item.get("id") or url.rstrip("/").split("/")[-1])
    event = SportEvent(
        id=eid,
        title=title,
        platform="eventbrite",
        registration_url=url.split("?")[0],
        mode="online" if item.get("online_event") else "offline",
        location=str(location),
        deadline=parse_datetime(start),
        organisation=str(org) if org else None,
        image_url=image,
        description=None,
    )
    return with_category(event, hints=f"{title} {location}")


def fetch_eventbrite_sports() -> list[SportEvent]:
    out: list[SportEvent] = []
    seen: set[str] = set()
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
    }

    with httpx.Client(timeout=30.0, headers=headers, follow_redirects=True) as client:
        for page_url in _PAGES:
            try:
                resp = client.get(page_url)
                if resp.status_code != 200:
                    continue
                data = _extract_server_data(resp.text)
            except Exception:
                continue
            if not data:
                continue

            buckets = []
            event_data = data.get("event_data") or {}
            if isinstance(event_data, dict):
                for key in ("active_search", "category_search"):
                    section = event_data.get(key) or {}
                    events = (section.get("events") or {}).get("results") or []
                    if isinstance(events, list):
                        buckets.extend(events)

            for item in buckets:
                if not isinstance(item, dict):
                    continue
                event = _parse_result(item)
                if not event or event.id in seen:
                    continue
                seen.add(event.id)
                out.append(event)

    return out
