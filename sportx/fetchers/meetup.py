"""Meetup Bengaluru sports / fitness events via find pages + event enrichment."""

from __future__ import annotations

import json
import re

import httpx

from sportx.category import category_label, with_category
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
    "https://www.meetup.com/find/?keywords=padel&location=in--Bengaluru&source=EVENTS",
    "https://www.meetup.com/find/?keywords=cycling&location=in--Bengaluru&source=EVENTS",
    "https://www.meetup.com/find/?keywords=swimming&location=in--Bengaluru&source=EVENTS",
    "https://www.meetup.com/find/?keywords=yoga&location=in--Bengaluru&source=EVENTS",
    "https://www.meetup.com/find/?keywords=5k&location=in--Bengaluru&source=EVENTS",
    "https://www.meetup.com/find/?keywords=10k&location=in--Bengaluru&source=EVENTS",
)

_GENERIC_TITLES = {
    "match is on",
    "game on",
    "open play",
    "let's play",
    "lets play",
    "sports meetup",
}

_TIMEY_DESC = re.compile(
    r"^("
    r"(every\s+)?(mon|tue|wed|thu|fri|sat|sun)[a-z]*"
    r"|monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r"|\d{1,2}([.:]\d{2})?\s*(am|pm)?"
    r"|[\d\s.:apm]+"
    r")+$",
    re.I,
)


def _load_next_data(html: str) -> dict | None:
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
        flags=re.DOTALL,
    )
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _events_from_next_data(html: str) -> list[dict]:
    payload = _load_next_data(html)
    if not payload:
        return []

    # Event detail pages expose a rich object here
    page_event = ((payload.get("props") or {}).get("pageProps") or {}).get("event")
    if isinstance(page_event, dict) and page_event.get("title"):
        return [page_event]

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


def _photo_url(photo: object) -> str | None:
    if isinstance(photo, str) and photo.startswith("http"):
        # Ignore Meetup generic flyers / member avatar base paths as “covers”
        low = photo.lower()
        if "meetup-flyer" in low or "fallbacks" in low or "classic-member" in low:
            return None
        return photo
    if not isinstance(photo, dict):
        return None
    for key in ("highres", "highres_link", "photo_link", "url", "baseUrl", "id"):
        val = photo.get(key)
        if isinstance(val, str) and val.startswith("http"):
            return _photo_url(val)
    base = photo.get("baseUrl")
    photo_id = photo.get("id")
    if isinstance(base, str) and photo_id and "classic-member" not in base:
        # Meetup CDN pattern
        return f"{base.rstrip('/')}/{photo_id}"
    return None


def _pick_image(node: dict) -> str | None:
    for key in (
        "featuredEventPhoto",
        "displayPhoto",
        "imageUrl",
        "featured_photo",
        "coverUrl",
        "photoUrl",
        "image",
    ):
        url = _photo_url(node.get(key))
        if url:
            return url
    group = node.get("group") or {}
    if isinstance(group, dict):
        for key in ("keyGroupPhoto", "groupPhoto", "coverPhoto"):
            url = _photo_url(group.get(key))
            if url:
                return url
    return None


def _is_useless_description(text: str) -> bool:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) < 12:
        return True
    if _TIMEY_DESC.match(cleaned.replace(",", " ")):
        return True
    # Meetup often puts only a schedule fragment in description
    if len(cleaned) < 40 and re.search(r"\b(am|pm)\b", cleaned, re.I):
        return True
    return False


def _pick_description(node: dict, *, category: str, group_name: str, venue: dict) -> str | None:
    for key in ("description", "shortDescription", "summary"):
        val = node.get(key)
        if isinstance(val, str) and val.strip() and not _is_useless_description(val):
            return val.strip()

    bits: list[str] = []
    sport = category_label(category)
    if sport and sport != "Sports Event":
        bits.append(f"{sport} meetup in Bangalore")
    elif group_name:
        bits.append(f"{group_name.strip()} — sports meetup in Bangalore")

    series = node.get("series") or {}
    if isinstance(series, dict) and series.get("description"):
        bits.append(str(series["description"]).strip())

    venue_name = venue.get("name") if isinstance(venue, dict) else None
    venue_addr = venue.get("address") if isinstance(venue, dict) else None
    place = ", ".join(str(x) for x in (venue_name, venue_addr) if x)
    if place:
        bits.append(f"Venue: {place}")

    return ". ".join(bits) if bits else None


def _enrich_title(title: str, group_name: str) -> str:
    if not group_name:
        return title
    group_name = re.sub(r"\s+", " ", group_name).strip()
    if title.lower().strip() in _GENERIC_TITLES:
        return f"{title} — {group_name}"
    if len(title) < 28 and group_name.lower() not in title.lower():
        return f"{title} — {group_name}"
    return title


def _venue_location(venue: dict, group: dict) -> str:
    bits = [
        venue.get("name"),
        venue.get("address"),
        venue.get("city") or group.get("city"),
    ]
    cleaned = [re.sub(r"\s+", " ", str(b)).strip() for b in bits if b]
    return ", ".join(cleaned) if cleaned else "Bengaluru"


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

                group_name = str(
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
                            group_name,
                            title,
                        ],
                    )
                )

                # Find pages are Bangalore-scoped; still require a real geo signal
                # (do not invent "Bengaluru" into every listing).
                if not (
                    mentions_bangalore(city_blob) or "bengaluru" in page_url.lower()
                ):
                    continue
                if not is_sports_event(title, city_blob):
                    continue

                event = SportEvent(
                    id=eid,
                    title=_enrich_title(title, group_name),
                    platform="meetup",
                    registration_url=url,
                    mode="offline",
                    location=_venue_location(venue, group),
                    deadline=parse_datetime(
                        node.get("dateTime") or node.get("date") or node.get("startTime")
                    ),
                    organisation=re.sub(r"\s+", " ", group_name).strip() or None,
                    image_url=_pick_image(node),
                    description=None,
                )
                event = with_category(event, hints=city_blob)
                event.description = _pick_description(
                    node,
                    category=event.category,
                    group_name=group_name,
                    venue=venue if isinstance(venue, dict) else {},
                )
                seen.add(eid)
                out.append(event)

        # Enrich listings that still lack image / venue / description
        for event in out:
            if event.image_url and event.description and event.organisation and event.location:
                # Still refresh from detail page once for richer fields
                if " — " in event.title and event.description and "Venue:" in (event.description or ""):
                    continue
            try:
                page = client.get(event.registration_url)
                if page.status_code != 200:
                    continue
                nodes = _events_from_next_data(page.text)
                if not nodes:
                    continue
                node = next(
                    (
                        n
                        for n in nodes
                        if event.id in str(n.get("id") or n.get("eventId") or "")
                    ),
                    nodes[0],
                )
                venue = node.get("venue") or {}
                group = node.get("group") or {}
                if not isinstance(venue, dict):
                    venue = {}
                if not isinstance(group, dict):
                    group = {}
                group_name = str(group.get("name") or event.organisation or "")
                base_title = event.title.split(" — ", 1)[0]
                event.title = _enrich_title(base_title, group_name)
                event.organisation = re.sub(r"\s+", " ", group_name).strip() or event.organisation
                if venue:
                    event.location = _venue_location(venue, group)
                event.image_url = event.image_url or _pick_image(node)
                event = with_category(event, hints=f"{event.title} {group_name}")
                event.description = _pick_description(
                    node,
                    category=event.category,
                    group_name=group_name,
                    venue=venue,
                )
            except Exception:
                continue

    return out
