"""Infer a friendly event category from title/platform/type hints."""

from __future__ import annotations

import re

from eventx.models import HackathonEvent

_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("hackathon", ("hackathon", "buildathon", "codeathon", "hackfest", "ideathon")),
    ("marathon", ("marathon", "half marathon", "10k", "5k run", "running", "trail run", "cycling")),
    ("workshop", ("workshop", "masterclass", "bootcamp", "hands-on", "training")),
    ("seminar", ("seminar", "talk", "ama", "fireside", "webinar", "session")),
    ("conference", ("conference", "summit", "conclave", "symposium", "forum")),
    ("competition", ("competition", "contest", "challenge", "quiz", "olympiad", "pitch")),
    ("meetup", ("meetup", "networking", "community", "hangout")),
    ("festival", ("fest", "festival", "carnival", "fair")),
    ("music", ("concert", "live music", "gig", "DJ", "orchestra", "tour")),
    ("sports", ("tournament", "league match", "sports", "fitness", "yoga")),
    ("startup", ("startup", "pitch day", "demo day", "incubator")),
]


def infer_category(
    title: str,
    *,
    platform: str | None = None,
    hints: str | None = None,
) -> str:
    blob = f"{title} {hints or ''} {platform or ''}".lower()
    for category, keywords in _RULES:
        if any(k.lower() in blob for k in keywords):
            return category
    if platform in {"meetup"}:
        return "meetup"
    if platform in {"mlh", "hackerearth", "hack2skill"}:
        return "hackathon"
    if platform == "allevents":
        return "event"
    return "event"


def with_category(event: HackathonEvent, *, hints: str | None = None) -> HackathonEvent:
    if not event.category or event.category == "event":
        event.category = infer_category(event.title, platform=event.platform, hints=hints)
    return event


def category_label(category: str) -> str:
    return {
        "hackathon": "Hackathon",
        "marathon": "Marathon / Run",
        "workshop": "Workshop",
        "seminar": "Seminar",
        "conference": "Conference",
        "competition": "Competition",
        "meetup": "Meetup",
        "festival": "Festival",
        "music": "Music / Show",
        "sports": "Sports",
        "startup": "Startup",
        "event": "Event",
    }.get(category, category.title())
