"""AllEvents Bangalore sports listings via categorization API + keyword search."""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone

import httpx

from sportx.category import with_category
from sportx.fetchers._common import USER_AGENT, parse_datetime
from sportx.filter import is_sports_event
from sportx.models import SportEvent

_API = "https://allevents.in/api/index.php/categorization/web/v1/list"
_CATEGORIES = (
    "sports",
    "sports-fitness",
    "health-wellness",
)
_KEYWORDS = (
    "pickleball",
    "marathon",
    "half marathon",
    "cricket",
    "badminton",
    "football",
    "tennis",
    "padel",
    "running",
    "5k",
    "10k",
    "cycling",
    "swimming",
    "yoga",
    "triathlon",
)
_ROWS = 40
_MAX_PAGES = 3


def _parse_event(item: dict) -> SportEvent | None:
    title = html.unescape(
        (item.get("eventname") or item.get("eventname_raw") or "").strip()
    )
    url = (item.get("event_url") or item.get("share_url") or "").strip()
    if not title or not url:
        return None
    if url.startswith("/"):
        url = f"https://allevents.in{url}"

    location_bits = [
        item.get("location"),
        item.get("venue", {}).get("city") if isinstance(item.get("venue"), dict) else None,
        item.get("city"),
        "Bangalore",
    ]
    location = next((str(x) for x in location_bits if x), "Bangalore")

    when = (
        item.get("start_time")
        or item.get("start_time_display")
        or item.get("event_date")
        or item.get("start_date")
    )
    deadline = None
    if isinstance(when, (int, float)) or (isinstance(when, str) and str(when).isdigit()):
        try:
            deadline = datetime.fromtimestamp(int(when), tz=timezone.utc)
        except (OSError, ValueError, OverflowError):
            deadline = None
    else:
        deadline = parse_datetime(str(when) if when else None)

    org = item.get("organizer") or item.get("owner_name")
    if isinstance(org, dict):
        org = org.get("name")
    if org and "http" in str(org):
        org = None

    eid = str(item.get("event_id") or url.rstrip("/").split("/")[-1])
    if not is_sports_event(title, location):
        return None
    hints = f"{title} {location}"

    image = (
        item.get("thumb_url_large")
        or item.get("banner_url")
        or item.get("thumb_url")
        or item.get("cover_image")
    )
    if isinstance(image, str):
        image = image.replace("\\/", "/")
    else:
        image = None

    desc = item.get("description") or item.get("short_desc") or item.get("event_description")
    if isinstance(desc, str):
        desc = html.unescape(desc.strip())
    else:
        desc = None

    venue_name = None
    if isinstance(item.get("venue"), dict):
        venue_name = item["venue"].get("fullname") or item["venue"].get("full_address")
    if venue_name:
        location = (
            f"{venue_name}, {location}"
            if location and location not in str(venue_name)
            else str(venue_name)
        )

    event = SportEvent(
        id=eid,
        title=title,
        platform="allevents",
        registration_url=url.split("?")[0],
        mode="offline",
        location=location,
        deadline=deadline,
        organisation=str(org) if org else None,
        image_url=image,
        description=desc,
    )
    return with_category(event, hints=hints)


def _fetch_pages(
    client: httpx.Client,
    *,
    category: list | int,
    keywords: str | None,
    seen: set[str],
    out: list[SportEvent],
) -> None:
    for page in range(1, _MAX_PAGES + 1):
        payload = {
            "venue": 0,
            "page": page,
            "rows": _ROWS,
            "tag_type": "",
            "sdate": 0,
            "edate": 0,
            "city": "bangalore",
            "keywords": keywords,
            "category": category,
            "formats": 0,
            "sort_by_score_only": True,
        }
        try:
            resp = client.post(_API, content=json.dumps(payload))
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            break

        if not data or data is False or not isinstance(data, dict):
            break

        items = data.get("item") or []
        if not items:
            break

        for item in items:
            if not isinstance(item, dict):
                continue
            event = _parse_event(item)
            if not event or event.id in seen:
                continue
            seen.add(event.id)
            out.append(event)

        count = int(data.get("count") or 0)
        if page * _ROWS >= count or len(items) < _ROWS:
            break


def fetch_allevents_sports() -> list[SportEvent]:
    out: list[SportEvent] = []
    seen: set[str] = set()
    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://allevents.in",
        "Referer": "https://allevents.in/bangalore/sports",
    }

    with httpx.Client(timeout=30.0, headers=headers, follow_redirects=True) as client:
        client.get("https://allevents.in/bangalore/sports")

        for category in _CATEGORIES:
            _fetch_pages(
                client, category=[category], keywords=None, seen=seen, out=out
            )

        for keyword in _KEYWORDS:
            _fetch_pages(client, category=0, keywords=keyword, seen=seen, out=out)

    return out
