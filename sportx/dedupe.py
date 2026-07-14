"""Cross-platform dedupe for the same sports event."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from sportx.models import SportEvent

_STRIP = {"the", "a", "an", "and", "of", "for", "by", "2024", "2025", "2026", "2027", "2028"}
_AGGREGATORS = {
    "allevents.in",
    "www.allevents.in",
    "meetup.com",
    "www.meetup.com",
}


def normalize_title(title: str) -> str:
    text = re.sub(r"[^a-z0-9\s]", " ", title.lower())
    words = [w for w in text.split() if w and w not in _STRIP]
    return " ".join(words)


def event_fingerprint(event: SportEvent) -> str:
    try:
        parsed = urlparse(event.registration_url)
        host = (parsed.netloc or "").lower().removeprefix("www.")
        path = (parsed.path or "").rstrip("/").lower()
    except Exception:
        host, path = "", ""

    if host and host not in _AGGREGATORS:
        return f"url:{host}{path}"

    title_key = normalize_title(event.title)
    if len(title_key) >= 6:
        return f"title:{title_key}"
    return event.dedupe_key


def merge_duplicate_events(events: list[SportEvent]) -> list[SportEvent]:
    groups: dict[str, list[SportEvent]] = {}
    order: list[str] = []
    for event in events:
        key = event.fingerprint
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(event)

    merged: list[SportEvent] = []
    for key in order:
        group = groups[key]
        primary = group[0]
        platforms: list[str] = []
        for e in group:
            for p in e.platforms:
                if p not in platforms:
                    platforms.append(p)
        primary.platforms = platforms
        primary.platform = platforms[0]
        primary.location = next((e.location for e in group if e.location), primary.location)
        primary.deadline = next((e.deadline for e in group if e.deadline), primary.deadline)
        primary.organisation = next(
            (e.organisation for e in group if e.organisation), primary.organisation
        )
        merged.append(primary)
    return merged
