import re
from datetime import datetime, timezone

from eventx.config import BANGALORE_KEYWORDS, HACKATHON_KEYWORDS
from eventx.models import HackathonEvent

# Highway names that mention Bengaluru but are not in Bangalore
HIGHWAY_FALSE_POSITIVES = (
    re.compile(r"bengaluru\s*[-–]\s*chennai", re.I),
    re.compile(r"bangalore\s*[-–]\s*chennai", re.I),
)

CONTRADICTORY_REGIONS = (
    "tamil nadu",
    "chennai",
    "poonamallee",
    "hyderabad",
    "telangana",
    "pune",
    "maharashtra",
    "mumbai",
    "delhi",
    "noida",
    "gurgaon",
    "gurugram",
    "kolkata",
    "west bengal",
    "kochi",
    "kerala",
    "jaipur",
    "rajasthan",
    "ahmedabad",
    "gujarat",
    "lucknow",
    "uttar pradesh",
    "bhubaneswar",
    "odisha",
    "chandigarh",
    "goa",
)

# Platforms whose listings are already hackathon feeds
_HACKATHON_NATIVE_PLATFORMS = frozenset(
    {
        "unstop",
        "devfolio",
        "devpost",
        "hackerearth",
        "hack2skill",
        "dorahacks",
        "mlh",
    }
)

_NON_HACKATHON_BLOCKERS = (
    "workshop series",
    "masterclass",
    "concert",
    "standup",
    "comedy show",
    "music festival",
    "meetup group",
)


def _contains_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    low = text.lower()
    for keyword in keywords:
        if keyword == "blr":
            # Avoid matching inside words like "tumblr"
            if re.search(r"(?<![a-z0-9])blr(?![a-z0-9])", low):
                return True
            continue
        if keyword in low:
            return True
    return False


def _strong_match(event: HackathonEvent) -> bool:
    strong_text = " ".join(
        [
            event.title or "",
            event.registration_url or "",
            event.organisation or "",
        ]
    ).lower()
    return _contains_keyword(strong_text, BANGALORE_KEYWORDS)


def _location_match(location: str) -> bool:
    loc = location.lower()
    if not _contains_keyword(loc, BANGALORE_KEYWORDS):
        return False

    for pattern in HIGHWAY_FALSE_POSITIVES:
        if pattern.search(loc):
            return False

    if any(region in loc for region in CONTRADICTORY_REGIONS):
        return "karnataka" in loc

    return True


def _event_venue_text(event: HackathonEvent) -> str:
    return " ".join(
        [
            event.title or "",
            event.location or "",
            event.organisation or "",
            event.registration_url or "",
            event.mode or "",
        ]
    ).lower()


def _mentions_other_city(text: str) -> bool:
    return any(region in text for region in CONTRADICTORY_REGIONS)


def _location_is_bangalore_only(location: str) -> bool:
    """True when location points at Bangalore and not another city venue."""
    loc = location.lower()
    if not _contains_keyword(loc, BANGALORE_KEYWORDS):
        return False
    for pattern in HIGHWAY_FALSE_POSITIVES:
        if pattern.search(loc):
            return False
    if _mentions_other_city(loc):
        # e.g. "Bengaluru & Pune finals" — not Bangalore-only
        return False
    return True


def _normalized_mode(event: HackathonEvent) -> str:
    mode = (event.mode or "").strip().lower()
    if mode in {"online", "virtual", "remote"}:
        return "online"
    if mode in {"hybrid", "blended"}:
        return "hybrid"
    if mode in {"offline", "in-person", "in_person", "physical"}:
        return "offline"
    location = (event.location or "").strip().lower()
    if location in {"online", "everywhere", "virtual", "remote"}:
        return "online"
    if "hybrid" in location:
        return "hybrid"
    return mode or "unknown"


def is_bangalore_match(event: HackathonEvent) -> bool:
    """
    Bangalore-relevant hackathons only:
    - Offline / finals in Bangalore
    - Early rounds may be online (hybrid OK) only if offline side is Bangalore
    - Reject finals / offline rounds in Pune, Delhi, Mumbai, etc.
    - Reject pan-India online with no Bangalore link
    """
    location = event.location or ""
    venue = _event_venue_text(event)

    has_bangalore = _strong_match(event) or (
        bool(location) and _location_match(location)
    )
    other_city = _mentions_other_city(venue)

    # Explicit other-city venue and no Bangalore → never
    if other_city and not has_bangalore:
        return False

    # Multi-city offline/hybrid (Bangalore + Pune/Delhi/…) → not Bangalore-only
    if other_city and has_bangalore:
        if location and _location_is_bangalore_only(location):
            # Location is cleanly Bangalore; other city only in title/org noise
            return True
        return False

    return has_bangalore


def is_hackathon_match(event: HackathonEvent) -> bool:
    """HackathonX: only software/hardware/buildathon/ideathon/etc. style events."""
    title_blob = " ".join(
        [
            event.title or "",
            event.registration_url or "",
        ]
    ).lower()

    if any(blocker in title_blob for blocker in _NON_HACKATHON_BLOCKERS):
        return False

    # Luma city feeds mix meetups/talks/hackathons — require title/url keywords only
    if event.platform == "luma":
        return _contains_keyword(title_blob, HACKATHON_KEYWORDS)

    # Ignore generic inferred category "hackathon" (not a real signal)
    category = (event.category or "").lower()
    if category == "hackathon":
        category = ""

    blob = " ".join(
        [
            title_blob,
            category,
            event.platform or "",
        ]
    ).lower()

    if _contains_keyword(blob, HACKATHON_KEYWORDS):
        return True

    # Native hackathon feeds (Unstop /hackathons, Devfolio, MLH, …)
    if event.platform in _HACKATHON_NATIVE_PLATFORMS:
        return True

    return False


def filter_bangalore(events: list[HackathonEvent]) -> list[HackathonEvent]:
    return [e for e in events if is_bangalore_match(e)]


def filter_hackathons(events: list[HackathonEvent]) -> list[HackathonEvent]:
    return [e for e in events if is_hackathon_match(e)]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def is_open_event(event: HackathonEvent) -> bool:
    """Drop listings whose registration/end time is already past."""
    if event.deadline is None:
        return True
    return _as_utc(event.deadline) > datetime.now(timezone.utc)


def filter_open_events(events: list[HackathonEvent]) -> list[HackathonEvent]:
    return [e for e in events if is_open_event(e)]
