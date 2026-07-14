"""Hackathon subtype labels for HackathonX (software, hardware, buildathon, …)."""

from __future__ import annotations

from eventx.models import HackathonEvent

# Ordered: first match wins
_SUBTYPE_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("hardware", ("hardware", "iot", "robotics", "embedded", "electronics", "arduino", "pcb")),
    ("video", ("video hack", "film hack", "videoathon", "media hack")),
    ("game", ("game jam", "gamejam", "game hack", "unity hack")),
    ("ideathon", ("ideathon", "ideaathon", "idea hack")),
    ("buildathon", ("buildathon", "build-a-thon", "build a thon")),
    ("datathon", ("datathon", "data hack")),
    ("designathon", ("designathon", "ui/ux hack", "design hack")),
    ("makeathon", ("makeathon", "makerathon")),
    ("software", ("software", "web hack", "app hack", "coding hack", "fullstack")),
]


def infer_category(
    title: str,
    *,
    platform: str | None = None,
    hints: str | None = None,
) -> str:
    blob = f"{title} {hints or ''} {platform or ''}".lower()
    for category, keywords in _SUBTYPE_RULES:
        if any(k in blob for k in keywords):
            return category
    return "hackathon"


def with_category(event: HackathonEvent, *, hints: str | None = None) -> HackathonEvent:
    # Always refine subtype from title even if platform set a generic "hackathon"
    if not event.category or event.category in {"event", "hackathon"}:
        event.category = infer_category(event.title, platform=event.platform, hints=hints)
    return event


def category_label(category: str) -> str:
    return {
        "hackathon": "Hackathon",
        "software": "Software Hackathon",
        "hardware": "Hardware Hackathon",
        "buildathon": "Buildathon",
        "ideathon": "Ideathon",
        "video": "Video Hackathon",
        "game": "Game Jam",
        "datathon": "Datathon",
        "designathon": "Designathon",
        "makeathon": "Makeathon",
    }.get(category, "Hackathon")
