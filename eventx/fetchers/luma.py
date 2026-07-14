"""
Luma workaround: poll public event pages or discover feeds listed in LUMA_EVENT_URLS.

Luma's official API only covers calendars you own (Luma Plus). For discovery we
accept a comma-separated list of public Luma/lu.ma event URLs in .env and scrape
their Open Graph / JSON-LD metadata.
"""

from __future__ import annotations

import json
import os
import re

import httpx

from eventx.category import with_category
from eventx.fetchers._common import USER_AGENT, parse_datetime
from eventx.models import HackathonEvent


def _configured_urls() -> list[str]:
    raw = os.getenv("LUMA_EVENT_URLS", "")
    return [u.strip() for u in raw.split(",") if u.strip()]


def _parse_event_page(url: str, html: str) -> HackathonEvent | None:
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
                    location = loc.get("name") or (loc.get("address") or {}).get("addressLocality")
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
    if not any(k in blob for k in ("bangalore", "bengaluru", "blr")):
        # Still accept configured URLs — user curated them.
        pass

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


def fetch_luma_hackathons() -> list[HackathonEvent]:
    urls = _configured_urls()
    if not urls:
        return []

    events: list[HackathonEvent] = []
    with httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        for url in urls:
            try:
                response = client.get(url)
                response.raise_for_status()
                event = _parse_event_page(url, response.text)
                if event:
                    events.append(event)
            except Exception as exc:
                print(f"  Warning: luma URL failed ({url}): {exc}")
    return events
