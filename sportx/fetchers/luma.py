"""Luma Bengaluru discover feed — sports / fitness listings only."""

from __future__ import annotations

import json
import re

import httpx

from sportx.category import with_category
from sportx.fetchers._common import USER_AGENT, parse_datetime
from sportx.filter import is_sports_event
from sportx.models import SportEvent

_DISCOVER_URLS = (
    "https://luma.com/bengaluru",
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


def _from_luma_dict(
    item: dict,
    *,
    organisation: str | None = None,
) -> SportEvent | None:
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
    image = item.get("cover_url") or item.get("social_image_url")
    if isinstance(image, str):
        image = image.replace("\\/", "/")
    else:
        image = None

    hints = f"{title} {location}"
    if not is_sports_event(title, hints):
        return None

    if not organisation:
        organisation = _organisation_from_hosts_and_calendar(
            item.get("hosts"), item.get("calendar")
        )

    event = SportEvent(
        id=str(api_id),
        title=title,
        platform="luma",
        registration_url=registration_url,
        mode="online"
        if str(item.get("location_type") or "").lower() == "online"
        else "offline",
        location=str(location),
        deadline=parse_datetime(item.get("start_at") or item.get("end_at")),
        organisation=organisation,
        image_url=image,
        description=None,
    )
    return with_category(event, hints=hints)


def fetch_luma_sports() -> list[SportEvent]:
    out: list[SportEvent] = []
    seen: set[str] = set()
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html"}

    with httpx.Client(timeout=30.0, headers=headers, follow_redirects=True) as client:
        for url in _DISCOVER_URLS:
            try:
                resp = client.get(url)
                resp.raise_for_status()
            except Exception:
                continue
            payload = _load_next_data(resp.text)
            if not payload:
                continue
            entries = (
                ((payload.get("props") or {}).get("pageProps") or {})
                .get("initialData", {})
                .get("data", {})
                .get("events")
            )
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                raw = entry.get("event")
                if not isinstance(raw, dict):
                    continue
                org = _organisation_from_hosts_and_calendar(
                    entry.get("hosts"), entry.get("calendar")
                )
                event = _from_luma_dict(raw, organisation=org)
                if not event or event.id in seen:
                    continue
                seen.add(event.id)
                out.append(event)

    return out
