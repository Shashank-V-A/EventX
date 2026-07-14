"""AllEvents Bangalore sports listings via categorization API."""

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
    # AllEvents often uses unix timestamps
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
    # Title-first: do not trust AllEvents category tags (travel often tagged "sports")
    if not is_sports_event(title, location):
        return None
    hints = f"{title} {location}"

    event = SportEvent(
        id=eid,
        title=title,
        platform="allevents",
        registration_url=url.split("?")[0],
        mode="offline",
        location=location,
        deadline=deadline,
        organisation=str(org) if org else None,
    )
    return with_category(event, hints=hints)


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
        # Session cookies help some AllEvents endpoints
        client.get("https://allevents.in/bangalore/sports")

        for category in _CATEGORIES:
            for page in range(1, _MAX_PAGES + 1):
                payload = {
                    "venue": 0,
                    "page": page,
                    "rows": _ROWS,
                    "tag_type": "",
                    "sdate": 0,
                    "edate": 0,
                    "city": "bangalore",
                    "keywords": None,
                    "category": [category],
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

    return out
