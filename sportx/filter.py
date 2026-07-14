from __future__ import annotations

import re

from sportx.config import BANGALORE_KEYWORDS, NON_SPORT_BLOCKERS, SPORT_KEYWORDS
from sportx.models import SportEvent

# Title-only signals that are too short/ambiguous to use in free-text extras
_TITLE_ONLY = re.compile(
    r"\b("
    r"running|race|races|"
    r"match|matches|tournament|league|"
    r"open play|pickup|box cricket|"
    r"fun run|city run|night run|charity run|"
    r"bengaluru run|bangalore run|india run"
    r")\b",
    re.I,
)

_FALSE_RUN = re.compile(
    r"\b(how to run|run ai|run your|run a |running late|runtime|runner.?up)\b",
    re.I,
)


def mentions_bangalore(text: str | None) -> bool:
    if not text:
        return False
    blob = text.lower()
    return any(k in blob for k in BANGALORE_KEYWORDS)


def is_sports_event(title: str, extra: str = "") -> bool:
    """True if the listing looks like a sports/fitness activity (title-first)."""
    title_l = title.lower()
    blob = f"{title} {extra}".lower()

    if _FALSE_RUN.search(title):
        # still allow if a strong sport keyword survives
        if not any(
            s in blob
            for s in ("marathon", "cricket", "pickleball", "badminton", "10k", "5k")
        ):
            return False

    if any(b in blob for b in NON_SPORT_BLOCKERS):
        strong = (
            "marathon",
            "cricket",
            "pickleball",
            "badminton",
            "football",
            "tennis",
            "10k",
            "5k",
        )
        if not any(s in blob for s in strong):
            return False

    if any(k in title_l for k in SPORT_KEYWORDS):
        return True
    if _TITLE_ONLY.search(title):
        return True
    # Standalone "run" only when sports-like (… Run 2026 / Namma Run / …)
    if re.search(r"\brun\b", title_l) and re.search(
        r"\b(run\s+\d{4}|namma\s+run|\brun\b.*\b(club|challenge|series|fest))"
        r"|(\d+k|\b5k\b|\b10k\b).*\brun\b|\brun\b.*(\d+k|\b5k\b|\b10k\b)",
        title_l,
    ):
        return True
    # Extra may mention sport type (Meetup venue notes) but ignore bare "sports" category tags
    extra_l = extra.lower()
    for k in SPORT_KEYWORDS:
        if k == "sports":
            continue
        if k in extra_l:
            return True
    return False


def is_bangalore_event(event: SportEvent) -> bool:
    return mentions_bangalore(event.location) or mentions_bangalore(event.title)


def filter_events(events: list[SportEvent]) -> list[SportEvent]:
    out: list[SportEvent] = []
    for event in events:
        if not is_bangalore_event(event):
            continue
        if not is_sports_event(event.title, event.location or ""):
            continue
        out.append(event)
    return out
