"""
Luma / lu.ma fetcher for HackathonX.

Discovers events from city calendars (default: https://luma.com/bengaluru)
embedded in the page's Next.js data. Optional extra URLs via LUMA_EVENT_URLS
(comma-separated discover calendars or single event pages).
"""

from __future__ import annotations

import json
import os
import re

import httpx

from eventx.category import with_category
from eventx.fetchers._common import USER_AGENT, parse_datetime
from eventx.models import HackathonEvent

_DEFAULT_DISCOVER = ("https://luma.com/bengaluru",)


def _configured_urls() -> list[str]:
    raw = os.getenv("LUMA_EVENT_URLS", "")
    extras = [u.strip() for u in raw.split(",") if u.strip()]
    # Always include Bengaluru discover unless explicitly disabled
    disable_default = os.getenv("LUMA_DISABLE_DEFAULT", "").lower() in (
        "1",
        "true",
        "yes",
    )
    urls = [] if disable_default else list(_DEFAULT_DISCOVER)
    for u in extras:
        if u not in urls:
            urls.append(u)
    return urls


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


def _location_from_geo(geo: object) -> str | None:
    if not isinstance(geo, dict):
        return None
    for key in ("city", "city_state", "address", "full_address", "description"):
        val = geo.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


_ORG_HINTS = (
    "club",
    "venture",
    "lab",
    "labs",
    "foundation",
    "dialogues",
    "community",
    "collective",
    "studio",
    "hq",
    "inc",
    "ltd",
    "university",
    "institute",
    "academy",
    "society",
    "capital",
    "partners",
)


def _organisation_from_hosts_and_calendar(
    hosts: object,
    calendar: object,
) -> str | None:
    """Build a host label from Luma discover entry fields (siblings of event)."""
    names: list[str] = []
    if isinstance(hosts, list):
        for host in hosts:
            if not isinstance(host, dict):
                continue
            name = (host.get("name") or "").strip()
            if name:
                names.append(name)

    orgish = [
        n
        for n in names
        if any(h in n.lower() for h in _ORG_HINTS) or (" " not in n and len(n) > 3)
    ]
    picked = orgish[:3] if orgish else names[:3]
    if picked:
        return ", ".join(picked)

    if isinstance(calendar, dict):
        cal_name = (calendar.get("name") or "").strip()
        if cal_name:
            return cal_name
    return None


def _event_from_luma_dict(
    item: dict,
    *,
    organisation: str | None = None,
) -> HackathonEvent | None:
    title = (item.get("name") or item.get("title") or "").strip()
    if not title:
        return None

    slug = (item.get("url") or "").strip()
    api_id = (item.get("api_id") or item.get("event_api_id") or slug or title).strip()
    if slug.startswith("http"):
        registration_url = slug
    elif slug:
        registration_url = f"https://lu.ma/{slug}"
    else:
        registration_url = f"https://lu.ma/{api_id}"

    location = (
        _location_from_geo(item.get("geo_address_info"))
        or item.get("location")
        or "Bengaluru"
    )
    mode = "online" if str(item.get("location_type") or "").lower() == "online" else "offline"
    deadline = parse_datetime(item.get("end_at") or item.get("start_at"))

    if not organisation:
        organisation = _organisation_from_hosts_and_calendar(
            item.get("hosts"), item.get("calendar")
        )

    return with_category(
        HackathonEvent(
            id=str(api_id),
            title=title,
            platform="luma",
            registration_url=registration_url,
            mode=mode,
            location=str(location),
            deadline=deadline,
            organisation=organisation,
            eligibility=None,
            prize_pool=None,
            team_size=None,
            category="event",
        )
    )


