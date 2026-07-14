"""Cross-platform deduplication for the same hackathon listed in multiple places."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from eventx.models import HackathonEvent

_STRIP_WORDS = {
    "hackathon",
    "hack",
    "the",
    "a",
    "an",
    "and",
    "of",
    "for",
    "by",
    "2024",
    "2025",
    "2026",
    "2027",
}

_AGGREGATOR_HOSTS = {
    "unstop.com",
    "www.unstop.com",
    "devpost.com",
    "www.devpost.com",
    "hackerearth.com",
    "www.hackerearth.com",
    "dorahacks.io",
    "www.dorahacks.io",
    "hack2skill.com",
    "www.hack2skill.com",
    "vision.hack2skill.com",
    "mlh.io",
    "www.mlh.io",
    "lu.ma",
    "luma.com",
}


def normalize_title(title: str) -> str:
    text = title.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    words = [w for w in text.split() if w and w not in _STRIP_WORDS]
    return " ".join(words)


def event_fingerprint(event: HackathonEvent) -> str:
    try:
        parsed = urlparse(event.registration_url)
        host = (parsed.netloc or "").lower().removeprefix("www.")
        path = (parsed.path or "").rstrip("/").lower()
    except Exception:
        host, path = "", ""

    # Devfolio subdomain is a stable ID across scrapes.
    if host.endswith(".devfolio.co"):
        return f"devfolio:{host.split('.')[0]}"

    # Custom event websites are strong cross-platform IDs.
    if host and host not in _AGGREGATOR_HOSTS and not host.endswith(".devfolio.co"):
        return f"url:{host}{path}"

    title_key = normalize_title(event.title)
    if len(title_key) >= 6:
        return f"title:{title_key}"

    return event.dedupe_key


def merge_duplicate_events(events: list[HackathonEvent]) -> list[HackathonEvent]:
    """Collapse the same hackathon across platforms into one alert."""
    groups: dict[str, list[HackathonEvent]] = {}
    order: list[str] = []

    for event in events:
        key = event.fingerprint
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(event)

    merged: list[HackathonEvent] = []
    for key in order:
        group = groups[key]
        primary = _pick_primary(group)
        platforms = []
        for e in group:
            for p in e.platforms:
                if p not in platforms:
                    platforms.append(p)

        prize = next((e.prize_pool for e in group if e.prize_pool), primary.prize_pool)
        team = next((e.team_size for e in group if e.team_size), primary.team_size)
        eligibility = next((e.eligibility for e in group if e.eligibility), primary.eligibility)
        org = next((e.organisation for e in group if e.organisation), primary.organisation)
        location = next((e.location for e in group if e.location), primary.location)
        deadline = next((e.deadline for e in group if e.deadline), primary.deadline)

        primary.platforms = platforms
        primary.platform = platforms[0]
        primary.prize_pool = prize
        primary.team_size = team
        primary.eligibility = eligibility
        primary.organisation = org
        primary.location = location
        primary.deadline = deadline
        merged.append(primary)

    return merged


def _pick_primary(group: list[HackathonEvent]) -> HackathonEvent:
    prefer = ("unstop", "devfolio", "devpost", "mlh", "hack2skill", "hackerearth", "dorahacks", "luma")
    ranked = sorted(
        group,
        key=lambda e: (
            prefer.index(e.platform) if e.platform in prefer else 99,
            0 if e.deadline else 1,
            0 if e.prize_pool else 1,
        ),
    )
    return ranked[0]
