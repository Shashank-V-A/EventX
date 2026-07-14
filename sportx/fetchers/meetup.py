"""Meetup Bengaluru sports / fitness events via find pages + GraphQL fallback."""

from __future__ import annotations

import json
import re

import httpx

from sportx.category import with_category
from sportx.fetchers._common import USER_AGENT, parse_datetime
from sportx.filter import is_sports_event, mentions_bangalore
from sportx.models import SportEvent

_FIND_URLS = (
    "https://www.meetup.com/find/?keywords=sports&location=in--Bengaluru&source=EVENTS",
    "https://www.meetup.com/find/?keywords=marathon&location=in--Bengaluru&source=EVENTS",
    "https://www.meetup.com/find/?keywords=cricket&location=in--Bengaluru&source=EVENTS",
    "https://www.meetup.com/find/?keywords=pickleball&location=in--Bengaluru&source=EVENTS",
    "https://www.meetup.com/find/?keywords=badminton&location=in--Bengaluru&source=EVENTS",
    "https://www.meetup.com/find/?keywords=running&location=in--Bengaluru&source=EVENTS",
    "https://www.meetup.com/find/?keywords=football&location=in--Bengaluru&source=EVENTS",
    "https://www.meetup.com/find/?keywords=tennis&location=in--Bengaluru&source=EVENTS",
    "https://www.meetup.com/find/?keywords=cycling&location=in--Bengaluru&source=EVENTS",
    "https://www.meetup.com/find/?keywords=yoga&location=in--Bengaluru&source=EVENTS",
)


def _events_from_next_data(html: str) -> list[dict]:
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
        flags=re.DOTALL,
    )
    if not match:
        return []
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []

    found: list[dict] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            title = node.get("title") or node.get("name")
            url = (
                node.get("eventUrl")
                or node.get("url")
                or node.get("link")
                or node.get("seoUrl")
            )
            eid = node.get("id") or node.get("eventId")
            if title and url and ("meetup.com" in str(url) or str(url).startswith("/")):
                found.append(node)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return found


def _normalize_url(url: str) -> str:
    if url.startswith("/"):
        return f"https://www.meetup.com{url}"
    return url


def fetch_meetup_sports() -> list[SportEvent]:
    out: list[SportEvent] = []
    seen: set[str] = set()
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
    }

    with httpx.Client(timeout=30.0, headers=headers, follow_redirects=True) as client:
        for page_url in _FIND_URLS:
            try:
                resp = client.get(page_url)
                if resp.status_code != 200:
                    continue
                nodes = _events_from_next_data(resp.text)
            except Exception:
                continue

            for node in nodes:
                title = str(node.get("title") or node.get("name") or "").strip()
                url = _normalize_url(str(node.get("eventUrl") or node.get("url") or ""))
                eid = str(node.get("id") or node.get("eventId") or url)
                if not title or not url or eid in seen:
                    continue

                venue = node.get("venue") or {}
                group = node.get("group") or {}
                if isinstance(venue, str):
                    venue = {"name": venue}
                if isinstance(group, str):
                    group = {"name": group}

                # Meetup Next.js payloads often flatten group fields
                group_name = (
                    group.get("name")
                    or node.get("groupName")
                    or node.get("group_name")
                    or node.get("organizerName")
                    or ""
                )
                city_blob = " ".join(
                    filter(
                        None,
                        [
                            str(venue.get("city") or ""),
                            str(venue.get("address") or ""),
                            str(group.get("city") or ""),
                            str(group_name),
                            title,
                            "Bengaluru",
                        ],
                    )
                )

                if not (
                    mentions_bangalore(city_blob)
                    or "bengaluru" in page_url.lower()
                ):
                    continue
                if not is_sports_event(title, city_blob):
                    continue

                seen.add(eid)
                event = SportEvent(
                    id=eid,
                    title=title,
                    platform="meetup",
                    registration_url=url,
                    mode="offline",
                    location=str(venue.get("city") or group.get("city") or "Bengaluru"),
                    deadline=parse_datetime(
                        node.get("dateTime") or node.get("date") or node.get("startTime")
                    ),
                    organisation=str(group_name) or None,
                )
                out.append(with_category(event, hints=city_blob))

    return out
