"""Sport subtype labels for SportX."""

from __future__ import annotations

from sportx.models import SportEvent

_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("marathon", ("marathon", "half marathon", "ultra", "10k", "5k", "fun run", "running", "namma run", "bengaluru run", "bangalore run", "india run")),
    ("cricket", ("cricket", "ipl", "t20", "box cricket")),
    ("pickleball", ("pickleball", "pickle ball")),
    ("badminton", ("badminton",)),
    ("tennis", ("tennis", "padel")),
    ("football", ("football", "soccer", "futsal")),
    ("basketball", ("basketball",)),
    ("cycling", ("cycling", "bike ride", "bicycling")),
    ("swimming", ("swimming", "triathlon", "aqua")),
    ("yoga", ("yoga", "fitness", "workout")),
    ("tournament", ("tournament", "league", "championship", "open")),
]


def infer_category(title: str, *, hints: str | None = None) -> str:
    blob = f"{title} {hints or ''}".lower()
    for category, keywords in _RULES:
        if any(k in blob for k in keywords):
            return category
    return "sports"


def with_category(event: SportEvent, *, hints: str | None = None) -> SportEvent:
    if not event.category or event.category == "sports":
        event.category = infer_category(event.title, hints=hints)
    return event


def category_label(category: str) -> str:
    return {
        "marathon": "Marathon / Run",
        "cricket": "Cricket",
        "pickleball": "Pickleball",
        "badminton": "Badminton",
        "tennis": "Tennis / Padel",
        "football": "Football",
        "basketball": "Basketball",
        "cycling": "Cycling",
        "swimming": "Swimming",
        "yoga": "Fitness / Yoga",
        "tournament": "Tournament",
        "sports": "Sports Event",
    }.get(category, "Sports Event")