def _events_from_discover_payload(payload: dict) -> list[HackathonEvent]:
    events: list[HackathonEvent] = []
    seen: set[str] = set()

    # City discover pages: props.pageProps.initialData.data.events[].event
    # Hosts/calendar live on the entry, not inside event.
    entries = (
        ((payload.get("props") or {}).get("pageProps") or {})
        .get("initialData", {})
        .get("data", {})
        .get("events")
    )
    if isinstance(entries, list):
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            raw = entry.get("event")
            if not isinstance(raw, dict):
                continue
            org = _organisation_from_hosts_and_calendar(
                entry.get("hosts"), entry.get("calendar")
            )
            event = _event_from_luma_dict(raw, organisation=org)
            if event and event.id not in seen:
                seen.add(event.id)
                events.append(event)
        if events:
            return events

    # Fallback: walk for Luma event dicts
    def walk(node: object) -> None:
        if isinstance(node, dict):
            if node.get("api_id", "").startswith("evt-") and node.get("name") and node.get("url"):
                event = _event_from_luma_dict(node)
                if event and event.id not in seen:
                    seen.add(event.id)
                    events.append(event)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return events


def _parse_event_page(url: str, html: str) -> HackathonEvent | None:
    payload = _load_next_data(html)
    if payload:
        page_props = ((payload.get("props") or {}).get("pageProps") or {})
        # Single event pages sometimes nest under pageProps.event
        page_event = page_props.get("event")
        if isinstance(page_event, dict):
            org = _organisation_from_hosts_and_calendar(
                page_props.get("hosts") or page_event.get("hosts"),
                page_props.get("calendar") or page_event.get("calendar"),
            )
            event = _event_from_luma_dict(page_event, organisation=org)
            if event:
                return event
    title = None
    description = ""
    start = None
    location = None

    m = re.search(
        r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>',
        html,
        re.S,
    )
    if m:
        try:
            data = json.loads(m.group(1))
            if isinstance(data, dict) and data.get("@type") in {"Event", "SocialEvent"}:
                title = data.get("name")
                description = data.get("description") or ""
                start = data.get("endDate") or data.get("startDate")
                loc = data.get("location")
                if isinstance(loc, dict):
                    location = loc.get("name") or (loc.get("address") or {}).get(
                        "addressLocality"
                    )
                elif isinstance(loc, str):
                    location = loc
        except json.JSONDecodeError:
            pass

    if not title:
        og = re.search(r'<meta property="og:title" content="([^"]+)"', html)
        title = og.group(1) if og else None

    if not title:
        return None

    blob = f"{title} {description} {location or ''} {url}".lower()
    mode = "online" if "online" in blob and "bengaluru" not in blob else "offline"
    event_id = url.rstrip("/").split("/")[-1]

    return with_category(
        HackathonEvent(
            id=event_id,
            title=title.replace(" · Luma", "").strip(),
            platform="luma",
            registration_url=url,
            mode=mode,
            location=location or "Bangalore",
            deadline=parse_datetime(start) if isinstance(start, str) else None,
            organisation=None,
            eligibility=None,
            prize_pool=None,
            team_size=None,
            category="event",
        )
    )


def _is_discover_url(url: str) -> bool:
    low = url.lower().rstrip("/")
    return low.endswith("/bengaluru") or "/discover" in low or low.count("/") <= 3


def fetch_luma_hackathons() -> list[HackathonEvent]:
    urls = _configured_urls()
    events: list[HackathonEvent] = []
    seen: set[str] = set()

    with httpx.Client(
        timeout=30.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True
    ) as client:
        for url in urls:
            try:
                response = client.get(url)
                response.raise_for_status()
            except Exception as exc:
                print(f"  Warning: luma URL failed ({url}): {exc}")
                continue

            payload = _load_next_data(response.text)
            batch: list[HackathonEvent] = []
            if payload and (
                _is_discover_url(url)
                or "initialData" in response.text
                or "/bengaluru" in url.lower()
            ):
                batch = _events_from_discover_payload(payload)

            if not batch:
                single = _parse_event_page(url, response.text)
                if single:
                    batch = [single]

            for event in batch:
                if event.id in seen:
                    continue
                seen.add(event.id)
                events.append(event)

    return events
