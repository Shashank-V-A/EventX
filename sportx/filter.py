from __future__ import annotations

import re
from datetime import datetime, timezone

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

# Substring keywords that are long enough / multi-word to safely use `in`
_SAFE_SUBSTRING = tuple(k for k in SPORT_KEYWORDS if " " in k or len(k.strip()) >= 5)
# Short tokens need word boundaries (mma matched "Gemma" / "Namma" before)
_SHORT_TOKENS = tuple(k.strip() for k in SPORT_KEYWORDS if " " not in k and len(k.strip()) < 5)


def _keyword_hit(text: str) -> bool:
    low = text.lower()
    if any(k in low for k in _SAFE_SUBSTRING):
        return True
    for token in _SHORT_TOKENS:
        if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", low):
            return True
    return False


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

    # Block obvious non-sport meetups even if a short token mis-hits
    if re.search(r"\b(hackathon|startup|founders?|huggingface|book\s*club)\b", title_l):
        if not any(
            s in title_l
            for s in ("marathon", "cricket", "pickleball", "badminton", "football", "run ")
        ):
            return False

    if _keyword_hit(title_l):
        return True
    if _TITLE_ONLY.search(title):
        return True
    if re.search(r"\brun\b", title_l) and re.search(
        r"\b(run\s+\d{4}|namma\s+run|\brun\b.*\b(club|challenge|series|fest))"
        r"|(\d+k|\b5k\b|\b10k\b).*\brun\b|\brun\b.*(\d+k|\b5k\b|\b10k\b)",
        title_l,
    ):
        return True

    # Venue / location extras — skip bare "sports" category noise
    extra_l = extra.lower()
    if _keyword_hit(extra_l) and "sports" not in extra_l.split():
        # still allow location "GoRally Pickleball ..."
        tokens = set(re.findall(r"[a-z0-9]+", extra_l))
        if "sports" in tokens and len(tokens) <= 2:
            return False
        return _keyword_hit(extra_l.replace("sports", " "))
    if _keyword_hit(extra_l):
        # If the only hit was the word sports alone in a short extra, ignore
        if re.fullmatch(r"\s*sports\s*", extra_l):
            return False
        return True
    return False


def is_bangalore_event(event: SportEvent) -> bool:
    return mentions_bangalore(event.location) or mentions_bangalore(event.title)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def is_upcoming_event(event: SportEvent) -> bool:
    """Drop sports listings whose start/end time is already past."""
    if event.deadline is None:
        return True
    return _as_utc(event.deadline) > datetime.now(timezone.utc)


def filter_events(events: list[SportEvent]) -> list[SportEvent]:
    out: list[SportEvent] = []
    for event in events:
        if not is_bangalore_event(event):
            continue
        if not is_sports_event(event.title, event.location or ""):
            continue
        if not is_upcoming_event(event):
            continue
        out.append(event)
    return out
